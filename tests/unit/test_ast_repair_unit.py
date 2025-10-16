"""
Pure unit tests for AST repair engine.

These tests run in <0.1s total with no external dependencies.
No Modal calls, no network, just pure logic testing.
"""

import pytest

from lift_sys.codegen.ast_repair import ASTRepairEngine


@pytest.mark.unit
@pytest.mark.ast_repair
class TestLoopReturnRepair:
    """Test loop return placement repairs."""

    def test_detects_and_fixes_return_in_loop(self):
        """Return statement inside loop should be moved after loop."""
        engine = ASTRepairEngine()

        buggy_code = """def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
        return -1"""

        result = engine.repair(buggy_code, "find_index")

        # Should have applied repair
        assert result is not None

        # Verify return -1 exists
        assert "return -1" in result

        # Verify it's after the loop (not indented as much)
        lines = result.split("\n")
        return_line = [line for line in lines if "return -1" in line][0]

        # Should have 4 spaces (function body level), not 8 (inside loop)
        assert return_line.startswith("    return -1")
        assert not return_line.startswith("        return -1")

    def test_preserves_correct_return_placement(self):
        """Correct code should not be modified."""
        engine = ASTRepairEngine()

        correct_code = """def find_index(lst: list[int], value: int) -> int:
    for index, item in enumerate(lst):
        if item == value:
            return index
    return -1"""

        result = engine.repair(correct_code, "find_index")

        # No repair needed
        assert result is None

    def test_handles_nested_loops(self):
        """Should handle nested loop structures."""
        engine = ASTRepairEngine()

        code_with_nested = """def find_in_matrix(matrix, value):
    for row in matrix:
        for item in row:
            if item == value:
                return True
    return False"""

        result = engine.repair(code_with_nested, "find_in_matrix")

        # Already correct, no repair needed
        assert result is None

    def test_preserves_returns_inside_if(self):
        """Returns inside if statements should be preserved."""
        engine = ASTRepairEngine()

        code = """def example(lst, val):
    for item in lst:
        if item == val:
            return True
    return False"""

        result = engine.repair(code, "example")

        # Already correct
        assert result is None


@pytest.mark.unit
@pytest.mark.ast_repair
class TestTypeCheckRepair:
    """Test type checking pattern repairs."""

    def test_replaces_type_name_with_isinstance(self):
        """type().__name__ should be replaced with isinstance checks."""
        engine = ASTRepairEngine()

        buggy_code = """def get_type_name(value):
    return type(value).__name__.lower()"""

        result = engine.repair(buggy_code, "get_type_name")

        # Should have applied repair
        assert result is not None

        # Should use isinstance
        assert "isinstance" in result
        assert "isinstance(value, int)" in result
        assert "isinstance(value, str)" in result
        assert "isinstance(value, list)" in result

        # Should not use type()
        assert "type(" not in result
        assert "__name__" not in result

        # Should return correct strings
        assert "'int'" in result
        assert "'str'" in result
        assert "'list'" in result
        assert "'other'" in result

    def test_preserves_correct_isinstance_usage(self):
        """Correct isinstance usage should not be modified."""
        engine = ASTRepairEngine()

        correct_code = """def check_type(value):
    if isinstance(value, int):
        return 'integer'
    elif isinstance(value, str):
        return 'string'
    else:
        return 'other'"""

        result = engine.repair(correct_code, "check_type")

        # No repair needed
        assert result is None

    def test_handles_type_without_lower(self):
        """Should handle type().__name__ without .lower()."""
        engine = ASTRepairEngine()

        code = """def get_type(value):
    return type(value).__name__"""

        result = engine.repair(code, "get_type")

        # Should still repair it
        assert result is not None
        assert "isinstance" in result


@pytest.mark.unit
@pytest.mark.ast_repair
class TestRepairEngine:
    """Test overall repair engine behavior."""

    def test_applies_multiple_repairs_if_needed(self):
        """Should apply all applicable repairs."""
        engine = ASTRepairEngine()

        # Code with both bugs
        multi_bug_code = """def bad_function(lst, val):
    for item in lst:
        if item == val:
            return True
        return False"""

        result = engine.repair(multi_bug_code, "bad_function")

        # Should fix the loop return issue
        assert result is not None
        assert "return False" in result

        # Return False should be after loop
        lines = result.split("\n")
        false_return = [line for line in lines if "return False" in line][0]
        assert false_return.startswith("    return False")

    def test_handles_syntax_errors_gracefully(self):
        """Should handle unparseable code gracefully."""
        engine = ASTRepairEngine()

        invalid_code = """def broken(
    this is not valid python"""

        # Should raise SyntaxError (can't repair unparseable code)
        with pytest.raises(SyntaxError):
            engine.repair(invalid_code, "broken")

    def test_preserves_code_semantics(self):
        """Repaired code should have same semantics."""
        engine = ASTRepairEngine()

        original = """def find_index(lst, val):
    for i, v in enumerate(lst):
        if v == val:
            return i
        return -1"""

        repaired = engine.repair(original, "find_index")

        # Should still have the same structure
        assert "enumerate(lst)" in repaired
        assert "if" in repaired
        assert "return i" in repaired
        assert "return -1" in repaired

    def test_empty_function_body(self):
        """Should handle functions with minimal bodies."""
        engine = ASTRepairEngine()

        minimal = """def noop():
    pass"""

        result = engine.repair(minimal, "noop")

        # Nothing to repair
        assert result is None


@pytest.mark.unit
@pytest.mark.ast_repair
def test_repair_engine_initialization():
    """Test that repair engine initializes correctly."""
    engine = ASTRepairEngine()

    assert engine is not None
    assert hasattr(engine, "repair")
    assert hasattr(engine, "_fix_loop_returns")
    assert hasattr(engine, "_fix_type_checks")


@pytest.mark.unit
@pytest.mark.ast_repair
def test_repair_with_context():
    """Test repair with optional context parameter."""
    engine = ASTRepairEngine()

    code = """def example():
    return 42"""

    # Should accept context parameter (even if not used yet)
    result = engine.repair(code, "example", context={"some": "data"})

    # No repair needed
    assert result is None


# Run time: Should be <0.1s for all tests
# No external dependencies, no network calls, no Modal API
# Can run these constantly during development
