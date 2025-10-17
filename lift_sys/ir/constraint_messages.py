"""
User-friendly constraint violation messages.

Provides enhanced error messages with:
1. Clear explanation of the violation
2. Why it matters (impact on correctness)
3. Actionable suggestions for fixing

This module transforms technical constraint violations into user-friendly feedback
that helps LLMs generate correct code on retry.
"""

from __future__ import annotations

from lift_sys.ir.constraint_validator import ConstraintViolation
from lift_sys.ir.constraints import (
    Constraint,
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
)


def format_violation_for_user(
    violation: ConstraintViolation, constraint: Constraint | None = None
) -> str:
    """
    Format a constraint violation with enhanced user-friendly message.

    Args:
        violation: The constraint violation to format
        constraint: Optional constraint object for additional context

    Returns:
        Enhanced, actionable error message
    """
    # Determine constraint type and delegate to specialized formatter
    constraint_type = violation.constraint_type

    if constraint_type == "return_constraint":
        return _format_return_violation(violation, constraint)
    elif constraint_type == "loop_constraint":
        return _format_loop_violation(violation, constraint)
    elif constraint_type == "position_constraint":
        return _format_position_violation(violation, constraint)
    elif constraint_type == "syntax_error":
        return _format_syntax_error(violation)
    elif constraint_type == "missing_function":
        return _format_missing_function(violation)
    else:
        # Fallback for unknown constraint types
        return f"Constraint violation: {violation.description}"


def _format_return_violation(violation: ConstraintViolation, constraint: Constraint | None) -> str:
    """Format ReturnConstraint violations with actionable suggestions."""
    if not isinstance(constraint, ReturnConstraint):
        # Fallback if constraint not provided
        return f"Missing return statement: {violation.description}"

    value_name = constraint.value_name

    if "No return statement" in violation.description:
        return f"""ReturnConstraint violation: Missing return statement

What's wrong:
  Function does not have a return statement, but it computes '{value_name}'

Why it matters:
  Without an explicit return, the function will return None instead of the
  computed value. This causes tests to fail and violates the function's contract.

How to fix:
  Add 'return {value_name}' after computing the value

Example:
  # Current (wrong):
  def compute_result(data):
      {value_name} = process(data)
      # Missing return!

  # Fixed (correct):
  def compute_result(data):
      {value_name} = process(data)
      return {value_name}
"""

    elif "return None" in violation.description or "returns None" in violation.description.lower():
        return f"""ReturnConstraint violation: Returns None instead of computed value

What's wrong:
  All return statements return None, but function should return '{value_name}'

Why it matters:
  Explicitly returning None discards the computed result, causing tests to
  fail. The caller expects the computed value, not None.

How to fix:
  Return the computed '{value_name}' value instead of None

Example:
  # Current (wrong):
  def compute_result(data):
      {value_name} = process(data)
      return None  # Wrong!

  # Fixed (correct):
  def compute_result(data):
      {value_name} = process(data)
      return {value_name}
"""

    else:
        # Generic return constraint violation
        return f"""ReturnConstraint violation: {violation.description}

How to fix:
  Ensure the function explicitly returns the computed '{value_name}' value
  Example: return {value_name}
"""


