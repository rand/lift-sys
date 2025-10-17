#!/usr/bin/env python3
"""Quick 2x validation to measure variance before full stability test."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from debug.test_cases_nontrivial import TEST_SUITES
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider


async def run_single_phase3(iteration: int, provider, translator) -> dict:
    """Run Phase 3 once and return results."""
    print(f"\n{'=' * 80}")
    print(f"ITERATION {iteration}/2")
    print(f"{'=' * 80}\n")

    phase3_tests = TEST_SUITES["phase3"]["tests"]
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
            generator = XGrammarCodeGenerator(provider=provider)
            result = await generator.generate(ir)
            code = result.source_code

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
                print("❌ (function not found)")
                failed += 1
                results.append(
                    {"test": test_name, "status": "failed", "reason": "function_not_found"}
                )
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
                results.append(
                    {"test": test_name, "status": "failed", "reason": "test_case_failed"}
                )

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
    """Run 1x validation."""
    print("=" * 80)
    print("QUICK 1X VALIDATION - Phase 3")
    print("Temperature: 0.8, Best-of-N: n=3")
    print("Estimated time: 8-10 minutes")
    print("=" * 80)

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create translator with Best-of-N
    translator = BestOfNIRTranslator(provider=provider, n_candidates=3, temperature=0.8)

    # Run 1 iteration
    iteration_result = await run_single_phase3(1, provider, translator)

    # Analysis
    print(f"\n{'=' * 80}")
    print("1X VALIDATION ANALYSIS")
    print("=" * 80)

    success_rate = iteration_result["success_rate"]

    print(
        f"\nRun 1: {success_rate:.1f}% ({iteration_result['passed']}/{iteration_result['total']})"
    )

    # Per-test results
    print("\nPer-Test Results:")
    test_names = [t["name"] for t in TEST_SUITES["phase3"]["tests"]]
    for test_name in test_names:
        test_result = next((r for r in iteration_result["results"] if r["test"] == test_name), None)
        if test_result:
            status = "✅" if test_result["status"] == "passed" else "❌"
            print(f"  {status} {test_name}")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = Path("logs") / f"validation_1x_{timestamp}.json"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(
            {
                "metadata": {
                    "timestamp": timestamp,
                    "n_iterations": 1,
                    "temperature": 0.8,
                    "model": "Qwen2.5-Coder-32B-Instruct",
                    "best_of_n": 3,
                },
                "summary": {
                    "success_rate": success_rate,
                },
                "iteration": iteration_result,
            },
            f,
            indent=2,
        )

    print(f"\n✅ Results saved to: {output_file}")

    # Quick assessment
    print("\nQuick Assessment:")
    if success_rate >= 80.0:
        print("  ✅ Meets or exceeds 80% goal")
    else:
        print("  ⚠️  Below 80% goal")


if __name__ == "__main__":
    asyncio.run(main())
