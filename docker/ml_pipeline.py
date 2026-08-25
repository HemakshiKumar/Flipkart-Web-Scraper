"""Standalone Machine Learning Model Pipeline.

Reproduces the TF-IDF vectorization, cleaning, and cosine similarity ranking
pipeline from `web-scraping-project/code file.ipynb`.

Usage:
    python ml_pipeline.py "Bluetooth neckband with mic and 50-hour playback under 1000" --top-n 5
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ml_model")


def load_and_preprocess_dataset(csv_path: Path) -> pd.DataFrame:
    """Load dataset and perform the cleaning steps from the notebook."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    logger.info("Loading dataset from: %s", csv_path)
    df = pd.read_csv(csv_path)

    # 1. Drop missing prices
    df_clean = df.dropna(subset=["PRICE"]).copy()

    # 2. Clean PRICE column
    df_clean["PRICE"] = (
        df_clean["PRICE"]
        .astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df_clean["PRICE"] = pd.to_numeric(df_clean["PRICE"], errors="coerce").fillna(0).astype(int)

    # 3. Clean RETURN POLICY
    if "RETURN POLICY" in df_clean.columns:
        df_clean["RETURN POLICY"] = df_clean["RETURN POLICY"].astype(str).str.replace("?;", "", regex=False).str.strip()

    # 4. Clean and convert AVG RATING
    if "AVG RATING" in df_clean.columns:
        df_clean["AVG RATING"] = pd.to_numeric(df_clean["AVG RATING"], errors="coerce").fillna(0.0)

    # 5. Build DESCRIPTION column for TF-IDF
    details_strings: list[str] = []
    for raw_details in df_clean["DETAILS"].fillna("").astype(str):
        parts = [p.strip().replace(":", " ") for p in raw_details.split(";") if p.strip()]
        details_strings.append(" ".join(parts))

    descriptions = [
        f"{title} {detail}".strip()
        for title, detail in zip(df_clean["TITLE"].fillna(""), details_strings)
    ]
    df_clean["DESCRIPTION"] = descriptions

    logger.info("Preprocessed %d product rows ready for TF-IDF vectorization.", len(df_clean))
    return df_clean


class RecommendationModel:
    """TF-IDF + Cosine Similarity Recommendation Model."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df.reset_index(drop=True)
        self.vectorizer = TfidfVectorizer(stop_words="english")
        logger.info("Fitting TF-IDF vectorizer on product descriptions...")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.df["DESCRIPTION"])
        logger.info("TF-IDF matrix vocabulary size: %d features.", self.tfidf_matrix.shape[1])

    def recommend(self, query: str, top_n: int = 5) -> pd.DataFrame:
        """Score query against product matrix using cosine similarity."""
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        top_indices = similarities.argsort()[-top_n:][::-1]
        results = self.df.iloc[top_indices].copy()
        results["SIMILARITY_SCORE"] = similarities[top_indices]

        output_cols = [col for col in ["TITLE", "PRICE", "AVG RATING", "SIMILARITY_SCORE", "RETURN POLICY"] if col in results.columns]
        return results[output_cols]


def main() -> None:
    parser = argparse.ArgumentParser(description="Flipkart ML Recommendation Model Runner")
    parser.add_argument("query", nargs="?", default="Bluetooth neckband with mic and 50-hour playback under 1000", help="User search query")
    parser.add_argument("--dataset", type=str, default="flipkart_data.csv", help="Path to flipkart_data.csv")
    parser.add_argument("--top-n", type=int, default=5, help="Number of recommendations to return")

    args = parser.parse_args()

    # Search for dataset path
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        fallback_candidates = [
            Path("/workspace/web-scraping-project/flipkart_data.csv"),
            Path("web-scraping-project/flipkart_data.csv"),
            Path("../web-scraping-project/flipkart_data.csv"),
            Path("flipkart_data.csv"),
        ]
        for candidate in fallback_candidates:
            if candidate.exists():
                dataset_path = candidate
                break

    try:
        df = load_and_preprocess_dataset(dataset_path)
        model = RecommendationModel(df)
        print(f"\n{'='*80}\nQuery: \"{args.query}\"\n{'='*80}")
        recommendations = model.recommend(args.query, top_n=args.top_n)
        print(recommendations.to_string(index=False))
        print(f"{'='*80}\n")
    except Exception as exc:
        logger.error("Error executing ML recommendation pipeline: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
