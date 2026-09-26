# watch_skill

> Give any Agent Zero session a video input: watch, index, ask, and iterate (THE LOOP). Wraps the upstream `watch-skill` engine (a separate Python package the user installs on the host) as a side-car MCP server, plus native `ws_*` CLI tools, slash commands, API handlers, a WebUI chip + settings panel, and a video-analyst sub-agent.

**Version:** 1.2.0 · **Plugin ID:** `watch_skill` · **Engine:** `watch-skill` 1.4.x

## Purpose

Make video a first-class input for an agent. The upstream MCP server (39 tools) is the primary integration path; the native `ws_*` tools wrap the engine CLI as a fallback for when the MCP server fails to spawn.

## Ownership / Layout

- `hooks.py` (plugin ROOT — the only file the framework loads, `helpers/plugins.py HOOKS_SCRIPT`): `install` (workdir + MCP registration via `helpers.settings.set_settings_delta`, optional auto-install), `pre_update`, `uninstall` (MCP deregistration), `get_plugin_config` (deep-merges `default_config.yaml` UNDER `config.json`), `save_plugin_config` (passthrough).
- `tools/` — 11 `helpers.tool.Tool` subclasses, one per file: `ws_doctor ws_list ws_ask ws_watch ws_status ws_search ws_moment ws_library ws_stats ws_report_mistake ws_loop`, plus `_common.py` (CLI runner, capability probe, config loader, TTL cache, arg coercion, redaction).
- `prompts/` — `agent.system.tool.ws_*.md` (one per tool; this is what registers a tool with the LLM) + `watch-skill-agent.md` (sub-agent persona).
- `api/` — 5 `ApiHandler`s: `status` (GET), `doctor` (POST), `library` (GET), `setup` (POST), `mcp_config` (GET).
- `commands/` — 4 slash commands (`watch`, `ws-doctor`, `ws-library`, `ws-stats`) as `*.command.yaml` + `run(payload)` scripts, dispatched by the `_commands` plugin.
- `extensions/python/banners/banner.py` — topbar status chip. `extensions/python/system_prompt/_10_watch_skill_persona.py` — persona for the `watch_skill-agent` profile.
- `webui/config.html` — Settings panel. `agents/watch_skill-agent/agent.yaml` — sub-agent profile. `skills/` — 4 auxiliary skills.

## Local Contracts

- **Two distinct names, never conflate them.** `hooks.PLUGIN_NAME = "watch_skill"` is the *plugin* identity used by every `get_plugin_config` / `save_plugin_config` / `get_plugin_meta` call. `hooks.MCP_SERVER_NAME = "watch-skill"` is the key written into the user's `mcp_servers` setting. `helpers.plugins.determine_plugin_asset_path` resolves `usr/plugins/<name>/config.json` from the *name passed in*, so a mismatch does not raise — it silently reads a non-existent directory. The installer also requires the directory name to equal `plugin.yaml`'s `name`, and the store index requires `^[a-z0-9_]+$`; hence the underscore in the plugin name and the hyphen only in the MCP server key. If you add a config lookup, use `PLUGIN_NAME`.
- **Tools load `_common.py` by path.** A0 loads tool files as synthetic modules (basename only, no parent package, not in `sys.modules`) and `agent.py:load_classes_from_file(path, Tool)` takes the FIRST `Tool` subclass per file. Every tool file therefore re-execs `_common.py` via `spec_from_file_location`, guarded in `sys.modules` as `_watch_skill_common` and re-executed when its mtime changes.
- **Tool args arrive as strings** (`dict[str,str]`); `arg_str/arg_bool/arg_int/arg_float` coerce.
- **API handlers** need explicit `get_methods() -> ["GET"]` and `requires_csrf() -> False` for read-only endpoints — the framework default is POST + CSRF, which 405s a plain GET. POST endpoints use the framework's `fetchApi` so the `X-CSRF-Token` header is sent.
- **MCP registration** goes through `helpers.settings.set_settings_delta({"mcp_servers": json.dumps(...)})`; the setting is a JSON *string* shaped `{"mcpServers": {...}}`. Never hand-edit settings files.
- **Plugin config** returns `config.json` wholesale (no merge against `default_config.yaml`); the root `get_plugin_config` hook does the deep-merge, so a partial `config.json` is safe.
- **Every blocking subprocess is off the event loop** via `asyncio.to_thread`. This is mandatory: a foreground `ws_watch` runs 600 s, and `api/setup.py` runs a 300 s package install.
- **`plugin.yaml` keys actually parsed** are only `name`, `title`, `description`, `version`, `settings_sections`, `per_project_config`, `per_agent_config`, `always_enabled`. Anything else is silently dropped, so engine requirements live in prose comments, not manifest keys.

## Engine Surface (watch-skill 1.4.x) — verified against upstream

The engine CLI and this wrapper drift independently. Treat this table as the contract; verify with `watch-skill <cmd> --help` before changing any argv.

| Wrapper | Engine invocation | Note |
| --- | --- | --- |
| `ws_watch` | `watch SOURCE` / `batch SOURCE` | **no `--question`, no `--background`** |
| `ws_ask` | `ask VIDEO QUESTION --max-frames N` | |
| `ws_list` | `list` | **no options** |
| `ws_status` | `jobs status JOB_ID` | `status` is not a top-level command |
| `ws_search` | `search QUERY` | no documented options |
| `ws_moment` | *(none)* | MCP-only (`get_moment`); the tool explains this instead of shelling out |
| `ws_library` | `library ask Q --videos N` / `library overview` | flag is `--videos` |
| `ws_stats` | `stats` | |
| `ws_report_mistake` | `lessons add VIDEO Q WRONG CORRECTION [--session S]` | was `report-mistake`; flag is `--session` |
| `ws_loop` | `loop start\|iterate\|status\|video-gen\|game\|monitor`, plus top-level `capture` | `capture` is NOT under `loop` |
| `ws_doctor` | `doctor` | |

