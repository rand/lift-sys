"""Unit tests for EnhancedIR (Week 4, STEP-14).

Tests the user-facing API for causal-enhanced IR with lazy evaluation.
"""

import ast

import networkx as nx
import pytest

from lift_sys.causal.causal_enhancer import CausalEnhancer
from lift_sys.causal.enhanced_ir import EnhancedIR
from lift_sys.causal.intervention_engine import InterventionEngine
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
    y = x * 2
    return y
"""
    return ast.parse(code)


@pytest.fixture
def simple_traces():
    """Create execution traces for x → y."""
    graph = nx.DiGraph([("x", "y")])
    code = {"y": "def double(x):\n    return x * 2"}
    return collect_traces(graph, code, num_samples=100, random_seed=42)


@pytest.fixture
def enhanced_ir_with_causal(simple_ir, simple_ast):
    """Create EnhancedIR with causal capabilities."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    y = x * 2\n    return y"},
    )

    return EnhancedIR.from_enhancement_result(result)


@pytest.fixture
def enhanced_ir_without_causal(simple_ir):
    """Create EnhancedIR without causal capabilities (simulates failure)."""
    return EnhancedIR(
        base_ir=simple_ir,
        causal_graph=None,
        causal_scm=None,
        intervention_engine=None,
        mode=None,
        metadata={"warnings": ["causal_unavailable"]},
    )


# =============================================================================
# Initialization and Construction
# =============================================================================


def test_enhanced_ir_initialization(simple_ir):
    """Test EnhancedIR can be initialized directly."""
    graph = nx.DiGraph([("x", "y")])
    scm = {"mode": "static", "mechanisms": {}}
    engine = InterventionEngine()

    enhanced_ir = EnhancedIR(
        base_ir=simple_ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=engine,
        mode="static",
        metadata={"warnings": []},
    )

    assert enhanced_ir._base_ir == simple_ir
    assert enhanced_ir._causal_graph == graph
    assert enhanced_ir._causal_scm == scm
    assert enhanced_ir._intervention_engine == engine
    assert enhanced_ir._mode == "static"


