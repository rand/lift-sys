#!/usr/bin/env python3
"""
Quick test of Phase 4 v2 AST Repair on the two known failing tests.

Tests if deterministic AST repair fixes:
1. find_index - loop return placement bug
2. get_type_name - type().__name__ pattern bug
"""

import asyncio

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.providers.modal_provider import ModalProvider

# Test prompts
FIND_INDEX_PROMPT = """Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found."""

GET_TYPE_NAME_PROMPT = """Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other')."""


async def test_repair(prompt: str, test_name: str, provider):
    """Test a single prompt and show if AST repair was applied."""
    print(f"\n{'=' * 70}")
    print(f"Testing: {test_name}")
    print(f"{'=' * 70}")
    print(f"Prompt: {prompt[:100]}...")

    # Generate IR
    translator = XGrammarIRTranslator(provider)
    result = await translator.translate(prompt)

    if not result.success:
        print(f"❌ IR generation failed: {result.error}")
        return False

    print("✓ IR generated successfully")

    # Generate code with AST repair
    generator = XGrammarCodeGenerator(provider=provider)

    code_result = await generator.generate(result.ir)

    if not code_result.success:
        print("❌ Code generation failed")
        print(f"Validation issues: {code_result.validation_issues}")
        return False

    print("✓ Code generated successfully")
    print("\nGenerated code:")
    print("-" * 70)
    print(code_result.source_code)
    print("-" * 70)

    # Check for repair indicators
    if "🔧 Applied deterministic AST repairs" in str(code_result):
        print("\n🔧 AST REPAIR WAS APPLIED!")

    # Check for specific fixes
    if test_name == "find_index":
        # Should have return -1 AFTER the loop
        lines = code_result.source_code.split("\n")
        in_loop = False
        loop_indent = None
        return_after_loop = False

        for i, line in enumerate(lines):
            if "for" in line and "enumerate" in line:
                in_loop = True
                loop_indent = len(line) - len(line.lstrip())
            elif in_loop and line.strip().startswith("return -1"):
                current_indent = len(line) - len(line.lstrip())
                if current_indent == loop_indent:
                    return_after_loop = True
                    print(f"\n✅ FIX VERIFIED: return -1 is AFTER loop (line {i + 1})")
                elif current_indent > loop_indent:
                    print(f"\n❌ BUG STILL EXISTS: return -1 is INSIDE loop (line {i + 1})")
                in_loop = False

        if return_after_loop:
            print("✅ find_index FIX SUCCESSFUL")
            return True
        else:
            print("❌ find_index STILL BROKEN")
            return False

    elif test_name == "get_type_name":
        # Should use isinstance, not type().__name__
        has_isinstance = "isinstance" in code_result.source_code
        has_type_name = "type(" in code_result.source_code and "__name__" in code_result.source_code

        if has_isinstance and not has_type_name:
            print("\n✅ FIX VERIFIED: Uses isinstance, not type().__name__")
            print("✅ get_type_name FIX SUCCESSFUL")
            return True
        elif has_type_name:
            print("\n❌ BUG STILL EXISTS: Still uses type().__name__")
            print("❌ get_type_name STILL BROKEN")
            return False
        else:
            print("\n⚠️ UNKNOWN: Unexpected code pattern")
            return False

    return True


async def main():
    """Run both tests."""
    print("=" * 70)
    print("PHASE 4 V2: AST REPAIR VERIFICATION")
    print("=" * 70)
    print("\nTesting if deterministic AST repair fixes known bugs:")
    print("1. Loop return placement (find_index)")
    print("2. Type checking pattern (get_type_name)")

    # Initialize provider
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    results = {
        "find_index": await test_repair(FIND_INDEX_PROMPT, "find_index", provider),
        "get_type_name": await test_repair(GET_TYPE_NAME_PROMPT, "get_type_name", provider),
    }

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    for test, success in results.items():
        status = "✅ FIXED" if success else "❌ STILL BROKEN"
        print(f"{test:20s}: {status}")

    total = sum(results.values())
    print(f"\nTotal fixed: {total}/2 ({total / 2 * 100:.0f}%)")

    if total == 2:
        print("\n🎉 SUCCESS! Both bugs fixed by AST repair!")
        print("Phase 4 v2 is working as expected.")
    elif total == 1:
        print("\n⚠️ PARTIAL SUCCESS: 1/2 bugs fixed")
        print("One repair rule needs debugging.")
    else:
        print("\n❌ FAILURE: Neither bug was fixed")
        print("AST repair integration may have issues.")

    return total == 2


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
