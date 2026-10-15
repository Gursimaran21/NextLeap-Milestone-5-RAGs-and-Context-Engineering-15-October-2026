"""CLI approval gate used by the standalone (non-Streamlit) workflow.

Typing APPROVE here is the human-in-the-loop step. Nothing is written unless
the user types APPROVE.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config  # noqa: E402
from src.mcp_tools import ApprovalGate  # noqa: E402


def preview(action: str, payload: dict, limit: int = 2000) -> None:
    print("\n" + "=" * 70)
    print(f"APPROVAL REQUIRED — action: {action}")
    print("=" * 70)
    blob = json.dumps(payload, indent=2, default=str)
    print(blob[:limit] + ("\n... (truncated)" if len(blob) > limit else ""))
    print("=" * 70)


def approve_interactive(action: str, payload: dict, gate: ApprovalGate) -> bool:
    preview(action, payload)
    answer = input(f"Type APPROVE to run '{action}' (anything else = reject): ").strip()
    if answer == "APPROVE":
        gate.approve(action, payload, approver="terminal_user")
        print("Approved. Proceeding.")
        return True
    gate.reject(action, payload, approver="terminal_user")
    print("Rejected. No action taken.")
    return False


if __name__ == "__main__":
    gate = ApprovalGate()
    demo = {
        "action": "append_to_notes",
        "payload": {
            "date": "2026-10-14",
            "top_themes": config.TOP_THEMES if isinstance(config.TOP_THEMES, list) else [],
            "note": "Run via src/run_all.py for the real payload.",
        },
    }
    ok = approve_interactive(demo["action"], demo["payload"], gate)
    print(f"decision logged to {config.APPROVAL_LOG} | approved={ok}")
