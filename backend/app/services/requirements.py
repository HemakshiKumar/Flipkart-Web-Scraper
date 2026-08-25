"""Deterministic natural-language requirements parser.

The existing engine ranks products by TF-IDF similarity against a free-text
query, which handles *descriptive* requirements ("good sound quality") well but
cannot express *constraints* ("under 5000", ">4.5 rating") - a numeral in a
TF-IDF query is just another token.

This layer closes that gap without introducing an LLM dependency: the user's
sentence is parsed with regular expressions into

* numeric filters (rating / price bounds),
* extra query terms fed to the existing vectoriser (synonym expansion, so
  "battery life" also matches "50 hr playtime"),
* ranking weight adjustments ("cheap", "highly rated",
  "battery is more important than price").

Everything is rule-based and therefore reproducible: the same sentence always
produces the same filters.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

RUPEE = "₹"

# --------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------
#: Feature phrase -> extra terms appended to the TF-IDF query. The expansions
#: use vocabulary that actually appears in the scraped DETAILS column
#: (e.g. "Battery life: 50 hr | Charging time: 1.5 Hours").
FEATURE_SYNONYMS: dict[str, str] = {
    "battery life": "battery life playtime playback hours hr charge",
    "battery": "battery life playtime playback hours hr",
    "long battery": "battery life playtime hours hr long",
    "playback": "playback playtime battery hours hr",
    "playtime": "playtime playback battery hours hr",
    "fast charging": "fast charging charge time quick",
    "sound quality": "sound audio quality bass driver stereo",
    "sound": "sound audio bass driver",
    "audio": "audio sound driver stereo",
    "bass": "bass deep audio sound driver",
    "noise cancellation": "noise cancellation anc active",
    "noise cancelling": "noise cancellation anc active",
    "anc": "noise cancellation anc active",
    "wireless": "wireless bluetooth",
    "bluetooth": "bluetooth wireless version",
    "wired": "wired connector cable",
    "mic": "mic microphone calling",
    "microphone": "mic microphone calling",
    "calling": "mic microphone calling clear",
    "waterproof": "waterproof water resistant ipx sweat",
    "water resistant": "water resistant ipx sweat proof",
    "sweatproof": "sweat proof ipx water resistant",
    "gaming": "gaming low latency mode",
    "low latency": "low latency gaming mode ms",
    "comfortable": "comfortable lightweight ear fit",
    "lightweight": "lightweight light weight comfortable",
    "durable": "durable build quality",
    "warranty": "warranty months replacement",
    "range": "wireless range meters",
    "dual pairing": "dual pairing multipoint connect",
}

#: Words that only express a constraint - they are not useful search terms.
STOP_PHRASES = {
    "i", "want", "need", "looking", "for", "with", "at", "least", "more",
    "than", "less", "under", "below", "above", "over", "around", "about",
    "rating", "rated", "star", "stars", "rs", "inr", "price", "priced",
    "cost", "budget", "and", "or", "the", "a", "an", "is", "should", "be",
    "something", "anything", "good", "best", "top", "high", "low", "cheap",
    "expensive", "important", "prefer", "preferably", "must", "have", "has",
}

_NUMBER = r"(?:" + RUPEE + r"|rs\.?|inr)?\s*([\d][\d,]*(?:\.\d+)?)\s*(k|thousand)?"

_RATING_MIN_PATTERNS = [
    re.compile(
        r"(?:>=|>|above|over|at\s*least|min(?:imum)?|more\s+than)\s*"
        r"(\d(?:\.\d+)?)\s*\+?\s*(?:star|stars|rating|rated)?",
        re.I,
    ),
    re.compile(r"(\d(?:\.\d+)?)\s*\+\s*(?:star|stars|rating|rated)", re.I),
    re.compile(
        r"(\d(?:\.\d+)?)\s*(?:star|stars)\s*(?:rating|rated|and\s+above|or\s+above|\+)?",
        re.I,
    ),
    re.compile(r"rating\s*(?:of\s*)?(?:>=|>|above|over|at\s*least)?\s*(\d(?:\.\d+)?)", re.I),
]
_RATING_MAX_PATTERN = re.compile(
    r"(?:<=|<|under|below|less\s+than)\s*(\d(?:\.\d+)?)\s*(?:star|stars|rating|rated)",
    re.I,
)
_PRICE_MAX_PATTERN = re.compile(
    r"(?:under|below|less\s+than|cheaper\s+than|max(?:imum)?|upto|up\s+to|within|<=|<|no\s+more\s+than)\s*"
    + _NUMBER,
    re.I,
)
_PRICE_MIN_PATTERN = re.compile(
    r"(?:above|over|more\s+than|at\s*least|min(?:imum)?|starting\s+(?:from|at)|>=|>)\s*" + _NUMBER,
    re.I,
)
_PRICE_RANGE_PATTERN = re.compile(
    r"between\s*" + _NUMBER + r"\s*(?:and|to|-)\s*" + _NUMBER, re.I
)
_PRIORITY_PATTERN = re.compile(
    r"([\w\s]{2,40}?)\s+(?:is|are)?\s*more\s+important\s+than\s+([\w\s]{2,40})", re.I
)

_CHEAP_WORDS = re.compile(
    r"\b(cheap|cheapest|budget|affordable|value\s+for\s+money|low\s+price|inexpensive)\b", re.I
)
_PREMIUM_WORDS = re.compile(r"\b(premium|flagship|high\s*end|best\s+quality)\b", re.I)
_HIGH_RATED_WORDS = re.compile(
    r"\b(high(?:ly)?\s*rated|well\s*rated|top\s*rated|best\s*rated|good\s*rating|highest\s+rating)\b",
    re.I,
)
_POPULAR_WORDS = re.compile(
    r"\b(popular|most\s+reviewed|bestseller|best\s*selling|trusted|many\s+reviews)\b", re.I
)
_PRICE_LOSER = re.compile(r"\b(price|cost|budget)\b", re.I)
_RATING_LOSER = re.compile(r"\b(rating|review|reviews)\b", re.I)

#: Ratings live on a 0-5 scale; anything larger in a numeric slot is a price.
MAX_RATING = 5.0


@dataclass(slots=True)
class ParsedRequirements:
    """Structured view of the user's free-text requirements."""

    raw: str = ""
    min_rating: float | None = None
    max_rating: float | None = None
    min_price: int | None = None
    max_price: int | None = None
    prefer_cheap: bool = False
    prefer_popular: bool = False
    boosted_features: list[str] = field(default_factory=list)
    query_terms: list[str] = field(default_factory=list)
    weight_overrides: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def has_filters(self) -> bool:
        return any(
            value is not None
            for value in (self.min_rating, self.max_rating, self.min_price, self.max_price)
        )

    def query_text(self) -> str:
        return " ".join(self.query_terms)

    def to_dict(self) -> dict[str, object]:
        return {
            "minRating": self.min_rating,
            "maxRating": self.max_rating,
            "minPrice": self.min_price,
            "maxPrice": self.max_price,
            "preferCheap": self.prefer_cheap,
            "preferPopular": self.prefer_popular,
            "boostedFeatures": self.boosted_features,
            "notes": self.notes,
        }


