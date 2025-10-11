"""Conflict driven planner orchestrating reverse and forward workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from ..ir.models import IntermediateRepresentation
from .conflict_learning import (
    Clause,
    ClauseStore,
    ImplicationGraph,
    extract_reason_literals,
)
from .plan import Plan, PlanStep, derive_plan


@dataclass(slots=True)
class PlannerEvent:
    """Structured planner telemetry event."""

    type: str
    data: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"type": self.type, "data": self.data}


@dataclass(slots=True)
class PlannerStepResult:
    """Detailed result for a planner transition."""

    next_steps: list[PlanStep]
    learned_clauses: list[Clause]
    backjump_target: int | None
    events: list[dict[str, object]]


@dataclass
class PlannerState:
    completed: list[str] = field(default_factory=list)
    conflicts: dict[str, str] = field(default_factory=dict)
    decision_levels: dict[str, int] = field(default_factory=dict)
    checkpoints: list[str] = field(default_factory=list)


class Planner:
    """Freer arrow inspired planner with conflict learning."""

    def __init__(self) -> None:
        self.state = PlannerState()
        self.current_plan: Plan | None = None
        self.current_ir: IntermediateRepresentation | None = None
        self.clauses = ClauseStore()
        self.graph = ImplicationGraph()
        self._event_queue: list[PlannerEvent] = []
        self._event_history: list[PlannerEvent] = []
        self._current_step_events: list[PlannerEvent] = []

    def load_ir(self, ir) -> Plan:
        self.current_plan = derive_plan(ir)
        self.current_ir = ir
        self.state = PlannerState()
        self.clauses = ClauseStore()
        self.graph.reset()
        self._event_queue.clear()
        self._event_history.clear()
        return self.current_plan

    def _record_event(self, event_type: str, data: dict[str, object]) -> None:
        event = PlannerEvent(type=event_type, data=data)
        self._current_step_events.append(event)

    def _flush_events(self) -> list[dict[str, object]]:
        events = [event.to_dict() for event in self._current_step_events]
        self._event_history.extend(self._current_step_events)
        self._event_queue.extend(self._current_step_events)
        self._current_step_events = []
        return events

    def consume_events(self) -> list[dict[str, object]]:
        events = [event.to_dict() for event in self._event_queue]
        self._event_queue.clear()
        return events

    def recent_events(self, limit: int = 25) -> list[dict[str, object]]:
        return [event.to_dict() for event in self._event_history[-limit:]]

    def _filter_next_steps(self, candidates: Iterable[PlanStep]) -> list[PlanStep]:
        active_literals = self.graph.assigned_literals()
        filtered: list[PlanStep] = []
        for step in candidates:
            literals = (
                self.current_plan.literals_for_step(step.identifier) if self.current_plan else []
            )
            if self.clauses.would_conflict(active_literals, literals):
                continue
            filtered.append(step)
        return filtered

    def record_checkpoint(self, label: str) -> None:
        self.state.checkpoints.append(label)
        self._record_event("checkpoint", {"label": label})
        self._flush_events()

    def step(self, result: str, success: bool, reason: str | None = None) -> PlannerStepResult:
        if not self.current_plan:
            raise RuntimeError("Planner has no plan loaded")
        self._current_step_events = []
        learned_clauses: list[Clause] = []
        backjump_target: int | None = None
        if success:
            self.state.completed.append(result)
            self.state.conflicts.pop(result, None)
            literals = self.current_plan.literals_for_step(result)
            level, _ = self.graph.push_decision(result, literals)
            self.state.decision_levels[result] = level
            literal_payload = [
                self.current_plan.decision_literals[literal].to_dict()
                for literal in literals
                if literal in self.current_plan.decision_literals
            ]
            self._record_event(
                "decision",
                {
                    "step": result,
                    "level": level,
                    "literals": literal_payload,
                },
            )
        else:
            self.state.conflicts[result] = reason or "unknown"
            literals = self.current_plan.literals_for_step(result)
            blocking_literals = extract_reason_literals(reason)
            negative_blockers = [f"!{literal}" for literal in blocking_literals]
            clause_literals = tuple(dict.fromkeys(literals + negative_blockers))
            clause = Clause(literals=clause_literals, explanation=reason or "conflict")
            learned_clauses.append(clause)
            self.clauses.add(clause)
            backjump_target = self.graph.backjump_target(clause)
            removed_steps = self.graph.pop_to_level(backjump_target)
            for removed in removed_steps:
                if removed in self.state.decision_levels:
                    self.state.decision_levels.pop(removed)
                if removed in self.state.completed:
                    self.state.completed.remove(removed)
            self._record_event(
                "learned_clause",
                {
                    "step": result,
                    "clause": clause.to_dict(),
                    "backjump": backjump_target,
                },
            )
            if not blocking_literals:
                self._record_event(
                    "assist_needed",
                    {
                        "step": result,
                        "detail": reason or "Planner requires operator input",
                    },
                )
        next_steps = self._filter_next_steps(self.current_plan.next_steps(self.state.completed))
        self._record_event(
            "next_decisions",
            {
                "candidates": [step.identifier for step in next_steps],
            },
        )
        events = self._flush_events()
        return PlannerStepResult(
            next_steps=next_steps,
            learned_clauses=learned_clauses,
            backjump_target=backjump_target,
            events=events,
        )

    def suggest_resolution(self) -> dict[str, str]:
        suggestions: dict[str, str] = {}
        for node, reason in self.state.conflicts.items():
            suggestions[node] = f"Investigate {node}: {reason}"
        return suggestions


__all__ = [
    "Planner",
    "PlannerEvent",
    "PlannerState",
    "PlannerStepResult",
]
