"""Forward mode constrained generation components."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from ..ir.models import IntermediateRepresentation, TypedHole


@dataclass
class SynthesizerConfig:
    model_endpoint: str
    temperature: float = 0.0


@dataclass
class Constraint:
    name: str
    value: str
    metadata: Dict[str, str]


class Controller:
    def __init__(self, config: SynthesizerConfig) -> None:
        self.config = config

    def build_prompt(self, ir: IntermediateRepresentation, constraints: Iterable[Constraint]) -> Dict[str, object]:
        return {
            "endpoint": self.config.model_endpoint,
            "temperature": self.config.temperature,
            "prompt": {
                "intent": ir.intent.summary,
                "signature": ir.signature.to_dict() if hasattr(ir.signature, "to_dict") else ir.signature.name,
                "constraints": [constraint.__dict__ for constraint in constraints],
            },
        }


class CodeSynthesizer:
    def __init__(self, config: SynthesizerConfig) -> None:
        self.controller = Controller(config)

    def compile_constraints(self, ir: IntermediateRepresentation) -> List[Constraint]:
        constraints: List[Constraint] = []
        for assertion in ir.assertions:
            constraints.append(
                Constraint(
                    name="assertion",
                    value=assertion.predicate,
                    metadata={"rationale": assertion.rationale or ""},
                )
            )
        for hole in ir.typed_holes():
            constraints.append(self._constraint_for_hole(hole))
        return constraints

    def generate(self, ir: IntermediateRepresentation) -> Dict[str, object]:
        constraints = self.compile_constraints(ir)
        request = self.controller.build_prompt(ir, constraints)
        # A real implementation would stream from vLLM; we return the payload for testing.
        return request

    def _constraint_for_hole(self, hole: TypedHole) -> Constraint:
        return Constraint(
            name=f"hole::{hole.identifier}",
            value=hole.type_hint,
            metadata={"description": hole.description, "kind": hole.kind.value},
        )


__all__ = ["SynthesizerConfig", "Constraint", "Controller", "CodeSynthesizer"]
