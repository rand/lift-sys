"""Test fixtures for SCMFitter (H21 - Week 2).

Provides reusable fixtures for STEP-06 through STEP-09 testing:
- STEP-06: Static mechanism inference
- STEP-07: Execution trace collection
- STEP-08: Dynamic mechanism fitting
- STEP-09: Cross-validation

All fixtures include:
- Function source code
- Parsed AST trees
- Expected mechanism types
- Sample execution traces (pandas DataFrames)
"""

import ast
from typing import Any

import pandas as pd
import pytest

# =============================================================================
# Simple Linear Functions (STEP-06: Static Analysis)
# =============================================================================


@pytest.fixture
def double_function() -> dict[str, Any]:
    """Linear function: y = 2*x (coefficient=2).

    Expected mechanism: Linear
    Expected coefficient: 2.0
    """
    code = """
def double(x):
    return x * 2
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "double",
        "params": ["x"],
        "mechanism_type": "linear",
        "coefficients": {"x": 2.0},
        "offset": 0.0,
    }


@pytest.fixture
def increment_function() -> dict[str, Any]:
    """Linear function with offset: y = x + 1.

    Expected mechanism: Linear with offset
    Expected coefficient: 1.0
    Expected offset: 1.0
    """
    code = """
def increment(x):
    return x + 1
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "increment",
        "params": ["x"],
        "mechanism_type": "linear",
        "coefficients": {"x": 1.0},
        "offset": 1.0,
    }


@pytest.fixture
def triple_offset_function() -> dict[str, Any]:
    """Linear function: y = 3*x + 5.

    Expected mechanism: Linear with offset
    Expected coefficient: 3.0
    Expected offset: 5.0
    """
    code = """
def triple_offset(x):
    return 3 * x + 5
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "triple_offset",
        "params": ["x"],
        "mechanism_type": "linear",
        "coefficients": {"x": 3.0},
        "offset": 5.0,
    }


# =============================================================================
# Constant Functions (STEP-06: Edge Cases)
# =============================================================================


@pytest.fixture
def always_zero_function() -> dict[str, Any]:
    """Constant function: y = 0.

    Expected mechanism: Constant
    Expected value: 0.0
    """
    code = """
def always_zero(x):
    return 0
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "always_zero",
        "params": ["x"],
        "mechanism_type": "constant",
        "value": 0.0,
    }


@pytest.fixture
def constant_value_function() -> dict[str, Any]:
    """Constant function with no parameters: y = 42.

    Expected mechanism: Constant
    Expected value: 42.0
    """
    code = """
def constant_value():
    return 42
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "constant_value",
        "params": [],
        "mechanism_type": "constant",
        "value": 42.0,
    }


# =============================================================================
# Nonlinear Functions (STEP-06: Complex Mechanisms)
# =============================================================================


@pytest.fixture
def square_function() -> dict[str, Any]:
    """Nonlinear function: y = x^2.

    Expected mechanism: Nonlinear (polynomial degree 2)
    """
    code = """
def square(x):
    return x ** 2
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "square",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "polynomial_degree": 2,
    }


@pytest.fixture
def exponential_function() -> dict[str, Any]:
    """Nonlinear function: y = 2^x.

    Expected mechanism: Nonlinear (exponential)
    """
    code = """
def exponential(x):
    return 2 ** x
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "exponential",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "function_type": "exponential",
    }


@pytest.fixture
def cubic_function() -> dict[str, Any]:
    """Nonlinear function: y = x^3 - 2*x.

    Expected mechanism: Nonlinear (polynomial degree 3)
    """
    code = """
def cubic(x):
    return x ** 3 - 2 * x
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "cubic",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "polynomial_degree": 3,
    }


# =============================================================================
# Multi-variable Functions (STEP-06: Multiple Parents)
# =============================================================================


@pytest.fixture
def add_function() -> dict[str, Any]:
    """Multi-variable linear: result = a + b.

    Expected mechanism: Linear
    Expected coefficients: {a: 1.0, b: 1.0}
    """
    code = """
def add(a, b):
    return a + b
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "add",
        "params": ["a", "b"],
        "mechanism_type": "linear",
        "coefficients": {"a": 1.0, "b": 1.0},
        "offset": 0.0,
    }


@pytest.fixture
def weighted_sum_function() -> dict[str, Any]:
    """Multi-variable linear: result = 2*x + 3*y.

    Expected mechanism: Linear
    Expected coefficients: {x: 2.0, y: 3.0}
    """
    code = """
def weighted_sum(x, y):
    return 2 * x + 3 * y
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "weighted_sum",
        "params": ["x", "y"],
        "mechanism_type": "linear",
        "coefficients": {"x": 2.0, "y": 3.0},
        "offset": 0.0,
    }


