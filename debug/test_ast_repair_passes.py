#!/usr/bin/env python3
"""Quick test of AST repair passes on the 3 failure patterns."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.ast_repair import ASTRepairEngine


def test_missing_return():
    """Test Pass 5: Missing return statement (count_words pattern)."""
    print("\n" + "=" * 80)
    print("TEST 1: Missing Return Statement (count_words)")
    print("=" * 80)

    buggy_code = """def count_words(text: str) -> int:
    words = text.split()
    len(words)
"""

    print("\nBuggy code:")
    print(buggy_code)

    engine = ASTRepairEngine()
    repaired = engine.repair(buggy_code, "count_words")

    if repaired:
        print("\n✅ Repaired code:")
        print(repaired)

        # Verify it works
        exec_namespace = {}
        exec(repaired, exec_namespace)
        func = exec_namespace["count_words"]

        result = func("hello world")
        print(f"\nTest: count_words('hello world') = {result}")
        assert result == 2, f"Expected 2, got {result}"
        print("✅ TEST PASSED")
        return True
    else:
        print("\n❌ No repairs applied")
        return False


def test_enumerate_early_return():
    """Test Pass 7: Enumerate early return (find_index pattern)."""
    print("\n" + "=" * 80)
    print("TEST 2: Enumerate Early Return (find_index)")
    print("=" * 80)

    buggy_code = """def find_index(items: list[int], target: int) -> int:
    result = -1
    for i, item in enumerate(items):
        if item == target:
            result = i
    return result
"""

    print("\nBuggy code:")
    print(buggy_code)

    engine = ASTRepairEngine()
    repaired = engine.repair(buggy_code, "find_index")

    if repaired:
        print("\n✅ Repaired code:")
        print(repaired)

        # Verify it works
        exec_namespace = {}
        exec(repaired, exec_namespace)
        func = exec_namespace["find_index"]

        # Test with duplicate values (should return FIRST occurrence)
        result = func([1, 2, 1], 1)
        print(f"\nTest: find_index([1, 2, 1], 1) = {result}")
        assert result == 0, f"Expected 0 (first occurrence), got {result}"
        print("✅ TEST PASSED")
        return True
    else:
        print("\n❌ No repairs applied")
        return False


def test_email_validation_adjacency():
    """Test Pass 6: Email validation adjacency (is_valid_email pattern)."""
    print("\n" + "=" * 80)
    print("TEST 3: Email Validation Adjacency (is_valid_email)")
    print("=" * 80)

    buggy_code = """def is_valid_email(email: str) -> bool:
    if '@' not in email or '.' not in email:
        return False
    if email.index('@') > email.rindex('.'):
        return False
    return True
"""

    print("\nBuggy code:")
    print(buggy_code)

    engine = ASTRepairEngine()
    repaired = engine.repair(buggy_code, "is_valid_email")

    if repaired:
        print("\n✅ Repaired code:")
        print(repaired)

        # Verify it works
        exec_namespace = {}
        exec(repaired, exec_namespace)
        func = exec_namespace["is_valid_email"]

        # Test with adjacency bug case
        result = func("test@.com")
        print(f"\nTest: is_valid_email('test@.com') = {result}")
        assert result is False, f"Expected False (dot adjacent to @), got {result}"
        print("✅ TEST PASSED")
        return True
    else:
        print("\n❌ No repairs applied")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("AST Repair Pass Testing - 3 Failure Patterns")
    print("=" * 80)

    results = {
        "Missing Return": test_missing_return(),
        "Enumerate Early Return": test_enumerate_early_return(),
        "Email Adjacency": test_email_validation_adjacency(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")

    total = sum(results.values())
    print(f"\nTotal: {total}/3 tests passed ({total / 3 * 100:.0f}%)")

    if total == 3:
        print("\n🎉 SUCCESS! All AST repair passes working correctly!")
        return 0
    else:
        print(f"\n❌ FAILURE: {3 - total} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
