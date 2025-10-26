# SCM Test Fixtures

**Created**: 2025-10-26
**Purpose**: Test infrastructure for H21 (SCMFitter) - Week 2 implementation
**Coverage**: STEP-06 through STEP-09

## Overview

This directory provides comprehensive test fixtures for DoWhy SCM fitting tests. All fixtures are pytest-compatible and automatically available to tests in `tests/causal/`.

## Fixture Categories

### STEP-06: Static Mechanism Inference (16 fixtures)

**Linear Functions:**
- `double_function` - y = 2*x (coefficient=2)
- `increment_function` - y = x + 1 (offset=1)
- `triple_offset_function` - y = 3*x + 5

**Constant Functions:**
- `always_zero_function` - y = 0
- `constant_value_function` - y = 42 (no parameters)

**Nonlinear Functions:**
- `square_function` - y = x²
- `exponential_function` - y = 2^x
- `cubic_function` - y = x³ - 2x

**Multi-variable Functions:**
- `add_function` - result = a + b
- `weighted_sum_function` - result = 2x + 3y
- `complex_combination_function` - result = 2a + 3b - 5

**Conditional Functions:**
- `abs_value_function` - |x| (piecewise)
- `clamp_function` - clamp(x, min, max)
- `step_function` - step function

**Edge Cases:**
- `empty_function` - no return statement
- `no_params_function` - exogenous variable

### STEP-07: Execution Trace Collection (8 fixtures)

**Clean Traces:**
- `double_traces` - 10 samples of y = 2*x
- `double_traces_large` - 1000 samples (performance testing)
- `increment_traces` - 10 samples of y = x + 1
- `add_traces` - Multi-variable: result = a + b
- `weighted_sum_traces` - Multi-variable: result = 2x + 3y
- `square_traces` - Nonlinear: y = x²

**Error Cases:**
- `insufficient_traces` - Too few samples (<5)
- `mismatched_traces` - Wrong column names

### STEP-08: Dynamic Mechanism Fitting (8 fixtures)

Reuses STEP-07 traces plus:
- `noisy_linear_traces` - 50 samples with Gaussian noise (R² >0.7 but <1.0)
- `pipeline_linear_example` - Complete example with code + traces
- `pipeline_nonlinear_example` - Complete nonlinear example
- `pipeline_multi_variable_example` - Complete multi-variable example

### STEP-09: Cross-Validation (4 fixtures)

- `cv_linear_traces` - 100 samples, clean linear (80/20 split)
- `cv_polynomial_traces` - 100 samples, quadratic
- `cv_noisy_traces` - 100 samples with noise
- `noisy_linear_traces` - Reused from STEP-08

## Shared Utilities (conftest.py)

### DoWhy Environment
- `dowhy_available` - Check if DoWhy can be imported
- `require_dowhy` - Skip test if DoWhy unavailable
- `dowhy_python_path` - Path to Python 3.11 with DoWhy

### Temporary Files
- `temp_dir` - Temporary directory (auto-cleanup)
- `temp_file` - Create temporary file

### Graph Comparison
- `graph_comparator` - Compare NetworkX graphs
  - `equal(g1, g2)` - Boolean comparison
  - `assert_equal(g1, g2, msg)` - Detailed assertion

### Performance
- `benchmark_timer` - Time operations with max_seconds constraint

### Validation
- `r_squared_calculator` - Calculate R² for fitted models
- `trace_validator` - Validate DataFrame columns

### Mock Objects
- `mock_scm` - Lightweight SCM for tests without DoWhy

### Sample Graphs
- `simple_linear_graph` - x → y
- `multi_parent_graph` - a → c, b → c
- `chain_graph` - a → b → c → d
- `diamond_graph` - a → b/c, b/c → d

## Usage Examples

### Basic Fixture Usage

```python
def test_static_inference(double_function):
    """Test static mechanism inference on linear function."""
    code = double_function["code"]
    ast_tree = double_function["ast"]

    # Expected mechanism
    assert double_function["mechanism_type"] == "linear"
    assert double_function["coefficients"]["x"] == 2.0
```

