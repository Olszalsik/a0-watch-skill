"""Plugin self-diagnose — invoked by Settings → Plugins → Run diagnostic.

Returns a dict with `ok`, `checks` (per-step results), and `fix` (a single
string for the worst failure, suitable for a chat reply).

Checks performed (in order):
  1. watch-skill CLI on PATH
  2. CLI --version (smoke test)
  3. MCP server registered in /a0/tmp/settings.json
  4. `watch-skill list` (index reachable)
  5. plugin directory layout (tools/, skills/, api/ present)
  6. optional: `watch-skill doctor` (set fast=False to run)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

PLUGIN_NAME = "watch-skill"


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _check(name: str, fn) -> dict:
    try:
        ok, detail = fn()
        return {"name": name, "ok": bool(ok), "detail": detail}
    except Exception as e:
        return {"name": name, "ok": False, "detail": f"exception: {e}"}


def self_diagnose(fast: bool = True) -> dict:
    """Run all checks; return a structured report.

    Args:
        fast: if True, skip the slow `watch-skill doctor` step (default).
    """
    checks: list[dict] = []

    # 1. CLI on PATH
    def c1():
        cli = shutil.which("watch-skill")
        return (bool(cli), cli or "watch-skill CLI not found on PATH")

    checks.append(_check("cli_on_path", c1))
    cli = shutil.which("watch-skill")

    # 2. CLI --version
    if cli:
        def c2():
            try:
                out = subprocess.run(
                    [cli, "--version"],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                return (out.returncode == 0, out.stdout.strip() or out.stderr.strip())
            except Exception as e:
                return (False, str(e))
        checks.append(_check("cli_version", c2))

    # 3. MCP registered
    def c3():
        p = Path("/a0/tmp/settings.json")
        if not p.exists():
            return (False, "settings.json missing — plugin will re-register on next enable")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            servers = data.get("mcp_servers") or data.get("mcpServers") or {}
            if "watch-skill" in servers:
                return (True, servers["watch-skill"])
            return (False, "watch-skill server not present in mcp_servers")
        except Exception as e:
            return (False, f"could not parse settings.json: {e}")
    checks.append(_check("mcp_registered", c3))

    # 4. Index reachable (only if CLI present)
    if cli:
        def c4():
            try:
                out = subprocess.run(
                    [cli, "list", "--limit", "0", "--json"],
                    capture_output=True, text=True, timeout=15, check=False,
                )
                if out.returncode == 0:
                    try:
                        data = json.loads(out.stdout or "[]")
                        n = len(data) if isinstance(data, list) else (
                            len(data.get("videos", [])) if isinstance(data, dict) else None
                        )
                        return (True, f"index reachable, {n} videos")
                    except json.JSONDecodeError:
                        return (True, "index reachable (non-JSON list output)")
                return (False, out.stderr.strip() or f"exit {out.returncode}")
            except Exception as e:
                return (False, str(e))
        checks.append(_check("index_reachable", c4))

    # 5. Plugin layout
    def c5():
        root = _plugin_root()
        required = ["tools", "skills", "api", "agents", "prompts"]
        missing = [d for d in required if not (root / d).is_dir()]
        if missing:
            return (False, f"missing dirs: {missing}")
        return (True, "layout ok")
    checks.append(_check("plugin_layout", c5))

    # 6. doctor (slow)
    if not fast and cli:
        def c6():
            try:
                out = subprocess.run(
                    [cli, "doctor"], capture_output=True, text=True, timeout=180, check=False,
                )
                return (out.returncode == 0, out.stdout[-500:] or out.stderr[-500:])
            except Exception as e:
                return (False, str(e))
        checks.append(_check("doctor", c6))

    ok_all = all(c["ok"] for c in checks)
    failing = [c for c in checks if not c["ok"]]
    fix = ""
    if failing:
        first = failing[0]
        fix = f"{first['name']}: {first['detail']}"
    return {
        "ok": ok_all,
        "checks": checks,
        "fix": fix,
        "summary": f"{sum(c['ok'] for c in checks)}/{len(checks)} checks passed",
    }
