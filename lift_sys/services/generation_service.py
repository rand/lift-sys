"""Code generation service relying on the local vLLM."""
from __future__ import annotations

from typing import Any, Dict

from .orchestrator import HybridOrchestrator, Task


class GenerationService:
    """Generate constrained outputs using the hybrid orchestrator."""

    def __init__(self, orchestrator: HybridOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def generate_code(self, prompt: str, schema: Dict[str, Any], *, temperature: float = 0.0) -> Dict[str, Any]:
        task = Task(
            prompt=prompt,
            temperature=temperature,
            requires_constrained_output=True,
            output_schema=schema,
        )
        result = await self._orchestrator.execute_task(task)
        if isinstance(result.content, dict):
            return result.content
        raise TypeError("expected structured output from local provider")
