"""ws_status — poll a backgrounded watch job.

Use after `ws_watch(background=true)`: the engine returns a `job_id`, and
this tool reports progress until the index entry appears.

v1.1.0 re-port: extracted from ws_watch.py — the framework loads only the
first Tool class per file, so each tool needs its own file.
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

arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_status(job_id: str) -> str:
    """Poll a backgrounded watch job. Use after ws_watch(background=True)."""
    return format_for_llm(
        run_cli(["status", job_id], timeout=30, json_output=True), max_chars=4000
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
        return Response(message=ws_status(job_id), break_loop=False)