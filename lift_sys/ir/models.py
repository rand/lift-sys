"""Intermediate Representation (IR) data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class HoleKind(str, Enum):
    """Enumeration describing the semantic purpose of a typed hole."""

    INTENT = "intent"
    SIGNATURE = "signature"
    EFFECT = "effect"
    ASSERTION = "assertion"
    IMPLEMENTATION = "implementation"


@dataclass(slots=True)
class TypedHole:
    """Explicit representation of an unknown value in the IR."""

    identifier: str
    type_hint: str
    description: str = ""
    constraints: Dict[str, str] = field(default_factory=dict)
    kind: HoleKind = HoleKind.INTENT

    def label(self) -> str:
        """Return a human friendly label for visualisations."""

        return f"<?{self.identifier}: {self.type_hint}?>"


@dataclass(slots=True)
class IntentClause:
    summary: str
    rationale: Optional[str] = None
    holes: List[TypedHole] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": self.summary,
            "rationale": self.rationale,
            "holes": [hole.__dict__ for hole in self.holes],
        }


@dataclass(slots=True)
class Parameter:
    name: str
    type_hint: str
    description: Optional[str] = None


@dataclass(slots=True)
class SigClause:
    name: str
    parameters: List[Parameter]
    returns: Optional[str]
    holes: List[TypedHole] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "parameters": [param.__dict__ for param in self.parameters],
            "returns": self.returns,
            "holes": [hole.__dict__ for hole in self.holes],
        }


@dataclass(slots=True)
class EffectClause:
    description: str
    holes: List[TypedHole] = field(default_factory=list)


@dataclass(slots=True)
class AssertClause:
    predicate: str
    rationale: Optional[str] = None
    holes: List[TypedHole] = field(default_factory=list)


@dataclass(slots=True)
class Metadata:
    source_path: Optional[str] = None
    language: Optional[str] = None
    origin: Optional[str] = None


@dataclass(slots=True)
class IntermediateRepresentation:
    """The single source of truth for a lifted specification."""

    intent: IntentClause
    signature: SigClause
    effects: List[EffectClause] = field(default_factory=list)
    assertions: List[AssertClause] = field(default_factory=list)
    metadata: Metadata = field(default_factory=Metadata)

    def typed_holes(self) -> List[TypedHole]:
        """Return every typed hole contained within the IR."""

        holes: List[TypedHole] = []
        holes.extend(self.intent.holes)
        holes.extend(self.signature.holes)
        for param in self.signature.parameters:
            if isinstance(param, TypedHole):  # pragma: no cover - defensive
                holes.append(param)
        for effect in self.effects:
            holes.extend(effect.holes)
        for assertion in self.assertions:
            holes.extend(assertion.holes)
        return holes

    def to_dict(self) -> Dict[str, object]:
        """Serialise the IR into a dictionary suitable for APIs."""

        return {
            "intent": {
                "summary": self.intent.summary,
                "rationale": self.intent.rationale,
                "holes": [hole.__dict__ for hole in self.intent.holes],
            },
            "signature": {
                "name": self.signature.name,
                "parameters": [param.__dict__ for param in self.signature.parameters],
                "returns": self.signature.returns,
                "holes": [hole.__dict__ for hole in self.signature.holes],
            },
            "effects": [
                {"description": eff.description, "holes": [hole.__dict__ for hole in eff.holes]}
                for eff in self.effects
            ],
            "assertions": [
                {
                    "predicate": assertion.predicate,
                    "rationale": assertion.rationale,
                    "holes": [hole.__dict__ for hole in assertion.holes],
                }
                for assertion in self.assertions
            ],
            "metadata": self.metadata.__dict__,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "IntermediateRepresentation":
        """Create an IR instance from a dictionary."""

        intent_data = payload["intent"]
        signature_data = payload["signature"]

        def parse_holes(data: List[Dict[str, object]]) -> List[TypedHole]:
            return [TypedHole(**hole) for hole in data]

        intent = IntentClause(
            summary=intent_data["summary"],
            rationale=intent_data.get("rationale"),
            holes=parse_holes(intent_data.get("holes", [])),
        )

        signature = SigClause(
            name=signature_data["name"],
            parameters=[Parameter(**param) for param in signature_data.get("parameters", [])],
            returns=signature_data.get("returns"),
            holes=parse_holes(signature_data.get("holes", [])),
        )

        effects = [
            EffectClause(description=effect["description"], holes=parse_holes(effect.get("holes", [])))
            for effect in payload.get("effects", [])
        ]

        assertions = [
            AssertClause(
                predicate=assertion["predicate"],
                rationale=assertion.get("rationale"),
                holes=parse_holes(assertion.get("holes", [])),
            )
            for assertion in payload.get("assertions", [])
        ]

        metadata = Metadata(**payload.get("metadata", {}))

        return cls(intent=intent, signature=signature, effects=effects, assertions=assertions, metadata=metadata)


__all__ = [
    "HoleKind",
    "TypedHole",
    "IntentClause",
    "Parameter",
    "SigClause",
    "EffectClause",
    "AssertClause",
    "Metadata",
    "IntermediateRepresentation",
]
