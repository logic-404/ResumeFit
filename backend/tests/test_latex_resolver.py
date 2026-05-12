from pathlib import Path

import pytest

from app.services.latex_resolver import (
    LatexResolveError,
    _strip_comments,
    resolve_latex_project,
)


def test_strip_comments_simple():
    src = "hello % a comment\nworld"
    assert _strip_comments(src) == "hello \nworld"


def test_strip_comments_preserves_escaped_percent():
    src = r"value: 50\%"
    assert _strip_comments(src) == r"value: 50\%"


def test_strip_comments_full_line():
    src = "% whole line\nactual"
    assert _strip_comments(src) == "\nactual"


def test_resolve_basic_project(tmp_path: Path):
    (tmp_path / "main.tex").write_text(
        r"""\documentclass{article}
\begin{document}
\input{sections/experience}
\end{document}
""",
        encoding="utf-8",
    )
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections" / "experience.tex").write_text(
        "EXPERIENCE_BODY\n", encoding="utf-8"
    )

    text, structure = resolve_latex_project(tmp_path)
    assert "EXPERIENCE_BODY" in text
    assert structure["root_file"] == "main.tex"
    paths = {f["path"] for f in structure["files"]}
    assert "main.tex" in paths
    assert "sections/experience.tex" in paths


def test_commented_input_ignored(tmp_path: Path):
    (tmp_path / "main.tex").write_text(
        r"""\documentclass{article}
\begin{document}
% \input{sections/secret}
DONE
\end{document}
""",
        encoding="utf-8",
    )
    (tmp_path / "sections").mkdir()
    (tmp_path / "sections" / "secret.tex").write_text("SHOULD_NOT_APPEAR\n", encoding="utf-8")

    text, _ = resolve_latex_project(tmp_path)
    assert "SHOULD_NOT_APPEAR" not in text
    assert "DONE" in text


def test_cycle_detected(tmp_path: Path):
    (tmp_path / "main.tex").write_text(
        r"""\begin{document}
\input{a}
\end{document}
""",
        encoding="utf-8",
    )
    (tmp_path / "a.tex").write_text(r"\input{b}", encoding="utf-8")
    (tmp_path / "b.tex").write_text(r"\input{a}", encoding="utf-8")

    with pytest.raises(LatexResolveError):
        resolve_latex_project(tmp_path)


def test_missing_root_raises(tmp_path: Path):
    (tmp_path / "stub.tex").write_text("just a stub", encoding="utf-8")
    with pytest.raises(LatexResolveError):
        resolve_latex_project(tmp_path)


def test_extension_auto_suffix(tmp_path: Path):
    (tmp_path / "main.tex").write_text(
        r"""\begin{document}
\input{body}
\end{document}
""",
        encoding="utf-8",
    )
    (tmp_path / "body.tex").write_text("BODY_FOUND", encoding="utf-8")

    text, _ = resolve_latex_project(tmp_path)
    assert "BODY_FOUND" in text
