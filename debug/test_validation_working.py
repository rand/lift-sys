#!/usr/bin/env python3
"""Test that Phase 2 validation is actually working."""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.schema import IR_JSON_SCHEMA
from lift_sys.providers.modal_provider import ModalProvider


async def test_validation():
    """Test validation on known failing cases."""
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    # Test case 1: get_type_name (should detect type().__name__ issue)
    print("=" * 70)
    print("TEST 1: get_type_name - Should detect type().__name__ usage")
    print("=" * 70)

    prompt1 = """Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other')."""

    ir_json1 = await provider.generate_structured(
        prompt=prompt1,
        schema=IR_JSON_SCHEMA,
        max_tokens=3000,
        temperature=0.3,
    )
    ir1 = IntermediateRepresentation.from_dict(ir_json1)

    print(f"\nIR Generated: {ir1.signature.name}")
    print(f"Effects ({len(ir1.effects)}):")
    for i, effect in enumerate(ir1.effects, 1):
        print(f"  {i}. {effect.description}")

    generator = XGrammarCodeGenerator(provider=provider)

    print("\nGenerating code with validation enabled...")
    result1 = await generator.generate(ir1, max_retries=3)

    print("\n📝 Generated Code:")
    print("-" * 70)
    print(result1.source_code)
    print("-" * 70)

    # Check if validation would flag this
    issues = generator.validator.validate(
        code=result1.source_code,
        function_name=ir1.signature.name,
        context={"prompt": ir1.intent.summary, "effects": [e.description for e in ir1.effects]},
    )

    print(f"\n🔍 Validation Issues Found: {len(issues)}")
    for issue in issues:
        print(f"  [{issue.severity}] {issue.category}: {issue.message}")
        if issue.suggestion:
            print(f"    Suggestion: {issue.suggestion}")

    # Test case 2: find_index (should detect missing return -1)
    print("\n" + "=" * 70)
    print("TEST 2: find_index - Should detect missing explicit return")
    print("=" * 70)

    prompt2 = """Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found."""

    ir_json2 = await provider.generate_structured(
        prompt=prompt2,
        schema=IR_JSON_SCHEMA,
        max_tokens=3000,
        temperature=0.3,
    )
    ir2 = IntermediateRepresentation.from_dict(ir_json2)

    print(f"\nIR Generated: {ir2.signature.name}")
    print(f"Effects ({len(ir2.effects)}):")
    for i, effect in enumerate(ir2.effects, 1):
        print(f"  {i}. {effect.description}")

    print("\nGenerating code with validation enabled...")
    result2 = await generator.generate(ir2, max_retries=3)

    print("\n📝 Generated Code:")
    print("-" * 70)
    print(result2.source_code)
    print("-" * 70)

    issues2 = generator.validator.validate(
        code=result2.source_code,
        function_name=ir2.signature.name,
        context={"prompt": ir2.intent.summary, "effects": [e.description for e in ir2.effects]},
    )

    print(f"\n🔍 Validation Issues Found: {len(issues2)}")
    for issue in issues2:
        print(f"  [{issue.severity}] {issue.category}: {issue.message}")
        if issue.suggestion:
            print(f"    Suggestion: {issue.suggestion}")

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"get_type_name: {len(issues)} validation issues")
    print(f"find_index: {len(issues2)} validation issues")

    if len(issues) > 0 or len(issues2) > 0:
        print("\n✅ Validation IS detecting issues")
        print("   However, the retry mechanism may not be working correctly")
    else:
        print("\n⚠️  Validation NOT detecting expected issues")
        print("   May need to refine validation patterns")


if __name__ == "__main__":
    asyncio.run(test_validation())