def _format_loop_violation(violation: ConstraintViolation, constraint: Constraint | None) -> str:
    """Format LoopBehaviorConstraint violations with clear examples."""
    if not isinstance(constraint, LoopBehaviorConstraint):
        return f"Loop behavior violation: {violation.description}"

    search_type = constraint.search_type
    requirement = constraint.requirement

    if search_type == LoopSearchType.FIRST_MATCH and requirement == LoopRequirement.EARLY_RETURN:
        if (
            "no return" in violation.description.lower()
            or "early return" in violation.description.lower()
        ):
            return """LoopBehaviorConstraint violation: Missing early return for FIRST match

What's wrong:
  Loop searches for FIRST match but doesn't return immediately when found.
  Instead, it continues iterating or accumulates results.

Why it matters:
  Without early return, the loop continues to the LAST match, not the first.
  This produces incorrect results (e.g., find_index returns wrong index).

How to fix:
  Add 'return' statement inside loop when match is found

Example:
  # Current (wrong - finds LAST match):
  def find_first(items, target):
      result = -1
      for i, item in enumerate(items):
          if item == target:
              result = i  # Accumulates to last match!
      return result

  # Fixed (correct - finds FIRST match):
  def find_first(items, target):
      for i, item in enumerate(items):
          if item == target:
              return i  # Early return on first match!
      return -1  # Default if not found
"""
        else:
            return f"LoopBehaviorConstraint violation: {violation.description}\nExpected early return pattern for FIRST_MATCH"

    elif search_type in [LoopSearchType.ALL_MATCHES, LoopSearchType.LAST_MATCH]:
        if requirement == LoopRequirement.ACCUMULATE:
            return """LoopBehaviorConstraint violation: Missing accumulation for ALL/LAST matches

What's wrong:
  Loop should accumulate all matches, but has early return instead

Why it matters:
  Early return stops at first match, missing subsequent matches.
  This produces incomplete results (e.g., find_all_indices returns only first).

How to fix:
  Accumulate matches in a list/variable, return after loop completes

Example:
  # Current (wrong - returns first only):
  def find_all(items, target):
      for i, item in enumerate(items):
          if item == target:
              return [i]  # Early return - wrong!
      return []

  # Fixed (correct - finds all):
  def find_all(items, target):
      indices = []  # Accumulator
      for i, item in enumerate(items):
          if item == target:
              indices.append(i)  # Accumulate
      return indices  # Return after loop
"""
        else:
            return f"LoopBehaviorConstraint violation: {violation.description}\nExpected accumulation pattern for ALL_MATCHES/LAST_MATCH"

    else:
        # Generic loop constraint violation
        return f"LoopBehaviorConstraint violation: {violation.description}"


def _format_position_violation(
    violation: ConstraintViolation, constraint: Constraint | None
) -> str:
    """Format PositionConstraint violations with validation examples."""
    if not isinstance(constraint, PositionConstraint):
        return f"Position constraint violation: {violation.description}"

    elements = constraint.elements
    requirement = constraint.requirement
    elements_str = " and ".join([f"'{e}'" for e in elements])

    if requirement == PositionRequirement.NOT_ADJACENT:
        min_distance = constraint.min_distance
        return f"""PositionConstraint violation: Elements must not be adjacent

What's wrong:
  Code validates that {elements_str} exist, but doesn't check they're not adjacent

Why it matters:
  Adjacent elements can cause invalid inputs to be accepted (e.g., email
  validation accepting 'test@.com' where dot immediately follows @).

How to fix:
  Add position check ensuring elements are at least {min_distance + 1} characters apart

Example (for email validation):
  # Current (wrong - accepts 'test@.com'):
  def is_valid(email):
      return '@' in email and '.' in email  # No position check!

  # Fixed (correct - rejects 'test@.com'):
  def is_valid(email):
      at_idx = email.find('@')
      dot_idx = email.find('.')
      if at_idx == -1 or dot_idx == -1:
          return False
      return abs(at_idx - dot_idx) > {min_distance}  # Check distance!
"""

    elif requirement == PositionRequirement.ORDERED:
        return f"""PositionConstraint violation: Elements must appear in order

What's wrong:
  Code doesn't verify that {elements_str} appear in the required order

Why it matters:
  Order matters for validity (e.g., closing bracket before opening bracket
  would be invalid).

How to fix:
  Add comparison to ensure first element appears before subsequent elements

Example:
  # Current (wrong):
  def validate(text):
      return '{elements[0]}' in text and '{elements[1]}' in text

  # Fixed (correct):
  def validate(text):
      idx1 = text.find('{elements[0]}')
      idx2 = text.find('{elements[1]}')
      return idx1 != -1 and idx2 != -1 and idx1 < idx2
"""

    elif requirement == PositionRequirement.MIN_DISTANCE:
        min_distance = constraint.min_distance
        return f"""PositionConstraint violation: Elements must be at least {min_distance} characters apart

What's wrong:
  Code doesn't enforce minimum distance of {min_distance} between {elements_str}

How to fix:
  Add check: abs(idx1 - idx2) >= {min_distance}
"""

    elif requirement == PositionRequirement.MAX_DISTANCE:
        max_distance = constraint.max_distance
        return f"""PositionConstraint violation: Elements must be at most {max_distance} characters apart

What's wrong:
  Code doesn't enforce maximum distance of {max_distance} between {elements_str}

How to fix:
  Add check: abs(idx1 - idx2) <= {max_distance}
"""

    else:
        return f"PositionConstraint violation: {violation.description}"


