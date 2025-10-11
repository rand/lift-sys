"""Forward mode constrained generation components."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..ir.models import IntermediateRepresentation, TypedHole
from .controller_runtime import ControllerRuntime


@dataclass
class SynthesizerConfig:
    """Configuration for the forward-mode synthesiser runtime."""

    model_endpoint: str
    temperature: float = 0.0
    provider_type: str = "vllm"
    schema_uri: str | None = None
    grammar_source: str | None = None
    controller_path: str | None = None


@dataclass
class Constraint:
    """Representation of a single constraint sent to the runtime."""

    name: str
    value: str
    metadata: dict[str, str] = field(default_factory=dict)


class CodeSynthesizer:
    """High level forward-mode synthesiser built on the controller runtime."""

    def __init__(
        self,
        config: SynthesizerConfig,
        runtime_factory: Callable[[SynthesizerConfig], ControllerRuntime] | None = None,
    ) -> None:
        self.config = config
        factory = runtime_factory or (lambda cfg: ControllerRuntime(cfg))
        self.runtime = factory(config)

    def compile_constraints(self, ir: IntermediateRepresentation) -> list[Constraint]:
        constraints: list[Constraint] = []
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

    def generate(self, ir: IntermediateRepresentation) -> dict[str, object]:
        constraints = self.compile_constraints(ir)
        payload = self.runtime.build_payload(ir, constraints)
        stream = list(self.runtime.stream(payload, constraints))
        payload["stream"] = stream
        payload["telemetry"] = self.runtime.telemetry
        return payload

    def _constraint_for_hole(self, hole: TypedHole) -> Constraint:
        return Constraint(
            name=f"hole::{hole.identifier}",
            value=hole.type_hint,
            metadata={"description": hole.description, "kind": hole.kind.value},
        )


__all__ = ["SynthesizerConfig", "Constraint", "CodeSynthesizer"]