@pytest.fixture
def complex_combination_function() -> dict[str, Any]:
    """Complex multi-variable: result = 2*a + 3*b - 5.

    Expected mechanism: Linear
    Expected coefficients: {a: 2.0, b: 3.0}
    Expected offset: -5.0
    """
    code = """
def complex_combination(a, b):
    return 2 * a + 3 * b - 5
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "complex_combination",
        "params": ["a", "b"],
        "mechanism_type": "linear",
        "coefficients": {"a": 2.0, "b": 3.0},
        "offset": -5.0,
    }


# =============================================================================
# Conditional Functions (STEP-06: Control Flow Complexity)
# =============================================================================


@pytest.fixture
def abs_value_function() -> dict[str, Any]:
    """Conditional function: |x|.

    Expected mechanism: Nonlinear (piecewise)
    """
    code = """
def abs_value(x):
    if x < 0:
        return -x
    return x
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "abs_value",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "function_type": "piecewise",
        "has_conditionals": True,
    }


@pytest.fixture
def clamp_function() -> dict[str, Any]:
    """Conditional function: clamp(x, min, max).

    Expected mechanism: Nonlinear (piecewise)
    """
    code = """
def clamp(x, min_val, max_val):
    if x < min_val:
        return min_val
    if x > max_val:
        return max_val
    return x
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "clamp",
        "params": ["x", "min_val", "max_val"],
        "mechanism_type": "nonlinear",
        "function_type": "piecewise",
        "has_conditionals": True,
    }


@pytest.fixture
def step_function() -> dict[str, Any]:
    """Step function: 0 if x < 0 else 1.

    Expected mechanism: Nonlinear (step)
    """
    code = """
def step_function(x):
    if x < 0:
        return 0
    else:
        return 1
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "step_function",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "function_type": "step",
        "has_conditionals": True,
    }


# =============================================================================
# Execution Traces (STEP-07, STEP-08: Dynamic Fitting)
# =============================================================================


@pytest.fixture
def double_traces() -> pd.DataFrame:
    """Execution traces for double(x) = x * 2.

    Perfect linear relationship with coefficient 2.0.
    R² should be 1.0 for linear fit.
    """
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [2, 4, 6, 8, 10, 12, 14, 16, 18, 20],
        }
    )


@pytest.fixture
def double_traces_large() -> pd.DataFrame:
    """Large dataset for double(x) = x * 2.

    1000 samples for performance testing.
    Ensures <10s fitting constraint is met.
    """
    x_values = list(range(1, 1001))
    y_values = [x * 2 for x in x_values]
    return pd.DataFrame(
        {
            "x": x_values,
            "y": y_values,
        }
    )


@pytest.fixture
def increment_traces() -> pd.DataFrame:
    """Execution traces for increment(x) = x + 1.

    Linear with offset 1.0.
    R² should be 1.0 for linear fit.
    """
    return pd.DataFrame(
        {
            "x": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            "y": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        }
    )


@pytest.fixture
def add_traces() -> pd.DataFrame:
    """Execution traces for add(a, b) = a + b.

    Multi-variable linear.
    R² should be 1.0 for linear fit.
    """
    return pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
            "b": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
            "result": [2, 3, 4, 5, 6, 3, 4, 5, 6, 7],
        }
    )


@pytest.fixture
def weighted_sum_traces() -> pd.DataFrame:
    """Execution traces for weighted_sum(x, y) = 2*x + 3*y.

    Multi-variable linear with coefficients.
    R² should be 1.0 for linear fit.
    """
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
            "y": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
            "result": [5, 7, 9, 11, 13, 8, 10, 12, 14, 16],
        }
    )


@pytest.fixture
def square_traces() -> pd.DataFrame:
    """Execution traces for square(x) = x^2.

    Nonlinear relationship.
    Linear R² should be poor (<0.7).
    Polynomial R² should be 1.0.
    """
    return pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "y": [1, 4, 9, 16, 25, 36, 49, 64, 81, 100],
        }
    )


@pytest.fixture
def noisy_linear_traces() -> pd.DataFrame:
    """Execution traces with noise: y ≈ 2*x + noise.

    For testing robustness and cross-validation.
    R² should be >0.7 but <1.0.
    """
    import numpy as np

    np.random.seed(42)  # Reproducible noise

    x_values = list(range(1, 51))
    y_values = [2 * x + np.random.normal(0, 0.5) for x in x_values]

    return pd.DataFrame(
        {
            "x": x_values,
            "y": y_values,
        }
    )


# =============================================================================
# Edge Cases and Error Conditions (STEP-06, STEP-08)
# =============================================================================


