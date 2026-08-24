"""API request / response schemas.

These are the only shapes the outside world sees. Nothing here exposes
selectors, file paths, dataset locations or stack traces.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.config import get_settings

_settings = get_settings()


class RecommendRequest(BaseModel):
    """POST /api/recommend body."""

    query: str = Field(..., min_length=2, max_length=_settings.max_query_length)
    requirements: str = Field("", max_length=_settings.max_requirements_length)
    limit: int = Field(10, ge=1, le=_settings.max_recommendations)
    refresh: bool = False

    @field_validator("query", "requirements")
    @classmethod
    def _clean(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("query")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("Query must be at least 2 characters")
        return value


class ParsedRequirementsModel(BaseModel):
    minRating: float | None = None
    maxRating: float | None = None
    minPrice: int | None = None
    maxPrice: int | None = None
    preferCheap: bool = False
    preferPopular: bool = False
    boostedFeatures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ProductModel(BaseModel):
    name: str
    price: int
    rating: float
    score: float
    similarity: float
    url: str | None = None
    searchUrl: str = ""
    ratingsCount: int = 0
    reviewsCount: int = 0
    returnPolicy: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    highlights: list[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
    query: str
    requirements: str
    limit: int
    count: int
    source: Literal["live", "cache", "seed"]
    datasetSize: int
    elapsedMs: int
    parsed: ParsedRequirementsModel
    warnings: list[str] = Field(default_factory=list)
    results: list[ProductModel] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: str
    #: Stable machine-readable code the frontend switches on.
    code: Literal[
        "invalid_request",
        "scraping_failed",
        "no_results",
        "internal_error",
    ]
    details: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    scrapingEnabled: bool
    seedDatasetAvailable: bool
    maxRecommendations: int
