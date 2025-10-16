#!/usr/bin/env python3
"""
Run benchmark with execution validation.

This validates that generated code not only compiles but also executes correctly.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from performance_benchmark import BenchmarkResult, PerformanceBenchmark
from test_case_definitions import QUICK_VALIDATION_TESTS

from lift_sys.providers.modal_provider import ModalProvider


async def run_benchmark_with_execution(
    test_cases: list[dict], output_dir: Path = Path("benchmark_results")
) -> tuple[list[BenchmarkResult], dict]:
    """
    Run benchmark suite with execution validation.

    Args:
        test_cases: List of test case dictionaries with execution test data
        output_dir: Directory to save results

    Returns:
        Tuple of (results list, summary statistics)
    """
    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark
    benchmark = PerformanceBenchmark(provider=provider, output_dir=output_dir, estimate_costs=True)

    results = []

    print("\n" + "=" * 60)
    print("EXECUTION VALIDATION BENCHMARK")
    print("=" * 60)
    print(f"Test cases: {len(test_cases)}")
    print("Provider: Modal (with return statement fix)")
    print("=" * 60)

    # Run each test case
    for test_case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Test: {test_case['name']} ({test_case['category']})")
        print(f"Prompt: {test_case['prompt']}")
        print(f"{'=' * 60}")

        # Run benchmark for this test case
        result = await benchmark.run_single_benchmark(
            test_name=test_case["name"], prompt=test_case["prompt"]
        )

        # If code generation succeeded, run execution tests
        if result.code_output and result.ir_to_code and result.ir_to_code.success:
            print("\n[3/3] Running execution tests...")

            function_name = test_case["function_name"]
            test_inputs = test_case["test_cases"]

            # Extract source code from GeneratedCode object or result metadata
            if hasattr(result.code_output, "source_code"):
                code = result.code_output.source_code
            elif isinstance(result.code_output, str):
                code = result.code_output
            elif result.ir_to_code.metadata.get("result"):
                gen_code = result.ir_to_code.metadata["result"]
                code = gen_code.source_code if hasattr(gen_code, "source_code") else str(gen_code)
            else:
                code = str(result.code_output)

            exec_results = benchmark.execute_generated_code(
                code=code, function_name=function_name, test_cases=test_inputs
            )

            result.execution_tests = exec_results
            result.execution_success = all(t.passed for t in exec_results)

            # Print execution results
            for exec_result in exec_results:
                if exec_result.passed:
                    print(f"  ✅ {exec_result.test_name}: {exec_result.actual}")
                else:
                    print(f"  ❌ {exec_result.test_name}: {exec_result.error}")

            if result.execution_success:
                print(f"\n✅ EXECUTION SUCCESS: All {len(exec_results)} tests passed")
            else:
                passed = sum(1 for t in exec_results if t.passed)
                print(f"\n⚠️  EXECUTION PARTIAL: {passed}/{len(exec_results)} tests passed")

        else:
            print("\n❌ Skipping execution tests (code generation failed)")
            result.execution_success = False

        results.append(result)

    # Calculate summary statistics
    total = len(results)
    compilation_success = sum(1 for r in results if r.end_to_end_success)
    execution_success = sum(1 for r in results if r.execution_success)

    summary = {
        "total_tests": total,
        "compilation_success": compilation_success,
        "compilation_rate": compilation_success / total if total > 0 else 0,
        "execution_success": execution_success,
        "execution_rate": execution_success / total if total > 0 else 0,
        "both_success": execution_success,  # If execution passes, compilation must have passed
        "both_rate": execution_success / total if total > 0 else 0,
    }

    # Print summary
    print("\n" + "=" * 60)
    print("EXECUTION VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total tests:          {total}")
    print(f"Compilation success:  {compilation_success} ({summary['compilation_rate'] * 100:.1f}%)")
    print(f"Execution success:    {execution_success} ({summary['execution_rate'] * 100:.1f}%)")
    print(f"Both success:         {execution_success} ({summary['both_rate'] * 100:.1f}%)")
    print("=" * 60)

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = output_dir / f"execution_validation_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "summary": summary,
                "results": [
                    {
                        "test_name": r.test_name,
                        "prompt": r.prompt,
                        "compilation_success": r.end_to_end_success,
                        "execution_success": r.execution_success,
                        "execution_tests": [
                            {
                                "test_name": t.test_name,
                                "passed": t.passed,
                                "expected": str(t.expected),
                                "actual": str(t.actual),
                                "error": t.error,
                            }
                            for t in r.execution_tests
                        ]
                        if r.execution_tests
                        else [],
                        "total_latency_ms": r.total_latency_ms,
                        "estimated_cost_usd": r.estimated_cost_usd,
                    }
                    for r in results
                ],
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results saved to: {results_file}")

    return results, summary


async def main():
    """Run quick execution validation."""
    print("\n🧪 Running Execution Validation (with return statement fix)")
    print("=" * 60)

    results, summary = await run_benchmark_with_execution(QUICK_VALIDATION_TESTS)

    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)

    if summary["execution_rate"] >= 0.9:
        print("✅ EXCELLENT: >90% execution success rate")
    elif summary["execution_rate"] >= 0.7:
        print("✅ GOOD: 70-90% execution success rate")
    elif summary["execution_rate"] >= 0.5:
        print("⚠️  ACCEPTABLE: 50-70% execution success rate")
    else:
        print("❌ NEEDS WORK: <50% execution success rate")

    if summary["execution_rate"] > summary["compilation_rate"] * 0.5:
        print("✅ Return statement fix appears to be working")
    else:
        print("⚠️  Many functions compile but don't execute correctly")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
