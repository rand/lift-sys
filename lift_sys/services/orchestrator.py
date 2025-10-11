"""Hybrid orchestration between external and local providers."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..providers import BaseProvider, LocalVLLMProvider

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class Task:
    """Represents a generation task with routing metadata."""

    prompt: str
    temperature: float = 0.7
    requires_constrained_output: bool = False
    requires_reasoning: bool = False
    requires_verification: bool = False
    output_schema: dict | None = None
    verification_schema: dict | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskResult:
    """Result metadata for a hybrid execution."""

    provider: str
    content: Any
    intermediate: Any | None = None


class HybridOrchestrator:
    """Route tasks between external providers and the local vLLM."""

    def __init__(
        self,
        external_provider: BaseProvider,
        local_provider: LocalVLLMProvider,
        *,
        fallback_to_local: bool = True,
    ) -> None:
        self.external = external_provider
        self.local = local_provider
        self.fallback_to_local = fallback_to_local

    async def execute_task(self, task: Task) -> TaskResult:
        """Dispatch the task to the appropriate provider."""

        try:
            provider, content = await self._execute_primary(task)
            return TaskResult(provider=provider.provider_type, content=content)
        except Exception as exc:  # pragma: no cover - defensive fallback path
            LOGGER.exception("primary provider failed: %s", exc)
            if not self.fallback_to_local:
                raise
            content = await self.local.generate_text(task.prompt, temperature=task.temperature)
            return TaskResult(provider=self.local.provider_type, content=content)

    async def _execute_primary(self, task: Task) -> tuple[BaseProvider, Any]:
        if task.requires_constrained_output:
            if not task.output_schema:
                raise ValueError("structured tasks require an output schema")
            content = await self.local.generate_structured(task.prompt, task.output_schema)
            return self.local, content
        if task.requires_reasoning and self.external.capabilities.reasoning:
            content = await self.external.generate_text(task.prompt, temperature=task.temperature)
            return self.external, content
        if task.requires_verification and task.verification_schema is not None:
            reasoning = await self.external.generate_text(task.prompt, temperature=task.temperature)
            verification_prompt = f"Formalize: {reasoning}"
            content = await self.local.generate_structured(
                verification_prompt, task.verification_schema
            )
            return self.local, content
        if task.output_schema and self.local.supports_structured_output:
            content = await self.local.generate_structured(task.prompt, task.output_schema)
            return self.local, content
        content = await self.external.generate_text(task.prompt, temperature=task.temperature)
        return self.external, content
