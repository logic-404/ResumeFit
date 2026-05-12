"""entity_diff: catch fabricated companies, dates, or numerics.

Pure-Python check (no LLM): tokenises proper nouns and numerics in both
source and output, returns any tokens present in the output but absent
from the source. The tailor_resume skill calls this after generation; a
non-empty `fabricated` list triggers a regenerate.
"""
from __future__ import annotations

import re

from app.tools.registry import Tool, registry

CAPITALIZED_RE = re.compile(r"\b[A-Z][A-Za-z0-9&]*(?:[\-\.][A-Za-z0-9&]+)*\b")
DATE_RE = re.compile(
    r"\b(?:\d{4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}|"
    r"\d{1,2}/\d{4})\b"
)
NUMERIC_RE = re.compile(r"\b\d+(?:[\.,]\d+)*\b")

# Common words that would otherwise look like proper nouns.
STOPWORDS = {
    "I",
    "A",
    "The",
    "An",
    "And",
    "Or",
    "But",
    "If",
    "When",
    "While",
    "We",
    "Our",
    "You",
    "Your",
    "My",
    "Me",
    "Dear",
    "Hiring",
    "Manager",
    "Sincerely",
    "Regards",
    "Kind",
    "Best",
}


def _tokens(text: str, regex: re.Pattern[str]) -> set[str]:
    return {m.group(0) for m in regex.finditer(text)}


def _ci(tokens: set[str]) -> set[str]:
    return {t.casefold() for t in tokens}


async def _run(args: dict) -> dict:
    source: str = args["source"]
    output: str = args["output"]

    # Compare case-insensitively against ALL words in source (not just
    # capitalised ones) — handles sentence-start capitalisation in the
    # output that appears mid-sentence in the source.
    src_word_set = _ci(set(re.findall(r"[A-Za-z][A-Za-z0-9&\-\.]*", source)))
    stop_ci = _ci(STOPWORDS)

    out_caps = _tokens(output, CAPITALIZED_RE)
    fabricated_entities = sorted(
        t for t in out_caps
        if t.casefold() not in src_word_set and t.casefold() not in stop_ci
    )

    src_dates = _tokens(source, DATE_RE)
    out_dates = _tokens(output, DATE_RE)
    fabricated_dates = sorted(out_dates - src_dates)

    src_nums = _tokens(source, NUMERIC_RE)
    out_nums = _tokens(output, NUMERIC_RE)
    fabricated_numerics = sorted(n for n in (out_nums - src_nums) if len(n) >= 2)

    fabricated = fabricated_entities + fabricated_dates + fabricated_numerics
    return {
        "ok": len(fabricated) == 0,
        "fabricated_entities": fabricated_entities,
        "fabricated_dates": fabricated_dates,
        "fabricated_numerics": fabricated_numerics,
    }


entity_diff_tool = registry.register(
    Tool(
        name="entity_diff",
        description=(
            "Compare an output document against a source resume. Returns any "
            "proper nouns, dates, or numerics that appear in the output but not "
            "the source — i.e. likely fabrications."
        ),
        parameters={
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "output": {"type": "string"},
            },
            "required": ["source", "output"],
        },
        run=_run,
    )
)
