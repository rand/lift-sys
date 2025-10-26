"""Static Causal Mechanism Inference (STEP-06).

This module infers causal mechanisms from code structure without execution.
Analyzes function bodies to determine mechanism types (linear, constant, etc.).

Part of H21 (SCMFitter) implementation.
"""

import ast
from dataclasses import dataclass
from enum import Enum
from typing import Any


class MechanismType(Enum):
    """Types of causal mechanisms."""

    LINEAR = "linear"  # y = a*x + b
    CONSTANT = "constant"  # y = c
    NONLINEAR = "nonlinear"  # y = f(x) where f is nonlinear
    CONDITIONAL = "conditional"  # y = f(x) with branches
    UNKNOWN = "unknown"  # Cannot infer statically


@dataclass
class InferredMechanism:
    """Result of static mechanism inference.

    Attributes:
        type: MechanismType (linear, constant, etc.)
        parameters: Dict of mechanism parameters
        confidence: 0-1 confidence score
        variables: Input variables
        expression: String representation of mechanism
    """

    type: MechanismType
    parameters: dict[str, Any]
    confidence: float  # 0-1
    variables: list[str]
    expression: str


class StaticMechanismInferrer(ast.NodeVisitor):
    """Infer causal mechanisms from function AST.

    Analyzes function bodies to determine mechanism types without execution.

    Example:
        >>> code = "def double(x): return x * 2"
        >>> tree = ast.parse(code)
        >>> inferrer = StaticMechanismInferrer()
        >>> mechanism = inferrer.infer(tree)
        >>> mechanism.type
        MechanismType.LINEAR
        >>> mechanism.parameters
        {'coefficient': 2.0, 'offset': 0.0}
    """

    def __init__(self):
        self.function_name: str | None = None
        self.parameters: list[str] = []
        self.return_expr: ast.expr | None = None

    def infer(self, tree: ast.Module) -> InferredMechanism:
        """Infer mechanism from function AST.

        Args:
            tree: AST of a function definition

        Returns:
            InferredMechanism with type and parameters

        Performance:
            - <1s for static mode (requirement)
        """
        # Find function definition
        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_def = node
                break

        if not func_def:
            return InferredMechanism(
                type=MechanismType.UNKNOWN,
                parameters={},
                confidence=0.0,
                variables=[],
                expression="",
            )

        self.function_name = func_def.name
        self.parameters = [arg.arg for arg in func_def.args.args]

        # Find return statement
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return) and node.value:
                self.return_expr = node.value
                break

        # Analyze return expression
        return self._analyze_return_expression()

    def _analyze_return_expression(self) -> InferredMechanism:
        """Analyze return expression to infer mechanism type."""
        if not self.return_expr:
            # No return or empty return
            return InferredMechanism(
                type=MechanismType.CONSTANT,
                parameters={"value": None},
                confidence=1.0,
                variables=[],
                expression="None",
            )

        expr = self.return_expr

        # Check for constant
        if isinstance(expr, ast.Constant):
            return InferredMechanism(
                type=MechanismType.CONSTANT,
                parameters={"value": expr.value},
                confidence=1.0,
                variables=[],
                expression=str(expr.value),
            )

        # Check for simple linear: x * c or c * x
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mult):
            if self._is_simple_linear_mult(expr):
                coef, var = self._extract_linear_mult(expr)
                return InferredMechanism(
                    type=MechanismType.LINEAR,
                    parameters={"coefficient": coef, "offset": 0.0, "variable": var},
                    confidence=0.9,
                    variables=[var],
                    expression=f"{coef}*{var}",
                )

        # Check for linear with addition: x * c + b or x + b
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            if self._is_linear_add(expr):
                coef, offset, var = self._extract_linear_add(expr)
                return InferredMechanism(
                    type=MechanismType.LINEAR,
                    parameters={"coefficient": coef, "offset": offset, "variable": var},
                    confidence=0.9,
                    variables=[var],
                    expression=f"{coef}*{var} + {offset}",
                )

        # Check for simple variable return: return x
        if isinstance(expr, ast.Name) and expr.id in self.parameters:
            return InferredMechanism(
                type=MechanismType.LINEAR,
                parameters={"coefficient": 1.0, "offset": 0.0, "variable": expr.id},
                confidence=1.0,
                variables=[expr.id],
                expression=expr.id,
            )

        # Check for multi-variable linear: a + b, 2*a + 3*b, etc.
        if self._is_multi_variable_linear(expr):
            coefficients, offset = self._extract_multi_variable_coefficients(expr)
            return InferredMechanism(
                type=MechanismType.LINEAR,
                parameters={"coefficients": coefficients, "offset": offset},
                confidence=0.8,
                variables=list(coefficients.keys()),
                expression=self._format_multi_linear(coefficients, offset),
            )

        # Check for power (nonlinear)
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Pow):
            return InferredMechanism(
                type=MechanismType.NONLINEAR,
                parameters={"function": "power"},
                confidence=0.7,
                variables=self._extract_variables(expr),
                expression=ast.unparse(expr),
            )

        # Check for conditional (if expression)
        if isinstance(expr, ast.IfExp):
            return InferredMechanism(
                type=MechanismType.CONDITIONAL,
                parameters={},
                confidence=0.6,
                variables=self._extract_variables(expr),
                expression=ast.unparse(expr),
            )

        # Unknown mechanism
        return InferredMechanism(
            type=MechanismType.UNKNOWN,
            parameters={},
            confidence=0.3,
            variables=self._extract_variables(expr),
            expression=ast.unparse(expr),
        )

    def _is_simple_linear_mult(self, node: ast.BinOp) -> bool:
        """Check if node is x * c or c * x."""
        left, right = node.left, node.right
        return (isinstance(left, ast.Name) and isinstance(right, ast.Constant)) or (
            isinstance(left, ast.Constant) and isinstance(right, ast.Name)
        )

    def _extract_linear_mult(self, node: ast.BinOp) -> tuple[float, str]:
        """Extract coefficient and variable from x * c or c * x."""
        if isinstance(node.left, ast.Constant):
            return float(node.left.value), node.right.id
        return float(node.right.value), node.left.id

    def _is_linear_add(self, node: ast.BinOp) -> bool:
        """Check if node is linear addition like x*c + b or x + b."""
        left, right = node.left, node.right

        # x + constant
        if isinstance(left, ast.Name) and isinstance(right, ast.Constant):
            return left.id in self.parameters

        # (x * c) + b
        if isinstance(left, ast.BinOp) and isinstance(right, ast.Constant):
            if isinstance(left.op, ast.Mult) and self._is_simple_linear_mult(left):
                return True

        return False

    def _extract_linear_add(self, node: ast.BinOp) -> tuple[float, float, str]:
        """Extract coefficient, offset, and variable from x*c + b or x + b."""
        left, right = node.left, node.right

        # x + b → coefficient=1, offset=b
        if isinstance(left, ast.Name) and isinstance(right, ast.Constant):
            return 1.0, float(right.value), left.id

        # (x * c) + b → coefficient=c, offset=b
        if isinstance(left, ast.BinOp) and isinstance(right, ast.Constant):
            coef, var = self._extract_linear_mult(left)
            return coef, float(right.value), var

        # Fallback
        return 1.0, 0.0, ""

    def _is_multi_variable_linear(self, node: ast.expr) -> bool:
        """Check if expression is multi-variable linear (a + b, 2*a + 3*b, etc.)."""
        if not isinstance(node, ast.BinOp):
            return False

        # Must be addition/subtraction at top level
        if not isinstance(node.op, (ast.Add, ast.Sub)):
            return False

        # Check both sides contain variables, linear terms, or constants
        def is_linear_term_or_constant(n: ast.expr) -> bool:
            # Allow constants (for offset terms like + 10)
            if isinstance(n, ast.Constant):
                return True
            if isinstance(n, ast.Name):
                return n.id in self.parameters
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
                return self._is_simple_linear_mult(n)
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)):
                return is_linear_term_or_constant(n.left) and is_linear_term_or_constant(n.right)
            return False

        return is_linear_term_or_constant(node.left) and is_linear_term_or_constant(node.right)

    def _extract_multi_variable_coefficients(
        self, node: ast.expr
    ) -> tuple[dict[str, float], float]:
        """Extract coefficients and offset for multi-variable linear expression.

        Returns:
            (coefficients, offset) where coefficients maps variable names to their
            coefficients, and offset is the constant term.
        """
        coefficients: dict[str, float] = {}
        offset: float = 0.0

        def extract_terms(n: ast.expr, sign: float = 1.0) -> None:
            nonlocal offset

            # Handle constants (offset terms)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, (int, float)):
                    offset += sign * float(n.value)

            elif isinstance(n, ast.Name) and n.id in self.parameters:
                coefficients[n.id] = coefficients.get(n.id, 0.0) + sign

            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
                if self._is_simple_linear_mult(n):
                    coef, var = self._extract_linear_mult(n)
                    coefficients[var] = coefficients.get(var, 0.0) + sign * coef

            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                extract_terms(n.left, sign)
                extract_terms(n.right, sign)

            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub):
                extract_terms(n.left, sign)
                extract_terms(n.right, -sign)

        extract_terms(node)
        return coefficients, offset

    def _format_multi_linear(self, coefficients: dict[str, float], offset: float = 0.0) -> str:
        """Format multi-variable linear expression."""
        terms = [f"{coef}*{var}" for var, coef in sorted(coefficients.items())]
        expr = " + ".join(terms)
        if offset != 0.0:
            expr += f" + {offset}"
        return expr

    def _extract_variables(self, node: ast.expr) -> list[str]:
        """Extract all parameter variables used in expression."""
        variables = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id in self.parameters:
                variables.add(n.id)
        return sorted(variables)


def infer_mechanism(tree: ast.Module) -> InferredMechanism:
    """Infer causal mechanism from function AST.

    Convenience function wrapping StaticMechanismInferrer.

    Args:
        tree: AST of a function definition

    Returns:
        InferredMechanism with type and parameters

    Example:
        >>> code = '''
        ... def add(a, b):
        ...     return a + b
        ... '''
        >>> tree = ast.parse(code)
        >>> mechanism = infer_mechanism(tree)
        >>> mechanism.type
        MechanismType.LINEAR
        >>> mechanism.parameters['coefficients']
        {'a': 1.0, 'b': 1.0}
    """
    inferrer = StaticMechanismInferrer()
    return inferrer.infer(tree)
