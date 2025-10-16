"""Check what IR is actually generated for the get_type_name prompt."""

import asyncio
from pathlib import Path

from lift_sys.providers.modal_provider import ModalProvider
from performance_benchmark import PerformanceBenchmark


async def check_ir():
    """Generate IR for get_type_name and examine assertions."""

    prompt = "Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other')."

    print("=" * 70)
    print("CHECKING IR GENERATION FOR get_type_name")
    print("=" * 70)
    print(f"\nPrompt:\n{prompt}\n")

    # Initialize provider and benchmark
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    benchmark = PerformanceBenchmark(
        provider=provider, output_dir=Path("benchmark_results"), estimate_costs=True
    )

    print("\n[1/2] Generating IR from prompt...")

    # Run just the NLP → IR step
    result = await benchmark.run_single_benchmark(test_name="get_type_name_ir_check", prompt=prompt)

    # Extract the IR
    ir = None
    if result.nlp_to_ir and hasattr(result.nlp_to_ir, "metadata"):
        ir_data = result.nlp_to_ir.metadata.get("result")
        if ir_data:
            ir = ir_data

    if not ir:
        print("  ❌ Could not extract IR from result")
        return

    print("  ✓ IR generated successfully\n")

    print("[2/2] Analyzing IR Assertions")
    print(f"  - Intent: {ir.intent.summary}")
    print(
        f"  - Signature: {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)}) -> {ir.signature.returns}"
    )
    print(f"  - Number of assertions: {len(ir.assertions)}\n")

    if ir.assertions:
        print("  Assertions:")
        for i, assertion in enumerate(ir.assertions, 1):
            print(f'    {i}. "{assertion.predicate}"')
    else:
        print("  ⚠️  NO ASSERTIONS FOUND!")

    # Check specifically for "other" clause
    has_other_clause = any("other" in assertion.predicate.lower() for assertion in ir.assertions)

    print(f"\n  Has 'other' clause: {has_other_clause}")

    if not has_other_clause:
        print("\n  🔍 FOUND THE PROBLEM!")
        print("  The IR doesn't have a 'Returns other for anything else' assertion.")
        print("  Without this, the assertion checker won't generate edge case tests")
        print("  for bool/float/dict/None, so it won't catch the isinstance(True, int) bug!")

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(check_ir())
