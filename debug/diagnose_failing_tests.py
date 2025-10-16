#!/usr/bin/env python3
"""Diagnose the two failing tests: find_index and get_type_name."""

import asyncio
import json

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.schema import IR_JSON_SCHEMA
from lift_sys.providers.modal_provider import ModalProvider


async def diagnose_test(name: str, prompt: str, test_cases: list):
    """Diagnose a single test by showing IR effects and generated code."""
    print("\n" + "=" * 80)
    print(f"DIAGNOSING: {name}")
    print("=" * 80)
    print(f"\nPrompt: {prompt}\n")

    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Generate IR
    print("1. Generating IR...")
    ir_json = await provider.generate_structured(
        prompt=prompt,
        schema=IR_JSON_SCHEMA,
        max_tokens=3000,
        temperature=0.3,
    )
    ir = IntermediateRepresentation.from_dict(ir_json)

    print(f"\n   Function: {ir.signature.name}")
    print(f"   Parameters: {[(p.name, p.type_hint) for p in ir.signature.parameters]}")
    print(f"   Returns: {ir.signature.returns}")
    print(f"\n   Intent: {ir.intent.summary}")

    print(f"\n   Effects ({len(ir.effects)}):")
    if not ir.effects:
        print("      ⚠️  NO EFFECTS GENERATED!")
    for i, effect in enumerate(ir.effects, 1):
        print(f"      {i}. {effect.description}")

    print(f"\n   Assertions ({len(ir.assertions)}):")
    for i, assertion in enumerate(ir.assertions, 1):
        print(f"      {i}. {assertion.predicate}")
        if assertion.rationale:
            print(f"         Rationale: {assertion.rationale}")

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
    func_name = ir.signature.name
    if func_name not in namespace:
        # Try to find it
        for name_candidate, obj in namespace.items():
            if callable(obj) and not name_candidate.startswith("_"):
                func_name = name_candidate
                break

    func = namespace.get(func_name)
    if not func:
        print(f"   ❌ Function '{func_name}' not found!")
        return

    print(f"   Testing function: {func_name}")
    passed = 0
    failed = 0

    for i, (inputs, expected) in enumerate(test_cases, 1):
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

    print(f"\n   Results: {passed}/{len(test_cases)} passed")

    return {
        "name": name,
        "ir": ir_json,
        "effects": [e.description for e in ir.effects],
        "code": result.source_code,
        "passed": passed,
        "total": len(test_cases),
    }


async def main():
    """Diagnose both failing tests."""
    results = []

    # Test 1: find_index
    result1 = await diagnose_test(
        name="find_index",
        prompt="Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found.",
        test_cases=[
            (([10, 20, 30], 20), 1),
            (([10, 20, 30], 40), -1),
            (([], 10), -1),
            (([5, 5, 5], 5), 0),
            (([1, 2, 3], 3), 2),
        ],
    )
    results.append(result1)

    # Test 2: get_type_name
    result2 = await diagnose_test(
        name="get_type_name",
        prompt="Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other').",
        test_cases=[
            ((5,), "int"),
            (("hi",), "str"),
            (([1, 2],), "list"),
            ((3.14,), "other"),
            ((True,), "other"),
        ],
    )
    results.append(result2)

    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)

    for result in results:
        print(f"\n{result['name']}:")
        print(f"  Success Rate: {result['passed']}/{result['total']}")
        print(f"  Effects Generated: {len(result['effects'])}")
        if not result['effects']:
            print(f"  ⚠️  NO EFFECTS - This is the problem!")
        print(f"  Key Issues:")
        if result["passed"] < result["total"]:
            print(f"    - {result['total'] - result['passed']} test(s) failing")
            if not result["effects"]:
                print("    - IR generated no effects to constrain logic")
            else:
                print("    - Effects may be too vague or incorrect")


if __name__ == "__main__":
    asyncio.run(main())
