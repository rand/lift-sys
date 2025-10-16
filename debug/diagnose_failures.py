#!/usr/bin/env python3
"""
Diagnose Phase 1 failures by examining generated code.
"""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark


async def diagnose_test(test_name, prompt):
    """Run a single test and show generated code."""

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print(f"\n{'=' * 70}")
    print(f"DIAGNOSING: {test_name}")
    print(f"{'=' * 70}")
    print(f"Prompt: {prompt}")
    print(f"{'=' * 70}\n")

    result = await benchmark.run_single_benchmark(test_name=test_name, prompt=prompt)

    print(f"\nCompilation: {'✅ SUCCESS' if result.end_to_end_success else '❌ FAILED'}")

    if result.end_to_end_success:
        # Extract code
        if hasattr(result.code_output, "source_code"):
            code = result.code_output.source_code
        else:
            code = str(result.code_output)

        print("\nGenerated code:")
        print("-" * 70)
        for i, line in enumerate(code.split("\n"), 1):
            print(f"{i:3d} | {line}")
        print("-" * 70)

        # Save to file
        filename = f"debug_{test_name}.py"
        with open(filename, "w") as f:
            f.write(code)
        print(f"\n✓ Saved to: {filename}")
    else:
        print(f"\nError: {result.ir_to_code.error if result.ir_to_code else 'Unknown'}")


async def main():
    """Diagnose key failures."""

    # Diagnose filter_even (for loop indentation issue)
    await diagnose_test(
        "filter_even_diagnostic",
        "Create a function that returns a new list containing only the even numbers from the input list",
    )

    # Diagnose letter_grade (assertion issue)
    await diagnose_test(
        "letter_grade_diagnostic",
        "Create a function that returns a letter grade (A, B, C, D, or F) based on a numeric score. A is 90+, B is 80-89, C is 70-79, D is 60-69, F is below 60",
    )


if __name__ == "__main__":
    asyncio.run(main())
