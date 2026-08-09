"""Banner for the watch-skill plugin — shown in the WebUI topbar.

The framework calls `render(context)` with the current chat context and
expects an HTML fragment. We render a compact status chip that:
  - shows whether the watch-skill CLI is installed
  - shows the library size (videos indexed)
  - links to the docs / agent-zero guide
  - degrades to a clean "install" link when the CLI is missing
"""

from __future__ import annotations

import json
import shutil
import subprocess
from html import escape
from pathlib import Path

PLUGIN_NAME = "watch-skill"
PLUGIN_TITLE = "Watch Skill"
DOCS_URL = "https://github.com/oxbshw/watch-skill/tree/main/docs/agents/agent-zero.md"


def _cli_installed() -> bool:
    return shutil.which("watch-skill") is not None


def _library_count() -> int | None:
    cli = shutil.which("watch-skill")
    if not cli:
        return None
    try:
        out = subprocess.run(
            [cli, "list", "--limit", "0", "--json"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            data = json.loads(out.stdout)
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict) and "videos" in data:
                return len(data["videos"])
    except Exception:
        pass
    return None


def render(context: dict | None = None) -> str:
    """Return an HTML fragment for the WebUI topbar."""
    installed = _cli_installed()
    n_videos = _library_count() if installed else None

    if installed:
        icon = "🎬"
        label = f"{PLUGIN_TITLE} ready"
        if n_videos is not None:
            label = f"{PLUGIN_TITLE} · {n_videos} videos"
        klass = "ws-chip ws-chip-ok"
        hint = "Open docs ↗"
        href = DOCS_URL
    else:
        icon = "⚠️"
        label = "Watch Skill — install needed"
        klass = "ws-chip ws-chip-warn"
        hint = "Install one-liner"
        href = (
            "https://github.com/oxbshw/watch-skill#start-in-60-seconds"
        )

    return (
        f'<a class="{klass}" href="{escape(href)}" target="_blank" '
        f'title="{escape(hint)}" rel="noopener">'
        f'<span class="ws-chip-icon">{icon}</span>'
        f'<span class="ws-chip-label">{escape(label)}</span>'
        f'<style>'
        f".ws-chip{{display:inline-flex;align-items:center;gap:6px;"
        f"padding:4px 10px;border-radius:999px;font-size:12px;"
        f"text-decoration:none;margin-left:8px;line-height:1.2;"
        f"border:1px solid rgba(127,127,127,.25);}}"
        f".ws-chip-ok{{background:rgba(40,200,120,.12);color:#1f7a4d;}}"
        f".ws-chip-warn{{background:rgba(255,170,0,.15);color:#9a5a00;}}"
        f".ws-chip-icon{{font-size:14px;}}"
        f".ws-chip-label{{font-weight:500;}}"
        f"</style>"
        f"</a>"
    )
