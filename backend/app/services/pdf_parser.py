from __future__ import annotations

from io import BytesIO

import pdfplumber


def extract_text_from_pdf(data: bytes) -> str:
    pages: list[str] = []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text.strip())
    return "\n\n".join(p for p in pages if p)