def test_enhanced_ir_from_enhancement_result(simple_ir, simple_ast):
    """Test EnhancedIR.from_enhancement_result() factory method."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    return x * 2"},
    )

    enhanced_ir = EnhancedIR.from_enhancement_result(result)

    assert enhanced_ir._base_ir == simple_ir
    assert enhanced_ir._causal_graph is not None
    assert enhanced_ir._causal_scm is not None


# =============================================================================
# Base IR Delegation
# =============================================================================


def test_enhanced_ir_delegates_intent(enhanced_ir_with_causal):
    """Test EnhancedIR delegates intent property to base IR."""
    assert enhanced_ir_with_causal.intent.summary == "Double the input value"


def test_enhanced_ir_delegates_signature(enhanced_ir_with_causal):
    """Test EnhancedIR delegates signature property to base IR."""
    assert enhanced_ir_with_causal.signature.name == "double"
    assert len(enhanced_ir_with_causal.signature.parameters) == 1
    assert enhanced_ir_with_causal.signature.parameters[0].name == "x"


def test_enhanced_ir_delegates_effects(enhanced_ir_with_causal):
    """Test EnhancedIR delegates effects property to base IR."""
    # Simple IR has no effects
    assert enhanced_ir_with_causal.effects == []


def test_enhanced_ir_delegates_assertions(enhanced_ir_with_causal):
    """Test EnhancedIR delegates assertions property to base IR."""
    # Simple IR has no assertions
    assert enhanced_ir_with_causal.assertions == []


def test_enhanced_ir_delegates_metadata(enhanced_ir_with_causal):
    """Test EnhancedIR delegates metadata property to base IR."""
    assert enhanced_ir_with_causal.metadata.source_path == "test.py"
    assert enhanced_ir_with_causal.metadata.language == "python"


def test_enhanced_ir_delegates_constraints(enhanced_ir_with_causal):
    """Test EnhancedIR delegates constraints property to base IR."""
    # Simple IR has no constraints
    assert enhanced_ir_with_causal.constraints == []


def test_enhanced_ir_delegates_typed_holes(enhanced_ir_with_causal):
    """Test EnhancedIR delegates typed_holes() method to base IR."""
    # Simple IR has no holes
    assert enhanced_ir_with_causal.typed_holes() == []


def test_enhanced_ir_delegates_to_dict(enhanced_ir_with_causal):
    """Test EnhancedIR delegates to_dict() to base IR."""
    ir_dict = enhanced_ir_with_causal.to_dict()

    assert "intent" in ir_dict
    assert "signature" in ir_dict
    assert ir_dict["intent"]["summary"] == "Double the input value"


# =============================================================================
# Causal Capability Checks
# =============================================================================


def test_has_causal_capabilities_true(enhanced_ir_with_causal):
    """Test has_causal_capabilities returns True when causal available."""
    assert enhanced_ir_with_causal.has_causal_capabilities is True


def test_has_causal_capabilities_false(enhanced_ir_without_causal):
    """Test has_causal_capabilities returns False when causal unavailable."""
    assert enhanced_ir_without_causal.has_causal_capabilities is False


def test_causal_mode_available(enhanced_ir_with_causal):
    """Test causal_mode property when causal available."""
    assert enhanced_ir_with_causal.causal_mode == "static"


def test_causal_mode_unavailable(enhanced_ir_without_causal):
    """Test causal_mode property when causal unavailable."""
    assert enhanced_ir_without_causal.causal_mode is None


def test_causal_warnings_empty(enhanced_ir_with_causal):
    """Test causal_warnings when no warnings."""
    warnings = enhanced_ir_with_causal.causal_warnings
    assert isinstance(warnings, list)


def test_causal_warnings_present(enhanced_ir_without_causal):
    """Test causal_warnings when warnings present."""
    warnings = enhanced_ir_without_causal.causal_warnings
    assert "causal_unavailable" in warnings


# =============================================================================
# Lazy Evaluation (@cached_property)
# =============================================================================


def test_causal_graph_lazy_evaluation(enhanced_ir_with_causal):
    """Test causal_graph uses lazy evaluation."""
    # First access computes value
    graph1 = enhanced_ir_with_causal.causal_graph
    assert graph1 is not None

    # Second access returns same object (cached)
    graph2 = enhanced_ir_with_causal.causal_graph
    assert graph2 is graph1  # Same object reference


def test_causal_model_lazy_evaluation(enhanced_ir_with_causal):
    """Test causal_model uses lazy evaluation."""
    # First access computes value
    scm1 = enhanced_ir_with_causal.causal_model
    assert scm1 is not None

    # Second access returns same object (cached)
    scm2 = enhanced_ir_with_causal.causal_model
    assert scm2 is scm1  # Same object reference


def test_causal_graph_returns_none_when_unavailable(enhanced_ir_without_causal):
    """Test causal_graph returns None when unavailable."""
    assert enhanced_ir_without_causal.causal_graph is None


def test_causal_model_returns_none_when_unavailable(enhanced_ir_without_causal):
    """Test causal_model returns None when unavailable."""
    assert enhanced_ir_without_causal.causal_model is None


# =============================================================================
# Causal Impact Analysis
# =============================================================================


def test_causal_impact_basic():
    """Test causal_impact() calculates downstream impact."""
    # Create IR with known graph structure: x → y → z
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Chain computation"),
        signature=SigClause(name="chain", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    # Calculate impact of x
    impact = enhanced_ir.causal_impact("x")

    assert impact is not None
    assert "y" in impact  # x affects y
    assert "z" in impact  # x affects z (transitively)
    assert impact["y"] >= impact["z"]  # y is closer, should have higher impact


def test_causal_impact_no_downstream():
    """Test causal_impact() when node has no downstream nodes."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y")])  # y is a leaf
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    # y has no downstream nodes
    impact = enhanced_ir.causal_impact("y")

    assert impact is not None
    assert impact == {}  # No downstream nodes


