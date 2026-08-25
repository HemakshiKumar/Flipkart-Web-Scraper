"""Environment-driven configuration for the recommendation service.

Every tunable that used to be hard-coded inside the notebook (URLs, headers,
Flipkart CSS selectors, ranking weights) lives here so the engine can be
adjusted without touching the pipeline code.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

# --------------------------------------------------------------------------
# Flipkart selectors.
#
# These are the EXACT anchor tags / CSS classes used by the original notebook
# (`web-scraping-project/code file.ipynb`). They are the source of truth for
# scraping and must not be replaced with guesses. When Flipkart changes its
# markup, override them through the FLIPKART_SELECTORS environment variable
# (JSON object) instead of editing the scraper.
# --------------------------------------------------------------------------
DEFAULT_SELECTORS: dict[str, dict[str, str]] = {
    # search results page -> product links
    "product_link": {"tag": "a", "class": "wjcEIp"},
    # product detail page -> fields
    "title": {"tag": "span", "class": "VU-ZEz"},
    "price": {"tag": "div", "class": "Nx9bqj CxhGGd"},
    "rating": {"tag": "div", "class": "XQDdHH"},
    "details": {"tag": "li", "class": "_7eSDEz"},
    "return_policy": {"tag": "li", "class": "_1u+DIo"},
    "review_count": {"tag": "span", "class": "Wphh3N"},
}


class Settings(BaseSettings):
    """Runtime settings. All values can be overridden via environment vars."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- service ---------------------------------------------------------
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # --- request limits (also enforced by the API schema) ----------------
    max_recommendations: int = 50
    max_query_length: int = 120
    max_requirements_length: int = 500

    # --- scraping --------------------------------------------------------
    flipkart_search_url: str = (
        "https://www.flipkart.com/search?q={query}&otracker=search"
        "&otracker1=search&marketplace=FLIPKART&as-show=on&as=off"
    )
    flipkart_base_url: str = "https://www.flipkart.com"
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    accept_language: str = "en-US, en;q =0.5"
    request_timeout: float = 15.0
    #: How many product detail pages to fetch per search (scraping is the
    #: slow part of the pipeline, so this bounds the worst case).
    max_products_per_search: int = 20
    #: Flipkart throttles aggressive clients with 403s, so this stays low.
    scrape_concurrency: int = 4
    scrape_retries: int = 1
    scrape_retry_delay: float = 1.5
    scraping_enabled: bool = True
    #: When a configured selector matches nothing, fall back to structural
    #: extraction (schema.org JSON-LD + embedded rating state). Set to false to
    #: run strictly on the selectors above.
    structural_fallback: bool = True
    selectors_json: str | None = Field(default=None, alias="FLIPKART_SELECTORS")

    # --- dataset / cache --------------------------------------------------
    #: Scraped searches are cached here so repeated queries skip the network.
    cache_dir: Path = BACKEND_ROOT / "data" / "cache"
    cache_ttl_seconds: int = 60 * 60 * 6
    #: The dataset shipped with the repository. Used as the corpus when live
    #: scraping is unavailable (Flipkart blocks the request or has changed its
    #: markup) so the pipeline still returns real, previously scraped rows.
    seed_dataset: Path = REPO_ROOT / "web-scraping-project" / "flipkart_data.csv"
    seed_dataset_fallback: bool = True

    # --- ranking weights (see services/recommender.py) --------------------
    weight_similarity: float = 0.70
    weight_rating: float = 0.20
    weight_popularity: float = 0.10

    @field_validator("cache_dir", "seed_dataset", mode="before")
    @classmethod
    def _expand(cls, value: object) -> object:
        if isinstance(value, str):
            return Path(value).expanduser()
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def selectors(self) -> dict[str, dict[str, str]]:
        """Selector map, with optional environment overrides merged in."""
        selectors = {key: dict(value) for key, value in DEFAULT_SELECTORS.items()}
        if not self.selectors_json:
            return selectors
        try:
            overrides = json.loads(self.selectors_json)
        except json.JSONDecodeError:
            logger.warning("FLIPKART_SELECTORS is not valid JSON; using defaults")
            return selectors
        for key, value in overrides.items():
            if key in selectors and isinstance(value, dict):
                selectors[key].update(value)
            else:
                logger.warning("Ignoring unknown selector override: %s", key)
        return selectors

    @property
    def request_headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Language": self.accept_language}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