def _format_syntax_error(violation: ConstraintViolation) -> str:
    """Format syntax errors clearly."""
    return f"""Syntax Error: Code cannot be parsed

What's wrong:
  {violation.description}

How to fix:
  Review and fix syntax errors before retrying constraint validation
"""


def _format_missing_function(violation: ConstraintViolation) -> str:
    """Format missing function errors clearly."""
    return f"""Missing Function: Expected function not found

What's wrong:
  {violation.description}

How to fix:
  Ensure the generated code includes the required function definition
"""


def format_violations_summary(
    violations: list[ConstraintViolation],
    constraints: dict[str, Constraint] | None = None,
) -> str:
    """
    Format multiple violations into a clear summary for retry feedback.

    Args:
        violations: List of constraint violations
        constraints: Optional mapping of constraint_type -> Constraint for context

    Returns:
        Formatted summary string for LLM feedback
    """
    if not violations:
        return "All constraints satisfied ✓"

    # Count violations by severity
    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    summary_parts = []

    summary_parts.append("=" * 80)
    summary_parts.append("CONSTRAINT VALIDATION FAILED")
    summary_parts.append("=" * 80)
    summary_parts.append("")

    if errors:
        summary_parts.append(
            f"Found {len(errors)} ERROR(s) - must fix before code can be accepted:"
        )
        summary_parts.append("")

        for i, violation in enumerate(errors, 1):
            summary_parts.append(f"ERROR {i}/{len(errors)}:")
            summary_parts.append("-" * 80)

            # Get corresponding constraint for better messages
            constraint = None
            if constraints and violation.constraint_type in constraints:
                constraint = constraints[violation.constraint_type]

            formatted_msg = format_violation_for_user(violation, constraint)
            summary_parts.append(formatted_msg)
            summary_parts.append("")

    if warnings:
        summary_parts.append(f"Found {len(warnings)} WARNING(s) - recommended to fix:")
        summary_parts.append("")

        for i, warning in enumerate(warnings, 1):
            summary_parts.append(f"WARNING {i}/{len(warnings)}: {warning.description}")

        summary_parts.append("")

    summary_parts.append("=" * 80)
    summary_parts.append("Please fix these violations in the next generation attempt.")
    summary_parts.append("=" * 80)

    return "\n".join(summary_parts)


def get_constraint_hint(constraint: Constraint) -> str:
    """
    Get a brief hint for a constraint to include in generation prompt.

    This is used to guide LLM generation proactively, not just react to violations.

    Args:
        constraint: The constraint to generate a hint for

    Returns:
        Brief, actionable hint string
    """
    if isinstance(constraint, ReturnConstraint):
        return f"MUST explicitly return '{constraint.value_name}' value (not None)"

    elif isinstance(constraint, LoopBehaviorConstraint):
        if constraint.search_type == LoopSearchType.FIRST_MATCH:
            return "MUST use early return inside loop for FIRST match (not accumulate to last)"
        elif constraint.search_type == LoopSearchType.ALL_MATCHES:
            return "MUST accumulate all matches (no early return)"
        elif constraint.search_type == LoopSearchType.LAST_MATCH:
            return "MUST accumulate to find LAST match (no early return)"
        else:
            return f"Loop behavior: {constraint.search_type.value}"

    elif isinstance(constraint, PositionConstraint):
        elements_str = " and ".join([f"'{e}'" for e in constraint.elements])
        if constraint.requirement == PositionRequirement.NOT_ADJACENT:
            return (
                f"MUST check {elements_str} are NOT adjacent (distance > {constraint.min_distance})"
            )
        elif constraint.requirement == PositionRequirement.ORDERED:
            return f"MUST check {elements_str} appear in this order"
        elif constraint.requirement == PositionRequirement.MIN_DISTANCE:
            return f"MUST check {elements_str} are at least {constraint.min_distance} apart"
        elif constraint.requirement == PositionRequirement.MAX_DISTANCE:
            return f"MUST check {elements_str} are at most {constraint.max_distance} apart"
        else:
            return f"Position constraint: {constraint.requirement.value}"

    else:
        return constraint.description if constraint.description else "Unknown constraint"
