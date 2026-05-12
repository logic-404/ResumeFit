"""Custom evaluators for golden-set assertions.

Each returns (ok: bool, message: str). Combine into one report per pair.
"""
from __future__ import annotations


def assert_match_score_in_range(
    score: float, lo: float, hi: float
) -> tuple[bool, str]:
    ok = lo <= score <= hi
    return ok, f"score {score:.2f} {'in' if ok else 'NOT in'} [{lo}, {hi}]"


def assert_skills_present(matched: list[dict], required: list[str]) -> tuple[bool, str]:
    matched_names = {m["skill"].lower() for m in matched if isinstance(m, dict) and m.get("skill")}
    missing = [s for s in required if s.lower() not in matched_names]
    return (not missing), (
        f"all required matched" if not missing else f"missing matched: {missing}"
    )


def assert_no_fabrication(diff_result: dict) -> tuple[bool, str]:
    ok = bool(diff_result.get("ok"))
    if ok:
        return True, "no fabrication"
    return False, (
        f"fabricated: entities={diff_result.get('fabricated_entities')} "
        f"dates={diff_result.get('fabricated_dates')} "
        f"numerics={diff_result.get('fabricated_numerics')}"
    )


def assert_keyword_min(letter: dict, minimum: int) -> tuple[bool, str]:
    n = int(letter.get("keyword_match_count", 0))
    return n >= minimum, f"keyword_match_count={n} (min {minimum})"
