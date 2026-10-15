"""Generate data/raw/groww_reviews_raw.csv = the clean sample + synthetic PII rows.

The extra rows exist ONLY to demonstrate that PII redaction works. They are
synthetic (fake) and never appear in any deliverable — ingest strips them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402

config.ensure_dirs()

sample = pd.read_csv(config.SAMPLE_REVIEWS)

pii_rows = pd.DataFrame(
    [
        {
            "review_id": 901,
            "date": "2026-10-09",
            "rating": 1,
            "title": "Charged extra, contact me",
            "review_text": "Redeemed and got less money. Please call me on 9876543210 or email rahul.sharma@gmail.com to explain exit load.",
            "source": "Google Play",
            "app_version": "9.0.8",
            "theme_hint": "Charges & Fees",
        },
        {
            "review_id": 902,
            "date": "2026-10-10",
            "rating": 2,
            "title": "Ticket ignored",
            "review_text": "My ticket 4471829361 is still open and no one replies. Handle from @rahul_trades or pay me back at rahul@okhdfcbank. Exit load was deducted.",
            "source": "Google Play",
            "app_version": "9.0.8",
            "theme_hint": "Charges & Fees",
        },
        {
            "review_id": 903,
            "date": "2026-10-11",
            "rating": 1,
            "title": "Confusing charges",
            "review_text": "Visit https://mysite.example.com and see. The redeem screen showed one amount, my account credited less. No fee breakdown anywhere.",
            "source": "App Store",
            "app_version": "9.0.8",
            "theme_hint": "Charges & Fees",
        },
    ]
)

raw = pd.concat([sample, pii_rows], ignore_index=True)
config.RAW_REVIEWS.parent.mkdir(parents=True, exist_ok=True)
raw.to_csv(config.RAW_REVIEWS, index=False)
print(f"wrote {config.RAW_REVIEWS} ({len(raw)} rows, {len(pii_rows)} with synthetic PII)")
