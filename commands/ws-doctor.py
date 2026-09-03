"""Slash-command script for /ws-doctor (see watch.py for the run(payload)
contract)."""

from __future__ import annotations


def run(payload: dict) -> dict:
    arguments = (payload or {}).get("arguments", {}) or {}
    flags = arguments.get("flags", {}) or {}
    no_fix = bool(flags.get("no-fix") or flags.get("no_fix"))

    if no_fix:
        text = (
            "Run the ws_doctor tool (no fixes): report the health status of "
            "the watch-skill engine only, do not download anything."
        )
    else:
        text = (
            "Run the ws_doctor tool with fix=true: check the watch-skill "
            "engine (ffmpeg, yt-dlp, transcription deps) and apply its safe "
            "self-heals, then report what was fixed."
        )

    return {"text": text, "effects": [{"type": "send_message", "text": text}]}