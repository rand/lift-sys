#!/usr/bin/env python3
"""Test the ExecutionValidator."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.execution_validator import ExecutionValidator
from lift_sys.codegen.test_generator import TestCase


def test_good_code():
    """Test validation with correct code."""
    print("\n" + "=" * 80)
    print("TEST 1: Good Code - Should Pass")
    print("=" * 80)

    code = """
def count_words(text: str) -> int:
    words = text.split()
    return len(words)
"""

    test_cases = [
        TestCase(inputs={"text": ""}, expected_output=0, description="empty string"),
        TestCase(inputs={"text": "hello world"}, expected_output=2, description="two words"),
        TestCase(inputs={"text": "hello"}, expected_output=1, description="one word"),
    ]

    validator = ExecutionValidator()
    result = validator.validate(code, "count_words", test_cases)

    print(f"\nResult: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print(f"Tests: {result.total_tests - len(result.failed_tests)}/{result.total_tests} passed")

    if result.failed_tests:
        print("\nFailed tests:")
        for failed in result.failed_tests:
            print(f"  - {failed.test_case.description}: {failed.error_message}")

    assert result.passed, "Good code should pass all tests"
    print("\n✅ Test passed: Good code validated successfully!")
    return True


def test_missing_return():
    """Test detection of missing return statement."""
    print("\n" + "=" * 80)
    print("TEST 2: Missing Return - Should Fail")
    print("=" * 80)

    code = """
def count_words(text: str) -> int:
    words = text.split()
    count = len(words)
    # BUG: Missing return statement!
"""

    test_cases = [
        TestCase(inputs={"text": "hello world"}, expected_output=2, description="two words"),
    ]

    validator = ExecutionValidator()
    result = validator.validate(code, "count_words", test_cases)

    print(f"\nResult: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print(f"Tests: {result.total_tests - len(result.failed_tests)}/{result.total_tests} passed")

    if result.failed_tests:
        print("\nFailed tests:")
        for failed in result.failed_tests:
            print(f"  - {failed.test_case.description}")
            print(f"    {failed.error_message}")

    if result.error_summary:
        print("\n📋 Error Summary for Regeneration:")
        print(result.error_summary)

    assert not result.passed, "Code with missing return should fail"
    assert len(result.failed_tests) == 1, "Should have 1 failed test"
    assert "None" in result.failed_tests[0].error_message, "Should mention None output"

    print("\n✅ Test passed: Missing return detected correctly!")
    return True


def test_wrong_output():
    """Test detection of wrong output (first/last bug)."""
    print("\n" + "=" * 80)
    print("TEST 3: Wrong Output (First/Last Bug) - Should Fail")
    print("=" * 80)

    code = """
def find_index(items: list, target: int) -> int:
    result = -1
    for i, item in enumerate(items):
        if item == target:
            result = i  # BUG: Should return immediately, not store!
    return result  # Returns LAST occurrence, not FIRST
"""

    test_cases = [
        TestCase(
            inputs={"items": [1, 2, 1], "target": 1},
            expected_output=0,
            description="Should return FIRST occurrence at index 0, not last",
        ),
    ]

    validator = ExecutionValidator()
    result = validator.validate(code, "find_index", test_cases)

    print(f"\nResult: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print(f"Tests: {result.total_tests - len(result.failed_tests)}/{result.total_tests} passed")

    if result.failed_tests:
        print("\nFailed tests:")
        for failed in result.failed_tests:
            print(f"  - {failed.test_case.description}")
            print(f"    Expected: {failed.test_case.expected_output}")
            print(f"    Got: {failed.actual_output}")

    if result.error_summary:
        print("\n📋 Error Summary for Regeneration:")
        print(result.error_summary)

    assert not result.passed, "Code with first/last bug should fail"
    assert len(result.failed_tests) == 1, "Should have 1 failed test"
    assert result.failed_tests[0].actual_output == 2, "Should have returned 2 (last index)"

    print("\n✅ Test passed: First/last bug detected correctly!")
    return True


def test_invalid_email():
    """Test detection of invalid email validation."""
    print("\n" + "=" * 80)
    print("TEST 4: Invalid Email Validation - Should Fail")
    print("=" * 80)

    code = """
def is_valid_email(email: str) -> bool:
    # BUG: Doesn't check that dot comes AFTER @
    has_at = '@' in email
    has_dot = '.' in email
    return has_at and has_dot
"""

    test_cases = [
        TestCase(
            inputs={"email": "test@.com"},
            expected_output=False,
            description="dot immediately after @ should be invalid",
        ),
    ]

    validator = ExecutionValidator()
    result = validator.validate(code, "is_valid_email", test_cases)

    print(f"\nResult: {'✅ PASSED' if result.passed else '❌ FAILED'}")
    print(f"Tests: {result.total_tests - len(result.failed_tests)}/{result.total_tests} passed")

    if result.failed_tests:
        print("\nFailed tests:")
        for failed in result.failed_tests:
            print(f"  - {failed.test_case.description}")
            print(f"    Expected: {failed.test_case.expected_output}")
            print(f"    Got: {failed.actual_output}")

    if result.error_summary:
        print("\n📋 Error Summary for Regeneration:")
        print(result.error_summary)

    assert not result.passed, "Code with email validation bug should fail"
    assert len(result.failed_tests) == 1, "Should have 1 failed test"
    assert result.failed_tests[0].actual_output is True, "Should have returned True (incorrect)"

    print("\n✅ Test passed: Email validation bug detected correctly!")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("ExecutionValidator: Testing Code Validation")
    print("=" * 80)
    print("\nGoal: Validate that ExecutionValidator correctly detects bugs")

    results = {
        "good_code": test_good_code(),
        "missing_return": test_missing_return(),
        "wrong_output": test_wrong_output(),
        "invalid_email": test_invalid_email(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {test_name}: {status}")

    total = sum(results.values())
    print(f"\nTotal: {total}/4 validators working ({total / 4 * 100:.0f}%)")

    if total == 4:
        print("\n🎉 SUCCESS! ExecutionValidator works correctly!")
        print("\n   Key capabilities demonstrated:")
        print("   - Executes code safely in restricted environment")
        print("   - Detects missing return statements")
        print("   - Detects incorrect outputs (first/last bug)")
        print("   - Detects validation logic errors")
        print("   - Provides helpful error summaries for regeneration")
        return 0
    else:
        print("\n❌ FAILURE: Some validation tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
