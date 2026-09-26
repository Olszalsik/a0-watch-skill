### ws_watch
watch a new video: download, extract frames, OCR, transcribe, and index it (video intelligence)
args: `source` (required), optional `start`, `end`, `max_frames`, `transcript_only`, `batch`, `limit`
- `source`: any yt-dlp-supported URL (1800+ sites), direct media URL, HLS/DASH manifest, or local file path
- `start` / `end`: optional timestamps (`SS`, `MM:SS`, or `HH:MM:SS`) to zoom into a section with denser sampling
- `transcript_only`: use json boolean `true` to skip frame extraction and download (fastest)
- `batch`: use json boolean `true` to treat `source` as a playlist/channel/folder/comma-separated list (cap with `limit`, default 20)
- `max_frames`: cap on extracted frames (0 = engine default; values > 2000 are rejected)
this tool runs the CLI, which has no `--question` and no `--background` option: it always watches in the foreground and returns the index result. To also answer a question, call `ws_watch` (no question), then `ws_ask` with the question against the resulting `video_id`. To run the watch as a background job instead, use the MCP tools `watch_video` (returns a `job_id`) and `get_status` (poll it).
always check `ws_list` first; do not re-watch an indexed video — use `ws_ask` for follow-ups
example:
~~~json
{
  "thoughts": ["New video, not in the index. Watch it, then ask my question."],
  "headline": "Watching video",
  "tool_name": "ws_watch",
  "tool_args": {
    "source": "https://youtu.be/aqz-KE-bpKQ",
    "max_frames": 200
  }
}
~~~
