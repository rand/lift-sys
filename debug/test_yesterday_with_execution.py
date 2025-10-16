#!/usr/bin/env python3
"""
Re-run yesterday's 5 tests with execution validation.

This compares the original Day 1 results (compilation only)
with today's results (compilation + execution with fix).
"""

import asyncio

from run_execution_validation import run_benchmark_with_execution

# Yesterday's 5 test cases with execution validation added
YESTERDAY_TESTS_WITH_EXECUTION = [
    {
        "name": "add_numbers",
        "prompt": "Create a function that adds two numbers",
        "category": "arithmetic",
        "function_name": "add_two_numbers",
        "test_cases": [
            ((2, 3), 5),
            ((10, 20), 30),
            ((0, 0), 0),
        ],
    },
    {
        "name": "multiply",
        "prompt": "Create a function that multiplies two numbers",
        "category": "arithmetic",
        "function_name": "multiply",
        "test_cases": [
            ((2, 3), 6),
            ((10, 5), 50),
            ((0, 10), 0),
        ],
    },
    {
        "name": "string_length",
        "prompt": "Create a function that returns the length of a string",
        "category": "string",
        "function_name": "get_string_length",
        "test_cases": [
            (("hello",), 5),
            (("",), 0),
        ],
    },
    {
        "name": "max_of_two",
        "prompt": "Create a function that returns the maximum of two numbers",
        "category": "boolean",
        "function_name": "max_of_two",
        "test_cases": [
            ((5, 10), 10),
            ((20, 15), 20),
            ((5, 5), 5),
        ],
    },
    {
        "name": "is_even",
        "prompt": "Create a function that checks if a number is even",
        "category": "boolean",
        "function_name": "is_even",
        "test_cases": [
            ((2,), True),
            ((3,), False),
            ((0,), True),
        ],
    },
]


async def main():
    """Re-run yesterday's tests with execution validation."""

    print("\n" + "=" * 60)
    print("RE-VALIDATION: Yesterday's 5 Tests")
    print("=" * 60)
    print("Original Day 1 Results (compilation only):")
    print("  - 4/5 tests compiled successfully (80%)")
    print("  - max_of_two failed with indentation bug")
    print("")
    print("Today's Re-run (with return statement fix + execution):")
    print("  - Testing compilation AND execution")
    print("  - Using fixed XGrammarCodeGenerator")
    print("=" * 60)

    results, summary = await run_benchmark_with_execution(YESTERDAY_TESTS_WITH_EXECUTION)

    # Compare to yesterday
    print("\n" + "=" * 60)
    print("COMPARISON: Day 1 vs Day 2 (with fix)")
    print("=" * 60)

    print("\nDay 1 Results (compilation only, no fix):")
    print("  Compilation success: 4/5 (80%)")
    print("  Execution success:   UNKNOWN (not tested)")
    print("  Known issues:")
    print("    - Missing return statements (discovered today)")
    print("    - Indentation bug (max_of_two failed)")

    print("\nDay 2 Results (with return statement fix):")
    print(
        f"  Compilation success: {summary['compilation_success']}/5 ({summary['compilation_rate'] * 100:.1f}%)"
    )
    print(
        f"  Execution success:   {summary['execution_success']}/5 ({summary['execution_rate'] * 100:.1f}%)"
    )

    # Calculate improvement
    if summary["execution_rate"] == 1.0:
        print("\n✅ PERFECT: 100% execution success!")
        print("   Return statement fix completely resolved the issue")
    elif summary["execution_rate"] >= 0.8:
        print(f"\n✅ EXCELLENT: {summary['execution_rate'] * 100:.0f}% execution success")
        print("   Return statement fix working well")
    elif summary["execution_rate"] >= 0.6:
        print(f"\n✅ GOOD: {summary['execution_rate'] * 100:.0f}% execution success")
        print("   Return statement fix helped, but other issues remain")
    else:
        print(f"\n⚠️  NEEDS WORK: {summary['execution_rate'] * 100:.0f}% execution success")
        print("   Additional issues beyond return statements")

    # Analyze failures
    failures = [r for r in results if not r.execution_success]
    if failures:
        print(f"\nFailed tests ({len(failures)}):")
        for r in failures:
            print(f"  - {r.test_name}: ", end="")
            if not r.end_to_end_success:
                print("Compilation failed")
            elif r.execution_tests:
                failed_tests = [t for t in r.execution_tests if not t.passed]
                if failed_tests:
                    print(f"{len(failed_tests)} execution test(s) failed")
                    for t in failed_tests[:2]:  # Show first 2
                        print(f"      {t.error}")
            else:
                print("No execution tests run")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
