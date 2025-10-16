#!/usr/bin/env python3
"""Test AST repair on the min_max_tuple bug."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lift_sys.codegen.ast_repair import ASTRepairEngine

# The buggy code from diagnostic (nested max check)
BUGGY_CODE = """
def find_min_max(numbers: list[int]) -> tuple[int, int]:
    if not numbers:
        return (None, None)
    min_value = numbers[0]
    max_value = numbers[0]
    for number in numbers[1:]:
        if number < min_value:
            min_value = number
            if number > max_value:
                max_value = number
    return (min_value, max_value)
"""

print("=" * 70)
print("TESTING AST REPAIR ON NESTED MIN/MAX BUG")
print("=" * 70)

print("\nBUGGY CODE (before repair):")
print("-" * 70)
print(BUGGY_CODE)

# Test with values [1, 5, 3]
namespace = {}
exec(BUGGY_CODE, namespace)
buggy_func = namespace["find_min_max"]
buggy_result = buggy_func([1, 5, 3])
print("\nTest: find_min_max([1, 5, 3])")
print(f"  Buggy result:   {buggy_result}  (WRONG - max stayed at 1)")
print("  Expected:       (1, 5)")

# Apply AST repair
print("\n" + "=" * 70)
print("APPLYING AST REPAIR")
print("=" * 70)

engine = ASTRepairEngine()
repaired_code = engine.repair(BUGGY_CODE, "find_min_max")

if repaired_code:
    print("\n✅ AST REPAIR APPLIED!")
    print("\nREPAIRED CODE (after fix):")
    print("-" * 70)
    print(repaired_code)

    # Test repaired code
    namespace = {}
    exec(repaired_code, namespace)
    fixed_func = namespace["find_min_max"]
    fixed_result = fixed_func([1, 5, 3])
    print("\nTest: find_min_max([1, 5, 3])")
    print(f"  Fixed result:   {fixed_result}")
    print("  Expected:       (1, 5)")

    if fixed_result == (1, 5):
        print("\n✅ SUCCESS! AST repair fixed the bug!")
    else:
        print(f"\n❌ FAILED: Still incorrect - got {fixed_result}")
else:
    print("\n❌ No repairs applied - pattern not detected")

print("\n" + "=" * 70)
