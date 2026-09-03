# watch-skill

> Give any Agent Zero session a video input: watch, index, ask, and iterate (THE LOOP). Wraps the upstream `watch-skill` CLI (a separate Python package the user installs on the host) as a side-car MCP server, plus native `ws_*` tools, slash commands, API handlers, a WebUI chip + settings panel, and a video-analyst sub-agent.

**Version:** 1.1.0 · **Plugin ID:** `watch-skill`

## Purpose

Give any Agent Zero session a video input: watch, index, ask, and iterate (THE LOOP). The upstream watch-skill MCP server (23 tools) is the primary integration path; the plugin's native tools wrap the CLI as a fallback for when the MCP server fails to spawn.

## Ownership / Layout

- `hooks.py` (plugin ROOT) — the only hook file the framework loads (`helpers/plugins.py HOOKS_SCRIPT`): `install` (workdir + MCP registration via `helpers.settings.set_settings_delta`, optional auto-install), `pre_update`, `uninstall` (MCP deregistration), `get_plugin_config` (deep-merges `default_config.yaml` UNDER `config.json`), `save_plugin_config` (passthrough).
- `tools/` — 11 native tools (`ws_doctor ws_list ws_ask ws_watch ws_status ws_search ws_moment ws_library ws_stats ws_report_mistake ws_loop`), one `helpers.tool.Tool` subclass per file, plus `_common.py` (CLI runner, config loader, TTL cache, string-arg coercion).
- `prompts/` — `agent.system.tool.ws_*.md` (one per native tool; this is what registers a tool with the LLM) + `watch-skill-agent.md` (sub-agent persona).
- `api/` — 5 ApiHandler classes: `status` (GET), `doctor` (POST), `library` (GET), `setup` (POST), `mcp_config` (GET). Route = `/api/plugins/watch-skill/<file basename>`.
- `commands/` — 4 slash commands (`watch`, `ws-doctor`, `ws-library`, `ws-stats`) as `*.command.yaml` + script `run(payload)` files, dispatched by the `_commands` plugin.
- `extensions/python/banners/banner.py` — topbar status chip (framework banner contract: append dicts to `banners`).
- `extensions/python/system_prompt/_10_watch_skill_persona.py` — appends the persona when `agent.config.profile == "watch-skill-agent"`.
- `extensions/webui/page-head/watch-skill-help.js` — topbar chip + help popover (polls `/api/plugins/watch-skill/status`).
- `webui/config.html` — Settings → Plugins panel (binds `pluginSettingsPrototype.settings` via `config`; the modal Save → `save_config` → config.json).
- `agents/watch-skill-agent/agent.yaml` — sub-agent profile (name/title/description/context/enabled only).
- `skills/` — 4 auxiliary a0 skills. `config/settings_schema.yaml` — decorative (no framework version renders it; `webui/config.html` is the real settings UI).

## Local Contracts

- **Tools**: A0 loads tool files as synthetic modules (basename only, no parent package, not in sys.modules) and `agent.py` `load_classes_from_file(path, Tool)` takes the FIRST Tool subclass per file. The hyphen in `watch-skill` makes package imports impossible, so every tool file loads `_common.py` via `spec_from_file_location` guarded in sys.modules as `_watch_skill_common`.
- **Tool args arrive as strings** (`dict[str,str]`); `_common.arg_str/arg_bool/arg_int/arg_float` coerce.
- **API handlers**: `class X(ApiHandler)` + `async def process(self, input_data, request)`; GET handlers override `get_methods() -> ["GET"]` and `requires_csrf() -> False` (default is POST + CSRF → 405 on plain GETs).
- **MCP registration** goes through `helpers.settings.set_settings_delta({"mcp_servers": json.dumps(...)})` — the setting is a JSON STRING shaped `{"mcpServers": {...}}` in `usr/settings.json`. Never write settings files by hand.
- **Plugin config**: `helpers.plugins.get_plugin_config("watch-skill")` returns config.json WHOLESALE (no merge against default_config.yaml); the root `get_plugin_config` hook does the deep-merge, making partial config.json safe.
- **agent.yaml**: the framework's SubAgent model parses only name/title/description/context/enabled/avatar; everything else is silently ignored. Persona comes from the system_prompt extension; model/tools overrides would go in `agents/watch-skill-agent/settings.json` (loaded by the framework's `_15_load_profile_settings.py`).
- **plugin.yaml**: only name/title/description/version/settings_sections/per_project_config/per_agent_config/always_enabled are parsed; `webui/config.html` existing is what enables the settings modal.

## v1.1.0 Re-port (this pass)

The v1.0.0 tree was written against a v2.2-era contract that no framework version dispatches. This pass re-ported everything:

- **F1/F2** — tools were plain functions with relative imports (all dead): rewrote all 11 as `Tool` subclasses with the `_watch_skill_common` importlib preamble; added `ws_status`, `ws_moment`, `ws_stats`, `ws_report_mistake` (prompt files created for all 11).
- **F3/F5** — `hooks/hooks.py` (never loaded, invented hook names) and `extensions/python/init/{initialize,self_diagnose}.py` (nonexistent extension points) deleted; real root `hooks.py` created; slash commands moved to `commands/` under the `_commands` dispatch contract.
- **F4** — banner rewritten from `render(context) -> str` to `WatchSkillBanner(Extension)` appending banner dicts; library-count subprocess cached 60s.
- **F6** — GET endpoints got `get_methods()/requires_csrf()` overrides (were 405).
- **F7** — page-head JS URL fixed `/plugins/...` → `/api/plugins/watch-skill/status`, uses `fetchApi` (dynamic import, raw-fetch fallback), tolerates 404.
- **F8** — MCP-registration checks read the framework `mcp_servers` setting (helpers.settings) instead of a hardcoded `/a0/tmp/settings.json`.
- **F9** — hooks.py install calls `api/setup.py::_install_cli` via a path-based import (hyphenated dir blocks packages).
- **F10** — phantom `a0_plugin_runtime` import removed from api/setup.py; real settings UI added at `webui/config.html`.
- **F11** — agent.yaml trimmed to the parsed keys; persona moved to `extensions/python/system_prompt/_10_watch_skill_persona.py`.
- **F12** — plugin.yaml rewritten: dead keys removed (documented as comments), version 1.1.0.
- **F13** — status.py subprocess probes cached 60s TTL.
- **F14** — setup.py vision config now persists to config.json via `helpers.plugins.save_plugin_config` (was an unread `config/settings.yaml`); MCP registration via `set_settings_delta`.
- **F15** — setup.py pip fallback uses `sys.executable` (no `python3` on Windows).
- **F16** — ws_loop numeric args coerced (`_coerce_float/_coerce_int/_coerce_script`).
- **F17** — README/AGENTS.md doc URLs corrected to `/api/plugins/watch-skill/<handler>`.

## Verification

- `GET /api/plugins/watch-skill/status` from a browser returns the JSON health snapshot (canonical ApiHandler-shape test).
- In chat: `/ws-doctor`, `/watch <url>`, `/ws-library`, `/ws-stats` should appear in the slash menu and send their prompts.
- Settings → Plugins → Watch Skill shows the config card; Save persists to config.json.

## See also

- `plugin.yaml` — manifest (parsed keys documented inline)
- `default_config.yaml` — defaults (deep-merged by the `get_plugin_config` hook)
- `README.md` — user-facing docs
- Framework references: `helpers/plugins.py` (lifecycle + config), `helpers/api.py` (API dispatch), `helpers/subagents.py` (agents/prompts/extensions path resolution), `plugins/_commands/helpers/commands.py` (slash commands)