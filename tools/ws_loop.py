"""ws_loop — THE LOOP: capture → critique → fix → proof.

Wraps `watch-skill loop` (MCP twins: `loop_start`, `loop_iterate`,
`loop_status`, `capture`, `loop_video_gen`, `loop_game`, `loop_monitor`).

The loop **only observes** — it never edits the user's code or UI. The
LLM is expected to apply the suggested fix, then call `iterate`.
"""

from __future__ import annotations

import json as _json
from typing import Any, Optional

from ._common import format_for_llm, load_plugin_config, run_cli


def _default_max_iterations() -> int:
    cfg = load_plugin_config().get("loop", {})
    return int(cfg.get("default_max_iterations", 5))


def _default_duration() -> float:
    cfg = load_plugin_config().get("loop", {})
    return float(cfg.get("default_duration", 8.0))


def ws_loop(
    mode: str,
    target: str = "",
    pass_criteria: str = "",
    script: Optional[list[dict[str, Any]]] = None,
    spec: str = "",
    generator_cmd: str = "",
    output: str = "",
    workdir: str = "",
    condition: str = "",
    source: str = "",
    run_cmd: str = "",
    loop_id: str = "",
    duration: float = -1.0,
    interval: float = 10.0,
    sample_seconds: float = 5.0,
    max_iterations: int = -1,
    max_checks: int = 10,
    timeout: float = 600.0,
) -> str:
    """Run a capture / loop_start / loop_iterate / loop_status / loop_video_gen /
    loop_game / loop_monitor command, then return a human-readable result.

    The exact set of arguments used depends on `mode`:
      - "start"       → target + pass_criteria (+ optional script)
      - "iterate"     → loop_id (only)
      - "status"      → loop_id (only)
      - "capture"     → target (+ optional duration)
      - "video-gen"   → spec + generator_cmd + output (+ workdir, timeout)
      - "game"        → target + pass_criteria (+ run_cmd, script, duration)
      - "monitor"     → source + condition (+ interval, max_checks,
                         sample_seconds)

    Args:
        mode: one of the seven modes listed above.
        All other parameters are mode-specific; defaults come from the
        plugin's `loop.*` config.

    Returns:
        Markdown report (or the loop JSON, depending on the engine surface).
    """
    if duration is None or duration < 0:
        duration = _default_duration()
    if max_iterations is None or max_iterations < 0:
        max_iterations = _default_max_iterations()

    args: list[str] = []
    json_out = True

    if mode == "start":
        if not target or not pass_criteria:
            return "**ws_loop(start)** needs `target` and `pass_criteria`."
        args += [
            "start", target, pass_criteria,
            "--max-iterations", str(max_iterations),
            "--duration", str(duration),
        ]
        if script:
            args += ["--script", _json.dumps(script)]
    elif mode == "iterate":
        if not loop_id:
            return "**ws_loop(iterate)** needs `loop_id` (from `loop_start`)."
        args += ["iterate", loop_id]
    elif mode == "status":
        if not loop_id:
            return "**ws_loop(status)** needs `loop_id`."
        args += ["status", loop_id]
    elif mode == "capture":
        if not target:
            return "**ws_loop(capture)** needs `target`."
        args += ["capture", target, "--duration", str(duration)]
    elif mode == "video-gen":
        if not spec or not generator_cmd or not output:
            return (
                "**ws_loop(video-gen)** needs `spec`, `generator_cmd`, and "
                "`output`."
            )
        args += [
            "video-gen",
            "--spec", spec,
            "--cmd", generator_cmd,
            "--output", output,
            "--max-iterations", str(max_iterations),
            "--timeout", str(timeout),
        ]
        if pass_criteria:
            args += ["--pass-criteria", pass_criteria]
        if workdir:
            args += ["--workdir", workdir]
    elif mode == "game":
        if not target or not pass_criteria:
            return "**ws_loop(game)** needs `target` and `pass_criteria`."
        args += [
            "game", target, pass_criteria,
            "--duration", str(duration),
            "--max-iterations", str(max_iterations),
        ]
        if run_cmd:
            args += ["--run-cmd", run_cmd]
        if script:
            args += ["--script", _json.dumps(script)]
    elif mode == "monitor":
        if not source or not condition:
            return "**ws_loop(monitor)** needs `source` and `condition`."
        args += [
            "monitor", source, condition,
            "--interval", str(interval),
            "--max-checks", str(max_checks),
            "--sample-seconds", str(sample_seconds),
        ]
    else:
        return (
            f"**ws_loop:** unknown mode {mode!r}. Expected one of: "
            "start, iterate, status, capture, video-gen, game, monitor."
        )

    return format_for_llm(
        run_cli(["loop", *args], timeout=int(timeout) + 60, json_output=json_out),
        max_chars=20000,
    )
