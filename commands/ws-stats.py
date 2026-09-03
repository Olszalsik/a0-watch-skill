"""Slash-command script for /ws-stats (see watch.py for the run(payload)
contract)."""

from __future__ import annotations


def run(payload: dict) -> dict:
    text = (
        "Use the ws_stats tool and report the watch-skill engine statistics: "
        "videos indexed, questions answered, and the lifetime token-savings "
        "meter."
    )
    return {"text": text, "effects": [{"type": "send_message", "text": text}]}