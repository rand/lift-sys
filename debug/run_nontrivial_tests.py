#!/usr/bin/env python3
"""
Runner for non-trivial test cases.

Runs tests in phases with detailed metrics collection.
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from performance_benchmark import PerformanceBenchmark
from test_cases_nontrivial import TEST_SUITES

from lift_sys.providers.modal_provider import ModalProvider


async def run_test_suite(phase="phase1", save_results=True):
    """
    Run a test suite phase.

    Args:
        phase: Phase name ("phase1", "phase2", or "phase3")
        save_results: Whether to save results to JSON

    Returns:
        Tuple of (results list, summary dict)
    """
    suite = TEST_SUITES[phase]
    tests = suite["tests"]

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n" + "=" * 70)
    print(f"{suite['name']}")
    print("=" * 70)
    print(f"{suite['description']}")
    print(f"Total tests: {len(tests)}")
    print("=" * 70)

    results = []
    category_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    complexity_stats = defaultdict(lambda: {"total": 0, "passed": 0})

    for i, test_case in enumerate(tests, 1):
        print(f"\n[Test {i}/{len(tests)}] {test_case['name']}")
        print(f"Category: {test_case['category']}, Complexity: {test_case['complexity']}")
        print(f"Prompt: {test_case['prompt'][:80]}...")
        print("-" * 70)

        # Run benchmark
        result = await benchmark.run_single_benchmark(
            test_name=test_case["name"], prompt=test_case["prompt"]
        )

        # Track compilation
        compiled = result.end_to_end_success

        # Run execution tests if compilation succeeded
        executed = False
        exec_results = []

        if compiled:
            # Extract source code
            if hasattr(result.code_output, "source_code"):
                code = result.code_output.source_code
            elif isinstance(result.code_output, str):
                code = result.code_output
            elif result.ir_to_code and result.ir_to_code.metadata.get("result"):
                gen_code = result.ir_to_code.metadata["result"]
                code = gen_code.source_code if hasattr(gen_code, "source_code") else str(gen_code)
            else:
                code = str(result.code_output)

            # Execute with test cases
            exec_results = benchmark.execute_generated_code(
                code=code,
                function_name=test_case["function_name"],
                test_cases=test_case["test_cases"],
            )

            executed = all(t.passed for t in exec_results)

            # Print execution results
            passed_count = sum(1 for t in exec_results if t.passed)
            print(f"  Execution: {passed_count}/{len(exec_results)} tests passed")

            if not executed:
                # Show first failure
                failed = [t for t in exec_results if not t.passed]
                if failed:
                    print(f"  ❌ First failure: {failed[0].error}")
        else:
            print("  ❌ Compilation failed")
            if result.ir_to_code:
                print(f"     Error: {result.ir_to_code.error}")

        # Overall status
        success = compiled and executed
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} (Compiled: {compiled}, Executed: {executed})")

        # Update stats
        category_stats[test_case["category"]]["total"] += 1
        complexity_stats[test_case["complexity"]]["total"] += 1

        if success:
            category_stats[test_case["category"]]["passed"] += 1
            complexity_stats[test_case["complexity"]]["passed"] += 1

        # Store result
        results.append(
            {
                "test_name": test_case["name"],
                "category": test_case["category"],
                "complexity": test_case["complexity"],
                "prompt": test_case["prompt"],
                "compiled": compiled,
                "executed": executed,
                "success": success,
                "execution_tests": [
                    {
                        "test_name": t.test_name,
                        "passed": t.passed,
                        "expected": str(t.expected),
                        "actual": str(t.actual),
                        "error": t.error,
                    }
                    for t in exec_results
                ],
                "latency_ms": result.total_latency_ms,
                "cost_usd": result.estimated_cost_usd,
            }
        )

    # Calculate summary
    total = len(results)
    compilation_success = sum(1 for r in results if r["compiled"])
    execution_success = sum(1 for r in results if r["executed"])
    overall_success = sum(1 for r in results if r["success"])

    summary = {
        "phase": phase,
        "total_tests": total,
        "compilation_success": compilation_success,
        "compilation_rate": compilation_success / total if total > 0 else 0,
        "execution_success": execution_success,
        "execution_rate": execution_success / total if total > 0 else 0,
        "overall_success": overall_success,
        "overall_rate": overall_success / total if total > 0 else 0,
        "by_category": {
            cat: {
                "total": stats["total"],
                "passed": stats["passed"],
                "rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0,
            }
            for cat, stats in category_stats.items()
        },
        "by_complexity": {
            comp: {
                "total": stats["total"],
                "passed": stats["passed"],
                "rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0,
            }
            for comp, stats in complexity_stats.items()
        },
        "total_latency_ms": sum(r["latency_ms"] for r in results),
        "total_cost_usd": sum(r["cost_usd"] for r in results),
    }

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests:       {total}")
    print(
        f"Compilation:       {compilation_success}/{total} ({summary['compilation_rate'] * 100:.1f}%)"
    )
    print(
        f"Execution:         {execution_success}/{total} ({summary['execution_rate'] * 100:.1f}%)"
    )
    print(f"Overall success:   {overall_success}/{total} ({summary['overall_rate'] * 100:.1f}%)")
    print(f"Total time:        {summary['total_latency_ms'] / 1000:.1f}s")
    print(f"Total cost:        ${summary['total_cost_usd']:.4f}")

    print("\nBy Category:")
    for cat, stats in summary["by_category"].items():
        print(f"  {cat:20s}: {stats['passed']}/{stats['total']} ({stats['rate'] * 100:.1f}%)")

    print("\nBy Complexity:")
    for comp, stats in summary["by_complexity"].items():
        print(f"  {comp:20s}: {stats['passed']}/{stats['total']} ({stats['rate'] * 100:.1f}%)")

    # Save results
    if save_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = Path("benchmark_results") / f"nontrivial_{phase}_{timestamp}.json"

        with open(results_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "phase": phase,
                    "suite_name": suite["name"],
                    "suite_description": suite["description"],
                    "summary": summary,
                    "results": results,
                },
                f,
                indent=2,
            )

        print(f"\n✓ Results saved to: {results_file}")

    print("=" * 70)

    return results, summary


async def main():
    """Run test suite with phase selection."""
    import sys

    # Get phase from command line or default to phase1
    phase = sys.argv[1] if len(sys.argv) > 1 else "phase1"

    if phase not in TEST_SUITES:
        print(f"Error: Unknown phase '{phase}'")
        print(f"Available phases: {', '.join(TEST_SUITES.keys())}")
        return

    results, summary = await run_test_suite(phase)

    # Assessment
    print("\n" + "=" * 70)
    print("ASSESSMENT")
    print("=" * 70)

    overall_rate = summary["overall_rate"]

    if overall_rate >= 0.90:
        print("✅ EXCELLENT: ≥90% success rate")
        print("   System performing very well on non-trivial tests")
    elif overall_rate >= 0.80:
        print("✅ GOOD: 80-90% success rate")
        print("   System performing well, minor issues to address")
    elif overall_rate >= 0.70:
        print("⚠️  ACCEPTABLE: 70-80% success rate")
        print("   System functional but has some limitations")
    else:
        print("❌ NEEDS WORK: <70% success rate")
        print("   System has significant issues to address")

    # Failure analysis
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\nFailed tests ({len(failures)}):")
        for r in failures:
            reason = "Compilation" if not r["compiled"] else "Execution"
            print(f"  - {r['test_name']} ({r['category']}): {reason} failed")

    # Next steps
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)

    if phase == "phase1":
        if overall_rate >= 0.80:
            print("✓ Phase 1 successful, recommend proceeding to Phase 2")
            print("  Command: uv run python run_nontrivial_tests.py phase2")
        else:
            print("⚠ Phase 1 below target, recommend investigating failures")
    elif phase == "phase2":
        if overall_rate >= 0.75:
            print("✓ Phase 2 successful, recommend proceeding to Phase 3")
            print("  Command: uv run python run_nontrivial_tests.py phase3")
        else:
            print("⚠ Phase 2 below target, recommend analyzing patterns")
    else:
        print("✓ Full test suite complete")
        print("  Ready to update documentation with results")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
