#!/usr/bin/env python3
"""Quick test to verify AST-based validation is detecting control flow bugs."""

from lift_sys.codegen.validation import CodeValidator

# Test case 1: find_index with return -1 INSIDE loop (bug)
buggy_code_1 = """
def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
        return -1  # ❌ BUG: This is INSIDE the loop!
"""

# Test case 2: find_index with return -1 AFTER loop (correct)
correct_code = """
def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
    return -1  # ✅ CORRECT: This is AFTER the loop
"""

# Test case 3: Another buggy pattern - return directly in loop body
buggy_code_2 = """
def search(lst: list, target) -> int:
    for i in range(len(lst)):
        return -1  # ❌ BUG: return directly in loop body
"""

validator = CodeValidator()

print("=" * 70)
print("TEST 1: find_index with return -1 INSIDE loop (should find error)")
print("=" * 70)
issues1 = validator.validate(buggy_code_1, "find_index", {"prompt": "find value in list"})
print(f"✓ Validation found {len(issues1)} issues")
for issue in issues1:
    print(f"  [{issue.severity}] {issue.category}: {issue.message}")

print("\n" + "=" * 70)
print("TEST 2: find_index with return -1 AFTER loop (should be clean)")
print("=" * 70)
issues2 = validator.validate(correct_code, "find_index", {"prompt": "find value in list"})
print(f"✓ Validation found {len(issues2)} issues")
for issue in issues2:
    print(f"  [{issue.severity}] {issue.category}: {issue.message}")

print("\n" + "=" * 70)
print("TEST 3: return directly in loop body (should find error)")
print("=" * 70)
issues3 = validator.validate(buggy_code_2, "search", {"prompt": "search list"})
print(f"✓ Validation found {len(issues3)} issues")
for issue in issues3:
    print(f"  [{issue.severity}] {issue.category}: {issue.message}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
if len(issues1) > 0 and len(issues2) == 0 and len(issues3) > 0:
    print("✅ SUCCESS: AST validation is working correctly!")
    print("   - Detects return -1 inside loop after if statement")
    print("   - Accepts return -1 after loop (correct pattern)")
    print("   - Detects return directly in loop body")
else:
    print("⚠️  ISSUES: AST validation may not be working as expected")
    print(f"   - Buggy code 1: {len(issues1)} issues (expected > 0)")
    print(f"   - Correct code: {len(issues2)} issues (expected = 0)")
    print(f"   - Buggy code 2: {len(issues3)} issues (expected > 0)")
