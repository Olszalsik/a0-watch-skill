"""POST /api/plugins/watch-skill/doctor

Runs `watch-skill doctor` and returns the result as JSON. Optionally
applies safe self-heals (download ffmpeg / yt-dlp) when the request body
contains `"fix": true`.

Ported to the v2.5 ApiHandler contract (v2.2 used a bare `handler(request)`
function which the framework no longer dispatches).
"""

from __future__ import annotations

import asyncio

import shutil
import subprocess
from typing import Any

from helpers.api import ApiHandler  # type: ignore


class Doctor(ApiHandler):
    """POST /api/plugins/watch-skill/doctor — body: `{"fix": true|false}`."""

    async def process(self, input_data: dict, request) -> dict:
        body: dict[str, Any] = input_data if isinstance(input_data, dict) else {}
        fix = bool(body.get("fix", False))

        cli = shutil.which("watch-skill")
        if not cli:
            return {
                "ok": False,
                "error": "config.cli_missing",
                "fix": (
                    "Install the watch-skill CLI: "
                    "`uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'`"
                ),
            }

        args = [cli, "doctor"]
        if fix:
            args.append("--fix")
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                args,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "health.timeout"}
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-8000:],  # tail the output for the response
            "stderr": proc.stderr[-2000:],
        }
