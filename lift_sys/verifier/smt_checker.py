"""Z3 SMT solver integration for validating IR assertions."""

from __future__ import annotations

import ast
from collections.abc import Iterable
from dataclasses import dataclass

from z3 import And, BoolVal, IntVal, Not, Or, Real, RealVal, Solver

from ..ir.models import AssertClause, IntermediateRepresentation


@dataclass
class SMTResult:
    success: bool
    model: dict[str, str]
    reason: str | None = None


class _ExpressionCompiler(ast.NodeVisitor):
    def __init__(self, context: dict[str, object]) -> None:
        self.context = context

    def visit_Name(self, node: ast.Name):  # noqa: D401
        name = node.id
        if name not in self.context:
            symbol = Real(name)
            self.context[name] = symbol
        return self.context[name]

    def visit_Constant(self, node: ast.Constant):
        value = node.value
        if isinstance(value, bool):
            return BoolVal(value)
        if isinstance(value, (int, float)):
            return RealVal(value) if isinstance(value, float) else IntVal(value)
        raise ValueError(f"Unsupported constant type: {type(value)!r}")

    def visit_Compare(self, node: ast.Compare):
        left = self.visit(node.left)
        result = None
        for comparator, op in zip(node.comparators, node.ops, strict=False):
            right = self.visit(comparator)
            comparison = self._apply_comparison(op, left, right)
            result = comparison if result is None else And(result, comparison)
            left = right
        assert result is not None  # for mypy
        return result

    def visit_BoolOp(self, node: ast.BoolOp):
        values = [self.visit(value) for value in node.values]
        if isinstance(node.op, ast.And):
            return And(*values)
        if isinstance(node.op, ast.Or):
            return Or(*values)
        raise ValueError("Unsupported boolean operator")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return Not(operand)
        raise ValueError("Unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        raise ValueError("Unsupported binary operator")

    def generic_visit(self, node: ast.AST):
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

    def _apply_comparison(self, op: ast.cmpop, left, right):
        if isinstance(op, ast.Gt):
            return left > right
        if isinstance(op, ast.GtE):
            return left >= right
        if isinstance(op, ast.Lt):
            return left < right
        if isinstance(op, ast.LtE):
            return left <= right
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        raise ValueError("Unsupported comparison operator")


class SMTChecker:
    """Evaluate IR assertions with Z3 for early verification."""

    def __init__(self) -> None:
        self.solver = Solver()

    def verify(
        self, ir: IntermediateRepresentation, assumptions: Iterable[tuple[str, float]] | None = None
    ) -> SMTResult:
        self.solver.reset()
        context: dict[str, object] = {}
        if assumptions:
            for name, value in assumptions:
                context[name] = Real(name)
                self.solver.add(context[name] == value)

        compiler = _ExpressionCompiler(context)
        for assertion in ir.assertions:
            expr = self._compile_assertion(assertion, compiler)
            self.solver.add(expr)

        sat_result = self.solver.check()
        result_text = str(sat_result)
        success = result_text == "sat"
        model = (
            {str(d): str(self.solver.model()[d]) for d in self.solver.model().decls()}
            if success
            else {}
        )
        if success:
            reason = None
        elif result_text == "unknown":
            reason_unknown = self.solver.reason_unknown()
            reason = f"unknown: {reason_unknown}" if reason_unknown else "unknown"
        else:
            reason = result_text
        return SMTResult(success=success, model=model, reason=reason)

    def _compile_assertion(self, assertion: AssertClause, compiler: _ExpressionCompiler):
        try:
            tree = ast.parse(assertion.predicate, mode="eval")
        except SyntaxError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid predicate syntax: {assertion.predicate}") from exc
        return compiler.visit(tree.body)


__all__ = ["SMTChecker", "SMTResult"]
