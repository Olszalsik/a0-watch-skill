### ws_moment
zoom into one specific moment of a watched video with dense sampling (video intelligence)
args: `video` (required), `timestamp` (required), optional `window` (seconds of context, default 10)
- `timestamp`: center of the window (`SS`, `MM:SS`, or `HH:MM:SS`)
use after `ws_ask` or `ws_search` when you need dense frames + transcript + OCR around a single timestamp
example:
~~~json
{
  "thoughts": ["Ask pointed at 02:30; get dense evidence around it."],
  "headline": "Zooming into timestamp",
  "tool_name": "ws_moment",
  "tool_args": {
    "video": "aqz-KE-bpKQ",
    "timestamp": "2:30",
    "window": 15
  }
}
~~~