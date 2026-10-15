"""Real MCP server (stdio) exposing the two approval-gated tools.

Requires:  pip install mcp
Run:       python mcp/server.py

MCP tools are DESTRUCTIVE and must only be called AFTER explicit human approval.
This server mirrors the local (mock) tools in src/mcp_tools.py, so you can demo
the prototype with zero external accounts, and switch to real MCP when ready.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.mcp_tools import ApprovalGate, append_to_notes, create_email_draft  # noqa: E402

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    print(
        "The 'mcp' package is not installed.\n"
        "Install it with:  pip install mcp\n"
        "The Streamlit prototype does not need it — it uses src/mcp_tools.py directly.",
        file=sys.stderr,
    )
    raise SystemExit(1)

mcp = FastMCP("groww-review-insights")
_gate = ApprovalGate()


@mcp.tool()
def read_pending_batch() -> dict:
    """Read the generated pulse/explainer/insights JSON awaiting submission."""
    out: dict = {}
    for key, path in (
        ("pulse", config.PULSE_JSON),
        ("explainer", config.EXPLAINER_JSON),
        ("insights", config.INSIGHTS_JSON),
    ):
        if path.exists():
            out[key] = json.loads(path.read_text(encoding="utf-8"))
    return out


@mcp.tool()
def request_approval(action: str, payload: dict) -> dict:
    """Step 1 of the gate: register the request and return a preview token."""
    token = _gate.request(action, payload)
    return {"token": token, "status": "awaiting_approval", "action": action}


@mcp.tool()
def grant_approval(action: str, payload: dict, approver: str = "human") -> dict:
    """Step 2 of the gate: the human approves. Required before any write."""
    token = _gate.approve(action, payload, approver=approver)
    return {"token": token, "status": "approved"}


@mcp.tool()
def append_weekly_entry(payload: dict) -> dict:
    """Append {date, top_themes, weekly_pulse, identified_fee_issue,
    explanation_bullets, source_links} to the Notes/Doc. Approval-gated."""
    return append_to_notes(payload, _gate)


@mcp.tool()
def create_email_draft_tool(subject: str, body: str) -> dict:
    """Create a Gmail DRAFT (never sends). Approval-gated."""
    return create_email_draft(subject, body, _gate)


if __name__ == "__main__":
    print("Groww Review Insights — MCP server (stdio)")
    for name, desc in [
        ("read_pending_batch", "read generated artifacts"),
        ("request_approval", "register an approval request"),
        ("grant_approval", "human approves a request"),
        ("append_weekly_entry", "append entry to Notes/Doc (gated)"),
        ("create_email_draft_tool", "create email draft (gated)"),
    ]:
        print(f"  - {name}: {desc}")
    mcp.run()
