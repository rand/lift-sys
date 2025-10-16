#!/usr/bin/env python3
"""
Debug letter_grade to see indentation issue.
"""

import asyncio
from pathlib import Path

from performance_benchmark import PerformanceBenchmark

from lift_sys.providers.modal_provider import ModalProvider


async def main():
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n" + "=" * 70)
    print("DEBUGGING: letter_grade")
    print("=" * 70)

    result = await benchmark.run_single_benchmark(
        "letter_grade_debug2",
        "Create a function that returns a letter grade (A, B, C, D, or F) based on a numeric score. A is 90+, B is 80-89, C is 70-79, D is 60-69, F is below 60",
    )

    if result.end_to_end_success:
        code = (
            result.code_output.source_code
            if hasattr(result.code_output, "source_code")
            else str(result.code_output)
        )
        print("\n✅ Generated code:")
        print("-" * 70)
        for i, line in enumerate(code.split("\n"), 1):
            print(f"{i:3d} | {line}")
        print("-" * 70)

        # Try to compile
        try:
            compile(code, "<generated>", "exec")
            print("\n✅ Code compiles successfully!")
        except SyntaxError as e:
            print(f"\n❌ Syntax error: {e}")
            print(f"   Line {e.lineno}: {e.text}")
    else:
        print(f"\n❌ Failed: {result.ir_to_code.error if result.ir_to_code else 'Unknown'}")


if __name__ == "__main__":
    asyncio.run(main())