@pytest.fixture
def empty_function() -> dict[str, Any]:
    """Empty function (no return statement).

    Should raise FittingError or default to None mechanism.
    """
    code = """
def empty_function(x):
    pass
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "empty_function",
        "params": ["x"],
        "mechanism_type": None,  # Invalid
    }


@pytest.fixture
def no_params_function() -> dict[str, Any]:
    """Function with no parameters.

    Should infer as root node (exogenous variable).
    """
    code = """
def get_value():
    return 10
"""
    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "get_value",
        "params": [],
        "mechanism_type": "constant",
        "value": 10.0,
        "is_exogenous": True,
    }


@pytest.fixture
def insufficient_traces() -> pd.DataFrame:
    """Traces with too few samples (< 5).

    Should raise DataError or warning for unreliable fitting.
    """
    return pd.DataFrame(
        {
            "x": [1, 2],
            "y": [2, 4],
        }
    )


@pytest.fixture
def mismatched_traces() -> pd.DataFrame:
    """Traces with mismatched columns.

    Should raise DataError when graph expects different nodes.
    """
    return pd.DataFrame(
        {
            "wrong_input": [1, 2, 3],
            "wrong_output": [2, 4, 6],
        }
    )


# =============================================================================
# Cross-Validation Fixtures (STEP-09)
# =============================================================================


@pytest.fixture
def cv_linear_traces() -> pd.DataFrame:
    """Traces for cross-validation testing.

    100 samples, clean linear relationship.
    For 80/20 train/test split validation.
    """
    x_values = list(range(1, 101))
    y_values = [2.5 * x + 1.0 for x in x_values]

    return pd.DataFrame(
        {
            "x": x_values,
            "y": y_values,
        }
    )


@pytest.fixture
def cv_polynomial_traces() -> pd.DataFrame:
    """Traces for polynomial cross-validation.

    100 samples, quadratic relationship.
    Tests overfitting detection.
    """
    x_values = list(range(1, 101))
    y_values = [0.5 * x**2 + 2 * x + 1 for x in x_values]

    return pd.DataFrame(
        {
            "x": x_values,
            "y": y_values,
        }
    )


@pytest.fixture
def cv_noisy_traces() -> pd.DataFrame:
    """Noisy traces for cross-validation robustness.

    100 samples with moderate noise.
    R² should still be >0.7 on held-out set.
    """
    import numpy as np

    np.random.seed(42)

    x_values = list(range(1, 101))
    y_values = [3 * x + 2 + np.random.normal(0, 2.0) for x in x_values]

    return pd.DataFrame(
        {
            "x": x_values,
            "y": y_values,
        }
    )


# =============================================================================
# Complex Integration Fixtures (Full Pipeline Testing)
# =============================================================================


@pytest.fixture
def pipeline_linear_example() -> dict[str, Any]:
    """Complete example for full pipeline testing.

    Combines function, AST, and traces for end-to-end tests.
    """
    code = """
def process(input_value):
    return input_value * 2.5 + 3.0
"""
    x_values = list(range(1, 21))
    y_values = [x * 2.5 + 3.0 for x in x_values]

    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "process",
        "params": ["input_value"],
        "mechanism_type": "linear",
        "coefficients": {"input_value": 2.5},
        "offset": 3.0,
        "traces": pd.DataFrame(
            {
                "input_value": x_values,
                "output": y_values,
            }
        ),
        "expected_r2": 1.0,
    }


@pytest.fixture
def pipeline_nonlinear_example() -> dict[str, Any]:
    """Complete nonlinear example for pipeline testing."""
    code = """
def transform(x):
    return x ** 2 + x
"""
    x_values = list(range(1, 21))
    y_values = [x**2 + x for x in x_values]

    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "transform",
        "params": ["x"],
        "mechanism_type": "nonlinear",
        "polynomial_degree": 2,
        "traces": pd.DataFrame(
            {
                "x": x_values,
                "output": y_values,
            }
        ),
        "expected_r2": 1.0,
    }


@pytest.fixture
def pipeline_multi_variable_example() -> dict[str, Any]:
    """Complete multi-variable example for pipeline testing."""
    code = """
def combine(a, b, c):
    return 2 * a + 3 * b - c
"""
    import itertools

    a_vals = [1, 2, 3, 4, 5]
    b_vals = [1, 2, 3, 4]
    c_vals = [1, 2, 3]

    data = []
    for a, b, c in itertools.product(a_vals, b_vals, c_vals):
        result = 2 * a + 3 * b - c
        data.append({"a": a, "b": b, "c": c, "result": result})

    return {
        "code": code,
        "ast": ast.parse(code),
        "name": "combine",
        "params": ["a", "b", "c"],
        "mechanism_type": "linear",
        "coefficients": {"a": 2.0, "b": 3.0, "c": -1.0},
        "offset": 0.0,
        "traces": pd.DataFrame(data),
        "expected_r2": 1.0,
    }
