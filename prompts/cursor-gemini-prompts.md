# Groww — Cursor (Gemini) Prompt Pack (combines BOTH Milestone 5 briefs)

Product: **Groww** · Goal: Reviews → Themes → Weekly Pulse + Fee Explainer → MCP (approval-gated) → Doc + Email Draft
Also covers *Learn in Public — App Review Insights Analyser* (one-page weekly note + email draft, no PII, theme legend).

How to use this file:
1. Open Cursor. If the project already exists, open that folder (the prompts are guarded to not overwrite existing files); otherwise create a new folder to build from scratch. Set the AI model to **Gemini**.
2. Run the prompts **in order**: P1 → P2 → P3 → P4 → P5 → P5.5 → P6 → P7 → P8 → P9 → P10 → S0 → S14 → P11 → P14. Each is a separate, self-contained message.
3. After each prompt, review the generated files before moving on.

## Combined requirements map (both briefs → one build)

| Requirement | Source | Where it's satisfied |
|---|---|---|
| Import reviews 8–12 wks (rating, title, text, date) | LIP | `src/ingest.py` |
| No PII in any artifact | LIP | `src/pii.py` (redact before processing + final assert) |
| ≤5 themes, top 3 highlighted | both | `src/cluster.py`, `src/insights.py` |
| 3 real user quotes | both | `src/insights.py` |
| Detect recurring confusion on a **fee/charge** | M5 | `src/insights.py` (`fee_issue`) + `src/retrieval.py` (RAG context) |
| Weekly pulse / one-page note ≤250 words | both | `src/pulse.py` |
| Fee explainer ≤6 bullets, 2 official links, "Last checked:" | M5 | `src/fee_explainer.py` |
| Append to Notes/Doc with the required JSON shape | M5 | `src/mcp_tools.py :: append_to_notes` |
| Email draft (subject + body), no auto-send | both | `src/mcp_tools.py :: create_email_draft` |
| Approval step before any action | M5 | `app.py` MCP tab + `ApprovalGate.require()` + `mcp/approval.py` |
| Theme legend + how to re-run | LIP | `README.md` |
| Working prototype | M5 + LIP | `app.py` (Streamlit) |

---

## Phase 0 — Project setup

### P1 — Scaffold the project
```
You are my senior AI engineer pair for a project called "Groww Milestone 5 — Review Insights Analyser".

Scaffold the project IN THE CURRENT FOLDER (do NOT create a nested subfolder).

Create this structure:
  data/raw/          # raw review exports (may contain PII)
  data/processed/    # cleaned + themed reviews
  src/               # python modules
  outputs/           # weekly pulse, fee explainer, notes/email, json
  mcp/               # MCP server (Doc append + email draft tools) + approval log
  docs/              # sources.md, demo_script.md
  scripts/           # helper scripts
  prompts/           # prompt pack
  .env.example
  requirements.txt
  README.md

Tech stack: Python 3.10+, pandas, scikit-learn (TF-IDF + KMeans),
google-genai (optional, for live Gemini text), python-dotenv, and Streamlit for the prototype UI.

requirements.txt (core must run with NO api key):
  streamlit, pandas, scikit-learn, python-dotenv
and add comments noting google-genai and mcp are OPTIONAL installs.

Create .env.example with comments:
  # LLM (optional). Empty GEMINI_API_KEY => deterministic offline writer (all constraints still met)
  GEMINI_API_KEY=
  GEMINI_MODEL=gemini-3.8-flash
  # MCP (optional, only for mcp/server.py; the app writes local files by default)
  GOOGLE_DOC_ID=
  GMAIL_SENDER=
  # Approval: "ui" (Streamlit button) or "terminal" (type APPROVE)
  APPROVAL_CHANNEL=ui

Add .gitignore (Python + .env + outputs/*.eml).
Add a minimal README.md with a "How to run" placeholder.
Keep it clean and production-style. Show me the tree when done.

Most of this already exists — do NOT overwrite existing files.
Just create anything missing and show me the current tree.
```

### P2 — Config + constants (theme legend)
```
Create src/config.py. No secrets here — API keys come from .env only.
Use `from __future__ import annotations`, type hints, and pathlib.

1) PATHS (absolute, off the repo root):
   ROOT = Path(__file__).resolve().parents[1]
   DATA_DIR, RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, DOCS_DIR, MCP_DIR
   RAW_REVIEWS       = data/raw/groww_reviews_raw.csv
   SAMPLE_REVIEWS    = data/groww_reviews_sample.csv
   REVIEWS_THEMED    = data/processed/reviews_themed.csv
   INSIGHTS_JSON, PULSE_MD, PULSE_JSON, EXPLAINER_MD, EXPLAINER_JSON,
   NOTES_JSON, NOTES_MD, EMAIL_EML, EMAIL_MD          # all under outputs/
   APPROVAL_LOG      = mcp/approval_log.jsonl
   def ensure_dirs() -> None: create the data/raw, data/processed, outputs, docs, mcp dirs.

2) LIMITS:
   WEEKS = 12
   MAX_THEMES = 5
   MAX_PULSE_WORDS = 250
   MAX_EXPLAINER_BULLETS = 6
   TOP_THEMES = 3
   TOP_QUOTES = 3
   RANDOM_STATE = 42

3) THEMES — exactly these 5, in this order:
   "Onboarding & KYC", "Payments & SIP", "Charges & Fees",
   "Withdrawals & Redemption", "Statements & Reports"
   THEME_MEANINGS: one-line meaning per theme (shown in the UI).
   THEME_KEYWORDS: keyword list per theme (cluster mapping + fallback).
   THEME_ACTIONS: one concrete product action per theme (used by the pulse).

4) FEE ISSUE:
   FEE_ISSUE_LABEL = "Exit Load on Mutual Fund Redemption"
   FEE_TERMS: ordered list, most specific first —
     exit load, expense ratio, dp charge, amc, annual maintenance, stamp duty,
     stt, conversion charge, brokerage, processing fee
   FEE_ISSUE_KEYWORDS: confusion phrases —
     exit load, charged less, amount credited less, less than shown,
     less than the value, deducted, deduction, hidden charge, no clear fee,
     fee breakdown, charges unclear
   FEE_ISSUE_LABELS: dict mapping each FEE_TERM -> a human-readable label.

5) SOURCES:
   SOURCES: 4-6 dicts {name, url, supports} for official, non-login pages —
     AMFI exit load, SEBI investor education, Groww exit load, Groww pricing,
     AMFI TER, NSE investor education.
   EXPLAINER_SOURCE_NAMES: exactly 2 names from that list (the ones the explainer injects).
   def explainer_sources() -> list[dict[str, str]]: return those 2 entries.

Most of this already exists in src/config.py — do NOT overwrite it.
Extend it if anything above is missing, then show me the final file.
```

