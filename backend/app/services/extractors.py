"""Structural fallback extraction for Flipkart pages.

Why this module exists
----------------------
The selectors the notebook uses (``a.wjcEIp``, ``span.VU-ZEz`` …) are kept as
the primary extraction path - they are the repository's source of truth. They
no longer match the pages Flipkart serves today: the site now renders through
generated, per-build class names (``css-g5y9jx``, ``v1zwn21m`` …) and loads the
specification list separately.

Replacing the notebook's selectors with today's generated class names would be
guesswork with a shelf life of days. Instead, this module extracts the same
fields from things that are *structural* rather than cosmetic:

* the ``schema.org`` ``ItemList`` / ``Product`` JSON-LD blocks Flipkart embeds
  for search engines (product name, URL, price, description);
* the rating block in the page's embedded state JSON (``"rating"``,
  ``"ratingsCount"``, ``"reviewsCount"``);
* the ``/p/itm…`` URL shape, and the ``<h1>`` element.

The fallback only runs for fields the configured selectors left empty, so
updating :data:`app.config.DEFAULT_SELECTORS` (or the ``FLIPKART_SELECTORS``
environment variable) immediately takes precedence again.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup as bs

logger = logging.getLogger(__name__)

PRODUCT_URL_RE = re.compile(r"href=\"(/[^\"]*?/p/itm[^\"?#]+)")
RATING_BLOCK_RE = re.compile(
    r'"rating"\s*:\s*([\d.]+)\s*,\s*"ratingsCount"\s*:\s*(\d+)\s*,\s*"reviewsCount"\s*:\s*(\d+)'
)
RUPEE = "₹"

#: Storefront boilerplate that carries no product signal for the TF-IDF corpus.
_BOILERPLATE_RE = re.compile(
    r"only genuine products|free shipping|cash on delivery|30 day replacement"
    r"|emi options|shop online|best price|buy .* online|specs & features"
    r"|check full specification",
    re.I,
)


def _iter_json_ld(soup: bs) -> Iterable[dict[str, Any]]:
    """Yield every JSON-LD object on the page, flattening lists and @graph."""
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        stack: list[Any] = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                yield node
                if "@graph" in node:
                    stack.append(node["@graph"])


def _product_node(soup: bs) -> dict[str, Any] | None:
    for node in _iter_json_ld(soup):
        if node.get("@type") == "Product":
            return node
    return None


# --------------------------------------------------------------------------
# Search page
# --------------------------------------------------------------------------
def extract_product_links(html: bytes | str, base_url: str) -> list[str]:
    """Product URLs from the JSON-LD ``ItemList``, falling back to href shape."""
    soup = bs(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for node in _iter_json_ld(soup):
        if node.get("@type") != "ItemList":
            continue
        for entry in node.get("itemListElement") or []:
            if not isinstance(entry, dict):
                continue
            url = entry.get("url") or (entry.get("item") or {}).get("url")
            if isinstance(url, str) and "/p/" in url:
                absolute = urljoin(base_url, url)
                if absolute not in seen:
                    seen.add(absolute)
                    links.append(absolute)

    if links:
        logger.info("extractors.links source=json-ld count=%d", len(links))
        return links

    text = html.decode("utf-8", "ignore") if isinstance(html, bytes) else html
    for href in PRODUCT_URL_RE.findall(text):
        absolute = urljoin(base_url, href)
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    if links:
        logger.info("extractors.links source=href-pattern count=%d", len(links))
    return links


# --------------------------------------------------------------------------
# Product page
# --------------------------------------------------------------------------
def extract_title(soup: bs) -> str:
    node = _product_node(soup)
    name = node.get("name") if node else None
    if isinstance(name, str) and name.strip():
        return name.strip()
    heading = soup.find("h1")
    if heading:
        # Flipkart appends a "… more" affordance to the visible heading.
        return re.sub(r"\s*\.\.\.\s*more$", "", heading.get_text(" ", strip=True))
    return ""


def extract_price(soup: bs) -> str:
    """Price in the notebook's raw string form (``"₹1,299"``)."""
    node = _product_node(soup)
    offers = node.get("offers") if node else None
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if isinstance(offers, dict):
        price = offers.get("price")
        if price is not None:
            try:
                return "{0}{1:,}".format(RUPEE, int(float(price)))
            except (TypeError, ValueError):
                pass
    return ""


def extract_details(soup: bs) -> str:
    """Description text, in the notebook's ``"…; …; "`` fragment format.

    Flipkart loads the structured specification table separately, so the
    marketing description is the richest text available from a single request.
    It feeds the same TF-IDF corpus the specification list used to.
    """
    node = _product_node(soup)
    description = node.get("description") if node else None
    if not isinstance(description, str) or not description.strip():
        return ""
    fragments = [
        part.strip()
        for part in re.split(r"[;|\n]|(?<=[a-zA-Z])\.\s", description)
        if part.strip() and not _BOILERPLATE_RE.search(part)
    ]
    return "".join(fragment + "; " for fragment in fragments[:12])


def extract_rating(html: str) -> str:
    match = RATING_BLOCK_RE.search(html)
    if not match:
        return ""
    rating = float(match.group(1))
    return "{0:g}".format(rating) if rating > 0 else ""


def extract_review_count(html: str) -> str:
    """Review counts in the notebook's ``"N Ratings & M Reviews"`` form."""
    match = RATING_BLOCK_RE.search(html)
    if not match:
        return ""
    ratings, reviews = int(match.group(2)), int(match.group(3))
    if ratings == 0 and reviews == 0:
        return ""
    return "{0:,} Ratings & {1:,} Reviews".format(ratings, reviews)
