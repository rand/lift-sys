"""
Constraint Detector - Automatically detects when to apply IR constraints.

The detector analyzes IR specifications (intent, effects, assertions) and identifies
patterns that indicate specific constraints should be applied to prevent common bugs.

Phase 7: This enables proactive bug prevention by adding constraints BEFORE generation.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from lift_sys.ir.constraints import (
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
    ReturnRequirement,
)

if TYPE_CHECKING:
    from lift_sys.ir.constraints import Constraint
    from lift_sys.ir.models import IntermediateRepresentation


class ConstraintDetector:
    """
    Detects constraint requirements from IR specifications.

    Analyzes intent, effects, and assertions to identify patterns that indicate
    specific constraints should be applied for correct code generation.
    """

    # Patterns for detecting return constraints
    RETURN_KEYWORDS = [
        "return",
        "returns",
        "compute",
        "computes",
        "calculate",
        "calculates",
        "count",
        "counts",
        "sum",
        "sums",
        "result",
        "output",
    ]

    # Patterns for detecting loop behavior constraints
    FIRST_MATCH_KEYWORDS = [
        "first",
        "earliest",
        "initial",
        "find first",
        "locate first",
        "search for first",
    ]

    LAST_MATCH_KEYWORDS = [
        "last",
        "final",
        "find last",
        "locate last",
        "search for last",
    ]

    ALL_MATCHES_KEYWORDS = [
        "all",
        "every",
        "each",
        "collect all",
        "find all",
        "gather all",
    ]

    LOOP_KEYWORDS = [
        "loop",
        "iterate",
        "iteration",
        "for each",
        "traverse",
        "walk through",
    ]

    # Patterns for detecting position constraints
    POSITION_KEYWORDS = [
        "adjacent",
        "next to",
        "immediately after",
        "immediately before",
        "distance",
        "position",
        "placement",
        "between",
        "not adjacent",
        "separated",
    ]

    def detect_constraints(self, ir: IntermediateRepresentation) -> list[Constraint]:
        """
        Analyze IR and detect all applicable constraints.

        Args:
            ir: The intermediate representation to analyze

        Returns:
            List of constraints that should be applied to this IR
        """
        constraints: list[Constraint] = []

        # Detect return constraints
        return_constraint = self._detect_return_constraint(ir)
        if return_constraint:
            constraints.append(return_constraint)

        # Detect loop behavior constraints
        loop_constraint = self._detect_loop_behavior_constraint(ir)
        if loop_constraint:
            constraints.append(loop_constraint)

        # Detect position constraints
        position_constraints = self._detect_position_constraints(ir)
        constraints.extend(position_constraints)

        return constraints

    def _detect_return_constraint(self, ir: IntermediateRepresentation) -> ReturnConstraint | None:
        """
        Detect if a return constraint is needed.

        Looks for:
        1. Function has non-None return type
        2. Intent/effects mention computing/calculating a value
        3. No explicit "return" mentioned in effects

        Returns None if constraint not needed.
        """
        # Check if function returns a value
        if not ir.signature.returns or ir.signature.returns == "None":
            return None

        # Combine text from intent and effects
        intent_text = f"{ir.intent.summary} {ir.intent.rationale or ''}".lower()
        effects_text = " ".join(effect.description.lower() for effect in ir.effects)
        combined_text = f"{intent_text} {effects_text}"

        # Check if any return keywords are mentioned
        has_return_keyword = any(keyword in combined_text for keyword in self.RETURN_KEYWORDS)

        if not has_return_keyword:
            return None

        # Check if return is already explicitly mentioned in effects
        has_explicit_return = "return" in effects_text

        if has_explicit_return:
            # Return is already mentioned, less likely to be forgotten
            return None

        # Extract likely variable name from intent
        value_name = self._extract_value_name(intent_text, effects_text)

        # Create return constraint
        return ReturnConstraint(
            value_name=value_name,
            requirement=ReturnRequirement.MUST_RETURN,
            description=f"Function must return the computed '{value_name}' value explicitly",
        )

    def _detect_loop_behavior_constraint(
        self, ir: IntermediateRepresentation
    ) -> LoopBehaviorConstraint | None:
        """
        Detect if a loop behavior constraint is needed.

        Looks for:
        1. Intent/effects mention iteration/looping
        2. Specific search pattern (first, last, all)
        3. Return behavior implications

        Returns None if constraint not needed.
        """
        # Combine text from intent and effects
        intent_text = f"{ir.intent.summary} {ir.intent.rationale or ''}".lower()
        effects_text = " ".join(effect.description.lower() for effect in ir.effects)
        combined_text = f"{intent_text} {effects_text}"

        # Check if looping is mentioned
        has_loop = any(keyword in combined_text for keyword in self.LOOP_KEYWORDS)

        if not has_loop:
            return None

        # Determine search type based on keywords
        search_type = None
        requirement = None

        # Check for FIRST match pattern
        if any(keyword in combined_text for keyword in self.FIRST_MATCH_KEYWORDS):
            search_type = LoopSearchType.FIRST_MATCH
            requirement = LoopRequirement.EARLY_RETURN

        # Check for LAST match pattern
        elif any(keyword in combined_text for keyword in self.LAST_MATCH_KEYWORDS):
            search_type = LoopSearchType.LAST_MATCH
            requirement = LoopRequirement.ACCUMULATE

        # Check for ALL matches pattern
        elif any(keyword in combined_text for keyword in self.ALL_MATCHES_KEYWORDS):
            search_type = LoopSearchType.ALL_MATCHES
            requirement = LoopRequirement.ACCUMULATE

        if not search_type:
            # Generic loop, no specific constraint
            return None

        # Extract loop variable if mentioned
        loop_variable = self._extract_loop_variable(effects_text)

        return LoopBehaviorConstraint(
            search_type=search_type,
            requirement=requirement,
            loop_variable=loop_variable,
        )

    def _detect_position_constraints(
        self, ir: IntermediateRepresentation
    ) -> list[PositionConstraint]:
        """
        Detect position constraints from assertions and effects.

        Looks for:
        1. Mentions of adjacency, distance, position
        2. Specific character/element pairs (e.g., '@' and '.')
        3. Requirements about element relationships

        Returns empty list if no position constraints needed.
        """
        constraints: list[PositionConstraint] = []

        # Combine text from intent, effects, and assertions
        intent_text = f"{ir.intent.summary} {ir.intent.rationale or ''}".lower()
        effects_text = " ".join(effect.description.lower() for effect in ir.effects)
        assertions_text = " ".join(
            f"{assertion.predicate} {assertion.rationale or ''}".lower()
            for assertion in ir.assertions
        )
        combined_text = f"{intent_text} {effects_text} {assertions_text}"

        # Check if position-related keywords are present
        has_position = any(keyword in combined_text for keyword in self.POSITION_KEYWORDS)

        if not has_position:
            return constraints

        # Detect specific patterns

        # Pattern 1: Email validation (@ and . not adjacent)
        if self._is_email_validation(combined_text):
            constraints.append(
                PositionConstraint(
                    elements=["@", "."],
                    requirement=PositionRequirement.NOT_ADJACENT,
                    min_distance=1,
                    description="@ and . must not be immediately adjacent (e.g., reject 'test@.com')",
                )
            )

        # Pattern 2: Parentheses matching (ordered)
        if self._is_parentheses_matching(combined_text):
            constraints.append(
                PositionConstraint(
                    elements=["(", ")"],
                    requirement=PositionRequirement.ORDERED,
                    description="Opening parenthesis must appear before closing parenthesis",
                )
            )

        # Pattern 3: Generic adjacency detection
        # Look for "X not adjacent to Y" or "X separated from Y"
        adjacency_pairs = self._extract_adjacency_pairs(combined_text)
        for element1, element2 in adjacency_pairs:
            constraints.append(
                PositionConstraint(
                    elements=[element1, element2],
                    requirement=PositionRequirement.NOT_ADJACENT,
                    min_distance=1,
                    description=f"'{element1}' and '{element2}' must not be immediately adjacent",
                )
            )

        return constraints

    # Helper methods

    def _extract_value_name(self, intent_text: str, effects_text: str) -> str:
        """
        Extract likely variable name for return value.

        Heuristics:
        - Look for "count", "sum", "result", "index", etc. in text
        - Default to "result" if nothing specific found
        """
        # Common value names in order of preference
        value_names = [
            "count",
            "index",
            "sum",
            "total",
            "result",
            "value",
            "output",
            "answer",
        ]

        combined = f"{intent_text} {effects_text}"

        for name in value_names:
            if name in combined:
                return name

        return "result"

    def _extract_loop_variable(self, effects_text: str) -> str | None:
        """
        Extract loop variable name from effects text.

        Looks for patterns like:
        - "for each item"
        - "iterate over elements"
        - "loop through values"
        """
        # Pattern: "for each X", "iterate over X", "loop through X"
        patterns = [
            r"for each (\w+)",
            r"iterate over (\w+)",
            r"loop through (\w+)",
            r"for every (\w+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, effects_text)
            if match:
                return match.group(1)

        return None

    def _is_email_validation(self, text: str) -> bool:
        """Check if text describes email validation."""
        email_keywords = ["email", "e-mail", "@"]
        return any(keyword in text for keyword in email_keywords)

    def _is_parentheses_matching(self, text: str) -> bool:
        """Check if text describes parentheses matching."""
        paren_keywords = ["parenthes", "bracket", "brace", "balanced"]
        return any(keyword in text for keyword in paren_keywords)

    def _extract_adjacency_pairs(self, text: str) -> list[tuple[str, str]]:
        """
        Extract pairs of elements that should not be adjacent.

        Looks for patterns like:
        - "X not adjacent to Y"
        - "X separated from Y"
        - "X should not be next to Y"

        Returns list of (element1, element2) tuples.
        """
        pairs: list[tuple[str, str]] = []

        # Pattern: "X not adjacent to Y"
        # This is a simplified version - could be expanded with more sophisticated NLP
        pattern = r"['\"](\S+)['\"].*not adjacent.*['\"](\S+)['\"]"
        matches = re.findall(pattern, text)
        pairs.extend(matches)

        return pairs


def detect_and_apply_constraints(ir: IntermediateRepresentation) -> IntermediateRepresentation:
    """
    Convenience function to detect and apply constraints to an IR.

    This modifies the IR in-place by adding detected constraints.

    Args:
        ir: The IR to analyze and modify

    Returns:
        The same IR object with constraints added (for chaining)
    """
    detector = ConstraintDetector()
    detected_constraints = detector.detect_constraints(ir)

    # Add detected constraints to IR (avoiding duplicates)
    existing_types = {type(c) for c in ir.constraints}

    for constraint in detected_constraints:
        # Only add if this constraint type doesn't already exist
        if type(constraint) not in existing_types:
            ir.constraints.append(constraint)

    return ir


__all__ = [
    "ConstraintDetector",
    "detect_and_apply_constraints",
]
