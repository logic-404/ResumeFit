"""Eval runner.

Usage:
    python -m eval.run_eval

Reads `eval/expectations.yaml`, loads each (resume, JD) pair from disk,
runs the full pipeline against the live LLM, and prints a pass/fail
report. Exit code 1 on any failure (CI-friendly).

Note: this assumes a profile is already uploaded. The pipeline reads the
singleton profile from the DB. Pre-stage by hitting POST /profile/upload
with the resume_file from the first pair, or extend this script to do so.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import yaml

from app.pipeline.graph import get_graph
from app.tools.registry import registry as tools
from eval.evaluators import (
    assert_keyword_min,
    assert_match_score_in_range,
    assert_no_fabrication,
    assert_skills_present,
)

ROOT = Path(__file__).resolve().parent


async def _run_pair(name: str, spec: dict) -> tuple[bool, list[str]]:
    msgs: list[str] = []
    jd_path = ROOT / spec["jd_file"]
    if not jd_path.exists():
        return False, [f"missing JD fixture: {jd_path}"]
    jd_text = jd_path.read_text(encoding="utf-8")

    from sqlalchemy import select  # local import to avoid app boot issues

    from app.database import SessionLocal
    from app.models import Profile

    async with SessionLocal() as session:
        profile = (await session.execute(select(Profile))).scalars().first()
    if profile is None:
        return False, ["no profile uploaded — run POST /profile/upload first"]

    initial = {
        "job_id": f"eval-{name}",
        "profile_id": str(profile.id),
        "profile": {
            "id": str(profile.id),
            "full_name": profile.full_name,
            "raw_resume_text": profile.raw_resume_text,
            "source_format": profile.source_format,
            "file_structure": profile.file_structure,
        },
        "jd_text": jd_text,
        "company_name": None,
        "role_title": None,
        "job_url": None,
        "metrics": {},
        "errors": [],
    }
    state = await get_graph().ainvoke(initial)

    gap = state["gap_analysis"]
    letter = state["cover_letter"]
    resume = state["tailored_resume"]

    # 1. score range
    ok, m = assert_match_score_in_range(
        gap["overall_match_score"], spec["match_score_min"], spec["match_score_max"]
    )
    msgs.append(f"score: {m}")
    all_ok = ok

    # 2. required matched skills
    if spec.get("must_match_skills"):
        ok, m = assert_skills_present(gap["matched_skills"], spec["must_match_skills"])
        msgs.append(f"matched: {m}")
        all_ok = all_ok and ok

    # 3. fabrication check on tailored resume
    if spec.get("forbid_fabricated_entities", True):
        from app.skills.tailor_resume.skill import _output_text  # private but useful here

        from pydantic import TypeAdapter

        from app.schemas.pipeline import TailoredResume as TR

        out_text = _output_text(TypeAdapter(TR).validate_python(resume))  # type: ignore[arg-type]
        diff = await tools.dispatch(
            "entity_diff",
            {"source": profile.raw_resume_text, "output": out_text},
        )
        ok, m = assert_no_fabrication(diff)
        msgs.append(f"fabrication: {m}")
        all_ok = all_ok and ok

    # 4. cover letter keyword threshold
    if "cover_letter_keyword_min" in spec:
        ok, m = assert_keyword_min(letter, int(spec["cover_letter_keyword_min"]))
        msgs.append(f"keywords: {m}")
        all_ok = all_ok and ok

    return all_ok, msgs


async def main() -> int:
    spec_path = ROOT / "expectations.yaml"
    if not spec_path.exists():
        print("missing expectations.yaml", file=sys.stderr)
        return 2
    specs = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    failures = 0
    for name, spec in specs.items():
        print(f"\n=== {name} ===")
        try:
            ok, msgs = await _run_pair(name, spec)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR: {e}")
            failures += 1
            continue
        for m in msgs:
            print(f"  {m}")
        print(f"  {'PASS' if ok else 'FAIL'}")
        if not ok:
            failures += 1

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
