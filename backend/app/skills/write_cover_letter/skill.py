"""Cover-letter skill.

Pre-tool phase: retrieve evidence for the top matched skills (from gap
analysis) and optionally pull a couple of company facts via web_search.
Single LLM call → CoverLetter. Uses the generation tier with mild
temperature so regenerate produces variation.
"""
from __future__ import annotations

import json

from app.config import settings
from app.schemas.pipeline import CoverLetter
from app.skills.base import Skill, SkillContext
from app.skills.write_cover_letter.prompt import PROMPT
from app.tools.registry import registry


async def _retrieve_for_matched(matched_skills: list[dict], k: int = 3) -> str:
    if not matched_skills:
        return "(no matched skills)"
    blocks: list[str] = []
    for entry in matched_skills[:5]:
        skill = entry.get("skill") if isinstance(entry, dict) else str(entry)
        if not skill:
            continue
        res = await registry.dispatch("resume_retriever", {"query": skill, "k": k})
        if not res.get("ok") or not res.get("results"):
            continue
        lines = [f"### {skill}"]
        for r in res["results"]:
            lines.append(f"- {r['text'][:240]}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "(no retrieval hits)"


async def _company_facts(company: str) -> str:
    if not settings.enable_web_search:
        return ""
    res = await registry.dispatch(
        "web_search", {"query": f"{company} company recent news products", "count": 3}
    )
    if not res.get("ok") or not res.get("results"):
        return ""
    return "\n".join(
        f"- {r['title']}: {r['snippet']}" for r in res["results"] if r.get("snippet")
    )


class WriteCoverLetterSkill(Skill):
    name = "write_cover_letter"
    model_tier = "generation"
    temperature = 0.7
    output_schema = CoverLetter
    prompt = PROMPT

    async def run(self, ctx: SkillContext) -> CoverLetter:
        parsed_jd = ctx.inputs["parsed_jd"]
        gap_analysis = ctx.inputs["gap_analysis"]
        full_name = ctx.inputs.get("full_name", "")

        retrieval_block = await _retrieve_for_matched(gap_analysis.get("matched_skills") or [])
        company_facts = await _company_facts(parsed_jd.get("company") or "")

        chain = self.prompt | self.llm().with_structured_output(self.output_schema)
        return await chain.ainvoke(  # type: ignore[return-value]
            {
                "full_name": full_name,
                "parsed_jd": json.dumps(parsed_jd, indent=2),
                "gap_analysis": json.dumps(gap_analysis, indent=2),
                "retrieval_block": retrieval_block,
                "company_facts": company_facts or "(none)",
            }
        )
