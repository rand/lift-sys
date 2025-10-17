"""
Semantic Validator - Step 2 of IR Interpreter

Validates IR consistency and semantic correctness:
1. Return value consistency with signature
2. Parameter usage validation
3. Assertion coverage checking
4. Control flow completeness

Works with ExecutionTrace from EffectChainAnalyzer to detect:
- Type mismatches between signature and effects
- Unused parameters
- Assertions that can't be checked
- Missing return paths
"""

from __future__ import annotations

from dataclasses import dataclass

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.validation.effect_analyzer import ExecutionTrace, SemanticIssue


@dataclass
class ValidationResult:
    """Result of semantic validation."""

    passed: bool
    """Whether validation passed (no errors)"""

    issues: list[SemanticIssue]
    """All issues found (errors + warnings)"""

    errors: list[SemanticIssue]
    """Only error-level issues"""

    warnings: list[SemanticIssue]
    """Only warning-level issues"""

    def __str__(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [f"Semantic Validation: {status}"]

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        return "\n".join(lines)


class SemanticValidator:
    """
    Validates IR semantic consistency.

    Takes an IR and ExecutionTrace (from EffectChainAnalyzer) and checks:
    1. Return value consistency with signature
    2. Parameter usage in effects
    3. Assertion coverage
    4. Control flow completeness
    """

    def validate(self, ir: IntermediateRepresentation, trace: ExecutionTrace) -> ValidationResult:
        """
        Perform full semantic validation.

        Args:
            ir: Intermediate representation
            trace: Execution trace from EffectChainAnalyzer

        Returns:
            ValidationResult with all issues found
        """
        issues: list[SemanticIssue] = []

        # Add issues already found by analyzer
        issues.extend(trace.issues)

        # Check return value consistency
        issues.extend(self.validate_return_consistency(ir, trace))

        # Check parameter usage
        issues.extend(self.validate_parameter_usage(ir, trace))

        # Check assertion coverage
        issues.extend(self.validate_assertion_coverage(ir, trace))

        # Separate errors and warnings
        errors = [issue for issue in issues if issue.severity == "error"]
        warnings = [issue for issue in issues if issue.severity == "warning"]

        return ValidationResult(
            passed=len(errors) == 0,
            issues=issues,
            errors=errors,
            warnings=warnings,
        )

    def validate_return_consistency(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Ensure effect chain produces value matching return type.

        Checks:
        - If signature has return type, effect chain must return a value
        - Return value type should match (or be compatible with) signature

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        # If no return type specified, nothing to check
        if not ir.signature.returns:
            return issues

        # If no return value in trace, error already flagged by analyzer
        # We just check for type mismatches here
        if trace.return_value:
            expected_type = ir.signature.returns
            actual_type = trace.return_value.type_hint

            # Check for type mismatch
            if not self._types_compatible(expected_type, actual_type):
                issues.append(
                    SemanticIssue(
                        severity="warning",
                        category="type_mismatch",
                        message=f"Return type mismatch: signature says '{expected_type}' but effect chain returns '{actual_type}'",
                        suggestion=f"Update effects to produce {expected_type}, or update signature",
                    )
                )

        return issues

    def validate_parameter_usage(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Check that all parameters are used in effects.

        Unused parameters might indicate:
        - Missing effect that should use the parameter
        - Unnecessary parameter in signature

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        # Get all effect descriptions
        effect_text = " ".join([e.description.lower() for e in ir.effects])

        # Check each parameter
        for param in ir.signature.parameters:
            param_name = param.name.lower()

            # Check if parameter name appears in any effect
            # Simple heuristic: parameter name should appear in effect descriptions
            if param_name not in effect_text:
                # Check if it's referenced by type (e.g., "input string" for "text" parameter)
                param_type = param.type_hint or ""
                type_keywords = self._get_type_keywords(param_type)

                # If neither name nor type keywords appear, parameter might be unused
                if not any(keyword in effect_text for keyword in type_keywords):
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="unused_parameter",
                            message=f"Parameter '{param.name}' may not be used in effects",
                            suggestion=f"Add effect that uses '{param.name}' or remove parameter from signature",
                        )
                    )

        return issues

    def validate_assertion_coverage(
        self, ir: IntermediateRepresentation, trace: ExecutionTrace
    ) -> list[SemanticIssue]:
        """
        Ensure assertions can be checked by effects.

        Checks:
        - Assertions reference values produced by effects
        - Assertions are checkable (not referring to non-existent values)

        Args:
            ir: Intermediate representation
            trace: Execution trace

        Returns:
            List of issues found
        """
        issues: list[SemanticIssue] = []

        # If no assertions, nothing to check
        if not ir.assertions:
            return issues

        # Get all value names from trace (parameters + computed)
        value_names = set(trace.values.keys())

        # Check each assertion
        for _i, assertion in enumerate(ir.assertions):
            predicate = assertion.predicate.lower()

            # Extract potential variable references from predicate
            # Look for patterns like "result is", "count equals", etc.
            words = predicate.split()

            # Check if any referenced values exist in trace
            referenced_values = []
            for word in words:
                if word in value_names:
                    referenced_values.append(word)

            # If assertion seems to reference computed values, check they exist
            # This is a simple heuristic - could be improved
            if not referenced_values:
                # Check if assertion references return value
                if trace.return_value and any(
                    keyword in predicate
                    for keyword in ["return", "result", "output", trace.return_value.name]
                ):
                    # Assertion references return value, which exists
                    continue

                # Assertion doesn't clearly reference any known values
                # This might be okay (e.g., assertions about parameters)
                # Only warn if it seems suspicious
                if any(
                    keyword in predicate
                    for keyword in ["result", "output", "computed", "calculated"]
                ):
                    issues.append(
                        SemanticIssue(
                            severity="warning",
                            category="assertion_coverage",
                            message=f"Assertion '{assertion.predicate}' may reference non-existent values",
                            effect_index=None,
                            suggestion="Ensure effects produce values needed for assertions",
                        )
                    )

        return issues

    def _types_compatible(self, expected: str, actual: str) -> bool:
        """
        Check if two types are compatible.

        Rules:
        - Exact match is compatible
        - "Any" is compatible with anything
        - "list[X]" is compatible with "list[Any]" or "list"
        - Basic type hierarchy (int compatible with float, etc.)

        Args:
            expected: Expected type from signature
            actual: Actual type from trace

        Returns:
            True if types are compatible
        """
        # Exact match
        if expected == actual:
            return True

        # Any is compatible with everything
        if expected == "Any" or actual == "Any":
            return True

        # List compatibility
        if "list" in expected.lower() and "list" in actual.lower():
            return True

        # Dict compatibility
        if "dict" in expected.lower() and "dict" in actual.lower():
            return True

        # Numeric compatibility (int -> float okay)
        if expected in ["float", "number"] and actual in ["int", "float", "number"]:
            return True

        # String compatibility
        if expected in ["str", "string"] and actual in ["str", "string"]:
            return True

        # Boolean compatibility
        if expected in ["bool", "boolean"] and actual in ["bool", "boolean"]:
            return True

        return False

    def _get_type_keywords(self, type_hint: str) -> list[str]:
        """
        Get keywords associated with a type.

        E.g., "str" -> ["string", "text", "word"]
             "int" -> ["integer", "number", "count"]

        Args:
            type_hint: Type hint string

        Returns:
            List of associated keywords
        """
        type_lower = type_hint.lower()

        if "str" in type_lower or "string" in type_lower:
            return ["string", "text", "word", "character"]
        elif "int" in type_lower or "integer" in type_lower:
            return ["integer", "number", "count", "index"]
        elif "bool" in type_lower:
            return ["boolean", "true", "false", "flag"]
        elif "float" in type_lower or "decimal" in type_lower:
            return ["float", "decimal", "number"]
        elif "list" in type_lower or "array" in type_lower:
            return ["list", "array", "collection", "items", "elements"]
        elif "dict" in type_lower or "map" in type_lower:
            return ["dict", "dictionary", "map", "object"]
        else:
            return []
