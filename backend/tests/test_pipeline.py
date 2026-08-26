"""End-to-end pipeline tests that never touch the network."""

from __future__ import annotations

import pandas as pd
import pytest

from app.config import get_settings
from app.services.dataset import DatasetService
from app.services.pipeline import PipelineError, RecommendationPipeline
from app.services.scraper import ScraperError

CATALOGUE = pd.DataFrame(
    [
        {
            "TITLE": "Boat Rockerz 255 Pro Neckband Bluetooth",
            "PRICE": "₹999",
            "AVG RATING": "4.2",
            "DETAILS": "With Mic:Yes; Bluetooth version: v5.0; Battery life: 40 hr; ",
            "RETURN POLICY": "7 Days Replacement Policy?; ",
            "REVIEW COUNT": "12,000 Ratings & 900 Reviews",
            "URL": "https://www.flipkart.com/boat/p/itm1",
        },
        {
            "TITLE": "Aroma NB120 Amaze 50 Hours Playtime Neckband Bluetooth",
            "PRICE": "₹399",
            "AVG RATING": "4.0",
            "DETAILS": "With Mic:Yes; Bluetooth version: v5.3; Battery life: 50 hr; ",
            "RETURN POLICY": "7 Days Replacement Policy?; ",
            "REVIEW COUNT": "2,400 Ratings & 120 Reviews",
            "URL": "https://www.flipkart.com/aroma/p/itm2",
        },
        {
            "TITLE": "Apple AirPods Pro 2nd generation True Wireless",
            "PRICE": "₹17,999",
            "AVG RATING": "4.6",
            "DETAILS": "With Mic:Yes; Active Noise Cancellation: Yes; Battery life: 6 hr; ",
            "RETURN POLICY": "No Returns Applicable?; ",
            "REVIEW COUNT": "8,000 Ratings & 700 Reviews",
            "URL": "https://www.flipkart.com/airpods/p/itm3",
        },
        {
            "TITLE": "Generic Wired Earphone",
            "PRICE": "₹199",
            "AVG RATING": "3.2",
            "DETAILS": "With Mic:No; Connector type: 3.5mm; ",
            "RETURN POLICY": "7 Days Replacement Policy?; ",
            "REVIEW COUNT": "300 Ratings & 20 Reviews",
            "URL": "https://www.flipkart.com/generic/p/itm4",
        },
    ]
)


class StubScraper:
    """Stands in for the real scraper; the network is never used in tests."""

    def __init__(self, frame: pd.DataFrame | None = CATALOGUE, error: str | None = None) -> None:
        self.frame = frame
        self.error = error
        self.calls = 0

    def scrape(self, query: str, limit: int | None = None) -> pd.DataFrame:
        self.calls += 1
        if self.error:
            raise ScraperError(self.error)
        return self.frame.copy()


@pytest.fixture()
def pipeline(tmp_path, monkeypatch) -> RecommendationPipeline:
    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    service = DatasetService(settings, scraper=StubScraper())
    return RecommendationPipeline(settings, dataset_service=service)


def test_full_flow_returns_ranked_products(pipeline: RecommendationPipeline) -> None:
    result = pipeline.run("bluetooth headphones", "high battery life", limit=3)

    assert result.source.value == "live"
    assert len(result.results) == 3
    scores = [item.score for item in result.results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= item.score <= 1.0 for item in result.results)
    assert all(item.url and item.url.startswith("https://www.flipkart.com") for item in result.results)
    # long-battery products should beat the wired earphone
    assert "Wired" not in result.results[0].name


def test_price_filter_is_applied(pipeline: RecommendationPipeline) -> None:
    result = pipeline.run("bluetooth headphones", "under 1000", limit=10)
    assert result.parsed.max_price == 1000
    assert all(item.price <= 1000 for item in result.results)


def test_rating_filter_is_applied(pipeline: RecommendationPipeline) -> None:
    result = pipeline.run("bluetooth headphones", ">4.5 rating", limit=10)
    assert all(item.rating >= 4.5 for item in result.results)


def test_unsatisfiable_filters_are_relaxed_with_a_warning(
    pipeline: RecommendationPipeline,
) -> None:
    result = pipeline.run("bluetooth headphones", "under 50 rupees", limit=5)
    assert result.relaxed_filters == ["max_price"]
    assert result.results
    assert any("relaxed" in warning for warning in result.warnings)


def test_every_result_can_link_to_flipkart(tmp_path) -> None:
    """Datasets without a URL column still get a usable Flipkart search link."""
    frame = CATALOGUE.drop(columns=["URL"])
    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    service = DatasetService(settings, scraper=StubScraper(frame=frame))
    result = RecommendationPipeline(settings, service).run("headphones", "", limit=2)
    assert all(item.url is None for item in result.results)
    assert all(
        item.search_url.startswith("https://www.flipkart.com/search?q=")
        for item in result.results
    )


def test_results_carry_attributes_and_highlights(pipeline: RecommendationPipeline) -> None:
    result = pipeline.run("bluetooth headphones", "battery life", limit=1)
    product = result.results[0]
    assert product.attributes.get("Battery life")
    assert any("Battery life" in highlight for highlight in product.highlights)
    assert product.ratings_count > 0


def test_second_identical_search_performs_fresh_scrape(tmp_path) -> None:
    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    scraper = StubScraper()
    pipeline = RecommendationPipeline(settings, DatasetService(settings, scraper=scraper))

    pipeline.run("bluetooth headphones", "", limit=2)
    second = pipeline.run("bluetooth headphones", "", limit=2)

    assert scraper.calls == 2
    assert second.source.value == "live"


def test_scrape_failure_falls_back_to_the_repository_dataset(tmp_path) -> None:
    settings = get_settings().model_copy(update={"cache_dir": tmp_path / "cache"})
    scraper = StubScraper(error="blocked")
    pipeline = RecommendationPipeline(settings, DatasetService(settings, scraper=scraper))

    result = pipeline.run("bluetooth headphones", "good sound quality", limit=5)

    assert result.source.value == "seed"
    assert result.results
    assert any("repository" in warning for warning in result.warnings)


def test_scrape_failure_without_fallback_raises(tmp_path) -> None:
    settings = get_settings().model_copy(
        update={"cache_dir": tmp_path / "cache", "seed_dataset_fallback": False}
    )
    pipeline = RecommendationPipeline(
        settings, DatasetService(settings, scraper=StubScraper(error="blocked"))
    )

    with pytest.raises(PipelineError) as excinfo:
        pipeline.run("bluetooth headphones", "", limit=5)
    assert excinfo.value.stage == "scraping"


def test_limit_is_capped_by_settings(pipeline: RecommendationPipeline) -> None:
    result = pipeline.run("bluetooth headphones", "", limit=10_000)
    assert result.limit == get_settings().max_recommendations
