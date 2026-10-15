# Final QA Pass — Groww Review Insights Analyser

**Date:** 2026-10-15 · **Reviewer:** strict checklist pass (P14)
**Reproduce:** `python -m scripts.qa_check` (exit code 0 = all green)

Scope: `outputs/weekly_pulse.md` + `outputs/weekly_pulse.json`, `outputs/fee_explainer.md`
+ `.json`, `outputs/insights.json`, every committed artifact (no PII), and the live MCP
approval gate.

| Requirement | Status | Evidence | Fix (if any) |
|---|---|---|---|
| Pulse ≤ 250 words | ✅ PASS | 223 / 250 (`weekly_pulse.json → word_count`) | — |
| Exactly 3 themes (≤ 5 clusters) | ✅ PASS | top_themes = Charges & Fees, Payments & SIP, Onboarding & KYC; 5 clusters, cap 5 | — |
| Exactly 3 real (verbatim) quotes | ✅ PASS | `insights.top_quotes = 3`; pulse "What Users Are Saying" = 3 bullets | — |
| Exactly 3 action ideas | ✅ PASS | pulse "4. 3 Action Ideas" → 3 numbered items | — |
| Pulse has the 5 required sections | ✅ PASS | Top Themes · What Users Are Saying · Key Observation · 3 Action Ideas · Fee Signal | — |
| Fee explainer ≤ 6 bullets | ✅ PASS | 6 bullets (max 6) | — |
| Exactly 2 official source links | ✅ PASS | AMFI — Expense Ratio (Investor Corner) · SEBI Investor — Exit Load | — |
| `Last checked:` present | ✅ PASS | `Last checked: 2026-10-15` | — |
| Facts-only tone | ✅ PASS | no superlatives / CTAs / exclamation marks | — |
| No PII in any artifact | ✅ PASS | 10 committed files scanned · 0 hits | **Fixed** — see below |
| MCP blocks writes before approval | ✅ PASS | unapproved `append_to_notes` → `PermissionError: approval_required` (logged `BLOCKED`) | — |
| MCP writes only after approval + log | ✅ PASS | `mcp/approval_log.jsonl` → `BLOCKED` → `APPROVED` → `APPROVED` | — |
| Email is a draft only (never sent) | ✅ PASS | `create_email_draft → draft_99d6a4ab0ce1`; no send path exists | — |

**Result: 13 / 13 checks passed.**

---

## Failures found & fixed

### 1. PII persisted in committed processing artifacts (fixed)

`data/processed/reviews_clean.csv` and `reviews_themed.csv` are committed, and they carried the
**raw, un-redacted** `review_text`/`title` columns (e.g. a synthetic demo row reading
`… call me on <phone> or email <email> …`) alongside the redacted `clean_text`. Redaction was
correct in `clean_text`, but the raw columns still shipped in the CSV.

**Fix (`src/ingest.py`, `src/cluster.py`):** both writers now drop `title`/`review_text` and persist
only the redacted columns. The pipeline was re-run (`python -m src.run_all --weeks 12`) and the two
CSVs regenerated — a re-scan finds **0 PII hits** (10 files scanned).

### 2. Stale word count in the README (fixed)

`README.md` advertised the sample pulse at *"238 words"*; the generated pulse is **223 words**. The
README now states 223, matching `weekly_pulse.json`.

---

## Audit log (MCP approval gate)

`mcp/approval_log.jsonl` is git-ignored on purpose (a local, append-only audit trail). A fresh run
produces this exact sequence — a blocked attempt first, then the two approved writes:

```json
{"ts": "2026-10-15T11:35:14.104401+00:00", "decision": "BLOCKED",  "action": "append_to_notes",     "token": "bc8a16808c09433e", "approver": ""}
{"ts": "2026-10-15T11:35:14.104810+00:00", "decision": "APPROVED", "action": "append_to_notes",     "token": "bc8a16808c09433e", "approver": "streamlit_user"}
{"ts": "2026-10-15T11:35:14.106229+00:00", "decision": "APPROVED", "action": "create_email_draft",  "token": "0b33e7492baf9944", "approver": "streamlit_user"}
```

The approval step is not optional: `append_to_notes()` and `create_email_draft()` both call
`ApprovalGate.require(action, payload)` first and raise `PermissionError: approval_required` when no
approved token exists — so the tools can never act unattended. Prove it live with
`python -m src.mcp_tools` → `BLOCKED as expected`.

---

## Notes

- The pulse word count differs by counting method: `weekly_pulse.json` reports **223** (the pipeline's
  own counter), a plain regex recount gives **218**; both are comfortably under the 250 cap.
- The demo screenshots show the app's built-in **40-review** sample (14 fee matches, 223-word pulse).
  This QA pass runs over the repo-canonical **43-review** export (17 fee matches) — same constraints.
- No review usernames, emails, phone numbers, UPI IDs or order IDs appear in any artifact; redaction
  runs in `src/ingest.py` *before* clustering, and a hard assert fails the run if any PII survives.
