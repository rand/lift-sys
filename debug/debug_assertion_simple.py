"""Simple debug script to test assertion checker with buggy get_type_name code."""

from lift_sys.ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    AssertClause,
    Parameter,
)
from lift_sys.validation import AssertionChecker


def test_buggy_get_type_name():
    """Test that buggy get_type_name is caught by assertion checker."""

    print("="*70)
    print("TESTING ASSERTION CHECKER ON BUGGY get_type_name")
    print("="*70)

    # Create IR manually (similar to unit test)
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Check the type of a value and return a type name string",
            rationale="Type checking function that returns descriptive type names"
        ),
        signature=SigClause(
            name="check_type",
            parameters=[
                Parameter(name="value", type_hint="Any")
            ],
            returns="str"
        ),
        assertions=[
            AssertClause(predicate="Returns 'int' for integer inputs", rationale=""),
            AssertClause(predicate="Returns 'str' for string inputs", rationale=""),
            AssertClause(predicate="Returns 'list' for list inputs", rationale=""),
            AssertClause(predicate="Returns 'other' for anything else", rationale=""),
        ]
    )

    print("\n[1/3] IR Created")
    print(f"  - Intent: {ir.intent.summary}")
    print(f"  - Signature: {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)})")
    print(f"  - Assertions: {len(ir.assertions)}")
    for i, assertion in enumerate(ir.assertions, 1):
        print(f"    {i}. {assertion.predicate}")

    # Buggy code (the one that should fail)
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

    print("\n[2/3] Testing Buggy Code")
    print("  Code to validate:")
    print("  " + "\n  ".join(buggy_code.strip().split("\n")))

    # Test assertion checker
    checker = AssertionChecker()
    result = checker.validate(
        code=buggy_code,
        function_name="check_type",
        ir=ir
    )

    print("\n[3/3] Validation Results")
    print(f"  - Validation passed: {result.passed}")
    print(f"  - Issues found: {len(result.issues)}")

    if result.issues:
        print("\n  Issues:")
        for i, issue in enumerate(result.issues, 1):
            print(f"    {i}. {issue.severity.upper()}: {issue.message}")
            if issue.test_input:
                print(f"       Input: {issue.test_input}")
                print(f"       Expected: {issue.expected}")
                print(f"       Actual: {issue.actual}")
    else:
        print("  ⚠️  NO ISSUES FOUND - This is the problem!")

    # Also check what test cases were generated
    print("\n[DEBUG] Test Case Generation")
    test_cases = checker._generate_test_cases_from_ir(ir)
    print(f"  - Generated {len(test_cases)} test cases from assertions:")
    for i, (inputs, expected) in enumerate(test_cases, 1):
        input_type = type(inputs[0]).__name__ if inputs else "?"
        print(f"    {i}. Input: {inputs} (type: {input_type}) → Expected: {expected}")

    # Check edge cases
    print("\n[DEBUG] Edge Case Generation")
    edge_cases = checker._generate_edge_cases(ir)
    print(f"  - Generated {len(edge_cases)} edge cases:")
    for i, (inputs, expected) in enumerate(edge_cases, 1):
        input_type = type(inputs[0]).__name__ if inputs else "?"
        print(f"    {i}. Input: {inputs} (type: {input_type}) → Expected: {expected}")

    print("\n" + "="*70)
    print("DEBUG COMPLETE")
    print("="*70)

    if not result.passed:
        print("\n✅ GOOD: Assertion checker caught the bug!")
    else:
        print("\n❌ BAD: Assertion checker did NOT catch the bug!")

    return result.passed


if __name__ == "__main__":
    test_buggy_get_type_name()
