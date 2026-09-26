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
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Iterable, Optional

# Tool-level constants. The agent layer will override these via the plugin config.
DEFAULT_TIMEOUT = 120

# Env vars the watch-skill engine recognizes for vision providers.
#
# The engine's own documented names are the WATCHSKILL_-prefixed ones
# (docs/configuration.md). The bare provider names are kept because
# several engines/SDKs also honour them and users already have them set.
# Both sets are forwarded, and BOTH are redacted by redact_secrets().
# Do not trim this list to the bare names: the prefixed names are the ones
# the engine actually reads, and dropping them silently disables vision
# while looking configured.
VISION_ENV_VARS = (
    # engine-native (authoritative)
    "WATCHSKILL_ANTHROPIC_API_KEY",
    "WATCHSKILL_OPENAI_API_KEY",
    "WATCHSKILL_GEMINI_API_KEY",
    "WATCHSKILL_GOOGLE_API_KEY",
    "WATCHSKILL_OPENROUTER_API_KEY",
    "WATCHSKILL_OLLAMA_BASE_URL",
    "WATCHSKILL_VISION_PROVIDER",
    "WATCHSKILL_VISION_MODEL",
    "WATCHSKILL_VISION_CHEAP_PROVIDER",
    "WATCHSKILL_VISION_CHEAP_MODEL",
    "WATCHSKILL_VISION_STRONG_PROVIDER",
    "WATCHSKILL_VISION_STRONG_MODEL",
    "WATCHSKILL_COST_POLICY",
    "WATCHSKILL_OFFLINE",
    "WATCHSKILL_DATA_DIR",
    # bare provider names (fallback)
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
)

# Env var NAMES that must never reach the LLM. Derived from
# VISION_ENV_VARS so the redaction list can never drift out of sync with
# the passthrough list -- that drift is what previously leaked
# WATCHSKILL_* keys into tool output.
_SECRET_ENV_NAMES = tuple(
    n for n in VISION_ENV_VARS if n.endswith("_API_KEY")
) + ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY")

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

    saved: dict = {}
    try:
        from helpers import plugins as _plugins  # framework API, absolute import

        saved = _plugins.get_plugin_config("watch_skill") or {}
    except Exception:
        saved = {}

    # The framework call returns {} (rather than raising) when the plugin has
    # no config.json yet. Previously that short-circuited the on-disk read
    # below, so a hand-written config.json was ignored whenever the framework
    # was importable. Fall through unless we got real data.
    if not isinstance(saved, dict) or not saved:
        user_cfg = root / "config.json"
        if user_cfg.exists():
            try:
                loaded = json.loads(user_cfg.read_text(encoding="utf-8")) or {}
                if isinstance(loaded, dict):
                    saved = loaded
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
    """Return the env-var mapping to use when invoking the CLI.

    The CLI is a plain subprocess, not a sandbox, so it inherits the whole
    environment. `passthrough_keys` is therefore only documentation of intent
    and is NOT a security boundary -- it must not be relied on as one.
    (The previous implementation copied the environ and then merged a
    filtered subset of that same copy back into itself, a no-op that gave
    the impression of an allowlist.)

    Provider keys are inherited from the real environment via VISION_ENV_VARS
    documentation; the configured provider/model are layered on top by
    apply_vision_env() so the settings UI actually reaches the engine.
    """
    env = os.environ.copy()
    if not passthrough_keys:
        return env
    return env


# Engine env var names for the configured vision provider/model. These are
# the engine's own names (docs/configuration.md); using the config values
# here is what makes vision.provider / vision.model functional rather than
# merely persisted.
_VISION_PROVIDER_ENV = "WATCHSKILL_VISION_PROVIDER"
_VISION_MODEL_ENV = "WATCHSKILL_VISION_MODEL"

_PROVIDER_TO_KEY_ENV = {
    "anthropic": "WATCHSKILL_ANTHROPIC_API_KEY",
    "openai": "WATCHSKILL_OPENAI_API_KEY",
    "gemini": "WATCHSKILL_GEMINI_API_KEY",
    "openrouter": "WATCHSKILL_OPENROUTER_API_KEY",
    "ollama": "WATCHSKILL_OLLAMA_BASE_URL",
}


def apply_vision_env(env: dict) -> dict:
    """Layer the configured vision provider/model onto `env` in place.

    The settings UI persisted `vision.provider` and `vision.model` to
    config.json, but nothing ever translated them into the engine's env
    vars -- so choosing a provider in the UI had no effect on any tool call.
    This is that missing translation.

    Rules:
      - An explicit `env` value always wins, so a shell-level override
        beats the settings UI (principle of least surprise).
      - `provider: auto` maps to the engine's own default and is not set.
      - `provider: none` disables cloud vision explicitly.
      - If the provider's key is not in the environment and no model was
        set, nothing is injected: inventing a provider value with no
        credential would just produce a confusing auth error.
    """
    try:
        vision = (load_plugin_config() or {}).get("vision") or {}
        if not isinstance(vision, dict):
            return env
    except Exception:
        return env

    provider = str(vision.get("provider", "auto") or "auto").strip().lower()
    model = str(vision.get("model", "") or "").strip()

    if provider and provider != "auto" and _VISION_PROVIDER_ENV not in env:
        env[_VISION_PROVIDER_ENV] = provider

    if model and _VISION_MODEL_ENV not in env:
        env[_VISION_MODEL_ENV] = model

    # Ollama needs no credential; every other provider does. Only inject the
    # provider when the credential is actually available, so the engine is
    # not pointed at a provider that will reject the request.
    key_env = _PROVIDER_TO_KEY_ENV.get(provider)
    if key_env and provider not in ("auto", "ollama") and key_env not in env:
        env.pop(_VISION_PROVIDER_ENV, None)

    return env


