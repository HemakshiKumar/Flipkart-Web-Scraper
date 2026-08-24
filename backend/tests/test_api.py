"""API contract tests, including what must never leak to the client."""

from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services import pipeline as pipeline_module
from app.services.dataset import DatasetService
from app.services.pipeline import RecommendationPipeline
from tests.test_pipeline import CATALOGUE, StubScraper


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    service = DatasetService(settings, scraper=StubScraper())
    test_pipeline = RecommendationPipeline(settings, dataset_service=service)
    monkeypatch.setattr(pipeline_module, "get_pipeline", lambda: test_pipeline)
    monkeypatch.setattr("app.main.get_pipeline", lambda: test_pipeline)
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_recommend_contract(client: TestClient) -> None:
    response = client.post(
        "/api/recommend",
        json={
            "query": "bluetooth headphones",
            "requirements": ">4 rating, high battery life",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["query"] == "bluetooth headphones"
    assert body["count"] == len(body["results"]) <= 3
    assert body["source"] in {"live", "cache", "seed"}
    assert body["parsed"]["minRating"] == 4.0

    product = body["results"][0]
    assert set(
        ["name", "price", "rating", "score", "url", "attributes", "highlights"]
    ) <= set(product)
    assert isinstance(product["price"], int)
    assert 0 <= product["score"] <= 1


@pytest.mark.parametrize(
    "payload",
    [
        {"query": "a", "limit": 5},
        {"query": "headphones", "limit": 0},
        {"query": "headphones", "limit": 10_000},
        {"requirements": "cheap"},
        {"query": "x" * 500, "limit": 5},
    ],
)
def test_invalid_requests_are_rejected(client: TestClient, payload: dict) -> None:
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_errors_never_leak_internals(tmp_path, monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("C:/secret/path/scraper.py exploded: class=wjcEIp")

    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    broken = RecommendationPipeline(settings, DatasetService(settings, scraper=StubScraper()))
    monkeypatch.setattr("app.main.get_pipeline", lambda: broken)
    monkeypatch.setattr(RecommendationPipeline, "run", boom)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/recommend", json={"query": "headphones", "limit": 5})

    assert response.status_code == 500
    body = response.text
    assert "secret" not in body and "wjcEIp" not in body and "Traceback" not in body
    assert response.json()["code"] == "internal_error"


def test_scraping_failure_returns_a_clean_502(tmp_path, monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={"cache_dir": tmp_path / "cache", "seed_dataset_fallback": False}
    )
    failing = RecommendationPipeline(
        settings, DatasetService(settings, scraper=StubScraper(error="blocked by flipkart"))
    )
    monkeypatch.setattr("app.main.get_pipeline", lambda: failing)

    with TestClient(app) as client:
        response = client.post("/api/recommend", json={"query": "headphones", "limit": 5})

    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "scraping_failed"
    assert "flipkart" not in body["error"].lower()


def test_response_is_json_serialisable_for_the_frontend(client: TestClient) -> None:
    response = client.post(
        "/api/recommend", json={"query": "bluetooth headphones", "limit": 2}
    )
    body = response.json()
    assert isinstance(body["warnings"], list)
    assert isinstance(body["parsed"]["boostedFeatures"], list)
    assert pd.notna(body["elapsedMs"])
