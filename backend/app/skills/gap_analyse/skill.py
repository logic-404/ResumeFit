"""Gap-analysis skill.

Pre-tool phase (deterministic): for each required + preferred skill in the
parsed JD, hit `resume_retriever` for top-3 matching chunks and
`skill_taxonomy_lookup` for canonical name + family. Inject as evidence
context into a single structured-output LLM call. The `overall_match_score`
is post-clamped to [0, 1] in case the model's arithmetic drifts.
"""
from __future__ import annotations

import json

from app.schemas.pipeline import GapAnalysis
from app.skills.base import Skill, SkillContext
from app.skills.gap_analyse.prompt import PROMPT
from app.tools.registry import registry


def _clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


async def _retrieve_evidence(skills: list[str], k: int = 3) -> str:
    blocks: list[str] = []
    for skill in skills:
        res = await registry.dispatch("resume_retriever", {"query": skill, "k": k})
        if not res.get("ok") or not res.get("results"):
            blocks.append(f"### {skill}\n  (no matches)")
            continue
        lines = [f"### {skill}"]
        for r in res["results"]:
            score = r.get("score", 0.0)
            src = r.get("source_file") or "-"
            text = r["text"][:240]
            lines.append(f"  ({score:.2f} | {src}) {text}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) if blocks else "(no skills to retrieve)"


async def _taxonomy_lookups(skills: list[str]) -> str:
    rows: list[str] = []
    for skill in skills:
        res = await registry.dispatch("skill_taxonomy_lookup", {"skill": skill})
        if res.get("found"):
            rows.append(
                f"- {skill} → {res['canonical']} (family: {res['family']}; "
                f"related: {', '.join(res.get('related', []))})"
            )
    return "\n".join(rows) if rows else "(no taxonomy hits)"


class GapAnalyseSkill(Skill):
    name = "gap_analyse"
    model_tier = "extraction"
    temperature = 0.0
    output_schema = GapAnalysis
    prompt = PROMPT

    async def run(self, ctx: SkillContext) -> GapAnalysis:
        parsed_jd: dict = ctx.inputs["parsed_jd"]
        all_skills = list(
            dict.fromkeys(
                (parsed_jd.get("required_skills") or [])
                + (parsed_jd.get("preferred_skills") or [])
            )
        )
        retrieval_block = await _retrieve_evidence(all_skills)
        taxonomy_block = await _taxonomy_lookups(all_skills)

        chain = self.prompt | self.llm().with_structured_output(self.output_schema)
        result: GapAnalysis = await chain.ainvoke(
            {
                "resume_text": ctx.inputs["resume_text"],
                "parsed_jd": json.dumps(parsed_jd, indent=2),
                "retrieval_block": retrieval_block,
                "taxonomy_block": taxonomy_block,
            }
        )
        result.overall_match_score = _clamp01(result.overall_match_score)
        return result
