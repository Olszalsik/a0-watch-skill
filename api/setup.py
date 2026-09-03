"""POST /api/plugins/watch-skill/setup

Optionally installs the watch-skill Python CLI on the host and registers
the MCP server with Agent Zero. Defaults are conservative:

  - install only when `install.auto_install=true` in the plugin config
  - never paste API keys into chat — read them from env vars instead

Request body:
  {
    "install": true|false,      # override install.auto_install
    "vision_provider": "anthropic",
    "vision_api_key_env": "ANTHROPIC_API_KEY",  # name of the env var to read
    "register_mcp": true|false,  # default true
  }

The endpoint returns a JSON report of what was attempted, with a `fix`
string for any failed step.

v1.1.0 re-port:
  - config is read via helpers.plugins.get_plugin_config (merged with
    default_config.yaml by the plugin's get_plugin_config hook) — the
    invented `a0_plugin_runtime` module is gone.
  - MCP registration goes through helpers.settings.set_settings_delta
    (usr/settings.json `mcp_servers` JSON string) instead of writing a
    hardcoded /a0/tmp/settings.json.
  - vision config is written to the plugin's config.json via
    helpers.plugins.save_plugin_config instead of config/settings.yaml
    (which nothing reads).
  - pip fallback uses sys.executable (python3 does not exist on Windows).
"""

from __future__ import annotations

import asyncio

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from helpers.api import ApiHandler  # type: ignore

PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _which_or_none(cmd: str) -> str | None:
    return shutil.which(cmd)


def _read_plugin_config() -> dict:
    """Read the plugin's merged config (defaults deep-merged under config.json
    by the plugin's get_plugin_config hook)."""
    try:
        from helpers import plugins as framework_plugins

        cfg = framework_plugins.get_plugin_config("watch-skill")
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    cfg = PLUGIN_DIR / "default_config.yaml"
    if cfg.exists():
        try:
            import yaml  # type: ignore

            return yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def _install_cli(extras: str = "[all]") -> dict:
    """Try to install the watch-skill CLI; return a per-step report."""
    steps: list[dict[str, Any]] = []
    if _which_or_none("watch-skill"):
        return {"ok": True, "already_installed": True, "steps": steps}

    pkg = f"watch-skill{extras} @ git+https://github.com/oxbshw/watch-skill"

    # Prefer uv
    if _which_or_none("uv"):
        cmd = ["uv", "tool", "install", pkg]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            steps.append(
                {"tool": "uv", "ok": proc.returncode == 0,
                 "stdout": proc.stdout[-500:], "stderr": proc.stderr[-500:]}
            )
            if proc.returncode == 0:
                return {"ok": True, "via": "uv", "steps": steps}
        except Exception as e:
            steps.append({"tool": "uv", "ok": False, "error": str(e)})

    # Fallback: pipx
    if _which_or_none("pipx"):
        try:
            proc = subprocess.run(
                ["pipx", "install", pkg], capture_output=True, text=True, timeout=300
            )
            steps.append(
                {"tool": "pipx", "ok": proc.returncode == 0,
                 "stdout": proc.stdout[-500:], "stderr": proc.stderr[-500:]}
            )
            if proc.returncode == 0:
                return {"ok": True, "via": "pipx", "steps": steps}
        except Exception as e:
            steps.append({"tool": "pipx", "ok": False, "error": str(e)})

    # Final fallback: pip --user via the running interpreter
    # (python3 is not guaranteed to exist — notably on Windows).
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", pkg],
            capture_output=True, text=True, timeout=300,
        )
        steps.append(
            {"tool": "pip", "ok": proc.returncode == 0,
             "stdout": proc.stdout[-500:], "stderr": proc.stderr[-500:]}
        )
        if proc.returncode == 0:
            return {"ok": True, "via": "pip", "steps": steps}
    except Exception as e:
        steps.append({"tool": "pip", "ok": False, "error": str(e)})

    return {
        "ok": False,
        "error": "config.cli_install_failed",
        "fix": (
            "Install the watch-skill CLI manually: "
            "`uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'`"
        ),
        "steps": steps,
    }


def _register_mcp(cli_path: str) -> dict:
    """Merge the `watch-skill` MCP server into the framework `mcp_servers`
    setting (a JSON string shaped {"mcpServers": {...}})."""
    try:
        from helpers import settings as framework_settings

        current = framework_settings.get_settings()
        raw = current.get("mcp_servers") if isinstance(current, dict) else None
        if not isinstance(raw, str) or not raw.strip():
            raw = '{"mcpServers": {}}'
        data = json.loads(raw)
        if not isinstance(data, dict):
            data = {}
        servers = data.setdefault("mcpServers", {})
        servers["watch-skill"] = {
            "command": cli_path,
            "args": ["serve"],
            "env": {},
        }
        framework_settings.set_settings_delta(
            {"mcp_servers": json.dumps(data, indent=2)}
        )
        return {"ok": True, "via": "settings"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _configure_vision(provider: str, api_key_env: str) -> dict:
    """Store the vision provider + key-env name in the plugin's config.json
    (the key VALUE is never stored — it is read from env at runtime)."""
    if not provider:
        return {"ok": True, "skipped": True}
    if provider not in {"anthropic", "openai", "gemini", "openrouter", "ollama"}:
        return {"ok": False, "error": f"unknown provider: {provider}"}
    key_val = os.environ.get(api_key_env, "") if api_key_env else ""
    vision: dict[str, Any] = {"provider": provider}
    if api_key_env:
        vision["api_key_env"] = api_key_env
    vision["api_key_present"] = bool(key_val)
    try:
        from helpers import plugins as framework_plugins

        cfg = _read_plugin_config()
        cfg.setdefault("vision", {}).update(vision)
        framework_plugins.save_plugin_config("watch-skill", "", "", cfg)
        return {
            "ok": True,
            "provider": provider,
            "api_key_env": api_key_env,
            "api_key_present": bool(key_val),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


class Setup(ApiHandler):
    """POST /api/plugins/watch-skill/setup → per-step report."""

    async def process(self, input_data, request) -> dict:
        body: dict = input_data if isinstance(input_data, dict) else {}

        cfg = _read_plugin_config()
        install_cfg = cfg.get("install", {})
        install = bool(body.get("install", install_cfg.get("auto_install", False)))
        register_mcp = bool(body.get("register_mcp", True))
        vision_provider = body.get("vision_provider", "")
        vision_api_key_env = body.get("vision_api_key_env", "")

        report: dict[str, Any] = {"steps": []}

        if install or shutil.which("watch-skill") is None:
            result = await asyncio.to_thread(
                _install_cli, install_cfg.get("install_extras", "[all]")
            )
            report["steps"].append({"name": "install_cli", **result})
        else:
            report["steps"].append(
                {"name": "install_cli", "ok": True, "skipped": True}
            )

        cli_path = shutil.which("watch-skill") or "watch-skill"

        if register_mcp:
            result = _register_mcp(cli_path)
            report["steps"].append({"name": "register_mcp", **result})

        if vision_provider:
            result = _configure_vision(vision_provider, vision_api_key_env)
            report["steps"].append({"name": "configure_vision", **result})

        report["ok"] = all(step.get("ok") for step in report["steps"])
        return report