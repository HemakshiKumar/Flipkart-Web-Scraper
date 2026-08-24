"""Dataset acquisition and caching.

Scraping is by far the slowest and least reliable step of the pipeline, so it
is isolated behind this module:

    query -> cache lookup -> (miss) scrape -> cache write -> DataFrame

The cache is a directory of CSVs in exactly the format the notebook produced,
which means a cached search can be inspected, edited or replaced by hand, and
the recommendation engine can be run against it without any network access.

If a live scrape fails and ``SEED_DATASET_FALLBACK`` is enabled, the dataset
shipped with the repository (``Web Scraping Project/flipkart_data.csv``) is
used instead. That file is real scraped data, not fixtures - the API reports
which source was used so the UI can be honest about it.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pandas as pd

from app.config import Settings, get_settings
from app.services.scraper import FlipkartScraper, ScraperError

logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class DatasetSource(str, Enum):
    """Where the rows the user is looking at came from."""

    LIVE = "live"
    CACHE = "cache"
    SEED = "seed"


class DatasetError(RuntimeError):
    """Raised when no dataset could be obtained for a query."""


@dataclass(slots=True)
class Dataset:
    frame: pd.DataFrame
    source: DatasetSource
    cache_key: str
    warning: str | None = None


def cache_key(query: str) -> str:
    normalised = " ".join(query.lower().split())
    slug = _SLUG_RE.sub("-", normalised).strip("-")[:48] or "query"
    digest = hashlib.sha1(normalised.encode("utf-8")).hexdigest()[:10]
    return "{0}-{1}".format(slug, digest)


class DatasetService:
    """Provides the raw product dataset for a search query."""

    def __init__(
        self, settings: Settings | None = None, scraper: FlipkartScraper | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.scraper = scraper or FlipkartScraper(self.settings)
        self.cache_dir: Path = self.settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- cache ------------------------------------------------------------
    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / "{0}.csv".format(key)

    def read_cache(self, key: str, ignore_ttl: bool = False) -> pd.DataFrame | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if not ignore_ttl and age > self.settings.cache_ttl_seconds:
            logger.info("dataset.cache_stale key=%s age=%.0fs", key, age)
            return None
        try:
            frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError) as exc:
            logger.warning("dataset.cache_unreadable key=%s error=%s", key, exc)
            return None
        logger.info("dataset.cache_hit key=%s rows=%d age=%.0fs", key, len(frame), age)
        return frame

    def write_cache(self, key: str, frame: pd.DataFrame) -> None:
        path = self._cache_path(key)
        try:
            frame.to_csv(path, header=True, index=False)
            logger.info("dataset.cache_write key=%s rows=%d", key, len(frame))
        except OSError as exc:  # pragma: no cover - disk failures
            logger.warning("dataset.cache_write_failed key=%s error=%s", key, exc)

    # -- seed dataset ------------------------------------------------------
    def read_seed(self) -> pd.DataFrame | None:
        path = self.settings.seed_dataset
        if not path.exists():
            logger.warning("dataset.seed_missing path=%s", path)
            return None
        try:
            frame = pd.read_csv(path)
        except (OSError, pd.errors.ParserError) as exc:
            logger.warning("dataset.seed_unreadable error=%s", exc)
            return None
        logger.info("dataset.seed_loaded rows=%d", len(frame))
        return frame

    # -- public API --------------------------------------------------------
    def get(self, query: str, refresh: bool = False) -> Dataset:
        """Return the dataset for ``query``, scraping only when necessary."""
        key = cache_key(query)

        if not refresh:
            cached = self.read_cache(key)
            if cached is not None and not cached.empty:
                return Dataset(cached, DatasetSource.CACHE, key)

        scrape_error: str | None = None
        try:
            frame = self.scraper.scrape(query)
            self.write_cache(key, frame)
            return Dataset(frame, DatasetSource.LIVE, key)
        except ScraperError as exc:
            scrape_error = str(exc)
            logger.warning("dataset.scrape_failed query=%r error=%s", query, exc)

        # A stale cache is still better than nothing.
        stale = self.read_cache(key, ignore_ttl=True)
        if stale is not None and not stale.empty:
            return Dataset(
                stale,
                DatasetSource.CACHE,
                key,
                warning="Showing cached results - live scraping is unavailable.",
            )

        if self.settings.seed_dataset_fallback:
            seed = self.read_seed()
            if seed is not None and not seed.empty:
                return Dataset(
                    seed,
                    DatasetSource.SEED,
                    key,
                    warning=(
                        "Live scraping is unavailable, so recommendations were "
                        "computed from the dataset stored in this repository."
                    ),
                )

        raise DatasetError(scrape_error or "No dataset available for this query")
