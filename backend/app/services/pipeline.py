"""End-to-end recommendation pipeline.

    user input
        -> requirements parsing        (services.requirements)
        -> dataset acquisition         (services.dataset -> services.scraper)
        -> preprocessing               (services.preprocessing)
        -> TF-IDF engine + ranking     (services.recommender)
        -> ranked products

Every stage logs a single structured line, so a failed request can be traced
to the stage that produced it. Built engines are memoised per dataset so a
repeated search does not re-vectorise the corpus.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock

from app.config import Settings, get_settings
from app.services.dataset import Dataset, DatasetError, DatasetService, DatasetSource
from app.services.preprocessing import PreprocessingError, preprocess
from app.services.recommender import (
    Recommendation,
    RecommendationEngine,
    RecommendationError,
)
from app.services.requirements import ParsedRequirements, parse_requirements

logger = logging.getLogger(__name__)

ENGINE_CACHE_SIZE = 16


class PipelineError(RuntimeError):
    """A user-facing pipeline failure with a stage attached."""

    def __init__(self, message: str, stage: str) -> None:
        super().__init__(message)
        self.stage = stage


@dataclass(slots=True)
class PipelineResult:
    query: str
    requirements: str
    limit: int
    results: list[Recommendation]
    parsed: ParsedRequirements
    source: DatasetSource
    dataset_size: int
    relaxed_filters: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed_ms: int = 0


class RecommendationPipeline:
    """Orchestrates the existing scraping / preprocessing / ranking stages."""

    def __init__(
        self, settings: Settings | None = None, dataset_service: DatasetService | None = None
    ) -> None:
        self.settings = settings or get_settings()
        self.datasets = dataset_service or DatasetService(self.settings)
        self._engines: OrderedDict[str, RecommendationEngine] = OrderedDict()
        self._lock = Lock()

    # -- engine cache -----------------------------------------------------
    def _engine_for(self, dataset: Dataset) -> RecommendationEngine:
        key = "{0}:{1}:{2}".format(dataset.cache_key, dataset.source.value, len(dataset.frame))
        with self._lock:
            engine = self._engines.get(key)
            if engine is not None:
                self._engines.move_to_end(key)
                logger.info("pipeline.engine_cache_hit key=%s", key)
                return engine

        frame = preprocess(dataset.frame)
        engine = RecommendationEngine(frame, self.settings)

        with self._lock:
            self._engines[key] = engine
            self._engines.move_to_end(key)
            while len(self._engines) > ENGINE_CACHE_SIZE:
                self._engines.popitem(last=False)
        return engine

    # -- public API -------------------------------------------------------
    def run(
        self,
        query: str,
        requirements: str = "",
        limit: int = 10,
        refresh: bool = False,
    ) -> PipelineResult:
        started = time.perf_counter()
        limit = max(1, min(limit, self.settings.max_recommendations))
        logger.info(
            "pipeline.start query=%r requirements=%r limit=%d refresh=%s",
            query, requirements, limit, refresh,
        )

        parsed = parse_requirements(requirements, product_query=query)

        try:
            dataset = self.datasets.get(query, refresh=refresh)
        except DatasetError as exc:
            logger.error("pipeline.failed stage=dataset query=%r error=%s", query, exc)
            raise PipelineError(str(exc), stage="scraping") from exc

        try:
            engine = self._engine_for(dataset)
        except PreprocessingError as exc:
            logger.error("pipeline.failed stage=preprocessing query=%r error=%s", query, exc)
            raise PipelineError(str(exc), stage="preprocessing") from exc
        except RecommendationError as exc:
            logger.error("pipeline.failed stage=engine query=%r error=%s", query, exc)
            raise PipelineError(str(exc), stage="engine") from exc

        try:
            results, relaxed = engine.recommend(parsed, limit=limit)
        except RecommendationError as exc:
            logger.error("pipeline.failed stage=ranking query=%r error=%s", query, exc)
            raise PipelineError(str(exc), stage="ranking") from exc

        warnings: list[str] = []
        if dataset.warning:
            warnings.append(dataset.warning)
        if relaxed:
            warnings.append(
                "Some filters were relaxed because no product matched them: "
                + ", ".join(_FILTER_LABELS.get(name, name) for name in relaxed)
            )
        if results and len(results) < limit:
            warnings.append(
                "Only {0} of the {1} requested products matched.".format(len(results), limit)
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "pipeline.done query=%r source=%s dataset=%d returned=%d elapsed_ms=%d",
            query, dataset.source.value, len(engine.df), len(results), elapsed_ms,
        )
        return PipelineResult(
            query=query,
            requirements=requirements,
            limit=limit,
            results=results,
            parsed=parsed,
            source=dataset.source,
            dataset_size=len(engine.df),
            relaxed_filters=relaxed,
            warnings=warnings,
            elapsed_ms=elapsed_ms,
        )


_FILTER_LABELS = {
    "min_rating": "minimum rating",
    "max_rating": "maximum rating",
    "min_price": "minimum price",
    "max_price": "maximum price",
}

_pipeline: RecommendationPipeline | None = None
_pipeline_lock = Lock()


def get_pipeline() -> RecommendationPipeline:
    """Process-wide pipeline singleton (keeps the engine cache warm)."""
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            _pipeline = RecommendationPipeline(get_settings())
        return _pipeline
