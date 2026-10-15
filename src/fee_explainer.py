"""Step 3 — Fee Explainer derived from the confusion found in reviews.

<=6 bullets, neutral facts-only tone, exactly 2 official source links, "Last checked:".
"""

from __future__ import annotations

import json
from datetime import date

from . import config, llm

SYSTEM = (
    "You write neutral, facts-only support copy for a stock and mutual-fund app. "
    "No marketing language, no investment advice, no opinion. Plain English that a "
    "support agent can paste into a reply. Never invent sources."
)


def _bullets_for(term: str) -> list[str]:
    """Deterministic, facts-only bullets keyed off the detected fee term."""
    library: dict[str, list[str]] = {
        "exit load": [
            "Exit load is a fee some mutual fund schemes charge when you redeem units before a defined holding period.",
            "It is charged by the fund scheme, not by Groww, and is deducted from your redemption proceeds.",
            "It is calculated as a percentage of the redeemed value, so the credited amount can be lower than the value shown.",
            "Each scheme sets its own exit load and holding period; check the scheme's Scheme Information Document.",
            "For most equity schemes the holding period is 1 year, but this varies by scheme.",
            "There is no exit load after the holding period defined by the scheme.",
        ],
        "expense ratio": [
            "The expense ratio is an annual fee charged by the fund to manage the scheme.",
            "It is deducted from the scheme's NAV daily, so you do not pay it separately.",
            "It is shown as a percentage per year, not as a one-time deduction on redemption.",
            "Different schemes have different expense ratios; check the scheme page or Scheme Information Document.",
            "Direct plans have a lower expense ratio than regular plans for the same scheme.",
            "It is not charged by Groww and does not depend on when you redeem.",
        ],
        "dp charge": [
            "A DP (Depository Participant) charge is charged by the depository when you sell shares from your demat account.",
            "It is a flat per-sell charge, applied per scrip per day, not per share.",
            "It appears in the contract note after the sale, not at the time of order placement.",
            "Groww's zero-brokerage promise covers brokerage only; statutory and DP charges still apply.",
            "The exact amount is published on Groww's pricing page.",
            "It is not charged when you buy shares.",
        ],
    }
    if term in library:
        return library[term][: config.MAX_EXPLAINER_BULLETS]
    return [
        f"{term.title()} is a charge applied under the scheme or platform's published rules.",
        "It is deducted from the transaction value, which is why the credited amount can be lower than shown.",
        "It is not an arbitrary deduction and is not set by the app's support team.",
        "The exact rate and conditions are published in the scheme or pricing documents.",
        "You can see the applicable charge in the confirmation/contract note after the transaction.",
        "For scheme-specific charges, check the Scheme Information Document.",
    ][: config.MAX_EXPLAINER_BULLETS]


def _render(label: str, bullets: list[str], sources: list[dict[str, str]]) -> str:
    lines = [f"# {label} — Explained", ""]
    lines += [f"{i}. {b}" for i, b in enumerate(bullets, 1)]
    lines += ["", "**Sources**"]
    lines += [f"- [{s['name']}]({s['url']})" for s in sources]
    lines += ["", f"Last checked: {date.today().isoformat()}"]
    return "\n".join(lines)


def _prompt(insights: dict, context: list[dict]) -> str:
    fee = insights["fee_issue"]
    ctx = "\n".join(f'- "{c["text"]}"' for c in context[:4])
    return f"""Write a customer-facing explainer for this charge: {fee['label']}.

Users are confused about exactly this (verbatim, from reviews):
{ctx or "- (no direct snippets)"}

Rules:
- MAX 6 numbered bullets.
- Neutral, facts-only, no advice, no marketing.
- Explain WHY the credited amount can be lower than the value shown.
- Include these 2 sources exactly:
  - {config.SOURCES[0]['name']}: {config.SOURCES[0]['url']}
  - {config.SOURCES[1]['name']}: {config.SOURCES[1]['url']}
- End with: Last checked: {date.today().isoformat()}
Format: "# {fee['label']} — Explained" then bullets, then **Sources**, then the date. Markdown only."""


def build(insights: dict, context: list[dict] | None = None) -> str:
    context = context or []
    fee = insights["fee_issue"]
    sources = config.explainer_sources()
    text = llm.generate(SYSTEM, _prompt(insights, context))
    if text and text.count("\n1.") <= 1:
        return text
    return _render(fee["label"], _bullets_for(fee.get("term", "charge")), sources)


def run(insights: dict, context: list[dict] | None = None) -> dict:
    config.ensure_dirs()
    md = build(insights, context)
    config.EXPLAINER_MD.write_text(md, encoding="utf-8")

    bullets = [
        ln.split(". ", 1)[1] if ". " in ln else ln
        for ln in md.splitlines()
        if ln.strip()[:1].isdigit() and ". " in ln
    ]
    payload = {
        "generated_at": insights["generated_at"],
        "label": insights["fee_issue"]["label"],
        "bullets": bullets[: config.MAX_EXPLAINER_BULLETS],
        "sources": config.explainer_sources(),
        "last_checked": date.today().isoformat(),
        "markdown": md,
        "llm": llm.used(),
    }
    config.EXPLAINER_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[fee_explainer] wrote {config.EXPLAINER_MD} ({len(payload['bullets'])} bullets)")
    return payload


if __name__ == "__main__":
    from .insights import load_insights

    run(load_insights())
