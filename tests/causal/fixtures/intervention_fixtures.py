"""Test fixtures for intervention queries.

Provides standard test cases for validating intervention execution,
including hard interventions, soft interventions, and edge cases.
"""

import networkx as nx
import numpy as np
import pandas as pd


def simple_linear_scm_data():
    """Simple linear SCM: x → y → z.

    Ground truth:
        x ~ N(0, 1)
        y = 2*x + N(0, 0.1)
        z = y + 1 + N(0, 0.1)

    Expected intervention effects:
        do(x=5): x=5, y≈10, z≈11
        do(x := x+2): Δy≈+4, Δz≈+4
        do(y=10): y=10, z≈11, x unchanged
    """
    graph = nx.DiGraph([("x", "y"), ("y", "z")])

    np.random.seed(42)
    n = 1000
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.1, n)
    z = y + 1 + np.random.normal(0, 0.1, n)

    traces = pd.DataFrame({"x": x, "y": y, "z": z})

    return {
        "graph": graph,
        "traces": traces,
        "ground_truth": {
            "x_mean": 0.0,
            "y_mean": 0.0,
            "z_mean": 1.0,
            "x_coef": 2.0,  # y = 2*x
            "y_coef": 1.0,  # z = y + 1
            "z_intercept": 1.0,
        },
    }


def diamond_scm_data():
    """Diamond SCM: x → y, x → z, y → w, z → w.

    Ground truth:
        x ~ N(0, 1)
        y = 2*x + N(0, 0.1)
        z = 3*x + N(0, 0.1)
        w = y + z + N(0, 0.1)

    Expected intervention effects:
        do(x=3): x=3, y≈6, z≈9, w≈15
        do(y=10, z=5): x unchanged, y=10, z=5, w≈15
        do(x=0): x=0, y≈0, z≈0, w≈0
    """
    graph = nx.DiGraph([("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")])

    np.random.seed(42)
    n = 1000
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.1, n)
    z = 3 * x + np.random.normal(0, 0.1, n)
    w = y + z + np.random.normal(0, 0.1, n)

    traces = pd.DataFrame({"x": x, "y": y, "z": z, "w": w})

    return {
        "graph": graph,
        "traces": traces,
        "ground_truth": {
            "x_mean": 0.0,
            "y_mean": 0.0,
            "z_mean": 0.0,
            "w_mean": 0.0,
        },
    }


def nonlinear_scm_data():
    """Nonlinear SCM: x → y (quadratic).

    Ground truth:
        x ~ U(-5, 5)
        y = x^2 + N(0, 0.5)

    Expected intervention effects:
        do(x=3): x=3, y≈9
        do(x=0): x=0, y≈0
        do(x=-3): x=-3, y≈9
    """
    graph = nx.DiGraph([("x", "y")])

    np.random.seed(42)
    n = 1000
    x = np.random.uniform(-5, 5, n)
    y = x**2 + np.random.normal(0, 0.5, n)

    traces = pd.DataFrame({"x": x, "y": y})

    return {
        "graph": graph,
        "traces": traces,
        "ground_truth": {
            "x_mean": 0.0,
            "y_mean": 8.33,  # E[X^2] for X ~ U(-5, 5)
            "relation": "quadratic",
        },
    }


