#!/usr/bin/env python3
"""Test the TestCaseGenerator on the 3 persistent failures."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.test_generator import TestCaseGenerator
from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


def test_count_words():
    """Test case generation for count_words."""
    print("\n" + "=" * 80)
    print("TEST 1: count_words - Test Case Generation")
    print("=" * 80)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Count the number of words in a string"),
        signature=SigClause(
            name="count_words",
            parameters=[Parameter(name="text", type_hint="str")],
            returns="int",
        ),
        effects=[
            EffectClause(description="Split input string by spaces into words list"),
            EffectClause(description="Count the number of elements"),
            EffectClause(description="Return the count"),
        ],
        assertions=[
            AssertClause(
                predicate="count is greater than or equal to 0",
                rationale="Word count cannot be negative",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    generator = TestCaseGenerator()
    test_cases = generator.generate_test_cases(ir)

    print(f"\nGenerated {len(test_cases)} test cases:")
    for i, tc in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {tc.description}")
        print(f"    Inputs: {tc.inputs}")
        print(f"    Expected: {tc.expected_output}")

    # Verify we have good test cases
    assert len(test_cases) > 0, "Should generate at least one test case"

    # Should have empty string test (edge case)
    empty_tests = [tc for tc in test_cases if tc.inputs.get("text") == ""]
    assert len(empty_tests) > 0, "Should have empty string test"
    assert empty_tests[0].expected_output == 0, "Empty string should expect 0"

    # Should have word count test
    word_tests = [tc for tc in test_cases if tc.inputs.get("text") in ["hello world", "hello"]]
    assert len(word_tests) > 0, "Should have word count tests"

    print("\n✅ count_words: Test generation successful!")
    return True


def test_find_index():
    """Test case generation for find_index."""
    print("\n" + "=" * 80)
    print("TEST 2: find_index - Test Case Generation")
    print("=" * 80)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Find FIRST index of value in list"),
        signature=SigClause(
            name="find_index",
            parameters=[
                Parameter(name="items", type_hint="list[int]"),
                Parameter(name="target", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="Use enumerate to iterate through list with indices"),
            EffectClause(description="Check if item equals target"),
            EffectClause(description="Return the index immediately when found"),
            EffectClause(description="Return -1 if not found"),
        ],
        assertions=[
            AssertClause(
                predicate="returned index is valid or -1",
                rationale="Index must be valid or -1 if not found",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    generator = TestCaseGenerator()
    test_cases = generator.generate_test_cases(ir)

    print(f"\nGenerated {len(test_cases)} test cases:")
    for i, tc in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {tc.description}")
        print(f"    Inputs: {tc.inputs}")
        print(f"    Expected: {tc.expected_output}")

    # Verify we have good test cases
    assert len(test_cases) > 0, "Should generate at least one test case"

    # Should have empty list test
    empty_tests = [tc for tc in test_cases if tc.inputs.get("items") == []]
    assert len(empty_tests) > 0, "Should have empty list test"
    assert empty_tests[0].expected_output == -1, "Empty list should expect -1"

    # Should have duplicate value test (CRITICAL for catching the bug!)
    dup_tests = [tc for tc in test_cases if tc.inputs.get("items") == [1, 2, 1]]
    assert len(dup_tests) > 0, "Should have duplicate value test to catch first/last bug"
    assert dup_tests[0].expected_output == 0, "Duplicate test should expect first index (0)"

    print("\n✅ find_index: Test generation successful!")
    print("   🎯 Generated critical test for first/last bug!")
    return True


def test_is_valid_email():
    """Test case generation for is_valid_email."""
    print("\n" + "=" * 80)
    print("TEST 3: is_valid_email - Test Case Generation")
    print("=" * 80)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Check if string is a valid email address"),
        signature=SigClause(
            name="is_valid_email",
            parameters=[Parameter(name="email", type_hint="str")],
            returns="bool",
        ),
        effects=[
            EffectClause(description="Check if email contains @ symbol"),
            EffectClause(description="Check if email contains . dot"),
            EffectClause(description="Check that dot comes after @"),
            EffectClause(description="Return True if all checks pass, False otherwise"),
        ],
        assertions=[
            AssertClause(
                predicate="result is True if email is valid format",
                rationale="Email must have @ and domain",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    generator = TestCaseGenerator()
    test_cases = generator.generate_test_cases(ir)

    print(f"\nGenerated {len(test_cases)} test cases:")
    for i, tc in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {tc.description}")
        print(f"    Inputs: {tc.inputs}")
        print(f"    Expected: {tc.expected_output}")

    # Verify we have good test cases
    assert len(test_cases) > 0, "Should generate at least one test case"

    # Should have valid email test
    valid_tests = [
        tc
        for tc in test_cases
        if "@" in str(tc.inputs.get("email", "")) and tc.expected_output is True
    ]
    assert len(valid_tests) > 0, "Should have valid email test"

    # Should have invalid email tests
    invalid_tests = [tc for tc in test_cases if tc.expected_output is False]
    assert len(invalid_tests) > 0, "Should have invalid email tests"

    # Should have test for dot immediately after @ (CRITICAL bug!)
    dot_after_at_tests = [tc for tc in test_cases if "test@.com" in str(tc.inputs.get("email", ""))]
    assert len(dot_after_at_tests) > 0, "Should have test for dot immediately after @"
    assert dot_after_at_tests[0].expected_output is False, "test@.com should be invalid"

    print("\n✅ is_valid_email: Test generation successful!")
    print("   🎯 Generated critical tests for email validation edge cases!")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("TestCaseGenerator: Testing on 3 Persistent Failures")
    print("=" * 80)
    print("\nGoal: Generate test cases that would catch the bugs")

    results = {
        "count_words": test_count_words(),
        "find_index": test_find_index(),
        "is_valid_email": test_is_valid_email(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {test_name}: {status}")

    total = sum(results.values())
    print(f"\nTotal: {total}/3 test generators working ({total / 3 * 100:.0f}%)")

    if total == 3:
        print("\n🎉 SUCCESS! TestCaseGenerator works correctly!")
        print("\n   All 3 generators created tests that would catch the bugs:")
        print("   - count_words: Tests for empty string and word counts")
        print("   - find_index: Tests for duplicates (catches first/last bug!)")
        print("   - is_valid_email: Tests for dot position (catches validation bug!)")
        return 0
    else:
        print("\n❌ FAILURE: Some test generators didn't work correctly")
        return 1


if __name__ == "__main__":
    sys.exit(main())
