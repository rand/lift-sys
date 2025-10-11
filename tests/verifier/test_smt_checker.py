"""Unit tests covering the SMT-based verifier."""

from __future__ import annotations

import pytest

pytest.importorskip("z3")

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.verifier.smt_checker import SMTChecker

pytestmark = pytest.mark.unit


def build_ir_with_assertions(*predicates: str) -> IntermediateRepresentation:
    return IntermediateRepresentation(
        intent=IntentClause(summary="SMT check"),
        signature=SigClause(
            name="demo",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
        effects=[EffectClause(description="noop")],
        assertions=[AssertClause(predicate=predicate) for predicate in predicates],
        metadata=Metadata(origin="unit-test"),
    )


def test_verifier_reports_unsat_for_valid_property() -> None:
    """The negation of a tautology should be UNSAT."""

    ir = build_ir_with_assertions("(x > 0) and not (x + 1 > x)")

    result = SMTChecker().verify(ir)
    status = "SAT" if result.success else "UNSAT"

    assert status == "UNSAT"
    assert result.reason == "unsat"


def test_verifier_returns_model_for_counterexample() -> None:
    """A falsifiable property yields a SAT result and counterexample."""

    ir = build_ir_with_assertions("not ((x > 5) and (x < 3))")

    result = SMTChecker().verify(ir)
    status = "SAT" if result.success else "UNSAT"

    assert status == "SAT"
    assert result.model  # A witness should be produced for the counterexample search.
