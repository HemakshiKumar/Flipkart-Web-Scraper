"""Flipkart scraper.

This module is a faithful refactor of the scraping cells in
`Web Scraping Project/code file.ipynb`. The CSS classes it looks for are the
ones that were already in the notebook (see `config.DEFAULT_SELECTORS`) - they
are NOT re-invented here. The notebook's per-field ``get_product_*`` helpers
map one-to-one onto the ``_field`` helpers below.

Differences from the notebook, all additive:

* the search URL is built from a user query instead of being pasted in;
* when a configured selector matches nothing, a structural fallback fills the
  gap (see :mod:`app.services.extractors`); the configured selectors always
  win when they match;
* the product URL is kept alongside the scraped fields (the website needs to
  link back to Flipkart);
* detail pages are fetched through a thread pool and a shared session;
* failures are logged instead of silently producing an empty frame.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from urllib.parse import quote_plus, urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
from bs4 import Tag

from app.config import Settings, get_settings
from app.services import extractors

logger = logging.getLogger(__name__)

#: Column order produced by the notebook, preserved so the existing
#: preprocessing step keeps working unchanged. ``URL`` is appended.
CSV_COLUMNS = [
    "TITLE",
    "PRICE",
    "AVG RATING",
    "DETAILS",
    "RETURN POLICY",
    "REVIEW COUNT",
    "URL",
]


class ScraperError(RuntimeError):
    """Raised when Flipkart could not be reached or returned nothing usable."""


@dataclass(slots=True)
class ScrapedProduct:
    """One row of the raw dataset, in the notebook's shape."""

    TITLE: str = ""
    PRICE: str = ""
    AVG_RATING: str = field(default="", metadata={"csv": "AVG RATING"})
    DETAILS: str = ""
    RETURN_POLICY: str = field(default="", metadata={"csv": "RETURN POLICY"})
    REVIEW_COUNT: str = field(default="", metadata={"csv": "REVIEW COUNT"})
    URL: str = ""

    def to_row(self) -> dict[str, str]:
        raw = asdict(self)
        return {
            "TITLE": raw["TITLE"],
            "PRICE": raw["PRICE"],
            "AVG RATING": raw["AVG_RATING"],
            "DETAILS": raw["DETAILS"],
            "RETURN POLICY": raw["RETURN_POLICY"],
            "REVIEW COUNT": raw["REVIEW_COUNT"],
            "URL": raw["URL"],
        }


def _find(content: Tag, selector: dict[str, str]) -> Tag | None:
    return content.find(selector["tag"], attrs={"class": selector["class"]})


def _find_all(content: Tag, selector: dict[str, str]) -> list[Tag]:
    return content.find_all(selector["tag"], attrs={"class": selector["class"]})


def _text(content: Tag, selector: dict[str, str]) -> str:
    """Equivalent of the notebook's ``get_product_*`` single-value helpers."""
    node = _find(content, selector)
    return node.text.strip() if node else ""


def _joined_text(content: Tag, selector: dict[str, str]) -> str:
    """Equivalent of ``get_product_details`` / ``rep_policy``.

    The notebook joined every match with ``"; "``, including the trailing
    separator; that exact format is kept because preprocessing parses it.
    """
    return "".join(node.text + "; " for node in _find_all(content, selector))


