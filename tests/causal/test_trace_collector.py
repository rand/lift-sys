"""Unit tests for execution trace collection (STEP-07)."""

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from lift_sys.causal.trace_collector import (
    ExecutionError,
    TraceCollectionError,
    TraceCollector,
    collect_traces,
)


def test_collect_simple_linear_traces():
    """Test collecting traces for simple linear function (y = 2*x)."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 2)
    assert list(traces.columns) == ["x", "y"]

    # Verify relationship: y should be ~2*x
    assert np.allclose(traces["y"], traces["x"] * 2)


def test_collect_multi_variable_traces():
    """Test collecting traces for multi-variable function (z = a + b)."""
    graph = nx.DiGraph([("a", "z"), ("b", "z")])
    code = {"z": "def add(a, b):\n    return a + b"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=50)

    assert traces.shape == (50, 3)
    assert set(traces.columns) == {"a", "b", "z"}

    # Verify relationship: z should be a + b
    assert np.allclose(traces["z"], traces["a"] + traces["b"])


def test_collect_chained_traces():
    """Test collecting traces for chained functions (x → y → z)."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def increment(y):\n    return y + 1",
    }

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 3)
    assert list(traces.columns) == ["x", "y", "z"]

    # Verify relationships
    assert np.allclose(traces["y"], traces["x"] * 2)
    assert np.allclose(traces["z"], traces["y"] + 1)
    assert np.allclose(traces["z"], traces["x"] * 2 + 1)


