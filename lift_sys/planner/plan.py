"""Static representation of verification and synthesis plans."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from ..ir.models import IntermediateRepresentation


@dataclass(slots=True)
class PlanStep:
    identifier: str
    description: str
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class Plan:
    """Immutable workflow representation derived from the IR."""

    steps: List[PlanStep]
    goals: List[str] = field(default_factory=list)

    def adjacency(self) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {step.identifier: [] for step in self.steps}
        for step in self.steps:
            for dependency in step.prerequisites:
                mapping.setdefault(dependency, []).append(step.identifier)
        return mapping

    def next_steps(self, completed: Iterable[str]) -> List[PlanStep]:
        completed_set = set(completed)
        ready: List[PlanStep] = []
        for step in self.steps:
            if step.identifier in completed_set:
                continue
            if set(step.prerequisites).issubset(completed_set):
                ready.append(step)
        return ready


def derive_plan(ir: IntermediateRepresentation) -> Plan:
    steps = [
        PlanStep(identifier="parse_ir", description="Parse IR and normalise metadata"),
        PlanStep(identifier="verify_assertions", description="Verify logical assertions with SMT", prerequisites=["parse_ir"]),
        PlanStep(identifier="synthesise_code", description="Generate constrained code skeleton", prerequisites=["verify_assertions"]),
    ]
    if ir.typed_holes():
        steps.append(
            PlanStep(
                identifier="resolve_holes",
                description="Coordinate hole resolution using planner",
                prerequisites=["parse_ir"],
            )
        )
        steps.append(
            PlanStep(
                identifier="finalise_ir",
                description="Incorporate resolved holes into IR",
                prerequisites=["resolve_holes", "verify_assertions"],
            )
        )
    goals = ["verified_ir", "code_generation"]
    return Plan(steps=steps, goals=goals)


__all__ = ["Plan", "PlanStep", "derive_plan"]
