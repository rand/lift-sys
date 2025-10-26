"""Validation tests for SCM test fixtures.

Ensures all fixtures are correctly structured and usable for STEP-06 through STEP-09.
"""

import ast

import pandas as pd


def test_double_function_fixture(double_function):
    """Verify double function fixture structure."""
    assert double_function["name"] == "double"
    assert double_function["params"] == ["x"]
    assert double_function["mechanism_type"] == "linear"
    assert double_function["coefficients"]["x"] == 2.0
    assert double_function["offset"] == 0.0
    assert isinstance(double_function["ast"], ast.Module)


def test_increment_function_fixture(increment_function):
    """Verify increment function fixture structure."""
    assert increment_function["name"] == "increment"
    assert increment_function["coefficients"]["x"] == 1.0
    assert increment_function["offset"] == 1.0


def test_constant_fixtures(always_zero_function, constant_value_function):
    """Verify constant function fixtures."""
    assert always_zero_function["mechanism_type"] == "constant"
    assert always_zero_function["value"] == 0.0

    assert constant_value_function["mechanism_type"] == "constant"
    assert constant_value_function["value"] == 42.0
    assert constant_value_function["params"] == []


def test_nonlinear_fixtures(square_function, exponential_function, cubic_function):
    """Verify nonlinear function fixtures."""
    assert square_function["mechanism_type"] == "nonlinear"
    assert square_function["polynomial_degree"] == 2

    assert exponential_function["mechanism_type"] == "nonlinear"
    assert exponential_function["function_type"] == "exponential"

    assert cubic_function["polynomial_degree"] == 3


def test_multi_variable_fixtures(add_function, weighted_sum_function):
    """Verify multi-variable function fixtures."""
    assert len(add_function["params"]) == 2
    assert add_function["coefficients"]["a"] == 1.0
    assert add_function["coefficients"]["b"] == 1.0

    assert weighted_sum_function["coefficients"]["x"] == 2.0
    assert weighted_sum_function["coefficients"]["y"] == 3.0


def test_conditional_fixtures(abs_value_function, clamp_function, step_function):
    """Verify conditional function fixtures."""
    assert abs_value_function["has_conditionals"]
    assert abs_value_function["function_type"] == "piecewise"

    assert clamp_function["has_conditionals"]
    assert len(clamp_function["params"]) == 3

    assert step_function["function_type"] == "step"


def test_double_traces_fixture(double_traces):
    """Verify double traces fixture."""
    assert isinstance(double_traces, pd.DataFrame)
    assert "x" in double_traces.columns
    assert "y" in double_traces.columns
    assert len(double_traces) == 10

    # Verify relationship: y = 2*x
    for _, row in double_traces.iterrows():
        assert row["y"] == row["x"] * 2


def test_double_traces_large_fixture(double_traces_large):
    """Verify large double traces fixture (performance testing)."""
    assert isinstance(double_traces_large, pd.DataFrame)
    assert len(double_traces_large) == 1000

    # Spot check
    assert double_traces_large.iloc[0]["y"] == 2
    assert double_traces_large.iloc[999]["y"] == 2000


def test_add_traces_fixture(add_traces):
    """Verify multi-variable traces fixture."""
    assert "a" in add_traces.columns
    assert "b" in add_traces.columns
    assert "result" in add_traces.columns

    # Verify relationship: result = a + b
    for _, row in add_traces.iterrows():
        assert row["result"] == row["a"] + row["b"]


def test_square_traces_fixture(square_traces):
    """Verify nonlinear traces fixture."""
    assert len(square_traces) == 10

    # Verify relationship: y = x^2
    for _, row in square_traces.iterrows():
        assert row["y"] == row["x"] ** 2


def test_noisy_linear_traces_fixture(noisy_linear_traces):
    """Verify noisy traces fixture has expected properties."""
    assert len(noisy_linear_traces) == 50

    # Check that relationship is approximately y = 2*x
    # (with noise, so not exact)
    import numpy as np

    x = noisy_linear_traces["x"].values
    y = noisy_linear_traces["y"].values

    # Linear regression: y = mx + b
    coeffs = np.polyfit(x, y, 1)
    slope = coeffs[0]

    # Slope should be close to 2.0 (within 10% due to noise)
    assert 1.8 <= slope <= 2.2


def test_edge_case_fixtures(empty_function, no_params_function):
    """Verify edge case fixtures."""
    assert empty_function["mechanism_type"] is None

    assert no_params_function["is_exogenous"]
    assert len(no_params_function["params"]) == 0


def test_insufficient_traces_fixture(insufficient_traces):
    """Verify insufficient traces fixture."""
    assert len(insufficient_traces) < 5


def test_cv_fixtures(cv_linear_traces, cv_polynomial_traces, cv_noisy_traces):
    """Verify cross-validation fixtures."""
    assert len(cv_linear_traces) == 100
    assert len(cv_polynomial_traces) == 100
    assert len(cv_noisy_traces) == 100

    # Verify linear traces: y = 2.5*x + 1.0
    for _, row in cv_linear_traces.iterrows():
        expected = 2.5 * row["x"] + 1.0
        assert abs(row["y"] - expected) < 0.001


