#!/usr/bin/env python3
"""
POC: Test Guidance with TypeScript code generation.

Phase 1 of llguidance migration plan.
This script demonstrates Guidance working with our TypeScript generation schemas.

Usage:
    uv run python scripts/poc/test_guidance_typescript_poc.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from guidance import gen, models
except ImportError:
    print("❌ ERROR: Guidance library not installed")
    print("Install with: uv add guidance")
    sys.exit(1)

from lift_sys.codegen.languages.typescript_schema import (
    TYPESCRIPT_GENERATION_SCHEMA,
    get_prompt_for_typescript_generation,
)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def test_typescript_poc() -> bool:
    """
    Test Guidance with TypeScript generation.

    Tests:
    1. Model loading
    2. Prompt generation
    3. Schema-constrained generation
    4. Output validation
    5. Latency measurement

    Returns:
        True if POC succeeded, False otherwise
    """
    print_section("Guidance TypeScript POC - Phase 1")

    # ============================================================================
    # Step 1: Model Loading
    # ============================================================================
    print_section("Step 1: Model Loading")
    print("Loading model: microsoft/phi-2 (CPU mode for POC)")
    print("NOTE: This is a small model for testing. Production will use larger models.")

    try:
        start_load = time.time()
        # Use a small, fast model for POC
        # Options: "microsoft/phi-2", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        lm = models.Transformers(
            "microsoft/phi-2",
            device_map="cpu",  # Use CPU for POC to avoid GPU setup
            trust_remote_code=True,
        )
        load_time = time.time() - start_load
        print(f"✅ Model loaded in {load_time:.2f}s")
    except Exception as e:
        print(f"❌ FAILED to load model: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure transformers is installed: uv add transformers torch")
        print("  2. Check model availability: microsoft/phi-2")
        print("  3. Try alternative model: TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        return False

    # ============================================================================
    # Step 2: Prompt Generation
    # ============================================================================
    print_section("Step 2: Prompt Generation")

    # Simple test case: add two numbers
    ir_summary = "A function that adds two numbers and returns the result"
    signature = "function add(a: number, b: number): number"
    effects = [
        "Accept two number parameters a and b",
        "Compute sum = a + b",
        "Return the sum",
    ]
    constraints = [
        "Must handle integer and floating-point numbers",
        "Must return a number type",
    ]

    prompt = get_prompt_for_typescript_generation(
        ir_summary=ir_summary,
        signature=signature,
        effects=effects,
        constraints=constraints,
    )

    print("Generated prompt:")
    print("-" * 60)
    print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
    print("-" * 60)

    # ============================================================================
    # Step 3: Schema-Constrained Generation
    # ============================================================================
    print_section("Step 3: Schema-Constrained Generation")
    print(f"Schema: {TYPESCRIPT_GENERATION_SCHEMA['title']}")
    print(f"Required fields: {TYPESCRIPT_GENERATION_SCHEMA['required']}")

    try:
        start_gen = time.time()

        # Apply prompt to model
        lm += prompt

        # Generate JSON output constrained by schema
        print("\nGenerating TypeScript implementation with schema constraints...")
        lm += gen(name="output", schema=TYPESCRIPT_GENERATION_SCHEMA)

        gen_time = time.time() - start_gen
        print(f"✅ Generation completed in {gen_time:.2f}s")

    except Exception as e:
        print(f"❌ FAILED during generation: {e}")
        print("\nError details:")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Error message: {str(e)}")
        return False

    # ============================================================================
    # Step 4: Output Validation
    # ============================================================================
    print_section("Step 4: Output Validation")

    try:
        # Extract generated output
        result = lm["output"]
        print("Generated output type:", type(result))

        # If result is a string, try to parse as JSON
        if isinstance(result, str):
            result = json.loads(result)

        print("\nGenerated structure:")
        print(json.dumps(result, indent=2)[:500] + "...")

        # Validate schema compliance
        validation_checks = {
            "Has 'implementation' key": "implementation" in result,
            "Has 'body_statements'": (
                "implementation" in result and "body_statements" in result["implementation"]
            ),
            "Body statements is list": (
                "implementation" in result
                and isinstance(result["implementation"].get("body_statements"), list)
            ),
            "Has at least one statement": (
                "implementation" in result
                and len(result["implementation"].get("body_statements", [])) > 0
            ),
        }

        print("\nValidation Results:")
        all_passed = True
        for check, passed in validation_checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check}")
            all_passed = all_passed and passed

        if all_passed:
            print("\n✅ All validation checks passed!")
        else:
            print("\n❌ Some validation checks failed")
            return False

    except json.JSONDecodeError as e:
        print(f"❌ FAILED to parse JSON output: {e}")
        print(f"Raw output: {result}")
        return False
    except Exception as e:
        print(f"❌ FAILED during validation: {e}")
        return False

    # ============================================================================
    # Step 5: Latency Summary
    # ============================================================================
    print_section("Step 5: Latency Summary")
    print(f"Model loading:  {load_time:.2f}s")
    print(f"Generation:     {gen_time:.2f}s")
    print(f"Total:          {load_time + gen_time:.2f}s")

    print("\nNOTE: This is a POC with a small model on CPU.")
    print("Production latency will differ with:")
    print("  - Larger models (GPT-4, Claude, Llama-70B)")
    print("  - GPU acceleration")
    print("  - Modal.com serverless infrastructure")

    # ============================================================================
    # Success Summary
    # ============================================================================
    print_section("POC Result")
    print("✅ SUCCESS: Guidance TypeScript POC completed successfully!")
    print("\nKey findings:")
    print("  1. ✅ Guidance can load and use transformers models")
    print("  2. ✅ gen() function works with JSON Schema")
    print("  3. ✅ TypeScript generation schema is compatible")
    print("  4. ✅ Output validation passes structural checks")
    print(f"  5. ✅ Latency: {gen_time:.2f}s (acceptable for POC)")

    print("\nNext steps (Phase 2):")
    print("  - Test with production-grade models")
    print("  - Compare latency vs XGrammar")
    print("  - Test with complex TypeScript patterns")
    print("  - Benchmark quality metrics")

    return True


def main() -> int:
    """Main entry point."""
    try:
        success = asyncio.run(test_typescript_poc())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
