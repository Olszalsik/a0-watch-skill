"""ws_ask — text-first question against a watched video, with timestamps.

Wraps `watch-skill ask` (or the MCP twin `ask_video`). The engine returns
timestamps and a confidence score; if the video does not clearly show the
answer it says so. Never re-run a watch for a follow-up — call this.
"""

from ._common import format_for_llm, run_cli


def ws_ask(
    video: str,
    question: str,
    max_frames: int = 6,
    include_frames: bool = False,
    language: str = "",
) -> str:
    """Ask a question about a video that was already watched.

    Args:
        video: the `video_id` or the original source URL/path.
        question: natural language question, any language.
        max_frames: cap on attached evidence frames (default 6).
        include_frames: force frames on/off. Default lets the engine decide
            (it attaches frames only when it could not verify text-first).
        language: optional ISO code to force the answer language (e.g. "ar").

    Returns:
        Markdown report with timestamps, confidence, and (if requested) frames.
    """
    args = ["ask", video, question, "--max-frames", str(max_frames)]
    if include_frames:
        args.append("--frames")
    else:
        args.append("--no-frames")
    if language:
        args += ["--language", language]
    return format_for_llm(run_cli(args, timeout=120), max_chars=16000)
