"""Native Python tools for the watch-skill plugin.

These tools are CLI wrappers around the `watch-skill` binary. They exist
so the LLM can do basic read operations even if the MCP server fails to
spawn. The MCP server (23 tools) is still the primary integration path.

Public surface (what Agent Zero exposes to the LLM):
    ws_doctor()
    ws_list()
    ws_ask()
    ws_watch()
    ws_status()
    ws_search()
    ws_moment()
    ws_library()
    ws_stats()
    ws_report_mistake()
    ws_loop()
"""

from .ws_doctor import ws_doctor
from .ws_list import ws_list
from .ws_ask import ws_ask
from .ws_watch import ws_status, ws_watch
from .ws_search import ws_moment, ws_search
from .ws_library import ws_library, ws_report_mistake, ws_stats
from .ws_loop import ws_loop

__all__ = [
    "ws_doctor",
    "ws_list",
    "ws_ask",
    "ws_watch",
    "ws_status",
    "ws_search",
    "ws_moment",
    "ws_library",
    "ws_stats",
    "ws_report_mistake",
    "ws_loop",
]
