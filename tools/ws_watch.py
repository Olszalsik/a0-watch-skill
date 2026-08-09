"""ws_watch — first look at a new video: download, OCR, transcribe, index.

Wraps `watch-skill watch` (MCP twin: `watch_video`). Always check the
index with `ws_list` first; never re-watch a video that's already there.
"""

from ._common import format_for_llm, run_cli


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


def ws_status(job_id: str) -> str:
    """Poll a backgrounded watch job. Use after ws_watch(background=True)."""
    return format_for_llm(
        run_cli(["status", job_id], timeout=30, json_output=True), max_chars=4000
    )
