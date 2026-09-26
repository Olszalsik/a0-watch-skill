"""ws_doctor — run the watch-skill self-healing doctor.

Shells out to `watch-skill doctor` and (optionally) `watch-skill --version`
to print a one-shot health check. Use this whenever any other tool fails
with a dependency or download error, or on first install.

The wrapper does NOT install anything on its own; it returns the install
hint if the CLI is missing so the LLM can present a one-liner to the user.

v1.1.0 re-port: tool files are loaded by A0 as synthetic modules (basename
only, no parent package), so `_common` is imported by absolute path instead
of a relative import. One Tool class per file (framework contract).
"""

from __future__ import annotations

import asyncio

import importlib.util
import sys
from pathlib import Path

from helpers.tool import Response, Tool

# Path-based import of _common.py (the plugin dir name contains a hyphen, so
# `usr.plugins.watch-skill` is not an importable package).
_common_path = Path(__file__).resolve().parent / "_common.py"
_common_mtime = _common_path.stat().st_mtime
_ws_common = sys.modules.get("_watch_skill_common")
# v1.1.1: reuse the cached module only if _common.py has not changed since
# it was executed. Without this, a Hub/plugin update left running agents on
# the STALE cached module until a full server restart; and a module whose
# exec_module() raised mid-init stayed poisoned in sys.modules forever
# (no __ws_common_mtime__ attribute -> re-executed on the next load).
if _ws_common is not None and getattr(_ws_common, "__ws_common_mtime", None) != _common_mtime:
    _ws_common = None
if _ws_common is None:
    _spec = importlib.util.spec_from_file_location("_watch_skill_common", _common_path)
    _ws_common = importlib.util.module_from_spec(_spec)
    sys.modules["_watch_skill_common"] = _ws_common
    _spec.loader.exec_module(_ws_common)
    _ws_common.__ws_common_mtime = _common_mtime

arg_bool = _ws_common.arg_bool
find_cli = _ws_common.find_cli
format_for_llm = _ws_common.format_for_llm
load_plugin_config = _ws_common.load_plugin_config
run_cli = _ws_common.run_cli


def ws_doctor(also_print_version: bool = True, fix: bool = False) -> str:
    """Run `watch-skill doctor` and return a human-readable report.

    Args:
        also_print_version: also report `watch-skill --version` before the
            doctor output, so the LLM has both pieces of context in one call.
        fix: if True, the doctor is allowed to apply its own fixes
            (download ffmpeg / yt-dlp into the managed bin dir). The engine
            is conservative — it will only apply safe self-heals.

    Returns:
        Markdown string ready to drop into a chat reply.
    """
    cli = find_cli()
    if not cli:
        cfg = load_plugin_config()
        install = cfg.get("install", {})
        lines = [
            "## watch-skill doctor",
            "",
            "**Status:** ❌ `watch-skill` CLI not found on PATH.",
            "",
            "**Fix (one-liner):**",
            "",
            "```bash",
            "uv tool install 'watch-skill[standard] @ git+https://github.com/oxbshw/watch-skill'",
            "```",
            "",
            "Fallbacks: `pipx install '<same spec>'` (there is no pip fallback: "
            "installing into the framework venv leaves the binary off PATH)",
        ]
        if not install.get("auto_install", False):
            lines.append("")
            lines.append(
                "(Set `install.auto_install=true` in the plugin settings to "
                "have the plugin run this for you.)"
            )
        return "\n".join(lines)

    parts: list[str] = ["## watch-skill doctor", ""]
    if also_print_version:
        v = run_cli(["--version"], timeout=15)
        if v["ok"]:
            parts.append(f"**Engine version:** `{v['stdout'].strip()}`")
        else:
            parts.append(
                f"**Engine version:** ⚠️ could not detect — {v['stderr'].strip()}"
            )
    parts.append("")
    args = ["doctor"]
    if fix:
        args.append("--fix")
    parts.append("### Health check")
    parts.append("")
    parts.append("```")
    parts.append(format_for_llm(run_cli(args, timeout=180), max_chars=8000))
    parts.append("```")
    return "\n".join(parts)


class WsDoctor(Tool):
    async def execute(self, **kwargs) -> Response:
        args = self.args or {}
        report = await asyncio.to_thread(
            ws_doctor,
            also_print_version=arg_bool(args, "also_print_version", True),
            fix=arg_bool(args, "fix", False),
        )
        return Response(message=report, break_loop=False)