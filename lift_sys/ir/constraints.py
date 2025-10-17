"""
IR Constraints - Explicit requirements for code generation behavior.

Constraints specify requirements at the IR level that guide LLM code generation
and can be validated post-generation. Unlike AST patterns (which are brittle and
structure-specific), constraints are specification-level requirements that work
for any code structure implementing the same semantics.

This is Phase 7's principled approach to preventing bugs before generation,
rather than fixing them with pattern matching after generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(str, Enum):
    """Types of constraints that can be applied to code generation."""

    RETURN = "return_constraint"
    """Ensures computed values are explicitly returned"""

    LOOP_BEHAVIOR = "loop_constraint"
    """Enforces specific loop behaviors (early return, accumulation, etc.)"""

    POSITION = "position_constraint"
    """Specifies position requirements between elements"""


class ConstraintSeverity(str, Enum):
    """Severity level of a constraint violation."""

    ERROR = "error"
    """Constraint violation blocks code generation"""

    WARNING = "warning"
    """Constraint violation logged but allows generation"""


class ReturnRequirement(str, Enum):
    """Requirement for return constraints."""

    MUST_RETURN = "MUST_RETURN"
    """Value must be explicitly returned"""

    OPTIONAL_RETURN = "OPTIONAL_RETURN"
    """Value may optionally be returned"""


class LoopSearchType(str, Enum):
    """Type of search operation in a loop."""

    FIRST_MATCH = "FIRST_MATCH"
    """Find and return first matching element"""

    LAST_MATCH = "LAST_MATCH"
    """Find and return last matching element"""

    ALL_MATCHES = "ALL_MATCHES"
    """Find and return all matching elements"""


class LoopRequirement(str, Enum):
    """Required loop behavior."""

    EARLY_RETURN = "EARLY_RETURN"
    """Loop must return immediately on finding match (not continue)"""

    ACCUMULATE = "ACCUMULATE"
    """Loop must accumulate results and return after completion"""

    TRANSFORM = "TRANSFORM"
    """Loop must transform elements and return collection"""


class PositionRequirement(str, Enum):
    """Required relationship between element positions."""

    NOT_ADJACENT = "NOT_ADJACENT"
    """Elements must NOT be immediately adjacent"""

    ORDERED = "ORDERED"
    """Elements must appear in specified order"""

    MIN_DISTANCE = "MIN_DISTANCE"
    """Elements must be at least N characters apart"""

    MAX_DISTANCE = "MAX_DISTANCE"
    """Elements must be at most N characters apart"""


@dataclass
class Constraint:
    """
    Base constraint type.

    Constraints are explicit requirements on code generation behavior that:
    1. Prevent bugs before generation (not after)
    2. Work for any code structure (not specific AST patterns)
    3. Scale maintainably (one constraint per bug type)
    4. Guide LLM generation with clear requirements
    """

    type: ConstraintType
    """Type of constraint"""

    description: str = ""
    """Human-readable description of what this constraint requires"""

    severity: ConstraintSeverity = ConstraintSeverity.ERROR
    """Severity of constraint violation (error blocks generation, warning logs)"""

    def to_dict(self) -> dict[str, Any]:
        """Serialize constraint to dictionary."""
        return {
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Constraint:
        """Deserialize constraint from dictionary."""
        constraint_type = ConstraintType(data["type"])

        # Route to appropriate subclass based on type
        if constraint_type == ConstraintType.RETURN:
            return ReturnConstraint.from_dict(data)
        elif constraint_type == ConstraintType.LOOP_BEHAVIOR:
            return LoopBehaviorConstraint.from_dict(data)
        elif constraint_type == ConstraintType.POSITION:
            return PositionConstraint.from_dict(data)
        else:
            # Fallback to base class
            return cls(
                type=constraint_type,
                description=data["description"],
                severity=ConstraintSeverity(data.get("severity", ConstraintSeverity.ERROR.value)),
            )


@dataclass
class ReturnConstraint(Constraint):
    """
    Constraint ensuring computed values are explicitly returned.

    Fixes bugs like count_words where LLM forgets to return the computed value.

    Example:
        ReturnConstraint(
            value_name="count",
            requirement=ReturnRequirement.MUST_RETURN,
            description="Function must return the computed count value"
        )

    This ensures the LLM generates: `return count` after computing count.
    """

    type: ConstraintType = field(default=ConstraintType.RETURN, init=False)

    value_name: str = ""
    """Name of the value that must be returned (e.g., 'count', 'result')"""

    requirement: ReturnRequirement = ReturnRequirement.MUST_RETURN
    """Whether return is required or optional"""

    def __post_init__(self):
        """Set default description if not provided."""
        if not self.description:
            self.description = f"Function must return '{self.value_name}' value explicitly"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result = super().to_dict()
        result.update(
            {
                "value_name": self.value_name,
                "requirement": self.requirement.value,
            }
        )
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReturnConstraint:
        """Deserialize from dictionary."""
        return cls(
            value_name=data["value_name"],
            requirement=ReturnRequirement(
                data.get("requirement", ReturnRequirement.MUST_RETURN.value)
            ),
            description=data.get("description", ""),
            severity=ConstraintSeverity(data.get("severity", ConstraintSeverity.ERROR.value)),
        )


@dataclass
class LoopBehaviorConstraint(Constraint):
    """
    Constraint enforcing specific loop behaviors.

    Fixes bugs like find_index where LLM accumulates instead of returning
    immediately on first match.

    Example:
        LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN,
            description="Loop must return immediately on FIRST match (not continue)"
        )

    This ensures the LLM generates early return pattern, not accumulation.
    """

    type: ConstraintType = field(default=ConstraintType.LOOP_BEHAVIOR, init=False)

    search_type: LoopSearchType = LoopSearchType.FIRST_MATCH
    """Type of search operation (first, last, all matches)"""

    requirement: LoopRequirement = LoopRequirement.EARLY_RETURN
    """Required loop behavior (early return, accumulate, transform)"""

    loop_variable: str | None = None
    """Optional: Name of the loop variable for clarity"""

    def __post_init__(self):
        """Set default description if not provided."""
        if not self.description:
            if self.search_type == LoopSearchType.FIRST_MATCH:
                self.description = (
                    "Loop must return immediately on FIRST match (not continue to last)"
                )
            elif self.search_type == LoopSearchType.LAST_MATCH:
                self.description = "Loop must return LAST match (accumulate until end)"
            else:
                self.description = "Loop must return ALL matches"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result = super().to_dict()
        result.update(
            {
                "search_type": self.search_type.value,
                "requirement": self.requirement.value,
            }
        )
        if self.loop_variable:
            result["loop_variable"] = self.loop_variable
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoopBehaviorConstraint:
        """Deserialize from dictionary."""
        return cls(
            search_type=LoopSearchType(data.get("search_type", LoopSearchType.FIRST_MATCH.value)),
            requirement=LoopRequirement(
                data.get("requirement", LoopRequirement.EARLY_RETURN.value)
            ),
            loop_variable=data.get("loop_variable"),
            description=data.get("description", ""),
            severity=ConstraintSeverity(data.get("severity", ConstraintSeverity.ERROR.value)),
        )


@dataclass
class PositionConstraint(Constraint):
    """
    Constraint specifying position requirements between elements.

    Fixes bugs like is_valid_email where LLM forgets to check that dot is not
    immediately adjacent to @ symbol.

    Example:
        PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.NOT_ADJACENT,
            min_distance=1,
            description="Dot must be at least 2 characters after @"
        )

    This ensures the LLM generates: check that @ and . are not adjacent.
    """

    type: ConstraintType = field(default=ConstraintType.POSITION, init=False)

    elements: list[str] = field(default_factory=list)
    """Elements whose positions are constrained (e.g., ["@", "."])"""

    requirement: PositionRequirement = PositionRequirement.NOT_ADJACENT
    """Required relationship between elements"""

    min_distance: int = 0
    """Minimum character distance between elements"""

    max_distance: int | None = None
    """Maximum character distance between elements (None = unlimited)"""

    def __post_init__(self):
        """Set default description if not provided."""
        if not self.description:
            if self.requirement == PositionRequirement.NOT_ADJACENT:
                self.description = f"Elements {self.elements} must NOT be immediately adjacent"
            elif self.requirement == PositionRequirement.ORDERED:
                self.description = f"Elements {self.elements} must appear in this order"
            elif self.requirement == PositionRequirement.MIN_DISTANCE:
                self.description = f"Elements {self.elements} must be at least {self.min_distance} characters apart"
            elif self.requirement == PositionRequirement.MAX_DISTANCE:
                self.description = (
                    f"Elements {self.elements} must be at most {self.max_distance} characters apart"
                )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result = super().to_dict()
        result.update(
            {
                "elements": self.elements,
                "requirement": self.requirement.value,
                "min_distance": self.min_distance,
            }
        )
        if self.max_distance is not None:
            result["max_distance"] = self.max_distance
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PositionConstraint:
        """Deserialize from dictionary."""
        return cls(
            elements=data.get("elements", []),
            requirement=PositionRequirement(
                data.get("requirement", PositionRequirement.NOT_ADJACENT.value)
            ),
            min_distance=data.get("min_distance", 0),
            max_distance=data.get("max_distance"),
            description=data.get("description", ""),
            severity=ConstraintSeverity(data.get("severity", ConstraintSeverity.ERROR.value)),
        )


def parse_constraint(data: dict[str, Any]) -> Constraint:
    """
    Parse a constraint from dictionary data.

    Routes to appropriate subclass based on 'type' field.

    Args:
        data: Dictionary containing constraint data

    Returns:
        Appropriate Constraint subclass instance
    """
    return Constraint.from_dict(data)
