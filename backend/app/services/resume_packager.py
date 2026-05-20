"""Serialise a TailoredResume payload back into a downloadable PDF.

Goal: always hand the user a single PDF regardless of source format.

- pdf_source  → render markdown / sections to styled HTML, then HTML→PDF
                via xhtml2pdf.
- tex         → pdflatex compile → PDF.
- tex_project → write tree, pdflatex compile root_file → PDF.

If pdflatex is unavailable, tex / tex_project gracefully fall back to the
raw .tex / .zip source so the user still has something to compile locally.
"""
from __future__ import annotations

import html as _html
import io
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

import markdown as md_lib
from pydantic import TypeAdapter
from xhtml2pdf import pisa

from app.config import settings
from app.schemas.pipeline import (
    PdfSourceResume,
    ResumeSection,
    TailoredResume,
    TexProjectResume,
    TexResume,
)

_ADAPTER = TypeAdapter(TailoredResume)
_PDFLATEX_TIMEOUT = 60


# ──────────────────────────────────────────────────────────
# pdf_source → HTML → PDF
# ──────────────────────────────────────────────────────────
_RESUME_CSS = """
@page { size: Letter; margin: 0.5in 0.65in; }
body {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 10.5pt;
  color: #1f2937;
  line-height: 1.15;
}
/* Name */
h1 {
  font-size: 22pt;
  font-weight: bold;
  margin: 0 0 4pt 0;
  text-align: center;
  letter-spacing: 0.6pt;
  color: #0f172a;
}
/* Contact line — first paragraph after the name. xhtml2pdf does not
   support adjacent-sibling selectors, so a class is injected during
   post-processing of the rendered markdown. */
p.contact {
  text-align: center;
  font-size: 9.5pt;
  color: #475569;
  margin: 0 0 10pt 0;
}
/* Section heading */
h2 {
  font-size: 10.5pt;
  font-weight: bold;
  margin: 9pt 0 4pt 0;
  padding-bottom: 2pt;
  border-bottom: 1pt solid #0f172a;
  text-transform: uppercase;
  letter-spacing: 1.4pt;
  color: #0f172a;
}
/* Role / sub-heading */
h3 {
  font-size: 11pt;
  font-weight: bold;
  margin: 8pt 0 2pt 0;
  color: #0f172a;
}
p { margin: 2pt 0; }
ul { margin: 2pt 0 3pt 16pt; padding: 0; }
li { margin: 0 0 1.5pt 0; padding-left: 2pt; }
strong, b { color: #0f172a; font-weight: bold; }
em, i { color: #475569; font-style: italic; }
hr { border: none; border-top: 0.5pt solid #cbd5e1; margin: 6pt 0; }
a { color: #0f172a; text-decoration: none; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0; font-size: 10pt; }
th, td { padding: 3pt 5pt; border-bottom: 0.5pt solid #e2e8f0; vertical-align: top; }
th { font-weight: bold; color: #0f172a; text-align: left; }
"""


def _sections_to_md(sections: list[ResumeSection]) -> str:
    parts: list[str] = []
    for s in sections:
        parts.append(f"## {s.title}")
        for b in s.bullets:
            parts.append(f"- {b}")
        parts.append("")
    return "\n".join(parts)


_CONTACT_AFTER_H1 = re.compile(
    r"(</h1>\s*)<p>", flags=re.IGNORECASE
)


def _resume_html(resume: PdfSourceResume) -> str:
    body_md = (
        resume.markdown.strip()
        or _sections_to_md(resume.sections).strip()
        or _html.escape(resume.plain_text)
    )
    body_html = md_lib.markdown(
        body_md,
        extensions=["extra", "sane_lists"],
    )
    # Tag the first paragraph after <h1> with class="contact" so the
    # contact line styling applies without a sibling-combinator rule.
    body_html = _CONTACT_AFTER_H1.sub(r'\1<p class="contact">', body_html, count=1)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_RESUME_CSS}</style></head>
<body>{body_html}</body></html>"""


def _html_to_pdf(html: str) -> bytes:
    buf = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buf, encoding="utf-8")
    if result.err:
        raise RuntimeError(f"xhtml2pdf failed: {result.err} errors")
    return buf.getvalue()


# ──────────────────────────────────────────────────────────
# tex / tex_project → pdflatex → PDF
# ──────────────────────────────────────────────────────────
def _normalise_files(files: list[tuple[str, str]]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for rel, content in files:
        rel = rel.lstrip("/").replace("\\", "/")
        if ".." in rel.split("/"):
            continue
        out.append((rel, content))
    return out


def _compile_tex_pdf(files: list[tuple[str, str]], root: str) -> bytes | None:
    binary = settings.pdflatex_bin
    if shutil.which(binary) is None:
        return None
    files = _normalise_files(files)
    root = root.lstrip("/").replace("\\", "/")
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for rel, content in files:
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(content, encoding="utf-8")
        for _ in range(2):  # twice for refs
            try:
                proc = subprocess.run(
                    [
                        binary,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        "-output-directory", str(base),
                        str(base / root),
                    ],
                    cwd=str(base),
                    capture_output=True,
                    timeout=_PDFLATEX_TIMEOUT,
                )
            except (FileNotFoundError, subprocess.TimeoutExpired):
                return None
            if proc.returncode != 0:
                return None
        pdf_path = base / Path(root).with_suffix(".pdf").name
        if pdf_path.exists():
            return pdf_path.read_bytes()
        return None


def _zip_files(files: list[tuple[str, str]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, content in files:
            zf.writestr(rel, content)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────
# Public entry
# ──────────────────────────────────────────────────────────
def package(content: dict) -> tuple[bytes, str, str]:
    """Return (data, filename, media_type). Always tries PDF first."""
    resume = _ADAPTER.validate_python(content)

    if isinstance(resume, PdfSourceResume):
        # Prefer structured spec when present — recruiter-grade layout via
        # dedicated styled renderer (web-researched best practice).
        if resume.styled is not None and resume.styled.name:
            from app.services.resume_styled import render_styled_html
            return (
                _html_to_pdf(render_styled_html(resume.styled)),
                "tailored_resume.pdf",
                "application/pdf",
            )
        return (
            _html_to_pdf(_resume_html(resume)),
            "tailored_resume.pdf",
            "application/pdf",
        )

    if isinstance(resume, TexResume):
        pdf = _compile_tex_pdf([("main.tex", resume.full_tex)], "main.tex")
        if pdf is not None:
            return pdf, "tailored_resume.pdf", "application/pdf"
        return (
            resume.full_tex.encode("utf-8"),
            "tailored_resume.tex",
            "application/x-tex",
        )

    if isinstance(resume, TexProjectResume):
        files = [(f.path, f.content) for f in resume.files]
        pdf = _compile_tex_pdf(files, resume.root_file)
        if pdf is not None:
            return pdf, "tailored_resume.pdf", "application/pdf"
        return (
            _zip_files(_normalise_files(files)),
            "tailored_resume.zip",
            "application/zip",
        )

    raise ValueError("Unknown tailored resume format")
