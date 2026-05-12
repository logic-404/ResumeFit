import io

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.services.upload_guard import (
    MAX_FILE_BYTES,
    MAX_FILES,
    UploadRejected,
    validate,
)


def _make_file(name: str, content: bytes, content_type: str | None = None) -> UploadFile:
    headers = Headers({"content-type": content_type}) if content_type else None
    return UploadFile(
        filename=name,
        file=io.BytesIO(content),
        headers=headers,
    )


@pytest.mark.asyncio
async def test_rejects_empty():
    with pytest.raises(UploadRejected):
        await validate([])


@pytest.mark.asyncio
async def test_rejects_too_many():
    files = [
        _make_file(f"f{i}.tex", b"x", "text/x-tex") for i in range(MAX_FILES + 1)
    ]
    with pytest.raises(UploadRejected) as exc:
        await validate(files)
    assert exc.value.detail["code"] == "TOO_MANY_FILES"


@pytest.mark.asyncio
async def test_rejects_oversize():
    big = b"x" * (MAX_FILE_BYTES + 1)
    with pytest.raises(UploadRejected) as exc:
        await validate([_make_file("big.pdf", big, "application/pdf")])
    assert exc.value.detail["code"] == "TOO_LARGE"


@pytest.mark.asyncio
async def test_rejects_bad_format():
    with pytest.raises(UploadRejected) as exc:
        await validate(
            [_make_file("evil.exe", b"MZ", "application/octet-stream")]
        )
    assert exc.value.detail["code"] == "BAD_FORMAT"


@pytest.mark.asyncio
async def test_accepts_pdf():
    out = await validate([_make_file("r.pdf", b"%PDF-1.4", "application/pdf")])
    assert len(out) == 1


@pytest.mark.asyncio
async def test_accepts_tex_by_suffix_even_if_mime_generic():
    out = await validate(
        [_make_file("r.tex", b"\\documentclass{article}", "application/octet-stream")]
    )
    assert len(out) == 1
