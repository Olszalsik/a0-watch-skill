"""GET /api/plugins/watch_skill/status

Health snapshot for the watch-skill plugin:
  - whether the `watch-skill` CLI is on PATH
  - the CLI's reported version
  - whether the MCP server config is registered with Agent Zero
  - how many videos are in the local index

Used by the WebUI status chip (extensions/python/banners/banner.py) and the plugin
card in Settings → Plugins.

v1.1.0 re-port:
  - GET contract: `get_methods() -> ["GET"]` + `requires_csrf() -> False`
    (POST-only default made this endpoint 405 on plain browser GETs).
  - MCP registration is read from the framework `mcp_servers` setting
    (helpers.settings; a JSON string shaped {"mcpServers": {...}}), not
    from a hardcoded /a0/tmp/settings.json path.
  - the CLI version / index-count subprocesses are cached (60s TTL) so the
    status chip does not spawn blocking subprocesses on every poll.
"""

from __future__ import annotations

import asyncio

import json
import shutil
import subprocess
import time

from helpers.api import ApiHandler  # type: ignore

_CACHE: dict[str, tuple[float, object]] = {}
_CACHE_TTL_S = 60.0


def _cached(key: str, fn):
    """Tiny TTL cache — these spawn subprocesses and are polled repeatedly."""
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and now - hit[0] < _CACHE_TTL_S:
        return hit[1]
    value = fn()
    _CACHE[key] = (now, value)
    return value


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
            # Engine 1.4.x `list` takes no options; the old `--limit 0`
            # (meaning "all") is a usage error there, so this probe silently
            # returned None and the dashboard always reported 0 videos.
            [cli, "list", "--json"],
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
    """Check the framework `mcp_servers` setting (helpers.settings).

    The setting is a JSON STRING shaped {"mcpServers": {...}} stored in
    usr/settings.json — never read that file by hand.
    """
    try:
        from helpers import settings as framework_settings

        current = framework_settings.get_settings()
        raw = current.get("mcp_servers") if isinstance(current, dict) else None
        data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        return isinstance(servers, dict) and "watch-skill" in servers
    except Exception:
        return False


def _plugin_version() -> str:
    try:
        from helpers import plugins as framework_plugins

        return str(
            getattr(framework_plugins.get_plugin_meta("watch_skill"), "version", "")
            or "unknown"
        )
    except Exception:
        return "unknown"

def _ui_flags() -> dict:
    """`ui.*` plugin config, for the WebUI chip/help-button toggles."""
    try:
        from helpers import plugins as framework_plugins

        cfg = framework_plugins.get_plugin_config("watch_skill") or {}
        ui = cfg.get("ui") if isinstance(cfg, dict) else None
        if isinstance(ui, dict):
            return {
                "show_status_chip": bool(ui.get("show_status_chip", True)),
                "show_help_button": bool(ui.get("show_help_button", True)),
            }
    except Exception:
        pass
    return {"show_status_chip": True, "show_help_button": True}


class Status(ApiHandler):
    """GET /api/plugins/watch_skill/status → JSON snapshot."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input_data, request) -> dict:
        cli = shutil.which("watch-skill")
        payload = {
            "ok": True,
            "plugin": "watch_skill",
            # v1.1.1: read from plugin.yaml -- a hardcoded string drifts
            # out of date on every bump.
            "version": _plugin_version(),
            "cli_installed": cli is not None,
            "cli_path": cli,
            # v1.1.1: _cli_version/_indexed_count spawn subprocesses -- run
            # _cached (and the subprocess inside it) on a worker thread so
            # they never block the event loop.
            "cli_version": await asyncio.to_thread(
                _cached, "cli_version", _cli_version
            ),
            "mcp_registered": _cached(
                "mcp_registered", _settings_mcp_registered
            ),
            "indexed_videos": await asyncio.to_thread(
                _cached, "indexed_count", _indexed_count
            ),
            "ui": _ui_flags(),
        }
        payload["ready"] = bool(payload["cli_installed"])
        if not payload["ready"]:
            payload["hint"] = (
                "Install the watch-skill CLI: "
                "`uv tool install 'watch-skill[standard] @ git+https://github.com/oxbshw/watch-skill'`"
            )
        return payload