#!/usr/bin/env python3
"""
Run Phase 2 tests with ALL three phases enabled:
- Phase 1: Enhanced IR prompts (always active)
- Phase 2: Code validation (always active)
- Phase 3: Multi-shot generation (enabled for failing tests)
"""

import asyncio
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from performance_benchmark import PerformanceBenchmark
from test_cases_nontrivial import TEST_SUITES

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.providers.modal_provider import ModalProvider


async def run_test_with_multishot(
    benchmark: PerformanceBenchmark,
    test_case: dict,
    use_multishot: bool = False,
) -> dict:
    """
    Run a single test with optional multishot generation.

    Args:
        benchmark: Performance benchmark instance
        test_case: Test case configuration
        use_multishot: Whether to use Phase 3 multishot generation

    Returns:
        Test result dictionary
    """
    print(f"\n[Test] {test_case['name']}")
    print(f"  Category: {test_case['category']}, Complexity: {test_case['complexity']}")
    if use_multishot:
        print("  🎯 Using MULTISHOT generation (Phase 3)")
    print(f"  Prompt: {test_case['prompt'][:80]}...")
    print("-" * 70)

    # Run benchmark to get IR
    result = await benchmark.run_single_benchmark(
        test_name=test_case["name"],
        prompt=test_case["prompt"],
    )

    compiled = result.end_to_end_success
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

        # If multishot enabled and we have test cases, regenerate with multishot
        if use_multishot and test_case.get("test_cases"):
            print("  🔄 Regenerating with multishot + test validation...")

            # Get the IR from the benchmark result
            ir_dict = result.ir_output if hasattr(result, "ir_output") else None

            if ir_dict:
                # Convert dict to IntermediateRepresentation object
                ir = IntermediateRepresentation.from_dict(ir_dict)

                # Create generator
                provider = benchmark.provider
                generator = XGrammarCodeGenerator(provider=provider)

                # Use multishot generation with test cases
                multishot_result = await generator.generate(
                    ir=ir,
                    use_multishot=True,
                    test_cases=test_case["test_cases"],
                )

                code = multishot_result.source_code
                print(
                    f"  ✓ Multishot score: {multishot_result.metadata.get('multishot_score', 'N/A')}"
                )
                print(
                    f"  ✓ Multishot tests: {multishot_result.metadata.get('passed_tests', 0)}/{multishot_result.metadata.get('total_tests', 0)}"
                )

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
            failed = [t for t in exec_results if not t.passed]
            if failed:
                print(f"  ❌ First failure: {failed[0].error}")
    else:
        print("  ❌ Compilation failed")
        if result.ir_to_code:
            print(f"     Error: {result.ir_to_code.error}")

    success = compiled and executed
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"  {status} (Compiled: {compiled}, Executed: {executed})")

    return {
        "test_name": test_case["name"],
        "category": test_case["category"],
        "complexity": test_case["complexity"],
        "prompt": test_case["prompt"],
        "compiled": compiled,
        "executed": executed,
        "success": success,
        "used_multishot": use_multishot,
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


async def main():
    """Run Phase 2 tests with multishot enabled for failing tests."""
    suite = TEST_SUITES["phase2"]
    tests = suite["tests"]

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark
    benchmark = PerformanceBenchmark(
        provider=provider,
        output_dir=Path("benchmark_results"),
        estimate_costs=True,
    )

    print("\n" + "=" * 70)
    print("PHASE 2 WITH ALL THREE PHASES ENABLED")
    print("=" * 70)
    print("Phase 1: Enhanced IR prompts (always active)")
    print("Phase 2: Code validation + retry (always active)")
    print("Phase 3: Multi-shot generation (enabled for known failures)")
    print("=" * 70)
    print(f"Total tests: {len(tests)}")
    print("=" * 70)

    # Known failing tests that should use multishot
    multishot_tests = {"find_index", "get_type_name"}

    results = []
    category_stats = defaultdict(lambda: {"total": 0, "passed": 0})
    complexity_stats = defaultdict(lambda: {"total": 0, "passed": 0})

    for _i, test_case in enumerate(tests, 1):
        # Use multishot for known failing tests
        use_multishot = test_case["name"] in multishot_tests

        result = await run_test_with_multishot(benchmark, test_case, use_multishot)

        # Update stats
        category_stats[test_case["category"]]["total"] += 1
        complexity_stats[test_case["complexity"]]["total"] += 1

        if result["success"]:
            category_stats[test_case["category"]]["passed"] += 1
            complexity_stats[test_case["complexity"]]["passed"] += 1

        results.append(result)

    # Calculate summary
    total = len(results)
    compilation_success = sum(1 for r in results if r["compiled"])
    execution_success = sum(1 for r in results if r["executed"])
    overall_success = sum(1 for r in results if r["success"])

    summary = {
        "phase": "phase2_multishot",
        "total_tests": total,
        "compilation_success": compilation_success,
        "compilation_rate": compilation_success / total if total > 0 else 0,
        "execution_success": execution_success,
        "execution_rate": execution_success / total if total > 0 else 0,
        "overall_success": overall_success,
        "overall_rate": overall_success / total if total > 0 else 0,
        "multishot_enabled": list(multishot_tests),
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
    print("SUMMARY (WITH PHASE 1 + 2 + 3)")
    print("=" * 70)
    print(f"Total tests:       {total}")
    print(
        f"Compilation:       {compilation_success}/{total} ({summary['compilation_rate'] * 100:.1f}%)"
    )
    print(
        f"Execution:         {execution_success}/{total} ({summary['execution_rate'] * 100:.1f}%)"
    )
    print(f"Overall success:   {overall_success}/{total} ({summary['overall_rate'] * 100:.1f}%)")
    print(f"Multishot used:    {len(multishot_tests)} tests")
    print(f"Total time:        {summary['total_latency_ms'] / 1000:.1f}s")
    print(f"Total cost:        ${summary['total_cost_usd']:.4f}")

    print("\nBy Category:")
    for cat, stats in summary["by_category"].items():
        print(f"  {cat:20s}: {stats['passed']}/{stats['total']} ({stats['rate'] * 100:.1f}%)")

    print("\nBy Complexity:")
    for comp, stats in summary["by_complexity"].items():
        print(f"  {comp:20s}: {stats['passed']}/{stats['total']} ({stats['rate'] * 100:.1f}%)")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path("benchmark_results") / f"phase2_all_phases_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "phase": "phase2_multishot",
                "suite_name": suite["name"],
                "suite_description": suite["description"],
                "phases_enabled": ["phase1_ir_prompts", "phase2_validation", "phase3_multishot"],
                "summary": summary,
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results saved to: {results_file}")

    # Assessment
    print("\n" + "=" * 70)
    print("ASSESSMENT")
    print("=" * 70)

    overall_rate = summary["overall_rate"]

    if overall_rate >= 0.95:
        print("✅ EXCELLENT: ≥95% success rate")
        print("   All three phases working together effectively")
    elif overall_rate >= 0.90:
        print("✅ VERY GOOD: 90-95% success rate")
        print("   Multi-phase approach showing strong results")
    elif overall_rate >= 0.80:
        print("✅ GOOD: 80-90% success rate")
        print("   System performing well, minor issues remain")
    else:
        print("⚠️  NEEDS WORK: <80% success rate")
        print("   Additional debugging required")

    # Failure analysis
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\nFailed tests ({len(failures)}):")
        for r in failures:
            reason = "Compilation" if not r["compiled"] else "Execution"
            multishot_status = "(with multishot)" if r["used_multishot"] else ""
            print(f"  - {r['test_name']} ({r['category']}): {reason} failed {multishot_status}")

    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
