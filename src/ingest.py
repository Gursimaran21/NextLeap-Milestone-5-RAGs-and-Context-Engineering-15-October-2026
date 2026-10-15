"""Step 0 — Load recent public reviews, filter to the window, redact PII.

Input columns expected: review_id, date, rating, title, review_text, source, app_version
(extra columns like `theme_hint` are tolerated and ignored for the analysis).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config
from .pii import contains_pii, redact_pii_counted

REQUIRED = ["date", "rating", "title", "review_text"]


def _resolve_input(path: str | Path | None = None) -> Path:
    if path:
        return Path(path)
    if config.RAW_REVIEWS.exists():
        return config.RAW_REVIEWS
    return config.SAMPLE_REVIEWS


def load_reviews(path: str | Path | None = None, weeks: int = config.WEEKS) -> pd.DataFrame:
    """Return a cleaned, PII-redacted, windowed dataframe."""
    src = _resolve_input(path)
    if not src.exists():
        raise FileNotFoundError(
            f"Reviews CSV not found at {src}. Add one to data/ or pass a path."
        )

    df = pd.read_csv(src)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"{src.name} is missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    # Window relative to the latest review in the export (reproducible for a fixed CSV).
    anchor = df["date"].max()
    cutoff = anchor - pd.Timedelta(weeks=weeks)
    before = len(df)
    df = df[df["date"] >= cutoff].copy()

    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"]).copy()

    df["title"] = df["title"].fillna("").astype(str)
    df["review_text"] = df["review_text"].fillna("").astype(str)

    # ---- PII redaction (before anything else) ----
    redactions = 0
    clean_texts: list[str] = []
    for _, row in df.iterrows():
        merged = f"{row['title']} {row['review_text']}".strip()
        merged, n = redact_pii_counted(merged)
        redactions += n
        clean_texts.append(merged)
    df["clean_text"] = clean_texts

    # drop noise
    df = df[df["clean_text"].str.len() >= 15].copy()
    df = df.drop_duplicates(subset=["clean_text"]).reset_index(drop=True)

    df.attrs["rows_loaded"] = before
    df.attrs["redactions"] = redactions
    df.attrs["anchor"] = anchor.date().isoformat()
    df.attrs["window_start"] = cutoff.date().isoformat()
    df.attrs["source_file"] = src.name

    # final safety gate
    assert not df["clean_text"].map(contains_pii).any(), "PII survived redaction!"

    return df


def run(path: str | Path | None = None, weeks: int = config.WEEKS) -> pd.DataFrame:
    config.ensure_dirs()
    df = load_reviews(path, weeks)
    out = config.PROCESSED_DIR / "reviews_clean.csv"
    # Persist ONLY the PII-redacted text. The raw `title`/`review_text` columns may
    # still contain PII and this CSV is committed — never write them to disk.
    safe = df.drop(columns=[c for c in ("title", "review_text") if c in df.columns])
    safe.to_csv(out, index=False)
    print(
        f"[ingest] {df.attrs['source_file']}: loaded {df.attrs['rows_loaded']} rows -> "
        f"{len(df)} kept | window {df.attrs['window_start']} .. {df.attrs['anchor']} | "
        f"PII redactions: {df.attrs['redactions']} | saved {out}"
    )
    return df


if __name__ == "__main__":
    run()
