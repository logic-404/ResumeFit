import io
import shutil
import zipfile

import pytest

from app.config import settings
from app.services.resume_packager import package


_HAS_PDFLATEX = shutil.which(settings.pdflatex_bin) is not None


def test_package_pdf_source_renders_pdf():
    data, name, mt = package(
        {
            "format": "pdf_source",
            "sections": [{"title": "Experience", "bullets": ["did a thing"]}],
            "plain_text": "experience: did a thing",
            "markdown": "## Experience\n- did a thing",
        }
    )
    assert name == "tailored_resume.pdf"
    assert mt == "application/pdf"
    assert data.startswith(b"%PDF")


def test_package_tex_pdf_or_tex_fallback():
    data, name, mt = package(
        {
            "format": "tex",
            "full_tex": r"\documentclass{article}\begin{document}hi\end{document}",
        }
    )
    if _HAS_PDFLATEX:
        assert name == "tailored_resume.pdf"
        assert mt == "application/pdf"
        assert data.startswith(b"%PDF")
    else:
        assert name == "tailored_resume.tex"
        assert mt == "application/x-tex"


def test_package_tex_project_pdf_or_zip_fallback():
    payload = {
        "format": "tex_project",
        "root_file": "main.tex",
        "files": [
            {
                "path": "main.tex",
                "content": r"\documentclass{article}\begin{document}\input{sections/exp}\end{document}",
            },
            {"path": "sections/exp.tex", "content": "exp"},
        ],
    }
    data, name, mt = package(payload)
    if _HAS_PDFLATEX:
        assert name == "tailored_resume.pdf"
        assert mt == "application/pdf"
        assert data.startswith(b"%PDF")
    else:
        assert name == "tailored_resume.zip"
        assert mt == "application/zip"
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = sorted(zf.namelist())
            assert "main.tex" in names
            assert "sections/exp.tex" in names


def test_package_rejects_path_traversal_in_zip_fallback():
    if _HAS_PDFLATEX:
        pytest.skip("pdflatex present — zip fallback not exercised")
    data, _, _ = package(
        {
            "format": "tex_project",
            "root_file": "main.tex",
            "files": [
                {"path": "main.tex", "content": "x"},
                {"path": "../escape.tex", "content": "evil"},
            ],
        }
    )
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        assert all(".." not in n for n in names)


def test_package_pdf_source_styled_renders_pdf():
    data, name, mt = package(
        {
            "format": "pdf_source",
            "markdown": "",
            "plain_text": "",
            "sections": [],
            "styled": {
                "name": "Tanvir Singh",
                "headline": "Senior Data Engineer",
                "contact": {
                    "email": "tanvir@example.com",
                    "phone": "+61 451 616 111",
                    "linkedin": "linkedin.com/in/tanvir",
                    "location": "Sydney, AU",
                },
                "summary": "Engineer with 6+ years building data platforms.",
                "experience": [
                    {
                        "company": "Acme",
                        "role": "Data Engineer",
                        "location": "Remote",
                        "start_date": "Jan 2023",
                        "end_date": "Present",
                        "bullets": [
                            "Led migration of legacy ETL to Python; cut p99 latency 35%.",
                            "Owned schema-aware retrieval pipeline serving 4M docs.",
                        ],
                    }
                ],
                "education": [
                    {
                        "school": "QUT",
                        "degree": "MIT (Data Science)",
                        "end_date": "2026",
                        "gpa": "5.9/7",
                    }
                ],
                "skills": [
                    {"label": "Languages", "skills": ["Python", "Go"]},
                ],
                "projects": [
                    {
                        "name": "Atelier",
                        "description": "Job application engine.",
                        "bullets": ["Streaming SSE pipeline."],
                    }
                ],
            },
        }
    )
    assert name == "tailored_resume.pdf"
    assert mt == "application/pdf"
    assert data.startswith(b"%PDF")


def test_package_invalid_format_raises():
    with pytest.raises(Exception):
        package({"format": "bogus"})
