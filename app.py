"""Groww — Milestone 5 Review Insights Analyser (Streamlit prototype).

Run:  streamlit run app.py

Flow: CSV reviews -> clean + PII redact -> cluster (<=5 themes) -> insights
      (top 3 themes, 3 quotes, fee issue) -> RAG context -> weekly pulse (<=250w)
      + fee explainer (<=6 bullets, 2 sources) -> MCP approval gate -> Notes/Doc
      append + email DRAFT (never sent).
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# Streamlit Community Cloud exposes secrets via st.secrets (not .env). Mirror the LLM
# keys into the environment so src.llm — which reads os.environ — works there too.
try:
    for _key in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if _key not in os.environ and _key in st.secrets:
            os.environ[_key] = str(st.secrets[_key])
except Exception:
    pass

from src import cluster as cluster_mod
from src import config, fee_explainer, ingest, insights as insights_mod, llm, pulse, retrieval
from src.mcp_tools import (
    ApprovalGate,
    append_to_notes,
    build_email_body,
    build_note_entry,
    create_email_draft,
    email_subject,
)

st.set_page_config(page_title="Groww — Review Insights Analyser", page_icon="📈", layout="wide")
config.ensure_dirs()

# Light, dependency-free polish (stable data-testid hooks only).
st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem;}
      [data-testid="stMetric"] {
          border: 1px solid rgba(128,128,128,.25);
          border-radius: 12px;
          padding: .6rem .9rem;
      }
      [data-testid="stMetricValue"] {font-size: 1.45rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- state
# The gate MUST persist across Streamlit reruns — otherwise an approved token is
# lost on rerun and the MCP tools would refuse to run.
st.session_state.setdefault("gate", ApprovalGate())
st.session_state.setdefault("results", None)
st.session_state.setdefault("action_results", None)

gate: ApprovalGate = st.session_state.gate


# --------------------------------------------------------------------------- pipeline
def run_pipeline(df: pd.DataFrame, weeks: int) -> dict:
    df = cluster_mod.run(df)
    ins = insights_mod.run(df, weeks)
    ctx = retrieval.run(df, ins["fee_issue"]["label"])
    p = pulse.run(ins, ctx)
    fx = fee_explainer.run(ins, ctx)
    return {"df": df, "insights": ins, "context": ctx, "pulse": p, "explainer": fx}


# --------------------------------------------------------------------------- reset
# One-click demo reset. Clears ONLY the human-approved artifacts (notes/email) and the
# audit log — the pipeline outputs (insights/pulse/explainer) stay until you re-run.
DEMO_ARTIFACTS = (
    config.NOTES_MD,
    config.NOTES_JSON,
    config.EMAIL_EML,
    config.EMAIL_MD,
    config.APPROVAL_LOG,
)


def clear_demo_artifacts() -> list[str]:
    """Delete the notes/email outputs + the approval log; return the names removed."""
    removed: list[str] = []
    for path in DEMO_ARTIFACTS:
        try:
            if path.exists():
                path.unlink()
                removed.append(path.name)
        except OSError:
            pass
    return removed


# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("📈 Groww — M5")
    st.caption("Reviews → Insights → Pulse + Fee Explainer → MCP (approved)")

    st.subheader("1 · Reviews source")
    uploaded = st.file_uploader("Upload a public reviews CSV", type=["csv"])
    st.caption(f"Default sample: `{config.SAMPLE_REVIEWS.name}`")

    weeks = st.slider("Look-back window (weeks)", 4, 16, config.WEEKS)

    run_clicked = st.button("▶ Run analysis", type="primary", use_container_width=True)

    st.divider()
    st.subheader("2 · LLM")
    if llm.available():
        st.success("Gemini key detected — live text.")
    else:
        st.info("No GEMINI_API_KEY → deterministic offline writer (all constraints still met).")

    st.divider()
    st.caption(f"Outputs → `{config.OUTPUTS_DIR.name}/`  ·  Approval log → `mcp/approval_log.jsonl`")

    if st.button("♻️ Reset demo artifacts", use_container_width=True,
                 help="Clears notes_doc/notes_log + email_draft + the approval log. "
                      "Pipeline outputs (pulse/explainer) stay until you re-run."):
        removed = clear_demo_artifacts()
        st.session_state.gate = ApprovalGate()
        st.session_state.results = None
        st.session_state.action_results = None
        st.success(f"Reset — removed {len(removed)} file(s). Run analysis again to rebuild.")

if run_clicked:
    with st.spinner("Running ingest → cluster → insights → retrieve → pulse → explainer…"):
        try:
            if uploaded is not None:
                config.RAW_DIR.mkdir(parents=True, exist_ok=True)
                up = config.RAW_DIR / "uploaded_reviews.csv"
                up.write_bytes(uploaded.getbuffer())
                df = ingest.load_reviews(up, weeks)
            else:
                df = ingest.load_reviews(config.SAMPLE_REVIEWS, weeks)
            st.session_state.results = run_pipeline(df, weeks)
            st.session_state.action_results = None
        except Exception as exc:  # noqa: BLE001
            st.error(f"Pipeline failed: {exc}")

if st.session_state.results is None:
    st.title("📈 Groww — Review Insights Analyser")
    st.markdown(
        "Turn the last **8–12 weeks** of App Store + Play Store reviews into a **weekly product "
        "pulse** and a **customer-facing fee explainer** — then log them through an **MCP approval gate**."
    )

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown("#### 1 · Review intelligence\n\n≤5 themes · top 3 · 3 real quotes · the fee pain point")
    s2.markdown("#### 2 · Weekly pulse\n\nA ≤250-word one-page internal note")
    s3.markdown("#### 3 · Fee explainer\n\n≤6 facts-only bullets + 2 official links")
    s4.markdown("#### 4 · MCP gate\n\nHuman approval → Notes/Doc append + email **draft**")

    st.divider()
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("How it works")
        st.markdown(
            "1. **Ingest** the sample CSV — or upload your own public reviews export.\n"
            "2. **Clean + redact PII**, then cluster into **≤5 themes**.\n"
            "3. **Extract insights**: top 3 themes, 3 verbatim quotes, and the recurring fee pain point.\n"
            "4. **Generate** the weekly pulse and the fee explainer "
            "(Gemini when a key is set, else a deterministic offline writer).\n"
            "5. **Human-in-the-loop MCP**: nothing is written or emailed until you click **Approve & Execute**."
        )
        with st.expander("Constraints enforced automatically", expanded=True):
            st.markdown(
                f"- ≤ **{config.MAX_THEMES}** themes (top **{config.TOP_THEMES}** highlighted)\n"
                f"- exactly **{config.TOP_QUOTES}** verbatim quotes\n"
                f"- pulse ≤ **{config.MAX_PULSE_WORDS}** words\n"
                f"- fee explainer ≤ **{config.MAX_EXPLAINER_BULLETS}** bullets + **2** official links + “Last checked:”\n"
                "- **no PII** in any artifact · the email is a **draft only** (never sent)\n"
                "- every MCP action needs an explicit **human approval** token"
            )
    with right:
        st.subheader("Sample data")
        if config.SAMPLE_REVIEWS.exists():
            try:
                preview = pd.read_csv(config.SAMPLE_REVIEWS)
                st.dataframe(preview.head(6), hide_index=True, use_container_width=True, height=250)
                n_sources = preview["source"].nunique() if "source" in preview.columns else "?"
                st.caption(f"`{config.SAMPLE_REVIEWS.name}` — {len(preview)} rows · {n_sources} stores")
            except Exception:  # noqa: BLE001
                st.caption("Preview unavailable.")
        st.info("Pick a source in the sidebar and click **▶ Run analysis**.")

    st.stop()

R = st.session_state.results
ins, ctx, p, fx, df = R["insights"], R["context"], R["pulse"], R["explainer"], R["df"]

# --------------------------------------------------------------------------- header
st.title("Groww — Review Insights Analyser")
st.caption(
    f"Window **{ins['window_start']} → {ins['window_end']}** · source `{ins.get('source_file', 'n/a')}` · "
    f"writer: **{'Gemini' if p['llm'] else 'offline'}**"
)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Reviews analysed", ins["total_reviews"])
k2.metric("Window", f"{ins['window_weeks']} wks")
k3.metric("Avg rating", ins["avg_rating"], "out of 5", delta_color="off")
k4.metric("Fee issue evidence", ins["fee_issue"]["evidence_count"])

tabs = st.tabs(
    ["🧭 Review Intelligence", "🗞️ Weekly Pulse", "💸 Fee Explainer", "🔐 MCP Approval", "📦 Deliverables"]
)

# --------------------------------------------------------------------------- tab 1
with tabs[0]:
    dist = pd.DataFrame(ins["theme_distribution"])

    top = st.columns(3)
    for col, t in zip(top, ins["top_themes"]):
        row = next((d for d in ins["theme_distribution"] if d["theme"] == t), None)
        if row:
            col.metric(f"⭐ {t}", f"{row['count']} reviews",
                       f"{row['share_pct']:.0f}% of reviews", delta_color="off")

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Themes (max 5)")
        show = dist.assign(**{"top 3": dist["theme"].isin(ins["top_themes"]).map({True: "⭐", False: ""})})
        st.dataframe(
            show,
            hide_index=True,
            use_container_width=True,
            column_config={
                "share_pct": st.column_config.ProgressColumn(
                    "share %", min_value=0, max_value=100, format="%.0f%%"
                ),
            },
        )
    with right:
        st.subheader("Reviews by rating")
        rc = df["rating"].value_counts().sort_index()
        rc.index = [f"{int(r)}★" for r in rc.index]
        st.bar_chart(rc, height=270)

    st.subheader("Top 3 themes")
    for i, t in enumerate(ins["top_themes"], 1):
        row = next(d for d in ins["theme_distribution"] if d["theme"] == t)
        st.markdown(f"**{i}. {t}** — {row['count']} reviews ({row['share_pct']:.0f}%)  \n_{config.THEME_MEANINGS.get(t, '')}_")

    st.subheader("Real user quotes (verbatim, redacted)")
    for q in ins["top_quotes"]:
        with st.container(border=True):
            st.markdown(f"> {q['text']}")
            stars = "★" * int(q["rating"]) + "☆" * (5 - int(q["rating"]))
            st.caption(f"{stars} · {q['week']} · theme: {q['theme']}")

    st.subheader("🎯 Recurring confusion / fee pain point")
    fee = ins["fee_issue"]
    st.error(
        f"**{fee['label']}** — detected in **{fee['evidence_count']}** reviews.\n\n"
        f"Matched signals: {', '.join(fee['matched_keywords']) or 'n/a'}"
    )
    with st.expander("Evidence snippets"):
        for s in fee["sample_snippets"]:
            st.markdown(f"- {s}")

    with st.expander("RAG context retrieved for the fee issue (grounds the generated text)"):
        st.dataframe(pd.DataFrame(ctx), hide_index=True, use_container_width=True)

    with st.expander("Reviews kept after cleaning (PII-redacted)"):
        st.dataframe(
            df[["date", "rating", "theme", "clean_text"]],
            hide_index=True,
            use_container_width=True,
        )

# --------------------------------------------------------------------------- tab 2
with tabs[1]:
    st.subheader("Weekly Product Pulse (one-page internal note)")
    st.caption(f"Word count: **{p['word_count']} / {config.MAX_PULSE_WORDS}** · writer: {'Gemini' if p['llm'] else 'offline'}")
    st.progress(min(1.0, p["word_count"] / config.MAX_PULSE_WORDS),
                text=f"{p['word_count']} / {config.MAX_PULSE_WORDS} words")
    st.markdown(p["markdown"])
    st.download_button("⬇ Download weekly_pulse.md", p["markdown"], file_name="weekly_pulse.md")
    if p["word_count"] > config.MAX_PULSE_WORDS:
        st.warning("Over the 250-word cap — trim before submitting.")

# --------------------------------------------------------------------------- tab 3
with tabs[2]:
    st.subheader(f"Fee Explainer — {fx['label']}")
    st.caption(f"{len(fx['bullets'])} bullets (max {config.MAX_EXPLAINER_BULLETS}) · facts-only · Last checked: {fx['last_checked']}")
    st.progress(min(1.0, len(fx["bullets"]) / config.MAX_EXPLAINER_BULLETS),
                text=f"{len(fx['bullets'])} / {config.MAX_EXPLAINER_BULLETS} bullets")
    st.markdown(fx["markdown"])
    st.download_button("⬇ Download fee_explainer.md", fx["markdown"], file_name="fee_explainer.md")

# --------------------------------------------------------------------------- tab 4
with tabs[3]:
    st.subheader("MCP actions — nothing runs without your approval")
    entry = build_note_entry(ins, p["markdown"], fx)
    subject = email_subject()
    body = build_email_body(ins, p["markdown"], fx)

    a_token = gate.token_for("append_to_notes", entry)
    e_token = gate.token_for("create_email_draft", {"subject": subject, "body": body})

    st.markdown("**1 · Append to Notes/Doc** — payload:")
    st.json(entry)
    st.markdown(f"**2 · Create email draft** — subject: `{subject}`")
    with st.expander("Email body preview"):
        st.markdown(body)

    c1, c2, _ = st.columns([1, 1, 2])
    approve = c1.button("✅ Approve & Execute", type="primary", use_container_width=True)
    reject = c2.button("⛔ Reject", use_container_width=True)

    if reject:
        gate.reject("append_to_notes", entry)
        gate.reject("create_email_draft", {"subject": subject, "body": body})
        st.session_state.action_results = {"rejected": True}

    if approve:
        # the human click IS the approval -> issue tokens, then the tools run
        gate.approve("append_to_notes", entry)
        gate.approve("create_email_draft", {"subject": subject, "body": body})
        res_note = append_to_notes(entry, gate)
        res_mail = create_email_draft(subject, body, gate)
        st.session_state.action_results = {"note": res_note, "mail": res_mail}

    res = st.session_state.action_results
    if res and res.get("rejected"):
        st.warning("Rejected. No doc entry and no email draft were created.")
    elif res:
        st.success("Approved. Both MCP actions completed.")
        st.write("**Notes/Doc append**")
        st.json(res["note"])
        st.write("**Email draft (not sent)**")
        st.json(res["mail"])
        st.download_button("⬇ notes_doc.md", config.NOTES_MD.read_text(encoding="utf-8"), file_name="notes_doc.md")
        st.download_button("⬇ email_draft.eml", config.EMAIL_EML.read_text(encoding="utf-8"), file_name="email_draft.eml")

    st.divider()
    st.caption("Approval log (mcp/approval_log.jsonl)")
    if config.APPROVAL_LOG.exists():
        lines = config.APPROVAL_LOG.read_text(encoding="utf-8").strip().splitlines()[-8:]
        st.code("\n".join(lines) or "(empty)", language="json")
    else:
        st.code("(no decisions logged yet)")

    st.caption(
        "Guard rail: `append_to_notes` / `create_email_draft` call `gate.require(...)` first and "
        "raise `approval_required` if no approved token exists — so the tools can never act unattended."
    )

# --------------------------------------------------------------------------- tab 5
with tabs[4]:
    st.subheader("Submission deliverables")
    st.markdown(
        """
