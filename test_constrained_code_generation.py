#!/usr/bin/env python3
"""
Test script for constrained IR → Code generation with Modal + XGrammar.

This verifies that:
1. IR → Code generation uses constrained generation (not just text parsing)
2. The CODE_GENERATION_SCHEMA is properly enforced
3. Speculative parallel decoding is enabled (implicit with XGrammar)
"""

import asyncio
import os

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.modal_provider import ModalProvider


async def test_constrained_code_generation():
    """Test IR → Code generation with constrained generation."""

    print("=" * 80)
    print("Testing Constrained IR → Code Generation")
    print("=" * 80)

    # Get Modal endpoint from environment
    modal_endpoint = os.getenv("MODAL_ENDPOINT_URL")
    if not modal_endpoint:
        print("\n❌ Error: MODAL_ENDPOINT_URL environment variable not set")
        print("\nSet it with:")
        print("  export MODAL_ENDPOINT_URL=https://rand--generate.modal.run")
        return

    print(f"\nModal Endpoint: {modal_endpoint}")

    # Initialize Modal provider
    print("\n1. Initializing Modal provider...")
    provider = ModalProvider(endpoint_url=modal_endpoint)
    await provider.initialize(credentials={})

    # Check health
    print("2. Checking Modal endpoint health...")
    is_healthy = await provider.check_health()
    if not is_healthy:
        print("   ❌ Modal endpoint is not healthy")
        await provider.aclose()
        return
    print("   ✅ Modal endpoint is healthy")

    # Create a simple IR for testing
    print("\n3. Creating test IR (fibonacci function)...")
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Calculate the nth Fibonacci number using iteration",
            rationale="Iterative approach is more efficient than recursion for this problem",
        ),
        signature=SigClause(
            name="fibonacci",
            parameters=[
                Parameter(
                    name="n",
                    type_hint="int",
                    description="The position in the Fibonacci sequence (0-indexed)",
                )
            ],
            returns="int",
        ),
        assertions=[
            AssertClause(
                predicate="n >= 0",
                rationale="Fibonacci is only defined for non-negative integers",
            )
        ],
        metadata=Metadata(
            language="python",
            origin="test_script",
        ),
    )

    print(f"   Intent: {ir.intent.summary}")
    print(
        f"   Signature: {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)})"
    )
    print(f"   Assertions: {len(ir.assertions)}")

    # Initialize code generator
    print("\n4. Initializing XGrammarCodeGenerator...")
    generator = XGrammarCodeGenerator(provider=provider)

    # Check if provider supports constrained generation
    has_constrained = (
        hasattr(provider, "generate_structured") and provider.capabilities.structured_output
    )
    print(f"   Provider supports constrained generation: {has_constrained}")

    if not has_constrained:
        print("   ⚠️  Warning: Provider doesn't support constrained generation")
        print("   Will fall back to text-based generation")
    else:
        print("   ✅ Will use XGrammar-constrained generation")

    # Generate code
    print("\n5. Generating code from IR...")
    print("   (This uses constrained generation with CODE_GENERATION_SCHEMA)")
    try:
        result = await generator.generate(ir)

        print("\n" + "=" * 80)
        print("GENERATION RESULT:")
        print("=" * 80)

        # Display metadata
        print("\nMetadata:")
        print(f"  Generator: {result.metadata.get('generator')}")
        print(f"  Attempts: {result.metadata.get('attempts')}")
        print(f"  Constrained Generation: {result.metadata.get('constrained_generation')}")

        # Display generated code
        print("\nGenerated Code:")
        print("-" * 80)
        print(result.source_code)
        print("-" * 80)

        # Verify constrained generation was used
        if result.metadata.get("constrained_generation"):
            print("\n✅ SUCCESS: Constrained generation was used!")
            print("   This means:")
            print("   - XGrammar enforced CODE_GENERATION_SCHEMA during generation")
            print("   - Speculative parallel decoding was enabled (vLLM optimization)")
            print("   - Output is guaranteed to match the schema structure")
        else:
            print("\n⚠️  WARNING: Fallback to text-based generation was used")
            print("   Consider checking Modal endpoint configuration")

        # Validate the code compiles
        print("\n6. Validating generated code...")
        try:
            compile(result.source_code, "<generated>", "exec")
            print("   ✅ Code compiles successfully")
        except SyntaxError as e:
            print(f"   ❌ Syntax error: {e}")

        # Try to execute it
        print("\n7. Testing execution...")
        namespace = {}
        exec(result.source_code, namespace)
        fibonacci = namespace["fibonacci"]

        # Test cases
        test_cases = [(0, 0), (1, 1), (5, 5), (10, 55)]
        all_passed = True

        for n, expected in test_cases:
            try:
                actual = fibonacci(n)
                passed = actual == expected
                symbol = "✅" if passed else "❌"
                print(f"   {symbol} fibonacci({n}) = {actual} (expected {expected})")
                if not passed:
                    all_passed = False
            except Exception as e:
                print(f"   ❌ fibonacci({n}) raised {type(e).__name__}: {e}")
                all_passed = False

        if all_passed:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed")

    except Exception as e:
        print(f"\n❌ Error during code generation: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await provider.aclose()

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_constrained_code_generation())
