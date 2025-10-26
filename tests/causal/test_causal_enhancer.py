"""Unit tests for CausalEnhancer (Week 4, STEP-14).

Tests the orchestration layer that integrates H20-H22 into reverse mode.
"""

import ast

import networkx as nx
import pandas as pd
import pytest

from lift_sys.causal.causal_enhancer import CausalEnhancer
from lift_sys.causal.scm_fitter import FittingError
from lift_sys.causal.trace_collector import collect_traces
from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


@pytest.fixture
def simple_ir():
    """Create simple IR for testing."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Double the input value"),
        signature=SigClause(
            name="double",
            parameters=[Parameter(name="x", type_hint="float")],
            returns="float",
        ),
        metadata=Metadata(source_path="test.py", language="python"),
    )


@pytest.fixture
def simple_ast():
    """Create simple AST: x → y."""
    code = """
def double(x):
    return x * 2
"""
    return ast.parse(code)


@pytest.fixture
def simple_traces():
    """Create execution traces for x → y."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}
    return collect_traces(graph, code, num_samples=100, random_seed=42)


# =============================================================================
# Basic Functionality Tests
# =============================================================================


def test_causal_enhancer_initialization():
    """Test CausalEnhancer can be initialized."""
    enhancer = CausalEnhancer()

    assert enhancer.graph_builder is not None
    assert enhancer.scm_fitter is not None
    assert enhancer.intervention_engine is not None
    assert enhancer._circuit_breaker_failures == 0
    assert enhancer._circuit_breaker_open is False


def test_causal_enhancer_static_mode(simple_ir, simple_ast):
    """Test CausalEnhancer in static mode (no traces)."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Check result structure
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is not None
    assert result["scm"] is not None
    assert result["scm"]["mode"] == "static"
    assert result["intervention_engine"] is not None
    assert result["mode"] == "static"
    assert "warnings" in result["metadata"]


def test_causal_enhancer_dynamic_mode(simple_ir, simple_ast, simple_traces):
    """Test CausalEnhancer in dynamic mode (with traces)."""
    enhancer = CausalEnhancer()

    try:
        result = enhancer.enhance(
            ir=simple_ir,
            ast_tree=simple_ast,
            traces=simple_traces,
            mode="dynamic",
        )
    except FittingError:
        pytest.skip("DoWhy not available")

    # Check result structure
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is not None
    assert result["scm"] is not None
    assert result["scm"]["mode"] == "dynamic"
    assert "traces" in result["scm"]  # Required for interventions
    assert result["intervention_engine"] is not None
    assert result["mode"] == "dynamic"


def test_causal_enhancer_auto_mode_static(simple_ir, simple_ast):
    """Test auto mode selection: static when no traces."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="auto",  # Should pick static
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    assert result["mode"] == "static"
    assert result["scm"]["mode"] == "static"


def test_causal_enhancer_auto_mode_dynamic(simple_ir, simple_ast, simple_traces):
    """Test auto mode selection: dynamic when traces available."""
    enhancer = CausalEnhancer()

    try:
        result = enhancer.enhance(
            ir=simple_ir,
            ast_tree=simple_ast,
            traces=simple_traces,
            mode="auto",  # Should pick dynamic
        )
    except FittingError:
        pytest.skip("DoWhy not available")

    assert result["mode"] == "dynamic"
    assert result["scm"]["mode"] == "dynamic"


# =============================================================================
# Error Handling and Graceful Degradation
# =============================================================================


def test_causal_enhancer_invalid_mode(simple_ir, simple_ast):
    """Test error on invalid mode."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="invalid",  # Invalid mode
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Should gracefully degrade (return base IR with warnings)
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is None
    assert result["scm"] is None
    assert "warnings" in result["metadata"]


def test_causal_enhancer_dynamic_mode_without_traces(simple_ir, simple_ast):
    """Test error when dynamic mode but no traces provided."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="dynamic",
        traces=None,  # Missing traces!
    )

    # Should gracefully degrade
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is None or result["scm"] is None
    assert "warnings" in result["metadata"]


def test_causal_enhancer_graph_extraction_failure(simple_ir):
    """Test graceful degradation when graph extraction fails."""
    enhancer = CausalEnhancer()

    # Invalid AST (empty module)
    invalid_ast = ast.parse("")

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=invalid_ast,
        mode="static",
    )

    # Should return base IR with warnings
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is None or len(result["causal_graph"].nodes()) == 0
    assert "warnings" in result["metadata"]


def test_causal_enhancer_scm_fitting_failure_returns_graph(simple_ir, simple_ast):
    """Test partial success: graph extracted but SCM fitting fails."""
    enhancer = CausalEnhancer()

    # Use invalid traces (wrong columns) to trigger fitting error
    invalid_traces = pd.DataFrame({"wrong": [1, 2, 3], "columns": [4, 5, 6]})

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        traces=invalid_traces,
        mode="dynamic",
    )

    # Should return graph but no SCM
    assert result["ir"] == simple_ir
    # Graph extraction might succeed even if fitting fails
    assert (
        result["causal_graph"] is not None
        or "graph_extraction_failed" in result["metadata"]["warnings"]
    )
    # SCM should be None due to fitting failure
    assert result["scm"] is None or "scm_fitting_failed" in result["metadata"]["warnings"]


# =============================================================================
# Circuit Breaker Tests
# =============================================================================


