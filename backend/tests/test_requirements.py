from __future__ import annotations

import pytest

from app.services.requirements import parse_requirements


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (">4.5 rating", 4.5),
        ("at least 4 star rating", 4.0),
        ("4+ rating", 4.0),
        ("rating above 4.2", 4.2),
        ("minimum 3.5 rating", 3.5),
        ("highly rated", 4.0),
    ],
)
def test_minimum_rating_forms(text: str, expected: float) -> None:
    assert parse_requirements(text).min_rating == expected


def test_impossible_rating_is_clamped() -> None:
    parsed = parse_requirements(">5 rating")
    assert parsed.min_rating == 4.5
    assert any("above 5" in note for note in parsed.notes)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("under ₹5000", 5000),
        ("under 5,000", 5000),
        ("below 3k", 3000),
        ("less than 2000", 2000),
        ("upto Rs 1500", 1500),
        ("I want something under 3000 with at least 4 star rating", 3000),
    ],
)
def test_maximum_price_forms(text: str, expected: int) -> None:
    assert parse_requirements(text).max_price == expected


def test_price_range() -> None:
    parsed = parse_requirements("between 1000 and 3000")
    assert (parsed.min_price, parsed.max_price) == (1000, 3000)


def test_rating_bound_is_not_mistaken_for_a_price() -> None:
    parsed = parse_requirements("above 4.5 rating")
    assert parsed.min_price is None
    assert parsed.min_rating == 4.5


def test_combined_constraints() -> None:
    parsed = parse_requirements("I want something under 3000 with at least 4 star rating")
    assert parsed.max_price == 3000
    assert parsed.min_rating == 4.0


def test_feature_synonyms_expand_the_query() -> None:
    parsed = parse_requirements("high battery life, good sound quality", "bluetooth headphones")
    assert "battery life" in parsed.boosted_features
    assert "sound quality" in parsed.boosted_features
    terms = parsed.query_text()
    assert "playtime" in terms and "bass" in terms
    assert "bluetooth" in terms and "headphones" in terms


def test_cheap_preference_adds_price_weight() -> None:
    parsed = parse_requirements("high rated and cheap")
    assert parsed.prefer_cheap is True
    assert parsed.weight_overrides.get("price", 0) > 0
    assert parsed.min_rating == 4.0


def test_priority_phrase_reweights_terms() -> None:
    parsed = parse_requirements("battery life is more important than price")
    terms = parsed.query_terms
    assert terms.count("battery") >= 2
    assert parsed.weight_overrides.get("price") == 0.05


def test_empty_requirements_fall_back_to_the_product_query() -> None:
    parsed = parse_requirements("", "bluetooth headphones")
    assert parsed.query_text() == "bluetooth headphones"
    assert parsed.has_filters is False


def test_parsing_is_deterministic() -> None:
    text = "under 5000, >4.2 rating, good sound quality"
    first = parse_requirements(text, "earbuds").to_dict()
    second = parse_requirements(text, "earbuds").to_dict()
    assert first == second