def intervention_test_cases():
    """Standard intervention test cases with expected results.

    Returns:
        List of test case dicts with:
            - name: Test case name
            - scm_data: SCM graph + traces
            - intervention: Intervention specification
            - expected: Expected results (means, effect sizes, etc.)
    """
    simple = simple_linear_scm_data()
    diamond = diamond_scm_data()

    return [
        # Test 1: Hard intervention on root node
        {
            "name": "hard_intervention_root",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5.0}],
                "query_nodes": ["x", "y", "z"],
                "num_samples": 1000,
            },
            "expected": {
                "x_mean": 5.0,
                "x_std": 0.0,  # Constant
                "y_mean": 10.0,
                "z_mean": 11.0,
                "tolerance": 0.2,  # Allow ±0.2 due to noise
            },
        },
        # Test 2: Soft intervention (shift)
        {
            "name": "soft_intervention_shift",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [
                    {"type": "soft", "node": "x", "transform": "shift", "param": 2.0}
                ],
                "query_nodes": ["x", "y", "z"],
                "num_samples": 1000,
            },
            "expected": {
                "x_mean_shift": 2.0,  # x → x + 2
                "y_mean_shift": 4.0,  # y shifts by 2*2
                "z_mean_shift": 4.0,  # z shifts by 4
                "tolerance": 0.3,
            },
        },
        # Test 3: Multiple interventions
        {
            "name": "multiple_interventions",
            "scm_data": diamond,
            "intervention": {
                "type": "interventional",
                "interventions": [
                    {"type": "hard", "node": "x", "value": 3.0},
                    {"type": "hard", "node": "y", "value": 10.0},
                ],
                "query_nodes": ["x", "y", "z", "w"],
                "num_samples": 1000,
            },
            "expected": {
                "x_mean": 3.0,
                "y_mean": 10.0,  # Overridden (breaks x→y edge)
                "z_mean": 9.0,  # 3*x = 9
                "w_mean": 19.0,  # y + z = 10 + 9
                "tolerance": 0.3,
            },
        },
        # Test 4: Intervention on intermediate node
        {
            "name": "intervention_intermediate",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "y", "value": 10.0}],
                "query_nodes": ["x", "y", "z"],
                "num_samples": 1000,
            },
            "expected": {
                "x_mean": 0.0,  # x unchanged (upstream of intervention)
                "x_std": 1.0,  # Still random
                "y_mean": 10.0,
                "z_mean": 11.0,
                "tolerance": 0.2,
            },
        },
        # Test 5: Soft intervention (scale)
        {
            "name": "soft_intervention_scale",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [
                    {"type": "soft", "node": "y", "transform": "scale", "param": 2.0}
                ],
                "query_nodes": ["y", "z"],
                "num_samples": 1000,
            },
            "expected": {
                "y_mean": 0.0,  # Baseline y ≈ 0, scaled still ≈ 0
                "y_std_ratio": 2.0,  # Std doubles
                "z_mean": 1.0,  # z intercept still applies
                "tolerance": 0.3,
            },
        },
        # Test 6: Observational query (no intervention)
        {
            "name": "observational_baseline",
            "scm_data": simple,
            "intervention": {
                "type": "observational",
                "query_nodes": ["x", "y", "z"],
                "num_samples": 1000,
            },
            "expected": {
                "x_mean": 0.0,
                "y_mean": 0.0,
                "z_mean": 1.0,
                "tolerance": 0.2,
            },
        },
    ]


def edge_case_intervention_tests():
    """Edge case intervention tests.

    Returns:
        List of edge case test dicts
    """
    simple = simple_linear_scm_data()

    return [
        # Edge 1: Intervention on non-existent node
        {
            "name": "invalid_node",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "nonexistent", "value": 5}],
                "num_samples": 100,
            },
            "expect_error": True,
            "error_type": "ValueError",
        },
        # Edge 2: Zero samples
        {
            "name": "zero_samples",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5}],
                "num_samples": 0,
            },
            "expect_error": True,
        },
        # Edge 3: Negative samples
        {
            "name": "negative_samples",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5}],
                "num_samples": -100,
            },
            "expect_error": True,
        },
        # Edge 4: Empty interventions list
        {
            "name": "empty_interventions",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [],
                "num_samples": 100,
            },
            "expected": {
                # Should behave like observational query
                "x_mean": 0.0,
                "y_mean": 0.0,
                "z_mean": 1.0,
                "tolerance": 0.3,
            },
        },
        # Edge 5: Query non-existent nodes
        {
            "name": "invalid_query_nodes",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5}],
                "query_nodes": ["x", "nonexistent"],
                "num_samples": 100,
            },
            "expect_error": True,
        },
    ]


def performance_test_cases():
    """Performance test cases for intervention queries.

    Returns:
        List of performance test dicts
    """
    simple = simple_linear_scm_data()
    diamond = diamond_scm_data()

    return [
        # Perf 1: Small query (1000 samples, simple graph)
        {
            "name": "small_query",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5}],
                "num_samples": 1000,
            },
            "max_time_ms": 100,  # Should complete in <100ms
        },
        # Perf 2: Large query (10000 samples, simple graph)
        {
            "name": "large_query",
            "scm_data": simple,
            "intervention": {
                "type": "interventional",
                "interventions": [{"type": "hard", "node": "x", "value": 5}],
                "num_samples": 10000,
            },
            "max_time_ms": 500,  # Should complete in <500ms
        },
        # Perf 3: Multiple interventions (complex)
        {
            "name": "multiple_interventions_perf",
            "scm_data": diamond,
            "intervention": {
                "type": "interventional",
                "interventions": [
                    {"type": "hard", "node": "x", "value": 3},
                    {"type": "soft", "node": "y", "transform": "shift", "param": 2.0},
                ],
                "num_samples": 1000,
            },
            "max_time_ms": 100,
        },
    ]