def test_collect_diamond_graph_traces():
    """Test collecting traces for diamond graph (x → y, x → z, y → w, z → w)."""
    graph = nx.DiGraph([("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def triple(x):\n    return x * 3",
        "w": "def add(y, z):\n    return y + z",
    }

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=50)

    assert traces.shape == (50, 4)
    assert set(traces.columns) == {"x", "y", "z", "w"}

    # Verify relationships
    assert np.allclose(traces["y"], traces["x"] * 2)
    assert np.allclose(traces["z"], traces["x"] * 3)
    assert np.allclose(traces["w"], traces["y"] + traces["z"])
    assert np.allclose(traces["w"], traces["x"] * 2 + traces["x"] * 3)
    assert np.allclose(traces["w"], traces["x"] * 5)


def test_collect_with_custom_input_ranges():
    """Test collecting traces with custom input ranges."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def square(x):\n    return x ** 2"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100, input_ranges={"x": (0.0, 1.0)})

    assert traces.shape == (100, 2)

    # Verify x is in range [0, 1]
    assert traces["x"].min() >= 0.0
    assert traces["x"].max() <= 1.0

    # Verify relationship
    assert np.allclose(traces["y"], traces["x"] ** 2)


def test_collect_traces_convenience_function():
    """Test convenience function collect_traces()."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces = collect_traces(graph, code, num_samples=50, random_seed=42)

    assert isinstance(traces, pd.DataFrame)
    assert traces.shape == (50, 2)
    assert np.allclose(traces["y"], traces["x"] * 2)


def test_collect_traces_with_no_function():
    """Test collecting traces where some nodes have no function (input nodes)."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        # No code for x (it's an input)
        "y": "def double(x):\n    return x * 2",
        "z": "def increment(y):\n    return y + 1",
    }

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 3)

    # x should be random values
    assert len(traces["x"].unique()) > 50  # Many unique values

    # Relationships should hold
    assert np.allclose(traces["y"], traces["x"] * 2)
    assert np.allclose(traces["z"], traces["y"] + 1)


def test_invalid_function_code():
    """Test handling of invalid function code."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "invalid python code {{{"}

    collector = TraceCollector()

    with pytest.raises(TraceCollectionError, match="Failed to parse"):
        collector.collect_traces(graph, code, num_samples=10)


def test_non_dag_graph():
    """Test that non-DAG graphs raise error."""
    graph = nx.DiGraph([("x", "y"), ("y", "x")])  # Cycle!
    code = {"y": "def f(x):\n    return x"}

    collector = TraceCollector()

    with pytest.raises(TraceCollectionError, match="must be a DAG"):
        collector.collect_traces(graph, code, num_samples=10)


def test_zero_samples():
    """Test that zero samples raises error."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def f(x):\n    return x"}

    collector = TraceCollector()

    with pytest.raises(TraceCollectionError, match="must be ≥1"):
        collector.collect_traces(graph, code, num_samples=0)


def test_function_with_exception():
    """Test handling of function that raises exceptions."""
    graph = nx.DiGraph([("x", "y")])
    code = {
        "y": """
def bad_function(x):
    if x > 5:
        raise ValueError("x too large")
    return x * 2
"""
    }

    collector = TraceCollector(random_seed=42)

    # Should handle exceptions gracefully and skip failed samples
    traces = collector.collect_traces(graph, code, num_samples=100, input_ranges={"x": (0.0, 10.0)})

    # Some samples should succeed (x <= 5), some fail (x > 5)
    # DataFrame should only contain successful samples
    assert len(traces) > 0
    assert len(traces) < 100  # Some failed

    # All remaining x values should be valid
    assert traces["x"].max() <= 5  # Only successful ones remain


def test_too_many_failures():
    """Test that too many execution failures raises error."""
    graph = nx.DiGraph([("x", "y")])
    code = {
        "y": """
def always_fails(x):
    raise RuntimeError("Always fails")
"""
    }

    collector = TraceCollector(random_seed=42)

    with pytest.raises(ExecutionError, match="Too many failed samples"):
        collector.collect_traces(graph, code, num_samples=100)


def test_reproducibility_with_seed():
    """Test that random seed ensures reproducibility."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces1 = collect_traces(graph, code, num_samples=50, random_seed=42)
    traces2 = collect_traces(graph, code, num_samples=50, random_seed=42)

    pd.testing.assert_frame_equal(traces1, traces2)


def test_different_seeds_produce_different_traces():
    """Test that different seeds produce different traces."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces1 = collect_traces(graph, code, num_samples=50, random_seed=42)
    traces2 = collect_traces(graph, code, num_samples=50, random_seed=123)

    # Should not be equal
    assert not traces1["x"].equals(traces2["x"])


def test_generate_random_inputs():
    """Test random input generation utility."""
    collector = TraceCollector(random_seed=42)

    inputs = collector.generate_random_inputs(
        param_names=["x", "y"],
        input_ranges={"x": (0, 1), "y": (-5, 5)},
        num_samples=100,
    )

    assert set(inputs.keys()) == {"x", "y"}
    assert inputs["x"].shape == (100,)
    assert inputs["y"].shape == (100,)

    # Verify ranges
    assert inputs["x"].min() >= 0
    assert inputs["x"].max() <= 1
    assert inputs["y"].min() >= -5
    assert inputs["y"].max() <= 5


def test_async_function():
    """Test that async functions are rejected (not supported)."""
    graph = nx.DiGraph([("x", "y")])
    code = {
        "y": """
async def double(x):
    return x * 2
"""
    }

    collector = TraceCollector(random_seed=42)

    # Async functions should be detected and rejected during compilation
    # (they return coroutines, not usable numeric values)
    with pytest.raises(TraceCollectionError, match="Async functions not supported"):
        collector.collect_traces(graph, code, num_samples=10)


def test_performance_1000_samples(benchmark_timer):
    """Test that collecting 1000 samples completes in <10s."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def increment(y):\n    return y + 1",
    }

    collector = TraceCollector(random_seed=42)

    with benchmark_timer(max_seconds=10.0):
        traces = collector.collect_traces(graph, code, num_samples=1000)

    assert traces.shape == (1000, 3)
    assert np.allclose(traces["y"], traces["x"] * 2)
    assert np.allclose(traces["z"], traces["y"] + 1)


def test_nonlinear_function():
    """Test collecting traces for nonlinear function."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def square(x):\n    return x ** 2"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 2)
    assert np.allclose(traces["y"], traces["x"] ** 2)


def test_complex_multi_variable():
    """Test collecting traces for complex multi-variable function."""
    graph = nx.DiGraph([("x", "w"), ("y", "w"), ("z", "w")])
    code = {"w": "def weighted_sum(x, y, z):\n    return 2*x + 3*y + 4*z + 10"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 4)
    assert set(traces.columns) == {"x", "y", "z", "w"}

    # Verify relationship
    expected = 2 * traces["x"] + 3 * traces["y"] + 4 * traces["z"] + 10
    assert np.allclose(traces["w"], expected)


def test_empty_graph():
    """Test handling of empty graph."""
    graph = nx.DiGraph()
    code = {}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=10)

    assert traces.shape == (10, 0)  # No columns


def test_single_node_no_function():
    """Test single node with no function (pure input)."""
    graph = nx.DiGraph()
    graph.add_node("x")
    code = {}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=50)

    assert traces.shape == (50, 1)
    assert list(traces.columns) == ["x"]

    # Should be random values
    assert len(traces["x"].unique()) > 25


def test_integration_with_scm_fitter():
    """Test integration with SCMFitter (STEP-08 preparation)."""
    from lift_sys.causal.scm_fitter import SCMFitter

    # Create simple graph
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    # Collect traces
    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    # Try to fit with SCMFitter (dynamic mode not yet implemented)
    fitter = SCMFitter()

    # This should raise NotImplementedError for now (STEP-08)
    with pytest.raises(NotImplementedError, match="Dynamic fitting.*not yet implemented"):
        fitter.fit(graph, traces=traces)


def test_collect_traces_returns_clean_dataframe():
    """Test that returned DataFrame has no NaN values."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    # Should have no NaN values
    assert not traces.isnull().any().any()


def test_large_graph_performance():
    """Test performance with larger graph (10 nodes)."""
    # Create chain: x0 → x1 → x2 → ... → x9
    nodes = [f"x{i}" for i in range(10)]
    edges = [(nodes[i], nodes[i + 1]) for i in range(9)]
    graph = nx.DiGraph(edges)

    # Create functions: xi+1 = xi + i
    code = {}
    for i in range(9):
        code[nodes[i + 1]] = f"""
def add_{i}({nodes[i]}):
    return {nodes[i]} + {i}
"""

    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=100)

    assert traces.shape == (100, 10)

    # Verify chain relationships
    for i in range(9):
        expected = traces[nodes[i]] + i
        assert np.allclose(traces[nodes[i + 1]], expected)
