"""Verification pipeline service."""
from __future__ import annotations

from typing import Any, Dict

from .orchestrator import HybridOrchestrator, Task


class VerificationService:
    """Coordinates hybrid verification across providers."""

    def __init__(self, orchestrator: HybridOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def verify(self, prompt: str, schema: Dict[str, Any], *, temperature: float = 0.2) -> Dict[str, Any]:
        task = Task(
            prompt=prompt,
            temperature=temperature,
            requires_verification=True,
            verification_schema=schema,
        )
        result = await self._orchestrator.execute_task(task)
        if isinstance(result.content, dict):
            return result.content
        raise TypeError("expected structured verification output")
