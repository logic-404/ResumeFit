"""Profile API: upload, fetch, update.

Singleton model: at most one profile row exists (DB-enforced). Upload
replaces it; chunks are wiped and rebuilt from the new resume.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Profile
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.services.embeddings import embed_batch
from app.services.latex_resolver import LatexResolveError, resolve_latex_project
from app.services.pdf_parser import extract_text_from_pdf
from app.services.resume_chunker import chunk_resume
from app.services.upload_guard import validate as validate_uploads
from app.services.vector_store import add_chunks as vs_add
from app.services.vector_store import delete_for_profile as vs_delete
from app.skills.base import SkillContext
from app.skills.parse_profile import ParseProfileSkill

router = APIRouter(tags=["profile"])


def _profile_to_response(p: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=p.id,
        full_name=p.full_name,
        email=p.email,
        phone=p.phone,
        linkedin_url=p.linkedin_url,
        skills=p.skills or [],
        experience=p.experience or [],
        education=p.education or [],
        certifications=p.certifications or [],
        source_format=p.source_format,
        file_structure=p.file_structure,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


async def _embed_into_vector_store(profile_id: str, raw_text: str) -> None:
    chunks = chunk_resume(raw_text)
    if not chunks:
        return
    embeddings = await embed_batch([c.text for c in chunks])
    items = [
        (c.text, emb, c.source_file, c.kind)
        for c, emb in zip(chunks, embeddings, strict=True)
    ]
    await vs_add(profile_id, items)


@router.post("/profile/upload", status_code=201, response_model=ProfileResponse)
async def upload_resume(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    validated = await validate_uploads(files)

    if len(validated) == 1:
        f, data = validated[0]
        name = (f.filename or "").lower()
        if name.endswith(".pdf"):
            raw_text = extract_text_from_pdf(data)
            source_format = "pdf"
            file_structure = None
        elif name.endswith(".tex"):
            raw_text = data.decode("utf-8", errors="ignore")
            source_format = "tex"
            file_structure = None
        else:
            raise HTTPException(
                400,
                {"code": "BAD_FORMAT", "message": "Single upload must be .pdf or .tex"},
            )
    else:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for f, data in validated:
                rel = (f.filename or "").replace("\\", "/")
                if rel.startswith("/") or ".." in rel.split("/"):
                    raise HTTPException(
                        400,
                        {"code": "BAD_PATH", "message": f"Suspicious path: {rel}"},
                    )
                dest = tmp_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            try:
                raw_text, file_structure = resolve_latex_project(tmp_dir)
            except LatexResolveError as e:
                raise HTTPException(
                    400, {"code": "LATEX_RESOLVE_FAILED", "message": str(e)}
                ) from e
        source_format = "tex_project"

    if not raw_text.strip():
        raise HTTPException(400, {"code": "EMPTY_RESUME", "message": "No text extracted"})

    skill = ParseProfileSkill()
    parsed = await skill.run(
        SkillContext(
            inputs={"resume_text": raw_text, "source_format": source_format},
        )
    )

    resume_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

    # Singleton: drop any existing profile (cascades to applications) +
    # wipe its vector chunks.
    existing = (await session.execute(select(Profile))).scalars().first()
    if existing is not None:
        await vs_delete(str(existing.id))
        await session.delete(existing)
        await session.flush()

    profile = Profile(
        full_name=parsed.full_name,
        email=parsed.email,
        phone=parsed.phone,
        linkedin_url=parsed.linkedin_url,
        skills=[s.model_dump() for s in parsed.skills],
        experience=[e.model_dump() for e in parsed.experience],
        education=[e.model_dump() for e in parsed.education],
        certifications=parsed.certifications,
        raw_resume_text=raw_text,
        resume_hash=resume_hash,
        source_format=source_format,
        file_structure=file_structure,
    )
    session.add(profile)
    await session.flush()
    profile_id = str(profile.id)
    await session.commit()
    await session.refresh(profile)

    await _embed_into_vector_store(profile_id, raw_text)
    return _profile_to_response(profile)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    profile = (await session.execute(select(Profile))).scalars().first()
    if profile is None:
        raise HTTPException(
            404,
            {"code": "PROFILE_NOT_FOUND", "message": "Upload a resume first"},
        )
    return _profile_to_response(profile)


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    payload: ProfileUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    profile = (await session.execute(select(Profile))).scalars().first()
    if profile is None:
        raise HTTPException(
            404,
            {"code": "PROFILE_NOT_FOUND", "message": "Upload a resume first"},
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in {"skills", "experience", "education"} and value is not None:
            setattr(profile, field, [v.model_dump() if hasattr(v, "model_dump") else v for v in value])
        else:
            setattr(profile, field, value)

    await session.commit()
    await session.refresh(profile)
    return _profile_to_response(profile)
