"""Slash-command script for /watch.

Contract (plugins/_commands/helpers/commands.py::_run_script_command): the
script is executed via runpy.run_path and must expose `run(payload)`. It
returns `{"text": ..., "effects": [...]}`; the `send_message` effect puts
the rendered prompt into the chat input and sends it, so the agent runs the
ws_* tools itself (commands never shell out to the CLI directly).

payload["arguments"] = {"raw": str, "tokens": [...], "positional": [...],
"flags": {...}} (parse_arguments()).
"""

from __future__ import annotations

_INSTALL_LINE = (
    "uv tool install "
    "'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'"
)


def run(payload: dict) -> dict:
    arguments = (payload or {}).get("arguments", {}) or {}
    raw = str(arguments.get("raw", "") or "").strip()
    positional = arguments.get("positional", []) or []

    if not raw:
        return {
            "text": f"/watch <video url or path> [question...]",
            "effects": [
                {
                    "type": "toast",
                    "level": "error",
                    "message": "Usage: /watch <video url or path> [question...]",
                }
            ],
        }

    video = str(positional[0] or "").strip() if positional else raw
    question = " ".join(str(p) for p in positional[1:]).strip()

    if question:
        text = (
            f"Watch the video `{video}` with the ws_watch / ws_ask tools and "
            f"answer: {question}\n\n"
            f"Cite timestamps for every claim. If a tool fails with a "
            f"dependency error, run ws_doctor with fix=true first."
        )
    else:
        text = (
            f"Watch the video `{video}` with the ws_watch tool (summarize it), "
            f"then give me a timeline of the main moments with timestamps.\n\n"
            f"If the tool fails with a dependency error, run ws_doctor with "
            f"fix=true first. If the CLI itself is missing, tell me to run: "
            f"`{_INSTALL_LINE}`"
        )

    return {"text": text, "effects": [{"type": "send_message", "text": text}]}