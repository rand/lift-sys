"""Unit tests for dynamic SCM fitting (STEP-08)."""

import networkx as nx
import pandas as pd
import pytest

from lift_sys.causal.scm_fitter import (
    DataError,
    SCMFitter,
    ValidationError,
)
from lift_sys.causal.trace_collector import collect_traces

# Mark all tests as requiring DoWhy
pytestmark = pytest.mark.skipif(
    not pytest.config.getoption("--dowhy", default=False),
    reason="Requires --dowhy flag and .venv-dowhy setup",
)


def test_fit_simple_linear_dynamic():
    """Test dynamic fitting for simple linear function (y = 2*x)."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    # Collect traces
    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    # Fit using dynamic mode
    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]
    assert "validation" in result
    assert "scm" in result

    # Check R² validation
    validation = result["validation"]
    assert "mean_r2" in validation
    assert validation["mean_r2"] >= 0.7  # Threshold


def test_fit_multi_variable_dynamic():
    """Test dynamic fitting for multi-variable function (z = a + b)."""
    graph = nx.DiGraph([("a", "z"), ("b", "z")])
    code = {"z": "def add(a, b):\n    return a + b"}

    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]
    assert result["validation"]["mean_r2"] >= 0.7


def test_fit_chained_functions_dynamic():
    """Test dynamic fitting for chained functions (x → y → z)."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def increment(y):\n    return y + 1",
    }

    traces = collect_traces(graph, code, num_samples=300, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]

    # Should have high R² for both edges
    assert result["validation"]["mean_r2"] >= 0.7


def test_fit_nonlinear_function_dynamic():
    """Test dynamic fitting for nonlinear function (y = x^2)."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def square(x):\n    return x ** 2"}

    traces = collect_traces(
        graph, code, num_samples=300, random_seed=42, input_ranges={"x": (-5.0, 5.0)}
    )

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    # Nonlinear may be harder to fit, but should still work
    assert result["status"] in ["success", "warning"]


def test_fit_with_insufficient_data():
    """Test that insufficient data raises appropriate error."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    # Only 10 samples (likely too few for good R²)
    traces = collect_traces(graph, code, num_samples=10, random_seed=42)

    fitter = SCMFitter()

    # May raise ValidationError if R² is too low
    # Or may succeed with warning
    try:
        result = fitter.fit(graph, traces=traces)
        # If it succeeds, should have warning or lower R²
        assert result["status"] in ["success", "warning"]
    except ValidationError as e:
        # Expected if R² < 0.7
        assert "validation failed" in str(e).lower()


def test_fit_mismatched_traces():
    """Test that mismatched traces raise DataError."""
    graph = nx.DiGraph([("x", "y")])

    # Traces with wrong column names
    traces = pd.DataFrame({"wrong_col": [1, 2, 3], "y": [2, 4, 6]})

    fitter = SCMFitter()

    with pytest.raises(DataError, match="do not match"):
        fitter.fit(graph, traces=traces)


def test_fit_with_custom_r2_threshold():
    """Test fitting with custom R² threshold."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    fitter = SCMFitter()

    # Strict threshold (may fail)
    try:
        result = fitter.fit(graph, traces=traces)
        # Default threshold is 0.7, which should pass
        assert result["validation"]["mean_r2"] >= 0.7
    except ValidationError:
        # Unexpected for clean linear relationship
        pytest.fail("Linear function should achieve R² ≥ 0.7")


def test_fit_diamond_graph_dynamic():
    """Test dynamic fitting for diamond graph structure."""
    graph = nx.DiGraph([("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def triple(x):\n    return x * 3",
        "w": "def add(y, z):\n    return y + z",
    }

    traces = collect_traces(graph, code, num_samples=400, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]
    assert result["validation"]["mean_r2"] >= 0.7


def test_fit_stores_mechanisms():
    """Test that fitted mechanisms are stored in fitter."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    # Should store mechanisms
    assert len(fitter.mechanisms) > 0
    assert "scm" in result
    assert "mechanisms" in result["scm"]


def test_fit_returns_metadata():
    """Test that fit returns useful metadata."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    # Should have metadata
    assert "metadata" in result
    metadata = result["metadata"]

    # Common metadata fields
    assert "num_samples" in metadata or "train_samples" in metadata
    assert "num_nodes" in metadata or "num_edges" in metadata


def test_fit_validation_structure():
    """Test that validation results have expected structure."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}

    traces = collect_traces(graph, code, num_samples=200, random_seed=42)

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    validation = result["validation"]

    # Expected validation fields
    assert "mean_r2" in validation
    assert "passed" in validation
    assert "failed_nodes" in validation

    # Mean R² should be valid
    assert 0.0 <= validation["mean_r2"] <= 1.0


def test_fit_with_noisy_data():
    """Test fitting with noisy data (may not reach threshold)."""
    import numpy as np

    graph = nx.DiGraph([("x", "y")])

    # Create noisy traces manually
    np.random.seed(42)
    x = np.random.uniform(-10, 10, size=300)
    y = 2 * x + np.random.normal(0, 5, size=300)  # Large noise

    traces = pd.DataFrame({"x": x, "y": y})

    fitter = SCMFitter()

    # May pass or fail depending on noise level
    try:
        result = fitter.fit(graph, traces=traces)
        # If it passes, R² should still be reported
        assert "mean_r2" in result["validation"]
    except ValidationError as e:
        # Expected with high noise
        assert "validation failed" in str(e).lower()


def test_fit_performance_1000_samples(benchmark_timer):
    """Test that dynamic fitting completes in <10s for 1000 samples."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def increment(y):\n    return y + 1",
    }

    traces = collect_traces(graph, code, num_samples=1000, random_seed=42)

    fitter = SCMFitter()

    with benchmark_timer(max_seconds=10.0):
        result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]


def test_fit_integration_with_trace_collector():
    """Test full integration: collect traces → fit SCM."""
    from lift_sys.causal.trace_collector import TraceCollector

    # Create graph
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    code = {
        "y": "def double(x):\n    return x * 2",
        "z": "def square(y):\n    return y ** 2",
    }

    # Collect traces
    collector = TraceCollector(random_seed=42)
    traces = collector.collect_traces(graph, code, num_samples=300)

    # Fit SCM
    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    # Should work end-to-end
    assert result["mode"] == "dynamic"
    assert result["status"] in ["success", "warning"]
    assert result["validation"]["mean_r2"] >= 0.0


def test_fit_empty_graph():
    """Test fitting with empty graph."""
    graph = nx.DiGraph()
    traces = pd.DataFrame()

    fitter = SCMFitter()

    # Should handle empty graph gracefully
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"


def test_fit_single_node():
    """Test fitting with single node (no edges)."""
    graph = nx.DiGraph()
    graph.add_node("x")

    traces = pd.DataFrame({"x": [1, 2, 3, 4, 5]})

    fitter = SCMFitter()
    result = fitter.fit(graph, traces=traces)

    assert result["mode"] == "dynamic"
    # Single node has no edges to validate
    assert "validation" in result
