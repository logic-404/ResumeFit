"""Pydantic contracts between pipeline steps."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field


def _coerce_bullets(v: Any) -> Any:
    """Flatten non-string bullet items the LLM occasionally emits.

    Some completions stuff full dicts (e.g. `{company, role, bullets}`)
    into a `bullets` list when they should have been their own section
    item. Coerce each entry to a readable string so the resume still
    renders rather than crashing the whole pipeline.
    """
    if not isinstance(v, list):
        return v
    out: list[str] = []
    for item in v:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            # Best-effort flatten: surface the most useful fields.
            head_parts = [
                str(item.get(k))
                for k in ("title", "name", "role", "company", "label")
                if item.get(k)
            ]
            head = " — ".join(head_parts) if head_parts else ""
            inner = item.get("bullets") or item.get("notes") or item.get("body")
            if isinstance(inner, list):
                inner_str = "; ".join(str(x) for x in inner if x)
            else:
                inner_str = str(inner) if inner else ""
            text = ": ".join(p for p in (head, inner_str) if p)
            if text:
                out.append(text)
        elif item is not None:
            out.append(str(item))
    return out


_Bullets = Annotated[list[str], BeforeValidator(_coerce_bullets)]


# ───────────────────────────────────────────────────────
# Step 1 — Parsed JD
# ───────────────────────────────────────────────────────
class ParsedJD(BaseModel):
    role: str = Field(description="Job title exactly as written")
    company: str = Field(description="Company name")
    department: str | None = Field(default=None)
    experience_level: Literal["junior", "mid", "senior", "lead", "principal"] = Field(
        description="Inferred from years required and language"
    )
    experience_years_min: int | None = Field(default=None)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    location: str | None = None
    salary_range: str | None = None


# ───────────────────────────────────────────────────────
# Step 2 — Gap analysis
# ───────────────────────────────────────────────────────
class SkillMatch(BaseModel):
    skill: str
    evidence: str = Field(description="Where in the resume this skill appears")


class SkillGap(BaseModel):
    skill: str
    severity: Literal["required", "preferred"]
    suggestion: str


class TransferableSkill(BaseModel):
    skill: str
    maps_to: str
    explanation: str


class GapAnalysis(BaseModel):
    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_skills: list[SkillGap] = Field(default_factory=list)
    transferable_skills: list[TransferableSkill] = Field(default_factory=list)
    overall_match_score: float = Field(ge=0.0, le=1.0)
    recommendation: str


# ───────────────────────────────────────────────────────
# Step 3 — Cover letter
# ───────────────────────────────────────────────────────
class CoverLetter(BaseModel):
    greeting: str = "Dear Hiring Manager,"
    opening_paragraph: str
    body_paragraphs: list[str] = Field(min_length=1, max_length=3)
    closing_paragraph: str
    sign_off: str
    tone_score: float = Field(ge=0.0, le=1.0)
    keyword_match_count: int = Field(ge=0)


# ───────────────────────────────────────────────────────
# Step 4 — Tailored resume (discriminated union by `format`)
# ───────────────────────────────────────────────────────
class ChangeLogEntry(BaseModel):
    # `section` is canonical, but the LLM often emits `file` for tex_project
    # outputs and `area`/`location` colloquially. Accept aliases.
    model_config = ConfigDict(populate_by_name=True)
    section: str = Field(
        validation_alias=AliasChoices("section", "file", "area", "location")
    )
    change: str
    reason: str


class ResumeSection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    title: str = Field(
        validation_alias=AliasChoices("title", "section", "name", "heading")
    )
    bullets: _Bullets = Field(default_factory=list)


# ── Structured resume spec (for high-fidelity rendering) ──────────────
class ContactInfo(BaseModel):
    phone: str | None = None
    email: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    location: str | None = None


class ExperienceItem(BaseModel):
    company: str
    role: str
    location: str | None = None
    start_date: str = ""  # free-form: "Jan 2024", "2021"
    end_date: str | None = None  # None / "" / "Present" all → "Present"
    bullets: _Bullets = Field(default_factory=list)


class EducationItem(BaseModel):
    school: str
    degree: str = ""
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: str | None = None
    notes: _Bullets = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str
    link: str | None = None
    description: str | None = None
    bullets: _Bullets = Field(default_factory=list)


class SkillGroup(BaseModel):
    label: str
    skills: list[str] = Field(default_factory=list)


class GenericSection(BaseModel):
    title: str
    body: str | None = None
    bullets: _Bullets = Field(default_factory=list)


class StyledResume(BaseModel):
    name: str
    headline: str | None = None  # short tagline e.g. "Senior Data Engineer"
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str | None = None
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    extras: list[GenericSection] = Field(default_factory=list)


class PdfSourceResume(BaseModel):
    format: Literal["pdf_source"] = "pdf_source"
    sections: list[ResumeSection] = Field(default_factory=list)
    plain_text: str = ""
    markdown: str = ""
    styled: StyledResume | None = None
    change_log: list[ChangeLogEntry] = Field(default_factory=list)


class TexResume(BaseModel):
    format: Literal["tex"] = "tex"
    full_tex: str
    change_log: list[ChangeLogEntry] = Field(default_factory=list)


class TexProjectFile(BaseModel):
    path: str
    content: str


class TexProjectResume(BaseModel):
    format: Literal["tex_project"] = "tex_project"
    root_file: str
    files: list[TexProjectFile]
    change_log: list[ChangeLogEntry] = Field(default_factory=list)


TailoredResume = Annotated[
    PdfSourceResume | TexResume | TexProjectResume,
    Field(discriminator="format"),
]


# ───────────────────────────────────────────────────────
# Profile extraction (used by the upload-time skill)
# ───────────────────────────────────────────────────────
class SkillEntry(BaseModel):
    name: str
    category: str | None = None
    proficiency: str | None = None


class ExperienceEntry(BaseModel):
    company: str
    role: str
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    bullets: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    institution: str
    degree: str | None = None
    start: str | None = None
    end: str | None = None
    details: str | None = None


class ProfileData(BaseModel):
    full_name: str
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    skills: list[SkillEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
