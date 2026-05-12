"""Skill abstraction.

A Skill bundles: prompt, output schema, allowed tools, model tier. Pipeline
nodes are thin wrappers that pick a skill and invoke it. Skills are
self-contained and unit-testable in isolation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.config import settings

ModelTier = Literal["extraction", "generation"]


def _make_llm(tier: ModelTier, temperature: float) -> BaseChatModel:
    model = settings.extraction_model if tier == "extraction" else settings.generation_model
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=settings.openai_api_key,
    )


@dataclass
class SkillContext:
    """Per-invocation context passed to a skill."""

    inputs: dict[str, Any]
    profile_id: str | None = None
    job_id: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class Skill(ABC):
    """Base class for all pipeline skills."""

    name: str
    model_tier: ModelTier = "generation"
    temperature: float = 0.0
    output_schema: type[BaseModel]
    prompt: ChatPromptTemplate
    tools: list = field(default_factory=list)  # type: ignore[assignment]

    def llm(self) -> BaseChatModel:
        return _make_llm(self.model_tier, self.temperature)

    @abstractmethod
    async def run(self, ctx: SkillContext) -> BaseModel:
        """Execute the skill. Implementations should return an instance of `output_schema`."""
        raise NotImplementedError

    async def run_structured(self, ctx: SkillContext) -> BaseModel:
        """Default implementation: prompt | llm.with_structured_output(schema)."""
        chain = self.prompt | self.llm().with_structured_output(self.output_schema)
        result = await chain.ainvoke(ctx.inputs)
        return result  # type: ignore[return-value]
