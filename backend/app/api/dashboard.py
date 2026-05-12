from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.stats import (
    response_metrics,
    status_counts,
    time_window_counts,
    top_skills,
    total_count,
)

router = APIRouter(tags=["dashboard"])


class DashboardStats(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    response_rate: float
    average_days_to_response: float | None = None
    top_matched_skills: list[str]
    top_missing_skills: list[str]
    applications_this_week: int
    applications_this_month: int


@router.get("/dashboard/stats", response_model=DashboardStats)
async def stats(session: AsyncSession = Depends(get_session)) -> DashboardStats:
    total = await total_count(session)
    by_status = await status_counts(session)
    rate, avg_days = await response_metrics(session)
    window = await time_window_counts(session)
    matched = await top_skills(session, "gap_analysis", "matched_skills", limit=5)
    missing = await top_skills(session, "gap_analysis", "missing_skills", limit=5)

    return DashboardStats(
        total_applications=total,
        by_status=by_status,
        response_rate=rate,
        average_days_to_response=avg_days,
        top_matched_skills=matched,
        top_missing_skills=missing,
        applications_this_week=window["applications_this_week"],
        applications_this_month=window["applications_this_month"],
    )
