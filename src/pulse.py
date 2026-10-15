"""Step 2 — Weekly Product Pulse (internal, <=250 words)."""

from __future__ import annotations

import json
from datetime import date

from . import config, llm

SYSTEM = (
    "You are a product analyst writing a weekly internal pulse for the Groww team. "
    "Neutral, factual, no marketing language. You MUST NOT invent quotes or numbers — "
    "use only the data provided. Respect the word limit strictly."
)


def _prompt(insights: dict, context: list[dict]) -> str:
    themes = "\n".join(
        f"- {d['theme']}: {d['count']} reviews ({d['share_pct']}%)"
        for d in insights["theme_distribution"]
    )
    quotes = "\n".join(
        f'- "{q["text"]}" ({q["rating"]}*, {q["week"]})' for q in insights["top_quotes"]
    )
    ctx = "\n".join(f"- [{c['relevance']}] {c['text']}" for c in context[:5])
    return f"""Write a weekly internal product pulse for Groww using ONLY this data.

WINDOW: {insights['window_start']} .. {insights['window_end']} ({insights['window_weeks']} weeks)
TOTAL REVIEWS: {insights['total_reviews']}  |  AVG RATING: {insights['avg_rating']}

THEME DISTRIBUTION:
{themes}

USER QUOTES (use verbatim, do not change):
{quotes}

RETRIEVED CONTEXT (RAG):
{ctx}

DETECTED FEE ISSUE: {insights['fee_issue']['label']} ({insights['fee_issue']['evidence_count']} reviews)

Output markdown with EXACTLY these sections:
# Weekly Product Pulse — Groww (Week of {date.today().isoformat()})
**1. Top Themes** (3 bullets: theme + count/share + one line)
**2. What Users Are Saying** (the 3 quotes verbatim with rating + week)
**3. Key Observation** (2-4 sentences: what is going wrong / trending)
**4. 3 Action Ideas** (3 concrete, testable actions, each tied to a theme)
**5. Fee Signal** (1-2 lines naming the fee issue + evidence count)
Total <= 250 words. Return markdown only."""


def _offline(insights: dict) -> str:
    top = insights["theme_distribution"][: config.TOP_THEMES]
    quotes = insights["top_quotes"]
    fee = insights["fee_issue"]

    theme_lines = [
        f"- **{d['theme']} ({d['count']} reviews, {d['share_pct']:.0f}%)** — "
        f"{config.THEME_MEANINGS.get(d['theme'], '')}."
        for d in top
    ]
    quote_lines = [f'- "{q["text"]}" — {q["rating"]}★, {q["week"]}' for q in quotes]

    lead = top[0]["theme"] if top else "Charges & Fees"
    second = top[1]["theme"] if len(top) > 1 else ""
    observation = (
        f"{lead} is the dominant and rising signal, not a one-off — the same complaint recurs "
        f"across weeks: the redeem/sell screen shows a gross value, the credited value is lower, "
        f"and the reason is not surfaced in the flow. "
    )
    if second:
        observation += (
            f"{second} is the second signal, with users reporting failures without an actionable reason. "
        )

    actions = [config.THEME_ACTIONS.get(d["theme"], "") for d in top]
    actions = [a for a in actions if a][:3]
    while len(actions) < 3:
        actions.append("Publish a single in-app \"All Charges\" page linked from the sell/redeem flow.")
        actions = list(dict.fromkeys(actions))[:3]

    md = f"""# Weekly Product Pulse — Groww (Week of {date.today().isoformat()})

**1. Top Themes**
{chr(10).join(theme_lines)}

**2. What Users Are Saying**
{chr(10).join(quote_lines)}

**3. Key Observation**
{observation.strip()}

**4. 3 Action Ideas**
{chr(10).join(f"{i}. {a}" for i, a in enumerate(actions, 1))}

**5. Fee Signal**
Detected fee issue: **{fee['label']}** — {fee['evidence_count']} matching reviews.
Users do not associate the lower credited amount with this charge."""
    return md


def _word_count(md: str) -> int:
    body = " ".join(
        line for line in md.splitlines() if not line.strip().startswith("#")
    )
    return len([w for w in body.replace("*", "").replace("_", "").split() if w.strip("():,.-")])


def _enforce_cap(md: str, limit: int = config.MAX_PULSE_WORDS) -> str:
    """Trim in the required order: quotes -> key observation -> action wording."""
    if _word_count(md) <= limit:
        return md
    lines = md.splitlines()
    # 1) shorten quotes to first 12 words
    out: list[str] = []
    for ln in lines:
        if ln.strip().startswith('- "') and "—" in ln:
            head, tail = ln.split("—", 1)
            words = head.strip().strip('- "').split()
            ln = '- "' + " ".join(words[:12]) + '…" —' + tail
        out.append(ln)
    md = "\n".join(out)
    if _word_count(md) <= limit:
        return md
    # 2) drop images of the observation to 2 sentences
    if "**3. Key Observation**" in md:
        parts = md.split("**3. Key Observation**")
        obs_and_rest = parts[1].split("**4.")
        obs = obs_and_rest[0].strip()
        sentences = [s.strip() for s in obs.replace("\n", " ").split(". ") if s.strip()]
        obs = ". ".join(sentences[:2]).rstrip(".") + "."
        md = parts[0] + "**3. Key Observation**\n" + obs + "\n\n**4." + obs_and_rest[1]
    return md


def build(insights: dict, context: list[dict] | None = None) -> str:
    context = context or []
    text = llm.generate(SYSTEM, _prompt(insights, context))
    md = text if text else _offline(insights)
    md = _enforce_cap(md)
    return md


def run(insights: dict, context: list[dict] | None = None) -> dict:
    config.ensure_dirs()
    md = build(insights, context)
    config.PULSE_MD.write_text(md, encoding="utf-8")
    payload = {
        "generated_at": insights["generated_at"],
        "word_count": _word_count(md),
        "top_themes": insights["top_themes"],
        "markdown": md,
        "llm": llm.used(),
    }
    config.PULSE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[pulse] wrote {config.PULSE_MD} ({payload['word_count']} words, llm={payload['llm']})")
    return payload


if __name__ == "__main__":
    from .insights import load_insights

    run(load_insights())
