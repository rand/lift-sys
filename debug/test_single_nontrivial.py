#!/usr/bin/env python3
"""
Test a single non-trivial test case to verify infrastructure.
"""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark


async def main():
    """Test letter_grade function."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n" + "=" * 60)
    print("SINGLE NON-TRIVIAL TEST: Letter Grade")
    print("=" * 60)

    # Test letter grade (if-elif-else)
    test_case = {
        "name": "letter_grade",
        "prompt": "Create a function that returns a letter grade (A, B, C, D, or F) based on a numeric score. A is 90+, B is 80-89, C is 70-79, D is 60-69, F is below 60",
        "function_name": "get_grade",
        "test_cases": [
            ((95,), "A"),
            ((85,), "B"),
            ((75,), "C"),
            ((65,), "D"),
            ((55,), "F"),
        ],
    }

    result = await benchmark.run_single_benchmark(
        test_name=test_case["name"], prompt=test_case["prompt"]
    )

    if result.end_to_end_success:
        print("\n✅ Compilation successful")

        # Extract code
        if hasattr(result.code_output, "source_code"):
            code = result.code_output.source_code
        else:
            code = str(result.code_output)

        print("\nGenerated code:")
        print("-" * 60)
        for i, line in enumerate(code.split("\n")[:25], 1):  # First 25 lines
            print(f"{i:3d} | {line}")
        print("-" * 60)

        # Execute tests
        exec_results = benchmark.execute_generated_code(
            code=code, function_name=test_case["function_name"], test_cases=test_case["test_cases"]
        )

        print("\nExecution results:")
        for exec_result in exec_results:
            if exec_result.passed:
                print(f"  ✅ {exec_result.test_name}: {exec_result.actual}")
            else:
                print(f"  ❌ {exec_result.test_name}: {exec_result.error}")

        all_passed = all(t.passed for t in exec_results)

        print("\n" + "=" * 60)
        if all_passed:
            print("✅ SUCCESS: All tests passed!")
        else:
            passed = sum(1 for t in exec_results if t.passed)
            print(f"⚠️  PARTIAL: {passed}/{len(exec_results)} tests passed")
        print("=" * 60)
    else:
        print("\n❌ Compilation failed")
        if result.ir_to_code:
            print(f"Error: {result.ir_to_code.error}")


if __name__ == "__main__":
    asyncio.run(main())