### Trace Fitting

```python
def test_dynamic_fitting(double_traces, r_squared_calculator):
    """Test fitting mechanism from traces."""
    # Fit linear model to traces
    model = fit_linear_model(double_traces)

    # Validate fit quality
    y_true = double_traces["y"].values
    y_pred = model.predict(double_traces["x"].values)
    r2 = r_squared_calculator(y_true, y_pred)

    assert r2 >= 0.7  # DoWhy constraint
```

### Cross-Validation

```python
def test_cross_validation(cv_linear_traces, benchmark_timer):
    """Test cross-validation with timing constraint."""
    with benchmark_timer(max_seconds=10):
        # Split 80/20
        train = cv_linear_traces[:80]
        test = cv_linear_traces[80:]

        # Fit on train, validate on test
        model = fit_scm(train)
        r2_test = validate_scm(model, test)

        assert r2_test >= 0.7
```

### Graph Comparison

```python
def test_graph_building(graph_comparator, simple_linear_graph):
    """Test causal graph construction."""
    builder = CausalGraphBuilder()
    constructed = builder.build(code)

    graph_comparator["assert_equal"](
        constructed,
        simple_linear_graph,
        "Graph structure mismatch"
    )
```

## Fixture Structure

All function fixtures return dictionaries with:

```python
{
    "code": str,                    # Source code
    "ast": ast.Module,              # Parsed AST
    "name": str,                    # Function name
    "params": list[str],            # Parameter names
    "mechanism_type": str,          # "linear" | "nonlinear" | "constant"
    "coefficients": dict[str, float],  # For linear mechanisms
    "offset": float,                # For linear mechanisms with offset
    "polynomial_degree": int,       # For polynomial mechanisms
    "function_type": str,           # "exponential" | "piecewise" | "step"
    "has_conditionals": bool,       # If function has if/else
    "is_exogenous": bool,           # If root node (no params)
}
```

All trace fixtures return `pandas.DataFrame` with appropriate columns.

## Performance Constraints

- **Large traces**: `double_traces_large` has 1000 samples
- **Timing**: Use `benchmark_timer(max_seconds=10)` for <10s constraint
- **Cross-validation**: 100 samples for 80/20 split

## Quality Constraints

- **R² threshold**: ≥0.7 for dynamic fitting (DoWhy requirement)
- **Clean traces**: R² = 1.0 (perfect fit)
- **Noisy traces**: R² >0.7 but <1.0 (realistic)

## Dependencies

- `pytest` - Test framework
- `pandas` - DataFrame support (DoWhy requirement)
- `networkx` - Graph structures
- `numpy` - Numerical operations (for noisy traces)
- `ast` - Python AST parsing

## Maintenance

When adding new fixtures:
1. Add to `scm_test_fixtures.py`
2. Use `@pytest.fixture` decorator
3. Include comprehensive docstring
4. Add validation test in `test_scm_fixtures.py`
5. Update this README

## Testing the Fixtures

Run validation suite:
```bash
uv run pytest tests/causal/test_scm_fixtures.py -v
```

Show coverage summary:
```bash
uv run pytest tests/causal/test_scm_fixtures.py::test_fixture_coverage_summary -s
```

## Statistics

- **Total fixtures**: 31 unique fixtures
- **STEP-06 coverage**: 16 fixtures (static inference)
- **STEP-07 coverage**: 8 fixtures (trace collection)
- **STEP-08 coverage**: 8 fixtures (dynamic fitting)
- **STEP-09 coverage**: 4 fixtures (cross-validation)
- **Shared utilities**: 13 utilities in conftest.py
- **Sample graphs**: 4 pre-built graphs

## Next Steps

These fixtures support Week 2 (H21) implementation:
- STEP-06: Use function fixtures for static analysis
- STEP-07: Use trace fixtures for execution trace testing
- STEP-08: Use combined fixtures for fitting tests
- STEP-09: Use CV fixtures for validation tests

All fixtures are ready for immediate use. Tests can be written in parallel with implementation.
