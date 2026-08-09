"""Common helpers for the watch-skill native tool wrappers.

Every ws_* tool ultimately shells out to the `watch-skill` CLI. We use a
single helper to:
  1. Locate the binary (or produce a clean `cli_missing` error).
  2. Run the command and capture stdout/stderr/exit code.
  3. Parse JSON when the command is `--json`, otherwise return text.
  4. Forward env-var API keys when the plugin config asks for it.

The MCP server is still the primary integration path; these tools exist
so the LLM can do basic read operations even if the MCP server fails to
spawn (e.g. on a fresh install before `watch-skill` is on PATH).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional

# Tool-level constants. The agent layer will override these via the plugin config.
DEFAULT_TIMEOUT = 120

# Env vars that the watch-skill engine recognizes for vision providers.
VISION_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "WATCHSKILL_VISION_PROVIDER",
    "WATCHSKILL_VISION_MODEL",
    "WATCHSKILL_CHEAP_MODEL",
    "WATCHSKILL_STRONG_MODEL",
)


def find_cli() -> Optional[str]:
    """Return absolute path to `watch-skill`, or None if not on PATH."""
    return shutil.which("watch-skill")


def plugin_config_dir() -> Path:
    """Return the plugin's per-instance config dir (under Agent Zero workdir)."""
    return Path(os.environ.get("A0_WORKDIR", "/a0/usr/workdir")) / "watch-skill"


def load_plugin_config() -> dict:
    """Best-effort load of the merged plugin config (defaults + user overrides)."""
    # The framework typically injects a `get_plugin_config` symbol into
    # the globals of plugin-provided tools. We try it first, then fall back.
    try:
        from a0_plugin_runtime import get_plugin_config  # type: ignore

        return get_plugin_config("watch-skill") or {}
    except Exception:
        pass

    cfg_path = Path(__file__).resolve().parent.parent / "default_config.yaml"
    if cfg_path.exists():
        try:
            import yaml  # type: ignore

            with cfg_path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}
    return {}


def build_env(passthrough_keys: bool = True) -> dict:
    """Return the env-var mapping to use when invoking the CLI."""
    env = os.environ.copy()
    if not passthrough_keys:
        return env
    forwarded = {k: v for k, v in env.items() if k in VISION_ENV_VARS and v}
    env.update(forwarded)
    return env


def run_cli(
    args: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT,
    json_output: bool = False,
    env: Optional[dict] = None,
    input_text: Optional[str] = None,
) -> dict[str, Any]:
    """Run a `watch-skill ...` subprocess and return a structured result."""
    cli = find_cli()
    if not cli:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": "watch-skill CLI not found on PATH",
            "fix": (
                "Install the watch-skill Python CLI: "
                "`uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'` "
                "(or run /ws-doctor in the chat to auto-install with a fallback chain)."
            ),
            "error": "config.cli_missing",
        }

    full_args = [cli, *args]
    if json_output and "--json" not in full_args:
        full_args.append("--json")

    try:
        proc = subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env or build_env(),
            input=input_text,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": e.stdout or "",
            "stderr": (e.stderr or "") + f"\n[watch-skill wrapper] timeout after {timeout}s",
            "error": "health.timeout",
            "fix": "Re-run with a longer timeout, or set `background=true` on watch_video.",
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "error": "config.cli_missing",
            "fix": "Install the watch-skill CLI (see /ws-doctor).",
        }

    out = {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if json_output and proc.stdout.strip():
        try:
            out["json"] = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out["json_parse_error"] = True
    if not out["ok"] and proc.stderr:
        first_line = proc.stderr.strip().splitlines()[:1]
        if first_line and first_line[0].startswith("{"):
            try:
                out["engine_error"] = json.loads(first_line[0])
            except json.JSONDecodeError:
                pass
    return out


def redact_secrets(text: str) -> str:
    """Crude secret redaction for log lines. Best-effort, not bulletproof."""
    if not text:
        return text
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                "OPENROUTER_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(key, "")
        if val and val in text:
            text = text.replace(val, f"<{key} redacted>")
    return text


def format_for_llm(result: dict[str, Any], *, max_chars: int = 12000) -> str:
    """Render a run_cli() result as a compact markdown block for the LLM."""
    if result.get("engine_error"):
        ee = result["engine_error"]
        return (
            f"**watch-skill error** ({ee.get('error', 'unknown')}): "
            f"{ee.get('message', '')}\n\n"
            f"**Fix:** {ee.get('fix', 'run /ws-doctor')}\n"
        )
    body = result.get("stdout") or ""
    if result.get("stderr"):
        body = body + "\n\n--- stderr ---\n" + result["stderr"]
    body = redact_secrets(body)
    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n[truncated {len(body) - max_chars} chars]"
    return body
