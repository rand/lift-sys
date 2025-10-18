#!/usr/bin/env python3
"""Test IR Interpreter on the 3 persistent failures."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.validation.ir_interpreter import IRInterpreter


def test_count_words_missing_return():
    """Test detection of missing return in count_words IR."""
    print("\n" + "=" * 80)
    print("TEST 1: count_words - Missing Return")
    print("=" * 80)

    # This is the failing IR - effects count but don't return
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Count the number of words in a string",
            rationale=None,
        ),
        signature=SigClause(
            name="count_words",
            parameters=[
                Parameter(name="text", type_hint="str", description="Input string"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="Split input string by spaces into words list"),
            EffectClause(description="Iterate through words list"),
            EffectClause(description="Count the number of elements"),
            # Missing: "Return the count"
        ],
        assertions=[
            AssertClause(
                predicate="count is greater than or equal to 0",
                rationale="Word count cannot be negative",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    print(f"\n{result}")

    if result.has_errors():
        print("\n✅ SUCCESS: IR Interpreter correctly detected semantic errors!")
        print("   This IR would be BLOCKED from code generation.")
    else:
        print("\n❌ FAILURE: IR Interpreter did not detect the missing return!")

    return result.has_errors()


def test_find_index_off_by_one():
    """Test detection of off-by-one error in find_index IR."""
    print("\n" + "=" * 80)
    print("TEST 2: find_index - Off-by-One Error")
    print("=" * 80)

    # This is the failing IR - finds FIRST but might return LAST
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Find FIRST index of value in list",
            rationale=None,
        ),
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
            EffectClause(description="Store the index"),
            # Missing: "Return immediately when found"
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

    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    print(f"\n{result}")

    if result.has_errors() or result.has_warnings():
        print("\n✅ SUCCESS: IR Interpreter detected potential off-by-one issue!")
        if result.has_errors():
            print("   This IR would be BLOCKED from code generation.")
        else:
            print("   Code generation would proceed with warnings.")
    else:
        print("\n⚠️  WARNING: IR Interpreter did not detect off-by-one risk.")

    return result.has_errors() or result.has_warnings()


def test_is_valid_email_incomplete():
    """Test detection of incomplete email validation."""
    print("\n" + "=" * 80)
    print("TEST 3: is_valid_email - Incomplete Validation")
    print("=" * 80)

    # This is the failing IR - checks @ and . but not order
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Check if string is a valid email address",
            rationale=None,
        ),
        signature=SigClause(
            name="is_valid_email",
            parameters=[
                Parameter(name="email", type_hint="str", description="Email address to validate"),
            ],
            returns="bool",
        ),
        effects=[
            EffectClause(description="Check if email contains @ symbol"),
            EffectClause(description="Check if email contains . dot"),
            EffectClause(description="Return True if both checks pass, False otherwise"),
            # Missing: "Check that dot comes AFTER @"
        ],
        assertions=[
            AssertClause(
                predicate="result is True if email is valid format",
                rationale="Email must have @ and domain",
            ),
        ],
        metadata=Metadata(origin="test"),
    )

    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    print(f"\n{result}")

    if result.has_errors() or result.has_warnings():
        print("\n✅ SUCCESS: IR Interpreter detected incomplete validation!")
        if result.has_errors():
            print("   This IR would be BLOCKED from code generation.")
        else:
            print("   Code generation would proceed with warnings.")
    else:
        print("\n⚠️  WARNING: IR Interpreter did not detect validation issue.")

    return result.has_errors() or result.has_warnings()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("IR INTERPRETER: Testing on 3 Persistent Failures")
    print("=" * 80)
    print("\nGoal: Detect semantic errors in IR before code generation")
    print("- count_words: Missing return statement (should ERROR)")
    print("- find_index: Off-by-one error (should WARN)")
    print("- is_valid_email: Incomplete validation (should WARN)")

    results = {
        "count_words": test_count_words_missing_return(),
        "find_index": test_find_index_off_by_one(),
        "is_valid_email": test_is_valid_email_incomplete(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for test_name, detected in results.items():
        status = "✅ DETECTED" if detected else "❌ MISSED"
        print(f"  {test_name}: {status}")

    total_detected = sum(results.values())
    print(f"\nTotal: {total_detected}/3 issues detected ({total_detected / 3 * 100:.0f}%)")

    if total_detected == 3:
        print("\n🎉 SUCCESS! IR Interpreter detected all semantic errors!")
    elif total_detected >= 2:
        print("\n⚠️  PARTIAL SUCCESS: Most issues detected, but not all.")
    else:
        print("\n❌ FAILURE: IR Interpreter missed critical issues.")

    return 0 if total_detected >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
