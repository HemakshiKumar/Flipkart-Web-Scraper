"""Data cleaning / feature preparation.

This is the notebook's "Data Cleaning" + "Preparing Data for the TFIDF
Vectorizer" sections, turned into pure functions that operate on a DataFrame.

The transformations are identical in intent to the notebook:

* rows without a price are dropped;
* ``PRICE`` loses its currency symbol and thousands separators and becomes an
  int;
* ``RETURN POLICY`` loses the ``"?;"`` artefact;
* ``REVIEW COUNT`` ("1,234 Ratings & 56 Reviews") is split into
  ``RATINGS COUNT`` / ``REVIEWS COUNT`` ints;
* ``DETAILS`` ("key: value; key: value; ") is flattened and concatenated with
  ``TITLE`` to build the ``DESCRIPTION`` column the TF-IDF vectoriser consumes.

Two defects of the notebook version are fixed here, because they silently
corrupt the corpus:

1. the notebook did ``raw_details[:-2]``, which dropped the last real detail of
   every product (the trailing ``"; "`` separator already produces an empty
   fragment). Empty fragments are now filtered explicitly instead.
2. splitting ``REVIEW COUNT`` used ``list.remove()`` and raised ``ValueError``
   on any product that had ratings but no reviews. A regex now handles both
   shapes and falls back to 0.
"""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

#: The repository ships a CSV whose rating column is called ``RATING`` while
#: the notebook's scraper emits ``AVG RATING``. Both are accepted.
COLUMN_ALIASES = {
    "RATING": "AVG RATING",
    "AVERAGE RATING": "AVG RATING",
    "PRODUCT URL": "URL",
    "LINK": "URL",
}

REQUIRED_COLUMNS = ("TITLE", "PRICE")
OPTIONAL_COLUMNS = ("AVG RATING", "DETAILS", "RETURN POLICY", "REVIEW COUNT", "URL")

_RATINGS_RE = re.compile(r"([\d,]+)\s*Ratings", re.IGNORECASE)
_REVIEWS_RE = re.compile(r"([\d,]+)\s*Reviews", re.IGNORECASE)
_PRICE_RE = re.compile(r"[^\d.]")


class PreprocessingError(ValueError):
    """Raised when a dataset cannot be turned into a usable corpus."""


def _to_int(value: object) -> int:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    digits = _PRICE_RE.sub("", str(value)).split(".")[0]
    return int(digits) if digits else 0


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.strip().upper() for c in df.columns})
    df = df.rename(columns={k: v for k, v in COLUMN_ALIASES.items() if k in df.columns})
    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    return df


def clean_price(df: pd.DataFrame) -> pd.DataFrame:
    """Notebook: dropna(subset=['PRICE']) + strip ``₹`` and ``,`` + astype(int)."""
    df = df.dropna(subset=["PRICE"]).copy()
    df["PRICE"] = df["PRICE"].astype(str).str.strip()
    df = df[df["PRICE"] != ""]
    df["PRICE"] = df["PRICE"].map(_to_int)
    return df[df["PRICE"] > 0].copy()


def clean_rating(df: pd.DataFrame) -> pd.DataFrame:
    df["AVG RATING"] = pd.to_numeric(df["AVG RATING"], errors="coerce").fillna(0.0)
    return df


def clean_return_policy(df: pd.DataFrame) -> pd.DataFrame:
    """Notebook: ``df_new["RETURN POLICY"].str.replace("?;", "")``."""
    df["RETURN POLICY"] = (
        df["RETURN POLICY"].fillna("").astype(str).str.replace("?;", ";", regex=False)
    )
    return df


def split_review_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Notebook: split ``"N Ratings & M Reviews"`` into two integer columns."""
    raw = df["REVIEW COUNT"].fillna("").astype(str)

    def _extract(pattern: re.Pattern[str], text: str) -> int:
        match = pattern.search(text)
        return _to_int(match.group(1)) if match else 0

    df["RATINGS COUNT"] = [_extract(_RATINGS_RE, text) for text in raw]
    df["REVIEWS COUNT"] = [_extract(_REVIEWS_RE, text) for text in raw]
    return df.drop(columns=["REVIEW COUNT"])


def flatten_details(details: object) -> str:
    """Notebook's detail flattening: ``"k: v; k: v; "`` -> ``"k v k v "``."""
    if details is None or (isinstance(details, float) and pd.isna(details)):
        return ""
    parts: list[str] = []
    for fragment in str(details).split(";"):
        fragment = fragment.strip()
        if not fragment:
            continue
        for piece in fragment.split(":"):
            piece = piece.strip()
            if piece:
                parts.append(piece)
    return " ".join(parts)


def build_description(df: pd.DataFrame) -> pd.DataFrame:
    """Notebook: ``DESCRIPTION = TITLE + " " + flattened details``."""
    details_string = df["DETAILS"].map(flatten_details)
    df["DESCRIPTION"] = (
        df["TITLE"].fillna("").astype(str).str.strip() + " " + details_string
    ).str.strip()
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full cleaning pipeline and return the model-ready frame."""
    if df is None or df.empty:
        raise PreprocessingError("Dataset is empty")

    df = normalise_columns(df)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise PreprocessingError(f"Dataset is missing required columns: {missing}")

    before = len(df)
    df = clean_price(df)
    df = clean_rating(df)
    df = clean_return_policy(df)
    df = split_review_counts(df)
    df = build_description(df)
    df = df[df["DESCRIPTION"].str.strip() != ""]
    df = df.drop_duplicates(subset=["TITLE", "PRICE"]).reset_index(drop=True)

    logger.info("preprocess.done rows_in=%d rows_out=%d", before, len(df))
    if df.empty:
        raise PreprocessingError("No usable rows remained after preprocessing")
    return df
