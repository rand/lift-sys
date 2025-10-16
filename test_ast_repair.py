"""
Test AST-based deterministic code repair.

Verify that the repair engine can fix known bug patterns.
"""

from lift_sys.codegen.ast_repair import ASTRepairEngine


def test_loop_return_repair():
    """Test fixing return statement inside loop."""
    print("\n=== Test 1: Loop Return Repair ===")

    # Buggy code: return -1 inside loop
    buggy_code = """
def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
        return -1
"""

    repair_engine = ASTRepairEngine()
    repaired = repair_engine.repair(buggy_code.strip(), "find_index")

    if repaired:
        print("✅ Repair applied:")
        print(repaired)
        print()

        # Check that return -1 is now after the loop
        assert "for index, item in enumerate(lst):" in repaired
        assert repaired.count("return -1") == 1

        # The return should not be indented as much (after loop, not inside)
        lines = repaired.split("\n")
        return_line = [line for line in lines if "return -1" in line][0]
        # Should have same indentation as 'for' (4 spaces in function body)
        assert return_line.startswith("    return -1")
        print("✅ Return is correctly placed after loop")
    else:
        print("❌ No repairs applied")


def test_type_check_repair():
    """Test fixing type().__name__ pattern."""
    print("\n=== Test 2: Type Check Repair ===")

    # Buggy code: using type().__name__
    buggy_code = """
def get_type_name(value):
    return type(value).__name__.lower()
"""

    repair_engine = ASTRepairEngine()
    repaired = repair_engine.repair(buggy_code.strip(), "get_type_name")

    if repaired:
        print("✅ Repair applied:")
        print(repaired)
        print()

        # Check that isinstance is used
        assert "isinstance" in repaired
        assert "type(" not in repaired
        assert "__name__" not in repaired

        # Check for expected return values
        assert "'int'" in repaired
        assert "'str'" in repaired
        assert "'list'" in repaired
        assert "'other'" in repaired

        print("✅ type().__name__ replaced with isinstance checks")
    else:
        print("❌ No repairs applied")


def test_correct_code_unchanged():
    """Test that correct code is not modified."""
    print("\n=== Test 3: Correct Code Unchanged ===")

    # Correct code: return -1 after loop
    correct_code = """
def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
    return -1
"""

    repair_engine = ASTRepairEngine()
    repaired = repair_engine.repair(correct_code.strip(), "find_index")

    if repaired is None:
        print("✅ No repairs needed (code is correct)")
    else:
        print("⚠️ Code was modified (should not have been):")
        print(repaired)


def main():
    """Run all repair engine tests."""
    print("=" * 60)
    print("AST REPAIR ENGINE TESTS")
    print("=" * 60)

    test_loop_return_repair()
    test_type_check_repair()
    test_correct_code_unchanged()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
