# Demo Script — Groww Review Insights Analyser (≤3 min)

Record with the Streamlit app already running: `streamlit run app.py`

| Time | On screen | Say |
|---|---|---|
| 0:00 | Title / landing screen | "Groww users are confused about charges they see only *after* they redeem. This turns raw reviews into a weekly pulse and a clear fee explainer." |
| 0:15 | Sidebar → pick sample CSV → window 12 weeks | "Reviews come from a public export. The window is the last 12 weeks." |
| 0:25 | Click **▶ Run analysis** | "One click runs ingest, PII redaction, clustering, insight extraction, retrieval and generation." |
| 0:40 | **Review Intelligence** tab | "Five themes max. Clustering found these; top three are highlighted." |
| 0:55 | Same tab → quotes | "Three real, verbatim, redacted quotes — the model cannot invent quotes, they come from the CSV." |
| 1:05 | Same tab → Fee pain point (red box) | "The recurring pain point: exit load. It shows up in N reviews — users see a lower credited amount than the value displayed." |
| 1:20 | Open **RAG context** expander | "This is the context engineering: only these retrieved reviews are passed to the model." |
| 1:35 | **Weekly Pulse** tab | "The one-page weekly note — under 250 words: themes, quotes, one observation, three action ideas." |
| 1:50 | **Fee Explainer** tab | "Six bullets, facts-only, two official sources, 'Last checked' date." |
| 2:05 | **MCP Approval** tab | "Nothing has been written yet. Here is the exact payload." |
| 2:15 | Click **✅ Approve & Execute** | "The click is the human approval. Only now do the MCP tools run." |
| 2:25 | Result cards + approval log | "The entry is appended to the Notes/Doc and an email draft is created — draft only, never sent. Every decision is logged." |
| 2:40 | **Deliverables** tab | "Compliance checklist is green: ≤5 themes, ≤250 words, 3 quotes, ≤6 bullets, 2 sources, approval gate." |
| 2:50 | Terminal: `python -m src.run_all --weeks 12` | "For a new week, drop the new export in `data/` and re-run one command." |

## Tips
- Have `outputs/notes_doc.md` and `outputs/email_draft.eml` open in a second window to show the artifacts.
- If asked "is this real MCP?" → the app uses `src/mcp_tools.py` (mirrors the MCP tools). `mcp/server.py`
  exposes the same tools over the real MCP stdio protocol (`pip install mcp`).
