"""
Unit tests for AssertionChecker (Phase 5a).

Tests validate that:
1. AssertionChecker can validate code against IR assertions
2. Test case generation works correctly
3. Edge cases are caught (get_type_name bug scenario)
"""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation import AssertionChecker


class TestAssertionCheckerBasics:
    """Test basic functionality of AssertionChecker."""

    def test_validation_passes_for_correct_code(self):
        """Test that validation passes when code is correct."""
        # Create simple IR with assertion
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Double a number"),
            signature=SigClause(
                name="double",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            assertions=[
                AssertClause(
                    predicate="Returns double the input value",
                )
            ],
        )

        code = """
def double(x: int) -> int:
    return x * 2
"""

        checker = AssertionChecker()
        result = checker.validate(code, "double", ir)

        # Should pass (no specific test cases generated from this assertion)
        assert result.passed
        assert len(result.issues) == 0

    def test_validation_fails_when_function_not_found(self):
        """Test that validation fails when function doesn't exist."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="missing_func",
                parameters=[],
                returns="int",
            ),
        )

        code = "def other_func(): return 42"

        checker = AssertionChecker()
        result = checker.validate(code, "missing_func", ir)

        assert not result.passed
        assert len(result.issues) == 1
        assert "not found" in result.issues[0].message.lower()

    def test_validation_fails_when_code_is_invalid(self):
        """Test that validation fails when code has syntax errors."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test_func",
                parameters=[],
                returns="int",
            ),
        )

        code = "def test_func( # syntax error"

        checker = AssertionChecker()
        result = checker.validate(code, "test_func", ir)

        assert not result.passed
        assert len(result.issues) == 1
        assert "failed to execute" in result.issues[0].message.lower()


class TestTestCaseGeneration:
    """Test test case generation from IR assertions."""

    def test_generate_test_cases_for_type_checker(self):
        """Test generation of test cases for type checking function."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check the type of a value and return its name"),
            signature=SigClause(
                name="get_type_name",
                parameters=[Parameter(name="value", type_hint="Any")],
                returns="str",
            ),
            assertions=[
                AssertClause(predicate="Returns 'int' for integer inputs"),
                AssertClause(predicate="Returns 'str' for string inputs"),
                AssertClause(predicate="Returns 'list' for list inputs"),
                AssertClause(predicate="Returns 'other' for anything else"),
            ],
        )

        checker = AssertionChecker()
        test_cases = checker._generate_test_cases_from_ir(ir)

        # Should generate test cases for int, str, list
        assert len(test_cases) > 0

        # Check that we have test cases for each type
        input_types = [type(tc[0][0]).__name__ for tc in test_cases if tc[0]]
        assert "int" in input_types
        assert "str" in input_types
        assert "list" in input_types

        # Should also generate edge cases for 'other'
        # (float, dict, None, bool)
        assert "float" in input_types
        assert "dict" in input_types or "NoneType" in input_types

    def test_returns_for_pattern_parsing(self):
        """Test parsing of 'Returns X for Y' pattern."""
        checker = AssertionChecker()

        # Test integer pattern
        cases = checker._parse_returns_for_pattern("Returns 'int' for integer inputs")
        assert len(cases) > 0
        assert any(isinstance(tc[0][0], int) for tc in cases)
        assert all(tc[1] == "int" for tc in cases)

        # Test string pattern
        cases = checker._parse_returns_for_pattern("Returns 'str' for string inputs")
        assert len(cases) > 0
        assert any(isinstance(tc[0][0], str) for tc in cases)
        assert all(tc[1] == "str" for tc in cases)

    def test_returns_if_pattern_parsing(self):
        """Test parsing of 'Returns X if Y' pattern."""
        checker = AssertionChecker()

        # Test zero pattern
        cases = checker._parse_returns_if_pattern("Returns 'zero' if zero")
        assert len(cases) > 0
        assert cases[0][0] == (0,)
        assert cases[0][1] == "zero"

        # Test negative pattern
        cases = checker._parse_returns_if_pattern("Returns 'negative' if negative")
        assert len(cases) > 0
        assert all(tc[0][0] < 0 for tc in cases)
        assert all(tc[1] == "negative" for tc in cases)


class TestGetTypeNameValidation:
    """
    Test validation of get_type_name function.

    This is the key test case - the bug that Phase 5a should catch.
    """

    def test_correct_get_type_name_passes(self):
        """Test that a correct get_type_name implementation passes validation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check the type of a value and return its name"),
            signature=SigClause(
                name="check_type",
                parameters=[Parameter(name="value", type_hint="Any")],
                returns="str",
            ),
            assertions=[
                AssertClause(predicate="Returns 'int' for integer inputs"),
                AssertClause(predicate="Returns 'str' for string inputs"),
                AssertClause(predicate="Returns 'list' for list inputs"),
                AssertClause(predicate="Returns 'other' for anything else"),
            ],
        )

        # CORRECT implementation
        code = """
def check_type(value):
    if isinstance(value, bool):
        return 'other'
    if isinstance(value, int):
        return 'int'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, list):
        return 'list'
    else:
        return 'other'
"""

        checker = AssertionChecker()
        result = checker.validate(code, "check_type", ir)

        assert result.passed, f"Validation failed: {result.issues}"

    def test_buggy_get_type_name_fails(self):
        """Test that buggy get_type_name (like Phase 4 v2) is caught."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check the type of a value and return its name"),
            signature=SigClause(
                name="check_type",
                parameters=[Parameter(name="value", type_hint="Any")],
                returns="str",
            ),
            assertions=[
                AssertClause(predicate="Returns 'int' for integer inputs"),
                AssertClause(predicate="Returns 'str' for string inputs"),
                AssertClause(predicate="Returns 'list' for list inputs"),
                AssertClause(predicate="Returns 'other' for anything else"),
            ],
        )

        # BUGGY implementation - missing bool check, returns 'int' for float/bool
        code = """