---

## Phase 1 — Review Intelligence Layer (Step 1)

### P3 — Load + clean + redact PII
```
Create TWO files: src/pii.py and src/ingest.py.

A) src/pii.py — pure, pytest-friendly, no pandas import.
   REDACTED = "[REDACTED]"
   - redact_pii(text: str) -> str
   - redact_pii_counted(text: str) -> tuple[str, int]   # (cleaned, n_replacements)
   - contains_pii(text: str) -> bool                    # final QA gate
   Apply, in this order, replacing matches with [REDACTED]:
     emails; URLs (http/https/www); @handles; phone numbers (10-digit and +91,
     with or without separators); UPI ids (name@bank-like); any standalone number
     with >= 8 digits (order/client/ticket ids).
   Collapse repeated "[REDACTED] [REDACTED]" into a single one. Return input unchanged
   for non-str / empty. Add a __main__ demo that prints before/after and asserts
   not contains_pii(out).

B) src/ingest.py
   - load_reviews(path=None, weeks=config.WEEKS) -> pd.DataFrame
     * input path: `path` if given, else config.RAW_REVIEWS if it exists, else
       config.SAMPLE_REVIEWS. (RAW may contain synthetic PII — that is the point; it gets redacted.)
     * required columns: date, rating, title, review_text. Tolerate/ignore extra columns
       (review_id, source, app_version, theme_hint).
     * parse `date` as datetime, drop unparsable; coerce `rating` to numeric, drop NaN.
     * WINDOW: anchor on the LATEST review date in the export (reproducible),
       cutoff = anchor - weeks; keep date >= cutoff. Do NOT use today's date.
     * REDACT BEFORE ANYTHING ELSE: raw = f"{title} {review_text}", run
       redact_pii_counted on it, sum the redaction count.
     * clean_text = the redacted string. Drop rows where review_text is empty OR
       clean_text shorter than 15 chars; drop duplicate clean_text.
     * final safety gate: assert not df["clean_text"].map(contains_pii).any()
     * store stats on df.attrs: rows_loaded, redactions, anchor, window_start, source_file.
   - run(path=None, weeks=config.WEEKS) -> pd.DataFrame: config.ensure_dirs(),
     load_reviews(), save to config.PROCESSED_DIR / "reviews_clean.csv",
     print "loaded N rows -> kept M | window X..Y | redactions R", return df.
   - __main__ block calling run().

Verify: `python -m src.pii` prints the redaction demo and "no PII remains";
`python -m src.ingest` prints "loaded 43 rows -> kept 43 | ... | redactions 6".
```

### P4 — Theme clustering
```
Create src/cluster.py — an explainable hybrid clusterer. Use config for everything
(THEMES, THEME_KEYWORDS, MAX_THEMES, RANDOM_STATE, REVIEWS_THEMED).

1) Keyword scorer
   - _review_theme(text) -> str: for each theme in config.THEME_KEYWORDS, sum keyword
     hits (multi-word phrases count MORE than single words, e.g. 1.6x vs 1.0x).
     Return the highest-scoring theme, or NONE ("__none__") if nothing matches.

2) cluster(df, k=config.MAX_THEMES) -> pd.DataFrame
   - Label every review first: df["review_theme"] = df["clean_text"].map(_review_theme).
   - Clamp k: k = max(1, min(k, len(df), config.MAX_THEMES))   # never crash on tiny data.
   - TF-IDF on clean_text: stop_words="english", ngram_range=(1,2), sublinear_tf=True.
   - KMeans(n_clusters=k, random_state=config.RANDOM_STATE, n_init=10) -> df["cluster_id"].
   - cluster_terms[cid] = the top ~8 TF-IDF terms of that cluster's centroid.
   - Map each cluster -> theme by MAJORITY of its members' review_theme (fall back to
     keyword evidence over the whole cluster if nobody voted). Sort clusters by vote
     strength and greedily assign so no two clusters take the same theme while a theme
     is still free. Store as df["cluster_theme"].
   - Final df["theme"]: each review keeps its own review_theme when it has one,
     else it inherits its cluster's theme. NEVER leave a theme unlabeled.
   - Add df["cluster_terms"] (comma-joined top terms). Keep columns:
     theme, cluster_id, cluster_theme, review_theme, cluster_terms.

3) run(df) -> pd.DataFrame
   - config.ensure_dirs(); out = cluster(df); save to config.REVIEWS_THEMED.
   - Print the theme distribution (count + % share), sorted descending, plus
     "N themes from M reviews".

4) __main__ block: load via ingest.load_reviews() then run().

QA checkpoint (run this after):
  python -c "import pandas as pd; d=pd.read_csv('data/processed/reviews_themed.csv'); \
  m=d[d.theme_hint.isin(d.theme.unique())]; print('match %.0f%%'%(100*(m.theme==m.theme_hint).mean()))"
  Expect ~95% and Charges & Fees = the #1 theme.

Note: this keeps a real KMeans clustering (cluster_id + cluster_terms) AND an accurate
fixed-legend label. The theme_hint column in the sample is ground truth only for this QA
check; never use it in the analysis itself.
```

