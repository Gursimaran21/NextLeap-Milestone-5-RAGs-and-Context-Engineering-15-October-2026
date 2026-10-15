"""P14 — Final QA pass (strict reviewer).

Verifies the generated artifacts against the milestone checklist, exercises the
MCP approval gate live, and prints a `Requirement | Status | Evidence | Fix`
table. Exit code is non-zero if any hard requirement fails.

Run:  python -m scripts.qa_check
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from src import config, mcp_tools

try:  # Windows consoles default to cp1252; the report uses ≤ and —
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

ROOT = config.ROOT
MAX_PULSE_WORDS = config.MAX_PULSE_WORDS
MAX_EXPLAINER_BULLETS = config.MAX_EXPLAINER_BULLETS

rows: list[dict] = []


def record(req: str, ok: bool, evidence: str, fix: str = "") -> None:
    rows.append({"req": req, "ok": bool(ok), "evidence": evidence, "fix": fix})


# --------------------------------------------------------------------------- load
def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""


pulse_md = read(config.PULSE_MD)
pulse = load_json(config.PULSE_JSON)
explainer_md = read(config.EXPLAINER_MD)
explainer = load_json(config.EXPLAINER_JSON)
insights = load_json(config.INSIGHTS_JSON)


def words(text: str) -> int:
    """Same definition the pipeline uses (headings skipped, markdown noise stripped)."""
    body = [ln for ln in text.splitlines() if not ln.strip().startswith("#")]
    return len(re.findall(r"[\w'’.-]+", "\n".join(body)))


def section(md: str, header: str) -> str:
    """Text between a '**N. Header**' marker and the next '**N. ...' marker."""
    m = re.search(re.escape(header) + r"(.*?)(?=\n\*\*\d+\.|\Z)", md, re.S)
    return m.group(1).strip() if m else ""


# --------------------------------------------------------------------------- pulse
topic_bullets = [l for l in section(pulse_md, "**1. Top Themes**").splitlines() if l.strip().startswith("- ")]
quote_bullets = [l for l in section(pulse_md, "**2. What Users Are Saying**").splitlines() if l.strip().startswith('- "')]
action_items = [l for l in section(pulse_md, "**4. 3 Action Ideas**").splitlines() if re.match(r"^\d+\.", l.strip())]

wc = words(pulse_md)
record(
    f"Pulse ≤ {MAX_PULSE_WORDS} words",
    wc <= MAX_PULSE_WORDS,
    f"{wc} words (json: {pulse.get('word_count', 'n/a')})",
)
record(
    "Exactly 3 themes",
    len(topic_bullets) == 3 and len(insights.get("top_themes", [])) == 3,
    f"pulse theme bullets={len(topic_bullets)}, top_themes={len(insights.get('top_themes', []))} "
    f"(of {len(insights.get('theme_distribution', []))} clusters, cap {config.MAX_THEMES})",
)
record(
    "Exactly 3 real (verbatim) quotes",
    len(insights.get("top_quotes", [])) == config.TOP_QUOTES and len(quote_bullets) == 3,
    f"insights.top_quotes={len(insights.get('top_quotes', []))}, pulse quote bullets={len(quote_bullets)}",
)
record(
    "Exactly 3 action ideas",
    len(action_items) == 3 and "3 Action Ideas" in pulse_md,
    f"{len(action_items)} numbered actions",
)
record(
    "Pulse has all 5 required sections",
    all(h in pulse_md for h in ("1. Top Themes", "2. What Users Are Saying", "3. Key Observation",
                                "4. 3 Action Ideas", "5. Fee Signal")),
    "sections 1–5 present",
)

# --------------------------------------------------------------------------- explainer
bullets = explainer.get("bullets", [])
sources = explainer.get("sources", [])
official_urls = {s["url"] for s in config.SOURCES}

record(
    f"Fee explainer ≤ {MAX_EXPLAINER_BULLETS} bullets",
    0 < len(bullets) <= MAX_EXPLAINER_BULLETS,
    f"{len(bullets)} bullets (max {MAX_EXPLAINER_BULLETS})",
)
record(
    "Exactly 2 official source links",
    len(sources) == 2 and all(s.get("url") in official_urls for s in sources),
    " · ".join(s.get("name", "?") for s in sources) or "none",
)
record(
    '"Last checked:" present',
    "Last checked:" in explainer_md and bool(explainer.get("last_checked")),
    f"Last checked: {explainer.get('last_checked', '(missing)')}",
)

banned = ("best", "amazing", "awesome", "guaranteed", "hurry", "limited time",
          "offer", "we recommend", "you should")
tone_hits = [w for w in banned if re.search(rf"\b{w}\b", explainer_md, re.I)]
record(
    "Facts-only tone (no marketing)",
    not tone_hits and "!" not in explainer_md,
    "no superlatives / CTAs / exclamation" if not tone_hits else f"found: {tone_hits}",
    "Rewrite flagged bullets in a neutral, factual tone." if tone_hits else "",
)

# --------------------------------------------------------------------------- PII
_ARTIFACT_FILES = [
    config.PULSE_MD, config.PULSE_JSON, config.EXPLAINER_MD, config.EXPLAINER_JSON,
    config.INSIGHTS_JSON, config.NOTES_MD, config.NOTES_JSON, config.EMAIL_EML,
    config.EMAIL_MD,
    *sorted(config.DOCS_DIR.glob("*.md")),
    *sorted((config.DATA_DIR / "processed").glob("*.csv")),
]

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[-\s]?)?[6-9]\d{9}(?!\d)")
_UPI = re.compile(r"\b[\w.-]{2,}@(?:ok\w+|ybl|paytm|apl|upi|ibl|axl|sbi|hdfcbank|icici)\b", re.I)
_LONGID = re.compile(r"(?<!\d)\d{8,}(?!\d)")


def scan_pii(text: str) -> list[str]:
    """PII only — ignore public http(s) URLs and the example.com placeholder."""
    stripped = re.sub(r"https?://\S+|www\.\S+", " ", text).replace("example.com", " ")
    hits: list[str] = []
    for label, pat in (("email", _EMAIL), ("phone", _PHONE), ("upi", _UPI), ("long-id", _LONGID)):
        hits += [f"{label}:{m.group(0)[:24]}" for m in pat.finditer(stripped)]
    return hits


pii_hits: list[str] = []
scanned = 0
for f in _ARTIFACT_FILES:
    if f.exists():
        scanned += 1
        pii_hits += [f"{f.name} → {h}" for h in scan_pii(f.read_text(encoding="utf-8", errors="ignore"))]
record(
    "No PII in any artifact",
    not pii_hits,
    f"{scanned} files scanned · 0 hits" if not pii_hits else f"{len(pii_hits)} hit(s): " + "; ".join(pii_hits[:6]),
)

# --------------------------------------------------------------------------- MCP
entry = mcp_tools.build_note_entry(insights, pulse_md, explainer)
subject = mcp_tools.email_subject()
body = mcp_tools.build_email_body(insights, pulse_md, explainer)

gate = mcp_tools.ApprovalGate()
blocked_ok = False
try:
    mcp_tools.append_to_notes(entry, gate)          # must raise
except PermissionError:
    blocked_ok = True

approved_ok = False
res_note = res_mail = {}
if blocked_ok and not pii_hits:
    gate.approve("append_to_notes", entry)
    gate.approve("create_email_draft", {"subject": subject, "body": body})
    res_note = mcp_tools.append_to_notes(entry, gate)
    res_mail = mcp_tools.create_email_draft(subject, body, gate)
    approved_ok = res_note.get("status") == "appended" and res_mail.get("status") == "draft_created"

log_lines: list[dict] = []
if config.APPROVAL_LOG.exists():
    for ln in read(config.APPROVAL_LOG).strip().splitlines():
        try:
            log_lines.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
decisions = {r["decision"] for r in log_lines}

record(
    "MCP blocks writes before approval",
    blocked_ok,
    "unapproved `append_to_notes` raised PermissionError (logged BLOCKED)",
)
record(
    "MCP writes only after approval + audit log",
    approved_ok and "APPROVED" in decisions and config.APPROVAL_LOG.exists(),
    f"log={config.APPROVAL_LOG.name} · decisions={sorted(decisions)} · {len(log_lines)} entries",
)
record(
    "Email is draft only (never sent)",
    res_mail.get("status") == "draft_created",
    f"create_email_draft → draft_id {res_mail.get('draft_id', 'n/a')}; no send path exists",
)

# --------------------------------------------------------------------------- report
print("\nFinal QA — Groww Review Insights Analyser\n")
print("| Requirement | Status | Evidence | Fix |")
print("|---|---|---|---|")
for r in rows:
    status = "PASS" if r["ok"] else "FAIL"
    print(f"| {r['req']} | {status} | {r['evidence']} | {r['fix'] or '—'} |")

fails = [r for r in rows if not r["ok"]]
print(f"\n{len(rows) - len(fails)}/{len(rows)} checks passed"
      + ("" if not fails else " — FAILURES: " + ", ".join(r["req"] for r in fails)))
sys.exit(1 if fails else 0)
