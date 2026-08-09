"""ws_search — hybrid keyword+semantic search across every indexed video.

Wraps `watch-skill search` (MCP twin: `search_videos`). Use this when the
user asks "find the moment in any video where X" and you don't know which
video holds the answer. Follow each hit with `ws_ask` or `ws_moment`.
"""

from ._common import format_for_llm, run_cli


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
    return format_for_llm(
        run_cli(["search", query, "--limit", str(limit)], timeout=60),
        max_chars=12000,
    )


def ws_moment(video: str, timestamp: str, window: float = 10.0) -> str:
    """Zoom into one specific moment of a watched video.

    Args:
        video: video_id or original source.
        timestamp: center of the window (`SS`, `MM:SS`, or `HH:MM:SS`).
        window: seconds of context around the timestamp (default 10).

    Returns:
        Dense frames + transcript + OCR around the timestamp.
    """
    return format_for_llm(
        run_cli(["moment", video, timestamp, "--window", str(window)], timeout=60),
        max_chars=12000,
    )
