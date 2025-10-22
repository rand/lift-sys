"""Tests for EquivalenceChecker."""

import math
import subprocess

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.robustness import EquivalenceChecker


class TestIntentEquivalence:
    """Tests for intent semantic similarity."""

    def test_identical_intents(self):
        """Identical intents should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._intents_equivalent(
            "Sort numbers in ascending order",
            "Sort numbers in ascending order",
        )

    def test_semantically_similar_intents(self):
        """Semantically similar intents should be equivalent."""
        checker = EquivalenceChecker(intent_similarity_threshold=0.85)
        assert checker._intents_equivalent(
            "Sort a list of numbers",
            "Order a list of numbers",
        )

    def test_different_intents(self):
        """Semantically different intents should not be equivalent."""
        checker = EquivalenceChecker()
        assert not checker._intents_equivalent(
            "Sort numbers in ascending order",
            "Calculate the sum of numbers",
        )

    def test_empty_intents(self):
        """Empty intents should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._intents_equivalent("", "")

    def test_paraphrased_intents(self):
        """Paraphrased intents should be equivalent."""
        checker = EquivalenceChecker(intent_similarity_threshold=0.85)
        assert checker._intents_equivalent(
            "Create a function that validates email addresses",
            "Write a function to validate email addresses",
        )


class TestSignatureEquivalence:
    """Tests for signature comparison."""

    def test_identical_signatures(self):
        """Identical signatures should be equivalent."""
        checker = EquivalenceChecker()
        sig1 = SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="nums", type_hint="list[int]")],
            returns="list[int]",
        )
        sig2 = SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="nums", type_hint="list[int]")],
            returns="list[int]",
        )
        assert checker._signatures_equivalent(sig1, sig2)

    def test_different_naming_styles_with_normalization(self):
        """Different naming styles should be equivalent with normalization."""
        checker = EquivalenceChecker(normalize_naming=True)
        sig1 = SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="input_list", type_hint="list[int]")],
            returns="list[int]",
        )
        sig2 = SigClause(
            name="sortNumbers",
            parameters=[Parameter(name="inputList", type_hint="list[int]")],
            returns="list[int]",
        )
        assert checker._signatures_equivalent(sig1, sig2)

    def test_different_naming_styles_without_normalization(self):
        """Different naming styles should not be equivalent without normalization."""
        checker = EquivalenceChecker(normalize_naming=False)
        sig1 = SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="input_list", type_hint="list[int]")],
            returns="list[int]",
        )
        sig2 = SigClause(
            name="sortNumbers",
            parameters=[Parameter(name="inputList", type_hint="list[int]")],
            returns="list[int]",
        )
        assert not checker._signatures_equivalent(sig1, sig2)

    def test_different_return_types(self):
        """Different return types should not be equivalent."""
        checker = EquivalenceChecker()
        sig1 = SigClause(
            name="process",
            parameters=[],
            returns="int",
        )
        sig2 = SigClause(
            name="process",
            parameters=[],
            returns="str",
        )
        assert not checker._signatures_equivalent(sig1, sig2)

    def test_different_parameter_counts(self):
        """Different parameter counts should not be equivalent."""
        checker = EquivalenceChecker()
        sig1 = SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        )
        sig2 = SigClause(
            name="add",
            parameters=[Parameter(name="a", type_hint="int")],
            returns="int",
        )
        assert not checker._signatures_equivalent(sig1, sig2)

    def test_different_parameter_types(self):
        """Different parameter types should not be equivalent."""
        checker = EquivalenceChecker()
        sig1 = SigClause(
            name="process",
            parameters=[Parameter(name="data", type_hint="int")],
            returns="int",
        )
        sig2 = SigClause(
            name="process",
            parameters=[Parameter(name="data", type_hint="str")],
            returns="int",
        )
        assert not checker._signatures_equivalent(sig1, sig2)

    def test_complex_naming_normalization(self):
        """Complex naming conversions should work correctly."""
        checker = EquivalenceChecker(normalize_naming=True)
        sig1 = SigClause(
            name="ProcessUserData",  # PascalCase
            parameters=[
                Parameter(name="user_id", type_hint="int"),  # snake_case
                Parameter(name="dataSource", type_hint="str"),  # camelCase
            ],
            returns="dict",
        )
        sig2 = SigClause(
            name="process_user_data",  # snake_case
            parameters=[
                Parameter(name="userId", type_hint="int"),  # camelCase
                Parameter(name="data_source", type_hint="str"),  # snake_case
            ],
            returns="dict",
        )
        assert checker._signatures_equivalent(sig1, sig2)