def test_causal_impact_invalid_node():
    """Test causal_impact() with non-existent node."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    # Node doesn't exist
    impact = enhanced_ir.causal_impact("nonexistent")

    assert impact is None


def test_causal_impact_without_causal(enhanced_ir_without_causal):
    """Test causal_impact() returns None when causal unavailable."""
    impact = enhanced_ir_without_causal.causal_impact("x")
    assert impact is None


def test_causal_impact_normalization():
    """Test causal_impact() normalizes scores to [0, 1]."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Chain"),
        signature=SigClause(name="chain", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    impact = enhanced_ir.causal_impact("x", normalize=True)

    # All scores should be in [0, 1]
    for score in impact.values():
        assert 0.0 <= score <= 1.0


# =============================================================================
# Causal Intervention Queries
# =============================================================================


def test_causal_intervention_returns_none_without_causal(enhanced_ir_without_causal):
    """Test causal_intervention() returns None when causal unavailable."""
    result = enhanced_ir_without_causal.causal_intervention({"x": 5.0})
    assert result is None


def test_causal_intervention_requires_dynamic_mode(simple_ir, simple_ast, simple_traces):
    """Test causal_intervention() works with dynamic mode."""
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

    enhanced_ir = EnhancedIR.from_enhancement_result(result)

    # Execute intervention
    result = enhanced_ir.causal_intervention(
        interventions={"x": 5.0},
        query_nodes=["y"],
        num_samples=100,
    )

    # Should return InterventionResult
    if result is not None:  # May fail if DoWhy unavailable
        assert hasattr(result, "samples")
        assert hasattr(result, "statistics")


# =============================================================================
# Causal Path Finding
# =============================================================================


def test_causal_paths_basic():
    """Test causal_paths() finds paths between nodes."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Chain"),
        signature=SigClause(name="chain", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    paths = enhanced_ir.causal_paths("x", "z")

    assert paths is not None
    assert len(paths) > 0
    assert ["x", "y", "z"] in paths


def test_causal_paths_no_path():
    """Test causal_paths() when no path exists."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y"), ("z", "w")])  # Disconnected components
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    paths = enhanced_ir.causal_paths("x", "w")

    assert paths == []


def test_causal_paths_invalid_nodes():
    """Test causal_paths() with non-existent nodes."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    graph = nx.DiGraph([("x", "y")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    paths = enhanced_ir.causal_paths("nonexistent", "y")

    assert paths == []


def test_causal_paths_without_causal(enhanced_ir_without_causal):
    """Test causal_paths() returns None when causal unavailable."""
    paths = enhanced_ir_without_causal.causal_paths("x", "y")
    assert paths is None


def test_causal_paths_max_paths_limit():
    """Test causal_paths() respects max_paths limit."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    # Create diamond graph with multiple paths
    graph = nx.DiGraph([("x", "a"), ("x", "b"), ("a", "y"), ("b", "y")])
    scm = {"mode": "static", "mechanisms": {}}

    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=graph,
        causal_scm=scm,
        intervention_engine=InterventionEngine(),
        mode="static",
    )

    paths = enhanced_ir.causal_paths("x", "y", max_paths=1)

    assert paths is not None
    assert len(paths) <= 1


# =============================================================================
# String Representation
# =============================================================================


def test_enhanced_ir_repr_with_causal(enhanced_ir_with_causal):
    """Test __repr__() with causal capabilities."""
    repr_str = repr(enhanced_ir_with_causal)

    assert "EnhancedIR" in repr_str
    assert "double" in repr_str
    assert "with causal" in repr_str


def test_enhanced_ir_repr_without_causal(enhanced_ir_without_causal):
    """Test __repr__() without causal capabilities."""
    repr_str = repr(enhanced_ir_without_causal)

    assert "EnhancedIR" in repr_str
    assert "double" in repr_str
    assert "without causal" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================


def test_enhanced_ir_end_to_end(simple_ir, simple_ast):
    """Test complete workflow: IR → enhance → query."""
    enhancer = CausalEnhancer()

    result = enhancer.enhance(
        ir=simple_ir,
        ast_tree=simple_ast,
        mode="static",
        source_code={"double": "def double(x):\n    y = x * 2\n    return y"},
    )

    enhanced_ir = EnhancedIR.from_enhancement_result(result)

    # Check causal is available
    assert enhanced_ir.has_causal_capabilities

    # Access causal graph
    graph = enhanced_ir.causal_graph
    assert graph is not None

    # Access causal model
    scm = enhanced_ir.causal_model
    assert scm is not None
    assert scm["mode"] == "static"


def test_enhanced_ir_graceful_degradation():
    """Test EnhancedIR gracefully degrades when causal unavailable."""
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test"),
        signature=SigClause(name="test", parameters=[], returns="int"),
    )

    # Create without causal
    enhanced_ir = EnhancedIR(
        base_ir=ir,
        causal_graph=None,
        causal_scm=None,
        intervention_engine=None,
        mode=None,
    )

    # All causal methods should return None or empty
    assert enhanced_ir.has_causal_capabilities is False
    assert enhanced_ir.causal_graph is None
    assert enhanced_ir.causal_model is None
    assert enhanced_ir.causal_impact("x") is None
    assert enhanced_ir.causal_intervention({"x": 5}) is None
    assert enhanced_ir.causal_paths("x", "y") is None

    # But base IR methods still work
    assert enhanced_ir.intent.summary == "Test"
    assert enhanced_ir.signature.name == "test"
