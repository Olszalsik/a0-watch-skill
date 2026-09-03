### ws_ask
answer a question about an already-indexed video with timestamped evidence (video intelligence)
args: `video` (required), `question` (required), optional `max_frames`, `include_frames`, `language`
- `video`: a `video_id` from `ws_list` or the original source URL/path
- text-first: the engine attaches frames only when it could not verify text-first; `include_frames` forces them on
- `language`: optional ISO code to force the answer language (e.g. "ar")
never re-run `ws_watch` for a follow-up — ask instead; when the engine says the video does not clearly show the answer, that is the answer — never invent past a refusal
example:
~~~json
{
  "thoughts": ["Video is indexed; ask from the index instead of re-watching."],
  "headline": "Asking about indexed video",
  "tool_name": "ws_ask",
  "tool_args": {
    "video": "aqz-KE-bpKQ",
    "question": "What error code appears at 2:30?"
  }
}
~~~