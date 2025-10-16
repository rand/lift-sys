#!/usr/bin/env python3
"""
Quick test to validate function name auto-detection fix.

Tests the multiply function which previously failed due to name mismatch.
"""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark


async def main():
    """Test function name auto-detection with multiply test."""

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Create benchmark
    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n" + "=" * 60)
    print("TESTING FUNCTION NAME AUTO-DETECTION FIX")
    print("=" * 60)
    print("Test case: multiply (previously failed with name mismatch)")
    print("=" * 60)

    # Run multiply test
    result = await benchmark.run_single_benchmark(
        test_name="multiply_fix_test", prompt="Create a function that multiplies two numbers"
    )

    if result.code_output and result.ir_to_code and result.ir_to_code.success:
        print("\n[Compilation successful, running execution test...]")

        # Extract source code
        if hasattr(result.code_output, "source_code"):
            code = result.code_output.source_code
        elif isinstance(result.code_output, str):
            code = result.code_output
        elif result.ir_to_code.metadata.get("result"):
            gen_code = result.ir_to_code.metadata["result"]
            code = gen_code.source_code if hasattr(gen_code, "source_code") else str(gen_code)
        else:
            code = str(result.code_output)

        print("\nGenerated code:")
        print("-" * 60)
        print(code)
        print("-" * 60)

        # Test with expected name "multiply" (should auto-detect actual name)
        test_cases = [
            ((2, 3), 6),
            ((10, 5), 50),
            ((0, 10), 0),
        ]

        exec_results = benchmark.execute_generated_code(
            code=code,
            function_name="multiply",  # This might not match actual name
            test_cases=test_cases,
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
            print("✅ SUCCESS: Function name auto-detection working!")
            print(f"   All {len(exec_results)} tests passed")
        else:
            passed = sum(1 for t in exec_results if t.passed)
            print(f"⚠️  PARTIAL: {passed}/{len(exec_results)} tests passed")
        print("=" * 60)
    else:
        print("\n❌ Compilation failed, cannot test execution")
        print(f"Error: {result.ir_to_code.error if result.ir_to_code else 'Unknown'}")


if __name__ == "__main__":
    asyncio.run(main())