def _to_amount(number: str, suffix: str | None) -> int:
    value = float(number.replace(",", ""))
    if suffix and suffix.lower() in {"k", "thousand"}:
        value *= 1000
    return int(round(value))


_RATING_SUFFIX = re.compile(r"^\s*(?:\+\s*)?(?:star|stars|rating|rated)", re.I)
_RATING_PREFIX = re.compile(r"(?:rating|rated|star|stars)\s*(?:of)?\s*$", re.I)


def _looks_like_rating(text: str, match: re.Match[str], amount: int) -> bool:
    """Decide whether a number belongs to the rating axis or the price axis.

    Anything above the 0-5 rating scale is unambiguously a price. Below that,
    only the words immediately around the number decide - a wider window would
    misread "under 3000 with at least 4 star rating" as a rating bound.
    """
    if amount > MAX_RATING:
        return False
    after = text[match.end() : match.end() + 14]
    before = text[max(0, match.start() - 14) : match.start()]
    return bool(_RATING_SUFFIX.match(after) or _RATING_PREFIX.search(before))


def _extract_features(text: str) -> tuple[list[str], list[str]]:
    """Return (matched feature phrases, expansion terms)."""
    lowered = text.lower()
    matched: list[str] = []
    expansions: list[str] = []
    for phrase, expansion in FEATURE_SYNONYMS.items():
        if not re.search(r"\b" + re.escape(phrase) + r"\b", lowered):
            continue
        # Keep the most specific phrase of an overlapping pair
        # ("battery life" wins over "battery").
        if any(phrase != other and phrase in other for other in matched):
            continue
        matched = [other for other in matched if other not in phrase]
        matched.append(phrase)
        expansions.extend(expansion.split())
    return matched, expansions


def _residual_terms(text: str) -> list[str]:
    """Words the user typed that are neither numbers nor constraint words."""
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]+", text.lower())
    return [word for word in words if word not in STOP_PHRASES and len(word) > 2]


