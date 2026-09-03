"""ws_list — show what is already in the local video index.

Always call this **before** `ws_watch` to avoid re-watching a video that
was analyzed in a previous session. Wraps `watch-skill list`.

v1.1.0 re-port: one Tool class per file; `_common` imported by absolute
path (synthetic-module loader, hyphenated plugin dir).
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

arg_bool = _ws_common.arg_bool
arg_int = _ws_common.arg_int
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_list(
    limit: int = 50,
    as_json: bool = False,
) -> str:
    """List the videos currently in the local watch-skill index.

    Args:
        limit: max number of rows to return (default 50, 0 = no cap).
        as_json: if True, return the raw JSON from `watch-skill list --json`,
            otherwise a compact markdown table.

    Returns:
        Markdown (or JSON) string summarizing indexed videos.
    """
    args = ["list"]
    if limit > 0:
        args += ["--limit", str(limit)]
    result = run_cli(args, timeout=30, json_output=as_json)
    if as_json and "json" in result:
        import json

        return "```json\n" + json.dumps(result["json"], indent=2)[:12000] + "\n```"
    return format_for_llm(result, max_chars=12000)


class WsList(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        report = ws_list(
            limit=arg_int(args, "limit", 50),
            as_json=arg_bool(args, "as_json", False),
        )
        return Response(message=report, break_loop=False)