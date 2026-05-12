"""Request/response schemas for the profile API."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.pipeline import (
    EducationEntry,
    ExperienceEntry,
    SkillEntry,
)


class ProfileResponse(BaseModel):
    id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    skills: list[SkillEntry]
    experience: list[ExperienceEntry]
    education: list[EducationEntry]
    certifications: list[str]
    source_format: str
    file_structure: dict | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    skills: list[SkillEntry] | None = None
    experience: list[ExperienceEntry] | None = None
    education: list[EducationEntry] | None = None
    certifications: list[str] | None = None