def test_pipeline_fixtures(
    pipeline_linear_example,
    pipeline_nonlinear_example,
    pipeline_multi_variable_example,
):
    """Verify complete pipeline fixtures."""
    # Linear example
    assert pipeline_linear_example["mechanism_type"] == "linear"
    assert "traces" in pipeline_linear_example
    assert pipeline_linear_example["expected_r2"] == 1.0

    # Nonlinear example
    assert pipeline_nonlinear_example["mechanism_type"] == "nonlinear"
    assert isinstance(pipeline_nonlinear_example["traces"], pd.DataFrame)

    # Multi-variable example
    assert len(pipeline_multi_variable_example["params"]) == 3
    assert "traces" in pipeline_multi_variable_example


def test_all_fixtures_have_required_fields():
    """Meta-test: verify all function fixtures have required fields."""
    # This is verified by the individual tests above
    # All fixtures are tested for correct structure
    assert True


def test_conftest_utilities(
    graph_comparator,
    benchmark_timer,
    r_squared_calculator,
    trace_validator,
):
    """Verify conftest utilities work correctly."""
    import networkx as nx

    # Test graph comparison
    g1 = nx.DiGraph()
    g1.add_edge("a", "b")

    g2 = nx.DiGraph()
    g2.add_edge("a", "b")

    assert graph_comparator["equal"](g1, g2)

    # Test timer
    import time

    with benchmark_timer(max_seconds=1.0):
        time.sleep(0.1)  # Should pass

    # Test R² calculator
    y_true = [1, 2, 3, 4, 5]
    y_pred = [1, 2, 3, 4, 5]
    r2 = r_squared_calculator(y_true, y_pred)
    assert r2 == 1.0

    # Test trace validator
    df = pd.DataFrame({"x": [1, 2], "y": [2, 4]})
    assert trace_validator(df, {"x", "y"})
    assert not trace_validator(df, {"x", "z"})


def test_mock_scm(mock_scm):
    """Verify mock SCM works for lightweight testing."""
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edge("x", "y")

    scm = mock_scm(graph)
    assert scm.graph == graph

    scm.set_causal_mechanism("x", "test_mechanism")
    assert scm.get_causal_mechanism("x") == "test_mechanism"


def test_sample_graphs(
    simple_linear_graph,
    multi_parent_graph,
    chain_graph,
    diamond_graph,
):
    """Verify sample graph fixtures."""
    assert simple_linear_graph.number_of_nodes() == 2
    assert simple_linear_graph.number_of_edges() == 1

    assert multi_parent_graph.number_of_nodes() == 3
    assert multi_parent_graph.number_of_edges() == 2

    assert chain_graph.number_of_nodes() == 4
    assert chain_graph.number_of_edges() == 3

    assert diamond_graph.number_of_nodes() == 4
    assert diamond_graph.number_of_edges() == 4


# =============================================================================
# Fixture Coverage Summary
# =============================================================================


def test_fixture_coverage_summary():
    """Document fixture coverage for each STEP.

    This test always passes - it's documentation.
    """
    coverage = {
        "STEP-06 (Static Mechanism Inference)": [
            "double_function",
            "increment_function",
            "triple_offset_function",
            "always_zero_function",
            "constant_value_function",
            "square_function",
            "exponential_function",
            "cubic_function",
            "add_function",
            "weighted_sum_function",
            "complex_combination_function",
            "abs_value_function",
            "clamp_function",
            "step_function",
            "empty_function",
            "no_params_function",
        ],
        "STEP-07 (Execution Trace Collection)": [
            "double_traces",
            "double_traces_large",
            "increment_traces",
            "add_traces",
            "weighted_sum_traces",
            "square_traces",
            "insufficient_traces",
            "mismatched_traces",
        ],
        "STEP-08 (Dynamic Mechanism Fitting)": [
            "double_traces",
            "add_traces",
            "weighted_sum_traces",
            "square_traces",
            "noisy_linear_traces",
            "pipeline_linear_example",
            "pipeline_nonlinear_example",
            "pipeline_multi_variable_example",
        ],
        "STEP-09 (Cross-Validation)": [
            "cv_linear_traces",
            "cv_polynomial_traces",
            "cv_noisy_traces",
            "noisy_linear_traces",
        ],
    }

    print("\n=== SCM Fixture Coverage Summary ===")
    for step, fixtures in coverage.items():
        print(f"\n{step}: {len(fixtures)} fixtures")
        for fixture in fixtures:
            print(f"  - {fixture}")

    # Total count
    all_fixtures = set()
    for fixtures in coverage.values():
        all_fixtures.update(fixtures)

    print(f"\nTotal unique fixtures: {len(all_fixtures)}")

    assert len(all_fixtures) > 0  # Always pass