| # | Deliverable | Where |
|---|---|---|
| 1 | Prototype (this app) / ≤3-min demo | `streamlit run app.py` + `docs/demo_script.md` |
| 2 | Weekly product pulse (one-page note) | `outputs/weekly_pulse.md` |
| 3 | Notes/Doc entry snippet | `outputs/notes_doc.md`, `outputs/notes_log.json` |
| 4 | Email draft | `outputs/email_draft.eml`, `outputs/email_draft.md` |
| 5 | Reviews CSV sample | `data/groww_reviews_sample.csv` |
| 6 | Source list (4–6 URLs) | `docs/sources.md` |
| 7 | README (run + approval + fee issue) | `README.md` |
"""
    )
    st.markdown("**Downloads**")
    cols = st.columns(3)
    if config.PULSE_MD.exists():
        cols[0].download_button("weekly_pulse.md", config.PULSE_MD.read_text(encoding="utf-8"), file_name="weekly_pulse.md")
    if config.EXPLAINER_MD.exists():
        cols[1].download_button("fee_explainer.md", config.EXPLAINER_MD.read_text(encoding="utf-8"), file_name="fee_explainer.md")
    if config.SAMPLE_REVIEWS.exists():
        cols[2].download_button("reviews sample CSV", config.SAMPLE_REVIEWS.read_text(encoding="utf-8"), file_name="groww_reviews_sample.csv")

    st.markdown("**Compliance checklist**")
    ok = {
        "≤5 themes": len(ins["theme_distribution"]) <= config.MAX_THEMES,
        "Pulse ≤250 words": p["word_count"] <= config.MAX_PULSE_WORDS,
        "Exactly 3 quotes": len(ins["top_quotes"]) == config.TOP_QUOTES,
        "Explainer ≤6 bullets": len(fx["bullets"]) <= config.MAX_EXPLAINER_BULLETS,
        "2 official source links": len(fx["sources"]) == 2,
        "\"Last checked\" present": "Last checked:" in fx["markdown"],
        "Approval gate present": True,
        "Email is draft only": True,
    }
    for k, v in ok.items():
        st.markdown(f"{'✅' if v else '⚠️'} {k}")

st.caption(f"Generated {ins['generated_at'][:19]}Z · source: {ins.get('source_file')} · no PII in any artifact.")
