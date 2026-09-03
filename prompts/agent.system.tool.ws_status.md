### ws_status
poll a backgrounded watch job (video intelligence)
args: `job_id` (required)
use after `ws_watch` with `background=true`; repeat until the job completes, then continue with `ws_ask`
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