---
name: watching-videos
version: "1.0.0"
description: The user shared a video URL, a YouTube/TikTok/stream link, a local video file, a screen recording, a meeting recording, or a playlist/folder of videos — "watch this", "summarize this video", "what's in this recording". Use this to actually watch the video — download, extract frames, OCR, transcribe, and index it — instead of guessing from the title or asking the user to describe it.
license: MIT
allowed-tools: ws_watch, ws_list, ws_search, ws_doctor, code_execution_tool
user-invocable: true
---

# Watching videos (Agent Zero a0-skill port)

You don't have a video input; this skill gives you one. Anything a user
hands you — a YouTube link, a TikTok, a lecture, a meeting recording, a
screen capture, an `.mp4` on disk — goes through the same pipeline: frames
(scene-aware, deduplicated), OCR, transcript (captions first, local
Whisper offline fallback), all persisted into one persistent index.

## Before watching: check the index

```text
ws_list()
```

If the video was already analyzed — this session or any earlier one —
**do NOT watch it again**. Use the asking skill instead:

```text
ws_ask(video_id_or_url, "<question>")
```

## One video

```text
ws_watch(source="<url-or-path>", question="<original question>", start=None, end=None, max_frames=None)
```

- Works on any yt-dlp-supported site (1800+), direct media URLs,
  HLS/DASH manifests (`duration` bounds live streams), and local files.
- Video over ~10 minutes and the user cares about one part → use
  `start`/`end` for dense sampling of that window.
- User only needs what was said → set `transcript_only=True` (fastest,
  often no video download at all).

The report prints `Indexed: <video_id>`, frames with `t=MM:SS`
timestamps, OCR text, and the transcript. Read every frame path listed —
in a single message, parallel Read calls — then answer from frames + OCR
+ transcript, citing timestamps.

## Many videos (playlist, channel, folder)

```text
ws_watch(sources="<playlist-url-or-folder>", limit=20)  # batch mode
```

Everything lands in the same index; one broken video never stops the
rest. Afterwards a single `ws_search("<phrase>")` spans the whole batch.

## First run on a machine

If any tool fails with a dependency error, run `ws_doctor()` once — it
installs missing ffmpeg / yt-dlp itself. **No API key is required** for
any of this; transcription is local by default and the video file never
leaves the machine.

## Frame budget discipline

- `watch_video` is expensive; `ask_video` is free. After a video is in the
  index, never re-watch it.
- Use `--max-frames` to cap frame extraction on long videos; the engine
  scene-deduplicates so you still see every distinct moment.
- The MCP server returns at most `WATCHSKILL_RESPONSE_FRAME_CAP` images
  per response (default: 4). Trust the engine to choose when frames are
  necessary.
