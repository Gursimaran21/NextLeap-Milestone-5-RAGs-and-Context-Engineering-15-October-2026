"""Central config + constants. No secrets here — see .env.example."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = ROOT / "outputs"
DOCS_DIR = ROOT / "docs"
MCP_DIR = ROOT / "mcp"

# Input: prefer a raw export if present (may contain PII -> gets redacted),
# otherwise fall back to the clean public sample.
RAW_REVIEWS = RAW_DIR / "groww_reviews_raw.csv"
SAMPLE_REVIEWS = DATA_DIR / "groww_reviews_sample.csv"

REVIEWS_THEMED = PROCESSED_DIR / "reviews_themed.csv"
INSIGHTS_JSON = OUTPUTS_DIR / "insights.json"
PULSE_MD = OUTPUTS_DIR / "weekly_pulse.md"
PULSE_JSON = OUTPUTS_DIR / "weekly_pulse.json"
EXPLAINER_MD = OUTPUTS_DIR / "fee_explainer.md"
EXPLAINER_JSON = OUTPUTS_DIR / "fee_explainer.json"
NOTES_JSON = OUTPUTS_DIR / "notes_log.json"
NOTES_MD = OUTPUTS_DIR / "notes_doc.md"
EMAIL_EML = OUTPUTS_DIR / "email_draft.eml"
EMAIL_MD = OUTPUTS_DIR / "email_draft.md"
APPROVAL_LOG = MCP_DIR / "approval_log.jsonl"

# ---------------------------------------------------------------- rules
WEEKS = 12                 # look-back window
MAX_THEMES = 5             # hard cap from the brief
MAX_PULSE_WORDS = 250      # hard cap from the brief
MAX_EXPLAINER_BULLETS = 6  # hard cap from the brief
TOP_THEMES = 3             # highlight top N
TOP_QUOTES = 3             # exactly N quotes
RANDOM_STATE = 42

# ---------------------------------------------------------------- themes
THEMES: list[str] = [
    "Onboarding & KYC",
    "Payments & SIP",
    "Charges & Fees",
    "Withdrawals & Redemption",
    "Statements & Reports",
]

THEME_MEANINGS: dict[str, str] = {
    "Onboarding & KYC": "signup, KYC verification, PAN/nominee friction",
    "Payments & SIP": "SIP execution, mandates, failed/refunded payments",
    "Charges & Fees": "brokerage, exit load, DP charges, AMC, deductions",
    "Withdrawals & Redemption": "money out, payout timelines, missing status",
    "Statements & Reports": "statements, capital gains, report downloads",
}

# Keyword evidence per theme (used for cluster -> theme mapping + fallback).
THEME_KEYWORDS: dict[str, list[str]] = {
    "Onboarding & KYC": [
        "kyc", "verification", "verify", "aadhaar", "aadhar", "pan", "nominee",
        "onboarding", "sign up", "signup", "account opening", "document", "re-verification",
    ],
    "Payments & SIP": [
        "sip", "mandate", "auto-pay", "autopay", "upi", "payment", "deposit",
        "add money", "refund", "debited", "deducted for sip", "order status",
        "processing", "netbanking", "bank transfer",
    ],
    "Charges & Fees": [
        "charge", "charges", "charged", "fee", "fees", "exit load", "expense ratio",
        "brokerage", "dp charge", "amc", "maintenance charge", "deduction",
        "deducted", "less than shown", "less than the value", "hidden", "stamp duty",
        "stt", "conversion",
    ],
    "Withdrawals & Redemption": [
        "withdraw", "withdrawal", "redeem", "redemption", "payout", "settlement",
        "money not received", "not reached my bank", "pending", "credited",
    ],
    "Statements & Reports": [
        "statement", "statements", "report", "capital gains", "tax", "p&l",
        "profit and loss", "download", "pdf", "invoice", "ledger",
    ],
}

# ---------------------------------------------------------------- fee issue
FEE_ISSUE_LABEL = "Exit Load on Mutual Fund Redemption"

# Ordered: the most specific / highest-priority fee signals first.
FEE_TERMS: list[str] = [
    "exit load",
    "expense ratio",
    "dp charge",
    "amc",
    "annual maintenance",
    "stamp duty",
    "stt",
    "conversion charge",
    "brokerage",
    "processing fee",
]

FEE_ISSUE_KEYWORDS: list[str] = [
    "exit load", "exit-load", "charged less", "amount credited less", "less than shown",
    "less than the value", "deducted", "deduction", "hidden charge", "hidden charges",
    "no clear fee", "fee breakdown", "charges unclear", "surprise charge",
]

FEE_ISSUE_LABELS: dict[str, str] = {
    "exit load": "Exit Load on Mutual Fund Redemption",
    "expense ratio": "Total Expense Ratio (TER) Confusion",
    "dp charge": "DP Charges on Selling Stocks",
    "amc": "Annual Maintenance Charge (AMC) on Demat",
    "annual maintenance": "Annual Maintenance Charge (AMC) on Demat",
    "stamp duty": "Stamp Duty on Trades",
    "stt": "Securities Transaction Tax (STT)",
    "conversion charge": "Payment Conversion Charges",
    "brokerage": "Brokerage / Platform Charges",
    "processing fee": "Payment Processing Fee",
}

# ---------------------------------------------------------------- action ideas
THEME_ACTIONS: dict[str, str] = {
    "Charges & Fees": "Add an inline \"expected exit load\" line to the redeem confirmation screen.",
    "Payments & SIP": "Return a specific failure reason + one-tap auto-retry for failed SIP debits.",
    "Withdrawals & Redemption": "Show a redemption timeline with live status (requested -> processed -> bank credit).",
    "Onboarding & KYC": "Add a KYC status tracker with the exact pending document and an ETA.",
    "Statements & Reports": "Ship a one-tap \"Monthly Statement\" and a plain-language capital gains summary.",
}

# ---------------------------------------------------------------- sources
# 4-6 official, non-login URLs (all verified to resolve). The fee explainer
# injects exactly two — see EXPLAINER_SOURCE_NAMES. Keep in sync with docs/sources.md.
#
# Note: AMFI's legacy exit-load page
# (amfiindia.com/investor-corner/knowledge-center/exit-load.html) now 404s, so AMFI is
# cited for fund charges/TER and the exit-load definition is grounded in SEBI's page.
SOURCES: list[dict[str, str]] = [
    {
        "name": "AMFI — Expense Ratio (Investor Corner)",
        "url": "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=expenseRatio",
        "supports": "What the Total Expense Ratio is, its components, and SEBI Regulation 52 limits",
    },
    {
        "name": "SEBI Investor — Exit Load",
        "url": "https://investor.sebi.gov.in/exit_load.html",
        "supports": "Definition of exit load, how it reduces the redemption amount, worked example",
    },
    {
        "name": "SEBI — Investor Education",
        "url": "https://investor.sebi.gov.in/",
        "supports": "Regulator's plain-language investor-education portal (charges, TER, fees)",
    },
    {
        "name": "Groww — Exit Load in Mutual Funds",
        "url": "https://groww.in/p/exit-load-in-mutual-funds",
        "supports": "Groww's product-level explainer: what exit load is and how it is calculated",
    },
    {
        "name": "Groww — Pricing & Charges",
        "url": "https://groww.in/pricing",
        "supports": "Groww's published brokerage / DP / AMC charges",
    },
    {
        "name": "NSE — Investor's Home (Investor Education)",
        "url": "https://www.nseindia.com/static/invest/investors-home",
        "supports": "Exchange investor-education hub (investing safely, charges & taxes)",
    },
]

# Sources injected into the generated explainer (must be exactly 2 per brief).
EXPLAINER_SOURCE_NAMES = [
    "AMFI — Expense Ratio (Investor Corner)",
    "SEBI Investor — Exit Load",
]


def explainer_sources() -> list[dict[str, str]]:
    picked = [s for s in SOURCES if s["name"] in EXPLAINER_SOURCE_NAMES]
    return picked[:2]


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, DOCS_DIR, MCP_DIR):
        d.mkdir(parents=True, exist_ok=True)