### P5 — Insight extraction
```
Create src/insights.py. Use config for limits/labels (TOP_THEMES, TOP_QUOTES,
WEEKS, FEE_TERMS, FEE_ISSUE_KEYWORDS, FEE_ISSUE_LABELS, INSIGHTS_JSON) and
pii.contains_pii for the quote safety gate.

API (do NOT read the CSV internally — take the themed DataFrame):
- build_insights(df, weeks=config.WEEKS) -> dict
- run(df, weeks=config.WEEKS) -> dict   # writes config.INSIGHTS_JSON, prints a summary
- load_insights() -> dict                # reads the JSON back
- __main__: cluster(load_reviews()) -> run()

Produce this JSON (add the 3 fields in BOLD — downstream code reads them):
{
  "generated_at": ISO timestamp (UTC),
  "window_weeks": int,
  "window_start": df.attrs["window_start"],   # from ingest
  "window_end":   df.attrs["anchor"],         # latest review date
  "source_file":  df.attrs["source_file"],
  "total_reviews": int,
  "avg_rating": float (2 dp),
  "theme_distribution": [{"theme": str, "count": int, "share_pct": float (1 dp)}],
  "top_themes": [ first config.TOP_THEMES theme names ],
  "top_quotes": [ {text, rating, date, week, theme} x config.TOP_QUOTES ],
  "fee_issue": {
     "label": str,              # from config.FEE_ISSUE_LABELS
     "term": str,               # the matched fee term, e.g. "exit load"
     "evidence_count": int,
     "matched_keywords": [str],
     "sample_snippets": [ up to 3 short snippets ]
  }
}

Selection rules:
- Sort theme_distribution by count descending.
- top_quotes: score reviews (prefer 3-4 star + a strong 1-star, moderate length,
  fee/theme specificity); spread quotes across different themes when possible;
  clip to 180 chars; skip any quote where contains_pii(text) is True; no duplicates.
  Each quote MUST include "week" = the review date as "%b %d" (e.g. "Aug 27").
- fee_issue detection: pick the term from config.FEE_TERMS with the highest review count;
  if all are zero, fall back to config.FEE_ISSUE_KEYWORDS (default "exit load").
  label via config.FEE_ISSUE_LABELS[term]. Count evidence reviews that mention the term OR a
  confusion keyword. Keep matched_keywords + up to 3 redacted sample_snippets.
- Guard: if the DataFrame is empty, raise a clear error (do not divide by zero).
```

**Verify after P5:**
```bash
python -m src.insights
python -c "import json; d=json.load(open('outputs/insights.json')); \
print(d['top_themes'], d['fee_issue']['label'], d['fee_issue']['term'], \
d['window_start'], d['window_end'], d['top_quotes'][0].keys())"
# expect: ['Charges & Fees', ...] 'Exit Load on Mutual Fund Redemption' 'exit load'
#         '2026-07-19' '2026-10-11' dict_keys([... 'week' ...])
```

### P5.5 — RAG retrieval (context engineering)
```
Create src/retrieval.py - the RAG retrieval layer. This IS the context engineering:
the pulse + fee explainer receive ONLY insights.json + this retrieved context, so the
model can never invent the fee issue.

API (must match what run_all.py / pulse / fee_explainer call):
- retrieve_context(df, query, k=6, must_match=None) -> list[dict]
  TF-IDF (stop_words="english", ngram_range=(1, 2)) + cosine similarity over
  df["clean_text"]. If must_match is given, restrict the candidate pool to reviews that
  contain at least one of those substrings (keeps context on-topic); if that pool is empty,
  fall back to the full df. Return the top-k as
  [{text, rating, date, theme, relevance}] with relevance = cosine score rounded to 3 dp.
- run(df, fee_label) -> list[dict]
  query = f"users confused about {fee_label} charges deductions on redemption"
  must_match = ["exit load", "charge", "charged", "deducted", "less"]
  -> retrieve_context(df, query, k=6, must_match=...)
  Print "[retrieval] retrieved N context reviews for '<fee_label>'".
- __main__: run(cluster(load_reviews()), config.FEE_ISSUE_LABEL)

Notes:
- No extra PII handling needed here: clean_text was already redacted in P3.
- Consumers read only c["text"] (fee_explainer) and c["relevance"]+c["text"] (pulse).
- Grounding guarantee = run_all passes this list straight into pulse.run()/fee_explainer.run();
  nothing else is sent to the model.
```

---

## Phase 2 — Weekly Product Pulse (Step 2)

