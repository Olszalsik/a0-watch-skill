"""ws_search — hybrid keyword+semantic search across every indexed video.

Wraps `watch-skill search` (MCP twin: `search_videos`). Use this when the
user asks "find the moment in any video where X" and you don't know which
video holds the answer. Follow each hit with `ws_ask` or `ws_moment`.

v1.1.0 re-port: `ws_moment` moved to its own file `ws_moment.py` (one Tool
class per file); `_common` imported by absolute path.
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

arg_int = _ws_common.arg_int
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli
build_args = _ws_common.build_args
dropped_flags_notice = _ws_common.dropped_flags_notice


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
    # Engine 1.4.x documents `search QUERY` with no options, so `limit` is
    # passed through build_args(): it is used when the installed build
    # supports it and reported as dropped when it does not, rather than
    # failing the whole search with a usage error.
    argv, dropped = build_args(
        ["search", query], [("--limit", str(limit))], probe=["search"]
    )
    return format_for_llm(
        run_cli(argv, timeout=60),
        max_chars=12000,
    ) + dropped_flags_notice(
        dropped,
        "The engine's own default hit count applies. Narrow the query instead.",
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
        report = await asyncio.to_thread(
            ws_search, query=query, limit=arg_int(args, "limit", 10)
        )
        return Response(message=report, break_loop=False)