#!/usr/bin/env python3
"""Run Phase 3 tests with Best-of-N sampling."""

import asyncio
import sys

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark
from test_cases_nontrivial import TEST_SUITES


async def main():
    """Run Phase 3 tests with Best-of-N sampling."""

    # Get configuration from command line
    use_best_of_n = "--best-of-n" in sys.argv
    n_candidates = 3  # Default

    if use_best_of_n:
        print("\n" + "=" * 70)
        print("🎯 BEST-OF-N MODE ENABLED")
        print(f"   Generating {n_candidates} candidates per IR, selecting best")
        print("   Cost: {n_candidates}x baseline")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("📊 BASELINE MODE")
        print("   Single IR generation (no Best-of-N)")
        print("=" * 70 + "\n")

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create translator
    if use_best_of_n:
        from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator

        translator = BestOfNIRTranslator(
            provider=provider, n_candidates=n_candidates, temperature=0.5
        )
    else:
        from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator

        translator = XGrammarIRTranslator(provider)

    # Get Phase 3 tests
    phase3_suite = TEST_SUITES["phase3"]
    tests = phase3_suite["tests"]

    print(f"\n{phase3_suite['name']}")
    print(f"{phase3_suite['description']}")
    print(f"Total tests: {len(tests)}")
    print("=" * 70 + "\n")

    # Create benchmark with translator override
    from pathlib import Path

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    # Override the translator in benchmark
    if use_best_of_n:
        benchmark.translator = translator

    results = []
    passed = 0
    failed = 0

    for i, test_case in enumerate(tests, 1):
        print(f"\n[Test {i}/{len(tests)}] {test_case['name']}")
        print(f"Category: {test_case['category']}, Complexity: {test_case['complexity']}")
        print(f"Prompt: {test_case['prompt'][:80]}...")
        print("-" * 70)

        # Generate IR using translator
        try:
            ir = await translator.translate(test_case["prompt"])
            print("✅ IR generated successfully")

            # Now run code generation and execution
            result = await benchmark.run_single_benchmark(
                test_name=test_case["name"], prompt=test_case["prompt"]
            )

            # Check if it compiled
            compiled = result.end_to_end_success

            # Run execution tests if compilation succeeded
            executed = False
            if compiled:
                # Extract source code
                if hasattr(result.code_output, "source_code"):
                    code = result.code_output.source_code
                elif isinstance(result.code_output, str):
                    code = result.code_output
                elif result.ir_to_code and result.ir_to_code.metadata.get("result"):
                    gen_code = result.ir_to_code.metadata["result"]
                    code = (
                        gen_code.source_code if hasattr(gen_code, "source_code") else str(gen_code)
                    )
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
                    # Show failures
                    failed_tests = [t for t in exec_results if not t.passed]
                    for ft in failed_tests[:2]:  # Show first 2
                        print(f"    ❌ {ft.test_name}: Expected {ft.expected}, got {ft.actual}")
                        if ft.error:
                            print(f"       Error: {ft.error}")
            else:
                print("  ❌ Compilation failed")
                if result.ir_to_code:
                    print(f"     Error: {result.ir_to_code.error}")

            # Overall status
            success = compiled and executed
            if success:
                passed += 1
                print("  ✅ PASS")
            else:
                failed += 1
                print(f"  ❌ FAIL (Compiled: {compiled}, Executed: {executed})")

            results.append(
                {
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "success": success,
                    "compiled": compiled,
                    "executed": executed,
                }
            )

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()
            failed += 1
            results.append(
                {
                    "name": test_case["name"],
                    "category": test_case["category"],
                    "success": False,
                    "compiled": False,
                    "executed": False,
                    "error": str(e),
                }
            )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests:       {len(tests)}")
    print(f"Passed:            {passed}/{len(tests)} ({passed / len(tests) * 100:.1f}%)")
    print(f"Failed:            {failed}/{len(tests)} ({failed / len(tests) * 100:.1f}%)")

    # By category
    from collections import defaultdict

    by_category = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in results:
        by_category[r["category"]]["total"] += 1
        if r["success"]:
            by_category[r["category"]]["passed"] += 1

    print("\nBy Category:")
    for cat, stats in sorted(by_category.items()):
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {cat:20s}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")

    # Failed tests
    if failed > 0:
        print(f"\nFailed tests ({failed}):")
        for r in results:
            if not r["success"]:
                print(f"  - {r['name']} ({r['category']})")

    print("=" * 70)

    # Return success rate for scripting
    return passed / len(tests)


if __name__ == "__main__":
    asyncio.run(main())