### P6 — Pulse generator
```
Create src/pulse.py.

API:
- build(insights: dict, context: list[dict]) -> str
- run(insights: dict, context: list[dict] | None = None) -> dict

Generate a weekly internal product pulse. Try Gemini first via src/llm.generate(...);
if no API key or the call fails, fall back to a DETERMINISTIC offline writer built from
insights + config (the pipeline must run with no API key).

Grounding: use ONLY insights["top_themes"], insights["theme_distribution"],
insights["top_quotes"], insights["fee_issue"] and the retrieved `context`.
The system prompt must forbid inventing quotes or numbers.

Hard rules:
- <= config.MAX_PULSE_WORDS (250) words total.
- Neutral, factual, internal tone.
- Structure EXACTLY:
  # Weekly Product Pulse — Groww (Week of {date})
  **1. Top Themes**
  (3 bullets, each with the theme name + count/share + one line from config.THEME_MEANINGS)
  **2. What Users Are Saying**
  (the 3 verbatim quotes from insights, with rating + week)
  **3. Key Observation**
  (2-4 sentences: what is going wrong / trending, naming the top theme and the fee signal)
  **4. 3 Action Ideas**
  (3 concrete, testable actions, taken from config.THEME_ACTIONS for the top themes)
  **5. Fee Signal**
  (1-2 lines naming insights["fee_issue"]["label"] + its evidence_count)
- Return ONLY markdown.
- Enforce the word cap PROGRAMMATICALLY after generation; if over, trim in this order:
  quotes -> key observation -> action wording.
- run() writes config.PULSE_MD and config.PULSE_JSON ({generated_at, word_count,
  top_themes, markdown, llm}) and prints the final word count + whether Gemini was used.
```

**Verify after P6:**
```bash
python -m src.pulse
python -c "import json; d=json.load(open('outputs/weekly_pulse.json')); print(d['word_count'], d['llm'], list(d.keys()))"
# expect: <= 250 words | llm True (Gemini) or False (offline) | keys ['generated_at','word_count','top_themes','markdown','llm']
python -c "t=open('outputs/weekly_pulse.md').read(); print([s for s in ['1. Top Themes','2. What Users Are Saying','3. Key Observation','4. 3 Action Ideas','5. Fee Signal'] if s in t])"
# expect: all 5 sections present
```

---

## Phase 3 — Fee Explainer (Step 3)

### P7 — Fee explainer generator
```
Create src/fee_explainer.py.

API:
- build(insights: dict, context: list[dict]) -> str
- run(insights: dict, context: list[dict] | None = None) -> dict

Derive the explainer from insights["fee_issue"] plus the retrieved `context` (the exact
reviews that mention the fee). Try Gemini first via src/llm.generate(...); if no API key
or the call fails, fall back to a DETERMINISTIC offline writer (the pipeline must run
with no API key). Keep a small library of facts-only bullets keyed by the fee term.

Hard rules:
- MAX config.MAX_EXPLAINER_BULLETS (6) bullet points.
- Neutral, facts-only, no marketing language, no advice.
- Plain English suitable for support copy-paste.
- Format:
  # {fee label} — Explained
  1. ... (<=6 bullets)
  **Sources**
  - [Source name](url)
  - [Source name](url)

  Last checked: {today in YYYY-MM-DD}

- Include exactly 2 official source links: take them from config.explainer_sources()
  (which returns 2 entries from config.SOURCES — AMFI exit load, SEBI investor education).
- Bullets must map to what users are confused about in the reviews (e.g. why the credited
  amount is lower than the value shown).
- No PII. No usernames.
- run() writes config.EXPLAINER_MD and config.EXPLAINER_JSON (generated_at, label,
  bullets as a list, sources, last_checked, markdown, llm) and prints the bullet count.
```

**Verify after P7:**
```bash
python -m src.fee_explainer
python -c "import json; d=json.load(open('outputs/fee_explainer.json')); print(d['label'], len(d['bullets']), [s['name'] for s in d['sources']], d['last_checked'], d['llm'], list(d.keys()))"
# expect: 'Exit Load on Mutual Fund Redemption' <=6 ['AMFI — Exit Load (Investor Corner)','SEBI — Investor Education'] <date> True/False
#         keys ['generated_at','label','bullets','sources','last_checked','markdown','llm']
python -c "t=open('outputs/fee_explainer.md').read(); print('Last checked:' in t, t.count('http'))"
# expect: True 2   (exactly 2 official links)
```

### P8 — Orchestrator
```
Create src/run_all.py that runs, in sequence:
  ingest -> cluster -> insights -> retrieval -> pulse -> fee_explainer
i.e. call ingest.run/load_reviews, cluster.run, insights.run, then
retrieval.run(df, insights["fee_issue"]["label"]) to get the RAG context, then
pulse.run(insights, context) and fee_explainer.run(insights, context).

Log each step with timing ("== n/6 <step> =="), and stop with a clear error if any step fails.
Add a --weeks CLI arg (default config.WEEKS=12) and a --input arg (path to a reviews CSV,
default None). At the end, print the elapsed time and remind the user to run
`streamlit run app.py` and approve the MCP actions.
```

**Verify after P8 (full end-to-end):**
```bash
python -m src.run_all --weeks 12
python -c "import os; print(sorted(f for f in os.listdir('outputs') if f.endswith(('.json','.md'))))"
# expect: banners == 1/6 .. 6/6, then "Done in N.Ns." + the Streamlit reminder, and outputs containing
#         fee_explainer.json, fee_explainer.md, insights.json, weekly_pulse.json, weekly_pulse.md
```

---

## Phase 4 — MCP + Approval (Step 4)

