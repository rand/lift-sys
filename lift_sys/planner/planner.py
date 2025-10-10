"""Conflict driven planner orchestrating reverse and forward workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .plan import Plan, PlanStep, derive_plan


@dataclass
class PlannerState:
    completed: List[str] = field(default_factory=list)
    conflicts: Dict[str, str] = field(default_factory=dict)
    checkpoints: List[str] = field(default_factory=list)


class Planner:
    """Freer arrow inspired planner with conflict learning."""

    def __init__(self) -> None:
        self.state = PlannerState()
        self.current_plan: Optional[Plan] = None

    def load_ir(self, ir) -> Plan:
        self.current_plan = derive_plan(ir)
        self.state = PlannerState()
        return self.current_plan

    def record_checkpoint(self, label: str) -> None:
        self.state.checkpoints.append(label)

    def step(self, result: str, success: bool, reason: str | None = None) -> List[PlanStep]:
        if not self.current_plan:
            raise RuntimeError("Planner has no plan loaded")
        if success:
            self.state.completed.append(result)
        else:
            self.state.conflicts[result] = reason or "unknown"
        return self.current_plan.next_steps(self.state.completed)

    def suggest_resolution(self) -> Dict[str, str]:
        suggestions: Dict[str, str] = {}
        for node, reason in self.state.conflicts.items():
            suggestions[node] = f"Investigate {node}: {reason}"
        return suggestions


__all__ = ["Planner", "PlannerState"]
