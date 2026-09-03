### ws_list
show what is already in the local video index (video intelligence)
args: `limit` (optional int, default 50, 0 = no cap), `as_json` (optional bool)
call this BEFORE `ws_watch` — never re-watch a video that is already indexed
returns the indexed videos with their `video_id`s; use a `video_id` with `ws_ask`, `ws_moment`, or `ws_report_mistake`
example:
~~~json
{
  "thoughts": ["Check whether this video was already analyzed."],
  "headline": "Listing indexed videos",
  "tool_name": "ws_list",
  "tool_args": {
    "limit": 20
  }
}
~~~