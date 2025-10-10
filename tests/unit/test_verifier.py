"""Unit tests for SMT verifier.

Tests cover:
- Provably true assertions (UNSAT)
- Provably false assertions (SAT with counterexample)
- Various predicate types
- Edge cases and error handling
"""
import pytest

from lift_sys.ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    Parameter,
    AssertClause,
    Metadata,
)
from lift_sys.verifier.smt_checker import SMTChecker


@pytest.mark.unit
class TestSMTChecker:
    """Unit tests for SMTChecker class."""

    def test_verify_provably_true_assertion(self):
        """Test that provably true assertions return UNSAT (no counterexample)."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test positive"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[AssertClause(predicate="x > 0")],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        result = checker.verify(ir, assumptions=[("x", 10)])
        assert result.success

    def test_verify_provably_false_assertion(self):
        """Test that provably false assertions return SAT with counterexample."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test impossible"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="x > 5"),
                AssertClause(predicate="x < 3"),  # Contradiction
            ],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        result = checker.verify(ir, assumptions=[("x", 4)])
        assert not result.success

    def test_verify_comparison_operators(self):
        """Test various comparison operators."""
        test_cases = [
            ("x > 5", [("x", 10)], True),
            ("x >= 5", [("x", 5)], True),
            ("x < 5", [("x", 3)], True),
            ("x <= 5", [("x", 5)], True),
            ("x == 5", [("x", 5)], True),
        ]

        for predicate, assumptions, should_succeed in test_cases:
            ir = IntermediateRepresentation(
                intent=IntentClause(summary="test"),
                signature=SigClause(
                    name="test",
                    parameters=[Parameter(name="x", type_hint="int")],
                    returns="int",
                ),
                effects=[],
                assertions=[AssertClause(predicate=predicate)],
                metadata=Metadata(origin="test"),
            )

            checker = SMTChecker()
            result = checker.verify(ir, assumptions=assumptions)
            assert result.success == should_succeed, f"Failed for predicate: {predicate}"

    def test_verify_multiple_variables(self):
        """Test verification with multiple variables."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test multiple vars"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int"),
                    Parameter(name="y", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="x > 0"),
                AssertClause(predicate="y > 0"),
                AssertClause(predicate="x < y"),
            ],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()

        # Valid case
        result = checker.verify(ir, assumptions=[("x", 5), ("y", 10)])
        assert result.success

        # Invalid case
        result = checker.verify(ir, assumptions=[("x", 10), ("y", 5)])
        assert not result.success

    def test_verify_arithmetic_expressions(self):
        """Test verification with arithmetic expressions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test arithmetic"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[],
            assertions=[AssertClause(predicate="a + b > 10")],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()

        # Valid case
        result = checker.verify(ir, assumptions=[("a", 6), ("b", 5)])
        assert result.success

        # Invalid case
        result = checker.verify(ir, assumptions=[("a", 2), ("b", 3)])
        assert not result.success

    def test_verify_with_no_assumptions(self):
        """Test verification without assumptions (all variables symbolic)."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[AssertClause(predicate="x > 0")],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        # Without assumptions, should check if constraint is satisfiable
        result = checker.verify(ir, assumptions=[])
        # This should succeed as x > 0 is satisfiable
        assert result.success

    def test_verify_tautology(self):
        """Test verification of tautology (always true)."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test tautology"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[AssertClause(predicate="x == x")],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        result = checker.verify(ir, assumptions=[("x", 42)])
        assert result.success

    def test_verify_contradiction(self):
        """Test verification of contradiction (always false)."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test contradiction"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="x > 10"),
                AssertClause(predicate="x < 5"),
            ],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        result = checker.verify(ir, assumptions=[])
        assert not result.success
        assert result.reason is not None

    def test_verify_boundary_conditions(self):
        """Test verification of boundary conditions."""
        test_cases = [
            ("x >= 0", [("x", 0)], True),   # Boundary
            ("x > 0", [("x", 0)], False),   # At boundary but exclusive
            ("x <= 100", [("x", 100)], True),  # Upper boundary
            ("x < 100", [("x", 100)], False),  # At upper boundary but exclusive
        ]

        for predicate, assumptions, should_succeed in test_cases:
            ir = IntermediateRepresentation(
                intent=IntentClause(summary="test"),
                signature=SigClause(
                    name="test",
                    parameters=[Parameter(name="x", type_hint="int")],
                    returns="int",
                ),
                effects=[],
                assertions=[AssertClause(predicate=predicate)],
                metadata=Metadata(origin="test"),
            )

            checker = SMTChecker()
            result = checker.verify(ir, assumptions=assumptions)
            assert result.success == should_succeed, \
                f"Failed for predicate: {predicate} with assumptions: {assumptions}"

    def test_verify_chained_comparisons(self):
        """Test verification with chained comparisons."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test range"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[
                AssertClause(predicate="x >= 0"),
                AssertClause(predicate="x <= 100"),
            ],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()

        # Within range
        result = checker.verify(ir, assumptions=[("x", 50)])
        assert result.success

        # Below range
        result = checker.verify(ir, assumptions=[("x", -5)])
        assert not result.success

        # Above range
        result = checker.verify(ir, assumptions=[("x", 105)])
        assert not result.success

    def test_verify_no_assertions(self):
        """Test verification with no assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        result = checker.verify(ir, assumptions=[("x", 42)])
        # No assertions should succeed trivially
        assert result.success

    def test_verify_invalid_predicate_syntax(self):
        """Test that invalid predicate syntax raises appropriate error."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[AssertClause(predicate="invalid syntax !!!")],
            metadata=Metadata(origin="test"),
        )

        checker = SMTChecker()
        with pytest.raises(ValueError):
            checker.verify(ir, assumptions=[("x", 42)])
