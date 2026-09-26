"""ws_status — poll a backgrounded watch job.

Use after `ws_watch(background=true)`: the engine returns a `job_id`, and
this tool reports progress until the index entry appears.

v1.1.0 re-port: extracted from ws_watch.py — the framework loads only the
first Tool class per file, so each tool needs its own file.
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

arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_status(job_id: str) -> str:
    """Poll a backgrounded watch job. Use after ws_watch(background=True).

    Engine 1.4.x moved job polling under the `jobs` group; the bare
    `status` subcommand does not exist (it was `get_status` on the MCP
    surface only). The `jobs` spelling is used here.
    """
    return format_for_llm(
        run_cli(["jobs", "status", job_id], timeout=30, json_output=True),
        max_chars=4000,
    )


class WsStatus(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        job_id = arg_str(args, "job_id")
        if not job_id:
            return Response(
                message=(
                    "**ws_status** needs the `job_id` returned by "
                    "ws_watch(background=true)."
                ),
                break_loop=False,
            )
        return Response(
            message=await asyncio.to_thread(ws_status, job_id), break_loop=False
        )