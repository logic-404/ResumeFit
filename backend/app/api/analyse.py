"""POST /analyse + GET /analyse/{job_id}/stream."""
from __future__ import annotations

import json

import tiktoken
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, model_validator
from sse_starlette.sse import EventSourceResponse

from app.pipeline.runner import spawn_run
from app.pipeline.streaming import registry as stream_registry
from app.skills.scrape_jd import scrape_jd

router = APIRouter(tags=["analyse"])

MAX_JD_TOKENS = 8000

try:
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - tiktoken usually has it bundled
    _ENC = None


def _count_tokens(text: str) -> int:
    if _ENC is None:
        return len(text) // 4
    return len(_ENC.encode(text))


class AnalyseRequest(BaseModel):
    jd_text: str | None = None
    jd_url: str | None = None
    company_name: str | None = None
    role_title: str | None = None
    job_url: str | None = None

    @model_validator(mode="after")
    def _one_of(self):
        if not self.jd_text and not self.jd_url:
            raise ValueError("Either jd_text or jd_url is required")
        return self


class AnalyseResponse(BaseModel):
    job_id: str


@router.post("/analyse", response_model=AnalyseResponse, status_code=202)
async def analyse(payload: AnalyseRequest, request: Request) -> AnalyseResponse:
    if payload.jd_text:
        jd_text = payload.jd_text
    else:
        try:
            jd_text = await scrape_jd(payload.jd_url)  # type: ignore[arg-type]
        except ValueError as e:
            raise HTTPException(
                400,
                {"code": "JD_FETCH_FAILED", "message": str(e)},
            ) from e

    if _count_tokens(jd_text) > MAX_JD_TOKENS:
        raise HTTPException(
            413,
            {
                "code": "JD_TOO_LARGE",
                "message": f"JD exceeds {MAX_JD_TOKENS} tokens",
            },
        )

    job_id = spawn_run(
        jd_text=jd_text,
        company_name=payload.company_name,
        role_title=payload.role_title,
        job_url=payload.job_url or payload.jd_url,
    )
    return AnalyseResponse(job_id=job_id)


@router.get("/analyse/{job_id}/stream")
async def analyse_stream(job_id: str, request: Request):
    s = stream_registry.get(job_id)
    if s is None:
        raise HTTPException(
            404, {"code": "JOB_NOT_FOUND", "message": "Unknown or expired job_id"}
        )

    async def event_publisher():
        try:
            async for ev in s.consume():
                if await request.is_disconnected():
                    break
                yield {"event": ev.event, "data": json.dumps(ev.data)}
        finally:
            stream_registry.discard(job_id)

    return EventSourceResponse(event_publisher())
