"""Tool registry.

Each tool exposes:
- a `name` (function-call identifier)
- a `description` (LLM-facing)
- a JSON-schema for parameters (`parameters`)
- an async `run(args: dict) -> dict | str` callable

The `as_openai()` helper returns a dict in OpenAI function-calling format
so tools can be bound to a chat model via `llm.bind_tools([...])`. Skills
choose which tools they need; nothing here is auto-loaded.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

ToolFunc = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema
    run: ToolFunc

    def as_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def select(self, names: list[str]) -> list[Tool]:
        return [self.get(n) for n in names]

    def openai_specs(self, names: list[str]) -> list[dict[str, Any]]:
        return [self.get(n).as_openai() for n in names]

    async def dispatch(self, name: str, args: dict[str, Any]) -> Any:
        return await self.get(name).run(args)


registry = ToolRegistry()
