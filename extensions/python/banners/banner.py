"""Banner for the watch-skill plugin — shown in the WebUI topbar.

v1.1.0 re-port to the framework banner extension contract
(extensions/python/banners/_10_unsecured_connection.py): the framework
instantiates this file's Extension subclass and calls `execute(banners=[],
frontend_context={}, ...)` — the plugin appends banner dicts, it does NOT
return an HTML fragment (the v1.0.0 `render(context) -> str` function was
never dispatched).

The banner:
  - shows whether the watch-skill CLI is installed + library size
  - degrades to an "install needed" warning when the CLI is missing
  - caches the library-count subprocess (60s TTL) so the banner endpoint
    stays fast.
"""

from __future__ import annotations

import asyncio

import json
import shutil
import subprocess
import time
from html import escape

from helpers.extension import Extension  # type: ignore

_DOCS_URL = "https://github.com/oxbshw/watch-skill/tree/main/docs/agents/agent-zero.md"
_INSTALL_URL = "https://github.com/oxbshw/watch-skill#start-in-60-seconds"

_LIB_CACHE: tuple[float, int | None] | None = None
_LIB_CACHE_TTL_S = 60.0

_CHIP_CSS = (
    ".ws-chip{display:inline-flex;align-items:center;gap:6px;"
    "padding:4px 10px;border-radius:999px;font-size:12px;"
    "text-decoration:none;margin-left:8px;line-height:1.2;"
    "border:1px solid rgba(127,127,127,.25);}"
    ".ws-chip-ok{background:rgba(40,200,120,.12);color:#1f7a4d;}"
    ".ws-chip-warn{background:rgba(255,170,0,.15);color:#9a5a00;}"
    ".ws-chip-icon{font-size:14px;}"
    ".ws-chip-label{font-weight:500;}"
)


def _cli_installed() -> bool:
    return shutil.which("watch-skill") is not None


def _library_count() -> int | None:
    global _LIB_CACHE
    now = time.monotonic()
    if _LIB_CACHE is not None and now - _LIB_CACHE[0] < _LIB_CACHE_TTL_S:
        return _LIB_CACHE[1]
    count: int | None = None
    cli = shutil.which("watch-skill")
    if cli:
        try:
            out = subprocess.run(
                [cli, "list", "--limit", "0", "--json"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                data = json.loads(out.stdout)
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict) and "videos" in data:
                    count = len(data["videos"])
        except Exception:
            count = None
    _LIB_CACHE = (now, count)
    return count


def _chip(icon: str, label: str, klass: str, href: str, hint: str) -> str:
    return (
        f'<a class="{escape(klass)}" href="{escape(href)}" target="_blank" '
        f'title="{escape(hint)}" rel="noopener">'
        f'<span class="ws-chip-icon">{icon}</span>'
        f'<span class="ws-chip-label">{escape(label)}</span>'
        f"<style>{_CHIP_CSS}</style>"
        f"</a>"
    )


class WatchSkillBanner(Extension):
    """Append the watch-skill status chip to the WebUI banners list."""

    async def execute(self, banners: list = [], frontend_context: dict = {}, **kwargs):
        try:
            installed = await asyncio.to_thread(_cli_installed)
            if installed:
                n_videos = await asyncio.to_thread(_library_count)
                label = "Watch Skill ready"
                if n_videos is not None:
                    label = f"Watch Skill · {n_videos} videos"
                html = _chip("🎬", label, "ws-chip ws-chip-ok", _DOCS_URL, "Open docs")
            else:
                html = _chip(
                    "⚠️",
                    "Watch Skill — install needed",
                    "ws-chip ws-chip-warn",
                    _INSTALL_URL,
                    "Install one-liner",
                )
            banners.append(
                {
                    "id": "watch-skill-status",
                    "type": "info" if installed else "warning",
                    "priority": 50,
                    "title": "Watch Skill",
                    "html": html,
                    "dismissible": True,
                    "source": "backend",
                }
            )
        except Exception:
            # A banner must never break the /banners endpoint.
            return