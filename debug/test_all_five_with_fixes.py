#!/usr/bin/env python3
"""
Test max_of_two with both fixes applied:
1. Function name auto-detection
2. Indentation bug fix

Expected: max_of_two should compile AND execute successfully
"""

import asyncio
from pathlib import Path

from performance_benchmark import PerformanceBenchmark

from lift_sys.providers.modal_provider import ModalProvider


async def main():
    """Test max_of_two with fixes."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n" + "=" * 60)
    print("TESTING MAX_OF_TWO WITH FIXES")
    print("=" * 60)
    print("Expected: Compilation ✅ + Execution ✅")
    print("=" * 60)

    # Run max_of_two test
    result = await benchmark.run_single_benchmark(
        test_name="max_of_two_fixed",
        prompt="Create a function that returns the maximum of two numbers",
    )

    if result.code_output and result.ir_to_code and result.ir_to_code.success:
        print("\n✅ COMPILATION SUCCESS!")

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
        for i, line in enumerate(code.split("\n"), 1):
            print(f"{i:3d} | {line}")
        print("-" * 60)

        # Test execution with function name auto-detection
        test_cases = [
            ((5, 10), 10),
            ((20, 15), 20),
            ((5, 5), 5),
        ]

        exec_results = benchmark.execute_generated_code(
            code=code,
            function_name="max_of_two",  # Will auto-detect if different
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
            print("🎉 SUCCESS: max_of_two works with both fixes!")
            print("   Compilation: ✅")
            print(f"   Execution: ✅ All {len(exec_results)} tests passed")
            print("\n   Both bugs are now FIXED:")
            print("   ✅ Indentation bug resolved")
            print("   ✅ Function name auto-detection working")
        else:
            passed = sum(1 for t in exec_results if t.passed)
            print(f"⚠️  PARTIAL: {passed}/{len(exec_results)} tests passed")
        print("=" * 60)
    else:
        print("\n❌ Compilation failed")
        print(f"Error: {result.ir_to_code.error if result.ir_to_code else 'Unknown'}")


if __name__ == "__main__":
    asyncio.run(main())
