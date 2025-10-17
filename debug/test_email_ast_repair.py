#!/usr/bin/env python3
"""Test the AST repair for email validation adjacency bug."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.ast_repair import ASTRepairEngine


def test_email_validation_repair():
    """Test that AST repair fixes the email validation adjacency bug."""
    print("\n" + "=" * 80)
    print("Testing AST Repair for Email Validation Adjacency Bug")
    print("=" * 80)

    # The buggy code that ValidatedCodeGenerator produced (all 3 attempts)
    buggy_code = '''def is_valid_email(email: str) -> bool:
    """Check if string is a valid email address.

    Args:
        email: Parameter value

    Returns:
        bool
    """
    # Algorithm: The function checks if the email contains an '@' symbol, a '.' dot, and ensures the dot comes after the '@'. It returns True if all conditions are met, otherwise False.

    # Check if email contains @ symbol
    if '@' not in email:
        # Return False if @ symbol is not found
        return False
    # Check if email contains . dot
    if '.' not in email:
        # Return False if . dot is not found
        return False
    # Check that dot comes after @
    if email.index('@') > email.rindex('.'):
        # Return False if dot does not come after @
        return False
    # Return True if all checks pass
    return True
'''

    print("\n📝 BUGGY CODE:")
    print("-" * 80)
    print(buggy_code)
    print("-" * 80)

    # Apply AST repair
    print("\n🔧 Applying AST repair...")
    repair_engine = ASTRepairEngine()
    repaired_code = repair_engine.repair(buggy_code, "is_valid_email")

    if repaired_code is None:
        print("\n❌ FAILED: AST repair returned None (no repairs detected)")
        print("\n⚠️  This means the pattern detection failed!")
        return False

    print("\n✅ AST repair detected the pattern and applied a fix!")
    print("\n📝 REPAIRED CODE:")
    print("-" * 80)
    print(repaired_code)
    print("-" * 80)

    # Test the repaired code
    print("\n🧪 Testing repaired code...")

    # Create namespace and execute repaired code
    namespace = {}
    try:
        exec(repaired_code, namespace)
    except Exception as e:
        print(f"\n❌ FAILED: Repaired code has syntax errors: {e}")
        return False

    is_valid_email = namespace["is_valid_email"]

    # Test cases
    test_cases = [
        # (input, expected_output, description)
        ("test@example.com", True, "Valid email"),
        ("test@.com", False, "Dot immediately after @ (the bug case!)"),
        ("test.com", False, "No @ symbol"),
        ("test@domain", False, "No dot"),
        ("@example.com", True, "@ at start (should still work with basic validation)"),
    ]

    failed_tests = []
    for email, expected, description in test_cases:
        result = is_valid_email(email)
        status = "✅" if result == expected else "❌"
        print(f"  {status} {description}: '{email}' -> {result} (expected {expected})")
        if result != expected:
            failed_tests.append((email, expected, result, description))

    # Check critical test case
    print("\n🎯 Critical Test Case: 'test@.com' should return False")
    result = is_valid_email("test@.com")
    if not result:
        print(f"  ✅ PASSED! Returns {result}")
    else:
        print(f"  ❌ FAILED! Returns {result} (expected False)")
        print("\n⚠️  The AST repair did not fix the adjacency bug!")
        return False

    if failed_tests:
        print(f"\n❌ FAILED: {len(failed_tests)} test(s) failed")
        for email, expected, got, description in failed_tests:
            print(f"  - {description}: '{email}' expected {expected}, got {got}")
        return False

    print("\n" + "=" * 80)
    print("✅ SUCCESS! AST repair fixed the email validation adjacency bug!")
    print("=" * 80)
    print("\n🎉 The repaired code now correctly rejects 'test@.com'")
    return True


if __name__ == "__main__":
    success = test_email_validation_repair()
    sys.exit(0 if success else 1)
