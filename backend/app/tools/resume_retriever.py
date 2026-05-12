"""resume_retriever: semantic search over the user's resume chunks.

Backed by Chroma. Embeds the query, runs cosine search scoped to the
current profile_id, returns top-k chunks with metadata. Skills call this
to ground their reasoning in the actual resume content.
"""
from __future__ import annotations

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Profile
from app.services.embeddings import embed_batch
from app.services.vector_store import query as vs_query
from app.tools.registry import Tool, registry


async def _run(args: dict) -> dict:
    q: str = args["query"]
    k: int = int(args.get("k", 5))

    async with SessionLocal() as session:
        profile = (await session.execute(select(Profile))).scalars().first()
        if profile is None:
            return {"ok": False, "error": "No profile uploaded", "results": []}
        pid = str(profile.id)

    [vec] = await embed_batch([q])
    chunks = await vs_query(pid, vec, k=k)

    return {
        "ok": True,
        "results": [
            {
                "text": c.text,
                "source_file": c.source_file,
                "kind": c.kind,
                "score": c.score,
            }
            for c in chunks
        ],
    }


resume_retriever_tool = registry.register(
    Tool(
        name="resume_retriever",
        description=(
            "Retrieve the top-k most semantically similar resume bullets/snippets "
            "for a query. Use to find concrete evidence in the candidate's resume."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Skill, requirement, or topic to match"},
                "k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
        },
        run=_run,
    )
)
