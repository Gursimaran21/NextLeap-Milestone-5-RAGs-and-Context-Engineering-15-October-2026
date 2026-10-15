"""Step 1a — Cluster reviews into <=5 themes (explainable hybrid).

How it works:
  1. Label every review with the theme whose keywords it matches most strongly.
  2. TF-IDF + KMeans groups the reviews statistically (this is the "clustering").
  3. Each KMeans cluster is mapped to the majority review theme, with a greedy
     pass so two clusters do not claim the same theme while another is free.

Result: genuine clustering + a label that always comes from the fixed 5-theme
legend, so a theme is NEVER left unlabeled.
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from . import config

NONE = "__none__"


def _review_theme(text: str) -> str:
    """Keyword score -> best theme for one review. Phrases count more than words."""
    low = text.lower()
    scores: dict[str, float] = {}
    for theme, kws in config.THEME_KEYWORDS.items():
        s = 0.0
        for kw in kws:
            hits = low.count(kw)
            if hits:
                s += hits * (1.6 if " " in kw else 1.0)
        scores[theme] = s
    if max(scores.values(), default=0) == 0:
        return NONE
    return max(scores, key=lambda t: scores[t])


def _label_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["review_theme"] = df["clean_text"].map(_review_theme)
    return df


def cluster(df: pd.DataFrame, k: int = config.MAX_THEMES) -> pd.DataFrame:
    if df.empty:
        raise ValueError("No reviews to cluster.")

    df = _label_reviews(df)
    k = max(1, min(k, len(df), config.MAX_THEMES))

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    X = vec.fit_transform(df["clean_text"])
    terms = vec.get_feature_names_out()

    km = KMeans(n_clusters=k, random_state=config.RANDOM_STATE, n_init=10)
    df["cluster_id"] = km.fit_predict(X)

    cluster_terms: dict[int, list[str]] = {}
    for cid in range(k):
        top_idx = km.cluster_centers_[cid].argsort()[::-1][:8]
        cluster_terms[cid] = [terms[i] for i in top_idx]

    # ---- vote: which review-level theme dominates each cluster? ----
    ranked_votes: list[tuple[int, list[str], int]] = []
    for cid in range(k):
        votes = df.loc[(df["cluster_id"] == cid) & (df["review_theme"] != NONE), "review_theme"]
        counts = votes.value_counts()
        top_count = int(counts.iloc[0]) if len(counts) else 0
        # fall back to keyword evidence over the whole cluster if nobody voted
        if not len(counts):
            blob = " ".join(df.loc[df["cluster_id"] == cid, "clean_text"]).lower()
            fallback = _review_theme(blob)
            order = [fallback if fallback != NONE else config.THEMES[0]]
        else:
            order = list(counts.index)
        # always keep the fixed legend as a tail so we can resolve collisions
        order += [t for t in config.THEMES if t not in order]
        ranked_votes.append((cid, order, top_count))

    # ---- greedy: strongest cluster picks first, no duplicate themes while possible ----
    ranked_votes.sort(key=lambda t: t[2], reverse=True)
    assigned: dict[int, str] = {}
    taken: dict[str, int] = {}
    for cid, order, _ in ranked_votes:
        choice = next((t for t in order if t not in taken), order[0])
        assigned[cid] = choice
        taken[choice] = cid

    df["theme"] = df["cluster_id"].map(assigned)
    df["cluster_terms"] = df["cluster_id"].map(lambda c: ", ".join(cluster_terms[c][:5]))

    # Per-review label is the accurate signal: keep the cluster mapping as
    # `cluster_theme` (the statistical grouping) but label each review by the
    # theme it actually matches. Reviews with no keyword signal inherit their
    # cluster's theme.
    df["cluster_theme"] = df["theme"]
    df["theme"] = df.apply(
        lambda r: r["cluster_theme"] if r["review_theme"] == NONE else r["review_theme"],
        axis=1,
    )
    return df


def run(df: pd.DataFrame) -> pd.DataFrame:
    config.ensure_dirs()
    out_df = cluster(df)
    out_df.to_csv(config.REVIEWS_THEMED, index=False)

    dist = out_df["theme"].value_counts()
    total = len(out_df)
    print(f"[cluster] {len(dist)} themes from {total} reviews -> saved {config.REVIEWS_THEMED}")
    for theme, count in dist.items():
        print(f"          {theme:<28} {count:>3}  ({count / total:.0%})")
    return out_df


if __name__ == "__main__":
    from .ingest import load_reviews

    run(load_reviews())
