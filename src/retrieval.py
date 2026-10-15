"""RAG retrieval layer — fetch the *context* that grounds the generated text.

This is the "context engineering" part: we never ask the LLM to invent a fee issue.
We retrieve the exact reviews that mention the detected fee, rank them by relevance
to the question, and pass them as the only factual context.
"""

from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import config


def retrieve_context(
    df: pd.DataFrame,
    query: str,
    k: int = 6,
    must_match: list[str] | None = None,
) -> list[dict]:
    """Return the top-k most relevant reviews for `query`.

    must_match: if given, only reviews containing at least one of these substrings
    are eligible (keeps the retrieved context on-topic for the fee issue).
    """
    pool = df
    if must_match:
        mask = pd.Series(False, index=df.index)
        low = df["clean_text"].str.lower()
        for term in must_match:
            mask = mask | low.str.contains(term, regex=False)
        filtered = df[mask]
        if len(filtered) >= 1:
            pool = filtered

    if pool.empty:
        pool = df

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vec.fit_transform(pool["clean_text"].tolist())
    q_vec = vec.transform([query])
    sims = cosine_similarity(q_vec, matrix).ravel()

    order = sims.argsort()[::-1][:k]
    out: list[dict] = []
    for idx in order:
        row = pool.iloc[idx]
        out.append(
            {
                "text": str(row["clean_text"]),
                "rating": int(row["rating"]),
                "date": pd.to_datetime(row["date"]).date().isoformat(),
                "theme": str(row["theme"]),
                "relevance": round(float(sims[idx]), 3),
            }
        )
    return out


def run(df: pd.DataFrame, fee_label: str) -> list[dict]:
    query = f"users confused about {fee_label} charges deductions on redemption"
    ctx = retrieve_context(df, query, k=6, must_match=["exit load", "charge", "charged", "deducted", "less"])
    print(f"[retrieval] retrieved {len(ctx)} context reviews for '{fee_label}'")
    return ctx


if __name__ == "__main__":
    from .cluster import cluster
    from .ingest import load_reviews

    run(cluster(load_reviews()), config.FEE_ISSUE_LABEL)
