"""Unit tests for assertion injector."""

from lift_sys.codegen.assertion_injector import DefaultAssertionInjector
from lift_sys.ir.models import AssertClause


class TestDefaultAssertionInjector:
    """Tests for DefaultAssertionInjector."""

    def test_inject_assert_mode(self):
        """Test injecting assertion in assert mode."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(
            predicate="x > 0",
            rationale="x must be positive",
        )

        result = injector.inject(assertion, mode="assert")

        assert len(result.code_lines) == 1
        assert result.code_lines[0] == 'assert x > 0, "x must be positive"'
        assert result.original_predicate == "x > 0"
        assert result.rationale == "x must be positive"
        assert result.position == "precondition"

    def test_inject_raise_mode(self):
        """Test injecting assertion in raise mode."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(
            predicate="x > 0",
            rationale="x must be positive",
        )

        result = injector.inject(assertion, mode="raise")

        assert len(result.code_lines) == 2
        assert result.code_lines[0] == "if not (x > 0):"
        assert result.code_lines[1] == '    raise ValueError("x must be positive")'
        assert result.position == "precondition"

    def test_inject_log_mode(self):
        """Test injecting assertion in log mode."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(
            predicate="x > 0",
            rationale="x must be positive",
        )

        result = injector.inject(assertion, mode="log")

        assert len(result.code_lines) == 2
        assert result.code_lines[0] == "if not (x > 0):"
        assert result.code_lines[1] == '    logger.warning("Assertion failed: x > 0")'
        assert result.position == "precondition"

    def test_inject_comment_mode(self):
        """Test injecting assertion in comment mode."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(
            predicate="x > 0",
            rationale="x must be positive",
        )

        result = injector.inject(assertion, mode="comment")

        assert len(result.code_lines) == 1
        assert result.code_lines[0] == "# Assertion: x > 0 (x must be positive)"
        assert result.position == "precondition"

    def test_inject_without_rationale(self):
        """Test injecting assertion without rationale."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(predicate="x > 0")

        result = injector.inject(assertion, mode="assert")

        assert 'assert x > 0, "Assertion from specification"' in result.code_lines[0]
        assert result.rationale == "Assertion from specification"

    def test_infer_precondition(self):
        """Test that preconditions are inferred correctly."""
        injector = DefaultAssertionInjector()

        # References to parameters should be preconditions
        assertion = AssertClause(predicate="x > 0 and y < 100")
        result = injector.inject(assertion)
        assert result.position == "precondition"

        assertion = AssertClause(predicate="len(items) > 0")
        result = injector.inject(assertion)
        assert result.position == "precondition"

    def test_infer_postcondition(self):
        """Test that postconditions are inferred correctly."""
        injector = DefaultAssertionInjector()

        # References to return value should be postconditions
        assertion = AssertClause(predicate="return_value > 0")
        result = injector.inject(assertion)
        assert result.position == "postcondition"

        assertion = AssertClause(predicate="result is not None")
        result = injector.inject(assertion)
        assert result.position == "postcondition"

        assertion = AssertClause(predicate="output.startswith('valid')")
        result = injector.inject(assertion)
        assert result.position == "postcondition"

    def test_infer_invariant(self):
        """Test that invariants are inferred correctly."""
        injector = DefaultAssertionInjector()

        # References to self or state should be invariants
        assertion = AssertClause(predicate="self.count >= 0")
        result = injector.inject(assertion)
        assert result.position == "invariant"

        assertion = AssertClause(predicate="self.is_valid()")
        result = injector.inject(assertion)
        assert result.position == "invariant"

        assertion = AssertClause(predicate="state.is_consistent()")
        result = injector.inject(assertion)
        assert result.position == "invariant"

    def test_inject_all(self):
        """Test injecting multiple assertions."""
        injector = DefaultAssertionInjector()

        assertions = [
            AssertClause(predicate="x > 0", rationale="x must be positive"),
            AssertClause(predicate="y > 0", rationale="y must be positive"),
            AssertClause(predicate="result > 0", rationale="result must be positive"),
        ]

        results = injector.inject_all(assertions, mode="assert")

        assert len(results) == 3
        assert all(r.original_predicate for r in results)
        assert results[0].position == "precondition"
        assert results[1].position == "precondition"
        assert results[2].position == "postcondition"

    def test_inject_with_custom_indent(self):
        """Test injection with custom indentation."""
        injector = DefaultAssertionInjector(indent="  ")  # 2 spaces

        assertion = AssertClause(predicate="x > 0")
        result = injector.inject(assertion, mode="raise")

        # Check that custom indent is used
        assert result.code_lines[1].startswith("  raise")

    def test_inject_complex_predicate(self):
        """Test injecting complex predicates."""
        injector = DefaultAssertionInjector()

        # Complex logical expression
        assertion = AssertClause(
            predicate="(x > 0 and y > 0) or (x < 0 and y < 0)",
            rationale="x and y must have the same sign",
        )

        result = injector.inject(assertion, mode="assert")

        assert "(x > 0 and y > 0) or (x < 0 and y < 0)" in result.code_lines[0]
        assert "same sign" in result.code_lines[0]

    def test_inject_predicate_with_function_calls(self):
        """Test injecting predicates with function calls."""
        injector = DefaultAssertionInjector()

        assertion = AssertClause(
            predicate="isinstance(value, int)",
            rationale="value must be an integer",
        )

        result = injector.inject(assertion, mode="assert")

        assert "isinstance(value, int)" in result.code_lines[0]

    def test_inject_multiple_modes(self):
        """Test that different modes produce different code."""
        injector = DefaultAssertionInjector()
        assertion = AssertClause(predicate="x > 0")

        assert_result = injector.inject(assertion, mode="assert")
        raise_result = injector.inject(assertion, mode="raise")
        log_result = injector.inject(assertion, mode="log")
        comment_result = injector.inject(assertion, mode="comment")

        # All should have different code
        assert assert_result.code_lines != raise_result.code_lines
        assert raise_result.code_lines != log_result.code_lines
        assert log_result.code_lines != comment_result.code_lines

        # But all should have same predicate and position
        assert assert_result.original_predicate == "x > 0"
        assert raise_result.original_predicate == "x > 0"
        assert log_result.original_predicate == "x > 0"
        assert comment_result.original_predicate == "x > 0"

    def test_whitespace_handling(self):
        """Test that whitespace in predicates is handled correctly."""
        injector = DefaultAssertionInjector()

        # Predicate with extra whitespace
        assertion = AssertClause(predicate="  x > 0  ")
        result = injector.inject(assertion, mode="assert")

        # Should strip whitespace
        assert "assert x > 0," in result.code_lines[0]
