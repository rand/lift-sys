"""
Test the 3 persistent failures with fixed constraint detection.

This verifies that fixing constraint detection bugs improves success rate.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider

# Test specifications for the 3 persistent failures
TEST_CASES = {
    "count_words": {
        "prompt": "Create a function that counts the number of words in a string",
        "test_cases": [
            ({"text": "hello world"}, 2),
            ({"text": "one"}, 1),
            ({"text": ""}, 0),
            ({"text": "a b c d e"}, 5),
            ({"text": "  spaced  "}, 1),
        ],
    },
    "find_index": {
        "prompt": "Create a function that finds the first index of a value in a list, returning -1 if not found",
        "test_cases": [
            ({"items": [1, 2, 3], "target": 2}, 1),
            ({"items": [1, 2, 3], "target": 4}, -1),
            ({"items": [], "target": 1}, -1),
            ({"items": [1, 2, 1], "target": 1}, 0),  # Critical: FIRST occurrence
            ({"items": [5], "target": 5}, 0),
        ],
    },
    "is_valid_email": {
        "prompt": "Create a function that validates if a string is a valid email address (must have @ and . with characters in between)",
        "test_cases": [
            ({"email": "test@example.com"}, True),
            ({"email": "invalid"}, False),
            ({"email": "no@at"}, False),
            ({"email": "test@.com"}, False),  # Critical: adjacency bug
            ({"email": "@example.com"}, False),
        ],
    },
}


async def test_single_function(test_name: str, spec: dict, provider, translator, generator):
    """Test a single function with constraint detection."""
    print(f"\n{'=' * 80}")
    print(f"Testing: {test_name}")
    print(f"{'=' * 80}")
    print(f"Prompt: {spec['prompt']}\n")

    # Generate IR with constraint detection
    print("1. Generating IR with constraint detection...")
    ir = await translator.translate(spec["prompt"], language="python")
    print(f"   ✓ IR generated: {ir.signature.name}")
    print(f"   ✓ Return type: {ir.signature.returns}")

    # Show detected constraints
    print(f"\n2. Constraints detected: {len(ir.constraints)}")
    for constraint in ir.constraints:
        print(f"   - {constraint.type.value}: {constraint.description}")

    if len(ir.constraints) == 0:
        print("   ⚠️  WARNING: No constraints detected!")

    # Generate code with constraint validation
    print("\n3. Generating code with constraint validation...")
    result = await generator.generate(ir, temperature=0.3, max_retries=5)

    print(f"   ✓ Code generated ({result.metadata.get('generation_attempts', 1)} attempts)")
    print("\n   Generated code:")
    print("   " + "\n   ".join(result.source_code.split("\n")))

    # Execute test cases
    print(f"\n4. Running {len(spec['test_cases'])} test cases...")
    namespace = {}
    try:
        exec(result.source_code, namespace)
        func = namespace.get(ir.signature.name)
        if not func:
            print(f"   ✗ ERROR: Function {ir.signature.name} not found")
            return False

        passed = 0
        failed = 0
        for i, (inputs, expected) in enumerate(spec["test_cases"], 1):
            try:
                actual = func(**inputs)
                if actual == expected:
                    print(f"   ✓ Test {i}: PASS - {inputs} → {actual}")
                    passed += 1
                else:
                    print(f"   ✗ Test {i}: FAIL - {inputs} → {actual} (expected {expected})")
                    failed += 1
            except Exception as e:
                print(f"   ✗ Test {i}: ERROR - {inputs} → {e}")
                failed += 1

        print(f"\n   Results: {passed}/{len(spec['test_cases'])} passed")
        return failed == 0

    except Exception as e:
        print(f"   ✗ ERROR executing code: {e}")
        return False


async def main():
    """Run tests on all 3 failing functions."""
    print(f"\n{'#' * 80}")
    print("# Testing 3 Persistent Failures with Fixed Constraint Detection")
    print("# Baseline: 0/3 passing (before fixes)")
    print("# Goal: Improve success rate with proper constraint detection")
    print(f"{'#' * 80}\n")

    # Initialize providers
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    translator = XGrammarIRTranslator(provider)
    generator = XGrammarCodeGenerator(provider)

    # Run tests
    results = {}
    for test_name, spec in TEST_CASES.items():
        success = await test_single_function(test_name, spec, provider, translator, generator)
        results[test_name] = success

    # Summary
    print(f"\n{'#' * 80}")
    print("# SUMMARY")
    print(f"{'#' * 80}\n")

    passing = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n{'=' * 80}")
    print(f"Results: {passing}/{total} tests passing ({passing / total * 100:.1f}%)")
    print("Baseline: 0/3 passing (0.0%)")
    print(f"Improvement: +{passing} tests fixed")
    print(f"{'=' * 80}\n")

    if passing > 0:
        print("✅ SUCCESS: Constraint detection fixes improved success rate!")
    else:
        print("❌ FAILURE: Constraint detection fixes had no impact")
        print("   → Need to investigate further (validation? LLM understanding?)")


if __name__ == "__main__":
    asyncio.run(main())
