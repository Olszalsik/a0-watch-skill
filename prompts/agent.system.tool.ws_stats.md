### ws_stats
report the lifetime token-savings meter of the video pipeline (vs naive raw-frame injection)
args: none
surface the numbers to the user when they ask about cost or efficiency of video processing
example:
~~~json
{
  "thoughts": ["User asked how much the video pipeline saves."],
  "headline": "Reading token savings",
  "tool_name": "ws_stats",
  "tool_args": {}
}
~~~