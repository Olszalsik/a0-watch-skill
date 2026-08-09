"""Extension hooks contributed by the watch-skill plugin.

The Agent Zero framework calls these by name:
  - on_chat_message(msg, context)    → can rewrite or augment a chat message
  - on_tool_call(tool_call, context) → can validate or transform a tool call
  - on_tool_result(result, context)  → can rewrite or filter a tool result
  - on_chat_start(context)           → runs when a new chat begins
  - on_chat_end(context)             → runs when a chat ends
  - on_settings_save(payload)        → runs when the user saves plugin settings

We use the chat-message hook to detect `/watch`, `/ws-doctor`, `/ws-library`,
and `/ws-stats` slash commands and route them to the right native tool.
All other hooks are best-effort: keep them cheap and never block the
agent.
"""

from __future__ import annotations

import re
from typing import Any

# Slash command patterns → (tool_name, kwargs_extractor)
SLASH_COMMANDS: list[tuple[re.Pattern, str, Any]] = [
    (
        re.compile(r"^/watch\s+(.+)$", re.IGNORECASE),
        "ws_watch",
        lambda m: {"source": m.group(1).strip()},
    ),
    (
        re.compile(r"^/ws-doctor\s*$", re.IGNORECASE),
        "ws_doctor",
        lambda m: {},
    ),
    (
        re.compile(r"^/ws-library\s*$", re.IGNORECASE),
        "ws_library",
        lambda m: {"overview": True},
    ),
    (
        re.compile(r"^/ws-stats\s*$", re.IGNORECASE),
        "ws_stats",
        lambda m: {},
    ),
]


def on_chat_message(msg: str, context: dict) -> dict:
    """Detect slash commands; return a tool_call override or pass-through.

    The framework's contract: return either
      - {"passthrough": True} (no change), or
      - {"tool_call": {"name": ..., "args": ...}, "strip_command": True}
    """
    if not msg:
        return {"passthrough": True}
    text = msg.strip()
    for pattern, tool_name, extract in SLASH_COMMANDS:
        m = pattern.match(text)
        if m:
            return {
                "tool_call": {"name": tool_name, "args": extract(m)},
                "strip_command": True,
                "reply_template": (
                    f"🎬 Watch Skill: routing to `{tool_name}`..."
                ),
            }
    return {"passthrough": True}


def on_tool_call(tool_call: dict, context: dict) -> dict:
    """Block obviously dangerous invocations of the native ws_* tools.

    The watch-skill tools are inherently local-first and safe, but we still
    catch a couple of foot-guns: empty `source` for `ws_watch`, oversized
    `max_frames`, etc.
    """
    name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    if name == "ws_watch" and not (args.get("source") or "").strip():
        return {"reject": True, "reason": "ws_watch requires a non-empty `source`."}
    if name in ("ws_watch",) and int(args.get("max_frames", 0) or 0) > 2000:
        return {
            "reject": True,
            "reason": "ws_watch max_frames > 2000 is rejected; use transcript_only or background.",
        }
    if name == "ws_loop" and args.get("mode") == "iterate" and not args.get("loop_id"):
        return {"reject": True, "reason": "ws_loop(iterate) requires `loop_id`."}

    return {"passthrough": True}


def on_tool_result(result: Any, context: dict) -> dict:
    """Cap extremely large watch-skill responses so they don't blow context.

    The native tools already truncate to 12-20k chars, but a chat history
    that re-pastes the full report can compound. We no-op here by default;
    the framework already handles per-message length caps.
    """
    return {"passthrough": True}


def on_chat_start(context: dict) -> dict:
    """Print a one-line welcome so the user knows watch-skill is loaded."""
    try:
        print("🎬  Watch Skill plugin loaded — try `/watch <url>` or just say "
              "'watch this video: ...'.")
    except Exception:
        pass
    return {"passthrough": True}


def on_chat_end(context: dict) -> dict:
    """No-op for now. Future: persist watch-skill lesson summaries to memory."""
    return {"passthrough": True}


def on_settings_save(payload: dict) -> dict:
    """When the user saves settings, also (re)register the MCP server.

    The framework will already persist the config; this hook is for
    side-effects like rewriting the MCP registration with the new path.
    """
    try:
        import json
        import shutil
        from pathlib import Path

        cli = shutil.which("watch-skill")
        if not cli:
            return {"passthrough": True, "note": "CLI not on PATH; skipping MCP re-register"}
        p = Path("/a0/tmp/settings.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
        servers = data.setdefault("mcp_servers", {})
        servers["watch-skill"] = {
            "command": cli, "args": ["serve"], "env": {},
        }
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"passthrough": True, "note": f"re-registered MCP server at {p}"}
    except Exception as e:
        return {"passthrough": True, "note": f"MCP re-register skipped: {e}"}
