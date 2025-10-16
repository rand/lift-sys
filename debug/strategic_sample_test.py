#!/usr/bin/env python3
"""
Strategic 8-test sample focusing on categories most likely to fail.

Focus areas:
- Boolean logic (expected 60% - indentation bug)
- Edge cases (expected 70%)
- Plus 2 baseline tests (arithmetic, string) for comparison
"""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark
from run_expanded_benchmark import analyze_by_category, print_category_analysis


async def main():
    """Run strategic 8-test sample."""

    print("\n🎯 Strategic Sample Test (8 tests, ~2 minutes)")
    print("Focus: Boolean logic and edge cases (most likely to fail)")
    print("=" * 60)

    # Strategic sample
    test_cases = [
        # 2 baseline (should pass)
        ("add_numbers", "Create a function that adds two numbers"),
        ("string_length", "Create a function that returns the length of a string"),
        # 4 boolean logic (test indentation bug - expected 60% success)
        ("is_even", "Create a function that checks if a number is even"),
        ("is_positive", "Create a function that checks if a number is positive"),
        ("max_of_two", "Create a function that returns the maximum of two numbers"),
        ("min_of_two", "Create a function that returns the minimum of two numbers"),
        # 2 edge cases (test error handling - expected 70% success)
        (
            "safe_divide",
            "Create a function that divides two numbers and returns zero if the divisor is zero",
        ),
        (
            "default_value",
            "Create a function that returns a value or a default if the value is None",
        ),
    ]

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    # Run tests
    summary = await benchmark.run_benchmark_suite(
        test_cases=test_cases,
        warmup_runs=0,  # Modal already warm
    )

    # Analyze by category
    category_stats = analyze_by_category(benchmark)
    print_category_analysis(category_stats)

    # Specific insights
    print("\n" + "=" * 60)
    print("KEY INSIGHTS")
    print("=" * 60)

    boolean_stats = category_stats.get("boolean", {})
    if boolean_stats:
        boolean_rate = boolean_stats["success_rate"]
        print(f"\n🔍 Boolean Logic: {boolean_rate * 100:.1f}% success")
        if boolean_rate < 0.6:
            print("   ⚠️  BELOW expectation - indentation bug confirmed")
        elif boolean_rate >= 0.75:
            print("   ✅ ABOVE expectation - indentation bug may be fixed/intermittent")
        else:
            print("   ✓  Meets expectation - consistent with known issue")

    edge_stats = category_stats.get("edge_case", {})
    if edge_stats:
        edge_rate = edge_stats["success_rate"]
        print(f"\n🔍 Edge Cases: {edge_rate * 100:.1f}% success")
        if edge_rate >= 0.7:
            print("   ✅ Meets expectation - error handling prompts work")
        else:
            print("   ⚠️  BELOW expectation - may need clearer prompts")

    overall_rate = summary.successful_runs / summary.total_runs
    print(f"\n📊 Overall: {overall_rate * 100:.1f}% success")
    if overall_rate >= 0.75:
        print("   ✅ Strong MVP viability (>75%)")
    elif overall_rate >= 0.60:
        print("   ⚠️  Acceptable but needs improvement (60-75%)")
    else:
        print("   ❌ Below MVP threshold (<60%)")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
