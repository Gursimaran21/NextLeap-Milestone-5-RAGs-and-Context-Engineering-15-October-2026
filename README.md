# Groww — Milestone 5: Review Insights Analyser

**Product:** Groww · **One-liner:** turn 8–12 weeks of public App Store + Play Store reviews
into (a) a weekly internal product pulse, (b) a customer-facing fee explainer, then push both
into internal tools through **MCP with a human approval gate**.

This repo satisfies **both** briefs at once:
- *Milestone 5 — RAGs & Context Engineering* (review intelligence → pulse → fee explainer → approval-gated MCP)
- *Learn in Public — App Review Insights Analyser* (one-page weekly note + email draft + theme legend)

---

## Architecture

```
 public reviews CSV (8-12 wks)
        |
        v
 [src/ingest.py]      parse dates · window filter · PII REDACT before anything
        |
        v
 [src/cluster.py]     TF-IDF + KMeans -> <=5 themes, mapped to a fixed legend
        |
        v
 [src/insights.py]    top 3 themes · 3 real quotes · fee pain point detection
        |
        v
 [src/retrieval.py]   RAG: retrieve only the reviews about the fee  (grounding)
        |
        +---------------------------+
        v                           v
 [src/pulse.py]             [src/fee_explainer.py]
 <=250-word weekly pulse    <=6 bullets + 2 official links + "Last checked"
        |                           |
        +-------------+-------------+
                      v
            >>> HUMAN APPROVAL GATE <<<   (Streamlit button OR terminal `APPROVE`)
                      |
        +-------------+-------------+
        v                           v
 [append_to_notes]            [create_email_draft]
 Notes/Doc append (JSON+MD)   Gmail-style DRAFT (never sent)
```

---

## Repo layout

```
app.py                      Streamlit prototype (the demo)
src/
  config.py                 themes, fee terms, sources, limits, paths
  pii.py                    redaction rules + final QA gate
  ingest.py                 load · window · redact · clean
  cluster.py                TF-IDF + KMeans -> 5 themes -> legend
  insights.py               themes, quotes, fee-issue detection
  retrieval.py              RAG context retrieval (grounding)
  llm.py                    Gemini wrapper (with model fallback + offline fallback)
  pulse.py                  weekly pulse (<=250 words)
  fee_explainer.py          fee explainer (<=6 bullets, 2 sources)
  mcp_tools.py              the 2 MCP tools + ApprovalGate (token enforced)
  run_all.py                one-command pipeline
mcp/
  approval.py               terminal approval gate (type APPROVE)
  server.py                 REAL MCP server (stdio, FastMCP) — optional
  approval_log.jsonl        every approval decision
data/
  groww_reviews_sample.csv  clean sample (deliverable)
  raw/groww_reviews_raw.csv sample + synthetic PII rows (redaction demo)
  processed/                cleaned + themed reviews
outputs/                    weekly_pulse.md · fee_explainer.md · notes_doc.md · email_draft.eml
docs/                       sources.md · demo_script.md
scripts/make_raw_with_pii.py  regenerates the raw demo export
prompts/cursor-gemini-prompts.md  the Cursor (Gemini) prompt pack used to build this
```

---

## How to run

```bash
pip install -r requirements.txt          # streamlit, pandas, scikit-learn, python-dotenv

# (optional) live LLM text instead of the deterministic writer
pip install google-genai

# 1) one-command pipeline (writes outputs/*)
python -m src.run_all --weeks 12

# 2) the prototype
streamlit run app.py
#   -> sidebar -> "Run analysis" -> open the "MCP Approval" tab -> "Approve & Execute"
```

Optional `.env` (copy `.env.example`):

```
GEMINI_API_KEY=          # empty => deterministic offline writer (constraints still met)
GEMINI_MODEL=gemini-3.8-flash
APPROVAL_CHANNEL=ui
```

> The pipeline **always works with no API key and no internet**. If `GEMINI_API_KEY` is set,
> `src/llm.py` calls Gemini (trying `gemini-3.8-flash`, then 3.5/2.5/flash-latest); if every
> model fails it silently falls back to the deterministic writer.