### P9 — MCP server scaffold
```
Create TWO pieces. The tool layer must work fully OFFLINE (no Google account needed);
the real MCP server is optional.

A) src/mcp_tools.py — the tool layer the Streamlit app calls.
   - build_note_entry(insights, pulse_md, explainer) -> dict with EXACTLY:
       {date, top_themes, weekly_pulse, identified_fee_issue, explanation_bullets, source_links}
     (date = today ISO; source_links = the 2 explainer source URLs.)
   - email_subject() -> f"Weekly Product Pulse + Customer Clarification — Groww (Week of {today})"
   - build_email_body(insights, pulse_md, explainer) -> str: the weekly pulse, then a
     "Reusable support snippet — {fee label}" section with the bullets + sources + Last checked.
   - class ApprovalGate:
       token_for(action, payload) -> sha256(action + json)[:16]
       request(action, payload) ; approve(action, payload, approver) ; reject(...)
       require(action, payload) -> raise PermissionError("approval_required: ...") and log
         BLOCKED if the token is not approved
       _log(decision, action, token, approver) appends {ts, decision, action, token, approver}
         to config.APPROVAL_LOG (jsonl).
   - append_to_notes(entry, gate) -> dict: call gate.require("append_to_notes", entry) FIRST,
     then append to config.NOTES_JSON (a list) and append a readable block to config.NOTES_MD.
     Return {tool, status:"appended", rows_in_doc, doc_file, json_file}.
   - create_email_draft(subject, body, gate) -> dict: call
     gate.require("create_email_draft", {"subject": subject, "body": body}) FIRST, then write
     config.EMAIL_EML (RFC822 via email.message.EmailMessage; To = self/alias) and config.EMAIL_MD.
     Return {tool, status:"draft_created", draft_id, to, eml_file, md_file}. NEVER sends.
   - read_pending_batch() -> dict reading the generated outputs/*.json.
   - __main__: prove the gate blocks an unapproved append_to_notes call.

B) mcp/server.py — OPTIONAL real MCP server (stdio, FastMCP) with a guarded import so the
   app never needs it (requires `pip install mcp`). Import the implementations from
   src.mcp_tools (single source of truth). Expose: read_pending_batch, request_approval,
   grant_approval, append_weekly_entry, create_email_draft_tool. Print a manifest of tool
   names + descriptions on startup.
   Top-of-file docstring: "MCP tools are DESTRUCTIVE and must only be called AFTER explicit human approval."
```

**Verify after P9:**
```bash
python -m src.mcp_tools
# expect: BLOCKED as expected -> approval_required: 'append_to_notes' was called without an approved token.
python -c "src=open('mcp/server.py',encoding='utf-8').read(); print(all(t in src for t in ['read_pending_batch','request_approval','grant_approval','append_weekly_entry','create_email_draft_tool']))"
# expect: True   (running the server itself needs: pip install mcp)
```

### P10 — Approval gate (MCP-side, defensive)
```
Approval gating = the ApprovalGate in src/mcp_tools.py (in-process, defensive) + mcp/approval.py
(interactive CLI). Implement both.

1. src/mcp_tools.ApprovalGate (from P9):
   - deterministic token per action+payload (sha256[:16]).
   - require() raises PermissionError("approval_required: ...") AND logs BLOCKED if the token
     was not approved -> the tools can NEVER act unattended.
   - every REQUESTED / APPROVED / REJECTED / BLOCKED decision is appended to config.APPROVAL_LOG.

2. mcp/approval.py:
   - preview(action, payload) prints a readable preview of what is about to be written.
   - approve_interactive(action, payload, gate) prints the preview and waits for the user to
     type exactly "APPROVE"; anything else calls gate.reject(...). Returns bool.
   - __main__ demo wiring the above.

Requirement satisfied: no write happens without a human decision, and every decision is logged.
```

**Verify after P10:**
```bash
python -m src.mcp_tools
# expect: BLOCKED as expected -> approval_required: ...   (unapproved write is refused + logged BLOCKED)
"" | python mcp/approval.py
# expect: prints the preview, then "Rejected. No action taken." and
#         "decision logged to ...approval_log.jsonl | approved=False"
python -c "import json,pathlib; p=pathlib.Path('mcp/approval_log.jsonl'); print([json.loads(l)['decision'] for l in p.read_text().splitlines()][-3:])"
# expect: recent decisions include REQUESTED/APPROVED/REJECTED/BLOCKED entries
# (piping APPROVE instead of an empty line exercises the approve branch)
```

---

## Phase 4.5 — Streamlit prototype (the deliverable demo)

Run these in order. Each is one message in Cursor. Review the diff, then send the next one.

### S0 — Prerequisites (do this before writing any app code)
```
Setup, no app code yet:
- Confirm Python 3.10+ (`python --version`); if the project already exists, open it as-is
  (do not overwrite existing files), otherwise create the project folder.
- requirements.txt: streamlit, pandas, scikit-learn, python-dotenv.
- Run `pip install -r requirements.txt`.
- Run `python -m src.run_all --weeks 12` and confirm it creates outputs/insights.json,
  outputs/weekly_pulse.md and outputs/fee_explainer.md with no errors and with no API key.
If anything fails, fix the pipeline first — the app only renders what the pipeline produces.
```

### S1 — Entry point: imports, page config, env
```
Create app.py with a module docstring describing the flow, then:
- `from __future__ import annotations`; import json, date, Path, pandas, streamlit.
- Load .env defensively: `try: from dotenv import load_dotenv; load_dotenv() except Exception: pass`.
- Import src modules (cluster, config, fee_explainer, ingest, insights, llm, pulse, retrieval)
  and the mcp_tools helpers (ApprovalGate, append_to_notes, build_email_body,
  build_note_entry, create_email_draft, email_subject).
- st.set_page_config(page_title="Groww — Review Insights Analyser", page_icon="📈", layout="wide").
- Call config.ensure_dirs() so output folders exist.
- Inject a small dependency-free style block (st.markdown with unsafe_allow_html) that trims
  the container's top padding and gives st.metric a rounded border (style via stable
  `[data-testid="stMetric"]` hooks only).
Do NOT call the pipeline at import time. No network calls on load.
```

### S2 — Session state + approval gate
```
Add a small state block right after set_page_config:
- st.session_state.setdefault("gate", ApprovalGate())
- st.session_state.setdefault("results", None)
- st.session_state.setdefault("action_results", None)
- Bind `gate = st.session_state.gate`.
Rationale (add as a comment): the gate must persist across Streamlit reruns, otherwise an
approved token would be lost and the MCP tools would refuse to run.
```

