"""Unit tests for InterventionEngine (STEP-10: Parser implementation).

Tests intervention specification parsing from multiple formats:
- String DSL: "do(x=5)", "do(x=x+2)", etc.
- Dict/JSON: {"type": "hard", "node": "x", "value": 5}
- Objects: HardIntervention, SoftIntervention, InterventionSpec
"""

import networkx as nx
import pytest

from lift_sys.causal.intervention_engine import (
    InterventionEngine,
    ParseError,
    ValidationError,
)
from lift_sys.causal.intervention_spec import (
    HardIntervention,
    InterventionSpec,
    SoftIntervention,
)

# ============================================================================
# String Parsing Tests (STEP-10)
# ============================================================================


def test_parse_hard_intervention_string():
    """Test parsing hard intervention: do(x=5)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=5)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, HardIntervention)
    assert intervention.node == "x"
    assert intervention.value == 5.0


def test_parse_hard_intervention_negative():
    """Test parsing hard intervention with negative value: do(x=-10)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=-10)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, HardIntervention)
    assert intervention.node == "x"
    assert intervention.value == -10.0


def test_parse_hard_intervention_float():
    """Test parsing hard intervention with float: do(x=3.14)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=3.14)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, HardIntervention)
    assert intervention.value == 3.14


def test_parse_soft_intervention_shift_positive():
    """Test parsing soft intervention (shift): do(x=x+2)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x+2)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "shift"
    assert intervention.param == 2.0


def test_parse_soft_intervention_shift_negative():
    """Test parsing soft intervention (negative shift): do(x=x-3)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x-3)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "shift"
    assert intervention.param == -3.0


def test_parse_soft_intervention_scale_multiply():
    """Test parsing soft intervention (scale): do(x=x*2)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x*2)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "scale"
    assert intervention.param == 2.0


def test_parse_soft_intervention_scale_divide():
    """Test parsing soft intervention (scale via division): do(x=x/2)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x/2)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "scale"
    assert intervention.param == 0.5  # 1/2


def test_parse_soft_intervention_float_param():
    """Test parsing soft intervention with float parameter: do(x=x+1.5)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x+1.5)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.param == 1.5


def test_parse_multiple_interventions():
    """Test parsing multiple interventions: do(x=5, y=10)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=5, y=10)")

    assert len(spec.interventions) == 2

    # Check first intervention
    assert isinstance(spec.interventions[0], HardIntervention)
    assert spec.interventions[0].node == "x"
    assert spec.interventions[0].value == 5.0

    # Check second intervention
    assert isinstance(spec.interventions[1], HardIntervention)
    assert spec.interventions[1].node == "y"
    assert spec.interventions[1].value == 10.0


def test_parse_multiple_mixed_interventions():
    """Test parsing multiple mixed interventions: do(x=5, y=y+2)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=5, y=y+2)")

    assert len(spec.interventions) == 2

    # First: hard intervention
    assert isinstance(spec.interventions[0], HardIntervention)
    assert spec.interventions[0].node == "x"
    assert spec.interventions[0].value == 5.0

    # Second: soft intervention
    assert isinstance(spec.interventions[1], SoftIntervention)
    assert spec.interventions[1].node == "y"
    assert spec.interventions[1].transform == "shift"
    assert spec.interventions[1].param == 2.0


def test_parse_string_with_whitespace():
    """Test parsing with various whitespace: do( x = 5 , y = 10 )."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do( x = 5 , y = 10 )")

    assert len(spec.interventions) == 2
    assert spec.interventions[0].node == "x"
    assert spec.interventions[1].node == "y"


def test_parse_custom_expression():
    """Test parsing custom expression: do(x=x**2)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=x**2)")

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "custom"
    assert intervention.custom_expr == "x**2"


# ============================================================================
# Dict Parsing Tests (STEP-10)
# ============================================================================


def test_parse_dict_hard_intervention():
    """Test parsing dict hard intervention."""
    engine = InterventionEngine()
    spec = engine.parse_intervention({"type": "hard", "node": "x", "value": 5})

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, HardIntervention)
    assert intervention.node == "x"
    assert intervention.value == 5


