"""FastAPI service exposing the existing recommendation engine.

Endpoints
    GET  /api/health     - readiness + capability probe
    POST /api/recommend  - run the full pipeline for a query

Errors are always returned as :class:`app.models.ErrorResponse`; the detailed
exception stays in the server log.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import configure_logging, request_id_var
from app.models import (
    ErrorResponse,
    HealthResponse,
    ParsedRequirementsModel,
    ProductModel,
    RecommendRequest,
    RecommendResponse,
)
from app.services.pipeline import PipelineError, PipelineResult, get_pipeline

logger = logging.getLogger("app.api")
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    logger.info(
        "service.start scraping_enabled=%s seed=%s",
        settings.scraping_enabled,
        settings.seed_dataset.exists(),
    )
    get_pipeline()
    yield
    logger.info("service.stop")


app = FastAPI(
    title="Flipkart Recommendation API",
    version="1.0.0",
    description="HTTP interface for the repository's scraping + TF-IDF recommendation engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    token = request_id_var.set(uuid.uuid4().hex[:8])
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id_var.get()
        return response
    finally:
        request_id_var.reset(token)


def _error(code: str, message: str, http_status: int) -> JSONResponse:
    payload = ErrorResponse(error=message, code=code)  # type: ignore[arg-type]
    return JSONResponse(status_code=http_status, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info("request.invalid errors=%s", exc.errors())
    return _error(
        "invalid_request",
        "The search request was not valid. Check the query, requirements and count.",
        422,
    )


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("request.unhandled error=%s", exc)
    return _error(
        "internal_error",
        "Something went wrong while generating recommendations.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        scrapingEnabled=settings.scraping_enabled,
        seedDatasetAvailable=settings.seed_dataset.exists(),
        maxRecommendations=settings.max_recommendations,
    )


@app.post(
    "/api/recommend",
    response_model=RecommendResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def recommend(payload: RecommendRequest) -> JSONResponse:
    pipeline = get_pipeline()
    try:
        result = pipeline.run(
            query=payload.query,
            requirements=payload.requirements,
            limit=payload.limit,
            refresh=payload.refresh,
        )
    except PipelineError as exc:
        logger.warning("recommend.failed stage=%s error=%s", exc.stage, exc)
        return _error(
            "scraping_failed" if exc.stage == "scraping" else "internal_error",
            "We couldn't retrieve products right now. Please try again in a moment."
            if exc.stage == "scraping"
            else "Something went wrong while generating recommendations.",
            status.HTTP_502_BAD_GATEWAY
            if exc.stage == "scraping"
            else status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(content=_serialise(result).model_dump())


def _serialise(result: PipelineResult) -> RecommendResponse:
    return RecommendResponse(
        query=result.query,
        requirements=result.requirements,
        limit=result.limit,
        count=len(result.results),
        source=result.source.value,  # type: ignore[arg-type]
        datasetSize=result.dataset_size,
        elapsedMs=result.elapsed_ms,
        parsed=ParsedRequirementsModel(**result.parsed.to_dict()),  # type: ignore[arg-type]
        warnings=result.warnings,
        results=[ProductModel(**item.to_dict()) for item in result.results],  # type: ignore[arg-type]
    )
