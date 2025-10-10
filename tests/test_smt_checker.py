from lift_sys.ir.models import AssertClause, IntentClause, IntermediateRepresentation, Metadata, Parameter, SigClause
from lift_sys.verifier.smt_checker import SMTChecker


def build_ir():
    return IntermediateRepresentation(
        intent=IntentClause(summary="ensure positive"),
        signature=SigClause(name="foo", parameters=[Parameter(name="x", type_hint="int")], returns="int"),
        effects=[],
        assertions=[AssertClause(predicate="x > 0")],
        metadata=Metadata(origin="test"),
    )


def test_smt_checker_accepts_valid_ir():
    ir = build_ir()
    checker = SMTChecker()
    result = checker.verify(ir, assumptions=[("x", 1)])
    assert result.success
