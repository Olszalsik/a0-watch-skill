"""ws_moment — zoom into one specific moment of a watched video.

Wraps `watch-skill moment` (MCP twin: `get_moment`). Use after ws_ask or
ws_search when you need dense frames + transcript + OCR around a single
timestamp.

v1.1.0 re-port: extracted from ws_search.py — one Tool class per file.
"""

from __future__ import annotations

import asyncio

import importlib.util
import sys
from pathlib import Path

from helpers.tool import Response, Tool

_common_path = Path(__file__).resolve().parent / "_common.py"
_common_mtime = _common_path.stat().st_mtime
_ws_common = sys.modules.get("_watch_skill_common")
# v1.1.1: reuse the cached module only if _common.py has not changed since
# it was executed. Without this, a Hub/plugin update left running agents on
# the STALE cached module until a full server restart; and a module whose
# exec_module() raised mid-init stayed poisoned in sys.modules forever
# (no __ws_common_mtime__ attribute -> re-executed on the next load).
if _ws_common is not None and getattr(_ws_common, "__ws_common_mtime", None) != _common_mtime:
    _ws_common = None
if _ws_common is None:
    _spec = importlib.util.spec_from_file_location("_watch_skill_common", _common_path)
    _ws_common = importlib.util.module_from_spec(_spec)
    sys.modules["_watch_skill_common"] = _ws_common
    _spec.loader.exec_module(_ws_common)
    _ws_common.__ws_common_mtime = _common_mtime

arg_float = _ws_common.arg_float
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_moment(video: str, timestamp: str, window: float = 10.0) -> str:
    """Zoom into one specific moment of a watched video.

    The engine exposes this ONLY on the MCP surface (`get_moment`); there is
    no `watch-skill moment` CLI subcommand in 1.4.x, so shelling out would
    just return a Typer usage error. This tool therefore reports the correct
    path instead of burning a subprocess, and the prompt tells the model to
    prefer the MCP tool.

    Args:
        video: video_id or original source.
        timestamp: center of the window (`SS`, `MM:SS`, or `HH:MM:SS`).
        window: seconds of context around the timestamp (default 10).

    Returns:
        A short explanation of which tool to use (the MCP `get_moment`).
    """
    return (
        "**ws_moment** has no CLI fallback: the engine provides moment zoom "
        "only through its MCP tool `get_moment`, and the installed CLI has no "
        "`moment` subcommand.\n\n"
        "Use the MCP tool instead:\n"
        f"- `get_moment(video=\"{video}\", timestamp=\"{timestamp}\", window={window})`\n\n"
        "It returns dense frames + transcript + OCR around the timestamp. "
        "If the MCP server is not registered, enable it in Settings -> MCP, or "
        "run `/ws-doctor`. For a question about that moment rather than raw "
        "evidence, `ws_ask` works over the CLI."
    )


class WsMoment(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        video = arg_str(args, "video")
        timestamp = arg_str(args, "timestamp")
        if not video or not timestamp:
            return Response(
                message=(
                    "**ws_moment** needs `video` (video_id or source) and "
                    "`timestamp` (SS / MM:SS / HH:MM:SS)."
                ),
                break_loop=False,
            )
        window = arg_float(args, "window", 10.0)
        if window <= 0:
            window = 10.0
        return Response(
            message=await asyncio.to_thread(
                ws_moment, video, timestamp, window=window
            ),
            break_loop=False,
        )