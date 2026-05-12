from app.schemas.pipeline import ParsedJD
from app.skills.base import Skill, SkillContext
from app.skills.parse_jd.prompt import PROMPT


class ParseJDSkill(Skill):
    name = "parse_jd"
    model_tier = "extraction"
    temperature = 0.0
    output_schema = ParsedJD
    prompt = PROMPT

    async def run(self, ctx: SkillContext) -> ParsedJD:
        return await self.run_structured(ctx)  # type: ignore[return-value]
