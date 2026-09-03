"""ws_stats — lifetime token-savings meter.

Wraps `watch-skill stats`. Reports savings vs naive raw-frame injection.
Surface it to the user when they ask about cost.

v1.1.0 re-port: extracted from ws_library.py — one Tool class per file,
and the `/ws-stats` slash command now routes to a tool that actually exists.
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
        return Response(message=ws_stats(), break_loop=False)