### S3 — Pipeline helper
```
Add run_pipeline(df, weeks) -> dict that calls, in order:
  cluster_mod.run(df) -> insights_mod.run(df, weeks) -> retrieval.run(df, fee_label)
  -> pulse.run(ins, ctx) -> fee_explainer.run(ins, ctx)
Return {"df":..., "insights":..., "context":..., "pulse":..., "explainer":...}.
It must reuse the existing src functions only — no logic duplicated in the app.
Add an optional `progress=None` callback; after each stage call `progress("<message>")`
(guard for None) so the UI can stream step-by-step updates — e.g. themed cluster count,
top themes, retrieved context count, pulse word count vs config.MAX_PULSE_WORDS, and
bullet count vs config.MAX_EXPLAINER_BULLETS.
```

### S4 — Sidebar (source, window, run button, LLM status)
```
Add `with st.sidebar:`:
- Title "📈 Groww — M5" + one-line caption of the flow.
- st.file_uploader("Upload a public reviews CSV", type=["csv"]) and a caption naming the
  default sample file.
- st.slider("Look-back window (weeks)", 4, 16, config.WEEKS).
- st.button("▶ Run analysis", type="primary", use_container_width=True) -> run_clicked.
- LLM status: if llm.available() -> st.success("Gemini key detected — live text.") else
  st.info("No GEMINI_API_KEY → deterministic offline writer (all constraints still met).").
- A caption showing the outputs folder and the approval log path.
- A `st.button("♻️ Reset demo artifacts", use_container_width=True)` that calls
  `clear_demo_artifacts()` — defined next to `run_pipeline()`, it deletes
  `config.NOTES_MD`, `NOTES_JSON`, `EMAIL_EML`, `EMAIL_MD` and `APPROVAL_LOG` and returns
  the names removed. On click, also reset `st.session_state.gate` to a fresh
  `ApprovalGate()` and `st.session_state.results`/`action_results` to `None`, then show
  `st.success(f"Reset — removed {len(removed)} file(s). Run analysis again to rebuild.")`.
```

### S5 — Run handler
```
Handle run_clicked inside a live status panel (NOT a single st.spinner):
`with st.status("Running analysis…", expanded=True) as status:` and a try/except:
- If a file was uploaded, save its bytes to data/raw/uploaded_reviews.csv and call
  ingest.load_reviews(that_path, weeks); otherwise ingest.load_reviews(config.SAMPLE_REVIEWS, weeks).
  Then st.write a "✅ Ingested <src> — N reviews kept (M PII redactions)" line.
- st.session_state.results = run_pipeline(df, weeks, progress=st.write) so each stage
  streams a line into the panel; reset st.session_state.action_results = None.
- On success: status.update(label="Analysis complete ✅", state="complete", expanded=False).
- On failure: status.update(label="Pipeline failed", state="error", expanded=True) and
  st.error(f"Pipeline failed: {exc}").
Layout: render the page title ONCE as a black heading — `st.markdown('<h1 style="color:#000000;
margin:0 0 .35rem 0; font-weight:800;">📈 Groww — Review Insights Analyser</h1>',
unsafe_allow_html=True)` — before this handler, then create two fixed-position slots in
display order —
`header_slot = st.container()` then `status_slot = st.empty()`. Run the pipeline inside
`with status_slot.container(), st.status(...) as status:`. Later render the caption + metric
cards inside `with header_slot:`. Containers/slots render in creation order regardless of when
they are filled, so the progress panel sits BELOW the header/metric cards and ABOVE the tabs.
The progress panel is TRANSIENT: track a local `completed` flag, and after a successful run call
`status_slot.empty()` so the panel DISAPPEARS once results are ready (leave it visible on error
so the failure is readable). Do not duplicate the title in the landing or results branch.
```

### S6 — Landing (empty) state
```
app never runs before the pipeline has produced results:
- One-line summary of the flow (the page title is already rendered once, above this branch).
- st.columns(4) with "#### 1..4" cards: Review intelligence / Weekly pulse / Fee explainer /
  MCP gate.
- st.divider(), then st.columns([3, 2], gap="large"):
  * left: "How it works" numbered list (ingest -> clean+redact -> insights -> generate ->
    human-in-the-loop MCP) + an expander "Constraints enforced automatically" whose bullets
    read the limits from config (MAX_THEMES, TOP_THEMES, TOP_QUOTES, MAX_PULSE_WORDS,
    MAX_EXPLAINER_BULLETS, "no PII", "draft only", approval token).
  * right: "Sample data" — pd.read_csv(config.SAMPLE_REVIEWS).head(6) in a st.dataframe
    (height 250) + a caption with row count and store count, then st.info(
    "Pick a source in the sidebar and click **▶ Run analysis**.").
```

### S7 — Result unpacking + metric cards
```
After the guard, unpack:
  R = st.session_state.results
  ins, ctx, p, fx, df = R["insights"], R["context"], R["pulse"], R["explainer"], R["df"]
Then a title, a st.caption showing the window (ins["window_start"] → ins["window_end"]),
the source file and the writer (Gemini vs offline), and 4 metric columns (st.metric):
  Reviews Analysed = ins["total_reviews"]; Window = f"{ins['window_weeks']} wks";
  Avg Rating = f"{ins['avg_rating']} out of 5"; Fee Issue Evidence = ins["fee_issue"]["evidence_count"].
Keep "out of 5" inline in the value (no delta) so the Avg Rating box is the same height as the
other three.
```

