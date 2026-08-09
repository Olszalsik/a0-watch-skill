"""ws_library — cross-video memory: ask the whole library at once.

Wraps `watch-skill library` (MCP twins: `library_synthesize`,
`library_overview`). Every watched video distills structured notes
(entities, claims, chapters) with (video_id, timestamp) provenance.
Indexing video N never reprocesses the others.
"""

from ._common import format_for_llm, run_cli


def ws_library(
    question: str = "",
    k_videos: int = 5,
    overview: bool = False,
) -> str:
    """Ask the local video library, or show its overview.

    Args:
        question: natural-language question to ask across every indexed
            video. Leave empty when `overview=True`.
        k_videos: how many videos to consult (default 5).
        overview: if True, ignore the question and print the library
            overview (videos indexed, hours, note counts, recurring entities,
            recent additions, lifetime token savings).

    Returns:
        Markdown synthesis with per-video timestamp citations, or the
        library overview if `overview=True`.
    """
    if overview:
        return format_for_llm(
            run_cli(["library", "overview"], timeout=60, json_output=True),
            max_chars=12000,
        )
    if not question:
        return (
            "**ws_library** needs a question, or pass `overview=True` to "
            "print the library overview."
        )
    return format_for_llm(
        run_cli(
            ["library", "ask", question, "--k-videos", str(k_videos)],
            timeout=120,
            json_output=False,
        ),
        max_chars=16000,
    )


def ws_stats() -> str:
    """Return the lifetime token-savings meter (vs naive raw-frame injection)."""
    return format_for_llm(
        run_cli(["stats"], timeout=30, json_output=True),
        max_chars=4000,
    )


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
