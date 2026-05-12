"""latex_compile_check: run pdflatex on rewritten files in a temp dir.

Returns ok/log/missing_refs so the caller (tailor_resume skill) can
decide whether to trigger a single repair pass before persisting. No-ops
gracefully when pdflatex isn't installed or the feature is disabled.
"""
from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path

from app.config import settings
from app.tools.registry import Tool, registry

COMPILE_TIMEOUT = 30.0
ERROR_LINE_RE = re.compile(r"^!\s.+", re.MULTILINE)
MISSING_RE = re.compile(r"File `([^']+)' not found", re.IGNORECASE)


async def _run(args: dict) -> dict:
    if not settings.enable_latex_compile:
        return {"ok": True, "skipped": True, "log": "compile disabled", "missing_refs": []}

    files = args["files"]  # list of {path, content}
    root_file = args.get("root_file")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for f in files:
            rel = f["path"]
            if rel.startswith("/") or ".." in rel.replace("\\", "/").split("/"):
                return {"ok": False, "log": f"suspicious path: {rel}", "missing_refs": []}
            dst = base / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(f["content"], encoding="utf-8")

        if root_file is None:
            tex_files = list(base.rglob("*.tex"))
            for t in tex_files:
                if r"\begin{document}" in t.read_text(encoding="utf-8", errors="ignore"):
                    root_file = str(t.relative_to(base).as_posix())
                    break
        if root_file is None:
            return {"ok": False, "log": "no root .tex found", "missing_refs": []}

        try:
            proc = await asyncio.create_subprocess_exec(
                settings.pdflatex_bin,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(base),
                str(base / root_file),
                cwd=str(base),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except (FileNotFoundError, NotImplementedError) as e:
            # pdflatex missing OR Windows SelectorEventLoop can't spawn
            # subprocesses. Skip rather than break the pipeline.
            return {
                "ok": True,
                "skipped": True,
                "log": f"pdflatex unavailable: {e!r}",
                "missing_refs": [],
            }
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=COMPILE_TIMEOUT)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "log": "pdflatex timeout", "missing_refs": []}

        log = (stdout or b"").decode("utf-8", errors="ignore")
        ok = proc.returncode == 0
        errors = ERROR_LINE_RE.findall(log)[:10]
        missing = list({m for m in MISSING_RE.findall(log)})
        return {
            "ok": ok,
            "log": "\n".join(errors) if errors else "ok",
            "missing_refs": missing,
            "exit_code": proc.returncode,
        }


latex_compile_tool = registry.register(
    Tool(
        name="latex_compile_check",
        description=(
            "Compile a set of LaTeX files with pdflatex. Returns whether compilation "
            "succeeded, key errors, and any missing-file references."
        ),
        parameters={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
                "root_file": {"type": "string", "description": "Optional root path"},
            },
            "required": ["files"],
        },
        run=_run,
    )
)