# ---------------------------------------------------------------------------
# CLI capability detection
# ---------------------------------------------------------------------------
#
# The engine's CLI surface moves between releases (e.g. `report-mistake`
# became `lessons add`; `moment` exists only on the MCP surface; `watch`
# never gained `--question`/`--background`). Hard-coding a flag list made
# this plugin silently emit usage errors, and hard-coding a second list
# would just re-introduce the same drift. Instead we ask the installed
# engine which options it actually accepts, once per subcommand, and drop
# anything it would reject -- telling the caller (and the LLM) what was
# dropped so the behaviour is never silent.
#
# `None` from supported_flags() means "could not tell"; callers then fall
# back to the documented flag set rather than dropping everything.

_HELP_CACHE: dict[str, tuple[float, Optional[frozenset]]] = {}
_HELP_TTL_S = 300.0
_HELP_TIMEOUT_S = 15.0
_FLAG_RE = re.compile(r"(?<![\w-])(--[a-z0-9][a-z0-9-]*)")


def supported_flags(subcommand: Iterable[str]) -> Optional[frozenset]:
    """Return the option names `watch-skill <subcommand> --help` advertises.

    Cached for _HELP_TTL_S. Returns None when the probe cannot run (no CLI,
    non-zero exit, unparseable help) so callers can fall back.
    """
    key = " ".join(subcommand)
    now = time.monotonic()
    hit = _HELP_CACHE.get(key)
    if hit is not None and now - hit[0] < _HELP_TTL_S:
        return hit[1]

    result: Optional[frozenset] = None
    cli = find_cli()
    if cli:
        try:
            proc = subprocess.run(
                [cli, *subcommand, "--help"],
                capture_output=True,
                text=True,
                timeout=_HELP_TIMEOUT_S,
                check=False,
            )
            if proc.returncode == 0:
                blob = (proc.stdout or "") + "\n" + (proc.stderr or "")
                found = set(_FLAG_RE.findall(blob))
                # A subcommand that takes no options still reports --help;
                # an empty set is a legitimate answer.
                result = frozenset(found) if found else frozenset()
        except Exception:
            result = None

    _HELP_CACHE[key] = (now, result)
    return result


def build_args(
    base: list[str],
    flags: list[tuple[str, str]],
    probe: Optional[Iterable[str]] = None,
) -> tuple[list[str], list[str]]:
    """Append `flags` to `base`, dropping any the engine will reject.

    `flags` is a list of ``(flag, value)``; an empty `value` means a
    boolean flag (pass the flag alone).

    `probe` is the subcommand path used for the `--help` capability probe and
    MUST exclude positional arguments (``base`` may be
    ``["library", "ask", question]`` while the probe is ``["library","ask"]``).
    It defaults to ``base[:1]``.

    Returns ``(argv, dropped)`` where `dropped` lists the omitted flags so the
    caller can surface them. When the probe is inconclusive nothing is
    dropped -- a failed probe must never silently disable every option.
    """
    probe_args = list(probe) if probe is not None else base[:1]
    supported = supported_flags(probe_args)
    if supported is None:
        argv = list(base)
        for flag, value in flags:
            argv.append(flag)
            if value:
                argv.append(str(value))
        return argv, []

    argv = list(base)
    dropped: list[str] = []
    for flag, value in flags:
        if flag not in supported:
            dropped.append(flag)
            continue
        argv.append(flag)
        if value:
            argv.append(str(value))
    return argv, dropped


def dropped_flags_notice(dropped: list[str], guidance: str = "") -> str:
    """Render a short, actionable note about flags the engine rejected."""
    if not dropped:
        return ""
    uniq = sorted(set(dropped))
    body = (
        "\n\n---\n**watch-skill note:** the installed engine's CLI does not "
        "accept " + ", ".join(f"`{f}`" for f in uniq) + ", so "
        + ("that argument was " + ("dropped" if len(uniq) == 1 else "those arguments were") + ".")
        + " The installed engine version may differ from what this plugin targets."
    )
    if guidance:
        body += " " + guidance
    return body


