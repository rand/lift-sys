"""Conflict learning primitives for the planner."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass(slots=True)
class Clause:
    """A learned clause over decision literals."""

    literals: Tuple[str, ...]
    explanation: str = ""

    def to_dict(self) -> dict:
        return {"literals": list(self.literals), "explanation": self.explanation}


@dataclass(slots=True)
class ClauseStore:
    """Container storing learned clauses and performing compatibility checks."""

    learned: List[Clause] = field(default_factory=list)

    def add(self, clause: Clause) -> None:
        self.learned.append(clause)

    def would_conflict(self, active_literals: Set[str], candidate_literals: Iterable[str]) -> bool:
        """Check if a clause blocks the activation of the candidate literals."""

        combined = set(active_literals)
        combined.update(candidate_literals)
        for clause in self.learned:
            if set(clause.literals).issubset(combined):
                return True
        return False

    def as_dict(self) -> List[dict]:
        return [clause.to_dict() for clause in self.learned]


@dataclass(slots=True)
class DecisionNode:
    """A vertex in the implication graph."""

    literal: str
    step: str
    level: int
    antecedent: Optional[Clause] = None


class ImplicationGraph:
    """Tracks planner decisions to support backjumping."""

    def __init__(self) -> None:
        self.current_level: int = -1
        self.nodes: List[DecisionNode] = []
        self._literal_index: Dict[str, DecisionNode] = {}

    def reset(self) -> None:
        self.current_level = -1
        self.nodes.clear()
        self._literal_index.clear()

    def push_decision(self, step: str, literals: Sequence[str]) -> Tuple[int, List[DecisionNode]]:
        """Record a new decision level for the provided literals."""

        self.current_level += 1
        assigned: List[DecisionNode] = []
        for literal in literals:
            node = DecisionNode(literal=literal, step=step, level=self.current_level)
            self.nodes.append(node)
            self._literal_index[literal] = node
            assigned.append(node)
        return self.current_level, assigned

    def assigned_literals(self) -> Set[str]:
        return set(self._literal_index.keys())

    def level_of(self, literal: str) -> Optional[int]:
        node = self._literal_index.get(literal)
        return node.level if node else None

    def backjump_target(self, clause: Clause) -> int:
        levels = [self.level_of(literal) for literal in clause.literals if self.level_of(literal) is not None]
        if not levels:
            return 0
        highest = max(levels)
        target = highest - 1
        return target if target >= 0 else 0

    def pop_to_level(self, level: int) -> List[str]:
        """Remove nodes above the specified level and return affected steps."""

        removed_steps: List[str] = []
        while self.nodes and self.nodes[-1].level > level:
            node = self.nodes.pop()
            self._literal_index.pop(node.literal, None)
            if node.step not in removed_steps:
                removed_steps.append(node.step)
        self.current_level = level
        return removed_steps


def extract_reason_literals(reason: Optional[str]) -> List[str]:
    """Parse conflict literals encoded in a reason string."""

    if not reason:
        return []
    marker = "blocked_by:"
    if marker not in reason:
        return []
    payload = reason.split(marker, 1)[1]
    candidates = [part.strip() for part in payload.split(",") if part.strip()]
    return candidates


__all__ = [
    "Clause",
    "ClauseStore",
    "DecisionNode",
    "ImplicationGraph",
    "extract_reason_literals",
]

