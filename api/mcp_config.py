"""GET /api/plugins/watch-skill/mcp-config

Returns the `mcpServers` JSON snippet Agent Zero needs to register the
watch-skill MCP server. Used by both the auto-enable path and the
"copy MCP config" button in the WebUI.

Ported to the v2.5 ApiHandler contract (v2.2 used a bare `handler(request)`
function which the framework no longer dispatches).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from helpers.api import ApiHandler  # type: ignore


def _discover_cli() -> str:
    """Return the absolute path to the watch-skill binary (or `watch-skill`)."""
    return shutil.which("watch-skill") or "watch-skill"


def _is_already_registered() -> bool:
    p = Path("/a0/tmp/settings.json")
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        servers = data.get("mcp_servers") or data.get("mcpServers") or {}
        return "watch-skill" in servers
    except Exception:
        return False


class McpConfig(ApiHandler):
    """GET /api/plugins/watch-skill/mcp-config → JSON."""

    async def process(self, input_data, request) -> dict:
        cli = _discover_cli()
        # Agent Zero accepts the same mcpServers shape as Claude Desktop / Cursor.
        snippet = {
            "mcpServers": {
                "watch-skill": {
                    "command": cli,
                    "args": ["serve"],
                    "env": {},
                }
            }
        }
        return {
            "ok": True,
            "snippet": snippet,
            "auto_registered": _is_already_registered(),
            "docs": (
                "https://github.com/oxbshw/watch-skill/tree/main/docs/agents/agent-zero.md"
            ),
        }
