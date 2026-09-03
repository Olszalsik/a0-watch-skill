"""Watch Skill plugin hooks (Agent Zero v2.5 contract).

The framework loads ONLY this file (plugin root `hooks.py`, see
helpers.plugins.HOOKS_SCRIPT) and calls exported functions by name via
helpers.plugins.call_plugin_hook(). The only hook names the framework
ever calls are:

  - install()          (plugins/_plugin_installer/helpers/install.py)
  - pre_update()
  - uninstall()        (helpers/plugins.py)
  - get_plugin_config(default=..., agent=..., ...)
  - get_default_plugin_config(file_path=...)
  - save_plugin_config(default=..., settings=..., ...)

The v1.0.0 file lived at hooks/hooks.py (never loaded) and invented
on_chat_message / on_tool_call / ... handlers that no framework version
dispatches — those are gone. Slash commands now live in commands/
(*.command.yaml + script), the banner in extensions/python/banners/, and
per-agent prompt injection in extensions/python/system_prompt/.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

PLUGIN_NAME = "watch-skill"
PLUGIN_DIR = Path(__file__).resolve().parent

# MCP server registration (shape matches helpers.mcp_handler.MCPConfig:
# {"mcpServers": {"<name>": {"command": ..., "args": [...]}}}).
MCP_SERVER_NAME = "watch-skill"
MCP_SERVER_CONFIG = {"command": "watch-skill", "args": ["serve"], "env": {}}


def _log(message: str) -> None:
    sys.stdout.write(f"[watch-skill] {message}\n")
    sys.stdout.flush()


def _ensure_workdir() -> str:
    """Create the per-instance workdir under the framework workdir."""
    try:
        from helpers import files

        workdir = files.get_abs_path_dockerized("usr", "workdir", "watch-skill")
    except Exception:
        import os

        base = os.environ.get("A0_WORKDIR", str(Path.home() / ".a0-workdir"))
        workdir = str((Path(base) / "watch-skill").resolve())
    try:
        Path(workdir).mkdir(parents=True, exist_ok=True)
        return workdir
    except Exception as e:
        _log(f"could not create workdir {workdir}: {e}")
        return workdir


def _import_setup_module():
    """Path-import api/setup.py (hyphenated plugin dir blocks pkg imports)."""
    import importlib.util

    api_dir = PLUGIN_DIR / "api"
    spec = importlib.util.spec_from_file_location(
        "_watch_skill_setup", api_dir / "setup.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["_watch_skill_setup"] = module
    spec.loader.exec_module(module)
    return module


def _register_mcp_in_settings() -> dict:
    """Merge the watch-skill MCP server into the framework `mcp_servers`
    setting (helpers.settings.set_settings_delta). The setting is a JSON
    STRING shaped {"mcpServers": {...}} — never write files by hand.
    """
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
        if MCP_SERVER_NAME in servers:
            return {"ok": True, "registered": True, "note": "already registered"}
        cli = shutil.which("watch-skill") or "watch-skill"
        servers[MCP_SERVER_NAME] = {
            "command": cli,
            "args": list(MCP_SERVER_CONFIG["args"]),
            "env": {},
        }
        framework_settings.set_settings_delta(
            {"mcp_servers": json.dumps(data, indent=2)}
        )
        return {"ok": True, "registered": True, "command": cli}
    except Exception as e:
        return {"ok": False, "registered": False, "error": str(e)}


def install() -> dict:
    """Runs once after the plugin is installed/enabled (plugin installer)."""
    report: dict[str, Any] = {"ok": True, "steps": []}

    workdir = _ensure_workdir()
    report["workdir"] = workdir

    cli = shutil.which("watch-skill")
    if cli:
        try:
            import subprocess

            out = subprocess.run(
                [cli, "--version"], capture_output=True, text=True,
                timeout=10, check=False,
            )
            version = out.stdout.strip() if out.returncode == 0 else ""
        except Exception:
            version = ""
        report["cli"] = version or "on PATH (version unknown)"
        mcp = _register_mcp_in_settings()
        report["mcp_registration"] = mcp
        if not mcp.get("ok"):
            report["ok"] = False
    else:
        report["cli_missing"] = True
        report["install_hint"] = (
            "uv tool install "
            "'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'"
        )
        try:
            cfg = json.loads(
                (PLUGIN_DIR / "config.json").read_text(encoding="utf-8")
            ) if (PLUGIN_DIR / "config.json").exists() else {}
        except Exception:
            cfg = {}
        if cfg.get("install", {}).get("auto_install", False):
            # F9: call api/setup.py::_install_cli directly (path-based import;
            # the hyphenated plugin dir blocks normal package imports).
            try:
                _setup = _import_setup_module()
                result = _setup._install_cli(
                    cfg.get("install", {}).get("install_extras", "[all]")
                )
                report["auto_install"] = result
                if not result.get("ok"):
                    report["ok"] = False
                else:
                    mcp = _register_mcp_in_settings()
                    report["mcp_registration"] = mcp
            except Exception as e:
                report["auto_install"] = {"ok": False, "error": str(e)}
                report["ok"] = False
        else:
            _log(
                "watch-skill CLI not found on PATH. Install with: "
                "uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill' "
                "(or set install.auto_install=true in the plugin settings)."
            )

    return report


def pre_update() -> dict:
    """Runs before the plugin is updated (plugin installer)."""
    return {"ok": True, "note": "watch-skill: no pre-update snapshot needed"}


def uninstall() -> dict:
    """Runs before the plugin is deleted (helpers.plugins.uninstall_plugin)."""
    removed = False
    try:
        from helpers import settings as framework_settings

        current = framework_settings.get_settings()
        raw = current.get("mcp_servers") if isinstance(current, dict) else None
        data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if isinstance(servers, dict) and MCP_SERVER_NAME in servers:
            servers.pop(MCP_SERVER_NAME, None)
            framework_settings.set_settings_delta(
                {"mcp_servers": json.dumps(data, indent=2)}
            )
            removed = True
    except Exception as e:
        return {"ok": False, "note": f"MCP deregistration skipped: {e}"}
    return {"ok": True, "mcp_deregistered": removed}


# ---------------------------------------------------------------------------
# Config hooks
# ---------------------------------------------------------------------------


def _deep_merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def get_plugin_config(default: Any = None, **kwargs) -> Any:
    """Merge default_config.yaml UNDER the loaded config.

    helpers.plugins.get_plugin_config() returns config.json wholesale when
    it exists (no merge against default_config.yaml), so user-saved settings
    would lose every key absent from the save. This hook deep-merges the
    defaults underneath, making partial config.json files safe.
    """
    try:
        import yaml

        defaults = yaml.safe_load(
            (PLUGIN_DIR / "default_config.yaml").read_text(encoding="utf-8")
        ) or {}
    except Exception:
        return default
    if isinstance(default, dict):
        merged = _deep_merge(defaults, default)
        return merged
    return defaults


def save_plugin_config(default: Any = None, settings: Any = None, **kwargs) -> Any:
    """Passthrough: persist exactly what the settings UI sent."""
    return default