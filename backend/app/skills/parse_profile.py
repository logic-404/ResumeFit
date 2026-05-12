"""Skill: extract structured ProfileData from raw resume text."""
from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from app.schemas.pipeline import ProfileData
from app.skills.base import Skill, SkillContext

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract structured candidate data from a resume. Return only "
            "fields explicitly present. Do not invent skills, dates, or roles. "
            "If a field is not present, omit it. For LaTeX source: ignore markup, "
            "extract semantic content only.",
        ),
        (
            "human",
            "Resume source format: {source_format}\n\nResume content:\n\n{resume_text}",
        ),
    ]
)


class ParseProfileSkill(Skill):
    name = "parse_profile"
    model_tier = "extraction"
    temperature = 0.0
    output_schema = ProfileData
    prompt = _PROMPT

    async def run(self, ctx: SkillContext) -> ProfileData:
        return await self.run_structured(ctx)  # type: ignore[return-value]
