"""Pipeline runner — owns the background task lifecycle.

Endpoints call `spawn_run` to fire-and-forget a pipeline; clients consume
events from the SSE registry by job_id. Errors are caught and surfaced as
'error' events so the client always reaches a terminal state.
"""
from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Profile
from app.pipeline.graph import get_graph
from app.pipeline.streaming import StreamEvent, registry as stream_registry


async def _load_profile_dict() -> dict:
    async with SessionLocal() as session:
        p = (await session.execute(select(Profile))).scalars().first()
        if p is None:
            raise LookupError("No profile uploaded")
        return {
            "id": str(p.id),
            "full_name": p.full_name,
            "raw_resume_text": p.raw_resume_text,
            "source_format": p.source_format,
            "file_structure": p.file_structure,
        }


async def _run_pipeline(
    job_id: str,
    jd_text: str,
    company_name: str | None,
    role_title: str | None,
    job_url: str | None,
) -> None:
    s = stream_registry.get(job_id)
    try:
        profile = await _load_profile_dict()
        initial = {
            "job_id": job_id,
            "profile_id": profile["id"],
            "profile": profile,
            "jd_text": jd_text,
            "company_name": company_name,
            "role_title": role_title,
            "job_url": job_url,
            "metrics": {},
            "errors": [],
        }
        graph = get_graph()
        final_state = await graph.ainvoke(initial)
        if s is not None:
            await s.push(
                StreamEvent(
                    event="result",
                    data={
                        "application_id": final_state.get("application_id"),
                        "cover_letter": final_state.get("cover_letter"),
                        "gap_analysis": final_state.get("gap_analysis"),
                        "tailored_resume": final_state.get("tailored_resume"),
                        "metrics": final_state.get("metrics", {}),
                    },
                )
            )
    except Exception as e:  # noqa: BLE001
        if s is not None:
            await s.push(
                StreamEvent(
                    event="error",
                    data={"code": type(e).__name__, "message": str(e)},
                )
            )
    finally:
        if s is not None:
            await s.end()


def spawn_run(
    jd_text: str,
    company_name: str | None,
    role_title: str | None,
    job_url: str | None,
) -> str:
    job_id = str(uuid.uuid4())
    stream_registry.create(job_id)
    asyncio.create_task(
        _run_pipeline(job_id, jd_text, company_name, role_title, job_url)
    )
    return job_id
