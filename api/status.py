"""GET /api/plugins/watch-skill/status

Health snapshot for the watch-skill plugin:
  - whether the `watch-skill` CLI is on PATH
  - the CLI's reported version
  - whether the MCP server config is registered with Agent Zero
  - how many videos are in the local index
  - the lifetime token-savings meter (if available)

Used by the WebUI status chip and the plugin card in Settings → Plugins.

Ported to the v2.5 ApiHandler contract (v2.2 used a bare `handler(request)`
function which the framework no longer dispatches).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from helpers.api import ApiHandler  # type: ignore


def _cli_version() -> str | None:
    cli = shutil.which("watch-skill")
    if not cli:
        return None
    try:
        out = subprocess.run(
            [cli, "--version"], capture_output=True, text=True, timeout=10, check=False
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _indexed_count() -> int | None:
    cli = shutil.which("watch-skill")
    if not cli:
        return None
    try:
        out = subprocess.run(
            [cli, "list", "--limit", "0", "--json"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            data = json.loads(out.stdout)
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict) and "videos" in data:
                return len(data["videos"])
    except Exception:
        pass
    return None


def _settings_mcp_registered() -> bool:
    """Check if Agent Zero's tmp/settings.json already lists `watch-skill`."""
    p = Path("/a0/tmp/settings.json")
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        servers = data.get("mcp_servers") or data.get("mcpServers") or {}
        return "watch-skill" in servers
    except Exception:
        return False


class Status(ApiHandler):
    """GET /api/plugins/watch-skill/status → JSON snapshot."""

    async def process(self, input_data, request) -> dict:
        cli = shutil.which("watch-skill")
        payload = {
            "ok": True,
            "plugin": "watch-skill",
            "version": "1.0.0",
            "cli_installed": cli is not None,
            "cli_path": cli,
            "cli_version": _cli_version(),
            "mcp_registered": _settings_mcp_registered(),
            "indexed_videos": _indexed_count(),
        }
        payload["ready"] = bool(payload["cli_installed"])
        if not payload["ready"]:
            payload["hint"] = (
                "Install the watch-skill CLI: "
                "`uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'`"
            )
        return payload