def test_parse_dict_soft_intervention_shift():
    """Test parsing dict soft intervention (shift)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention(
        {"type": "soft", "node": "x", "transform": "shift", "param": 2.0}
    )

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.node == "x"
    assert intervention.transform == "shift"
    assert intervention.param == 2.0


def test_parse_dict_soft_intervention_scale():
    """Test parsing dict soft intervention (scale)."""
    engine = InterventionEngine()
    spec = engine.parse_intervention(
        {"type": "soft", "node": "x", "transform": "scale", "param": 1.5}
    )

    assert len(spec.interventions) == 1
    intervention = spec.interventions[0]
    assert isinstance(intervention, SoftIntervention)
    assert intervention.transform == "scale"
    assert intervention.param == 1.5


def test_parse_dict_complete_intervention_spec():
    """Test parsing complete InterventionSpec dict."""
    engine = InterventionEngine()
    spec = engine.parse_intervention(
        {
            "interventions": [
                {"type": "hard", "node": "x", "value": 5},
                {"type": "soft", "node": "y", "transform": "shift", "param": 2.0},
            ],
            "query_nodes": ["z", "w"],
            "num_samples": 500,
        }
    )

    assert len(spec.interventions) == 2
    assert spec.query_nodes == ["z", "w"]
    assert spec.num_samples == 500

    # Check interventions
    assert isinstance(spec.interventions[0], HardIntervention)
    assert spec.interventions[0].node == "x"

    assert isinstance(spec.interventions[1], SoftIntervention)
    assert spec.interventions[1].node == "y"


# ============================================================================
# Object Parsing Tests (STEP-10)
# ============================================================================


def test_parse_hard_intervention_object():
    """Test parsing HardIntervention object."""
    engine = InterventionEngine()
    intervention = HardIntervention(node="x", value=5)
    spec = engine.parse_intervention(intervention)

    assert len(spec.interventions) == 1
    assert spec.interventions[0] is intervention


def test_parse_soft_intervention_object():
    """Test parsing SoftIntervention object."""
    engine = InterventionEngine()
    intervention = SoftIntervention(node="x", transform="shift", param=2.0)
    spec = engine.parse_intervention(intervention)

    assert len(spec.interventions) == 1
    assert spec.interventions[0] is intervention


def test_parse_intervention_spec_passthrough():
    """Test pass-through of InterventionSpec object."""
    engine = InterventionEngine()
    original_spec = InterventionSpec(
        interventions=[HardIntervention(node="x", value=5)], query_nodes=["y"], num_samples=1000
    )
    parsed_spec = engine.parse_intervention(original_spec)

    # Should return the same object (pass-through)
    assert parsed_spec is original_spec


# ============================================================================
# Error Handling Tests (STEP-10)
# ============================================================================


def test_parse_missing_do_wrapper():
    """Test error when missing 'do(...)' wrapper."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="must be in format 'do\\(...\\)'"):
        engine.parse_intervention("x=5")


def test_parse_missing_equals():
    """Test error when missing '=' in intervention."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="missing '='"):
        engine.parse_intervention("do(x)")


def test_parse_invalid_hard_intervention_value():
    """Test error when hard intervention value is not numeric."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="Invalid hard intervention value"):
        engine.parse_intervention("do(x=abc)")


def test_parse_invalid_shift_parameter():
    """Test error when shift parameter is not numeric."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="Invalid shift parameter"):
        engine.parse_intervention("do(x=x+abc)")


def test_parse_invalid_scale_parameter():
    """Test error when scale parameter is not numeric."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="Invalid scale parameter"):
        engine.parse_intervention("do(x=x*abc)")


def test_parse_division_by_zero():
    """Test error when dividing by zero."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="Invalid scale parameter"):
        engine.parse_intervention("do(x=x/0)")


def test_parse_unsupported_format():
    """Test error when format is unsupported."""
    engine = InterventionEngine()

    with pytest.raises(ParseError, match="Unsupported intervention format"):
        engine.parse_intervention(12345)  # Integer is not supported


def test_parse_unknown_intervention_type_dict():
    """Test error when dict has unknown intervention type."""
    engine = InterventionEngine()

    with pytest.raises(ValueError, match="Unknown intervention type"):
        engine.parse_intervention({"type": "unknown", "node": "x"})


# ============================================================================
# Validation Tests (STEP-10)
# ============================================================================


def test_validate_intervention_nodes_exist():
    """Test validation passes when intervention nodes exist in graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    spec = InterventionSpec(interventions=[HardIntervention(node="x", value=5)])

    # Should not raise
    engine.validate_intervention(spec, graph)


def test_validate_intervention_node_not_in_graph():
    """Test validation fails when intervention node not in graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y")])
    spec = InterventionSpec(interventions=[HardIntervention(node="z", value=5)])

    with pytest.raises(ValidationError, match="node 'z' not in causal graph"):
        engine.validate_intervention(spec, graph)


def test_validate_query_nodes_exist():
    """Test validation passes when query nodes exist in graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    spec = InterventionSpec(
        interventions=[HardIntervention(node="x", value=5)], query_nodes=["y", "z"]
    )

    # Should not raise
    engine.validate_intervention(spec, graph)


