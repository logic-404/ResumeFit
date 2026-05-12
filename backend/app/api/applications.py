"""Applications CRUD + regenerate + tailored-resume download."""
from __future__ import annotations

import asyncio
import re
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal, get_session
from app.models import Application, GeneratedOutput, Profile
from app.pipeline.graph import (
    cover_letter_node,
    gap_analysis_node,
    tailored_resume_node,
)
from app.pipeline.streaming import StreamEvent, registry as stream_registry
from app.schemas.application import (
    ApplicationDetail,
    ApplicationSummary,
    ApplicationUpdate,
    GeneratedOutputDTO,
    RegenerateRequest,
)
from app.services.resume_packager import package as package_resume

router = APIRouter(tags=["applications"])


def _summary(app: Application, score: float | None = None) -> ApplicationSummary:
    return ApplicationSummary(
        id=app.id,
        company_name=app.company_name,
        role_title=app.role_title,
        location=app.location,
        status=app.status,  # type: ignore[arg-type]
        applied_date=app.applied_date,
        response_date=app.response_date,
        job_url=app.job_url,
        created_at=app.created_at,
        updated_at=app.updated_at,
        overall_match_score=score,
    )


async def _latest_outputs(
    session: AsyncSession, application_id: uuid.UUID
) -> list[GeneratedOutput]:
    """Return latest version of each output_type for one application."""
    sub = (
        select(
            GeneratedOutput.output_type,
            func.max(GeneratedOutput.version).label("v"),
        )
        .where(GeneratedOutput.application_id == application_id)
        .group_by(GeneratedOutput.output_type)
        .subquery()
    )
    stmt = (
        select(GeneratedOutput)
        .join(
            sub,
            (GeneratedOutput.output_type == sub.c.output_type)
            & (GeneratedOutput.version == sub.c.v),
        )
        .where(GeneratedOutput.application_id == application_id)
    )
    return list((await session.execute(stmt)).scalars())