class TestEffectEquivalence:
    """Tests for effect comparison."""

    def test_identical_effects_order_matters(self):
        """Identical effects should be equivalent when order matters."""
        checker = EquivalenceChecker(check_effect_order=True)
        effects1 = [
            EffectClause(description="Read file input.txt"),
            EffectClause(description="Write to database"),
        ]
        effects2 = [
            EffectClause(description="Read file input.txt"),
            EffectClause(description="Write to database"),
        ]
        assert checker._effects_equivalent(effects1, effects2)

    def test_reordered_effects_order_matters(self):
        """Reordered effects should not be equivalent when order matters."""
        checker = EquivalenceChecker(check_effect_order=True)
        effects1 = [
            EffectClause(description="Read file input.txt"),
            EffectClause(description="Write to database"),
        ]
        effects2 = [
            EffectClause(description="Write to database"),
            EffectClause(description="Read file input.txt"),
        ]
        assert not checker._effects_equivalent(effects1, effects2)

    def test_reordered_effects_order_doesnt_matter(self):
        """Reordered effects should be equivalent when order doesn't matter."""
        checker = EquivalenceChecker(check_effect_order=False)
        effects1 = [
            EffectClause(description="Read file input.txt"),
            EffectClause(description="Write to database"),
        ]
        effects2 = [
            EffectClause(description="Write to database"),
            EffectClause(description="Read file input.txt"),
        ]
        assert checker._effects_equivalent(effects1, effects2)

    def test_different_effect_counts(self):
        """Different effect counts should not be equivalent."""
        checker = EquivalenceChecker()
        effects1 = [EffectClause(description="Read file")]
        effects2 = [
            EffectClause(description="Read file"),
            EffectClause(description="Write file"),
        ]
        assert not checker._effects_equivalent(effects1, effects2)

    def test_empty_effects(self):
        """Empty effect lists should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._effects_equivalent([], [])


class TestAssertionEquivalence:
    """Tests for assertion comparison."""

    def test_identical_assertions(self):
        """Identical assertions should be equivalent."""
        checker = EquivalenceChecker()
        assertions1 = [AssertClause(predicate="result > 0")]
        assertions2 = [AssertClause(predicate="result > 0")]
        assert checker._assertions_equivalent(assertions1, assertions2)

    def test_reordered_assertions(self):
        """Reordered assertions should be equivalent (sets comparison)."""
        checker = EquivalenceChecker()
        assertions1 = [
            AssertClause(predicate="result > 0"),
            AssertClause(predicate="len(result) < 100"),
        ]
        assertions2 = [
            AssertClause(predicate="len(result) < 100"),
            AssertClause(predicate="result > 0"),
        ]
        assert checker._assertions_equivalent(assertions1, assertions2)

    def test_different_assertions(self):
        """Different assertions should not be equivalent."""
        checker = EquivalenceChecker()
        assertions1 = [AssertClause(predicate="result > 0")]
        assertions2 = [AssertClause(predicate="result < 0")]
        assert not checker._assertions_equivalent(assertions1, assertions2)

    def test_empty_assertions(self):
        """Empty assertion lists should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._assertions_equivalent([], [])


class TestIREquivalence:
    """Tests for full IR equivalence."""

    def test_identical_irs(self, sample_ir):
        """Identical IRs should be equivalent."""
        checker = EquivalenceChecker()
        assert checker.ir_equivalent(sample_ir, sample_ir)

    def test_irs_with_different_naming(self):
        """IRs with different naming should be equivalent with normalization."""
        checker = EquivalenceChecker(normalize_naming=True)

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sort_numbers",
                parameters=[Parameter(name="nums", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(
                name="sortNumbers",
                parameters=[Parameter(name="nums", type_hint="list[int]")],
                returns="list[int]",
            ),
            effects=[],
            assertions=[],
        )

        assert checker.ir_equivalent(ir1, ir2)

    def test_irs_with_reordered_effects(self):
        """IRs with reordered effects should be equivalent."""
        checker = EquivalenceChecker(check_effect_order=False)

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[
                EffectClause(description="Read file"),
                EffectClause(description="Write database"),
            ],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns="None"),
            effects=[
                EffectClause(description="Write database"),
                EffectClause(description="Read file"),
            ],
            assertions=[],
        )

        assert checker.ir_equivalent(ir1, ir2)

    def test_irs_with_different_intents(self):
        """IRs with different intents should not be equivalent."""
        checker = EquivalenceChecker()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Sort numbers"),
            signature=SigClause(name="sort", parameters=[], returns="list"),
            effects=[],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Sum numbers"),
            signature=SigClause(name="sort", parameters=[], returns="list"),
            effects=[],
            assertions=[],
        )

        assert not checker.ir_equivalent(ir1, ir2)


