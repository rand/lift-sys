"""
Assertion-based validation of generated code against IR specifications.

Phase 5a: Simple Assertion Checker
Validates generated code by:
1. Generating test cases from IR assertions
2. Executing code with test inputs
3. Checking outputs match expected behavior
4. Reporting semantic errors
"""

import re
from dataclasses import dataclass, field
from typing import Any

from lift_sys.ir.models import IntermediateRepresentation


@dataclass
class ValidationIssue:
    """An issue found during validation."""

    severity: str  # 'error', 'warning'
    message: str
    location: str | None = None
    test_input: Any = None
    expected: Any = None
    actual: Any = None


@dataclass
class ValidationResult:
    """Result of validating code against IR."""

    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    def __str__(self) -> str:
        if self.passed:
            return "✓ Validation passed"
        return f"✗ Validation failed: {len(self.issues)} issue(s)"


class AssertionChecker:
    """Validates generated code against IR assertions.

    Approach:
    - Parse IR assertions to understand expected behavior
    - Generate test inputs covering edge cases
    - Execute generated code with inputs
    - Verify outputs match assertions
    """

    def validate(
        self,
        code: str,
        function_name: str,
        ir: IntermediateRepresentation,
    ) -> ValidationResult:
        """
        Validate generated code satisfies IR assertions.

        Args:
            code: Generated Python code
            function_name: Name of function to validate
            ir: Intermediate representation with assertions

        Returns:
            ValidationResult with pass/fail and issues
        """
        issues: list[ValidationIssue] = []

        # Extract function from code
        namespace: dict[str, Any] = {}
        try:
            exec(code, namespace)
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Failed to execute code: {e}",
                )
            )
            return ValidationResult(passed=False, issues=issues)

        func = namespace.get(function_name)
        if not func:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Function '{function_name}' not found in generated code",
                )
            )
            return ValidationResult(passed=False, issues=issues)

        # Generate test cases from IR
        test_cases = self._generate_test_cases_from_ir(ir)

        # If no test cases, validation passes trivially
        if not test_cases:
            return ValidationResult(passed=True, issues=[])

        # Validate each test case
        for test_input, expected_property in test_cases:
            try:
                actual = func(*test_input)
                if not self._check_property(actual, expected_property):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            message=f"Assertion failed: expected {expected_property}, got {actual}",
                            test_input=test_input,
                            expected=expected_property,
                            actual=actual,
                        )
                    )
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        message=f"Execution failed: {e}",
                        test_input=test_input,
                    )
                )

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
        )

    def _generate_test_cases_from_ir(
        self, ir: IntermediateRepresentation
    ) -> list[tuple[tuple[Any, ...], Any]]:
        """
        Generate test cases from IR assertions.

        Returns:
            List of (input_tuple, expected_output) pairs
        """
        test_cases: list[tuple[tuple[Any, ...], Any]] = []

        # Parse assertions
        for assertion in ir.assertions:
            predicate = assertion.predicate.lower()

            # Pattern: "Returns 'X' for Y inputs"
            # Example: "Returns 'int' for integer inputs"
            if "returns" in predicate and "for" in predicate:
                cases = self._parse_returns_for_pattern(predicate)
                test_cases.extend(cases)

            # Pattern: "Returns 'X' if Y"
            # Example: "Returns 'zero' if zero"
            elif "returns" in predicate and "if" in predicate:
                cases = self._parse_returns_if_pattern(predicate)
                test_cases.extend(cases)

        # Add edge case test inputs
        edge_cases = self._generate_edge_cases(ir)
        test_cases.extend(edge_cases)

        return test_cases

    def _parse_returns_for_pattern(self, predicate: str) -> list[tuple[tuple[Any, ...], Any]]:
        """
        Parse "Returns 'X' for Y inputs" pattern.

        Example: "Returns 'int' for integer inputs" → [(42,), 'int']
        """
        test_cases: list[tuple[tuple[Any, ...], Any]] = []

        # Extract expected return value (in quotes)
        match = re.search(r"returns\s+['\"]([^'\"]+)['\"]", predicate, re.IGNORECASE)
        if not match:
            return test_cases

        expected_value = match.group(1)

        # Determine input type
        predicate_lower = predicate.lower()
        if "integer" in predicate_lower or "int" in predicate_lower:
            test_cases.append(((42,), expected_value))
            test_cases.append(((0,), expected_value))
            test_cases.append(((-5,), expected_value))
        elif "string" in predicate_lower or "str" in predicate_lower:
            test_cases.append((("hello",), expected_value))
            test_cases.append((("",), expected_value))
        elif "list" in predicate_lower:
            test_cases.append((([1, 2, 3],), expected_value))
            test_cases.append((([],), expected_value))
        elif "float" in predicate_lower:
            test_cases.append(((3.14,), expected_value))
            test_cases.append(((0.0,), expected_value))
        elif "none" in predicate_lower or "null" in predicate_lower:
            test_cases.append(((None,), expected_value))
        elif "dict" in predicate_lower or "object" in predicate_lower:
            test_cases.append((({"key": "value"},), expected_value))

        return test_cases

    def _parse_returns_if_pattern(self, predicate: str) -> list[tuple[tuple[Any, ...], Any]]:
        """
        Parse "Returns 'X' if Y" pattern.

        Example: "Returns 'zero' if zero" → [(0,), 'zero']
        """
        test_cases: list[tuple[tuple[Any, ...], Any]] = []

        # Extract expected return value
        match = re.search(r"returns\s+['\"]([^'\"]+)['\"]", predicate, re.IGNORECASE)
        if not match:
            return test_cases

        expected_value = match.group(1)

        # Determine condition
        predicate_lower = predicate.lower()
        if "zero" in predicate_lower:
            test_cases.append(((0,), expected_value))
        elif "negative" in predicate_lower:
            test_cases.append(((-5,), expected_value))
            test_cases.append(((-100,), expected_value))
        elif "positive" in predicate_lower:
            if "even" in predicate_lower:
                test_cases.append(((4,), expected_value))
                test_cases.append(((100,), expected_value))
            elif "odd" in predicate_lower:
                test_cases.append(((3,), expected_value))
                test_cases.append(((99,), expected_value))
            else:
                test_cases.append(((5,), expected_value))
        elif "empty" in predicate_lower:
            if "list" in predicate_lower:
                test_cases.append((([],), expected_value))
            elif "string" in predicate_lower:
                test_cases.append((("",), expected_value))

        return test_cases

    def _generate_edge_cases(
        self, ir: IntermediateRepresentation
    ) -> list[tuple[tuple[Any, ...], Any]]:
        """
        Generate edge case test inputs based on function signature.

        For type checking functions, include types NOT in assertions
        to test the 'other' or 'else' branch.
        """
        edge_cases: list[tuple[tuple[Any, ...], Any]] = []

        # Check if this is a type checking function
        intent = ir.intent.summary.lower()
        assertions = [a.predicate.lower() for a in ir.assertions]
        all_assertion_text = " ".join(assertions)

        # Detect if this is likely a type-checking function by looking for:
        # 1. "type" in intent
        # 2. "isinstance" in intent
        # 3. Multiple type-specific assertions (int, str, list, etc.)
        type_keywords_in_intent = "type" in intent or "isinstance" in intent

        type_count = sum(
            [
                1
                for keyword in ["int", "str", "list", "float", "dict", "bool"]
                if keyword in all_assertion_text
            ]
        )
        has_multiple_types = type_count >= 2

        is_type_checking_function = type_keywords_in_intent or has_multiple_types

        if is_type_checking_function:
            # Determine what the 'other' value should be
            # Look for "other", "unknown", "else", etc. in assertions
            other_value = "other"  # default
            for assertion in assertions:
                if "other" in assertion:
                    # Try to extract the quoted value
                    match = re.search(r"['\"]([^'\"]*other[^'\"]*)['\" ]", assertion)
                    if match:
                        other_value = match.group(1)
                        break
                elif "unknown" in assertion:
                    other_value = "unknown"
                    break
                elif "else" in assertion:
                    # Extract value after "else"
                    match = re.search(r"else[^'\"]*['\"]([^'\"]+)['\"]", assertion)
                    if match:
                        other_value = match.group(1)
                        break

            # Check what types are already covered
            covered_types = set()
            if any("int" in a for a in assertions):
                covered_types.add("int")
            if any("str" in a for a in assertions):
                covered_types.add("str")
            if any("list" in a for a in assertions):
                covered_types.add("list")
            if any("float" in a for a in assertions):
                covered_types.add("float")
            if any("dict" in a for a in assertions):
                covered_types.add("dict")
            if any("bool" in a for a in assertions):
                covered_types.add("bool")

            # Generate edge cases for uncovered common Python types
            if "float" not in covered_types:
                edge_cases.append(((3.14,), other_value))  # float
            if "dict" not in covered_types:
                edge_cases.append((({"key": "val"},), other_value))  # dict
            if "none" not in covered_types:
                edge_cases.append(((None,), other_value))  # None
            if "bool" not in covered_types:
                edge_cases.append(((True,), other_value))  # bool
                edge_cases.append(((False,), other_value))

        return edge_cases

    def _check_property(self, actual: Any, expected: Any) -> bool:
        """Check if actual value satisfies expected property."""
        return actual == expected
