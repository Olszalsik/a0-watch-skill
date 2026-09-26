### ws_status
poll a watch job by id (video intelligence)
args: `job_id` (required)
polls an engine watch job. `ws_watch` itself always runs in the foreground, so only MCP background jobs (`watch_video`) produce a `job_id`; use this to poll one, or use the MCP `get_status` tool. When the job completes, continue with `ws_ask` against its video_id
example:
~~~json
{
  "thoughts": ["The background watch returned a job_id; check progress."],
  "headline": "Polling watch job",
  "tool_name": "ws_status",
  "tool_args": {
    "job_id": "b1e2c3d4"
  }
}
~~~