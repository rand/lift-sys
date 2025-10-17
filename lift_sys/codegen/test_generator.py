"""
Test Case Generator - Generate test cases from IR for validation.

Generates test cases from IR components to validate generated code:
1. From assertions → expected behavior
2. From effects → test scenarios
3. From parameter types → valid/invalid inputs
4. Edge cases from signature (empty, None, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lift_sys.ir.models import IntermediateRepresentation


@dataclass
class TestCase:
    """A test case for validating generated code."""

    inputs: dict[str, Any]
    """Input values for function parameters"""

    expected_output: Any | None
    """Expected return value (None if should raise)"""

    should_raise: type[Exception] | None = None
    """Exception type that should be raised, if any"""

    description: str = ""
    """Human-readable description of what this test validates"""


class TestCaseGenerator:
    """Generate test cases from IR for validation."""

    def generate_test_cases(self, ir: IntermediateRepresentation) -> list[TestCase]:
        """
        Generate test cases from IR.

        Args:
            ir: Intermediate representation

        Returns:
            List of test cases for validation
        """
        test_cases: list[TestCase] = []

        # 1. Edge cases from parameter types
        test_cases.extend(self._generate_edge_cases(ir))

        # 2. Test cases from assertions
        test_cases.extend(self._generate_assertion_tests(ir))

        # 3. Test cases from effects (behavior-based)
        test_cases.extend(self._generate_effect_tests(ir))

        return test_cases

    def _generate_edge_cases(self, ir: IntermediateRepresentation) -> list[TestCase]:
        """Generate edge case tests from parameter types."""
        tests: list[TestCase] = []

        # Get intent and signature
        intent_text = ir.intent.summary.lower()
        params = ir.signature.parameters
        return_type = ir.signature.returns

        # Edge case patterns based on parameter types
        for param in params:
            type_hint = param.type_hint.lower() if param.type_hint else ""

            # String parameters
            if "str" in type_hint:
                # Empty string
                inputs = {p.name: ("" if p.name == param.name else "test") for p in params}

                # For count/length functions, empty should return 0
                if any(word in intent_text for word in ["count", "length", "number of"]):
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=0,
                            description="Edge case: empty string should return 0",
                        )
                    )
                # For validation functions, empty might be invalid
                elif any(word in intent_text for word in ["valid", "check", "validate"]):
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=False,
                            description="Edge case: empty string should be invalid",
                        )
                    )

            # List parameters
            elif "list" in type_hint:
                # Empty list
                inputs = {p.name: ([] if p.name == param.name else 1) for p in params}

                # For "find"/"index" functions, empty list should return -1
                if "find" in intent_text or "index" in intent_text:
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=-1,
                            description="Edge case: empty list should return -1",
                        )
                    )
                # For "first" functions (but not find first), empty should return None
                elif "first" in intent_text and "find" not in intent_text:
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=None,
                            description="Edge case: empty list should return None",
                        )
                    )
                # For average/sum, empty should return 0 or 0.0
                elif "average" in intent_text or "sum" in intent_text:
                    expected = 0.0 if return_type == "float" else 0
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=expected,
                            description=f"Edge case: empty list should return {expected}",
                        )
                    )

        return tests

    def _generate_assertion_tests(self, ir: IntermediateRepresentation) -> list[TestCase]:
        """Generate test cases from IR assertions."""
        tests: list[TestCase] = []

        intent_text = ir.intent.summary.lower()
        params = ir.signature.parameters

        # Check assertions for specific conditions
        for assertion in ir.assertions:
            predicate = assertion.predicate.lower()

            # "result >= 0" → test that we never return negative
            if ">= 0" in predicate or "non-negative" in predicate:
                # Create a minimal test case
                inputs = {p.name: self._get_minimal_value(p.type_hint) for p in params}
                # We can't know exact output, but we know it should be >= 0
                # This will be validated during execution
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=None,  # Will validate >= 0 during execution
                        description="Assertion test: result should be >= 0",
                    )
                )

            # "index is valid or -1" → test not found case
            if ("-1" in predicate or "not found" in predicate) and "find" in intent_text:
                # Create inputs where target won't be found
                if len(params) >= 2:
                    inputs = {params[0].name: [1, 2, 3], params[1].name: 999}
                    tests.append(
                        TestCase(
                            inputs=inputs,
                            expected_output=-1,
                            description="Assertion test: not found should return -1",
                        )
                    )

        return tests

    def _generate_effect_tests(self, ir: IntermediateRepresentation) -> list[TestCase]:
        """Generate test cases from effect descriptions."""
        tests: list[TestCase] = []

        intent_text = ir.intent.summary.lower()
        params = ir.signature.parameters
        effects = [e.description.lower() for e in ir.effects]
        all_effects = " ".join(effects)

        # Pattern 1: "split by spaces" + "count" → word counting
        if "split" in all_effects and "space" in all_effects:
            if "count" in all_effects or "count" in intent_text:
                # Test with known word count
                inputs = {params[0].name: "hello world"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=2,
                        description="Effect test: 'hello world' should have 2 words",
                    )
                )

                # Test with single word
                inputs = {params[0].name: "hello"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=1,
                        description="Effect test: 'hello' should have 1 word",
                    )
                )

        # Pattern 2: "find first" + "return immediately" → test with duplicates
        if "first" in intent_text and "enumerate" in all_effects:
            if len(params) >= 2:
                # Test with duplicate values - should return FIRST index
                inputs = {params[0].name: [1, 2, 1], params[1].name: 1}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=0,
                        description="Effect test: should return FIRST occurrence at index 0, not last",
                    )
                )

        # Pattern 3: Email validation - @ and dot checks
        if "email" in intent_text and "valid" in intent_text:
            if len(params) >= 1:
                # Valid email
                inputs = {params[0].name: "test@example.com"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=True,
                        description="Effect test: 'test@example.com' should be valid",
                    )
                )

                # Invalid: no @
                inputs = {params[0].name: "test.example.com"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=False,
                        description="Effect test: 'test.example.com' should be invalid (no @)",
                    )
                )

                # Invalid: no dot
                inputs = {params[0].name: "test@example"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=False,
                        description="Effect test: 'test@example' should be invalid (no dot)",
                    )
                )

                # Invalid: dot before @
                inputs = {params[0].name: "test.@example"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=False,
                        description="Effect test: 'test.@example' should be invalid (dot before @)",
                    )
                )

                # Invalid: dot immediately after @
                inputs = {params[0].name: "test@.com"}
                tests.append(
                    TestCase(
                        inputs=inputs,
                        expected_output=False,
                        description="Effect test: 'test@.com' should be invalid (dot immediately after @)",
                    )
                )

        return tests

    def _get_minimal_value(self, type_hint: str | None) -> Any:
        """Get minimal value for a type (for testing)."""
        if not type_hint:
            return None

        type_hint = type_hint.lower()

        if "str" in type_hint:
            return ""
        elif "int" in type_hint:
            return 0
        elif "float" in type_hint:
            return 0.0
        elif "bool" in type_hint:
            return False
        elif "list" in type_hint:
            return []
        elif "dict" in type_hint:
            return {}
        else:
            return None
