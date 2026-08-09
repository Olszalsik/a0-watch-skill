# watch-skill

> Give any Agent Zero session a video input: watch, index, ask. Wraps the upstream `watch-skill` CLI (a separate Python package the user installs on the host) and exposes its `doctor` / `library overview` / `setup` / `status` capabilities to the A0 WebUI.

**Version:** 1.0.0 · **Plugin ID:** `watch-skill`

## Purpose

Give any Agent Zero session a video input: watch, index, ask. Wraps the upstream `watch-skill` CLI (a separate Python package the user installs on the host) and exposes its `doctor` / `library overview` / `setup` / `status` capabilities to the A0 WebUI.

## Ownership / Layout

- `api/doctor.py` — POST /api/plugins/watch-skill/doctor (runs `watch-skill doctor`, optional `--fix`)
- `api/library.py` — GET /api/plugins/watch-skill/library/overview
- `api/mcp_config.py` — GET /api/plugins/watch-skill/mcp-config (returns the mcpServers JSON snippet)
- `api/setup.py` — POST /api/plugins/watch-skill/setup (install CLI, register MCP, configure vision)
- `api/status.py` — GET /api/plugins/watch-skill/status
- `agents/` — agent profile preloaded with watch-skill tools
- `hooks/` — custom directory (no `hooks.py`); plugin does not use the v2.5 lifecycle hooks
- `tools/` — agent-callable video-search / transcript tools

## Local Contracts

- **API handlers use the v2.5 ApiHandler contract**: each `api/<name>.py` defines `class X(ApiHandler)` with `async def process(self, input_data, request)`. v2.2-era bare `handler(request)` functions are NOT dispatched by v2.5's `helpers/api.py:238` (`load_classes_from_file(file, ApiHandler)`). The 5 handlers in this plugin were all ported from the v2.2 convention to ApiHandler — see git history for the exact diff.
- No `hooks.py` (uses a custom `hooks/` subdirectory instead). The scanner flags this as a finding but it is intentional — the plugin does not need install / pre_update / uninstall.
- The plugin does NOT bundle the `watch-skill` CLI; the user must install it separately (the API's `setup` endpoint can do this for them). The plugin reads `shutil.which('watch-skill')` on every API call and returns `cli_missing` if it is absent.

## v2.5 Status

- All 5 API handlers ported from `def handler(request)` to `class X(ApiHandler): async def process(...)` in the v2.5 cleanup pass. JSON body is now read from `input_data` (the framework parses it), not from `request.json()` (which doesn't exist on Flask's request object the way the v2.2 code assumed).

## Verification

Hit GET /api/plugins/watch-skill/status from a browser. Before the port this returned 404 'API endpoint not found'; after the port it returns a JSON health snapshot. The status code is the canonical test that the ApiHandler shape is correct.

## See also

- `plugin.yaml` — manifest (name, version, settings_sections, per_project_config, per_agent_config)
- `default_config.yaml` — defaults (referenced by `install()` and the WebUI settings UI)
- `README.md` — user-facing docs (what the plugin does from a user's perspective)
- Framework references: `helpers/plugins.py` (lifecycle), `helpers/api.py` (API dispatch), `helpers/ui_server.py` (asset serving)
