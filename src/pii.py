"""PII redaction. Runs BEFORE any analysis, so no PII ever reaches the LLM,
the outputs, the doc entry, or the email draft.

Deliverable rule: no usernames / emails / IDs in any artifact.
"""

from __future__ import annotations

import re

REDACTED = "[REDACTED]"

_PATTERNS: list[re.Pattern[str]] = [
    # email
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    # URL
    re.compile(r"https?://\S+|www\.\S+"),
    # @handle
    re.compile(r"(?<!\w)@[A-Za-z0-9_.]{2,}"),
    # +91 phone / 10-digit phone / spaced phone
    re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)(?:\+?\d{1,3}[-\s]?)?\d{3}[-\s]\d{3}[-\s]\d{4}(?!\d)"),
    # UPI id (name@bank)
    re.compile(r"\b[\w.-]{2,}@(?:ok\w+|ybl|paytm|apl|upi|ibl|axl|sbi|hdfcbank|icici)\b", re.I),
    # long numeric IDs (>= 8 digits): order ids, client ids, ticket ids
    re.compile(r"(?<!\d)\d{8,}(?!\d)"),
]


def redact_pii(text: str) -> str:
    """Return text with PII replaced by [REDACTED]."""
    return redact_pii_counted(text)[0]


def redact_pii_counted(text: str) -> tuple[str, int]:
    """Return (redacted_text, number_of_replacements)."""
    if not isinstance(text, str) or not text:
        return text, 0
    cleaned = text
    hits = 0
    for pat in _PATTERNS:
        cleaned, n = pat.subn(REDACTED, cleaned)
        hits += n
    # collapse accidental duplicates like [REDACTED] [REDACTED]
    cleaned = re.sub(r"(?:\[REDACTED\]\s*){2,}", f"{REDACTED} ", cleaned).strip()
    return cleaned, hits


def contains_pii(text: str) -> bool:
    """True if any PII pattern still matches (used as a final QA gate)."""
    if not isinstance(text, str):
        return False
    return any(pat.search(text) for pat in _PATTERNS)


if __name__ == "__main__":
    demo = "Mail me at rahul.sharma@gmail.com or call 9876543210, my UPI is rahul@okhdfcbank, order #123456789, handle @rahul_trades"
    out, n = redact_pii_counted(demo)
    print("in :", demo)
    print("out:", out)
    print("redactions:", n)
    assert not contains_pii(out), "PII still present!"
    print("OK — no PII remains.")
