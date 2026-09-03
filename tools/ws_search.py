"""ws_search — hybrid keyword+semantic search across every indexed video.

Wraps `watch-skill search` (MCP twin: `search_videos`). Use this when the
user asks "find the moment in any video where X" and you don't know which
video holds the answer. Follow each hit with `ws_ask` or `ws_moment`.

v1.1.0 re-port: `ws_moment` moved to its own file `ws_moment.py` (one Tool
class per file); `_common` imported by absolute path.
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

arg_int = _ws_common.arg_int
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_search(
    query: str,
    limit: int = 10,
) -> str:
    """Search the local video index for a phrase or question.

    Args:
        query: keywords or a phrase, any language (Arabic folding, CJK
            segmentation, Thai segmentation are applied automatically).
        limit: max hits to return (default 10).

    Returns:
        Markdown list of hit videos with timestamped evidence.
    """
    return format_for_llm(
        run_cli(["search", query, "--limit", str(limit)], timeout=60),
        max_chars=12000,
    )


class WsSearch(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        query = arg_str(args, "query")
        if not query:
            return Response(
                message="**ws_search** needs a non-empty `query`.",
                break_loop=False,
            )
        report = ws_search(query=query, limit=arg_int(args, "limit", 10))
        return Response(message=report, break_loop=False)