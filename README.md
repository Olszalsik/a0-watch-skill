# Watch Skill - Agent Zero Plugin

> **Watch. Remember. Fix. Verify.**
> Give any Agent Zero session a video input: watch, index, ask, and iterate
> (THE LOOP). 23 MCP tools + a CLI + REST + native Python wrappers, with a
> specialized "watch-skill video analyst" sub-agent and auxiliary skills for
> watching videos, asking with timestamped evidence, running THE LOOP, and
> learning from mistakes.

This is an **Agent Zero plugin port** of the open-source
[oxbshw/watch-skill](https://github.com/oxbshw/watch-skill) project
(per the official [Agent Zero guide](https://github.com/oxbshw/watch-skill/blob/main/docs/agents/agent-zero.md)).
It does **not** vendor the upstream Python engine - that is installed at
runtime via `uv tool install` and runs as a side-car MCP server.

---

## Capabilities

| Capability | What you get |
|---|---|
| **Watch** | Scene-aware frames, on-screen text (OCR), and local-first transcription from 1,800+ sites, live HLS/DASH streams, local media, meetings, browsers, windows, and desktops. |
| **Remember** | A persistent, searchable index with timestamp citations, hybrid keyword+semantic retrieval, cross-video synthesis, and reusable lessons. |
| **Verify** | A capture -> critique -> fix -> proof loop (`THE LOOP`) for browser flows, UIs, generated video, gameplay, and monitored streams. |

---

## What this plugin ships

| Layer | Files | Notes |
|---|---|---|
| **Manifest** | `plugin.yaml` + `default_config.yaml` + `config/settings_schema.yaml` | Settings card renders under Agent Zero -> Settings -> Plugins. |
| **Agent profile** | `agents/watch-skill-agent/agent.yaml` + `prompts/watch-skill-agent.md` | A focused "video analyst" sub-agent inheriting the developer profile. |
| **MCP server** | `plugin.yaml#mcp_servers` | Auto-registers `watch-skill` with Agent Zero's Settings -> MCP. |
| **Native tools** | `tools/ws_*.py` (7 tools) | CLI fallbacks so the LLM can do read operations even when the MCP server fails to spawn. |
| **API endpoints** | `api/*.py` (5 endpoints) | `/plugins/watch-skill/{status,doctor,library,setup,mcp-config}`. |
| **Auxiliary skills** | `skills/{watching-videos,asking-with-evidence,the-loop,learning-from-mistakes}/SKILL.md` | 4 a0 skills. |
| **Hooks** | `hooks/hooks.py` | Slash commands (`/watch`, `/ws-doctor`, `/ws-library`, `/ws-stats`) + safety checks. |
| **Init / diagnose** | `extensions/python/init/{initialize,self_diagnose}.py` | Runs on plugin enable; "Run diagnostic" in Settings. |
| **WebUI** | `extensions/webui/page-head/watch-skill-help.js` + `extensions/python/banners/banner.py` | Topbar status chip + help popover. |

---

## Install

### 1. Enable the plugin

Drop the plugin directory into `/a0/usr/plugins/watch-skill/` (or install
via the Plugin Hub), then toggle it on in **Settings -> Plugins -> Watch
Skill**.

### 2. Install the watch-skill CLI (one-liner)

The plugin will **not** install the engine by default - run this in your
shell:

```bash
uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'
```

Or, in the chat, simply say:

> /ws-doctor

...and the plugin will print the right one-liner (and try the fallback
chain if the preferred one isn't on PATH).

If you want the plugin to install automatically on enable, set
`install.auto_install=true` in the plugin settings.

### 3. Configure a vision provider (optional)

Transcription, OCR, and search work **without** an API key. To enable
visual Q&A and the loop critic, pick a provider in
**Settings -> Plugins -> Watch Skill -> Vision provider** (or set the
matching env var):

| Provider | Env var to set |
|---|---|
| `anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `gemini` | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) |
| `openrouter` | `OPENROUTER_API_KEY` |
| `ollama` | (no key - local model server) |

The plugin forwards these env vars to the MCP subprocess so the key is
**never** pasted into chat.

### 4. Smoke test (3 steps, taken from the upstream docs)

1. New chat: *"Watch https://www.youtube.com/watch?v=aqz-KE-bpKQ and tell
   me what happens at 0:10."*
2. Watch the tool router pick `watch_video`.
3. Follow up: *"what color is the bird?"* - should route to `ask_video`,
   no re-processing.

---

## Slash commands

| Command | What it does |
|---|---|
| `/watch <url-or-path>` | Watch a video (download, OCR, transcribe, index). |
| `/ws-doctor` | Run `watch-skill doctor` (self-heal ffmpeg / yt-dlp). |
| `/ws-library` | Show the local video library overview. |
| `/ws-stats` | Show the lifetime token-savings meter. |

---

## Native tools (CLI fallbacks)

These are available to the LLM even if the MCP server fails to spawn:

| Tool | Purpose |
|---|---|
| `ws_doctor()` | Run `watch-skill doctor`. |
| `ws_list()` | Show the indexed videos. |
| `ws_ask(video, question)` | Text-first question with timestamps. |
| `ws_watch(source, question, ...)` | Watch a new video. |
| `ws_status(job_id)` | Poll a backgrounded `ws_watch`. |
| `ws_search(query)` | Hybrid search across the index. |
| `ws_moment(video, timestamp)` | Zoom into a timestamp. |
| `ws_library(question, ...)` | Cross-video memory. |
| `ws_stats()` | Token-savings meter. |
| `ws_report_mistake(...)` | Store a local lesson. |
| `ws_loop(mode, ...)` | THE LOOP - capture, iterate, video-gen, game, monitor. |

The **MCP server** (23 tools, auto-injected into the system prompt) is
still the primary integration path - these are belt-and-braces.

---

## REST API (for the WebUI + external clients)

| Method + path | Purpose |
|---|---|
| `GET  /plugins/watch-skill/status` | CLI installed? MCP registered? Library size? |
| `POST /plugins/watch-skill/doctor` | Run `watch-skill doctor` (optional `{"fix": true}`). |
| `GET  /plugins/watch-skill/library/overview` | Full library overview JSON. |
| `GET  /plugins/watch-skill/mcp-config` | The `mcpServers` snippet (for copy-paste). |
| `POST /plugins/watch-skill/setup` | Install CLI + register MCP + set vision provider. |

---

## Running Agent Zero inside Docker

The original upstream doc calls this out - the MCP server needs to run
**inside the same container** as Agent Zero, and the storage directory
(`~/.watch-skill/`) should be mounted back to the host:

```bash
docker run -it \
  -v ~/.watch-skill:/root/.watch-skill \
  your/agent-zero-image
```

Inside the container:

```bash
# Install the engine once (or run /ws-doctor in the chat)
uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'

# Run the MCP server (already wired in by this plugin)
watch-skill serve
```

Alternatively, run the server on the host with `watch-skill serve --http`
and configure a remote streaming-HTTP entry instead.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Topbar chip is red and says "install needed" | Run `/ws-doctor` in the chat. |
| `watch-skill: command not found` | The CLI isn't on PATH. Install with `uv tool install ...` and restart the shell. |
| `error: config.cli_missing` from a tool | Same - install the CLI. |
| MCP server doesn't show up in the LLM | Toggle the plugin off/on, or check Settings -> MCP for the `watch-skill` entry. |
| `permission denied` writing to `~/.watch-skill` | Mount that path back to the host (see Docker section). |
| Loop says "the video does not clearly show the answer" | That's the engine's honest floor - don't invent past it. |

---

## References

- Upstream project: <https://github.com/oxbshw/watch-skill>
- Agent Zero guide (original): <https://github.com/oxbshw/watch-skill/blob/main/docs/agents/agent-zero.md>
- MCP tool reference: <https://github.com/oxbshw/watch-skill/blob/main/docs/tools/README.md>
- `THE LOOP` design: <https://github.com/oxbshw/watch-skill/blob/main/docs/guides/the-loop.md>
- Cost policy: <https://github.com/oxbshw/watch-skill/blob/main/docs/cost.md>

## License

MIT - see `LICENSE`.
