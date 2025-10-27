"""Shared pytest fixtures and utilities for causal inference tests.

Provides:
- DoWhy environment checking
- Temporary file utilities
- Graph comparison utilities
- Performance benchmarking utilities
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import networkx as nx
import pytest

# Note: pytest_plugins declaration moved to root conftest.py
# to comply with pytest deprecation warning about non-top-level plugin definitions


# =============================================================================
# DoWhy Environment Checking
# =============================================================================


@pytest.fixture(scope="session")
def dowhy_available() -> bool:
    """Check if DoWhy is available in Python 3.11 venv.

    Returns:
        True if DoWhy can be imported, False otherwise.

    Note:
        DoWhy requires Python 3.11 and runs in subprocess.
        Main lift-sys code uses Python 3.12+.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import dowhy"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture
def require_dowhy(dowhy_available: bool):
    """Skip test if DoWhy is not available.

    Usage:
        def test_something(require_dowhy):
            # Test will be skipped if DoWhy unavailable
            ...
    """
    if not dowhy_available:
        pytest.skip("DoWhy not available (requires Python 3.11 venv)")


@pytest.fixture(scope="session")
def dowhy_python_path() -> str:
    """Get path to Python 3.11 interpreter with DoWhy installed.

    Returns:
        Path to Python executable or system python as fallback.
    """
    # Check for venv in project
    venv_paths = [
        Path.cwd() / ".venv311" / "bin" / "python",
        Path.cwd() / "venv311" / "bin" / "python",
        Path.home() / ".venv311" / "bin" / "python",
    ]

    for path in venv_paths:
        if path.exists():
            return str(path)

    # Fallback to system python
    return sys.executable


# =============================================================================
# Temporary File Utilities
# =============================================================================


@pytest.fixture
def temp_dir() -> Path:
    """Create temporary directory for test artifacts.

    Automatically cleaned up after test.
    """
    temp_path = Path(tempfile.mkdtemp(prefix="lift_causal_test_"))
    yield temp_path

    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def temp_file(temp_dir: Path):
    """Create temporary file in temp directory.

    Returns a function that creates files.

    Usage:
        def test_something(temp_file):
            path = temp_file("test.py", "def foo(): pass")
            assert path.exists()
    """

    def _create_file(name: str, content: str = "") -> Path:
        file_path = temp_dir / name
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


# =============================================================================
# Graph Comparison Utilities
# =============================================================================


def graphs_equal(g1: nx.DiGraph, g2: nx.DiGraph) -> bool:
    """Check if two directed graphs are structurally equal.

    Args:
        g1: First graph
        g2: Second graph

    Returns:
        True if graphs have same nodes and edges, False otherwise.
    """
    if set(g1.nodes()) != set(g2.nodes()):
        return False

    if set(g1.edges()) != set(g2.edges()):
        return False

    return True


def assert_graphs_equal(g1: nx.DiGraph, g2: nx.DiGraph, msg: str = ""):
    """Assert two graphs are equal, with detailed error message.

    Args:
        g1: First graph
        g2: Second graph
        msg: Optional custom message

    Raises:
        AssertionError: If graphs are not equal
    """
    prefix = f"{msg}: " if msg else ""

    # Check nodes
    nodes1 = set(g1.nodes())
    nodes2 = set(g2.nodes())

    if nodes1 != nodes2:
        missing_in_g2 = nodes1 - nodes2
        missing_in_g1 = nodes2 - nodes1
        error_parts = [f"{prefix}Graphs have different nodes."]

        if missing_in_g2:
            error_parts.append(f"  In g1 but not g2: {missing_in_g2}")
        if missing_in_g1:
            error_parts.append(f"  In g2 but not g1: {missing_in_g1}")

        raise AssertionError("\n".join(error_parts))

    # Check edges
    edges1 = set(g1.edges())
    edges2 = set(g2.edges())

    if edges1 != edges2:
        missing_in_g2 = edges1 - edges2
        missing_in_g1 = edges2 - edges1
        error_parts = [f"{prefix}Graphs have different edges."]

        if missing_in_g2:
            error_parts.append(f"  In g1 but not g2: {missing_in_g2}")
        if missing_in_g1:
            error_parts.append(f"  In g2 but not g1: {missing_in_g1}")

        raise AssertionError("\n".join(error_parts))


