"""scrape_jd skill — thin orchestrator over the fetch_job_description tool.

Used by the API layer when /analyse is called with `jd_url` instead of
`jd_text`. Not a graph node — runs once before the pipeline starts.
"""
from __future__ import annotations

from app.tools.registry import registry


async def scrape_jd(url: str) -> str:
    res = await registry.dispatch("fetch_job_description", {"url": url})
    if not res.get("ok"):
        raise ValueError(res.get("error", "JD fetch failed"))
    return res["text"]


__all__ = ["scrape_jd"]
