"""Plugin initialization — runs once when Agent Zero enables this plugin.

Responsibilities (in order):
  1. Print a one-line banner so the user knows watch-skill is active.
  2. Detect the watch-skill CLI; if missing, print the install one-liner
     (never auto-install unless the plugin config says so).
  3. Optionally register the MCP server with Agent Zero's settings.json
     when the framework exposes a helper for it.
  4. Create the per-instance workdir under /a0/usr/workdir/watch-skill.

This module must be import-safe — Agent Zero imports it at boot time.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

PLUGIN_NAME = "watch-skill"
PLUGIN_TITLE = "Watch Skill — Video Intelligence for Agents"


def _plugin_root() -> Path:
    # extensions/python/init/initialize.py → /a0/usr/plugins/watch-skill/
    return Path(__file__).resolve().parents[3]


def _load_plugin_config() -> dict:
    cfg_path = _plugin_root() / "default_config.yaml"
    if not cfg_path.exists():
        return {}
    try:
        import yaml  # type: ignore

        return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _print_banner() -> None:
    print(f"\n🎬  {PLUGIN_TITLE}  (plugin: {PLUGIN_NAME})")


def _check_cli() -> bool:
    """Return True if `watch-skill` is on PATH."""
    return shutil.which("watch-skill") is not None


def _print_install_hint() -> None:
    print("    ⚠️  watch-skill CLI not found on PATH.")
    print("    Install with one of:")
    print("      uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'")
    print("      pipx install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'")
    print("      pip install --user 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'")
    print("    Or run /ws-doctor in the chat to auto-install with a fallback chain.")


def _try_version() -> str | None:
    cli = shutil.which("watch-skill")
    if not cli:
        return None
    try:
        out = subprocess.run(
            [cli, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        if out.returncode == 0:
            v = out.stdout.strip()
            print(f"    ✅ watch-skill CLI ready — {v}")
            return v
    except Exception:
        pass
    return None


def _register_mcp(cli_path: str) -> bool:
    """Surgically merge the MCP server into Agent Zero's settings.json."""
    p = Path("/a0/tmp/settings.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    servers = data.setdefault("mcp_servers", {})
    if "watch-skill" in servers:
        print("    ✅ MCP server already registered (watch-skill)")
        return True
    servers["watch-skill"] = {
        "command": cli_path,
        "args": ["serve"],
        "env": {},
    }
    try:
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"    ✅ MCP server registered in {p}")
        return True
    except Exception as e:
        print(f"    ⚠️  failed to write settings.json: {e}")
        return False


def _ensure_workdir() -> Path:
    wd = Path(os.environ.get("A0_WORKDIR", "/a0/usr/workdir")) / "watch-skill"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def initialize() -> None:
    """Entry point — called by Agent Zero when the plugin is enabled."""
    _print_banner()
    cfg = _load_plugin_config()

    if _check_cli():
        v = _try_version()
        cli_path = shutil.which("watch-skill")
        if cli_path and cfg.get("mcp", {}).get("expose_tools_in_prompt", True):
            _register_mcp(cli_path)
    else:
        _print_install_hint()
        auto = cfg.get("install", {}).get("auto_install", False)
        if auto:
            print("    → auto_install=true, attempting install…")
            try:
                # Lazy import so we don't hard-depend on the api/ dir at boot.
                from api.setup import handler  # type: ignore

                result = handler(
                    type("R", (), {"json": lambda self=None: {"install": True}})()
                )
                ok = result.get("ok", False)
                print(f"    auto-install result: ok={ok}, steps={result.get('steps', [])}")
            except Exception as e:
                print(f"    auto-install failed: {e}")

    _ensure_workdir()
    print("    Docs: https://github.com/oxbshw/watch-skill/tree/main/docs/agents/agent-zero.md")
    print()
