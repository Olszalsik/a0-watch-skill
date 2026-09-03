### ws_watch
watch a new video: download, extract frames, OCR, transcribe, and index it (video intelligence)
args: `source` (required), optional `question`, `start`, `end`, `max_frames`, `transcript_only`, `background`, `batch`, `limit`
- `source`: any yt-dlp-supported URL (1800+ sites), direct media URL, HLS/DASH manifest, or local file path
- `transcript_only`: use json boolean `true` to skip frame extraction and download (fastest)
- `background`: use json boolean `true` for long videos — returns a `job_id` instantly; poll it with `ws_status`
- `batch`: use json boolean `true` to treat `source` as a playlist/channel/folder/comma-separated list (cap with `limit`, default 20)
- `max_frames`: cap on extracted frames (0 = engine default; values > 2000 are rejected)
always check `ws_list` first; do not re-watch an indexed video — use `ws_ask` for follow-ups
example:
~~~json
{
  "thoughts": ["New video, not in the index. Watch it in the background."],
  "headline": "Watching video",
  "tool_name": "ws_watch",
  "tool_args": {
    "source": "https://youtu.be/aqz-KE-bpKQ",
    "question": "What happens in the first minute?",
    "background": true
  }
}
~~~