def parse_requirements(raw: str, product_query: str = "") -> ParsedRequirements:
    """Turn free-text requirements into filters, query terms and weights."""
    parsed = ParsedRequirements(raw=raw or "")
    text = (raw or "").strip()

    if text:
        _parse_rating(text, parsed)
        _parse_price(text, parsed)
        _parse_preferences(text, parsed)

    features, expansions = _extract_features(text) if text else ([], [])
    parsed.boosted_features = features

    # The TF-IDF query keeps the product query first (it carries the category
    # signal), then the user's own words, then the synonym expansions.
    terms = _residual_terms(product_query) + _residual_terms(text) + expansions
    _apply_priority(text, parsed, terms)
    parsed.query_terms = terms or _residual_terms(product_query)

    logger.info(
        "requirements.parsed raw=%r min_rating=%s max_price=%s features=%s",
        raw,
        parsed.min_rating,
        parsed.max_price,
        features,
    )
    return parsed


def _parse_rating(text: str, parsed: ParsedRequirements) -> None:
    for pattern in _RATING_MIN_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        value = float(match.group(1))
        if not 0 < value <= MAX_RATING:
            continue
        if value >= MAX_RATING and re.search(r">\s*5|above\s*5|over\s*5", text, re.I):
            # ">5 rating" is unsatisfiable on a 0-5 scale.
            parsed.min_rating = 4.5
            parsed.notes.append("No product is rated above 5 - using rating >= 4.5")
        else:
            parsed.min_rating = value
        break

    match = _RATING_MAX_PATTERN.search(text)
    if match:
        value = float(match.group(1))
        if 0 < value <= MAX_RATING:
            parsed.max_rating = value

    if parsed.min_rating is None and _HIGH_RATED_WORDS.search(text):
        parsed.min_rating = 4.0
        parsed.notes.append("Interpreted 'highly rated' as rating >= 4.0")

    if parsed.min_rating is not None:
        parsed.weight_overrides["rating"] = 0.28
        if not any(note.startswith("No product") for note in parsed.notes):
            parsed.notes.append("Rating >= {0:g}".format(parsed.min_rating))
    if parsed.max_rating is not None:
        parsed.notes.append("Rating <= {0:g}".format(parsed.max_rating))


def _parse_price(text: str, parsed: ParsedRequirements) -> None:
    range_match = _PRICE_RANGE_PATTERN.search(text)
    if range_match:
        low = _to_amount(range_match.group(1), range_match.group(2))
        high = _to_amount(range_match.group(3), range_match.group(4))
        parsed.min_price, parsed.max_price = min(low, high), max(low, high)
    else:
        match = _PRICE_MAX_PATTERN.search(text)
        if match:
            amount = _to_amount(match.group(1), match.group(2))
            if not _looks_like_rating(text, match, amount) and amount > MAX_RATING:
                parsed.max_price = amount
        match = _PRICE_MIN_PATTERN.search(text)
        if match:
            amount = _to_amount(match.group(1), match.group(2))
            if not _looks_like_rating(text, match, amount) and amount > MAX_RATING:
                parsed.min_price = amount

    if parsed.max_price is not None:
        parsed.notes.append("Price <= {0}{1:,}".format(RUPEE, parsed.max_price))
    if parsed.min_price is not None:
        parsed.notes.append("Price >= {0}{1:,}".format(RUPEE, parsed.min_price))


def _parse_preferences(text: str, parsed: ParsedRequirements) -> None:
    if _CHEAP_WORDS.search(text):
        parsed.prefer_cheap = True
        parsed.weight_overrides["price"] = 0.18
        parsed.notes.append("Cheaper products ranked higher")
    if _PREMIUM_WORDS.search(text):
        parsed.prefer_cheap = False
        parsed.weight_overrides.pop("price", None)
        parsed.notes.append("Premium products preferred")
    if _POPULAR_WORDS.search(text):
        parsed.prefer_popular = True
        parsed.weight_overrides["popularity"] = 0.20
        parsed.notes.append("Well-reviewed products ranked higher")


def _apply_priority(text: str, parsed: ParsedRequirements, terms: list[str]) -> None:
    """Handle "X is more important than Y" by re-weighting X's terms."""
    match = _PRIORITY_PATTERN.search(text)
    if not match:
        return
    winner, loser = match.group(1).strip(), match.group(2).strip()
    _, winner_terms = _extract_features(winner)
    winner_terms = winner_terms or _residual_terms(winner)
    # Repeating the terms raises their term frequency in the query vector, so
    # the existing vectoriser honours the emphasis with no changes.
    terms.extend(winner_terms * 2)
    parsed.notes.append("'{0}' weighted above '{1}'".format(winner, loser))
    if _PRICE_LOSER.search(loser):
        parsed.prefer_cheap = False
        parsed.weight_overrides["price"] = 0.05
    if _RATING_LOSER.search(loser):
        parsed.weight_overrides["rating"] = 0.10
