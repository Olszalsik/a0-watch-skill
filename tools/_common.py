"""Common helpers for the watch-skill native tool wrappers.

Every ws_* tool ultimately shells out to the `watch-skill` CLI. We use a
single helper to:
  1. Locate the binary (or produce a clean `cli_missing` error).
  2. Run the command and capture stdout/stderr/exit code.
  3. Parse JSON when the command is `--json`, otherwise return text.
  4. Forward env-var API keys when the plugin config asks for it.

IMPORT CONTRACT (v1.1.0 re-port): Agent Zero loads tool files as synthetic
modules (basename only, no parent package), so relative imports such as
`from ._common import ...` fail. The hyphen in the plugin directory name
(`watch-skill`) also makes `usr.plugins.watch-skill` an invalid package
path. Each tool file therefore loads this module by absolute path via
importlib (see the loader snippet duplicated at the top
of every ws_*.py). The module is registered in sys.modules as
`_watch_skill_common` so all tool files share one instance.

The MCP server is still the primary integration path; these tools exist
so the LLM can do basic read operations even if the MCP server fails to
spawn (e.g. on a fresh install before `watch-skill` is on PATH).
"""

from __future__ import annotations

import json
import os
import asyncio
import shutil
import subprocess
import time
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

# ---------------------------------------------------------------------------
# Shared-module loader (see module docstring): tools are loaded as synthetic
# modules by helpers.modules.import_module, so we resolve _common.py relative
# to THIS file's absolute path and cache it in sys.modules.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def plugin_root() -> Path:
    """Plugin directory (usr/plugins/watch-skill), derived from this file."""
    return Path(__file__).resolve().parent.parent


def plugin_config_dir() -> Path:
    """Per-instance workdir for tool output (host/container agnostic)."""
    base = os.environ.get("A0_WORKDIR", "")
    if not base:
        try:
            from helpers import files as _files

            base = _files.get_abs_path_dockerized("usr", "workdir")
        except Exception:
            base = str(Path.home() / ".a0-workdir")
    return Path(base) / "watch-skill"


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge `override` into `base` recursively; override wins; base mutated."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_plugin_config() -> dict:
    """Load the plugin config: default_config.yaml overlaid with config.json.

    The framework's get_plugin_config() does NOT merge the two (config.json
    wins wholesale), so plugin code does its own conservative merge: defaults
    first, then any user-saved config.json nested on top. All failures are
    swallowed -- tools must work even with a broken config.
    """
    cfg: dict = {}
    root = plugin_root()

    default_path = root / "default_config.yaml"
    if default_path.exists():
        try:
            import yaml

            cfg = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}
        except Exception:
            cfg = {}

    try:
        from helpers import plugins as _plugins  # framework API, absolute import

        saved = _plugins.get_plugin_config("watch-skill") or {}
    except Exception:
        saved = {}
        user_cfg = root / "config.json"
        if user_cfg.exists():
            try:
                saved = json.loads(user_cfg.read_text(encoding="utf-8")) or {}
            except Exception:
                saved = {}

    if isinstance(saved, dict) and saved:
        _deep_merge(cfg, saved)
    return cfg


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def find_cli() -> Optional[str]:
    """Return absolute path to `watch-skill`, or None if not on PATH."""
    return shutil.which("watch-skill")


def build_env(passthrough_keys: bool = True) -> dict:
    """Return the env-var mapping to use when invoking the CLI."""
    env = os.environ.copy()
    if not passthrough_keys:
        return env
    forwarded = {k: v for k, v in env.items() if k in VISION_ENV_VARS and v}
    env.update(forwarded)
    return env


async def run_cli_async(*args, **kwargs) -> dict[str, Any]:
    """Awaitable run_cli: offload the blocking subprocess to a worker thread.

    v1.1.1: run_cli is a blocking subprocess.run -- the framework awaits
    Tool.execute() directly on the server event loop (agent.py), so a
    foreground ws_watch (600s) or an LLM-supplied huge `timeout` on
    ws_loop froze the ENTIRE server (all chats, WS heartbeats, WebUI)
    for the duration. Every async entry point must call this wrapper
    (or its own asyncio.to_thread) instead of run_cli directly.
    """
    return await asyncio.to_thread(run_cli, *args, **kwargs)


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


# ---------------------------------------------------------------------------
# Tiny TTL cache for expensive CLI probes (banner/status render paths).
# Process-local; 60s default TTL keeps the WebUI responsive without
# hammering the CLI with subprocesses.
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl: float, fn):
    """Return a cached value for `key`, refreshing via fn() when older than ttl."""
    now = time.monotonic()
    entry = _CACHE.get(key)
    if entry is not None and now - entry[0] < ttl:
        return entry[1]
    value = fn()
    _CACHE[key] = (now, value)
    return value


# ---------------------------------------------------------------------------
# Tool-arg coercion (A0 tool args arrive as strings)
# ---------------------------------------------------------------------------


def arg_str(args: dict, key: str, default: str = "") -> str:
    value = (args or {}).get(key, "")
    if value is None:
        return default
    return str(value).strip() or default


def arg_bool(args: dict, key: str, default: bool = False) -> bool:
    value = (args or {}).get(key, None)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def arg_int(args: dict, key: str, default: int = 0) -> int:
    try:
        return int(float(str((args or {}).get(key, "") or default)))
    except (TypeError, ValueError):
        return default


def arg_float(args: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(str((args or {}).get(key, "") or default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


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