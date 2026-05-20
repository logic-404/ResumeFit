"""Render a StyledResume to a recruiter-grade HTML/PDF document.

This is the resume-design skill: layout, typography, spacing, and ATS-safe
markup live here. The LLM (tailor_resume skill) produces the *content* spec;
this module produces the *visual document*.

Best practices applied (web-researched, cross-referenced with Harvard
career-center, Google Docs default, and modern recruiter guidance):

- Single column, no layout columns/grids — ATS parsers index L→R T→B.
- 0.5in vertical / 0.65in horizontal margins (industry norm 0.5–1in).
- Body 10.5pt, name 22pt, section heads 10.5pt small-caps with hairline rule.
- **Dates rendered on a SECOND line below role/school**, italic + muted.
  Avoids the collision problem of float-right dates and reads cleaner.
- Tight bullet spacing (1.5pt) for density without crowding; 1.15 line-height
  (resume norm — 1.4 inflated rendered output ~1 full page vs source).
- Helvetica family — most consistent across PDF readers and ATS engines.
- Color used sparingly: deep slate body, near-black headings; muted grey for
  meta/dates/location. Survives black-and-white printing.
- Conventional section ORDER: Summary → Experience → Education → Skills →
  Projects → Extras (awards / certifications / leadership).
- Extras with role/dates patterns get rendered as experience-style rows
  under a shared "Activities & Leadership" section (LLM convention is to
  emit one GenericSection per role — group them).
- No emoji, no decorative icons (ATS noise).
- All HTML escaped — safe against injection.

CSS subset is xhtml2pdf-compatible: no flex, no grid, no sibling combinators.
"""
from __future__ import annotations

import html
import re
from typing import Iterable

from app.schemas.pipeline import (
    ContactInfo,
    EducationItem,
    ExperienceItem,
    GenericSection,
    ProjectItem,
    SkillGroup,
    StyledResume,
)


# ──────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────
STYLED_CSS = """
@page { size: Letter; margin: 0.5in 0.65in; }
body {
  font-family: "Helvetica", "Arial", sans-serif;
  font-size: 10.5pt;
  color: #1f2937;
  line-height: 1.15;
}

/* ── Header ──────────────────────────────────────────── */
h1.name {
  font-size: 22pt;
  margin: 0;
  text-align: center;
  letter-spacing: 0.4pt;
  color: #0f172a;
  font-weight: bold;
}
.headline {
  text-align: center;
  font-size: 11pt;
  color: #374151;
  margin: 2pt 0 4pt 0;
  font-style: italic;
}
.contact {
  text-align: center;
  font-size: 9.5pt;
  color: #475569;
  margin: 0 0 10pt 0;
}
.contact a { color: #475569; text-decoration: none; }

/* ── Section heads ───────────────────────────────────── */
h2.section {
  font-size: 10.5pt;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.6pt;
  color: #0f172a;
  border-bottom: 1pt solid #0f172a;
  margin: 9pt 0 4pt 0;
  padding-bottom: 1pt;
  /* never leave a section heading alone at the foot of a page */
  -pdf-keep-with-next: true;
}

/* ── Item rows ───────────────────────────────────────── */
.item { margin: 4pt 0 3pt 0; }
.item-title {
  font-weight: bold;
  font-size: 10.8pt;
  color: #0f172a;
  margin: 0;
  /* role/school title must not split from its meta/bullets */
  -pdf-keep-with-next: true;
}
.item-meta {
  font-size: 9.5pt;
  font-style: italic;
  color: #6b7280;
  margin: 1pt 0 3pt 0;
  -pdf-keep-with-next: true;
}

/* ── Bullets ─────────────────────────────────────────── */
ul.bullets {
  margin: 2pt 0 3pt 16pt;
  padding: 0;
}
ul.bullets li {
  margin-bottom: 1.5pt;
  padding-left: 2pt;
}

/* ── Content blocks ──────────────────────────────────── */
.summary {
  margin: 0 0 4pt 0;
  font-size: 10.5pt;
  color: #1f2937;
}
.skill-row { margin: 2pt 0; }
.skill-row .label {
  font-weight: bold;
  color: #0f172a;
}
.project-stack {
  font-size: 9.5pt;
  font-style: italic;
  color: #6b7280;
  margin: 1pt 0 3pt 0;
  -pdf-keep-with-next: true;
}
.project-link {
  font-weight: normal;
  font-style: italic;
  font-size: 9.5pt;
  color: #475569;
}
.project-link a { color: #475569; text-decoration: none; }
"""


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _e(s: str | None) -> str:
    return html.escape(s) if s else ""


