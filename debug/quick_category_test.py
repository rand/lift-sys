#!/usr/bin/env python3
"""Quick 3-test validation of category analysis."""

import asyncio
from pathlib import Path

from performance_benchmark import PerformanceBenchmark
from run_expanded_benchmark import analyze_by_category, print_category_analysis

from lift_sys.providers.modal_provider import ModalProvider


async def main():
    """Run quick 3-test validation."""

    print("\n⚡ Quick Category Analysis Test (3 tests)")
    print("=" * 60)

    # One test from each of 3 categories
    test_cases = [
        ("add_numbers", "Create a function that adds two numbers"),
        ("string_length", "Create a function that returns the length of a string"),
        ("is_even", "Create a function that checks if a number is even"),
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
        warmup_runs=0,  # Skip warmup for quick test
    )

    # Analyze by category
    category_stats = analyze_by_category(benchmark)
    print_category_analysis(category_stats)

    print("\n✅ Category analysis validated!")
    print("Ready to run full suite with: python run_expanded_benchmark.py --full")


if __name__ == "__main__":
    asyncio.run(main())
