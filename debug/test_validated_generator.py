#!/usr/bin/env python3
"""Test the ValidatedCodeGenerator on the 3 persistent failures."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.execution_validator import ExecutionValidator
from lift_sys.codegen.test_generator import TestCaseGenerator
from lift_sys.codegen.validated_generator import ValidatedCodeGenerator
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.modal_provider import ModalProvider


async def test_count_words():
    """Test validated generation for count_words."""
    print("\n" + "=" * 80)
    print("TEST 1: count_words - Validated Code Generation")
    print("=" * 80)

    # Create IR
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Count the number of words in a string"),
        signature=SigClause(
            name="count_words",
            parameters=[Parameter(name="text", type_hint="str")],
            returns="int",
        ),
        effects=[
            EffectClause(description="Split input string by spaces into words list"),
            EffectClause(description="Count the number of elements"),
            EffectClause(description="Return the count"),
        ],
        assertions=[
            AssertClause(
                predicate="count is greater than or equal to 0",
                rationale="Word count cannot be negative",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    # Create provider and generators
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    base_generator = XGrammarCodeGenerator(provider)
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        test_generator=TestCaseGenerator(),
        validator=ExecutionValidator(),
        max_attempts=3,
    )

    # Generate code with validation
    print("\n📝 Generating code with validation...")
    result = await validated_generator.generate(ir)

    print(f"\n{'=' * 80}")
    print("GENERATED CODE:")
    print("=" * 80)
    print(result.source_code)
    print("=" * 80)

    # Check if validation succeeded
    validated = result.metadata.get("validated", False)
    tests_passed = result.metadata.get("tests_passed", 0)
    total_tests = result.metadata.get("total_tests", 0)

    print("\n📊 Results:")
    print(f"  Validated: {validated}")
    print(f"  Tests passed: {tests_passed}/{total_tests}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Test should pass validation
    assert validated, "count_words should pass validation"
    assert tests_passed == total_tests, f"Should pass all tests, got {tests_passed}/{total_tests}"

    print("\n✅ count_words: Validated generation successful!")
    return True


async def test_find_index():
    """Test validated generation for find_index."""
    print("\n" + "=" * 80)
    print("TEST 2: find_index - Validated Code Generation")
    print("=" * 80)

    # Create IR
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Find FIRST index of value in list"),
        signature=SigClause(
            name="find_index",
            parameters=[
                Parameter(name="items", type_hint="list[int]"),
                Parameter(name="target", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="Use enumerate to iterate through list with indices"),
            EffectClause(description="Check if item equals target"),
            EffectClause(description="Return the index immediately when found"),
            EffectClause(description="Return -1 if not found"),
        ],
        assertions=[
            AssertClause(
                predicate="returned index is valid or -1",
                rationale="Index must be valid or -1 if not found",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    # Create provider and generators
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    base_generator = XGrammarCodeGenerator(provider)
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        test_generator=TestCaseGenerator(),
        validator=ExecutionValidator(),
        max_attempts=3,
    )

    # Generate code with validation
    print("\n📝 Generating code with validation...")
    result = await validated_generator.generate(ir)

    print(f"\n{'=' * 80}")
    print("GENERATED CODE:")
    print("=" * 80)
    print(result.source_code)
    print("=" * 80)

    # Check if validation succeeded
    validated = result.metadata.get("validated", False)
    tests_passed = result.metadata.get("tests_passed", 0)
    total_tests = result.metadata.get("total_tests", 0)

    print("\n📊 Results:")
    print(f"  Validated: {validated}")
    print(f"  Tests passed: {tests_passed}/{total_tests}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Test should pass validation
    assert validated, "find_index should pass validation"
    assert tests_passed == total_tests, f"Should pass all tests, got {tests_passed}/{total_tests}"

    print("\n✅ find_index: Validated generation successful!")
    return True


async def test_is_valid_email():
    """Test validated generation for is_valid_email."""
    print("\n" + "=" * 80)
    print("TEST 3: is_valid_email - Validated Code Generation")
    print("=" * 80)

    # Create IR
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Check if string is a valid email address"),
        signature=SigClause(
            name="is_valid_email",
            parameters=[Parameter(name="email", type_hint="str")],
            returns="bool",
        ),
        effects=[
            EffectClause(description="Check if email contains @ symbol"),
            EffectClause(description="Check if email contains . dot"),
            EffectClause(description="Check that dot comes after @"),
            EffectClause(description="Return True if all checks pass, False otherwise"),
        ],
        assertions=[
            AssertClause(
                predicate="result is True if email is valid format",
                rationale="Email must have @ and domain",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    # Create provider and generators
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})
    base_generator = XGrammarCodeGenerator(provider)
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        test_generator=TestCaseGenerator(),
        validator=ExecutionValidator(),
        max_attempts=3,
    )

    # Generate code with validation
    print("\n📝 Generating code with validation...")
    result = await validated_generator.generate(ir)

    print(f"\n{'=' * 80}")
    print("GENERATED CODE:")
    print("=" * 80)
    print(result.source_code)
    print("=" * 80)

    # Check if validation succeeded
    validated = result.metadata.get("validated", False)
    tests_passed = result.metadata.get("tests_passed", 0)
    total_tests = result.metadata.get("total_tests", 0)

    print("\n📊 Results:")
    print(f"  Validated: {validated}")
    print(f"  Tests passed: {tests_passed}/{total_tests}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    # Test should pass validation
    assert validated, "is_valid_email should pass validation"
    assert tests_passed == total_tests, f"Should pass all tests, got {tests_passed}/{total_tests}"

    print("\n✅ is_valid_email: Validated generation successful!")
    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("ValidatedCodeGenerator: Testing on 3 Persistent Failures")
    print("=" * 80)
    print("\nGoal: Generate correct code that passes all tests")
    print("Note: This test requires Modal.com GPU instance to be running")

    results = {}

    try:
        results["count_words"] = await test_count_words()
    except Exception as e:
        print(f"\n❌ count_words failed: {e}")
        results["count_words"] = False

    try:
        results["find_index"] = await test_find_index()
    except Exception as e:
        print(f"\n❌ find_index failed: {e}")
        results["find_index"] = False

    try:
        results["is_valid_email"] = await test_is_valid_email()
    except Exception as e:
        print(f"\n❌ is_valid_email failed: {e}")
        results["is_valid_email"] = False

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {test_name}: {status}")

    total = sum(results.values())
    print(f"\nTotal: {total}/3 tests successful ({total / 3 * 100:.0f}%)")

    if total == 3:
        print("\n🎉 SUCCESS! ValidatedCodeGenerator works correctly!")
        print("\n   All 3 persistent failures now generate correct code:")
        print("   - count_words: Proper return statement")
        print("   - find_index: Returns FIRST match, not last")
        print("   - is_valid_email: Validates dot position correctly")
        return 0
    else:
        print("\n❌ FAILURE: Some validated generation tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
