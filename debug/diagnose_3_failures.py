#!/usr/bin/env python3
"""Diagnose the 3 failing tests from temperature=0.8 run."""

import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.best_of_n_translator import BestOfNIRTranslator
from lift_sys.providers.modal_provider import ModalProvider

FAILING_TESTS = [
    {
        "name": "count_words",
        "prompt": "Create a function that counts the number of words in a string, where words are separated by spaces",
        "function_name": "count_words",
        "test_cases": [
            (("hello world",), 2),
            (("single",), 1),
            (("",), 0),
            (("one two three",), 3),
            (("  extra   spaces  ",), 2),
        ],
    },
    {
        "name": "find_index",
        "prompt": "Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found.",
        "function_name": "find_value_index",
        "test_cases": [
            (([10, 20, 30], 20), 1),
            (([10, 20, 30], 40), -1),
            (([], 10), -1),
            (([5, 5, 5], 5), 0),  # This one failed - expected 0, got 2
            (([1, 2, 3], 3), 2),
        ],
    },
    {
        "name": "is_valid_email",
        "prompt": "Create a function that checks if a string is a valid email address. Must contain @ symbol and a dot after the @",
        "function_name": "is_valid_email",
        "test_cases": [
            (("user@example.com",), True),
            (("invalid.email",), False),
            (("missing@domain",), False),
            (("test@.com",), False),  # This one failed - expected False, got True
            (("user@domain.com",), True),
        ],
    },
]


async def diagnose_test(test_info):
    """Diagnose a single failing test."""
    print("\n" + "=" * 80)
    print(f"DIAGNOSING: {test_info['name']}")
    print("=" * 80)
    print(f"Prompt: {test_info['prompt']}\n")

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Use Best-of-N translator with temp=0.8
    translator = BestOfNIRTranslator(provider=provider, n_candidates=3, temperature=0.8)

    # Generate IR
    print("1. Generating IR with Best-of-N (temp=0.8)...")
    ir = await translator.translate(test_info["prompt"])

    print(f"\n   Function: {ir.signature.name}")
    print(f"   Parameters: {[(p.name, p.type_hint) for p in ir.signature.parameters]}")
    print(f"   Returns: {ir.signature.returns}")

    print(f"\n   Effects ({len(ir.effects)}):")
    for i, effect in enumerate(ir.effects, 1):
        print(f"      {i}. {effect.description}")

    print(f"\n   Assertions ({len(ir.assertions)}):")
    for i, assertion in enumerate(ir.assertions, 1):
        print(f"      {i}. {assertion.predicate}")

    # Generate code
    print("\n2. Generating code...")
    generator = XGrammarCodeGenerator(provider=provider)
    result = await generator.generate(ir)

    print("\n" + "-" * 80)
    print("GENERATED CODE:")
    print("-" * 80)
    print(result.source_code)
    print("-" * 80)

    # Test the code
    print("\n3. Testing generated code...")
    namespace = {}
    exec(result.source_code, namespace)

    # Find the function
    func_name = test_info["function_name"]
    func = None
    for name, obj in namespace.items():
        if callable(obj) and not name.startswith("_"):
            if name == func_name or func_name in name or name in func_name:
                func = obj
                func_name = name
                break

    if not func:
        print(
            f"   ❌ Function not found! Available: {[n for n in namespace.keys() if callable(namespace[n])]}"
        )
        return

    print(f"   Testing function: {func_name}")
    passed = 0
    failed = 0

    for i, (inputs, expected) in enumerate(test_info["test_cases"], 1):
        try:
            actual = func(*inputs)
            if actual == expected:
                print(f"   ✅ Test {i}: PASS ({inputs} -> {actual})")
                passed += 1
            else:
                print(f"   ❌ Test {i}: FAIL")
                print(f"      Input: {inputs}")
                print(f"      Expected: {expected}")
                print(f"      Actual: {actual}")
                failed += 1
        except Exception as e:
            print(f"   ❌ Test {i}: ERROR - {e}")
            print(f"      Input: {inputs}")
            failed += 1

    print(f"\n   Results: {passed}/{len(test_info['test_cases'])} passed\n")

    return {
        "name": test_info["name"],
        "ir": ir,
        "code": result.source_code,
        "passed": passed,
        "total": len(test_info["test_cases"]),
    }


async def main():
    """Diagnose all 3 failing tests."""
    results = []

    for test_info in FAILING_TESTS:
        result = await diagnose_test(test_info)
        results.append(result)

    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)

    for result in results:
        print(f"\n{result['name']}: {result['passed']}/{result['total']} passed")


if __name__ == "__main__":
    asyncio.run(main())
