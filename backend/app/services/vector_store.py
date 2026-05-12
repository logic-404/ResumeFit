"""Chroma-backed vector store for resume chunks.

Single collection. Each document is one chunk; metadata carries
{profile_id, source_file, kind} so we can scope queries to the current
profile and clear on re-upload. Embeddings are produced by our own
OpenAI embedder (kept out-of-process) to ensure model consistency
between writes and queries.

Chroma's PythonClient is sync; we wrap calls in `asyncio.to_thread` to
keep the FastAPI event loop unblocked.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_client: chromadb.api.ClientAPI | None = None
_collection = None
_lock = asyncio.Lock()


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        _collection = _get_client().get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


@dataclass
class RetrievedChunk:
    text: str
    source_file: str | None
    kind: str
    score: float


async def add_chunks(
    profile_id: str,
    items: list[tuple[str, list[float], str | None, str]],
) -> None:
    """items = [(text, embedding, source_file, kind), ...]"""
    if not items:
        return
    ids = [str(uuid.uuid4()) for _ in items]
    docs = [t for t, _, _, _ in items]
    embs = [e for _, e, _, _ in items]
    metas = [
        {"profile_id": profile_id, "source_file": s or "", "kind": k}
        for _, _, s, k in items
    ]

    def _add():
        _get_collection().add(ids=ids, documents=docs, embeddings=embs, metadatas=metas)

    async with _lock:
        await asyncio.to_thread(_add)


async def delete_for_profile(profile_id: str) -> None:
    def _del():
        _get_collection().delete(where={"profile_id": profile_id})

    async with _lock:
        await asyncio.to_thread(_del)


async def query(
    profile_id: str, query_embedding: list[float], k: int = 5
) -> list[RetrievedChunk]:
    def _q():
        return _get_collection().query(
            query_embeddings=[query_embedding],
            n_results=max(1, min(k, 20)),
            where={"profile_id": profile_id},
        )

    res = await asyncio.to_thread(_q)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out: list[RetrievedChunk] = []
    for doc, meta, dist in zip(docs, metas, dists, strict=True):
        out.append(
            RetrievedChunk(
                text=doc,
                source_file=meta.get("source_file") or None,
                kind=meta.get("kind") or "paragraph",
                score=1.0 - float(dist),
            )
        )
    return out
