"""POST /jd/preview — scrape URL + extract company/role for form prefill."""
from __future__ import annotations

import tiktoken
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.pipeline import ParsedJD
from app.skills.base import SkillContext
from app.skills.parse_jd.skill import ParseJDSkill
from app.skills.scrape_jd import scrape_jd

router = APIRouter(tags=["jd_preview"])

MAX_JD_TOKENS = 8000

try:
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover
    _ENC = None


def _count_tokens(text: str) -> int:
    if _ENC is None:
        return len(text) // 4
    return len(_ENC.encode(text))


class JDPreviewRequest(BaseModel):
    url: str


class JDPreviewResponse(BaseModel):
    company: str | None = None
    role: str | None = None
    location: str | None = None
    jd_text: str


@router.post("/jd/preview", response_model=JDPreviewResponse)
async def jd_preview(payload: JDPreviewRequest) -> JDPreviewResponse:
    try:
        jd_text = await scrape_jd(payload.url)
    except ValueError as e:
        raise HTTPException(
            400, {"code": "JD_FETCH_FAILED", "message": str(e)}
        ) from e

    if _count_tokens(jd_text) > MAX_JD_TOKENS:
        raise HTTPException(
            413,
            {"code": "JD_TOO_LARGE", "message": f"JD exceeds {MAX_JD_TOKENS} tokens"},
        )

    try:
        parsed: ParsedJD = await ParseJDSkill().run(
            SkillContext(inputs={"jd_text": jd_text})
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            502, {"code": "JD_PARSE_FAILED", "message": str(e)}
        ) from e

    return JDPreviewResponse(
        company=parsed.company or None,
        role=parsed.role or None,
        location=parsed.location,
        jd_text=jd_text,
    )
