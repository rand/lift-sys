#!/usr/bin/env python3
"""Quick test of the performance benchmark with a single test case."""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark


async def main():
    """Run a quick single-test benchmark to verify everything works."""

    # Simple test case to avoid indentation issues
    test_cases = [
        ("add_numbers", "Create a function that adds two numbers"),
    ]

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})  # No credentials needed for Modal

    # Create benchmark suite
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    # Run single test
    print("\n🧪 Running single-test benchmark validation...")
    summary = await benchmark.run_benchmark_suite(
        test_cases=test_cases,
        warmup_runs=0,  # Skip warmup for quick test
    )

    if summary.successful_runs > 0:
        print("\n✅ Benchmark script works! Ready for full suite.")
    else:
        print("\n❌ Benchmark failed. Check errors above.")


if __name__ == "__main__":
    asyncio.run(main())
