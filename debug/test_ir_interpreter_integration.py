#!/usr/bin/env python3
"""Quick test to verify IR Interpreter is integrated into code generator."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


def test_ir_interpreter_detects_missing_return():
    """Test that IR Interpreter blocks code generation for missing return."""
    print("\n" + "=" * 80)
    print("TEST: IR Interpreter Integration")
    print("=" * 80)
    print("\nTesting: count_words with missing return (should be BLOCKED)\n")

    # Create IR with missing return
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
        metadata=Metadata(origin="test"),
    )

    # Create code generator
    generator = XGrammarCodeGenerator()

    # Generate code (should be blocked by IR Interpreter)
    print("Attempting code generation...")
    result = generator.generate(ir)

    # Check result
    print(f"\nGenerated code:\n{result.source_code}")
    print(f"\nMetadata: {result.metadata}")

    if "blocked" in result.metadata.get("generator", ""):
        print("\n✅ SUCCESS: IR Interpreter correctly blocked code generation!")
        print(f"   Errors: {result.metadata.get('errors', [])}")
        return True
    else:
        print("\n❌ FAILURE: IR Interpreter did not block code generation")
        return False


def test_ir_interpreter_allows_valid_ir():
    """Test that IR Interpreter allows code generation for valid IR."""
    print("\n" + "=" * 80)
    print("Testing: factorial with valid IR (should be ALLOWED)\n")

    # Create valid IR
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Calculate factorial of a number",
            rationale=None,
        ),
        signature=SigClause(
            name="factorial",
            parameters=[
                Parameter(name="n", type_hint="int", description="Non-negative integer"),
            ],
            returns="int",
        ),
        effects=[
            EffectClause(description="Initialize result to 1"),
            EffectClause(description="For each number from 1 to n, multiply result by that number"),
            EffectClause(description="Return the result"),  # Has return!
        ],
        metadata=Metadata(origin="test"),
    )

    # Create code generator
    generator = XGrammarCodeGenerator()

    # Generate code (should be allowed)
    print("Attempting code generation...")
    result = generator.generate(ir)

    # Check result
    print(f"\nGenerated code:\n{result.source_code[:200]}...")
    print(f"\nMetadata: {result.metadata.get('generator', 'unknown')}")

    if "blocked" not in result.metadata.get("generator", ""):
        print("\n✅ SUCCESS: IR Interpreter allowed valid IR!")
        return True
    else:
        print("\n❌ FAILURE: IR Interpreter incorrectly blocked valid IR")
        print(f"   Errors: {result.metadata.get('errors', [])}")
        return False


def main():
    """Run integration tests."""
    results = []

    results.append(test_ir_interpreter_detects_missing_return())
    results.append(test_ir_interpreter_allows_valid_ir())

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n🎉 SUCCESS: IR Interpreter is working correctly!")
        return 0
    else:
        print("\n❌ FAILURE: IR Interpreter integration has issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
