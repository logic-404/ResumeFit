"""LangGraph state machine for the analyse pipeline.

Nodes: parse_jd → gap_analysis → {cover_letter, tailored_resume} → persist.
Cover letter and tailored resume fan out in parallel since they share the
same dependencies (parsed_jd + gap_analysis + profile).
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.database import SessionLocal
from app.models import Application, GeneratedOutput, Profile
from app.pipeline.streaming import StreamEvent, registry as stream_registry
from app.skills.base import SkillContext
from app.skills.gap_analyse import GapAnalyseSkill
from app.skills.parse_jd import ParseJDSkill
from app.skills.tailor_resume import TailorResumeSkill
from app.skills.write_cover_letter import WriteCoverLetterSkill

# Retry only on transient API errors. Schema/validation errors should
# surface immediately rather than burn budget retrying.
try:
    from openai import APIConnectionError, APITimeoutError, RateLimitError
    _RETRY_EXC = (RateLimitError, APITimeoutError, APIConnectionError)
except ImportError:  # pragma: no cover
    _RETRY_EXC = ()


def _merge_metrics(left: dict, right: dict) -> dict:
    """Reducer for parallel fan-out nodes both writing `metrics`.

    Deep-merges the `steps` sub-dict so cover_letter and tailored_resume
    metric writes don't clobber each other.
    """
    out: dict[str, Any] = {**(left or {}), **(right or {})}
    left_steps = (left or {}).get("steps") or {}
    right_steps = (right or {}).get("steps") or {}
    if left_steps or right_steps:
        out["steps"] = {**left_steps, **right_steps}
    return out


def _extend_errors(left: list, right: list) -> list:
    return [*(left or []), *(right or [])]


class PipelineState(TypedDict, total=False):
    job_id: str
    profile_id: str
    profile: dict
    jd_text: str
    company_name: str | None
    role_title: str | None
    job_url: str | None
    parsed_jd: dict
    gap_analysis: dict
    cover_letter: dict
    tailored_resume: dict
    application_id: str | None
    metrics: Annotated[dict[str, Any], _merge_metrics]
    errors: Annotated[list[str], _extend_errors]


async def _push(job_id: str, event: str, data: dict) -> None:
    s = stream_registry.get(job_id)
    if s is not None:
        await s.push(StreamEvent(event=event, data=data))


async def _retrying(coro_factory):
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(_RETRY_EXC) if _RETRY_EXC else retry_if_exception_type(()),
        reraise=True,
    ):
        with attempt:
            return await coro_factory()


def _record_metric(state: PipelineState, name: str, ms: int) -> None:
    state.setdefault("metrics", {}).setdefault("steps", {})[name] = {"ms": ms}


# ──────────────────────────────────────────────────────────
# Nodes
# ──────────────────────────────────────────────────────────
async def parse_jd_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _push(job_id, "step", {"name": "parse_jd", "status": "started"})
    t0 = time.monotonic()
    skill = ParseJDSkill()
    parsed = await _retrying(
        lambda: skill.run(SkillContext(inputs={"jd_text": state["jd_text"]}))
    )
    ms = int((time.monotonic() - t0) * 1000)
    out = {"parsed_jd": parsed.model_dump()}
    new_state = {**state, **out}
    _record_metric(new_state, "parse_jd", ms)
    await _push(job_id, "step", {"name": "parse_jd", "status": "done", "ms": ms})
    return out | {"metrics": new_state["metrics"]}


async def gap_analysis_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _push(job_id, "step", {"name": "gap_analysis", "status": "started"})
    t0 = time.monotonic()
    skill = GapAnalyseSkill()
    gap = await _retrying(
        lambda: skill.run(
            SkillContext(
                inputs={
                    "parsed_jd": state["parsed_jd"],
                    "resume_text": state["profile"]["raw_resume_text"],
                }
            )
        )
    )
    ms = int((time.monotonic() - t0) * 1000)
    out = {"gap_analysis": gap.model_dump()}
    new_state = {**state, **out}
    _record_metric(new_state, "gap_analysis", ms)
    await _push(job_id, "step", {"name": "gap_analysis", "status": "done", "ms": ms})
    return out | {"metrics": new_state["metrics"]}


async def cover_letter_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _push(job_id, "step", {"name": "cover_letter", "status": "started"})
    t0 = time.monotonic()
    skill = WriteCoverLetterSkill()
    letter = await _retrying(
        lambda: skill.run(
            SkillContext(
                inputs={
                    "parsed_jd": state["parsed_jd"],
                    "gap_analysis": state["gap_analysis"],
                    "full_name": state["profile"].get("full_name", ""),
                }
            )
        )
    )
    ms = int((time.monotonic() - t0) * 1000)
    out = {"cover_letter": letter.model_dump()}
    new_state = {**state, **out}
    _record_metric(new_state, "cover_letter", ms)
    await _push(job_id, "step", {"name": "cover_letter", "status": "done", "ms": ms})
    return out | {"metrics": new_state["metrics"]}


async def tailored_resume_node(state: PipelineState) -> dict:
    job_id = state["job_id"]
    await _push(job_id, "step", {"name": "tailored_resume", "status": "started"})
    t0 = time.monotonic()
    skill = TailorResumeSkill()
    resume = await _retrying(
        lambda: skill.run(
            SkillContext(
                inputs={
                    "parsed_jd": state["parsed_jd"],
                    "gap_analysis": state["gap_analysis"],
                    "resume_text": state["profile"]["raw_resume_text"],
                    "source_format": state["profile"]["source_format"],
                    "file_structure": state["profile"].get("file_structure"),
                }
            )
        )
    )
    ms = int((time.monotonic() - t0) * 1000)
    out = {"tailored_resume": resume.model_dump()}
    new_state = {**state, **out}
    _record_metric(new_state, "tailored_resume", ms)
    await _push(job_id, "step", {"name": "tailored_resume", "status": "done", "ms": ms})
    return out | {"metrics": new_state["metrics"]}


async def persist_node(state: PipelineState) -> dict:
    """Single-transaction insert of application + 3 generated_outputs."""
    job_id = state["job_id"]
    await _push(job_id, "step", {"name": "persist", "status": "started"})
    t0 = time.monotonic()

    parsed_jd = state["parsed_jd"]
    company = state.get("company_name") or parsed_jd.get("company") or "Unknown"
    role = state.get("role_title") or parsed_jd.get("role") or "Unknown"

    async with SessionLocal() as session:
        # Verify profile still exists (defensive — single-user, but...)
        p = (
            await session.execute(
                select(Profile).where(Profile.id == uuid.UUID(state["profile_id"]))
            )
        ).scalars().first()
        if p is None:
            raise RuntimeError("profile vanished mid-pipeline")

        app_obj = Application(
            profile_id=p.id,
            company_name=company,
            role_title=role,
            location=parsed_jd.get("location"),
            salary_range=parsed_jd.get("salary_range"),
            job_url=state.get("job_url"),
            raw_jd_text=state["jd_text"],
            parsed_jd=parsed_jd,
            status="draft",
        )
        session.add(app_obj)
        await session.flush()

        outputs = [
            GeneratedOutput(
                application_id=app_obj.id,
                output_type="cover_letter",
                content=state["cover_letter"],
                version=1,
            ),
            GeneratedOutput(
                application_id=app_obj.id,
                output_type="gap_analysis",
                content=state["gap_analysis"],
                version=1,
            ),
            GeneratedOutput(
                application_id=app_obj.id,
                output_type="tailored_resume",
                content=state["tailored_resume"],
                version=1,
            ),
        ]
        session.add_all(outputs)
        await session.commit()
        application_id = str(app_obj.id)

    ms = int((time.monotonic() - t0) * 1000)
    out = {"application_id": application_id}
    new_state = {**state, **out}
    _record_metric(new_state, "persist", ms)
    await _push(
        job_id,
        "step",
        {"name": "persist", "status": "done", "ms": ms, "application_id": application_id},
    )
    return out | {"metrics": new_state["metrics"]}


# ──────────────────────────────────────────────────────────
# Graph build
# ──────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("parse_jd", parse_jd_node)
    graph.add_node("gap_analysis", gap_analysis_node)
    graph.add_node("cover_letter", cover_letter_node)
    graph.add_node("tailored_resume", tailored_resume_node)
    graph.add_node("persist", persist_node)

    graph.add_edge(START, "parse_jd")
    graph.add_edge("parse_jd", "gap_analysis")
    # Fan-out
    graph.add_edge("gap_analysis", "cover_letter")
    graph.add_edge("gap_analysis", "tailored_resume")
    # Fan-in
    graph.add_edge("cover_letter", "persist")
    graph.add_edge("tailored_resume", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


_compiled = None


def get_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled
