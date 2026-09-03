"""ws_report_mistake — report a wrong video answer so the engine learns.

Wraps `watch-skill report-mistake`. The engine stores a local lesson,
applies it to related questions, and where possible re-asks the original
question to confirm the lesson works.

v1.1.0 re-port: extracted from ws_library.py — one Tool class per file.
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


def ws_report_mistake(
    video: str,
    question: str,
    wrong_answer: str,
    correction: str,
    session_id: str = "",
) -> str:
    """Report a wrong video answer so the engine stores a local lesson."""
    args = [
        "report-mistake",
        video,
        "--question", question,
        "--wrong", wrong_answer,
        "--correction", correction,
    ]
    if session_id:
        args += ["--session-id", session_id]
    return format_for_llm(
        run_cli(args, timeout=60, json_output=True),
        max_chars=8000,
    )


class WsReportMistake(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        video = arg_str(args, "video")
        question = arg_str(args, "question")
        wrong_answer = arg_str(args, "wrong_answer")
        correction = arg_str(args, "correction")
        if not (video and question and wrong_answer and correction):
            return Response(
                message=(
                    "**ws_report_mistake** needs `video`, `question`, "
                    "`wrong_answer`, and `correction`."
                ),
                break_loop=False,
            )
        report = await asyncio.to_thread(
            ws_report_mistake,
            video=video,
            question=question,
            wrong_answer=wrong_answer,
            correction=correction,
            session_id=arg_str(args, "session_id"),
        )
        return Response(message=report, break_loop=False)