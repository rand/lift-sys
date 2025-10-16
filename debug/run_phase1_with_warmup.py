#!/usr/bin/env python3
"""
Run Phase 1 tests with Modal warm-up.

Adds a warm-up phase to ensure Modal endpoint is ready.
"""

import asyncio
from pathlib import Path

from performance_benchmark import PerformanceBenchmark
from test_cases_nontrivial import PHASE_1_TESTS

from lift_sys.providers.modal_provider import ModalProvider


async def warm_up_modal(provider):
    """Send a simple request to warm up the Modal endpoint."""
    print("\n🔥 Warming up Modal endpoint...")
    print("   This may take 30-60 seconds for cold start...")

    try:
        # Simple test request
        result = await provider.generate_structured(
            prompt="Return an empty object",
            schema={"type": "object", "properties": {"status": {"type": "string"}}},
            max_tokens=50,
            temperature=0.1,
        )
        print("   ✓ Warm-up successful")
        return True
    except Exception as e:
        print(f"   ⚠️  Warm-up had issues: {e}")
        print("   Continuing anyway...")
        return False


async def run_phase1():
    """Run Phase 1 tests with warm-up."""

    # Initialize provider
    print("\n" + "=" * 70)
    print("PHASE 1: High Priority Tests (5 tests)")
    print("=" * 70)
    print("Initializing Modal provider...")

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Warm up endpoint
    await warm_up_modal(provider)
    print("\nWaiting 5 seconds for model to be fully ready...")
    await asyncio.sleep(5)

    # Create benchmark
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\nStarting Phase 1 tests...")
    print("=" * 70)

    results = []
    passed = 0

    for i, test_case in enumerate(PHASE_1_TESTS, 1):
        print(f"\n[Test {i}/5] {test_case['name']}")
        print(f"Category: {test_case['category']}")
        print(f"Prompt: {test_case['prompt'][:70]}...")
        print("-" * 70)

        try:
            # Run benchmark
            result = await benchmark.run_single_benchmark(
                test_name=test_case["name"], prompt=test_case["prompt"]
            )

            # Check compilation
            compiled = result.end_to_end_success

            if not compiled:
                print("  ❌ Compilation failed")
                results.append(
                    {
                        "name": test_case["name"],
                        "category": test_case["category"],
                        "compiled": False,
                        "executed": False,
                        "success": False,
                    }
                )
                continue

            print("  ✓ Compilation successful")

            # Extract code
            if hasattr(result.code_output, "source_code"):
                code = result.code_output.source_code
            elif isinstance(result.code_output, str):
                code = result.code_output
            else:
                code = str(result.code_output)

            # Execute tests
            exec_results = benchmark.execute_generated_code(
                code=code,
                function_name=test_case["function_name"],
                test_cases=test_case["test_cases"],
            )

            executed = all(t.passed for t in exec_results)
            passed_count = sum(1 for t in exec_results if t.passed)

            print(f"  Execution: {passed_count}/{len(exec_results)} tests passed")

            if executed:
                print("  ✅ PASS")
                passed += 1
            else:
                print("  ❌ FAIL - Some execution tests failed")
                # Show first failure
                failed = [t for t in exec_results if not t.passed]
                if failed:
                    print(f"     First failure: {failed[0].error}")

            results.append(
                {
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "compiled": True,
                    "executed": executed,
                    "success": executed,
                    "exec_passed": passed_count,
                    "exec_total": len(exec_results),
                }
            )

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append(
                {
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "compiled": False,
                    "executed": False,
                    "success": False,
                    "error": str(e),
                }
            )

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 1 SUMMARY")
    print("=" * 70)
    print("Total tests:    5")
    print(f"Passed:         {passed}/5 ({passed / 5 * 100:.1f}%)")
    print(f"Failed:         {5 - passed}/5")

    print("\nBy Category:")
    from collections import defaultdict

    by_category = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in results:
        by_category[r["category"]]["total"] += 1
        if r["success"]:
            by_category[r["category"]]["passed"] += 1

    for cat, stats in sorted(by_category.items()):
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cat:20s}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    print("\n" + "=" * 70)
    print("ASSESSMENT")
    print("=" * 70)

    success_rate = passed / 5

    if success_rate >= 0.80:
        print("✅ EXCELLENT: ≥80% success rate")
        print("   Recommend proceeding to Phase 2 (10 tests)")
    elif success_rate >= 0.60:
        print("✅ GOOD: 60-80% success rate")
        print("   System working well, some issues to investigate")
    else:
        print("⚠️  NEEDS INVESTIGATION: <60% success rate")
        print("   Recommend analyzing failures before continuing")

    # Detailed failures
    failures = [r for r in results if not r["success"]]
    if failures:
        print(f"\nFailed tests ({len(failures)}):")
        for f in failures:
            print(f"  - {f['name']} ({f['category']})")

    print("=" * 70)

    return results, passed


async def main():
    """Run Phase 1 with warm-up."""
    results, passed = await run_phase1()

    if passed >= 4:  # 80%+
        print("\n✓ Phase 1 successful!")
        print("  Ready to proceed to Phase 2")
        print("  Command: uv run python run_nontrivial_tests.py phase2")
    elif passed >= 3:  # 60%+
        print("\n⚠ Phase 1 acceptable")
        print("  Recommend reviewing failures before Phase 2")
    else:
        print("\n⚠ Phase 1 below expectations")
        print("  Recommend investigating issues")


if __name__ == "__main__":
    asyncio.run(main())