async def run_cli_async(*args, **kwargs) -> dict[str, Any]:
    """Awaitable run_cli: offload the blocking subprocess to a worker thread.

    v1.1.1: run_cli is a blocking subprocess.run -- the framework awaits
    Tool.execute() directly on the server event loop (agent.py:1212), so a
    blocking call inside execute() froze the ENTIRE server (all chats, WS
    heartbeats, WebUI) for the duration.

    v1.1.2 docstring correction: the plugin's tools do NOT call this
    wrapper -- each tool offloads at its own layer (e.g. WsLoop.execute
    awaits asyncio.to_thread around the whole sync ``ws_loop`` function,
    which internally calls run_cli). Kept as a convenience for external
    callers that want to await a single run_cli from async code.
    """
    return await asyncio.to_thread(run_cli, *args, **kwargs)


def _popen_group_kwargs() -> dict:
    """Put the child in its own process group.

    `subprocess.run(timeout=...)` kills only the direct child. The engine
    spawns ffmpeg / yt-dlp, so on timeout (or on server shutdown) those
    grandchildren survived as orphans holding the download open. Running
    the child as a group leader lets us signal the whole tree.
    """
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def _kill_tree(proc: subprocess.Popen) -> None:
    """Best-effort kill of the child's whole process group."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.kill()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


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
                "Install the watch-skill Python CLI (engine 1.4.x):\n"
                "  uv tool install 'watch-skill[standard] @ git+https://github.com/oxbshw/watch-skill'\n"
                "The [standard] extra is required -- a bare install has no frame "
                "extraction, no retrieval and no MCP server.\n"
                "Fallbacks: pipx install '<same spec>'. There is deliberately no "
                "`pip install` step: it targets the framework venv, whose bin "
                "directory is not on PATH, so the CLI would stay invisible.\n"
                "Then restart the shell / re-enable the plugin, or run /ws-doctor."
            ),
            "error": "config.cli_missing",
        }

    full_args = [cli, *args]
    if json_output and "--json" not in full_args:
        full_args.append("--json")

    proc: Optional[subprocess.Popen] = None
    try:
        proc = subprocess.Popen(
            full_args,
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env or apply_vision_env(build_env()),
            **_popen_group_kwargs(),
        )
        try:
            stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except Exception:
                stdout, stderr = "", ""
            return {
                "ok": False,
                "exit_code": -1,
                "stdout": stdout or "",
                "stderr": (stderr or "")
                + f"\n[watch-skill wrapper] timeout after {timeout}s; process group killed",
                "error": "health.timeout",
                "fix": (
                    "Re-run with a longer timeout, or use the MCP `watch_video` "
                    "tool, which runs the watch as a background job."
                ),
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
    except Exception as e:  # noqa: BLE001 - a tool must never raise
        if proc is not None:
            _kill_tree(proc)
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "error": "health.exec_failed",
            "fix": "Run `watch-skill doctor` (/ws-doctor) to check the installation.",
        }

    out = {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout": stdout or "",
        "stderr": stderr or "",
    }
    if json_output and (stdout or "").strip():
        try:
            out["json"] = json.loads(stdout)
        except json.JSONDecodeError:
            out["json_parse_error"] = True
    if not out["ok"] and out["stderr"]:
        first_line = out["stderr"].strip().splitlines()[:1]
        if first_line and first_line[0].startswith("{"):
            try:
                out["engine_error"] = json.loads(first_line[0])
            except json.JSONDecodeError:
                pass
        elif "No such command" in out["stderr"] or "Usage:" in out["stderr"]:
            # Typer/Click reject an unknown subcommand or flag with a usage
            # error rather than the engine's structured {error, fix} shape.
            # Flag it so callers can degrade with guidance instead of
            # dumping a raw usage string at the LLM.
            out["usage_error"] = True
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
    """Redact engine/provider API keys from text bound for the LLM.

    The name list is derived from _SECRET_ENV_NAMES (itself derived from
    VISION_ENV_VARS) so it cannot drift out of sync with what we forward.
    This previously only knew the five bare provider names, while the
    engine actually reads the WATCHSKILL_-prefixed ones -- so a prefixed key
    echoed by the engine reached the model verbatim.

    Also redacts the other credential-shaped vars the engine documents
    (bearer token), which are not provider keys.
    """
    if not text:
        return text
    for key in _SECRET_ENV_NAMES + ("WATCHSKILL_API_BEARER_TOKEN", "WATCHSKILL_COST_CEILING_USD"):
        val = os.environ.get(key, "")
        if val and len(val) >= 8 and val in text:
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
    if result.get("usage_error"):
        return (
            "**watch-skill: unsupported CLI invocation.**\n\n"
            "The installed engine rejected this command or one of its options, "
            "so the native CLI fallback cannot serve this request.\n\n"
            f"```\n{result.get('stderr', '').strip()[:800]}\n```\n\n"
            "Use the corresponding MCP tool instead (the MCP server exposes the "
            "full engine surface and is not limited by the CLI), or run "
            "`/ws-doctor` and check the engine version."
        )
    body = result.get("stdout") or ""
    if result.get("stderr"):
        body = body + "\n\n--- stderr ---\n" + result["stderr"]
    body = redact_secrets(body)
    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n[truncated {len(body) - max_chars} chars]"
    return body