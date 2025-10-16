#!/usr/bin/env python3
"""
Run Expanded Benchmark Suite with Category Analysis

This script runs the full 25-test suite and provides category-level analysis.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark
from test_cases_expanded import ALL_TEST_CASES, CATEGORY_COUNTS, EXPECTED_SUCCESS_RATES


def analyze_by_category(benchmark: PerformanceBenchmark) -> dict:
    """Analyze benchmark results by category."""

    # Group results by category
    category_results = defaultdict(list)

    for result in benchmark.results:
        # Extract category from test name
        test_name = result.test_name
        category = None

        # Find matching test case
        for name, prompt, cat in ALL_TEST_CASES:
            if name == test_name:
                category = cat
                break

        if category:
            category_results[category].append(result)

    # Calculate statistics per category
    category_stats = {}

    for category, results in category_results.items():
        total = len(results)
        successful = sum(1 for r in results if r.end_to_end_success)
        success_rate = successful / total if total > 0 else 0

        # Latencies for successful tests only
        successful_results = [r for r in results if r.end_to_end_success]
        if successful_results:
            avg_latency = sum(r.total_latency_ms for r in successful_results) / len(
                successful_results
            )
            avg_nlp_to_ir = sum(
                r.nlp_to_ir.latency_ms for r in successful_results if r.nlp_to_ir
            ) / len(successful_results)
            avg_ir_to_code = sum(
                r.ir_to_code.latency_ms for r in successful_results if r.ir_to_code
            ) / len(successful_results)
        else:
            avg_latency = 0
            avg_nlp_to_ir = 0
            avg_ir_to_code = 0

        category_stats[category] = {
            "total": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": success_rate,
            "expected_success_rate": EXPECTED_SUCCESS_RATES.get(category, 0),
            "avg_latency_ms": avg_latency,
            "avg_nlp_to_ir_ms": avg_nlp_to_ir,
            "avg_ir_to_code_ms": avg_ir_to_code,
        }

    return category_stats


def print_category_analysis(category_stats: dict):
    """Print detailed category analysis."""
    print("\n" + "#" * 60)
    print("# CATEGORY ANALYSIS")
    print("#" * 60)

    # Sort by category name
    for category in sorted(category_stats.keys()):
        stats = category_stats[category]

        print(f"\n--- {category.upper()} ---")
        print(f"Tests:           {stats['total']}")
        print(f"Successful:      {stats['successful']} ({stats['success_rate'] * 100:.1f}%)")
        print(f"Failed:          {stats['failed']}")
        print(f"Expected:        {stats['expected_success_rate'] * 100:.0f}%")

        if stats["success_rate"] >= stats["expected_success_rate"]:
            status = "✅ MEETS EXPECTATION"
        else:
            status = f"⚠️  BELOW EXPECTATION ({(stats['success_rate'] - stats['expected_success_rate']) * 100:+.1f}%)"
        print(f"Status:          {status}")

        if stats["successful"] > 0:
            print(
                f"Avg Latency:     {stats['avg_latency_ms']:.0f}ms ({stats['avg_latency_ms'] / 1000:.2f}s)"
            )
            print(f"  NLP → IR:      {stats['avg_nlp_to_ir_ms']:.0f}ms")
            print(f"  IR → Code:     {stats['avg_ir_to_code_ms']:.0f}ms")

    # Overall comparison
    print("\n" + "=" * 60)
    overall_success = sum(s["successful"] for s in category_stats.values())
    overall_total = sum(s["total"] for s in category_stats.values())
    overall_rate = overall_success / overall_total if overall_total > 0 else 0

    # Calculate weighted expected rate
    expected_overall = sum(
        CATEGORY_COUNTS[cat] * EXPECTED_SUCCESS_RATES[cat] for cat in CATEGORY_COUNTS
    ) / sum(CATEGORY_COUNTS.values())

    print(f"OVERALL SUCCESS RATE: {overall_rate * 100:.1f}% ({overall_success}/{overall_total})")
    print(f"EXPECTED SUCCESS RATE: {expected_overall * 100:.1f}%")

    if overall_rate >= expected_overall:
        print("✅ MEETS OVERALL EXPECTATION")
    else:
        diff = (overall_rate - expected_overall) * 100
        print(f"⚠️  BELOW EXPECTATION ({diff:+.1f}%)")
    print("=" * 60)


async def main(run_subset: bool = False, subset_size: int = 10):
    """Run expanded benchmark suite."""

    print("\n" + "#" * 60)
    print("# EXPANDED BENCHMARK SUITE")
    print("# Total test cases: 25")
    if run_subset:
        print(f"# Running SUBSET: {subset_size} tests")
    else:
        print("# Running FULL SUITE: All 25 tests")
    print(f"# Estimated time: {(subset_size if run_subset else 25) * 15 / 60:.1f} minutes")
    print("#" * 60)

    # Select test cases
    if run_subset:
        # Run a balanced subset across categories
        test_cases = [
            # 2 arithmetic
            ("add_numbers", "Create a function that adds two numbers"),
            ("absolute_value", "Create a function that returns the absolute value of a number"),
            # 2 string
            ("string_length", "Create a function that returns the length of a string"),
            ("uppercase", "Create a function that converts a string to uppercase"),
            # 2 list
            ("list_length", "Create a function that returns the length of a list"),
            ("list_sum", "Create a function that returns the sum of numbers in a list"),
            # 2 boolean (test indentation bug)
            ("is_even", "Create a function that checks if a number is even"),
            ("max_of_two", "Create a function that returns the maximum of two numbers"),
            # 1 edge case
            (
                "safe_divide",
                "Create a function that divides two numbers and returns zero if the divisor is zero",
            ),
            # 1 type conversion
            ("int_to_string", "Create a function that converts an integer to a string"),
        ]
    else:
        test_cases = [(name, prompt) for name, prompt, _ in ALL_TEST_CASES]

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark suite
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    # Run benchmark
    print("\n⏱️  Starting benchmark run...")
    print(f"🔥 This will take approximately {len(test_cases) * 15 / 60:.1f} minutes\n")

    summary = await benchmark.run_benchmark_suite(
        test_cases=test_cases,
        warmup_runs=1,  # One warmup to handle cold start
    )

    # Analyze by category
    category_stats = analyze_by_category(benchmark)
    print_category_analysis(category_stats)

    # Save category analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    analysis_file = Path("benchmark_results") / f"category_analysis_{timestamp}.json"

    with open(analysis_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "test_count": len(test_cases),
                "category_stats": category_stats,
                "summary": {
                    "total_runs": summary.total_runs,
                    "successful_runs": summary.successful_runs,
                    "failed_runs": summary.failed_runs,
                    "success_rate": summary.successful_runs / summary.total_runs
                    if summary.total_runs > 0
                    else 0,
                },
            },
            f,
            indent=2,
        )

    print(f"\n✓ Category analysis saved to: {analysis_file}")

    return summary, category_stats


if __name__ == "__main__":
    import sys

    # Check for --subset flag
    run_subset = "--subset" in sys.argv or "-s" in sys.argv

    # Check for --full flag
    run_full = "--full" in sys.argv or "-f" in sys.argv

    if run_full:
        print("\n🔥 Running FULL suite (25 tests, ~6 minutes)")
        asyncio.run(main(run_subset=False))
    elif run_subset:
        print("\n⚡ Running SUBSET (10 tests, ~2.5 minutes)")
        asyncio.run(main(run_subset=True, subset_size=10))
    else:
        print("\nUsage:")
        print("  python run_expanded_benchmark.py --subset  # Run 10-test subset (~2.5 min)")
        print("  python run_expanded_benchmark.py --full    # Run full 25 tests (~6 min)")
        print("\nRecommendation: Start with --subset to validate, then run --full")
        sys.exit(1)
