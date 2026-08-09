---
name: the-loop
version: "1.0.0"
description: The user built or changed something visual — a UI, an animation, a game, a generated video — and wants it verified, or asks "why does my UI look wrong", "check that the fix actually worked", "does the animation glitch". Use this to record the running thing, critique the recording against plain-language pass criteria, and iterate until it passes with before/after proof.
license: MIT
allowed-tools: ws_loop, code_execution_tool
user-invocable: true
---

# THE LOOP (Agent Zero a0-skill port)

A screenshot shows a moment; it cannot show a flow. **THE LOOP** records
the actual running target, watches the recording, and judges it against
pass criteria you state in plain language. The loop only observes — **you**
apply the fixes, then iterate. On pass it renders a before/after MP4 + GIF
as proof.

## UI / web page / desktop window

```text
ws_loop(
  mode="start",
  target="<url | screen: | window:<title> | file>",
  pass_criteria="<plain-language pass criteria>",
  script=[...],                 # optional, same replayed every iteration
  max_iterations=5,
  duration=8.0,
)
# ...apply the suggested fixes to the code...
ws_loop(mode="iterate", loop_id="<id>")
```

- Pass criteria are ordinary sentences: "the checkout completes, no error
  toast ever appears, the total is never NaN". Negative claims ("never X")
  and exemplars ("a real price (like $29.00)") are both understood and
  enforced deterministically.
- `script` replays the same clicks/fills every iteration, so the
  comparison is honest.
- Only call `iterate` after you actually changed something. It diffs
  against the previous iteration: fixed / unchanged / new.

## Generated video (Manim, Remotion, ffmpeg, AI-gen)

```text
ws_loop(
  mode="video-gen",
  spec="<what the video must show>",
  generator_cmd="<render command>",
  output="<video file the command writes>",
  max_iterations=5,
  timeout=600,
)
```

Re-runs the generator each iteration and judges the fresh render against
the spec.

## Game / simulation

```text
ws_loop(
  mode="game",
  target="<canvas-url | window:<title> | screen:>",
  pass_criteria="<e.g. SCORE must show a number, never NaN>",
  run_cmd="<launch cmd>",        # optional
  script=[...],                   # optional, for canvas games
  duration=10.0,
  max_iterations=5,
)
```

Catches the failures screenshots miss: a NaN score counter, black
flicker frames, sprites that vanish mid-motion.

## Watch for a condition (monitoring)

```text
ws_loop(
  mode="monitor",
  source="<folder | url | screen: | window:<title>>",
  condition="<plain-language condition>",
  interval=10.0,
  max_checks=10,
  sample_seconds=5.0,
)
```

**Bounded — it always terminates.** Events land in `events.jsonl` under
the loop directory as structured records.

## Record without judging

```text
ws_loop(mode="capture", target="<...>", duration=10.0)
```

Capture alone never critiques; it just records, analyzes, and indexes.
Use `loop_start` when there are pass criteria.

## Discipline

- The loop **never** edits the user's code or UI. Apply the suggested fix
  yourself, then iterate.
- Always inspect the previous iteration's diff (fixed/unchanged/new) before
  iterating again. No-progress stops the loop automatically.
- On pass, the engine renders a self-contained MP4+GIF proof; do not skip
  the visual confirmation.