@pytest.fixture
def graph_comparator():
    """Provide graph comparison utilities.

    Returns:
        Dict with comparison functions.

    Usage:
        def test_something(graph_comparator):
            assert graph_comparator['equal'](g1, g2)
            graph_comparator['assert_equal'](g1, g2, "Custom message")
    """
    return {
        "equal": graphs_equal,
        "assert_equal": assert_graphs_equal,
    }


# =============================================================================
# Performance Benchmarking
# =============================================================================


@pytest.fixture
def benchmark_timer():
    """Simple timer for performance assertions.

    Usage:
        def test_performance(benchmark_timer):
            with benchmark_timer(max_seconds=10):
                # Code that must complete in <10s
                slow_function()
    """
    import time
    from contextlib import contextmanager

    @contextmanager
    def _timer(max_seconds: float | None = None):
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start

        if max_seconds is not None and elapsed > max_seconds:
            raise AssertionError(f"Code took {elapsed:.2f}s, exceeds limit of {max_seconds}s")

    return _timer


# =============================================================================
# Mock SCM and DoWhy Objects (for tests without DoWhy)
# =============================================================================


class MockStructuralCausalModel:
    """Mock SCM for tests that don't need real DoWhy.

    Minimal interface matching dowhy.gcm.StructuralCausalModel.
    """

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.mechanisms: dict[str, Any] = {}

    def set_causal_mechanism(self, node: str, mechanism: Any):
        """Set mechanism for a node."""
        self.mechanisms[node] = mechanism

    def get_causal_mechanism(self, node: str) -> Any:
        """Get mechanism for a node."""
        return self.mechanisms.get(node)


@pytest.fixture
def mock_scm():
    """Provide MockStructuralCausalModel for lightweight testing.

    Usage:
        def test_without_dowhy(mock_scm):
            scm = mock_scm(graph)
            scm.set_causal_mechanism("x", LinearMechanism())
    """
    return MockStructuralCausalModel


# =============================================================================
# Sample Graphs (for quick testing)
# =============================================================================


@pytest.fixture
def simple_linear_graph() -> nx.DiGraph:
    """Simple linear causal graph: x → y.

    Used for basic mechanism fitting tests.
    """
    graph = nx.DiGraph()
    graph.add_edge("x", "y")
    return graph


@pytest.fixture
def multi_parent_graph() -> nx.DiGraph:
    """Multi-parent graph: a → c, b → c.

    Used for multi-variable mechanism tests.
    """
    graph = nx.DiGraph()
    graph.add_edge("a", "c")
    graph.add_edge("b", "c")
    return graph


@pytest.fixture
def chain_graph() -> nx.DiGraph:
    """Chain graph: a → b → c → d.

    Used for propagation and validation tests.
    """
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "d")
    return graph


@pytest.fixture
def diamond_graph() -> nx.DiGraph:
    """Diamond graph: a → b, a → c, b → d, c → d.

    Used for complex dependency tests.
    """
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("b", "d")
    graph.add_edge("c", "d")
    return graph


# =============================================================================
# R² Validation Utilities
# =============================================================================


def calculate_r_squared(y_true: list[float], y_pred: list[float]) -> float:
    """Calculate R² (coefficient of determination).

    Args:
        y_true: True values
        y_pred: Predicted values

    Returns:
        R² value (1.0 = perfect fit, 0.0 = no better than mean)
    """
    import numpy as np

    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    ss_res = np.sum((y_true_arr - y_pred_arr) ** 2)
    ss_tot = np.sum((y_true_arr - np.mean(y_true_arr)) ** 2)

    if ss_tot == 0:
        return 1.0 if ss_res == 0 else 0.0

    return 1 - (ss_res / ss_tot)


@pytest.fixture
def r_squared_calculator():
    """Provide R² calculation utility.

    Usage:
        def test_fitting(r_squared_calculator):
            r2 = r_squared_calculator(y_true, y_pred)
            assert r2 >= 0.7
    """
    return calculate_r_squared


# =============================================================================
# Data Validation Utilities
# =============================================================================


def validate_trace_columns(traces, expected_columns: set[str]) -> bool:
    """Check if DataFrame has expected columns.

    Args:
        traces: pandas DataFrame
        expected_columns: Set of expected column names

    Returns:
        True if all columns present, False otherwise
    """
    return set(traces.columns) == expected_columns


@pytest.fixture
def trace_validator():
    """Provide trace validation utilities.

    Usage:
        def test_traces(trace_validator):
            assert trace_validator(df, {'x', 'y'})
    """
    return validate_trace_columns
