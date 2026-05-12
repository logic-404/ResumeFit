"""web_search: minimal Brave Search wrapper, gated by feature flag.

Used by the cover-letter skill to fetch one or two facts about the target
company so the opener isn't generic. Returns top results as
{title, url, snippet}. No-ops when ENABLE_WEB_SEARCH is false or the API
key is missing.
"""
from __future__ import annotations

import httpx

from app.config import settings
from app.tools.registry import Tool, registry

ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


async def _run(args: dict) -> dict:
    if not settings.enable_web_search or not settings.brave_search_api_key:
        return {"ok": False, "error": "web search disabled", "results": []}

    query: str = args["query"]
    count: int = max(1, min(int(args.get("count", 3)), 5))

    headers = {
        "X-Subscription-Token": settings.brave_search_api_key,
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                ENDPOINT,
                headers=headers,
                params={"q": query, "count": count, "result_filter": "web"},
            )
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "error": str(e), "results": []}

    web = (data.get("web") or {}).get("results") or []
    return {
        "ok": True,
        "results": [
            {"title": w.get("title"), "url": w.get("url"), "snippet": w.get("description")}
            for w in web[:count]
        ],
    }


web_search_tool = registry.register(
    Tool(
        name="web_search",
        description="Web search for company facts. Returns top web results with snippets.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
            },
            "required": ["query"],
        },
        run=_run,
    )
)
