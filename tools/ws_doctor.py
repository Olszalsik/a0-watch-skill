"""ws_doctor — run the watch-skill self-healing doctor.

Shells out to `watch-skill doctor` and (optionally) `watch-skill --version`
to print a one-shot health check. Use this whenever any other tool fails
with a dependency or download error, or on first install.

The wrapper does NOT install anything on its own; it returns the install
hint if the CLI is missing so the LLM can present a one-liner to the user.
"""

from ._common import find_cli, format_for_llm, load_plugin_config, run_cli


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
            "uv tool install 'watch-skill[all] @ git+https://github.com/oxbshw/watch-skill'",
            "```",
            "",
            "Fallbacks: `pipx install ...` or `pip install --user ...`",
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