def _url(s: str | None) -> str:
    """Absolute URL for href. Bare domains (linkedin.com/in/x) get
    https:// — xhtml2pdf treats a schemeless href as relative, so the
    link is not clickable without this."""
    if not s:
        return ""
    u = s.strip()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", u):
        u = "https://" + u
    return html.escape(u, quote=True)


def _date_range(start: str | None, end: str | None) -> str:
    s = (start or "").strip()
    e = (end or "").strip()
    if not s and not e:
        return ""
    if not e or e.lower() in {"present", "current", "now"}:
        e_disp = "Present"
    else:
        e_disp = e
    if not s:
        return _e(e_disp)
    return f"{_e(s)} &ndash; {_e(e_disp)}"


def _meta_line(parts: Iterable[str]) -> str:
    """Join non-empty meta parts with bullet separators on a single line."""
    items = [p for p in parts if p]
    return " &nbsp;·&nbsp; ".join(items)


def _bullets(bullets: list[str]) -> str:
    if not bullets:
        return ""
    items = "".join(f"<li>{_e(b)}</li>" for b in bullets if b and b.strip())
    return f'<ul class="bullets">{items}</ul>' if items else ""


# ──────────────────────────────────────────────────────────
# Sections
# ──────────────────────────────────────────────────────────
def _render_contact(c: ContactInfo) -> str:
    parts: list[str] = []
    if c.phone:
        parts.append(_e(c.phone))
    if c.email:
        parts.append(f'<a href="mailto:{_e(c.email)}">{_e(c.email)}</a>')
    if c.linkedin:
        parts.append(f'<a href="{_url(c.linkedin)}">{_e(c.linkedin)}</a>')
    if c.github:
        parts.append(f'<a href="{_url(c.github)}">{_e(c.github)}</a>')
    if c.website:
        parts.append(f'<a href="{_url(c.website)}">{_e(c.website)}</a>')
    if c.location:
        parts.append(_e(c.location))
    if not parts:
        return ""
    return f'<p class="contact">{_meta_line(parts)}</p>'


def _render_summary(summary: str | None) -> str:
    if not summary or not summary.strip():
        return ""
    return (
        '<h2 class="section">Summary</h2>'
        f'<div class="summary">{_e(summary)}</div>'
    )


def _experience_item_html(it: ExperienceItem) -> str:
    title = f"{_e(it.role)} &mdash; {_e(it.company)}" if it.company else _e(it.role)
    meta = _meta_line(
        [
            _date_range(it.start_date, it.end_date),
            _e(it.location),
        ]
    )
    return (
        '<div class="item">'
        f'<div class="item-title">{title}</div>'
        + (f'<div class="item-meta">{meta}</div>' if meta else "")
        + _bullets(it.bullets)
        + "</div>"
    )


def _render_experience(items: list[ExperienceItem]) -> str:
    if not items:
        return ""
    return '<h2 class="section">Experience</h2>' + "".join(
        _experience_item_html(it) for it in items
    )


def _render_education(items: list[EducationItem]) -> str:
    if not items:
        return ""
    rows: list[str] = []
    for it in items:
        title = _e(it.school)
        meta_parts: list[str] = []
        if it.degree:
            meta_parts.append(_e(it.degree))
        if it.gpa:
            meta_parts.append(f"GPA {_e(it.gpa)}")
        if it.location:
            meta_parts.append(_e(it.location))
        date = _date_range(it.start_date, it.end_date)
        if date:
            meta_parts.append(date)
        meta = _meta_line(meta_parts)
        rows.append(
            '<div class="item">'
            f'<div class="item-title">{title}</div>'
            + (f'<div class="item-meta">{meta}</div>' if meta else "")
            + _bullets(it.notes)
            + "</div>"
        )
    return '<h2 class="section">Education</h2>' + "".join(rows)


