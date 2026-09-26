"""GET /api/plugins/watch_skill/library

Returns the `watch-skill library overview` JSON — videos indexed, hours,
note counts, recurring entities, recent additions, and the lifetime
token-savings meter. Used by the WebUI settings card.

Ported to the v2.5 ApiHandler contract (v2.2 used a bare `handler(request)`
function which the framework no longer dispatches).
"""

from __future__ import annotations

import asyncio

import json
import shutil
import subprocess

from helpers.api import ApiHandler  # type: ignore


class Library(ApiHandler):
    """GET /api/plugins/watch_skill/library → JSON."""

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input_data, request) -> dict:
        cli = shutil.which("watch-skill")
        if not cli:
            return {
                "ok": False,
                "error": "config.cli_missing",
                "fix": "Install the watch-skill CLI first.",
            }

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [cli, "library", "overview", "--json"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "health.timeout"}

        if proc.returncode != 0 or not proc.stdout.strip():
            return {
                "ok": False,
                "error": "library.empty",
                "stderr_tail": proc.stderr[-1000:],
            }
        try:
            return {"ok": True, "data": json.loads(proc.stdout)}
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "library.invalid_json",
                "stdout_tail": proc.stdout[-1000:],
            }
