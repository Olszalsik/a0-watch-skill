### ws_report_mistake
report a wrong video answer so the engine stores a local lesson (video intelligence)
args: `video` (required), `question` (required), `wrong_answer` (required), `correction` (required), optional `session_id`
the engine stores the lesson, applies it to related questions, and where possible re-asks the original question to confirm the fix
use it when the user says a video answer was wrong, or when you realize your own video-based response was incorrect
example:
~~~json
{
  "thoughts": ["My answer cited the wrong timestamp; report the lesson."],
  "headline": "Reporting video-answer mistake",
  "tool_name": "ws_report_mistake",
  "tool_args": {
    "video": "aqz-KE-bpKQ",
    "question": "What happens at 2:30?",
    "wrong_answer": "A crash is shown at 2:30",
    "correction": "A version banner appears at 2:30; the crash is at 3:05"
  }
}
~~~