def _render_skills(groups: list[SkillGroup]) -> str:
    if not groups:
        return ""
    rows: list[str] = []
    for g in groups:
        if not g.skills:
            continue
        rows.append(
            f'<div class="skill-row"><span class="label">{_e(g.label)}:</span> '
            f'{_e(", ".join(g.skills))}</div>'
        )
    if not rows:
        return ""
    return '<h2 class="section">Skills</h2>' + "".join(rows)


def _render_projects(items: list[ProjectItem]) -> str:
    if not items:
        return ""
    rows: list[str] = []
    for it in items:
        title = _e(it.name)
        if it.link:
            title += (
                ' <span class="project-link">&middot; '
                f'<a href="{_url(it.link)}">{_e(it.link)}</a></span>'
            )
        stack = (
            f'<div class="project-stack">{_e(it.description)}</div>'
            if it.description
            else ""
        )
        rows.append(
            '<div class="item">'
            f'<div class="item-title">{title}</div>'
            f"{stack}"
            + _bullets(it.bullets)
            + "</div>"
        )
    return '<h2 class="section">Projects</h2>' + "".join(rows)


# ── Extras handling ───────────────────────────────────────
# LLM convention: leadership / activities arrive as multiple GenericSection
# entries with role-shaped titles ("Project Director — TECH, QUT" etc).
# Group them under one section head if the pattern looks like roles.
_ROLE_SHAPED = re.compile(r" [—–|-] ")


def _is_role_shaped_title(title: str) -> bool:
    return bool(_ROLE_SHAPED.search(title))


def _split_role_shaped_title(title: str) -> tuple[str, str]:
    """Try to separate primary role/title from organisation/location.

    Returns (primary, secondary). Common shapes:
      "Tech Head | Computer Engineering Society, X"
      "Project Director — TECH, QUT"
      "Research Assistant – Dept. of CS — Guru Nanak Dev University"
    """
    # Cut off "Leadership & Experience — " style prefixes the LLM emits.
    cleaned = re.sub(r"^(leadership|activit(ies|y))\s*&\s*\w+\s*[—–-]\s*", "",
                     title, flags=re.IGNORECASE)
    parts = re.split(r"\s+[—–|]\s+", cleaned, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return cleaned.strip(), ""


def _render_extras(extras: list[GenericSection]) -> str:
    if not extras:
        return ""

    # If majority of extras have role-shaped titles, render as a single
    # "Activities & Leadership" section with experience-style rows.
    role_like = [e for e in extras if _is_role_shaped_title(e.title)]
    if len(role_like) >= max(1, len(extras) // 2):
        rows: list[str] = []
        for e in extras:
            primary, secondary = _split_role_shaped_title(e.title)
            title_html = _e(primary)
            if secondary:
                title_html += f" &mdash; {_e(secondary)}"
            meta = ""
            if e.body:
                meta = f'<div class="item-meta">{_e(e.body)}</div>'
            rows.append(
                '<div class="item">'
                f'<div class="item-title">{title_html}</div>'
                f"{meta}"
                + _bullets(e.bullets)
                + "</div>"
            )
        return (
            '<h2 class="section">Activities &amp; Leadership</h2>'
            + "".join(rows)
        )

    # Otherwise: each extra is its own short section.
    out: list[str] = []
    for s in extras:
        body = (
            f'<div class="summary">{_e(s.body)}</div>' if s.body else ""
        )
        out.append(
            f'<h2 class="section">{_e(s.title)}</h2>'
            f'<div class="item">{body}{_bullets(s.bullets)}</div>'
        )
    return "".join(out)


# ──────────────────────────────────────────────────────────
# Public entry
# ──────────────────────────────────────────────────────────
def render_styled_html(resume: StyledResume) -> str:
    name = _e(resume.name) or "Resume"
    headline = (
        f'<div class="headline">{_e(resume.headline)}</div>'
        if resume.headline
        else ""
    )
    contact = _render_contact(resume.contact)
    body = (
        _render_summary(resume.summary)
        + _render_experience(resume.experience)
        + _render_education(resume.education)
        + _render_skills(resume.skills)
        + _render_projects(resume.projects)
        + _render_extras(resume.extras)
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{STYLED_CSS}</style></head>
<body>
<h1 class="name">{name}</h1>
{headline}
{contact}
{body}
</body></html>"""
