"""Thin LLM wrapper.

If GEMINI_API_KEY is set (and google-genai is installed) we call Gemini.
Otherwise `generate()` returns None and callers use their deterministic writer,
so the prototype always runs — even with no API key and no internet.
"""

from __future__ import annotations

import os

from . import config

_client = None
_working_model: str | None = None
_last_used_llm = False

# Tried in order; the first one that responds is cached for the session.
_MODEL_CANDIDATES: list[str] = [
    os.getenv("GEMINI_MODEL", "").strip(),
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


def _candidates() -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _MODEL_CANDIDATES:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai  # google-genai
    except Exception:
        return None
    _client = genai.Client(api_key=api_key)
    return _client


def available() -> bool:
    return _get_client() is not None


def active_model() -> str:
    return _working_model or _candidates()[0]


def used() -> bool:
    """True if the most recent generate() call actually returned model text."""
    return _last_used_llm


def generate(system: str, prompt: str, temperature: float = 0.2) -> str | None:
    """Return model text, or None if no LLM is configured/reachable."""
    global _working_model, _last_used_llm
    _last_used_llm = False
    client = _get_client()
    if client is None:
        return None

    order = ([_working_model] if _working_model else []) + _candidates()
    last_error = ""
    for model in order:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config={"system_instruction": system, "temperature": temperature},
            )
            text = getattr(resp, "text", None)
            if text:
                _working_model = model
                _last_used_llm = True
                return text.strip()
        except Exception as exc:  # noqa: BLE001 — try the next model
            last_error = str(exc)
            continue

    if last_error:
        print(f"[llm] Gemini call failed ({last_error[:180]}); using offline writer.")
    return None
