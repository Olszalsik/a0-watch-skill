"""Slash-command script for /ws-library (see watch.py for the run(payload)
contract)."""

from __future__ import annotations


def run(payload: dict) -> dict:
    arguments = (payload or {}).get("arguments", {}) or {}
    raw = str(arguments.get("raw", "") or "").strip()

    if raw:
        text = (
            f"Use the ws_library tool to answer, with references to specific "
            f"videos and timestamps: {raw}"
        )
    else:
        text = (
            "Use the ws_library tool (overview mode) and summarize my video "
            "library: how many videos are indexed, total hours, note counts, "
            "and the most recently added videos."
        )

    return {"text": text, "effects": [{"type": "send_message", "text": text}]}