"""
Constraint Validator - Validates that generated code satisfies IR constraints.

This module provides validation logic to check if generated Python code adheres to
the constraints specified in the IR. Unlike AST repair (which fixes code after generation),
constraint validation VERIFIES that the LLM followed the constraints during generation.

Phase 7: This enables verification that prevention worked, not just post-hoc repair.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lift_sys.ir.constraints import (
        Constraint,
        LoopBehaviorConstraint,
        PositionConstraint,
        ReturnConstraint,
    )
    from lift_sys.ir.models import IntermediateRepresentation


class ConstraintViolation:
    """Represents a constraint violation found during validation."""

    def __init__(
        self,
        constraint_type: str,
        description: str,
        severity: str = "error",
        line_number: int | None = None,
    ):
        self.constraint_type = constraint_type
        self.description = description
        self.severity = severity
        self.line_number = line_number

    def __repr__(self) -> str:
        line_info = f" (line {self.line_number})" if self.line_number else ""
        return f"[{self.severity.upper()}] {self.constraint_type}: {self.description}{line_info}"


class ConstraintValidator:
    """
    Validates that generated code satisfies IR constraints.

    This validator checks AST structure to ensure constraints are met,
    but unlike AST repair, it doesn't modify the code - it only reports violations.
    """

    def validate(self, code: str, ir: IntermediateRepresentation) -> list[ConstraintViolation]:
        """
        Validate that generated code satisfies all constraints in the IR.

        Args:
            code: Generated Python code to validate
            ir: IR containing constraints to check

        Returns:
            List of constraint violations (empty if all constraints satisfied)
        """
        violations: list[ConstraintViolation] = []

        # Parse code to AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Syntax errors prevent constraint validation
            violations.append(
                ConstraintViolation(
                    constraint_type="syntax_error",
                    description=f"Code has syntax error: {e}",
                    severity="error",
                    line_number=e.lineno,
                )
            )
            return violations

        # Find the main function (matching IR signature name)
        func_def = self._find_function(tree, ir.signature.name)
        if not func_def:
            violations.append(
                ConstraintViolation(
                    constraint_type="missing_function",
                    description=f"Function '{ir.signature.name}' not found in generated code",
                    severity="error",
                )
            )
            return violations

        # Validate each constraint
        for constraint in ir.constraints:
            constraint_violations = self._validate_constraint(constraint, func_def, code, ir)
            violations.extend(constraint_violations)

        return violations

    def _find_function(self, tree: ast.AST, name: str) -> ast.FunctionDef | None:
        """Find function definition by name in AST."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                return node
        return None

    def _validate_constraint(
        self,
        constraint: Constraint,
        func_def: ast.FunctionDef,
        code: str,
        ir: IntermediateRepresentation,
    ) -> list[ConstraintViolation]:
        """Validate a single constraint against function AST."""
        from lift_sys.ir.constraints import (
            LoopBehaviorConstraint,
            PositionConstraint,
            ReturnConstraint,
        )

        if isinstance(constraint, ReturnConstraint):
            return self._validate_return_constraint(constraint, func_def)
        elif isinstance(constraint, LoopBehaviorConstraint):
            return self._validate_loop_constraint(constraint, func_def)
        elif isinstance(constraint, PositionConstraint):
            return self._validate_position_constraint(constraint, func_def, code, ir)
        else:
            # Unknown constraint type - skip validation
            return []

    def _validate_return_constraint(
        self, constraint: ReturnConstraint, func_def: ast.FunctionDef
    ) -> list[ConstraintViolation]:
        """
        Validate ReturnConstraint: Check that computed value is explicitly returned.

        Looks for:
        1. A return statement exists
        2. Return statement returns a variable (not None)
        3. Variable name matches the expected value_name (if we can determine it)
        """
        violations: list[ConstraintViolation] = []

        # Find all return statements
        returns = [node for node in ast.walk(func_def) if isinstance(node, ast.Return)]

        if not returns:
            violations.append(
                ConstraintViolation(
                    constraint_type="return_constraint",
                    description=f"No return statement found. Expected to return '{constraint.value_name}'",
                    severity=constraint.severity.value,
                )
            )
            return violations

        # Check if at least one return statement returns a value (not None)
        has_value_return = False
        for ret in returns:
            if ret.value is not None and not (
                isinstance(ret.value, ast.Constant) and ret.value.value is None
            ):
                has_value_return = True
                break

        if not has_value_return:
            violations.append(
                ConstraintViolation(
                    constraint_type="return_constraint",
                    description=f"All return statements return None. Expected to return '{constraint.value_name}'",
                    severity=constraint.severity.value,
                    line_number=returns[0].lineno if returns else None,
                )
            )

        return violations

    def _validate_loop_constraint(
        self, constraint: LoopBehaviorConstraint, func_def: ast.FunctionDef
    ) -> list[ConstraintViolation]:
        """
        Validate LoopBehaviorConstraint: Check loop behavior matches requirement.

        For FIRST_MATCH + EARLY_RETURN:
        - Check that loop contains a return statement (early return pattern)
        - Not just accumulation into a variable

        For LAST_MATCH/ALL_MATCHES + ACCUMULATE:
        - Check that loop accumulates into a variable
        - Return happens after loop completes
        """
        from lift_sys.ir.constraints import LoopRequirement, LoopSearchType

        violations: list[ConstraintViolation] = []

        # Find all for/while loops in function
        loops = [node for node in ast.walk(func_def) if isinstance(node, (ast.For, ast.While))]

        if not loops:
            # No loops found - might not be a violation if function doesn't need loops
            # Only report if constraint explicitly requires loops
            if constraint.search_type in [
                LoopSearchType.FIRST_MATCH,
                LoopSearchType.LAST_MATCH,
                LoopSearchType.ALL_MATCHES,
            ]:
                violations.append(
                    ConstraintViolation(
                        constraint_type="loop_constraint",
                        description=f"No loop found, but constraint requires {constraint.search_type.value} pattern",
                        severity=constraint.severity.value,
                    )
                )
            return violations

        # Check FIRST_MATCH + EARLY_RETURN pattern
        if (
            constraint.search_type == LoopSearchType.FIRST_MATCH
            and constraint.requirement == LoopRequirement.EARLY_RETURN
        ):
            # At least one loop should have a return inside it
            has_early_return = False
            for loop in loops:
                for node in ast.walk(loop):
                    if isinstance(node, ast.Return) and node != loop:
                        # Found return inside loop
                        has_early_return = True
                        break
                if has_early_return:
                    break

            if not has_early_return:
                violations.append(
                    ConstraintViolation(
                        constraint_type="loop_constraint",
                        description="FIRST_MATCH requires early return inside loop, but no return found in loop body",
                        severity=constraint.severity.value,
                        line_number=loops[0].lineno if loops else None,
                    )
                )

        # Check ACCUMULATE pattern (LAST_MATCH or ALL_MATCHES)
        elif constraint.requirement == LoopRequirement.ACCUMULATE:
            # Loop should NOT have early return (should accumulate instead)
            has_early_return = False
            for loop in loops:
                # Check all returns inside loop (including nested in if statements)
                for node in ast.walk(loop):
                    if isinstance(node, ast.Return) and node != loop:
                        # Found return inside loop
                        has_early_return = True
                        break
                if has_early_return:
                    break

            if has_early_return:
                violations.append(
                    ConstraintViolation(
                        constraint_type="loop_constraint",
                        description=f"{constraint.search_type.value} requires accumulation, but found early return in loop",
                        severity=constraint.severity.value,
                        line_number=loops[0].lineno if loops else None,
                    )
                )

        return violations

    def _validate_position_constraint(
        self,
        constraint: PositionConstraint,
        func_def: ast.FunctionDef,
        code: str,
        ir: IntermediateRepresentation,
    ) -> list[ConstraintViolation]:
        """
        Validate PositionConstraint: Check element position requirements.

        This is domain-specific (e.g., email validation) and harder to validate
        statically from AST. We check for basic patterns:
        - NOT_ADJACENT: Check that code validates elements are not adjacent
        - ORDERED: Check that code validates element ordering
        """
        from lift_sys.ir.constraints import PositionRequirement

        violations: list[ConstraintViolation] = []

        # Check semantic applicability - skip validation for nonsensical constraints
        # (e.g., position constraints on parameter names in arithmetic functions)
        is_applicable, reason = constraint.is_semantically_applicable(ir)
        if not is_applicable:
            # Constraint is not semantically applicable - skip validation
            # (Don't report as violation since the constraint itself is spurious)
            return violations

        # For now, do basic heuristic checking
        # A more sophisticated validator would trace data flow

        if constraint.requirement == PositionRequirement.NOT_ADJACENT:
            # Check if code mentions both elements and has some adjacency check
            elements_str = " and ".join(f"'{e}'" for e in constraint.elements)

            # Heuristic: look for index arithmetic or position checking
            # Need to check for index/find operations or arithmetic
            has_index_lookup = any(
                keyword in code
                for keyword in [
                    "index(",
                    "find(",
                    ".index",
                    ".find",
                    "idx",
                    "position",
                ]
            )

            has_arithmetic = any(
                keyword in code for keyword in ["abs(", "!=", "> 1", "< -1", " - ", " + "]
            )

            has_position_check = has_index_lookup and has_arithmetic

            if not has_position_check:
                violations.append(
                    ConstraintViolation(
                        constraint_type="position_constraint",
                        description=f"Constraint requires {elements_str} to not be adjacent, but no position checking found",
                        severity=constraint.severity.value,
                    )
                )

        elif constraint.requirement == PositionRequirement.ORDERED:
            # Check if code validates ordering
            has_order_check = any(
                keyword in code for keyword in ["index", "find", "before", "<", ">"]
            )

            if not has_order_check:
                elements_str = " before ".join(f"'{e}'" for e in constraint.elements)
                violations.append(
                    ConstraintViolation(
                        constraint_type="position_constraint",
                        description=f"Constraint requires {elements_str}, but no ordering check found",
                        severity=constraint.severity.value,
                    )
                )

        return violations


def validate_code_against_constraints(
    code: str, ir: IntermediateRepresentation
) -> tuple[bool, list[ConstraintViolation]]:
    """
    Convenience function to validate code against IR constraints.

    Args:
        code: Generated Python code
        ir: IR with constraints

    Returns:
        Tuple of (is_valid, violations)
        - is_valid: True if no ERROR-level violations
        - violations: List of all violations found
    """
    validator = ConstraintValidator()
    violations = validator.validate(code, ir)

    # Check if any violations are errors (not just warnings)
    has_errors = any(v.severity == "error" for v in violations)

    return (not has_errors, violations)


__all__ = [
    "ConstraintValidator",
    "ConstraintViolation",
    "validate_code_against_constraints",
]
