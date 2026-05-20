"""Tailor-resume skill.

Pipeline:
1. Pre-tool: retrieve resume evidence for each JD required skill.
2. Generate: LLM produces a TailoredResume (discriminated union by format).
3. Verify-1: entity_diff against original source. If fabrications found,
   regenerate ONCE with explicit anti-fabrication note.
4. Verify-2 (LaTeX only): latex_compile_check. If fail, regenerate ONCE
   with the compiler errors fed back.

Each verifier runs at most once. After both retries, the last attempt is
returned even if imperfect — the change_log will surface what happened.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter

from app.schemas.pipeline import (
    PdfSourceResume,
    TailoredResume,
    TexProjectResume,
    TexResume,
)
from app.skills.base import Skill, SkillContext
from app.skills.tailor_resume.prompt import PROMPT
from app.tools.registry import registry

_TAILORED_ADAPTER = TypeAdapter(TailoredResume)
_SOURCE_TO_FORMAT = {
    "pdf": "pdf_source",
    "tex": "tex",
    "tex_project": "tex_project",
}


async def _retrieve_for_jd(parsed_jd: dict, k: int = 3) -> str:
    skills = list(
        dict.fromkeys(
            (parsed_jd.get("required_skills") or [])
            + (parsed_jd.get("preferred_skills") or [])
        )
    )
    if not skills:
        return "(no skills to retrieve)"
    blocks: list[str] = []
    for skill in skills[:10]:
        res = await registry.dispatch("resume_retriever", {"query": skill, "k": k})
        if not res.get("ok") or not res.get("results"):
            continue
        lines = [f"### {skill}"]
        for r in res["results"]:
            src = r.get("source_file") or "-"
            lines.append(f"- ({src}) {r['text'][:240]}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or "(no retrieval hits)"


def _output_text(resume: PdfSourceResume | TexResume | TexProjectResume) -> str:
    """Concatenate the writable content for entity_diff."""
    if isinstance(resume, PdfSourceResume):
        return resume.plain_text + "\n" + resume.markdown
    if isinstance(resume, TexResume):
        return resume.full_tex
    return "\n\n".join(f.content for f in resume.files)


def _expected_format(source_format: str) -> str:
    return _SOURCE_TO_FORMAT.get(source_format, source_format)


def _is_empty(resume: PdfSourceResume | TexResume | TexProjectResume) -> bool:
    if isinstance(resume, PdfSourceResume):
        return not (
            resume.markdown.strip()
            or resume.plain_text.strip()
            or any(s.bullets for s in resume.sections)
        )
    if isinstance(resume, TexResume):
        return not resume.full_tex.strip()
    return not resume.files or not any(f.content.strip() for f in resume.files)


def _format_mismatch_note(expected: str, got: str) -> str:
    return (
        f"\nCRITICAL: Previous attempt emitted format='{got}' but the source "
        f"resume is '{expected}'. You MUST emit format='{expected}' and the "
        f"matching shape. Re-read the FORMAT-SPECIFIC RULES and retry.\n"
    )


def _empty_note(fmt: str) -> str:
    return (
        f"\nCRITICAL: Previous attempt produced an EMPTY resume (no content "
        f"in the required fields for format='{fmt}'). Populate the actual "
        f"resume content drawn from the source. Do not return an empty shell.\n"
    )


class TailorResumeSkill(Skill):
    name = "tailor_resume"
    model_tier = "generation"
    temperature = 0.3
    output_schema = TailoredResume  # type: ignore[assignment]
    prompt = PROMPT

    async def _generate(
        self, inputs: dict[str, Any], repair_note: str
    ) -> PdfSourceResume | TexResume | TexProjectResume:
        # Cannot use with_structured_output on a discriminated union directly
        # via Pydantic in all langchain versions — use JSON-mode + adapter.
        chain = self.prompt | self.llm().bind(response_format={"type": "json_object"})
        msg = await chain.ainvoke({**inputs, "repair_note": repair_note})
        raw = msg.content if hasattr(msg, "content") else str(msg)
        data, _ = json.JSONDecoder().raw_decode(raw.strip())
        # Backstop: LLM sometimes omits the `format` discriminator. Infer
        # from source_format so validation succeeds.
        if isinstance(data, dict) and "format" not in data:
            data["format"] = _SOURCE_TO_FORMAT.get(
                inputs["source_format"], inputs["source_format"]
            )
        return _TAILORED_ADAPTER.validate_python(data)

    async def run(self, ctx: SkillContext):
        parsed_jd = ctx.inputs["parsed_jd"]
        retrieval_block = await _retrieve_for_jd(parsed_jd)

        base_inputs = {
            "source_format": ctx.inputs["source_format"],
            "file_structure": (
                json.dumps(ctx.inputs.get("file_structure"), indent=2)
                if ctx.inputs.get("file_structure")
                else "(N/A — single file)"
            ),
            "resume_text": ctx.inputs["resume_text"],
            "parsed_jd": json.dumps(parsed_jd, indent=2),
            "gap_analysis": json.dumps(ctx.inputs["gap_analysis"], indent=2),
            "retrieval_block": retrieval_block,
        }

        expected_fmt = _expected_format(ctx.inputs["source_format"])

        resume = await self._generate(base_inputs, repair_note="")

        # Verify-0a: format must match the source format. Regen once.
        if resume.format != expected_fmt:
            resume = await self._generate(
                base_inputs,
                repair_note=_format_mismatch_note(expected_fmt, resume.format),
            )
            if resume.format != expected_fmt:
                raise ValueError(
                    f"Tailored resume format '{resume.format}' does not match "
                    f"source format '{expected_fmt}' after one repair attempt."
                )

        # Verify-0b: content must be non-empty. Regen once.
        if _is_empty(resume):
            resume = await self._generate(
                base_inputs, repair_note=_empty_note(expected_fmt)
            )
            if _is_empty(resume):
                raise ValueError(
                    "Tailored resume is empty after one repair attempt — "
                    "model failed to populate content."
                )

        # Verify-1: fabrication check
        diff = await registry.dispatch(
            "entity_diff",
            {"source": ctx.inputs["resume_text"], "output": _output_text(resume)},
        )
        if not diff["ok"]:
            note = (
                "\nPREVIOUS ATTEMPT FABRICATED CONTENT. The following tokens appeared "
                "in the output but NOT the source. Remove or replace them with content "
                "actually present in the source resume:\n"
                f"  entities: {diff['fabricated_entities']}\n"
                f"  dates:    {diff['fabricated_dates']}\n"
                f"  numbers:  {diff['fabricated_numerics']}\n"
            )
            resume = await self._generate(base_inputs, repair_note=note)

        # Verify-2: LaTeX compile (only for tex / tex_project)
        if isinstance(resume, TexResume):
            comp = await registry.dispatch(
                "latex_compile_check",
                {
                    "files": [{"path": "main.tex", "content": resume.full_tex}],
                    "root_file": "main.tex",
                },
            )
            if not comp["ok"] and not comp.get("skipped"):
                note = (
                    f"\nPREVIOUS LATEX FAILED TO COMPILE. Errors:\n{comp['log']}\n"
                    f"Missing files: {comp.get('missing_refs', [])}\n"
                    "Fix and re-emit a compilable single-file LaTeX resume."
                )
                resume = await self._generate(base_inputs, repair_note=note)
        elif isinstance(resume, TexProjectResume):
            comp = await registry.dispatch(
                "latex_compile_check",
                {
                    "files": [f.model_dump() for f in resume.files],
                    "root_file": resume.root_file,
                },
            )
            if not comp["ok"] and not comp.get("skipped"):
                note = (
                    f"\nPREVIOUS LATEX PROJECT FAILED TO COMPILE. Errors:\n{comp['log']}\n"
                    f"Missing files: {comp.get('missing_refs', [])}\n"
                    "Fix and re-emit. Make sure every \\input/\\include target "
                    "exists in `files` and the root file path matches."
                )
                resume = await self._generate(base_inputs, repair_note=note)

        return resume
