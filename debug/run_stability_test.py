#!/usr/bin/env python3
"""Run Phase 3 multiple times to measure stability and variance.

This script runs the Phase 3 test suite N times (default 5) with temperature=0.8
to understand the variance in results. This is critical for production confidence.

Results are saved to logs/stability_test_TIMESTAMP.json
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from debug.performance_benchmark import PerformanceBenchmark
from debug.test_cases_nontrivial import TEST_SUITES
from lift_sys.providers.modal_provider import ModalProvider


async def run_single_iteration(iteration: int, provider, translator) -> dict:
    """Run Phase 3 once and return results."""
    print(f"\n{'='*80}")
    print(f"ITERATION {iteration}/5")
    print(f"{'='*80}\n")

    phase3_tests = TEST_SUITES["phase3"]
    passed = 0
    failed = 0
    results = []

    for i, test in enumerate(phase3_tests, 1):
        test_name = test["name"]
        print(f"[{i}/{len(phase3_tests)}] {test_name}...", end=" ", flush=True)

        try:
            # Generate IR
            ir = await translator.translate(test["prompt"])

            # Generate code
            generator = provider.get_code_generator()
            code = await generator.generate_code(ir)

            # Execute validation
            func_name = test.get("expected_function_name", test_name)
            namespace = {}
            exec(code, namespace)

            # Find function
            func = None
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith("_"):
                    if name == func_name or func_name in name or name in func_name:
                        func = obj
                        func_name = name
                        break

            if not func:
                print(f"❌ (function not found)")
                failed += 1
                results.append({"test": test_name, "status": "failed", "reason": "function_not_found"})
                continue

            # Run test cases
            test_passed = True
            for inputs, expected in test["test_cases"]:
                try:
                    result = func(*inputs) if isinstance(inputs, tuple) else func(inputs)
                    if result != expected:
                        test_passed = False
                        break
                except Exception as e:
                    test_passed = False
                    break

            if test_passed:
                print("✅")
                passed += 1
                results.append({"test": test_name, "status": "passed"})
            else:
                print("❌")
                failed += 1
                results.append({"test": test_name, "status": "failed", "reason": "test_case_failed"})

        except Exception as e:
            print(f"❌ (error: {str(e)[:50]})")
            failed += 1
            results.append({"test": test_name, "status": "failed", "reason": str(e)[:100]})

    success_rate = (passed / len(phase3_tests)) * 100
    print(f"\nIteration {iteration}: {passed}/{len(phase3_tests)} ({success_rate:.1f}%)")

    return {
        "iteration": iteration,
        "passed": passed,
        "failed": failed,
        "total": len(phase3_tests),
        "success_rate": success_rate,
        "results": results,
    }


async def main():
    """Run stability test: Phase 3 x5 iterations."""
    n_iterations = 5
    temperature = 0.8

    print("="*80)
    print("STABILITY TEST - Phase 3 x5 Iterations")
    print(f"Temperature: {temperature}, Best-of-N: n=3")
    print("="*80)

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create translator with Best-of-N
    from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
    translator = BestOfNIRTranslator(
        provider=provider,
        n_candidates=3,
        temperature=temperature
    )

    # Run iterations
    all_results = []
    for i in range(1, n_iterations + 1):
        iteration_result = await run_single_iteration(i, provider, translator)
        all_results.append(iteration_result)

    # Analysis
    print("\n" + "="*80)
    print("STABILITY ANALYSIS")
    print("="*80)

    success_rates = [r["success_rate"] for r in all_results]
    avg_rate = sum(success_rates) / len(success_rates)
    min_rate = min(success_rates)
    max_rate = max(success_rates)
    variance = sum((r - avg_rate) ** 2 for r in success_rates) / len(success_rates)
    std_dev = variance ** 0.5

    print(f"\nSuccess Rate Statistics:")
    print(f"  Average:  {avg_rate:.1f}%")
    print(f"  Min:      {min_rate:.1f}%")
    print(f"  Max:      {max_rate:.1f}%")
    print(f"  Std Dev:  {std_dev:.1f}%")
    print(f"  Variance: {variance:.1f}")

    # Per-test consistency
    print(f"\nPer-Test Consistency:")
    test_names = [t["name"] for t in TEST_SUITES["phase3"]]
    for test_name in test_names:
        passes = sum(
            1 for result in all_results
            for test_result in result["results"]
            if test_result["test"] == test_name and test_result["status"] == "passed"
        )
        consistency = (passes / n_iterations) * 100
        status = "✅" if consistency == 100 else "⚠️" if consistency >= 80 else "❌"
        print(f"  {status} {test_name}: {passes}/{n_iterations} ({consistency:.0f}%)")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path("logs") / f"stability_test_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump({
            "metadata": {
                "timestamp": timestamp,
                "n_iterations": n_iterations,
                "temperature": temperature,
                "model": "Qwen2.5-Coder-32B-Instruct",
                "best_of_n": 3,
            },
            "summary": {
                "avg_success_rate": avg_rate,
                "min_success_rate": min_rate,
                "max_success_rate": max_rate,
                "std_dev": std_dev,
                "variance": variance,
            },
            "iterations": all_results,
        }, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")

    # Production readiness assessment
    print(f"\nProduction Readiness Assessment:")
    if std_dev < 5.0:
        print(f"  ✅ Excellent stability (std dev < 5%)")
    elif std_dev < 10.0:
        print(f"  ⚠️  Acceptable stability (std dev < 10%)")
    else:
        print(f"  ❌ High variance (std dev >= 10%) - investigate")

    if avg_rate >= 80.0:
        print(f"  ✅ Meets 80% success target")
    else:
        print(f"  ❌ Below 80% target (avg: {avg_rate:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
