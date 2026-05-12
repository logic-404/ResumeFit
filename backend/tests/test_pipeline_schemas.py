import pytest
from pydantic import ValidationError, TypeAdapter

from app.schemas.pipeline import (
    CoverLetter,
    GapAnalysis,
    ParsedJD,
    PdfSourceResume,
    ResumeSection,
    TailoredResume,
    TexProjectFile,
    TexProjectResume,
    TexResume,
)


def test_parsed_jd_required_fields():
    jd = ParsedJD(
        role="ML Engineer",
        company="Atlassian",
        experience_level="mid",
        required_skills=["Python", "PyTorch"],
        responsibilities=["Build ML pipelines"],
    )
    assert jd.role == "ML Engineer"
    assert jd.preferred_skills == []


def test_parsed_jd_rejects_bad_experience_level():
    with pytest.raises(ValidationError):
        ParsedJD(role="x", company="y", experience_level="wizard")


def test_gap_score_bounds():
    with pytest.raises(ValidationError):
        GapAnalysis(overall_match_score=1.5, recommendation="x")
    with pytest.raises(ValidationError):
        GapAnalysis(overall_match_score=-0.1, recommendation="x")
    ok = GapAnalysis(overall_match_score=0.7, recommendation="strong")
    assert ok.overall_match_score == 0.7


def test_cover_letter_body_length():
    with pytest.raises(ValidationError):
        CoverLetter(
            opening_paragraph="hi",
            body_paragraphs=[],
            closing_paragraph="bye",
            sign_off="kind regards",
            tone_score=0.5,
            keyword_match_count=3,
        )
    with pytest.raises(ValidationError):
        CoverLetter(
            opening_paragraph="hi",
            body_paragraphs=["a", "b", "c", "d"],
            closing_paragraph="bye",
            sign_off="kind regards",
            tone_score=0.5,
            keyword_match_count=3,
        )


def test_tailored_resume_discriminator_dispatch():
    adapter = TypeAdapter(TailoredResume)

    pdf = adapter.validate_python(
        {
            "format": "pdf_source",
            "sections": [{"title": "Experience", "bullets": ["did a thing"]}],
            "plain_text": "...",
            "markdown": "## Experience\n- did a thing",
        }
    )
    assert isinstance(pdf, PdfSourceResume)

    tex = adapter.validate_python({"format": "tex", "full_tex": "\\documentclass{}"})
    assert isinstance(tex, TexResume)

    proj = adapter.validate_python(
        {
            "format": "tex_project",
            "root_file": "main.tex",
            "files": [{"path": "main.tex", "content": "..."}],
        }
    )
    assert isinstance(proj, TexProjectResume)


def test_tex_project_round_trip():
    p = TexProjectResume(
        root_file="main.tex",
        files=[TexProjectFile(path="main.tex", content="x")],
    )
    assert p.format == "tex_project"
    assert p.files[0].path == "main.tex"
