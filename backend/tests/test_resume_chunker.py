from app.services.resume_chunker import chunk_resume


def test_latex_items_become_bullets():
    src = r"""
\begin{itemize}
\item Built a multi-agent system using LangGraph for orchestration
\item Designed a stateful Agentic RAG pipeline with semantic retrieval
\end{itemize}
"""
    chunks = chunk_resume(src)
    bullets = [c for c in chunks if c.kind == "bullet"]
    assert len(bullets) == 2
    assert any("multi-agent" in b.text for b in bullets)


def test_paragraph_fallback_for_plain_text():
    src = (
        "Tanvir Singh\nMelbourne, Australia\n\n"
        "Worked on production ML systems handling millions of requests daily.\n\n"
        "Architected agentic data synthesis pipelines."
    )
    chunks = chunk_resume(src)
    assert all(c.kind == "paragraph" for c in chunks)
    assert len(chunks) >= 2


def test_short_chunks_dropped():
    src = "x\n\ny\n\n" + "long enough chunk here to be retained in output." * 1
    chunks = chunk_resume(src)
    assert all(len(c.text) >= 25 for c in chunks)


def test_latex_inline_macros_stripped():
    src = r"""
\begin{itemize}
\item Built \textbf{ML pipelines} on \textit{AWS} with high reliability metrics
\end{itemize}
"""
    [chunk] = [c for c in chunk_resume(src) if c.kind == "bullet"]
    assert "\\textbf" not in chunk.text
    assert "ML pipelines" in chunk.text
    assert "AWS" in chunk.text
