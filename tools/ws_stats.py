"""ws_stats — lifetime token-savings meter.

Wraps `watch-skill stats`. Reports savings vs naive raw-frame injection.
Surface it to the user when they ask about cost.

v1.1.0 re-port: extracted from ws_library.py — one Tool class per file,
and the `/ws-stats` slash command now routes to a tool that actually exists.
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

format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_stats() -> str:
    """Return the lifetime token-savings meter (vs naive raw-frame injection)."""
    return format_for_llm(
        run_cli(["stats"], timeout=30, json_output=True),
        max_chars=4000,
    )


class WsStats(Tool):
    async def execute(self, **kwargs) -> Response:
        return Response(
            message=await asyncio.to_thread(ws_stats), break_loop=False
        )