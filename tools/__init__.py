"""Native Python tools for the watch-skill plugin.

These tools are CLI wrappers around the `watch-skill` binary. They exist
so the LLM can do basic read operations even if the MCP server fails to
spawn. The MCP server (23 tools) is still the primary integration path.

v1.1.0 re-port: each tool file exposes exactly ONE `helpers.tool.Tool`
subclass (the framework loads only the first Tool class per file), named
after the file. A0 loads tool files as synthetic modules, so this package
__init__ intentionally performs no imports.

Public surface (what Agent Zero exposes to the LLM):
    ws_doctor            tools/ws_doctor.py
    ws_list              tools/ws_list.py
    ws_ask               tools/ws_ask.py
    ws_watch             tools/ws_watch.py
    ws_status            tools/ws_status.py
    ws_search            tools/ws_search.py
    ws_moment            tools/ws_moment.py
    ws_library           tools/ws_library.py
    ws_stats             tools/ws_stats.py
    ws_report_mistake    tools/ws_report_mistake.py
    ws_loop              tools/ws_loop.py
"""