def test_validate_query_node_not_in_graph():
    """Test validation fails when query node not in graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y")])
    spec = InterventionSpec(interventions=[HardIntervention(node="x", value=5)], query_nodes=["z"])

    with pytest.raises(ValidationError, match="Query node 'z' not in causal graph"):
        engine.validate_intervention(spec, graph)


def test_validate_multiple_interventions():
    """Test validation with multiple interventions."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y"), ("y", "z")])
    spec = InterventionSpec(
        interventions=[
            HardIntervention(node="x", value=5),
            SoftIntervention(node="y", transform="shift", param=2.0),
        ]
    )

    # Should not raise
    engine.validate_intervention(spec, graph)


def test_validate_error_message_includes_available_nodes():
    """Test validation error includes list of available nodes."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("a", "b"), ("b", "c")])
    spec = InterventionSpec(interventions=[HardIntervention(node="x", value=5)])

    with pytest.raises(ValidationError, match="Available nodes: \\['a', 'b', 'c'\\]"):
        engine.validate_intervention(spec, graph)


# ============================================================================
# Execute Method Tests (STEP-11 stub)
# ============================================================================


def test_execute_not_yet_implemented():
    """Test execute method raises NotImplementedError (STEP-11 pending)."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y")])
    scm = {}  # Fitted SCM (future)

    with pytest.raises(NotImplementedError, match="STEP-11"):
        engine.execute(scm, "do(x=5)", graph)


def test_execute_validates_before_execution():
    """Test execute validates intervention before attempting execution."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y")])
    scm = {}

    # Invalid node should raise ValidationError, not NotImplementedError
    with pytest.raises(ValidationError, match="node 'z' not in causal graph"):
        engine.execute(scm, "do(z=5)", graph)


# ============================================================================
# Integration Tests (STEP-10 with other components)
# ============================================================================


def test_parse_and_validate_workflow():
    """Test complete parse → validate workflow."""
    engine = InterventionEngine()
    graph = nx.DiGraph([("x", "y"), ("y", "z")])

    # Parse from string
    spec = engine.parse_intervention("do(x=5, y=y+2)")

    # Validate
    engine.validate_intervention(spec, graph)

    # Check result
    assert len(spec.interventions) == 2
    assert spec.interventions[0].node == "x"
    assert spec.interventions[1].node == "y"


def test_parse_multiple_formats_equivalent():
    """Test that different formats produce equivalent specs."""
    engine = InterventionEngine()

    # String format
    spec1 = engine.parse_intervention("do(x=5)")

    # Dict format
    spec2 = engine.parse_intervention({"type": "hard", "node": "x", "value": 5})

    # Object format
    spec3 = engine.parse_intervention(HardIntervention(node="x", value=5))

    # All should produce equivalent interventions
    assert spec1.interventions[0].node == spec2.interventions[0].node == spec3.interventions[0].node
    assert (
        spec1.interventions[0].value == spec2.interventions[0].value == spec3.interventions[0].value
    )


def test_scm_cache_initialization():
    """Test that SCM cache is initialized."""
    engine = InterventionEngine()

    assert hasattr(engine, "scm_cache")
    assert isinstance(engine.scm_cache, dict)
    assert len(engine.scm_cache) == 0


# ============================================================================
# Edge Cases and Robustness
# ============================================================================


def test_parse_empty_graph_validation():
    """Test validation with empty graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph()  # Empty graph
    spec = InterventionSpec(interventions=[HardIntervention(node="x", value=5)])

    with pytest.raises(ValidationError, match="not in causal graph"):
        engine.validate_intervention(spec, graph)


def test_parse_single_node_graph():
    """Test validation with single-node graph."""
    engine = InterventionEngine()
    graph = nx.DiGraph()
    graph.add_node("x")
    spec = InterventionSpec(interventions=[HardIntervention(node="x", value=5)])

    # Should pass
    engine.validate_intervention(spec, graph)


def test_parse_intervention_with_underscores():
    """Test parsing intervention with underscore in node name."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(node_name=5)")

    assert spec.interventions[0].node == "node_name"


def test_parse_intervention_with_numbers():
    """Test parsing intervention with numbers in node name."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x1=5)")

    assert spec.interventions[0].node == "x1"


def test_parse_large_value():
    """Test parsing very large intervention value."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=999999)")

    assert spec.interventions[0].value == 999999.0


def test_parse_very_small_value():
    """Test parsing very small intervention value."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=0.0001)")

    assert spec.interventions[0].value == 0.0001


def test_parse_scientific_notation():
    """Test parsing scientific notation value."""
    engine = InterventionEngine()
    spec = engine.parse_intervention("do(x=1e-5)")

    assert spec.interventions[0].value == 1e-5
