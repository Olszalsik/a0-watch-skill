### ws_loop
THE LOOP: record a running target, critique the recording against pass criteria, and iterate with proof (visual verification)
actions (arg `mode`): `start`, `iterate`, `status`, `capture`, `video-gen`, `game`, `monitor`
- `start`: `target` + `pass_criteria` (+ optional `script` json array) — record and critique
- `iterate`: `loop_id` only — call ONLY after you actually applied a fix
- `status`: `loop_id` only — inspect persisted loop state
- `capture`: `target` (+ optional `duration` seconds) — record footage, no judgment
- `video-gen`: `spec` + `generator_cmd` + `output` (+ `workdir`, `timeout`) — iterate a video generator (Manim/Remotion/ffmpeg/AI)
- `game`: `target` + `pass_criteria` (+ `run_cmd`, `script`, `duration`) — iterate a canvas/window game
- `monitor`: `source` + `condition` (+ `interval`, `max_checks`, `sample_seconds`) — watch a folder/live target for a condition
the loop only OBSERVES — it never edits the user's code or UI; you apply the fix between iterations, then call `iterate`
numeric args (`duration`, `interval`, `sample_seconds`, `max_iterations`, `max_checks`, `timeout`) accept numbers or numeric strings; invalid values fall back to plugin defaults
on pass the engine renders before/after proof (MP4 + GIF, per `loop.proof_format` config)
example:
~~~json
{
  "thoughts": ["Verify the fix visually with a loop."],
  "headline": "Starting verification loop",
  "tool_name": "ws_loop",
  "tool_args": {
    "mode": "start",
    "target": "http://localhost:3000",
    "pass_criteria": "The login form shows an error message on empty submit"
  }
}
~~~