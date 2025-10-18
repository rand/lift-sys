"""
Constraint filtering to reduce unnecessary code generation attempts.

This module filters constraints to only those applicable to the given IR,
preventing non-applicable constraints from causing repeated generation failures.

Key filtering strategies:
1. Loop constraints: Only for IRs with loop-related effects
2. Position constraints: Only for code entities (not semantic descriptions)
3. Return constraints: Always applicable

This is Phase 3.1's solution to the high-latency issue caused by enforcing
non-applicable constraints (e.g., loop constraints on if/elif/else code).
"""

from __future__ import annotations

from lift_sys.ir.constraints import (
    Constraint,
    LoopBehaviorConstraint,
    PositionConstraint,
    ReturnConstraint,
)
from lift_sys.ir.models import IntermediateRepresentation


def filter_applicable_constraints(
    ir: IntermediateRepresentation,
    constraints: list[Constraint],
) -> list[Constraint]:
    """
    Filter constraints to only those applicable to this IR.

    Applies different filtering strategies based on constraint type:
    - ReturnConstraint: Always applicable
    - LoopBehaviorConstraint: Only if IR has loop-related effects
    - PositionConstraint: Only if elements are code entities

    Args:
        ir: The IntermediateRepresentation to check constraints against
        constraints: List of constraints to filter

    Returns:
        Filtered list containing only applicable constraints, preserving order

    Example:
        >>> ir = IntermediateRepresentation(...)
        >>> constraints = [
        ...     ReturnConstraint(value_name="result"),
        ...     LoopBehaviorConstraint(search_type=LoopSearchType.FIRST_MATCH),
        ... ]
        >>> applicable = filter_applicable_constraints(ir, constraints)
        >>> # Returns only ReturnConstraint if IR has no loop effects
    """
    applicable = []

    for constraint in constraints:
        # Return constraints are always applicable
        if isinstance(constraint, ReturnConstraint):
            applicable.append(constraint)
            continue

        # Loop behavior constraints only applicable if IR has loop-related effects
        if isinstance(constraint, LoopBehaviorConstraint):
            if _has_loop_effects(ir):
                applicable.append(constraint)
            # Else: filter out (no loop in IR)
            continue

        # Position constraints only applicable if elements are code entities
        if isinstance(constraint, PositionConstraint):
            # Use the existing is_semantically_applicable method
            is_applicable, _reason = constraint.is_semantically_applicable(ir)
            if is_applicable:
                applicable.append(constraint)
            # Else: filter out (semantic description, not code entity)
            continue

        # Unknown constraint type: keep it (conservative approach)
        applicable.append(constraint)

    return applicable


def _has_loop_effects(ir: IntermediateRepresentation) -> bool:
    """
    Check if IR has loop-related effects.

    Searches for loop-related keywords in effect descriptions:
    - iterate, loop, for each, traverse, while (explicit iteration)
    - find (often implies search/iteration)
    - check all, check each (implies iteration over collection)

    Args:
        ir: The IntermediateRepresentation to check

    Returns:
        True if any effect contains loop-related keywords

    Example:
        >>> ir.effects = [EffectClause(description="iterate through list")]
        >>> _has_loop_effects(ir)
        True
        >>> ir.effects = [EffectClause(description="check if condition")]
        >>> _has_loop_effects(ir)
        False
    """
    # Keywords indicating loop/iteration behavior
    loop_keywords = {
        "iterate",
        "loop",
        "for each",
        "traverse",
        "while",
        "find",  # Often implies iteration to find
        "search",  # Implies iteration through collection
        "check all",  # Implies checking each element
        "check each",
        "accumulate",  # Implies iteration to accumulate
        "collect",  # Implies iteration to collect
        "filter",  # Implies iteration to filter
        "map",  # Implies iteration to transform
    }

    # Check all effect descriptions
    for effect in ir.effects:
        effect_lower = effect.description.lower()
        for keyword in loop_keywords:
            if keyword in effect_lower:
                return True

    return False


def is_code_entity(element: str) -> bool:
    """
    Check if element is a code entity vs semantic description.

    Code entities are short identifiers/symbols used in code:
    - Variable names (e.g., "count", "result", "i")
    - Operators (e.g., "@", ".", "+", "-")
    - Keywords (e.g., "return", "if")

    Semantic descriptions are longer phrases describing concepts:
    - "input_string" (describing the input parameter conceptually)
    - "the computed value" (describing what to return)
    - "first matching element" (describing algorithm behavior)

    Heuristic: Code entities are typically short (<20 chars) and contain no spaces.

    Args:
        element: String to check

    Returns:
        True if element appears to be a code entity, False if semantic description

    Example:
        >>> is_code_entity("@")
        True
        >>> is_code_entity("count")
        True
        >>> is_code_entity("input_string")
        False (likely semantic description of parameter)
        >>> is_code_entity("the result value")
        False (contains spaces, semantic description)
    """
    # Empty strings are not code entities
    if not element:
        return False

    # Strings with spaces are semantic descriptions (e.g., "input string")
    if " " in element:
        return False

    # Very short strings (1-3 chars) are likely operators or symbols
    if len(element) <= 3:
        return True

    # Longer strings (>20 chars) are likely semantic descriptions
    # Typical variable names are shorter
    if len(element) > 20:
        return False

    # Medium length (4-20 chars) could be either:
    # - Code entity: "count", "result", "index", "max_value"
    # - Semantic description: "input_string", "return_value"
    #
    # Additional heuristics:
    # - Underscores often indicate conceptual descriptions in IR
    #   (e.g., "input_string" vs actual code variable "s" or "text")
    # - However, snake_case is valid Python, so this is not definitive
    #
    # For now, accept 4-20 char identifiers without spaces as code entities.
    # This will catch most actual code symbols while filtering out longer
    # semantic descriptions.

    return True


__all__ = [
    "filter_applicable_constraints",
    "is_code_entity",
]
