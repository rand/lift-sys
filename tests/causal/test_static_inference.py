"""Unit tests for static mechanism inference (STEP-06).

Tests the StaticMechanismInferrer class and infer_mechanism function.
"""

import ast

from lift_sys.causal.static_inference import (
    MechanismType,
    StaticMechanismInferrer,
    infer_mechanism,
)


def test_infer_linear_simple(double_function):
    """Test inference of simple linear mechanism (y = 2*x)."""
    tree = double_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 2.0
    assert mechanism.parameters["offset"] == 0.0
    assert mechanism.parameters["variable"] == "x"
    assert mechanism.confidence >= 0.9
    assert "x" in mechanism.variables


def test_infer_linear_with_offset(increment_function):
    """Test inference of linear with offset (y = x + 1)."""
    tree = increment_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 1.0
    assert mechanism.parameters["offset"] == 1.0
    assert mechanism.confidence >= 0.9


def test_infer_linear_identity():
    """Test inference of identity function (y = x)."""
    code = """
def identity(x):
    return x
"""
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 1.0
    assert mechanism.parameters["offset"] == 0.0
    assert mechanism.confidence == 1.0


def test_infer_constant_zero(always_zero_function):
    """Test inference of constant function (y = 0)."""
    tree = always_zero_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.CONSTANT
    assert mechanism.parameters["value"] == 0
    assert mechanism.confidence == 1.0
    assert len(mechanism.variables) == 0


def test_infer_constant_value(constant_value_function):
    """Test inference of constant function (y = 42)."""
    tree = constant_value_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.CONSTANT
    assert mechanism.parameters["value"] == 42
    assert mechanism.confidence == 1.0


def test_infer_nonlinear_square(square_function):
    """Test inference of nonlinear function (y = x^2)."""
    tree = square_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.NONLINEAR
    assert mechanism.parameters["function"] == "power"
    assert "x" in mechanism.variables


def test_infer_nonlinear_exponential(exponential_function):
    """Test inference of exponential function (y = 2^x)."""
    tree = exponential_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.NONLINEAR
    assert "x" in mechanism.variables


def test_infer_multi_variable_add(add_function):
    """Test inference of multi-variable linear (z = a + b)."""
    tree = add_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert "coefficients" in mechanism.parameters
    coefficients = mechanism.parameters["coefficients"]
    assert coefficients["a"] == 1.0
    assert coefficients["b"] == 1.0
    assert set(mechanism.variables) == {"a", "b"}


def test_infer_multi_variable_weighted(weighted_sum_function):
    """Test inference of weighted sum (z = 2*x + 3*y)."""
    tree = weighted_sum_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    coefficients = mechanism.parameters["coefficients"]
    assert coefficients["x"] == 2.0
    assert coefficients["y"] == 3.0


def test_infer_conditional_abs(abs_value_function):
    """Test inference of conditional function (abs value)."""
    tree = abs_value_function["ast"]
    mechanism = infer_mechanism(tree)

    # Conditional functions are harder to analyze statically
    # We expect CONDITIONAL or UNKNOWN
    assert mechanism.type in [MechanismType.CONDITIONAL, MechanismType.UNKNOWN]
    assert "x" in mechanism.variables


def test_infer_conditional_clamp(clamp_function):
    """Test inference of conditional function (clamp)."""
    tree = clamp_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type in [MechanismType.CONDITIONAL, MechanismType.UNKNOWN]
    # Should identify at least x as a variable
    assert "x" in mechanism.variables


def test_infer_empty_function(empty_function):
    """Test inference of empty function (no return)."""
    tree = empty_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.CONSTANT
    assert mechanism.parameters["value"] is None
    assert mechanism.confidence == 1.0


def test_infer_no_params_function(no_params_function):
    """Test inference of function with no parameters."""
    tree = no_params_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.CONSTANT
    assert mechanism.parameters["value"] == 42


def test_infer_triple_offset(triple_offset_function):
    """Test inference of y = 3*x + 5."""
    tree = triple_offset_function["ast"]
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 3.0
    assert mechanism.parameters["offset"] == 5.0


def test_infer_complex_multi_variable(complex_combination_function):
    """Test inference of complex multi-variable function."""
    tree = complex_combination_function["ast"]
    mechanism = infer_mechanism(tree)

    # Should identify as multi-variable linear or unknown
    assert mechanism.type in [MechanismType.LINEAR, MechanismType.UNKNOWN]
    # Should identify at least some variables
    assert len(mechanism.variables) >= 2


def test_inferrer_class_direct():
    """Test StaticMechanismInferrer class directly."""
    code = """
def linear(x):
    return 5 * x
"""
    tree = ast.parse(code)

    inferrer = StaticMechanismInferrer()
    mechanism = inferrer.infer(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 5.0


def test_expression_unparsing():
    """Test that expressions are unparsed for display."""
    code = """
def complex_expr(x, y):
    return x**2 + y**3
"""
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    # Should have an expression string
    assert len(mechanism.expression) > 0
    assert mechanism.type == MechanismType.NONLINEAR


def test_confidence_scores():
    """Test that confidence scores are reasonable."""
    # High confidence: simple constant
    code1 = "def f(): return 42"
    m1 = infer_mechanism(ast.parse(code1))
    assert m1.confidence == 1.0

    # Medium confidence: complex expression
    code2 = "def f(x): return x**2 + x + 1"
    m2 = infer_mechanism(ast.parse(code2))
    assert 0.0 < m2.confidence < 1.0


def test_variable_extraction():
    """Test that all parameter variables are extracted."""
    code = """
def multi(a, b, c, d):
    return a + 2*b - c + 3*d
"""
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    # Should identify all four variables
    assert set(mechanism.variables) == {"a", "b", "c", "d"}


def test_performance_static_inference(benchmark_timer):
    """Test that static inference completes in <1s."""
    code = """
def complex_function(x, y, z):
    return 2*x + 3*y - 4*z + 10
"""
    tree = ast.parse(code)

    with benchmark_timer(max_seconds=1.0):
        mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR


def test_no_function_in_module():
    """Test handling of module with no functions."""
    code = "x = 42"
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.UNKNOWN
    assert mechanism.confidence == 0.0


def test_async_function():
    """Test inference for async functions."""
    code = """
async def async_double(x):
    return x * 2
"""
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 2.0


def test_nested_function():
    """Test inference for nested function (outer function analyzed)."""
    code = """
def outer(x):
    def inner(y):
        return y * 3
    return x * 2
"""
    tree = ast.parse(code)
    mechanism = infer_mechanism(tree)

    # Should analyze the outer function (returns x * 2)
    assert mechanism.type == MechanismType.LINEAR
    assert mechanism.parameters["coefficient"] == 2.0