def check_type(value):
    if isinstance(value, int):
        return 'int'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, list):
        return 'list'
    else:
        return 'other'
"""

        checker = AssertionChecker()
        result = checker.validate(code, "check_type", ir)

        # Should fail because True (bool) will match isinstance(value, int)
        # and return 'int' instead of 'other'
        assert not result.passed
        assert len(result.issues) > 0

        # Check that the issue is about bool/edge case
        issue_messages = [issue.message for issue in result.issues]
        assert any("other" in msg and "int" in msg for msg in issue_messages) or any(
            "other" in msg for msg in issue_messages
        )

    def test_edge_case_generation_for_type_checker(self):
        """Test that edge cases are generated for type checking functions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check the type of a value and return its name"),
            signature=SigClause(
                name="check_type",
                parameters=[Parameter(name="value", type_hint="Any")],
                returns="str",
            ),
            assertions=[
                AssertClause(predicate="Returns 'int' for integer inputs"),
                AssertClause(predicate="Returns 'str' for string inputs"),
                AssertClause(predicate="Returns 'list' for list inputs"),
                AssertClause(predicate="Returns 'other' for anything else"),
            ],
        )

        checker = AssertionChecker()
        edge_cases = checker._generate_edge_cases(ir)

        # Should generate edge cases for types not covered
        assert len(edge_cases) > 0

        # Should include float, dict, None, bool
        input_values = [ec[0][0] for ec in edge_cases]
        input_types = [type(val).__name__ for val in input_values]

        assert "float" in input_types
        assert "dict" in input_types or "NoneType" in input_types
        assert "bool" in input_types

        # All should expect 'other'
        assert all(ec[1] == "other" for ec in edge_cases)


class TestControlFlowValidation:
    """Test validation of control flow logic."""

    def test_classify_number_validation(self):
        """Test validation of classify_number function."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Classify a number as zero, negative, or positive (even/odd)"
            ),
            signature=SigClause(
                name="classify_number",
                parameters=[Parameter(name="n", type_hint="int")],
                returns="str",
            ),
            assertions=[
                AssertClause(predicate="Returns 'zero' if zero"),
                AssertClause(predicate="Returns 'negative' if negative"),
                AssertClause(predicate="Returns 'positive even' if positive and even"),
                AssertClause(predicate="Returns 'positive odd' if positive and odd"),
            ],
        )

        # Correct implementation
        code = """
def classify_number(n):
    if n == 0:
        return 'zero'
    elif n < 0:
        return 'negative'
    elif n % 2 == 0:
        return 'positive even'
    else:
        return 'positive odd'
"""

        checker = AssertionChecker()
        result = checker.validate(code, "classify_number", ir)

        assert result.passed, f"Validation failed: {result.issues}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