@router.get("/applications", response_model=list[ApplicationSummary])
async def list_applications(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[ApplicationSummary]:
    stmt = select(Application).order_by(desc(Application.created_at))
    if status:
        stmt = stmt.where(Application.status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            (Application.company_name.ilike(like))
            | (Application.role_title.ilike(like))
        )
    stmt = stmt.limit(limit).offset(offset)
    apps = list((await session.execute(stmt)).scalars())

    if not apps:
        return []

    # Pull latest gap_analysis score per app to enrich the summary
    ids = [a.id for a in apps]
    score_stmt = (
        select(
            GeneratedOutput.application_id,
            GeneratedOutput.content["overall_match_score"].astext.label("score"),
        )
        .where(
            GeneratedOutput.application_id.in_(ids),
            GeneratedOutput.output_type == "gap_analysis",
        )
        .order_by(GeneratedOutput.application_id, desc(GeneratedOutput.version))
    )
    rows = (await session.execute(score_stmt)).all()
    score_by_id: dict[uuid.UUID, float] = {}
    for r in rows:
        score_by_id.setdefault(r.application_id, float(r.score)) if r.score else None
    return [_summary(a, score_by_id.get(a.id)) for a in apps]


@router.get("/applications/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ApplicationDetail:
    app = (
        await session.execute(
            select(Application).where(Application.id == application_id)
        )
    ).scalars().first()
    if app is None:
        raise HTTPException(404, {"code": "APP_NOT_FOUND", "message": "Unknown application"})

    outputs = await _latest_outputs(session, application_id)
    score = next(
        (
            float(o.content.get("overall_match_score"))
            for o in outputs
            if o.output_type == "gap_analysis"
            and isinstance(o.content.get("overall_match_score"), (int, float))
        ),
        None,
    )

    return ApplicationDetail(
        **_summary(app, score).model_dump(),
        raw_jd_text=app.raw_jd_text,
        parsed_jd=app.parsed_jd,
        salary_range=app.salary_range,
        notes=app.notes,
        outputs=[
            GeneratedOutputDTO(
                output_type=o.output_type,  # type: ignore[arg-type]
                version=o.version,
                content=o.content,
                model_used=o.model_used,
                created_at=o.created_at,
            )
            for o in outputs
        ],
    )


@router.patch("/applications/{application_id}", response_model=ApplicationSummary)
async def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    session: AsyncSession = Depends(get_session),
) -> ApplicationSummary:
    app = (
        await session.execute(
            select(Application).where(Application.id == application_id)
        )
    ).scalars().first()
    if app is None:
        raise HTTPException(404, {"code": "APP_NOT_FOUND", "message": "Unknown application"})

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("status") == "applied" and app.applied_date is None:
        updates.setdefault("applied_date", date.today())
    for k, v in updates.items():
        setattr(app, k, v)
    await session.commit()
    await session.refresh(app)
    return _summary(app)


@router.delete("/applications/{application_id}", status_code=204)
async def delete_application(
    application_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    app = (
        await session.execute(
            select(Application).where(Application.id == application_id)
        )
    ).scalars().first()
    if app is None:
        raise HTTPException(404, {"code": "APP_NOT_FOUND", "message": "Unknown application"})
    await session.delete(app)
    await session.commit()
    return Response(status_code=204)


# ──────────────────────────────────────────────────────────
# Regenerate one output type
# ──────────────────────────────────────────────────────────
_REGEN_NODES = {
    "cover_letter": cover_letter_node,
    "gap_analysis": gap_analysis_node,
    "tailored_resume": tailored_resume_node,
}


async def _regen_run(application_id: uuid.UUID, output_type: str, job_id: str) -> None:
    s = stream_registry.get(job_id)
    try:
        async with SessionLocal() as session:
            app = (
                await session.execute(
                    select(Application).where(Application.id == application_id)
                )
            ).scalars().first()
            if app is None:
                raise LookupError("application gone")
            profile = (await session.execute(select(Profile))).scalars().first()
            if profile is None:
                raise LookupError("profile gone")
            outputs = await _latest_outputs(session, application_id)
            existing = {o.output_type: o for o in outputs}
            current_max = (
                await session.execute(
                    select(func.coalesce(func.max(GeneratedOutput.version), 0)).where(
                        GeneratedOutput.application_id == application_id,
                        GeneratedOutput.output_type == output_type,
                    )
                )
            ).scalar_one()

        gap = existing.get("gap_analysis")
        state = {
            "job_id": job_id,
            "profile_id": str(profile.id),
            "profile": {
                "raw_resume_text": profile.raw_resume_text,
                "source_format": profile.source_format,
                "file_structure": profile.file_structure,
                "full_name": profile.full_name,
            },
            "jd_text": app.raw_jd_text,
            "parsed_jd": app.parsed_jd,
            "gap_analysis": gap.content if gap else None,
            "metrics": {},
        }

        node = _REGEN_NODES[output_type]
        out = await node(state)  # type: ignore[arg-type]
        new_content = out[output_type]

        async with SessionLocal() as session:
            session.add(
                GeneratedOutput(
                    application_id=application_id,
                    output_type=output_type,
                    content=new_content,
                    version=int(current_max) + 1,
                )
            )
            await session.commit()

        if s is not None:
            await s.push(
                StreamEvent(
                    event="result",
                    data={
                        "application_id": str(application_id),
                        "output_type": output_type,
                        "content": new_content,
                        "version": int(current_max) + 1,
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


@router.post("/applications/{application_id}/regenerate", status_code=202)
async def regenerate(
    application_id: uuid.UUID,
    payload: RegenerateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    app = (
        await session.execute(
            select(Application).where(Application.id == application_id)
        )
    ).scalars().first()
    if app is None:
        raise HTTPException(404, {"code": "APP_NOT_FOUND", "message": "Unknown application"})

    if payload.output_type == "gap_analysis":
        # gap_analysis depends only on parsed_jd + profile, OK to regen
        pass
    elif payload.output_type in {"cover_letter", "tailored_resume"}:
        # Need a gap_analysis to exist
        latest = await _latest_outputs(session, application_id)
        types = {o.output_type for o in latest}
        if "gap_analysis" not in types:
            raise HTTPException(
                400,
                {
                    "code": "MISSING_DEP",
                    "message": "Run gap_analysis before regenerating this output",
                },
            )

    job_id = str(uuid.uuid4())
    stream_registry.create(job_id)
    asyncio.create_task(_regen_run(application_id, payload.output_type, job_id))
    return {"job_id": job_id}


# ──────────────────────────────────────────────────────────
# Download tailored resume
# ──────────────────────────────────────────────────────────
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9]+")


def _slug(s: str) -> str:
    return _FILENAME_SAFE.sub("_", s).strip("_") or "x"


@router.get("/applications/{application_id}/tailored-resume/download")
async def download_tailored_resume(
    application_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> Response:
    stmt = (
        select(GeneratedOutput)
        .where(
            GeneratedOutput.application_id == application_id,
            GeneratedOutput.output_type == "tailored_resume",
        )
        .order_by(desc(GeneratedOutput.version))
        .limit(1)
    )
    output = (await session.execute(stmt)).scalars().first()
    if output is None:
        raise HTTPException(
            404, {"code": "NO_TAILORED_RESUME", "message": "Generate one first"}
        )

    app_obj = (
        await session.execute(select(Application).where(Application.id == application_id))
    ).scalars().first()

    data, default_name, media_type = package_resume(output.content)

    ext = default_name.rsplit(".", 1)[-1] if "." in default_name else "bin"
    if app_obj is not None:
        filename = f"{_slug(app_obj.company_name)}-{_slug(app_obj.role_title)}.{ext}"
    else:
        filename = default_name

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
