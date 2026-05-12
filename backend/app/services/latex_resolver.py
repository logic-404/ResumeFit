"""LaTeX project resolver.

Finds the root .tex file (the one with \\begin{document}), recursively
inlines \\input{} and \\include{} directives, and emits both the assembled
source text and a directory-tree summary used by downstream tailoring.

Correctness invariants beyond a naive regex pass:
- Comments (lines starting with `%`, or `%` mid-line not preceded by `\\`)
  are stripped before scanning so we don't follow commented-out includes.
- Cycles abort with a clear error rather than recursing forever.
- Missing-file references are left as-is (still a valid LaTeX directive).
"""
from __future__ import annotations

import re
from pathlib import Path

INCLUDE_RE = re.compile(r"\\(?:input|include|subfile)\{([^}]+)\}")
DOC_BEGIN_RE = re.compile(r"\\begin\{document\}")


class LatexResolveError(ValueError):
    pass


def _strip_comments(text: str) -> str:
    """Remove LaTeX comments. A `%` starts a comment unless it's `\\%`."""
    out: list[str] = []
    for line in text.splitlines():
        i = 0
        cleaned: list[str] = []
        while i < len(line):
            ch = line[i]
            if ch == "\\" and i + 1 < len(line) and line[i + 1] == "%":
                cleaned.append("\\%")
                i += 2
                continue
            if ch == "%":
                break
            cleaned.append(ch)
            i += 1
        out.append("".join(cleaned))
    return "\n".join(out)


def _classify(content: str) -> str:
    if DOC_BEGIN_RE.search(content):
        return "root"
    if r"\usepackage" in content or r"\documentclass" in content:
        return "preamble"
    if r"\newcommand" in content or r"\def" in content or r"\renewcommand" in content:
        return "config"
    return "content"


def _find_root(project_dir: Path) -> Path:
    for tex in project_dir.rglob("*.tex"):
        try:
            text = tex.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if DOC_BEGIN_RE.search(_strip_comments(text)):
            return tex
    raise LatexResolveError(r"No root .tex file found containing \begin{document}")


def _resolve(file_path: Path, base_dir: Path, visited: set[Path]) -> str:
    real = file_path.resolve()
    if real in visited:
        raise LatexResolveError(f"\\input cycle detected at {file_path}")
    visited = visited | {real}

    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    stripped = _strip_comments(raw)

    def replace(match: re.Match[str]) -> str:
        ref = match.group(1).strip()
        candidate = (base_dir / ref).resolve()
        if not candidate.suffix:
            candidate = candidate.with_suffix(".tex")
        if not candidate.exists():
            return match.group(0)
        try:
            return _resolve(candidate, base_dir, visited)
        except LatexResolveError:
            raise

    return INCLUDE_RE.sub(replace, stripped)


def resolve_latex_project(project_dir: Path) -> tuple[str, dict]:
    """Return (assembled_text, file_structure)."""
    project_dir = project_dir.resolve()
    root = _find_root(project_dir)

    files = []
    for tex in sorted(project_dir.rglob("*.tex")):
        rel = tex.relative_to(project_dir).as_posix()
        try:
            content = _strip_comments(tex.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        files.append({"path": rel, "role": _classify(content)})

    file_structure = {
        "root_file": root.relative_to(project_dir).as_posix(),
        "files": files,
    }

    assembled = _resolve(root, project_dir, visited=set())
    return assembled, file_structure