---

## Where MCP approval happens

| Layer | File | What happens |
|---|---|---|
| UI (default) | `app.py` → *MCP Approval* tab | The payload is shown as JSON. **Nothing runs** until you click **✅ Approve & Execute**. Clicking issues the approval tokens, then the tools run. |
| Guard rail | `src/mcp_tools.py` → `ApprovalGate.require()` | Both tools call `require()` first and raise `PermissionError: approval_required` if no approved token exists. They cannot act unattended. Demo: `python -m src.mcp_tools` prints `BLOCKED as expected`. |
| Terminal | `mcp/approval.py` | Prints the payload and waits for you to type `APPROVE`. |
| Real MCP | `mcp/server.py` | Same two tools over MCP stdio (`request_approval` → `grant_approval` → `append_weekly_entry` / `create_email_draft_tool`). `pip install mcp`. |
| Audit | `mcp/approval_log.jsonl` | Every `REQUESTED / APPROVED / REJECTED / BLOCKED` decision with UTC timestamp + token. |

**Tools (approval-gated):**
1. `append_to_notes(entry)` → appends `{date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links}` to `outputs/notes_doc.md` + `outputs/notes_log.json`.
2. `create_email_draft(subject, body)` → writes `outputs/email_draft.eml` + `.md`. **Draft only, never sent.**

---

## Fee issue identified from reviews

**Exit load on mutual-fund redemption.**

Reviews repeatedly show users confused that the credited amount is lower than the value shown on
the redeem screen — e.g. *"Redeemed my mutual fund and got less than the value shown in the app.
Nobody told me about exit load."* and *"The redeem screen shows one amount but the bank credit is
less."* This is detected in `src/insights.py` (keyword/regex signal over the fee terms) and the
matching reviews are retrieved in `src/retrieval.py` to ground the explainer.

In the sample run: **17 of 43 reviews** match the fee signal, and **Charges & Fees** is the #1 theme (46%).

---

## Theme legend

| Theme | Meaning |
|---|---|
| Onboarding & KYC | signup, KYC verification, PAN/nominee friction |
| Payments & SIP | SIP execution, mandates, failed/refunded payments |
| Charges & Fees | brokerage, exit load, DP charges, AMC, deductions |
| Withdrawals & Redemption | money out, payout timelines, missing status |
| Statements & Reports | statements, capital gains, report downloads |

Clustering is a hybrid: TF-IDF + KMeans groups the reviews, each cluster is mapped to the legend,
and each review keeps the label its text actually matches (95% agreement with the CSV's ground-truth
`theme_hint` column on the sample).

---

## How to re-run for a new week

1. Drop the new public export into `data/` (same columns: `date, rating, title, review_text`).
2. `python -m src.run_all --weeks 12 --input data/your_new_export.csv`
3. `streamlit run app.py` → **Run analysis** → **Approve & Execute**.
4. New doc entry, new email draft, new approval-log lines are appended (old ones are preserved).

## Compliance
- Public review exports only — no scraping behind logins.
- All reviews are PII-redacted *before* any processing (`src/pii.py`); a final assert fails the run if any PII survives.
- No usernames, emails, or IDs in any artifact.
- The email is a **draft**, never sent.

## Deliverables map

| # | Deliverable | File |
|---|---|---|
| 1 | Prototype | `app.py` (`streamlit run app.py`) · demo plan in `docs/demo_script.md` |
| 2 | Weekly product pulse (one-page note) | `outputs/weekly_pulse.md` |
| 3 | Notes/Doc appended entry | `outputs/notes_doc.md`, `outputs/notes_log.json` |
| 4 | Email draft | `outputs/email_draft.eml`, `outputs/email_draft.md` |
| 5 | Reviews CSV sample | `data/groww_reviews_sample.csv` |
| 6 | Source list (4–6 URLs) | `docs/sources.md` |
| 7 | README | this file |
