"""Recommendation engine.

The core is unchanged from the notebook: a ``TfidfVectorizer(stop_words=
'english')`` fitted on the ``DESCRIPTION`` column, and cosine similarity
between the user's query vector and the product matrix.

What is added around it:

* the query is the *expanded* text produced by :mod:`app.services.requirements`
  (product query + user words + synonyms), so descriptive requirements match
  the scraped detail vocabulary;
* numeric filters (rating / price) are applied as a mask, and relaxed in a
  documented order when nothing survives;
* the final ranking blends similarity with the rating / review-reliability
  strategy the project README describes, so a 5-star product with two ratings
  cannot outrank a 4.5-star product with thousands of them.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import Settings, get_settings
from app.services.requirements import ParsedRequirements

logger = logging.getLogger(__name__)

_ATTRIBUTE_SPLIT = re.compile(r"\s*[;|]\s*")


class RecommendationError(RuntimeError):
    """Raised when the engine cannot be built or produces nothing."""


@dataclass(slots=True)
class Recommendation:
    """One ranked product, ready to be serialised for the frontend."""

    name: str
    price: int
    rating: float
    score: float
    similarity: float
    url: str | None = None
    #: Always populated: a Flipkart search for this exact title. Used when the
    #: dataset predates the URL column, so the UI can always link out.
    search_url: str = ""
    ratings_count: int = 0
    reviews_count: int = 0
    return_policy: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    highlights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "price": self.price,
            "rating": self.rating,
            "score": round(self.score, 4),
            "similarity": round(self.similarity, 4),
            "url": self.url or None,
            "searchUrl": self.search_url,
            "ratingsCount": self.ratings_count,
            "reviewsCount": self.reviews_count,
            "returnPolicy": self.return_policy or None,
            "attributes": self.attributes,
            "highlights": self.highlights,
        }


def parse_attributes(details: object) -> dict[str, str]:
    """Turn the scraped ``"key: value; key: value; "`` string into a dict."""
    if details is None or (isinstance(details, float) and pd.isna(details)):
        return {}
    attributes: dict[str, str] = {}
    for fragment in _ATTRIBUTE_SPLIT.split(str(details)):
        fragment = fragment.strip()
        if not fragment or ":" not in fragment:
            continue
        key, _, value = fragment.partition(":")
        key, value = key.strip(), value.strip()
        # Prose sentences occasionally contain a colon; skip those.
        if not key or not value or len(key) > 40 or len(key.split()) > 5:
            continue
        attributes.setdefault(key, value)
    return attributes


def _normalise(values: np.ndarray) -> np.ndarray:
    """Min-max scale to [0, 1]; a flat vector maps to all-ones."""
    if values.size == 0:
        return values
    low, high = float(values.min()), float(values.max())
    if math.isclose(low, high):
        return np.ones_like(values, dtype=float)
    return (values - low) / (high - low)


class RecommendationEngine:
    """TF-IDF + cosine similarity recommender over a preprocessed dataset."""

    def __init__(self, df: pd.DataFrame, settings: Settings | None = None) -> None:
        if df is None or df.empty:
            raise RecommendationError("Cannot build an engine from an empty dataset")
        self.settings = settings or get_settings()
        self.df = df.reset_index(drop=True)
        # --- the notebook's model, verbatim ---
        self.tfidf = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.tfidf.fit_transform(self.df["DESCRIPTION"])
        logger.info(
            "engine.built products=%d vocabulary=%d",
            len(self.df),
            len(self.tfidf.vocabulary_),
        )

    # -- filtering --------------------------------------------------------
    def _mask(self, parsed: ParsedRequirements, skip: set[str]) -> np.ndarray:
        mask = np.ones(len(self.df), dtype=bool)
        if parsed.min_rating is not None and "min_rating" not in skip:
            mask &= self.df["AVG RATING"].to_numpy() >= parsed.min_rating
        if parsed.max_rating is not None and "max_rating" not in skip:
            mask &= self.df["AVG RATING"].to_numpy() <= parsed.max_rating
        if parsed.max_price is not None and "max_price" not in skip:
            mask &= self.df["PRICE"].to_numpy() <= parsed.max_price
        if parsed.min_price is not None and "min_price" not in skip:
            mask &= self.df["PRICE"].to_numpy() >= parsed.min_price
        return mask

    def _apply_filters(self, parsed: ParsedRequirements) -> tuple[np.ndarray, list[str]]:
        """Apply filters, relaxing them one at a time if nothing survives.

        Relaxation order is fixed (price bounds first, then rating bounds) so
        the result is reproducible.
        """
        skip: set[str] = set()
        relaxed: list[str] = []
        order = ["min_price", "max_price", "max_rating", "min_rating"]
        mask = self._mask(parsed, skip)
        for name in order:
            if mask.any():
                break
            value = getattr(parsed, name, None)
            if value is None:
                continue
            skip.add(name)
            relaxed.append(name)
            mask = self._mask(parsed, skip)
        if relaxed:
            logger.info("engine.filters_relaxed relaxed=%s", relaxed)
        return mask, relaxed

    # -- scoring ----------------------------------------------------------
    def _weights(self, parsed: ParsedRequirements) -> dict[str, float]:
        weights = {
            "similarity": self.settings.weight_similarity,
            "rating": self.settings.weight_rating,
            "popularity": self.settings.weight_popularity,
            "price": 0.0,
        }
        weights.update(parsed.weight_overrides)
        if parsed.prefer_cheap and weights["price"] <= 0:
            weights["price"] = 0.18
        total = sum(weights.values())
        if total <= 0:
            raise RecommendationError("Ranking weights sum to zero")
        return {key: value / total for key, value in weights.items()}

    def _score(
        self, frame: pd.DataFrame, similarities: np.ndarray, parsed: ParsedRequirements
    ) -> np.ndarray:
        weights = self._weights(parsed)
        rating = frame["AVG RATING"].to_numpy(dtype=float) / 5.0
        # Review reliability: log-scaled so 10k ratings is "better" than 1k but
        # not 10x better, which is what the README's strategy asks for.
        counts = frame["RATINGS COUNT"].to_numpy(dtype=float) + frame[
            "REVIEWS COUNT"
        ].to_numpy(dtype=float)
        popularity = _normalise(np.log1p(counts))
        price_affinity = 1.0 - _normalise(frame["PRICE"].to_numpy(dtype=float))

        score = (
            weights["similarity"] * similarities
            + weights["rating"] * rating
            + weights["popularity"] * popularity
            + weights["price"] * price_affinity
        )
        return np.clip(score, 0.0, 1.0)

    # -- public API -------------------------------------------------------
    def recommend(
        self, parsed: ParsedRequirements, limit: int = 10
    ) -> tuple[list[Recommendation], list[str]]:
        """Return the top ``limit`` products plus the list of relaxed filters."""
        query_text = parsed.query_text().strip()
        if not query_text:
            raise RecommendationError("Empty search query")

        mask, relaxed = self._apply_filters(parsed)
        if not mask.any():
            return [], relaxed

        # --- the notebook's scoring step, verbatim ---
        user_vector = self.tfidf.transform([query_text])
        similarities = cosine_similarity(user_vector, self.tfidf_matrix).flatten()

        indices = np.flatnonzero(mask)
        frame = self.df.iloc[indices]
        scores = self._score(frame, similarities[indices], parsed)

        # Stable ordering: score desc, then rating desc, then price asc.
        order = np.lexsort(
            (
                frame["PRICE"].to_numpy(dtype=float),
                -frame["AVG RATING"].to_numpy(dtype=float),
                -scores,
            )
        )[:limit]

        results = [
            self._to_recommendation(frame.iloc[int(position)], float(scores[position]),
                                    float(similarities[indices[position]]))
            for position in order
        ]
        logger.info(
            "engine.recommended query=%r candidates=%d returned=%d top_score=%.3f",
            query_text,
            int(mask.sum()),
            len(results),
            results[0].score if results else 0.0,
        )
        return results, relaxed

    def _to_recommendation(
        self, row: pd.Series, score: float, similarity: float
    ) -> Recommendation:
        attributes = parse_attributes(row.get("DETAILS", ""))
        title = str(row.get("TITLE", "")).strip()
        return Recommendation(
            name=title,
            price=int(row.get("PRICE", 0)),
            rating=float(row.get("AVG RATING", 0.0)),
            score=score,
            similarity=similarity,
            url=(str(row.get("URL", "")).strip() or None),
            search_url=self.settings.flipkart_search_url.format(query=quote_plus(title)),
            ratings_count=int(row.get("RATINGS COUNT", 0)),
            reviews_count=int(row.get("REVIEWS COUNT", 0)),
            return_policy=_clean_policy(row.get("RETURN POLICY", "")),
            attributes=attributes,
            highlights=_highlights(attributes),
        )


def _clean_policy(value: object) -> str | None:
    text = str(value or "").replace(";", " ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    return text or None


def _highlights(attributes: dict[str, str], limit: int = 3) -> list[str]:
    """Pick the most decision-relevant attributes for the results UI."""
    preferred = ("Battery life", "Bluetooth version", "With Mic", "Wireless range",
                 "Charging time", "Connector type")
    chosen: list[str] = []
    for key in preferred:
        for name, value in attributes.items():
            if name.lower() == key.lower() and len(value) <= 60:
                chosen.append("{0}: {1}".format(name, value))
                break
        if len(chosen) >= limit:
            return chosen
    for name, value in attributes.items():
        entry = "{0}: {1}".format(name, value)
        if entry not in chosen and len(value) <= 60:
            chosen.append(entry)
        if len(chosen) >= limit:
            break
    return chosen
