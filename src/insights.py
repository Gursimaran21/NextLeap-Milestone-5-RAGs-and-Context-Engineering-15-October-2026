"""Step 1b — Insight extraction: top themes, real quotes, and the fee pain point."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from . import config
from .pii import contains_pii


def _quote_score(row: pd.Series) -> float:
    """Prefer reviews that are specific, moderate length, and emotional (extreme ratings)."""
    text = str(row["clean_text"])
    length_score = 1.0 if 60 <= len(text) <= 190 else 0.4
    rating = float(row["rating"])
    emotion = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.7, 5: 0.6}.get(int(rating), 0.5)
    specificity = sum(text.lower().count(k) for k in ["exit load", "charge", "sip", "kyc", "withdraw", "statement"]) * 0.15
    return length_score + emotion + specificity


def _clip(text: str, limit: int = 180) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0] + "…"


def _pick_quotes(df: pd.DataFrame, n: int = config.TOP_QUOTES) -> list[dict]:
    ranked = df.assign(_s=df.apply(_quote_score, axis=1)).sort_values("_s", ascending=False)
    quotes: list[dict] = []
    seen_themes: set[str] = set()
    for _, row in ranked.iterrows():
        text = _clip(str(row["clean_text"]))
        if contains_pii(text):
            continue
        theme = str(row["theme"])
        if theme in seen_themes and len(quotes) < n - 1:
            continue  # spread quotes across themes when possible
        quotes.append(
            {
                "text": text,
                "rating": int(row["rating"]),
                "date": pd.to_datetime(row["date"]).date().isoformat(),
                "week": pd.to_datetime(row["date"]).strftime("%b %d"),
                "theme": theme,
            }
        )
        seen_themes.add(theme)
        if len(quotes) == n:
            break
    return quotes


def detect_fee_issue(df: pd.DataFrame) -> dict:
    """Find the most-mentioned specific fee term, then pull evidence snippets."""
    blob = df["clean_text"].str.lower()

    counts = {term: int(blob.str.contains(term, regex=False).sum()) for term in config.FEE_TERMS}
    label_term = max(counts, key=lambda t: counts[t]) if counts else ""
    if counts.get(label_term, 0) == 0:
        # fall back to broader "confusion" keywords
        for kw in config.FEE_ISSUE_KEYWORDS:
            if blob.str.contains(kw, regex=False).any():
                label_term = "exit load"
                break

    label = config.FEE_ISSUE_LABELS.get(label_term, config.FEE_ISSUE_LABEL)

    mask = pd.Series(False, index=df.index)
    for kw in config.FEE_ISSUE_KEYWORDS:
        mask = mask | blob.str.contains(kw, regex=False)
    if label_term:
        mask = mask | blob.str.contains(label_term, regex=False)
    evidence = df[mask]

    matched = [k for k in config.FEE_ISSUE_KEYWORDS if blob.str.contains(k, regex=False).any()]

    snippets: list[str] = []
    for _, row in evidence.iterrows():
        s = _clip(str(row["clean_text"]), 140)
        if not contains_pii(s) and s not in snippets:
            snippets.append(s)
        if len(snippets) == 3:
            break

    return {
        "label": label,
        "term": label_term,
        "evidence_count": int(len(evidence)),
        "matched_keywords": matched,
        "sample_snippets": snippets,
    }


def build_insights(df: pd.DataFrame, weeks: int = config.WEEKS) -> dict:
    total = len(df)
    dist = df["theme"].value_counts()
    theme_distribution = [
        {"theme": t, "count": int(c), "share_pct": round(100 * c / total, 1)}
        for t, c in dist.items()
    ]
    top_themes = [d["theme"] for d in theme_distribution[: config.TOP_THEMES]]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_weeks": weeks,
        "window_start": df.attrs.get("window_start"),
        "window_end": df.attrs.get("anchor"),
        "total_reviews": total,
        "avg_rating": round(float(df["rating"].mean()), 2),
        "source_file": df.attrs.get("source_file"),
        "theme_distribution": theme_distribution,
        "top_themes": top_themes,
        "top_quotes": _pick_quotes(df),
        "fee_issue": detect_fee_issue(df),
    }


def run(df: pd.DataFrame, weeks: int = config.WEEKS) -> dict:
    config.ensure_dirs()
    insights = build_insights(df, weeks)
    config.INSIGHTS_JSON.write_text(json.dumps(insights, indent=2), encoding="utf-8")
    print(
        f"[insights] top themes: {', '.join(insights['top_themes'])} | "
        f"fee issue: {insights['fee_issue']['label']} "
        f"({insights['fee_issue']['evidence_count']} reviews) -> {config.INSIGHTS_JSON}"
    )
    return insights


def load_insights() -> dict:
    return json.loads(config.INSIGHTS_JSON.read_text(encoding="utf-8"))


if __name__ == "__main__":
    from .cluster import cluster
    from .ingest import load_reviews

    run(cluster(load_reviews()))
