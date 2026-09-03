"""ws_loop — THE LOOP: capture → critique → fix → proof.

Wraps `watch-skill loop` (MCP twins: `loop_start`, `loop_iterate`,
`loop_status`, `capture`, `loop_video_gen`, `loop_game`, `loop_monitor`).

The loop **only observes** — it never edits the user's code or UI. The
LLM is expected to apply the suggested fix, then call `iterate`.

v1.1.0 re-port: numeric tool args are coerced with try/except (A0 passes
tool args as strings); `_common` imported by absolute path.
"""

from __future__ import annotations

import importlib.util
import json as _json
import sys
from pathlib import Path
from typing import Any, Optional

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
load_plugin_config = _ws_common.load_plugin_config
run_cli = _ws_common.run_cli


def _default_max_iterations() -> int:
    cfg = load_plugin_config().get("loop", {})
    try:
        return int(cfg.get("default_max_iterations", 5))
    except (TypeError, ValueError):
        return 5


def _default_duration() -> float:
    cfg = load_plugin_config().get("loop", {})
    try:
        return float(cfg.get("default_duration", 8.0))
    except (TypeError, ValueError):
        return 8.0


def _coerce_float(value: Any, default: float) -> float:
    """Tool args arrive as strings; never let a bad number crash the tool."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(_coerce_float(value, float(default)))
    except (TypeError, ValueError):
        return default


def _coerce_script(value: Any) -> list[dict[str, Any]] | None:
    """Accept a list, a JSON string, or nothing for the `script` arg."""
    if value is None or value == "" or value == []:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = _json.loads(value)
            return parsed if isinstance(parsed, list) else None
        except _json.JSONDecodeError:
            return None
    return None


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


class WsLoop(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        mode = arg_str(args, "mode").lower()
        if not mode:
            return Response(
                message=(
                    "**ws_loop** needs `mode` (start, iterate, status, capture, "
                    "video-gen, game, monitor)."
                ),
                break_loop=False,
            )

        duration = _coerce_float(args.get("duration"), -1.0)
        max_iterations = _coerce_int(args.get("max_iterations"), -1)
        interval = _coerce_float(args.get("interval"), 10.0)
        sample_seconds = _coerce_float(args.get("sample_seconds"), 5.0)
        max_checks = _coerce_int(args.get("max_checks"), 10)
        timeout = _coerce_float(args.get("timeout"), 600.0)
        if timeout <= 0:
            timeout = 600.0
        script = _coerce_script(args.get("script"))

        report = ws_loop(
            mode=mode,
            target=arg_str(args, "target"),
            pass_criteria=arg_str(args, "pass_criteria"),
            script=script,
            spec=arg_str(args, "spec"),
            generator_cmd=arg_str(args, "generator_cmd"),
            output=arg_str(args, "output"),
            workdir=arg_str(args, "workdir"),
            condition=arg_str(args, "condition"),
            source=arg_str(args, "source"),
            run_cmd=arg_str(args, "run_cmd"),
            loop_id=arg_str(args, "loop_id"),
            duration=duration,
            interval=interval,
            sample_seconds=sample_seconds,
            max_iterations=max_iterations,
            max_checks=max_checks,
            timeout=timeout,
        )
        return Response(message=report, break_loop=False)