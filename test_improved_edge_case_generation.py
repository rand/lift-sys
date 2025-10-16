"""Test improved edge case generation (without explicit 'other' assertion)."""

from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation import AssertionChecker


def test_edge_cases_without_other_assertion():
    """Test that edge cases are generated even without 'Returns other' assertion."""

    print("=" * 70)
    print("TESTING IMPROVED EDGE CASE GENERATION")
    print("=" * 70)

    # Create IR WITHOUT "Returns 'other' for anything else" assertion
    # This simulates what the planner might actually generate
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Check the type of a value using isinstance",  # has "type" + "isinstance"
            rationale="Type checking function",
        ),
        signature=SigClause(
            name="check_type", parameters=[Parameter(name="value", type_hint="Any")], returns="str"
        ),
        assertions=[
            AssertClause(predicate="Returns 'int' for integer inputs", rationale=""),
            AssertClause(predicate="Returns 'str' for string inputs", rationale=""),
            AssertClause(predicate="Returns 'list' for list inputs", rationale=""),
            # NOTE: NO "Returns 'other' for anything else" assertion!
        ],
    )

    print("\n[1/2] IR Created (WITHOUT 'other' assertion)")
    print(f"  - Intent: {ir.intent.summary}")
    print(f"  - Assertions: {len(ir.assertions)}")
    for i, assertion in enumerate(ir.assertions, 1):
        print(f"    {i}. {assertion.predicate}")

    # Test edge case generation
    checker = AssertionChecker()
    edge_cases = checker._generate_edge_cases(ir)

    print("\n[2/2] Edge Cases Generated")
    print(f"  - Generated {len(edge_cases)} edge cases:")
    for i, (inputs, expected) in enumerate(edge_cases, 1):
        input_type = type(inputs[0]).__name__ if inputs else "?"
        print(f"    {i}. Input: {inputs} (type: {input_type}) → Expected: {expected}")

    # Verify bool edge cases are present
    bool_cases = [
        (inputs, expected) for inputs, expected in edge_cases if isinstance(inputs[0], bool)
    ]

    print("\n" + "=" * 70)
    if len(edge_cases) >= 4 and len(bool_cases) >= 2:
        print("✅ SUCCESS: Edge cases generated WITHOUT explicit 'other' assertion!")
        print(f"   - Generated {len(edge_cases)} total edge cases")
        print(f"   - Including {len(bool_cases)} bool edge cases (True/False)")
        return True
    else:
        print("❌ FAILURE: Not enough edge cases generated")
        print(f"   - Expected ≥4 edge cases, got {len(edge_cases)}")
        print(f"   - Expected ≥2 bool cases, got {len(bool_cases)}")
        return False


if __name__ == "__main__":
    success = test_edge_cases_without_other_assertion()
    exit(0 if success else 1)
