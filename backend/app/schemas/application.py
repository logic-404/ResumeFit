from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

Status = Literal["draft", "applied", "interview", "offer", "rejected", "withdrawn"]


class ApplicationSummary(BaseModel):
    id: UUID
    company_name: str
    role_title: str
    location: str | None = None
    status: Status
    applied_date: date | None = None
    response_date: date | None = None
    job_url: str | None = None
    created_at: datetime
    updated_at: datetime
    overall_match_score: float | None = None


class GeneratedOutputDTO(BaseModel):
    output_type: Literal["cover_letter", "gap_analysis", "tailored_resume"]
    version: int
    content: dict
    model_used: str | None = None
    created_at: datetime


class ApplicationDetail(ApplicationSummary):
    raw_jd_text: str
    parsed_jd: dict
    salary_range: str | None = None
    notes: str | None = None
    outputs: list[GeneratedOutputDTO]


class ApplicationUpdate(BaseModel):
    status: Status | None = None
    applied_date: date | None = None
    response_date: date | None = None
    notes: str | None = None


class RegenerateRequest(BaseModel):
    output_type: Literal["cover_letter", "gap_analysis", "tailored_resume"]
