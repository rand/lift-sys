"""Debug script to understand why assertion checker didn't catch get_type_name bug."""

import asyncio
import json

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.validation import AssertionChecker


async def debug_get_type_name():
    """Debug the get_type_name case."""

    # Create a simple IR for get_type_name
    prompt = "Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other')."

    print("=" * 70)
    print("DEBUGGING ASSERTION CHECKER FOR get_type_name")
    print("=" * 70)

    # Initialize provider and generator
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    generator = XGrammarCodeGenerator(provider=provider)

    # Generate IR from prompt
    print("\n[1/3] Generating IR from prompt...")
    from lift_sys.planner.planner import Planner
    planner = Planner(provider=provider)
    ir = await planner.synthesize_ir(prompt)

    print(f"  ✓ IR generated")
    print(f"  - Intent: {ir.intent.summary}")
    print(f"  - Signature: {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)})")
    print(f"  - Assertions: {len(ir.assertions)}")

    for i, assertion in enumerate(ir.assertions, 1):
        print(f"    {i}. {assertion.predicate}")

    # Test assertion checker directly
    print("\n[2/3] Testing AssertionChecker directly...")

    # Buggy code (the one that fails)
    buggy_code = """
def check_type(value):
    if isinstance(value, int):
        return 'int'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, list):
        return 'list'
    else:
        return 'other'
"""

    checker = AssertionChecker()
    result = checker.validate(
        code=buggy_code,
        function_name="check_type",
        ir=ir
    )

    print(f"  - Validation passed: {result.passed}")
    print(f"  - Issues found: {len(result.issues)}")

    if result.issues:
        print("\n  Issues:")
        for issue in result.issues:
            print(f"    - {issue.severity.upper()}: {issue.message}")
            if issue.test_input:
                print(f"      Input: {issue.test_input}")
                print(f"      Expected: {issue.expected}")
                print(f"      Actual: {issue.actual}")
    else:
        print("  ⚠️  NO ISSUES FOUND - This is the problem!")

    # Test case generation
    print("\n[3/3] Checking test case generation...")
    test_cases = checker._generate_test_cases_from_ir(ir)
    print(f"  - Generated {len(test_cases)} test cases:")

    for i, (inputs, expected) in enumerate(test_cases, 1):
        print(f"    {i}. Input: {inputs} → Expected: {expected}")

    # Check edge case generation specifically
    print("\n[4/4] Checking edge case generation...")
    edge_cases = checker._generate_edge_cases(ir)
    print(f"  - Generated {len(edge_cases)} edge cases:")

    for i, (inputs, expected) in enumerate(edge_cases, 1):
        input_type = type(inputs[0]).__name__
        print(f"    {i}. Input: {inputs} (type: {input_type}) → Expected: {expected}")

    print("\n" + "=" * 70)
    print("DEBUG COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(debug_get_type_name())