class FlipkartScraper:
    """Scrapes Flipkart search results using the repository's selectors."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.selectors = self.settings.selectors

    # -- search page ------------------------------------------------------
    def search_url(self, query: str) -> str:
        return self.settings.flipkart_search_url.format(query=quote_plus(query))

    def find_product_links(self, html: bytes | str) -> list[str]:
        """Notebook's ``find_product_links``, parameterised by page content."""
        content = bs(html, "html.parser")
        anchortags = _find_all(content, self.selectors["product_link"])
        links: list[str] = []
        seen: set[str] = set()
        for anchor in anchortags:
            href = anchor.get("href")
            if not href or not isinstance(href, str):
                continue
            absolute = urljoin(self.settings.flipkart_base_url, href)
            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)

        if links or not self.settings.structural_fallback:
            return links

        # The configured anchor class matched nothing: fall back to the
        # schema.org ItemList / product-URL shape (see services/extractors.py).
        logger.info("scrape.links_fallback selector=%s", self.selectors["product_link"])
        return extractors.extract_product_links(html, self.settings.flipkart_base_url)

    # -- product page -----------------------------------------------------
    def parse_product(self, html: bytes | str, url: str = "") -> ScrapedProduct:
        content = bs(html, "html.parser")
        product = ScrapedProduct(
            TITLE=_text(content, self.selectors["title"]),
            PRICE=_text(content, self.selectors["price"]),
            AVG_RATING=_text(content, self.selectors["rating"]),
            DETAILS=_joined_text(content, self.selectors["details"]),
            RETURN_POLICY=_joined_text(content, self.selectors["return_policy"]),
            REVIEW_COUNT=_text(content, self.selectors["review_count"]),
            URL=url,
        )
        if self.settings.structural_fallback:
            self._fill_gaps(product, content, html)
        return product

    def _fill_gaps(self, product: ScrapedProduct, content: Tag, html: bytes | str) -> None:
        """Fill only the fields the configured selectors could not produce."""
        text = html.decode("utf-8", "ignore") if isinstance(html, bytes) else html
        if not product.TITLE:
            product.TITLE = extractors.extract_title(content)
        if not product.PRICE:
            product.PRICE = extractors.extract_price(content)
        if not product.DETAILS:
            product.DETAILS = extractors.extract_details(content)
        if not product.AVG_RATING:
            product.AVG_RATING = extractors.extract_rating(text)
        if not product.REVIEW_COUNT:
            product.REVIEW_COUNT = extractors.extract_review_count(text)

    # -- orchestration ----------------------------------------------------
    def scrape(self, query: str, limit: int | None = None) -> pd.DataFrame:
        """Run the notebook's scraping loop for a search query.

        Returns a DataFrame with :data:`CSV_COLUMNS`. Raises
        :class:`ScraperError` when the search page cannot be fetched or when no
        product links are found (usually: Flipkart changed its markup, or the
        request was blocked).
        """
        if not self.settings.scraping_enabled:
            raise ScraperError("Live scraping is disabled by configuration")

        limit = limit or self.settings.max_products_per_search
        url = self.search_url(query)
        logger.info("scrape.search query=%r url=%s", query, url)

        with requests.Session() as session:
            session.headers.update(self.settings.request_headers)
            try:
                response = session.get(url, timeout=self.settings.request_timeout)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("scrape.search_failed query=%r error=%s", query, exc)
                raise ScraperError(f"Could not reach Flipkart search: {exc}") from exc

            links = self.find_product_links(response.content)
            logger.info("scrape.links query=%r found=%d", query, len(links))
            if not links:
                raise ScraperError(
                    "No product links found - the configured selectors did not "
                    "match the search page markup"
                )

            links = links[:limit]
            with ThreadPoolExecutor(max_workers=self.settings.scrape_concurrency) as pool:
                products = list(pool.map(lambda link: self._scrape_one(session, link), links))

        rows = [product.to_row() for product in products if product and product.TITLE]
        logger.info("scrape.products query=%r scraped=%d/%d", query, len(rows), len(links))
        if not rows:
            raise ScraperError(
                "Product pages were fetched but no fields matched the "
                "configured selectors"
            )
        return pd.DataFrame(rows, columns=CSV_COLUMNS)

    def _scrape_one(self, session: requests.Session, link: str) -> ScrapedProduct | None:
        """Fetch one product page, retrying once when Flipkart throttles us."""
        for attempt in range(self.settings.scrape_retries + 1):
            try:
                page = session.get(link, timeout=self.settings.request_timeout)
                page.raise_for_status()
            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                throttled = status in (403, 429, 503)
                if throttled and attempt < self.settings.scrape_retries:
                    time.sleep(self.settings.scrape_retry_delay * (attempt + 1))
                    continue
                logger.debug("scrape.product_failed url=%s status=%s", link, status)
                return None
            except requests.RequestException as exc:
                logger.debug("scrape.product_failed url=%s error=%s", link, exc)
                return None
            return self.parse_product(page.content, url=link)
        return None
