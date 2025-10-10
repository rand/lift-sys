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
    controllers: List[str] = field(default_factory=list)
    obligations: List[str] = field(default_factory=list)


@dataclass(slots=True)
class DecisionLiteral:
    identifier: str
    literal_type: str
    obligation: str
    steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "type": self.literal_type,
            "obligation": self.obligation,
            "steps": list(self.steps),
        }


@dataclass(slots=True)
class Plan:
    """Immutable workflow representation derived from the IR."""

    steps: List[PlanStep]
    goals: List[str] = field(default_factory=list)
    decision_literals: Dict[str, DecisionLiteral] = field(init=False, default_factory=dict)
    _step_index: Dict[str, PlanStep] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._step_index = {step.identifier: step for step in self.steps}
        self.decision_literals = {}
        for step in self.steps:
            step.obligations = []
        for step in self.steps:
            structural_identifier = f"structural:{step.identifier}"
            structural_literal = DecisionLiteral(
                identifier=structural_identifier,
                literal_type="structural",
                obligation=step.identifier,
                steps=[step.identifier],
            )
            self.decision_literals[structural_identifier] = structural_literal
            step.obligations.append(structural_identifier)
            for controller in step.controllers:
                literal_id = f"controller:{controller}"
                literal = self.decision_literals.get(literal_id)
                if not literal:
                    literal = DecisionLiteral(
                        identifier=literal_id,
                        literal_type="controller",
                        obligation=controller,
                        steps=[step.identifier],
                    )
                    self.decision_literals[literal_id] = literal
                else:
                    if step.identifier not in literal.steps:
                        literal.steps.append(step.identifier)
                step.obligations.append(literal_id)
            step.obligations = list(dict.fromkeys(step.obligations))

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

    def step_for(self, identifier: str) -> PlanStep:
        return self._step_index[identifier]

    def literals_for_step(self, identifier: str) -> List[str]:
        return list(self.step_for(identifier).obligations)


def derive_plan(ir: IntermediateRepresentation) -> Plan:
    steps = [
        PlanStep(identifier="parse_ir", description="Parse IR and normalise metadata"),
        PlanStep(
            identifier="verify_assertions",
            description="Verify logical assertions with SMT",
            prerequisites=["parse_ir"],
            controllers=["verifier"],
        ),
        PlanStep(
            identifier="synthesise_code",
            description="Generate constrained code skeleton",
            prerequisites=["verify_assertions"],
            controllers=["synthesiser"],
        ),
    ]
    if ir.typed_holes():
        steps.append(
            PlanStep(
                identifier="resolve_holes",
                description="Coordinate hole resolution using planner",
                prerequisites=["parse_ir"],
                controllers=["planner"],
            )
        )
        steps.append(
            PlanStep(
                identifier="finalise_ir",
                description="Incorporate resolved holes into IR",
                prerequisites=["resolve_holes", "verify_assertions"],
                controllers=["planner", "verifier"],
            )
        )
    goals = ["verified_ir", "code_generation"]
    return Plan(steps=steps, goals=goals)


__all__ = ["DecisionLiteral", "Plan", "PlanStep", "derive_plan"]
