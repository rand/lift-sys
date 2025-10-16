#!/usr/bin/env python3
"""Unit test to verify the return statement fix."""

from lift_sys.codegen.generator import CodeGeneratorConfig
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator


def test_return_statement_fix():
    """Test that return statements are properly assembled."""

    # Create generator (we won't call it, just test assembly logic)
    config = CodeGeneratorConfig()
    generator = XGrammarCodeGenerator(provider=None, config=config)

    # Simulate structure (signature, docstring)
    structure = {
        "imports": [],
        "signature": "def add_two_numbers(num1: int, num2: int) -> int:",
        "docstring": '    """Add two numbers."""',
        "assertions": [],
    }

    # TEST CASE 1: Return statement with type="return" but missing keyword
    impl_json_broken = {
        "implementation": {
            "body_statements": [
                {"type": "return", "code": "num1 + num2", "rationale": "Return the sum"}
            ]
        }
    }

    code = generator._combine_structure_and_implementation(structure, impl_json_broken)
    print("=" * 60)
    print("TEST 1: Return statement (type='return', code='num1 + num2')")
    print("=" * 60)
    print(code)
    print()

    # Check that 'return' keyword is present
    assert "return num1 + num2" in code, "❌ FAIL: Missing 'return' keyword"
    assert "    return num1 + num2" in code, "❌ FAIL: Incorrect indentation"
    print("✅ PASS: Return keyword added correctly")
    print()

    # TEST CASE 2: Return statement that already has keyword
    impl_json_correct = {
        "implementation": {
            "body_statements": [
                {"type": "return", "code": "return num1 + num2", "rationale": "Return the sum"}
            ]
        }
    }

    code = generator._combine_structure_and_implementation(structure, impl_json_correct)
    print("=" * 60)
    print("TEST 2: Return statement (already has 'return')")
    print("=" * 60)
    print(code)
    print()

    # Check that 'return' keyword is not duplicated
    assert "return return" not in code, "❌ FAIL: Duplicated 'return' keyword"
    assert "    return num1 + num2" in code, "❌ FAIL: Incorrect handling"
    print("✅ PASS: Return keyword not duplicated")
    print()

    # TEST CASE 3: Assignment followed by return
    impl_json_assignment = {
        "implementation": {
            "body_statements": [
                {
                    "type": "assignment",
                    "code": "result = num1 + num2",
                    "rationale": "Calculate sum",
                },
                {"type": "return", "code": "result", "rationale": "Return the result"},
            ]
        }
    }

    code = generator._combine_structure_and_implementation(structure, impl_json_assignment)
    print("=" * 60)
    print("TEST 3: Assignment + Return")
    print("=" * 60)
    print(code)
    print()

    # Check both statements are present
    assert "result = num1 + num2" in code, "❌ FAIL: Missing assignment"
    assert "return result" in code, "❌ FAIL: Missing return"
    print("✅ PASS: Assignment and return both correct")
    print()

    # TEST CASE 4: Expression statement (not a return)
    impl_json_expression = {
        "implementation": {
            "body_statements": [
                {"type": "expression", "code": "print('Hello')", "rationale": "Print message"}
            ]
        }
    }

    code = generator._combine_structure_and_implementation(structure, impl_json_expression)
    print("=" * 60)
    print("TEST 4: Expression (not a return)")
    print("=" * 60)
    print(code)
    print()

    # Check that 'return' was NOT added
    assert "return print" not in code, "❌ FAIL: Incorrectly added 'return' to expression"
    assert "print('Hello')" in code, "❌ FAIL: Expression missing"
    print("✅ PASS: Expression handled correctly (no return added)")
    print()

    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print()
    print("The return statement fix is working correctly:")
    print("1. Adds 'return' when type='return' but keyword missing")
    print("2. Doesn't duplicate 'return' if already present")
    print("3. Works with assignment + return pattern")
    print("4. Doesn't add 'return' to non-return expressions")


if __name__ == "__main__":
    test_return_fix()
