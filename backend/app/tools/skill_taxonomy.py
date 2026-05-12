"""skill_taxonomy_lookup: canonicalise + relate skills.

Bundled minimal taxonomy (subset of ESCO/O*NET-style data). Resolves
aliases (e.g. "K8s" → "Kubernetes") and returns related skills + family.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.tools.registry import Tool, registry

_DATA_PATH = Path(__file__).with_name("skill_taxonomy_data.json")
_DATA: dict[str, dict] = json.loads(_DATA_PATH.read_text(encoding="utf-8"))


def _resolve(skill: str) -> dict | None:
    key = skill.lower().strip()
    entry = _DATA.get(key)
    if entry is None:
        return None
    if "alias_of" in entry:
        return _DATA.get(entry["alias_of"])
    return entry


async def _run(args: dict) -> dict:
    skill: str = args["skill"]
    entry = _resolve(skill)
    if entry is None:
        return {"ok": False, "skill": skill, "found": False}
    return {
        "ok": True,
        "skill": skill,
        "found": True,
        "canonical": entry.get("canonical"),
        "family": entry.get("family"),
        "related": entry.get("related", []),
    }


skill_taxonomy_tool = registry.register(
    Tool(
        name="skill_taxonomy_lookup",
        description=(
            "Look up a skill in the canonical taxonomy. Returns the canonical name, "
            "the skill family, and related skills. Use to normalise abbreviations "
            "(e.g. 'K8s') and find transferable skill parents."
        ),
        parameters={
            "type": "object",
            "properties": {
                "skill": {"type": "string", "description": "Skill name to look up"},
            },
            "required": ["skill"],
        },
        run=_run,
    )
)