### S8 — Tab container
```
Create the tab bar:
tabs = st.tabs(["🧭 Review Intelligence", "🗞️ Weekly Pulse", "💸 Fee Explainer",
                "🔐 MCP Approval", "📦 Deliverables"])
Everything below is written inside the matching `with tabs[i]:` block.
```

### S9 — Tab 1: Review Intelligence
```
Inside tabs[0]:
- Render the five section headings ("Themes (max 5)", "Reviews by rating", "Top 3 themes",
  "Real user quotes (verbatim, redacted)", "🎯 Recurring confusion / fee pain point") in black
  via a small `section_heading(text)` helper (st.markdown with
  `<h3 style="color:#000000">`).
- Theme scorecards: st.columns(3) of st.metric — one per ins["top_themes"], value =
  f"{count} reviews", delta = f"{share_pct:.0f}% of reviews" (delta_color "off").
- Then st.columns([3, 2], gap="large"):
  * left "Themes (max 5)": DataFrame from ins["theme_distribution"] plus a "top 3" column
    ("⭐" when the theme is in ins["top_themes"]), shown with st.dataframe and a
    st.column_config.ProgressColumn on "share_pct" (min 0, max 100, "%.0f%%").
  * right "Reviews by rating": df["rating"].value_counts().sort_index() with the index
    relabelled "N★", rendered with st.bar_chart(height 270).
- "Top 3 themes": for each of ins["top_themes"], render name + count + share + the meaning
  from config.THEME_MEANINGS.
- "Real user quotes": for each q in ins["top_quotes"], wrap the quote in a bordered
  container (st.container(border=True)) — the quote as a markdown blockquote plus a st.caption
  with filled/empty stars (★/☆), the week and the theme.
- Fee pain point: st.error(...) showing ins["fee_issue"]["label"] and evidence_count, plus
  the matched keywords. Then expanders for (a) evidence snippets, (b) the RAG context ctx
  as a dataframe, (c) the cleaned reviews df[["date","rating","theme","clean_text"]].
```

### S10 — Tab 2: Weekly Pulse
```
Inside tabs[1]:
- st.subheader("Weekly Product Pulse (one-page internal note)").
- st.caption showing the word count vs config.MAX_PULSE_WORDS and the writer
  ("Gemini" if p["llm"] else "offline").
- st.progress(min(1.0, p["word_count"] / config.MAX_PULSE_WORDS),
  text=f"{p['word_count']} / {config.MAX_PULSE_WORDS} words").
- st.markdown(p["markdown"]).
- A st.download_button for weekly_pulse.md.
- If p["word_count"] > config.MAX_PULSE_WORDS, show st.warning to trim before submitting.
```

### S11 — Tab 3: Fee Explainer
```
Inside tabs[2]:
- st.subheader(f"Fee Explainer — {fx['label']}").
- st.caption with the bullet count vs config.MAX_EXPLAINER_BULLETS, "facts-only", and
  the "Last checked" date.
- st.progress(min(1.0, len(fx["bullets"]) / config.MAX_EXPLAINER_BULLETS),
  text=f"{len(fx['bullets'])} / {config.MAX_EXPLAINER_BULLETS} bullets").
- st.markdown(fx["markdown"]).
- A st.download_button for fee_explainer.md.
```

### S12 — Tab 4: MCP approval gate (the important one)
```
Inside tabs[3]:
- Build the payload: entry = build_note_entry(ins, p["markdown"], fx).
- subject = email_subject(); body = build_email_body(ins, p["markdown"], fx).
- Show the payload with st.json(entry) under a "1 · Append to Notes/Doc" heading, and the
  email subject + an expander with the body preview under "2 · Create email draft".
- Render EXACTLY two buttons in columns:
    c1.button("✅ Approve & Execute", type="primary")  and  c2.button("⛔ Reject").
- On Reject: gate.reject("append_to_notes", entry);
  gate.reject("create_email_draft", {"subject": subject, "body": body});
  st.session_state.action_results = {"rejected": True}.
- On Approve: gate.approve(...) for BOTH actions FIRST, then
  append_to_notes(entry, gate) and create_email_draft(subject, body, gate);
  store both result dicts in st.session_state.action_results.
- Render the outcome: warning if rejected, else st.success + st.json of each result +
  download buttons for notes_doc.md and email_draft.eml.
- Show the last 8 lines of mcp/approval_log.jsonl in st.code(language="json").
- Add a caption stating the guard rail: the tools call gate.require() first and raise
  approval_required if no approved token exists, so they can never act unattended.
```

### S13 — Tab 5: Deliverables + compliance checklist
```
Inside tabs[4]:
- A markdown table mapping every deliverable to its file path (prototype, weekly pulse,
  notes entry, email draft, reviews CSV, sources, README).
- Download buttons for weekly_pulse.md, fee_explainer.md and the reviews sample CSV.
- A compliance checklist dict rendered with ✅/⚠️:
  <=5 themes, pulse <=250 words, exactly 3 quotes, explainer <=6 bullets, 2 source links,
  "Last checked" present, approval gate present, email is draft only.
```

### S14 — Footer + verification pass
```
Add a footer caption with the generation timestamp, the source file, and "no PII in any artifact".
Then verify the prototype end to end and report a table Requirement | Status | Evidence:
- `streamlit run app.py` boots with no traceback (it should return HTTP 200 on localhost).
- Sample CSV works with NO api key.
- Run analysis fills all tabs.
- MCP Approval -> Approve & Execute writes outputs/notes_doc.md, outputs/notes_log.json,
  outputs/email_draft.eml/.md and appends to mcp/approval_log.jsonl.
- MCP Approval -> Reject writes nothing.
- Pipeline with an empty/short CSV does not crash the app (st.error shown).
Fix any failures, then print the exact commands I should run.
```

