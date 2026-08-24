from __future__ import annotations

import pandas as pd
import pytest

from app.services.preprocessing import (
    PreprocessingError,
    flatten_details,
    preprocess,
)

RAW = pd.DataFrame(
    [
        {
            "TITLE": "Aroma NB120 Neckband Bluetooth",
            "PRICE": "₹399",
            "AVG RATING": "4",
            "DETAILS": "With Mic:Yes; Bluetooth version: v5.3; Battery life: 50 hr; ",
            "RETURN POLICY": "7 Days Replacement Policy?; ",
            "REVIEW COUNT": "1,234 Ratings & 56 Reviews",
            "URL": "https://www.flipkart.com/a/p/itm1",
        },
        {
            "TITLE": "OnePlus Bullets Wireless Z2",
            "PRICE": "₹1,299",
            "AVG RATING": "4.3",
            "DETAILS": "With Mic:Yes; Battery life: 30 Hrs; ",
            "RETURN POLICY": "7 Days Service Center Replacement?; ",
            "REVIEW COUNT": "980 Ratings",
            "URL": "https://www.flipkart.com/b/p/itm2",
        },
        {
            "TITLE": "Broken row without price",
            "PRICE": None,
            "AVG RATING": "5",
            "DETAILS": "",
            "RETURN POLICY": "",
            "REVIEW COUNT": "",
            "URL": "",
        },
    ]
)


def test_preprocess_matches_notebook_cleaning() -> None:
    df = preprocess(RAW.copy())

    assert len(df) == 2  # priceless row dropped
    assert df["PRICE"].tolist() == [399, 1299]
    assert df["PRICE"].dtype.kind == "i"
    assert df["AVG RATING"].tolist() == [4.0, 4.3]
    assert df["RATINGS COUNT"].tolist() == [1234, 980]
    assert df["REVIEWS COUNT"].tolist() == [56, 0]  # "980 Ratings" has no reviews
    assert "REVIEW COUNT" not in df.columns
    assert "?" not in df["RETURN POLICY"].iloc[0]


def test_description_is_title_plus_all_details() -> None:
    df = preprocess(RAW.copy())
    description = df["DESCRIPTION"].iloc[0]
    assert description.startswith("Aroma NB120 Neckband Bluetooth")
    # The notebook's `raw_details[:-2]` dropped the final detail; it is kept now.
    assert "Battery life" in description and "50 hr" in description
    assert "Bluetooth version" in description


def test_flatten_details_drops_empty_fragments() -> None:
    assert flatten_details("A: 1; B: 2; ") == "A 1 B 2"
    assert flatten_details("") == ""
    assert flatten_details(None) == ""


def test_repository_csv_columns_are_accepted() -> None:
    """The committed CSV uses RATING and has no REVIEW COUNT / URL column."""
    legacy = pd.DataFrame(
        [
            {
                "TITLE": "Legacy product",
                "PRICE": "₹450",
                "RATING": "3.9",
                "DETAILS": "Battery life: 48 hr; ",
                "RETURN POLICY": "7 Days Replacement Policy?; ",
            }
        ]
    )
    df = preprocess(legacy)
    assert df["AVG RATING"].tolist() == [3.9]
    assert df["RATINGS COUNT"].tolist() == [0]
    assert df["URL"].tolist() == [""]


def test_empty_dataset_raises() -> None:
    with pytest.raises(PreprocessingError):
        preprocess(pd.DataFrame())
