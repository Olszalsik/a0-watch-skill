### ws_moment
report that moment zoom has no CLI fallback, and name the MCP tool to use instead (video intelligence)
args: `video` (required), `timestamp` (required), optional `window` (seconds of context, default 10)
- `timestamp`: center of the window (`SS`, `MM:SS`, or `HH:MM:SS`)
the engine provides moment zoom only through the MCP tool `get_moment`; the CLI has no `moment` subcommand, so this tool cannot return dense frames itself. Call the MCP tool `get_moment(video, timestamp, window)` for dense frames + transcript + OCR around a timestamp. For a question about that moment rather than raw evidence, `ws_ask` works over the CLI.
example:
~~~json
{
  "thoughts": ["Ask pointed at 02:30; I need dense evidence around it."],
  "headline": "Zooming into timestamp",
  "tool_name": "ws_moment",
  "tool_args": {
    "video": "aqz-KE-bpKQ",
    "timestamp": "2:30",
    "window": 15
  }
}
~~~
