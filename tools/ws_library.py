"""ws_library — cross-video memory: ask the whole library at once.

Wraps `watch-skill library` (MCP twins: `library_synthesize`,
`library_overview`). Every watched video distills structured notes
(entities, claims, chapters) with (video_id, timestamp) provenance.
Indexing video N never reprocesses the others.

v1.1.0 re-port: `ws_stats` and `ws_report_mistake` moved to their own files
(one Tool class per file); `_common` imported by absolute path.
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
load_plugin_config = _ws_common.load_plugin_config
run_cli = _ws_common.run_cli


def ws_library(
    question: str = "",
    k_videos: int = 5,
    overview: bool = False,
) -> str:
    """Ask the local video library, or show its overview.

    Args:
        question: natural-language question to ask across every indexed
            video. Leave empty when `overview=True`.
        k_videos: how many videos to consult (default 5).
        overview: if True, ignore the question and print the library
            overview (videos indexed, hours, note counts, recurring entities,
            recent additions, lifetime token savings).

    Returns:
        Markdown synthesis with per-video timestamp citations, or the
        library overview if `overview=True`.
    """
    if overview:
        return format_for_llm(
            run_cli(["library", "overview"], timeout=60, json_output=True),
            max_chars=12000,
        )
    if not question:
        return (
            "**ws_library** needs a question, or pass `overview=true` to "
            "print the library overview."
        )
    return format_for_llm(
        run_cli(
            ["library", "ask", question, "--k-videos", str(k_videos)],
            timeout=120,
            json_output=False,
        ),
        max_chars=16000,
    )


def _default_k_videos() -> int:
    cfg = load_plugin_config().get("index", {})
    try:
        return int(cfg.get("library_chunk_k_videos", 5))
    except (TypeError, ValueError):
        return 5


class WsLibrary(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        overview = arg_bool(args, "overview", False)
        question = arg_str(args, "question")
        if not overview and not question:
            return Response(
                message=(
                    "**ws_library** needs a `question`, or pass `overview=true` "
                    "to print the library overview."
                ),
                break_loop=False,
            )
        k_videos = arg_int(args, "k_videos", _default_k_videos())
        report = await asyncio.to_thread(
            ws_library,
            question=question, k_videos=k_videos, overview=overview
        )
        return Response(message=report, break_loop=False)