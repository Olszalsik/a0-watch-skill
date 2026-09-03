### ws_library
ask a question across the whole video library, or show its overview (cross-video memory)
args: `question` or `overview` (json boolean true), optional `k_videos` (how many videos to consult, default from config)
- with `question`: markdown synthesis with per-video timestamp citations
- with `overview=true`: library overview (videos indexed, hours, note counts, recurring entities, lifetime token savings)
orient with `overview=true` first when a question spans multiple videos, then synthesize with a `question`
example:
~~~json
{
  "thoughts": ["No single video answers this; synthesize across the library."],
  "headline": "Asking the video library",
  "tool_name": "ws_library",
  "tool_args": {
    "question": "What did we learn about error handling across all recordings?"
  }
}
~~~