**Never hard-code a flag list again.** Use `build_args(base, flags, probe=[...])`: it asks the installed engine which options the subcommand accepts (cached 300 s) and returns `(argv, dropped)`. Pass the drop list to `dropped_flags_notice()` so the model is told what was ignored instead of receiving a raw usage error. `probe` is the subcommand path *without* positionals. An inconclusive probe drops nothing — a failed probe must never silently disable every option.

**Capability asymmetry.** The MCP surface is a superset of the CLI (39 tools vs 22 CLI-reachable behaviours). When a request needs something the CLI lacks (`get_moment`, background `watch_video`, live/batch/workspace tools), the native tool should say so and name the MCP tool — it should not attempt a doomed subprocess.

**Install spec is `watch-skill[standard]`.** Since 1.4.0 a bare install has no frames, no retrieval and no MCP server. `[all]` is not a declared extra; `[transcribe]` and `[vlm]` never were.

**Install location is an isolated tool env** (`uv tool`, falling back to `pipx`). There is deliberately **no `pip` fallback**: hooks run in the framework runtime, so `sys.executable -m pip install --user` targets the framework venv's user site, which is not on `PATH` — the install would report success while `find_cli()` kept returning `None`.

## Configuration

Every key in `default_config.yaml` has a live consumer; a key with no consumer is a bug, because a settings toggle that silently does nothing reads as "configured". Live keys: `install.auto_install`, `install.install_extras`, `vision.provider`, `vision.model`, `vision.api_key_env`, `index.library_chunk_k_videos`, `loop.default_max_iterations`, `loop.default_duration`, `ui.show_status_chip`, `ui.show_help_button`.

`vision.provider` / `vision.model` are translated into `WATCHSKILL_VISION_PROVIDER` / `WATCHSKILL_VISION_MODEL` by `_common.apply_vision_env()` on every call. An explicit shell env var always wins over the settings UI, and a provider is only injected when its credential is actually present.

**Secrets.** API keys live only in environment variables, under the engine's own `WATCHSKILL_*` names. `_SECRET_ENV_NAMES` is derived from `VISION_ENV_VARS` so the redaction list cannot drift from the passthrough list — that drift previously leaked prefixed keys into tool output and therefore into the model context. Never print a key; add its name to `VISION_ENV_VARS` so it is forwarded *and* redacted.

## Work Guidance

- `run_cli` spawns the child in its own process group (`start_new_session` / `CREATE_NEW_PROCESS_GROUP`) and kills the group on timeout, because the engine spawns `ffmpeg`/`yt-dlp` that would otherwise survive as orphans holding the download open.
- `run_cli` flags Typer/Click usage rejections as `usage_error` so `format_for_llm` can return actionable guidance instead of dumping a usage string at the model.
- When a tool's behaviour depends on the engine version, degrade with a message naming the MCP equivalent; do not silently substitute different arguments.
- Keep `_common.py` free of framework imports at module scope so the path-based tool loader stays cheap.

## Verification

- `python -c "import ast,pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('usr/plugins/watch_skill').rglob('*.py')]"`
- Load all 11 tools through the `_watch_skill_common` preamble and confirm no failures.
- `GET /api/plugins/watch_skill/status` returns the JSON health snapshot.
- `build_args` unit behaviour: a probe lacking `--question`/`--background` drops them and reports them; an inconclusive probe drops nothing.
- In chat: `/ws-doctor`, `/watch <url>`, `/ws-library`, `/ws-stats` appear in the slash menu and send their prompts.
- Settings → Plugins shows the config card and Save persists to `config.json`.

## Store Submission

The runtime manifest and the hub index are **different files with different schemas in different repositories**. There is no local `plugin-hub/` directory — do not create one.

- Runtime: this repo's own `plugin.yaml` (installed to `usr/plugins/watch_skill/`).
- Discovery: `plugins/watch_skill/index.yaml` in a fork of `agent0ai/a0-plugins`.

**This plugin's contents must sit at its repository root**, not nested in a folder, so the installer finds `plugin.yaml` on extraction. The CI validator enforces, deterministically:

- folder name `^[a-z0-9_]+$`, no leading `_`, no dashes — hence `watch_skill`
- the remote `plugin.yaml`'s `name` exactly equals the index folder name
- only `title`, `description`, `github`, `tags`, `screenshots`; `title` ≤ 50, `description` ≤ 500, whole file ≤ 2000 chars, `tags` ≤ 5, `screenshots` ≤ 5 and reachable
- `github` points at a public repo that has `plugin.yaml` at its root, and is not already claimed by another indexed plugin
- one plugin per PR, and only `index.yaml` (+ an optional square `thumbnail.*` ≤ 20 KB) in the folder

Also required: a root `LICENSE` (its absence is a guaranteed validator warning and is required for index listing) and a `README.md` covering purpose, install, configuration, external services and their costs, usage, cleanup, and screenshots with no private data. `always_enabled` stays `false` — it is framework-reserved, and setting it forces the plugin on with no way to disable it.

`settings_sections` should list only `agent` and/or `external`: those are the only two values that actually mount the plugin settings subsection in the WebUI.

## See also

- `plugin.yaml` — manifest (parsed keys documented inline)
- `default_config.yaml` — defaults (deep-merged by the `get_plugin_config` hook)
- `README.md` — user-facing docs
- Framework: `helpers/plugins.py` (lifecycle + config), `helpers/api.py` (dispatch + CSRF), `helpers/subagents.py` (paths), `plugins/_commands/helpers/commands.py` (slash commands)
