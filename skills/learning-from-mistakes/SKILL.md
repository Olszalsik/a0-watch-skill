---
name: learning-from-mistakes
version: "1.0.0"
description: The user says a video answer was wrong, or you realized your own response was incorrect. Use this to report the mistake to the watch-skill engine so it stores a local lesson, applies it to related questions, and where possible re-asks the original question to confirm the lesson works.
license: MIT
allowed-tools: ws_ask, ws_watch, code_execution_tool, memory_save
user-invocable: true
---

# Learning from mistakes (Agent Zero a0-skill port)

A video answer turned out wrong? Report it. **The watch-skill engine
classifies the mistake, stores it as a local lesson, injects it into
future similar questions, and where possible re-asks the original
question to confirm the lesson works.** Nothing leaves the machine.

## Report a mistake

```text
# MCP call: report_mistake(
#   video=<video_id or original source>,
#   question=<the question that was answered wrongly>,
#   wrong_answer=<what was (wrongly) said>,
#   correction=<what the correct answer actually is>,
#   session_id=<optional, groups lessons under a session>,
# )
```

The engine returns the lesson (`lesson_id`, `error_class`, `content_type`,
`guidance`, `validated`) and, when re-asked, the validation outcome.

## Error classes (what the engine is checking against)

- `acquire.*` — failed to download / extract the video
- `perceive.*` — frame selection or scene detection failed
- `transcribe.*` — captions/Whisper failed
- `index.*` — indexing or retrieval failed
- `vision.*` — visual Q&A gave a wrong answer
- `loop.*` — the loop critic gave a wrong verdict
- `health.*` — environment / dependency error
- `config.*` — user config issue

## Self-correction protocol

1. User says your previous answer was wrong.
2. Re-fetch with `ws_ask` and read the new response — sometimes the engine
   already self-corrects via escalation.
3. Still wrong? Call `report_mistake` with the original question, your
   previous (wrong) answer, and the user's correction.
4. The engine stores a lesson. On the same session, future similar
   questions automatically inject this lesson into the prompt.
5. Where possible, the engine re-asks the original question and returns
   `validated: true` once the lesson is confirmed to work.

## Persist the lesson to Agent Zero memory too

For cross-session recall (so future Agent Zero sessions, not just
watch-skill, know about this), also save a compact summary via the
`memory_save` tool:

```text
memory_save(text="watch-skill lesson: <one-line summary of the correction>", area="watch-skill-lessons")
```

## Trust but verify

The engine is conservative: a lesson only gets applied to *similar*
questions (it classifies by content type + error class). Don't be afraid
to also state the lesson explicitly in your reply — the human will
appreciate the visible correction.
