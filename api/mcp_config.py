"""GET /api/plugins/watch-skill/mcp_config

Returns the `mcpServers` JSON snippet Agent Zero needs to register the
watch-skill MCP server. Used by both the auto-enable path and the
"copy MCP config" button in the WebUI.

v1.1.0 re-port:
  - GET contract: `get_methods() -> ["GET"]` + `requires_csrf() -> False`.
  - registration is checked against the framework `mcp_servers` setting
    (helpers.settings; a JSON string shaped {"mcpServers": {...}}), not a
    hardcoded /a0/tmp/settings.json path.
"""

from __future__ import annotations

import json
import shutil

from helpers.api import ApiHandler  # type: ignore


def _discover_cli() -> str:
    """Return the absolute path to the watch-skill binary (or `watch-skill`)."""
    return shutil.which("watch-skill") or "watch-skill"


def _is_already_registered() -> bool:
    try:
        from helpers import settings as framework_settings

        current = framework_settings.get_settings()
        raw = current.get("mcp_servers") if isinstance(current, dict) else None
        data = json.loads(raw) if isinstance(raw, str) and raw.strip() else {}
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        return isinstance(servers, dict) and "watch-skill" in servers
    except Exception:
        return False


class McpConfig(ApiHandler):
    """GET /api/plugins/watch-skill/mcp_config → JSON."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

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