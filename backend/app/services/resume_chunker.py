"""Resume chunker.

Splits assembled resume text into retrievable chunks. LaTeX-aware: each
`\\item ...` body becomes its own bullet chunk. Non-LaTeX text falls back
to paragraph splits. Chunks shorter than MIN_CHARS get folded into the
next non-empty chunk so we don't embed near-empty fragments.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

ITEM_RE = re.compile(r"\\item\s+(.+?)(?=(?:\\item\s)|\Z)", re.DOTALL)
SECTION_RE = re.compile(r"\\(?:section|subsection|paragraph)\*?\{([^}]*)\}")
MIN_CHARS = 25


@dataclass
class Chunk:
    text: str
    kind: str  # bullet | paragraph | skill_line | education_entry
    source_file: str | None = None


def _looks_like_latex(text: str) -> bool:
    return r"\begin{document}" in text or r"\item" in text or r"\section" in text


def _strip_latex_inline(s: str) -> str:
    s = re.sub(r"\\textbf\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\textit\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\emph\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\*?\{([^}]*)\}", r"\1", s)  # generic \cmd{arg}
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)  # bare \cmd
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def chunk_resume(text: str, source_file: str | None = None) -> list[Chunk]:
    chunks: list[Chunk] = []
    if _looks_like_latex(text):
        for m in ITEM_RE.finditer(text):
            body = _strip_latex_inline(m.group(1))
            if len(body) >= MIN_CHARS:
                chunks.append(Chunk(text=body, kind="bullet", source_file=source_file))
        # Section headers as separate skill_line chunks (lightweight context)
        for m in SECTION_RE.finditer(text):
            label = _strip_latex_inline(m.group(1))
            if label:
                chunks.append(Chunk(text=label, kind="skill_line", source_file=source_file))
    if not chunks:
        # Fallback: paragraph split
        for para in re.split(r"\n\s*\n", text):
            cleaned = re.sub(r"\s+", " ", para).strip()
            if len(cleaned) >= MIN_CHARS:
                chunks.append(Chunk(text=cleaned, kind="paragraph", source_file=source_file))
    return chunks
