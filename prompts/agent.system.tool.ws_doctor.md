### ws_doctor
run the watch-skill self-healing doctor (video intelligence health check)
args: optional `fix` (json boolean true to allow safe self-heals: download ffmpeg / yt-dlp), optional `also_print_version` (default true)
call this whenever any other ws_* tool fails with a dependency or download error, or on first install
the wrapper does NOT install the CLI on its own; if the CLI is missing it returns a one-line install hint to relay to the user
example:
~~~json
{
  "thoughts": ["ws_ask failed with a transcription dependency error."],
  "headline": "Running watch-skill doctor",
  "tool_name": "ws_doctor",
  "tool_args": {
    "fix": true
  }
}
~~~