"""Dashboard aggregation queries.

JSONB skill counts use raw SQL with `jsonb_array_elements` so the GIN
index on generated_outputs.content is leveraged. SQLAlchemy ORM-level
expressions aren't ergonomic for this.
"""
from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application


async def status_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.execute(
            select(Application.status, func.count())
            .group_by(Application.status)
        )
    ).all()
    out = {s: 0 for s in ("draft", "applied", "interview", "offer", "rejected", "withdrawn")}
    for status_val, count in rows:
        out[status_val] = int(count)
    return out


async def total_count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count(Application.id)))).scalar_one())


async def response_metrics(session: AsyncSession) -> tuple[float, float | None]:
    """Returns (response_rate, avg_days_to_response)."""
    total = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.status.in_(["applied", "interview", "offer", "rejected"])
            )
        )
    ).scalar_one()
    responded = (
        await session.execute(
            select(func.count(Application.id)).where(
                Application.response_date.is_not(None)
            )
        )
    ).scalar_one()
    avg_days = (
        await session.execute(
            text(
                "SELECT AVG(response_date - applied_date) "
                "FROM applications "
                "WHERE response_date IS NOT NULL AND applied_date IS NOT NULL"
            )
        )
    ).scalar()

    rate = float(responded) / float(total) if total else 0.0
    return rate, float(avg_days) if avg_days is not None else None


async def time_window_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')  AS week, "
                "  COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS month "
                "FROM applications"
            )
        )
    ).first()
    return {
        "applications_this_week": int(rows.week or 0),
        "applications_this_month": int(rows.month or 0),
    }


async def top_skills(session: AsyncSession, output_type: str, key: str, limit: int = 5) -> list[str]:
    """Aggregate top `key` (e.g. 'matched_skills') across all gap_analysis outputs."""
    sql = text(
        """
        SELECT skill, COUNT(*) AS n
        FROM generated_outputs go,
             jsonb_array_elements(go.content -> :key) AS item,
             LATERAL (
                 SELECT COALESCE(item->>'skill', item #>> '{}') AS skill
             ) s
        WHERE go.output_type = :output_type
          AND skill IS NOT NULL
        GROUP BY skill
        ORDER BY n DESC
        LIMIT :limit
        """
    )
    rows = (
        await session.execute(
            sql, {"key": key, "output_type": output_type, "limit": limit}
        )
    ).all()
    return [r.skill for r in rows]