class TestCodeEquivalence:
    """Tests for code functional equivalence."""

    def test_identical_code(self):
        """Identical code should be equivalent."""
        checker = EquivalenceChecker()
        code = """
def add(a, b):
    return a + b
"""
        test_inputs = [{"a": 1, "b": 2}, {"a": 0, "b": 0}, {"a": -5, "b": 10}]
        assert checker.code_equivalent(code, code, test_inputs)

    def test_functionally_equivalent_code(self):
        """Functionally equivalent code should be equivalent."""
        checker = EquivalenceChecker()

        code1 = """
def sort_numbers(nums):
    return sorted(nums)
"""

        code2 = """
def sort_numbers(nums):
    result = list(nums)
    result.sort()
    return result
"""

        test_inputs = [
            {"nums": [3, 1, 4, 1, 5]},
            {"nums": []},
            {"nums": [1]},
            {"nums": [5, 4, 3, 2, 1]},
        ]

        assert checker.code_equivalent(code1, code2, test_inputs)

    def test_different_implementations_same_result(self):
        """Different implementations with same result should be equivalent."""
        checker = EquivalenceChecker()

        code1 = """
def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""

        code2 = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

        test_inputs = [{"n": 0}, {"n": 1}, {"n": 5}, {"n": 10}]

        assert checker.code_equivalent(code1, code2, test_inputs)

    def test_different_outputs(self):
        """Code with different outputs should not be equivalent."""
        checker = EquivalenceChecker()

        code1 = """
def add(a, b):
    return a + b
"""

        code2 = """
def add(a, b):
    return a - b
"""

        test_inputs = [{"a": 1, "b": 2}]

        assert not checker.code_equivalent(code1, code2, test_inputs)

    def test_code_with_errors(self):
        """Code that raises errors should not be equivalent to working code."""
        checker = EquivalenceChecker()

        code1 = """
def divide(a, b):
    return a / b
"""

        code2 = """
def divide(a, b):
    return a // b
"""

        # This will cause division by zero in code1
        test_inputs = [{"a": 10, "b": 0}]

        assert not checker.code_equivalent(code1, code2, test_inputs)

    def test_empty_test_inputs(self):
        """Empty test inputs should return False."""
        checker = EquivalenceChecker()
        code = "def foo(): pass"
        assert not checker.code_equivalent(code, code, [])

    def test_floating_point_tolerance(self):
        """Floating point results should use tolerance comparison."""
        checker = EquivalenceChecker()

        code1 = """
def average(nums):
    return sum(nums) / len(nums)
"""

        code2 = """
def average(nums):
    total = 0.0
    for num in nums:
        total += num
    return total / len(nums)
"""

        test_inputs = [{"nums": [1, 2, 3]}, {"nums": [10.5, 20.3, 15.7]}]

        assert checker.code_equivalent(code1, code2, test_inputs)


class TestCodeExecution:
    """Tests for code execution helper methods."""

    def test_extract_function_name(self):
        """Should extract function name from code."""
        checker = EquivalenceChecker()

        code = """
def my_function(x, y):
    return x + y
"""
        assert checker._extract_function_name(code) == "my_function"

    def test_extract_function_name_complex(self):
        """Should extract function name from complex code."""
        checker = EquivalenceChecker()

        code = """
# Comment
import os

def process_data(items):
    '''Docstring'''
    return [x * 2 for x in items]
