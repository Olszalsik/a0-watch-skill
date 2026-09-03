"""ws_ask — text-first question against a watched video, with timestamps.

Wraps `watch-skill ask` (or the MCP twin `ask_video`). The engine returns
timestamps and a confidence score; if the video does not clearly show the
answer it says so. Never re-run a watch for a follow-up — call this.

v1.1.0 re-port: one Tool class per file; `_common` imported by absolute
path (synthetic-module loader, hyphenated plugin dir).
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

arg_bool = _ws_common.arg_bool
arg_int = _ws_common.arg_int
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_ask(
    video: str,
    question: str,
    max_frames: int = 6,
    include_frames: bool = False,
    language: str = "",
) -> str:
    """Ask a question about a video that was already watched.

    Args:
        video: the `video_id` or the original source URL/path.
        question: natural language question, any language.
        max_frames: cap on attached evidence frames (default 6).
        include_frames: force frames on/off. Default lets the engine decide
            (it attaches frames only when it could not verify text-first).
        language: optional ISO code to force the answer language (e.g. "ar").

    Returns:
        Markdown report with timestamps, confidence, and (if requested) frames.
    """
    args = ["ask", video, question, "--max-frames", str(max_frames)]
    if include_frames:
        args.append("--frames")
    else:
        args.append("--no-frames")
    if language:
        args += ["--language", language]
    return format_for_llm(run_cli(args, timeout=120), max_chars=16000)


class WsAsk(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        video = arg_str(args, "video")
        question = arg_str(args, "question")
        if not video or not question:
            return Response(
                message=(
                    "**ws_ask** needs `video` (video_id or source URL/path) and "
                    "`question`. Use ws_list first to find the video_id."
                ),
                break_loop=False,
            )
        report = await asyncio.to_thread(
            ws_ask,
            video=video,
            question=question,
            max_frames=arg_int(args, "max_frames", 6),
            include_frames=arg_bool(args, "include_frames", False),
            language=arg_str(args, "language"),
        )
        return Response(message=report, break_loop=False)