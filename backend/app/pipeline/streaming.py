"""SSE event registry.

A per-job-id asyncio.Queue that pipeline nodes push events into and the
SSE endpoint drains. No external broker — single-process is enough for
this single-user app. Queues are auto-removed when the consumer detaches.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

SENTINEL = object()


@dataclass
class StreamEvent:
    event: str  # 'step' | 'result' | 'error'
    data: dict[str, Any] = field(default_factory=dict)


class JobStream:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.done = False

    async def push(self, event: StreamEvent) -> None:
        await self.queue.put(event)

    async def end(self) -> None:
        self.done = True
        await self.queue.put(SENTINEL)

    async def consume(self) -> AsyncIterator[StreamEvent]:
        while True:
            item = await self.queue.get()
            if item is SENTINEL:
                return
            yield item


class StreamRegistry:
    def __init__(self) -> None:
        self._streams: dict[str, JobStream] = {}

    def create(self, job_id: str) -> JobStream:
        s = JobStream()
        self._streams[job_id] = s
        return s

    def get(self, job_id: str) -> JobStream | None:
        return self._streams.get(job_id)

    def discard(self, job_id: str) -> None:
        self._streams.pop(job_id, None)


registry = StreamRegistry()