---

## Phase 5 — Packaging & deliverables

### P11 — README
```
Write README.md for the submission with these sections:
- Project title + product (Groww) + one-line summary, and note it covers BOTH briefs (RAGs & Context Engineering + App Review Insights Analyser)
- Architecture diagram (ASCII): CSV -> clean/redact -> cluster -> insights -> RAG retrieve -> pulse + fee explainer -> MCP approval -> Doc + Gmail draft
- Repo layout (brief)
- How to run: pip install -r requirements.txt, copy .env.example (optional GEMINI_API_KEY), python -m src.run_all --weeks 12, streamlit run app.py, optional python mcp/server.py
- Where MCP approval happens (Streamlit button + gate.require() guard + terminal APPROVE) and what gets logged (mcp/approval_log.jsonl)
- What fee issue was identified from reviews (Exit Load on Mutual Fund Redemption) and why, with the sample counts
- Theme legend (the 5 themes + definition of each)
- How to re-run for a new week (replace CSV, one command, re-approve)
- Sample outputs + screenshot placeholders
- Source list (4-6 URLs)
- PII note: all reviews redacted, no usernames/emails/IDs; email is draft only
```

### P12 — Source list
```
Create docs/sources.md with 4-6 official, non-login URLs used for the fee explainer. Include for each: name, URL, what it supports, date checked. Cover AMFI (exit load), SEBI (investor education / TER & charges), Groww official pricing/charges page, and one exchange investor-education page. Mark "Last checked: <today>".
```

### P13 — Demo script + video plan (<=3 min)
```
Create docs/demo_script.md: a <=3 minute spoken walkthrough. Beats:
0:00 problem (Groww users confused about fees)
0:20 show CSV + redaction
0:40 show themes + top 3
1:00 show weekly pulse (<=250 words)
1:20 show fee explainer + sources
1:40 trigger MCP, show APPROVE prompt
2:00 show appended doc entry + Gmail draft screenshot
2:30 re-run for a new week (one command)
Include exact on-screen clicks.
```

### P14 — Final QA pass
```
Act as a strict reviewer against the milestone checklist. Read outputs/weekly_pulse.md and outputs/fee_explainer.md and verify:
- <=250 words in pulse, exactly 3 themes, 3 real quotes, 3 actions
- fee explainer <=6 bullets, 2 source links, "Last checked:" present, facts-only tone
- no PII anywhere
- MCP has an approval step with a log
Return a table: Requirement | Status | Evidence | Fix (if any). Fix any failures automatically and re-check.
```

---

## Quick reference — what each output must contain

| Artifact | Constraint |
|---|---|
| themes | max 5, top 3 highlighted |
| quotes | 3, verbatim, redacted |
| weekly pulse / one-page note | <= 250 words, structured |
| fee explainer | <= 6 bullets, 2 official links, "Last checked:" |
| MCP | approval before any write |
| doc entry | date, top_themes, weekly_pulse, fee_issue, bullets, links |
| email | DRAFT only, never sent |
| prototype | `streamlit run app.py`, works with no API key |
| PII | none in any artifact (redacted before processing) |
| re-run | new CSV + one command (`python -m src.run_all`) |
| theme legend | 5 themes, defined in README |

---

## Phase 6 — Host on Streamlit Community Cloud (optional)

### P15 — Publish a public URL
```
Yes — the local http://localhost:8501 URL can become a permanent Streamlit URL. Do:

Code prep:
- Add requirements-cloud.txt: `-r requirements.txt` plus `google-genai>=0.3` (so live
  Gemini text works on Cloud; locally Gemini stays optional).
- Add .streamlit/config.toml (primaryColor "#FF7A00", backgroundColor "#FFFFFF" -> white tab
  panels, secondaryBackgroundColor "#F0F0F0" -> light-grey sidebar, textColor "#000000") and
  [browser] gatherUsageStats = false. In app.py the main page heading and body/data text stay
  black for readability. The sidebar background is light grey and its title ("📈 Groww — M5") and
  section headers ("1 · Reviews source", "2 · LLM") are black; the sidebar LLM status
  "Gemini key detected — live text." is green (#0F9D58) via
  [data-testid="stAlertContentSuccess"].
- Add .gitignore excluding .env, .streamlit/secrets.toml, __pycache__/, data/raw/*.csv
  (may contain PII) and generated logs (outputs/*.jsonl, mcp/approval_log.jsonl).
- In app.py, right after load_dotenv(), bridge Streamlit secrets into the environment:
  for each of GEMINI_API_KEY / GEMINI_MODEL, if not already in os.environ and present in
  st.secrets, copy it into os.environ (wrap in try/except). This lets src.llm, which reads
  os.environ, work on Cloud where secrets arrive via st.secrets.
- Write docs/deploy_streamlit_cloud.md with the exact steps below.

Deploy (the owner does these — they need their own accounts):
1. Push the repo to GitHub: git init; git add .; git commit -m "..."; create an EMPTY repo;
   git remote add origin https://github.com/<user>/<repo>.git; git push -u origin main.
2. On share.streamlit.io -> Create app -> "Deploy a public app from GitHub" -> pick the
   repo + branch main, Main file path = app.py.
- Advanced settings: Python 3.11; Requirements file = requirements-cloud.txt; Secrets:
  GEMINI_API_KEY = "...". (No key? the app still runs with the offline writer.)
- Deploy -> you get https://<name>.streamlit.app. Reboot the app after changing
  requirements/secrets.

Caveat to state in docs: the Cloud container has NO persistent disk, so outputs/ and
mcp/approval_log.jsonl reset on reboot/sleep, and all visitors share one instance — fine
for a demo, not for production.
```
