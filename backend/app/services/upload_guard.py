"""Upload validation: size, MIME, file count.

Runs before any disk write or parser call. Defends against oversized
files, hostile MIME types, and zip-bomb-style multi-file uploads.
"""
from __future__ import annotations

from fastapi import HTTPException, UploadFile

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_FILES = 50

ALLOWED_MIME_PREFIXES: tuple[str, ...] = (
    "application/pdf",
    "application/x-tex",
    "application/x-latex",
    "text/",
)
ALLOWED_SUFFIXES: tuple[str, ...] = (".pdf", ".tex", ".sty", ".cls", ".bib")


class UploadRejected(HTTPException):
    def __init__(self, code: str, message: str):
        super().__init__(
            status_code=413 if code == "TOO_LARGE" else 400,
            detail={"code": code, "message": message},
        )


def _suffix_ok(filename: str) -> bool:
    name = (filename or "").lower()
    return any(name.endswith(s) for s in ALLOWED_SUFFIXES)


def _mime_ok(content_type: str | None) -> bool:
    if not content_type:
        return False
    return any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES)


async def validate(files: list[UploadFile]) -> list[tuple[UploadFile, bytes]]:
    """Read and validate uploaded files. Returns [(file, bytes), ...].

    Reads the bodies into memory (bounded by MAX_FILE_BYTES * MAX_FILES).
    """
    if not files:
        raise UploadRejected("NO_FILES", "No files uploaded")
    if len(files) > MAX_FILES:
        raise UploadRejected("TOO_MANY_FILES", f"Max {MAX_FILES} files per upload")

    out: list[tuple[UploadFile, bytes]] = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            raise UploadRejected(
                "TOO_LARGE",
                f"{f.filename}: exceeds {MAX_FILE_BYTES // (1024 * 1024)} MB",
            )
        # Accept by either filename suffix or MIME — some browsers lie.
        if not (_suffix_ok(f.filename or "") or _mime_ok(f.content_type)):
            raise UploadRejected(
                "BAD_FORMAT",
                f"{f.filename}: unsupported format ({f.content_type})",
            )
        out.append((f, data))
    return out
