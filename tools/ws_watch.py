"""ws_watch — first look at a new video: download, OCR, transcribe, index.

Wraps `watch-skill watch` (MCP twin: `watch_video`). Always check the
index with `ws_list` first; never re-watch a video that's already there.

v1.1.0 re-port: `ws_status` (background-job polling) moved to its own file
`ws_status.py` — the framework loads only the first Tool class per file.
`_common` is imported by absolute path (synthetic-module loader).
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
arg_str = _ws_common.arg_str
format_for_llm = _ws_common.format_for_llm
run_cli = _ws_common.run_cli


def ws_watch(
    source: str,
    question: str = "",
    start: str = "",
    end: str = "",
    max_frames: int = 0,
    transcript_only: bool = False,
    background: bool = False,
    batch: bool = False,
    limit: int = 20,
) -> str:
    """Watch (download + analyze + index) a video.

    Args:
        source: any yt-dlp-supported URL (1800+ sites), direct media URL,
            HLS/DASH manifest, or local file path. For batch mode this can
            be a playlist URL, channel URL, folder, or comma-separated list.
        question: optional original question — echoed in the report header so
            the engine answers it from the returned evidence.
        start / end: optional timestamps (`SS`, `MM:SS`, or `HH:MM:SS`) to
            zoom into a section with denser sampling.
        max_frames: cap on extracted frames (0 = engine default).
        transcript_only: if True, skip frame extraction and download (fastest).
        background: if True, return a `job_id` instantly; poll `ws_status`.
            Use this for long videos or strict client timeouts.
        batch: if True, treat `source` as a playlist/channel/folder/list.
        limit: in batch mode, max videos to process (default 20).

    Returns:
        Markdown report with `Indexed: <video_id>`, frames with timestamps,
        OCR, transcript, and the answer (if a question was given). For
        background mode, returns the job_id and instructions to poll.
    """
    cmd = ["batch"] if batch else ["watch"]
    cmd.append(source)
    if question:
        cmd += ["--question", question]
    if start:
        cmd += ["--start", start]
    if end:
        cmd += ["--end", end]
    if max_frames > 0:
        cmd += ["--max-frames", str(max_frames)]
    if transcript_only:
        cmd.append("--transcript-only")
    if background:
        cmd.append("--background")
    if batch and limit:
        cmd += ["--limit", str(limit)]

    timeout = 30 if background else 600  # backgrounding returns instantly
    return format_for_llm(
        run_cli(cmd, timeout=timeout, json_output=background), max_chars=16000
    )


class WsWatch(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        source = arg_str(args, "source")
        if not source:
            return Response(
                message=(
                    "**ws_watch** requires a non-empty `source` (video URL, media "
                    "URL, HLS/DASH manifest, or local file path)."
                ),
                break_loop=False,
            )
        max_frames = arg_int(args, "max_frames", 0)
        if max_frames > 2000:
            return Response(
                message=(
                    "**ws_watch** rejects `max_frames` > 2000; use "
                    "`transcript_only=true` or `background=true` instead."
                ),
                break_loop=False,
            )
        report = ws_watch(
            source=source,
            question=arg_str(args, "question"),
            start=arg_str(args, "start"),
            end=arg_str(args, "end"),
            max_frames=max_frames,
            transcript_only=arg_bool(args, "transcript_only", False),
            background=arg_bool(args, "background", False),
            batch=arg_bool(args, "batch", False),
            limit=arg_int(args, "limit", 20),
        )
        return Response(message=report, break_loop=False)