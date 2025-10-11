"""Reasoning service orchestrating high-level planning."""

from __future__ import annotations

from typing import Any

from .orchestrator import HybridOrchestrator, Task


class ReasoningService:
    """Service facade for planning workflows using the external provider."""

    def __init__(self, orchestrator: HybridOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def plan(
        self, prompt: str, *, temperature: float = 0.7, metadata: dict[str, Any] | None = None
    ) -> str:
        task = Task(
            prompt=prompt,
            temperature=temperature,
            requires_reasoning=True,
            metadata=metadata or {},
        )
        result = await self._orchestrator.execute_task(task)
        return str(result.content)