"""
        assert checker._extract_function_name(code) == "process_data"

    def test_extract_function_name_no_function(self):
        """Should return None for code without function definition."""
        checker = EquivalenceChecker()

        code = "x = 1 + 2"
        assert checker._extract_function_name(code) is None

    def test_outputs_equivalent_exact_match(self):
        """Exact matches should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._outputs_equivalent(42, 42)
        assert checker._outputs_equivalent("hello", "hello")
        assert checker._outputs_equivalent([1, 2, 3], [1, 2, 3])

    def test_outputs_equivalent_floats(self):
        """Floats within tolerance should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._outputs_equivalent(3.14159, 3.14159)
        assert checker._outputs_equivalent(1.0000001, 1.0000002)
        assert not checker._outputs_equivalent(1.0, 1.1)

    def test_outputs_equivalent_lists(self):
        """Lists with same elements should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._outputs_equivalent([1, 2, 3], [1, 2, 3])
        assert not checker._outputs_equivalent([1, 2, 3], [1, 2, 3, 4])

    def test_outputs_equivalent_dicts(self):
        """Dicts with same key-value pairs should be equivalent."""
        checker = EquivalenceChecker()
        assert checker._outputs_equivalent({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert checker._outputs_equivalent({"a": 1, "b": 2}, {"b": 2, "a": 1})
        assert not checker._outputs_equivalent({"a": 1}, {"a": 2})

    def test_outputs_equivalent_nested(self):
        """Nested structures should be compared recursively."""
        checker = EquivalenceChecker()
        output1 = {"data": [1, 2, 3], "meta": {"count": 3}}
        output2 = {"data": [1, 2, 3], "meta": {"count": 3}}
        assert checker._outputs_equivalent(output1, output2)


class TestNamingNormalization:
    """Tests for naming style normalization."""

    def test_normalize_snake_case(self):
        """Should normalize to snake_case."""
        checker = EquivalenceChecker()
        assert checker._normalize_name("sortNumbers") == "sort_numbers"
        assert checker._normalize_name("ProcessUserData") == "process_user_data"
        assert checker._normalize_name("CONSTANT_VALUE") == "constant_value"

    def test_normalize_already_snake_case(self):
        """Already snake_case names should remain unchanged."""
        checker = EquivalenceChecker()
        assert checker._normalize_name("sort_numbers") == "sort_numbers"
        assert checker._normalize_name("process_data") == "process_data"

    def test_normalize_single_word(self):
        """Single word names should be lowercased."""
        checker = EquivalenceChecker()
        assert checker._normalize_name("Sort") == "sort"
        assert checker._normalize_name("process") == "process"
        assert checker._normalize_name("DATA") == "data"


# Integration tests
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_ir_equivalent_with_none_returns(self):
        """IRs with None returns should be equivalent."""
        checker = EquivalenceChecker()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns=None),
            effects=[],
            assertions=[],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(name="process", parameters=[], returns=None),
            effects=[],
            assertions=[],
        )

        assert checker.ir_equivalent(ir1, ir2)

    def test_code_execution_timeout(self):
        """Code that times out should raise an error."""
        checker = EquivalenceChecker()

        code_infinite_loop = """
def infinite_loop():
    while True:
        pass
"""

        test_inputs = [{}]

        # Should not be equivalent due to timeout
        with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
            checker._execute_code(code_infinite_loop, {}, timeout_seconds=1)

    def test_code_with_no_function_definition(self):
        """Code without function definition should fail gracefully."""
        checker = EquivalenceChecker()

        code_no_func = "x = 1 + 2"

        test_inputs = [{}]

        with pytest.raises(RuntimeError):
            checker._execute_code(code_no_func, {}, timeout_seconds=5)

    def test_outputs_equivalent_with_nan(self):
        """NaN values should not be equivalent."""
        checker = EquivalenceChecker()
        # NaN is not equal to itself in standard comparison
        assert not checker._outputs_equivalent(math.nan, math.nan)

    def test_outputs_equivalent_different_types(self):
        """Different types should not be equivalent (except list/tuple)."""
        checker = EquivalenceChecker()
        assert not checker._outputs_equivalent(1, "1")
        assert not checker._outputs_equivalent({"a": 1}, [("a", 1)])
        assert not checker._outputs_equivalent([1, 2], "1, 2")

    def test_outputs_equivalent_list_with_mixed_types(self):
        """Lists with mixed types should be compared correctly."""
        checker = EquivalenceChecker()
        # Should work for exact matches
        assert checker._outputs_equivalent([1, "a", 2.5], [1, "a", 2.5])
        # Should fail for different values
        assert not checker._outputs_equivalent([1, "a"], [1, "b"])


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_end_to_end_ir_equivalence(self):
        """Full IR comparison with multiple transformations."""
        checker = EquivalenceChecker(
            normalize_naming=True,
            check_effect_order=False,
        )

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email addresses using regex"),
            signature=SigClause(
                name="validate_email",
                parameters=[
                    Parameter(name="email_address", type_hint="str"),
                ],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Check regex pattern"),
                EffectClause(description="Return validation result"),
            ],
            assertions=[
                AssertClause(predicate="result is boolean"),
            ],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email addresses using regex"),
            signature=SigClause(
                name="validateEmail",  # Different naming style
                parameters=[
                    Parameter(name="emailAddress", type_hint="str"),  # Different naming
                ],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Return validation result"),  # Reordered
                EffectClause(description="Check regex pattern"),
            ],
            assertions=[
                AssertClause(predicate="result is boolean"),
            ],
        )

        assert checker.ir_equivalent(ir1, ir2)

    def test_end_to_end_code_equivalence(self):
        """Full code equivalence with different implementations."""
        checker = EquivalenceChecker()

        code1 = """
def is_palindrome(s):
    s = s.lower().replace(" ", "")
    return s == s[::-1]
"""

        code2 = """
def is_palindrome(s):
    s = s.lower().replace(" ", "")
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True
"""

        test_inputs = [
            {"s": "racecar"},
            {"s": "hello"},
            {"s": "A man a plan a canal Panama"},
            {"s": ""},
            {"s": "a"},
        ]

        assert checker.code_equivalent(code1, code2, test_inputs)