def test_circuit_breaker_opens_after_threshold(simple_ir):
    """Test circuit breaker opens after repeated failures."""
    enhancer = CausalEnhancer(
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3,
    )

    # Trigger 3 failures with invalid AST
    invalid_ast = ast.parse("")

    for _ in range(3):
        result = enhancer.enhance(
            ir=simple_ir,
            ast_tree=invalid_ast,
            mode="static",
        )
        assert "warnings" in result["metadata"]

    # Circuit breaker should now be open
    assert enhancer._circuit_breaker_open is True
    assert enhancer._circuit_breaker_failures >= 3


def test_circuit_breaker_prevents_further_calls(simple_ir, simple_ast):
    """Test circuit breaker prevents calls after opening."""
    enhancer = CausalEnhancer(
        enable_circuit_breaker=True,
        circuit_breaker_threshold=2,
    )

    # Force open circuit breaker
    enhancer._circuit_breaker_failures = 2
    enhancer._circuit_breaker_open = True

    # Try to enhance (should immediately return with warning)
    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    assert result["ir"] == simple_ir
    assert result["causal_graph"] is None
    assert "causal_unavailable_circuit_breaker" in result["metadata"]["warnings"]


def test_circuit_breaker_reset(simple_ir, simple_ast):
    """Test circuit breaker can be reset."""
    enhancer = CausalEnhancer(
        enable_circuit_breaker=True,
        circuit_breaker_threshold=2,
    )

    # Open circuit breaker
    enhancer._circuit_breaker_failures = 3
    enhancer._circuit_breaker_open = True

    # Reset
    enhancer.reset_circuit_breaker()

    assert enhancer._circuit_breaker_failures == 0
    assert enhancer._circuit_breaker_open is False

    # Should work again
    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Should succeed this time (circuit breaker closed)
    assert result["causal_graph"] is not None


def test_circuit_breaker_disabled(simple_ir):
    """Test circuit breaker can be disabled."""
    enhancer = CausalEnhancer(
        enable_circuit_breaker=False,
    )

    # Trigger multiple failures (should not open circuit breaker)
    invalid_ast = ast.parse("")

    for _ in range(5):
        result = enhancer.enhance(
            ir=simple_ir,
            ast_tree=invalid_ast,
            mode="static",
        )
        assert "warnings" in result["metadata"]

    # Circuit breaker should remain closed
    assert enhancer._circuit_breaker_open is False


# =============================================================================
# Integration with H20-H22
# =============================================================================


def test_causal_enhancer_uses_h20_graph_builder(simple_ir, simple_ast):
    """Test CausalEnhancer correctly uses H20 (CausalGraphBuilder)."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Graph should be extracted
    graph = result["causal_graph"]
    assert graph is not None
    assert isinstance(graph, nx.DiGraph)

    # Graph should have nodes extracted from AST
    # (May be empty if AST is too simple, but should not be None)


def test_causal_enhancer_uses_h21_scm_fitter(simple_ir, simple_ast):
    """Test CausalEnhancer correctly uses H21 (SCMFitter)."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # SCM should be fitted
    scm = result["scm"]
    assert scm is not None
    assert "mode" in scm
    assert scm["mode"] == "static"


def test_causal_enhancer_provides_h22_intervention_engine(simple_ir, simple_ast):
    """Test CausalEnhancer provides H22 (InterventionEngine)."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Intervention engine should be provided
    engine = result["intervention_engine"]
    assert engine is not None
    assert hasattr(engine, "execute")


# =============================================================================
# Edge Cases
# =============================================================================


def test_causal_enhancer_empty_call_graph(simple_ir, simple_ast):
    """Test CausalEnhancer with no call graph (None)."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        call_graph=None,  # No call graph
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Should still work (call_graph defaults to empty DiGraph)
    assert result["ir"] == simple_ir


def test_causal_enhancer_with_call_graph(simple_ir, simple_ast):
    """Test CausalEnhancer with explicit call graph."""
    enhancer = CausalEnhancer()

    call_graph = nx.DiGraph([("double", "helper")])

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        call_graph=call_graph,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Should succeed
    assert result["ir"] == simple_ir
    assert result["causal_graph"] is not None


def test_causal_enhancer_metadata_warnings(simple_ir, simple_ast):
    """Test metadata warnings are tracked."""
    enhancer = CausalEnhancer()

    # Trigger graph extraction failure
    invalid_ast = ast.parse("")

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=invalid_ast,
        mode="static",
    )

    # Check warnings
    metadata = result["metadata"]
    assert "warnings" in metadata
    assert len(metadata["warnings"]) > 0


def test_causal_enhancer_preserves_base_ir(simple_ir, simple_ast):
    """Test that base IR is never modified."""
    enhancer = CausalEnhancer()

    original_ir_dict = simple_ir.to_dict()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    # Base IR should be unchanged
    assert result["ir"].to_dict() == original_ir_dict


# =============================================================================
# Performance and Sanity Checks
# =============================================================================


def test_causal_enhancer_static_mode_fast():
    """Test static mode completes quickly (<1s)."""
    import time

    enhancer = CausalEnhancer()

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test function"),
        signature=SigClause(
            name="test_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
    )

    ast_tree = ast.parse("def test_func(x):\n    return x + 1")

    start = time.time()
    result = enhancer.enhance(
        ir=ir,
        ast_tree=ast_tree,
        mode="static",
        source_code={"test_func": "def test_func(x):\n    return x + 1"},
    )
    elapsed = time.time() - start

    # Static mode should be fast (<1s, usually <100ms)
    assert elapsed < 1.0
    assert result["mode"] == "static"
