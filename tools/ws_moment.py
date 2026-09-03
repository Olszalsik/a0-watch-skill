"""ws_moment — zoom into one specific moment of a watched video.

Wraps `watch-skill moment` (MCP twin: `get_moment`). Use after ws_ask or
ws_search when you need dense frames + transcript + OCR around a single
timestamp.

v1.1.0 re-port: extracted from ws_search.py — one Tool class per file.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from helpers.tool import Response, Tool

_spec = importlib.util.spec_from_file_location(
    "_watch_skill_common", Path(__file__).resolve().parent / "_common.py"
)
_ws_common = sys.modules.get("_watch_skill_common")
if _ws_common is None:
    _ws_common = importlib.util.module_from_spec(_spec)
    sys.modules["_watch_skill_common"] = _ws_common
    _spec.loader.exec_module(_ws_common)

arg_float = _ws_common.arg_float
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_moment(video: str, timestamp: str, window: float = 10.0) -> str:
    """Zoom into one specific moment of a watched video.

    Args:
        video: video_id or original source.
        timestamp: center of the window (`SS`, `MM:SS`, or `HH:MM:SS`).
        window: seconds of context around the timestamp (default 10).

    Returns:
        Dense frames + transcript + OCR around the timestamp.
    """
    return format_for_llm(
        run_cli(["moment", video, timestamp, "--window", str(window)], timeout=60),
        max_chars=12000,
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
            message=ws_moment(video, timestamp, window=window), break_loop=False
        )