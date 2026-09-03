"""Per-agent persona injection for the watch-skill sub-agent.

v1.1.0 re-port: agent.yaml keys like `prompt_include` are not parsed by the
framework's SubAgent model, so the persona file is appended here instead —
the same mechanism plugins/_whatsapp_integration uses for its profiles.
Only fires for the watch-skill-agent profile, where `agent.read_prompt()`
resolves prompts/watch-skill-agent.md from the plugin's prompts/ dir.
"""

from __future__ import annotations

from helpers.extension import Extension  # type: ignore

PROFILE = "watch-skill-agent"
PERSONA_PROMPT = "watch-skill-agent.md"


class WatchSkillPersona(Extension):
    """Append the watch-skill persona to the sub-agent's system prompt."""

    async def execute(self, system_prompt: list[str] = [], loop_data=None, **kwargs):
        try:
            agent = getattr(self, "agent", None)
            if not agent or getattr(agent.config, "profile", "") != PROFILE:
                return
            persona = agent.read_prompt(PERSONA_PROMPT)
            if persona and persona.strip():
                system_prompt.append(persona.strip())
        except Exception:
            # A persona must never break the system prompt build.
            return