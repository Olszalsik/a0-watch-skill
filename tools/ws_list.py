"""ws_list — show what is already in the local video index.

Always call this **before** `ws_watch` to avoid re-watching a video that
was analyzed in a previous session. Wraps `watch-skill list`.
"""

from ._common import format_for_llm, run_cli


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
