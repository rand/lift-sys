"""Unit tests for IR models and serialization.

Tests cover:
- Model creation
- Serialization (to_dict)
- Deserialization (from_dict)
- Round-trip fidelity
- TypedHole handling
- Edge cases
"""
import pytest

from lift_sys.ir.models import (
    IntermediateRepresentation,
    IntentClause,
    SigClause,
    Parameter,
    AssertClause,
    EffectClause,
    TypedHole,
    HoleKind,
    Metadata,
)


@pytest.mark.unit
class TestIRModels:
    """Unit tests for IR model classes."""

    def test_create_simple_ir(self):
        """Test creating simple IR object."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test function"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        assert ir.signature.name == "test"
        assert len(ir.signature.parameters) == 1
        assert ir.intent.summary == "test function"

    def test_parameter_creation(self):
        """Test Parameter model creation."""
        param = Parameter(name="x", type_hint="int", description="input value")

        assert param.name == "x"
        assert param.type_hint == "int"
        assert param.description == "input value"

    def test_parameter_to_dict(self):
        """Test Parameter serialization."""
        param = Parameter(name="x", type_hint="int", description="test")
        param_dict = param.to_dict()

        assert param_dict["name"] == "x"
        assert param_dict["type_hint"] == "int"
        assert param_dict["description"] == "test"

    def test_typed_hole_creation(self):
        """Test TypedHole model creation."""
        hole = TypedHole(
            identifier="test_hole",
            type_hint="str",
            description="test description",
            kind=HoleKind.INTENT,
        )

        assert hole.identifier == "test_hole"
        assert hole.type_hint == "str"
        assert hole.description == "test description"
        assert hole.kind == HoleKind.INTENT

    def test_typed_hole_to_dict(self):
        """Test TypedHole serialization."""
        hole = TypedHole(
            identifier="test_hole",
            type_hint="str",
            description="test",
            kind=HoleKind.SIGNATURE,
        )
        hole_dict = hole.to_dict()

        assert hole_dict["identifier"] == "test_hole"
        assert hole_dict["type_hint"] == "str"
        assert hole_dict["description"] == "test"
        assert hole_dict["kind"] == HoleKind.SIGNATURE.value

    def test_ir_to_dict(self, simple_ir):
        """Test IntermediateRepresentation serialization."""
        ir_dict = simple_ir.to_dict()

        assert "intent" in ir_dict
        assert "signature" in ir_dict
        assert "effects" in ir_dict
        assert "assertions" in ir_dict
        assert "metadata" in ir_dict

        assert ir_dict["signature"]["name"] == "add"
        assert len(ir_dict["signature"]["parameters"]) == 2

    def test_ir_from_dict(self, simple_ir):
        """Test IntermediateRepresentation deserialization."""
        ir_dict = simple_ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(ir_dict)

        assert restored_ir.signature.name == simple_ir.signature.name
        assert len(restored_ir.signature.parameters) == len(simple_ir.signature.parameters)
        assert restored_ir.intent.summary == simple_ir.intent.summary

    def test_ir_round_trip_fidelity(self, simple_ir):
        """Test that IR survives round-trip serialization."""
        ir_dict = simple_ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(ir_dict)

        # Check all major fields
        assert restored_ir.signature.name == simple_ir.signature.name
        assert restored_ir.signature.returns == simple_ir.signature.returns
        assert len(restored_ir.signature.parameters) == len(simple_ir.signature.parameters)
        assert len(restored_ir.assertions) == len(simple_ir.assertions)
        assert len(restored_ir.effects) == len(simple_ir.effects)

        # Check parameter details
        for orig_param, restored_param in zip(simple_ir.signature.parameters, restored_ir.signature.parameters):
            assert orig_param.name == restored_param.name
            assert orig_param.type_hint == restored_param.type_hint

    def test_ir_with_holes_round_trip(self, parsed_with_holes_ir):
        """Test round-trip serialization of IR with typed holes."""
        ir_dict = parsed_with_holes_ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(ir_dict)

        original_holes = parsed_with_holes_ir.typed_holes()
        restored_holes = restored_ir.typed_holes()

        assert len(restored_holes) == len(original_holes)

        # Check hole details preserved
        orig_ids = {h.identifier for h in original_holes}
        restored_ids = {h.identifier for h in restored_holes}
        assert orig_ids == restored_ids

    def test_metadata_serialization(self):
        """Test Metadata serialization."""
        metadata = Metadata(
            source_path="/path/to/file.py",
            language="python",
            origin="reverse",
        )
        meta_dict = metadata.to_dict()

        assert meta_dict["source_path"] == "/path/to/file.py"
        assert meta_dict["language"] == "python"
        assert meta_dict["origin"] == "reverse"

    def test_intent_clause_with_holes(self):
        """Test IntentClause with holes."""
        hole = TypedHole(
            identifier="strategy",
            type_hint="str",
            description="optimization strategy",
            kind=HoleKind.INTENT,
        )
        intent = IntentClause(
            summary="optimize function",
            holes=[hole],
        )

        assert len(intent.holes) == 1
        assert intent.holes[0].identifier == "strategy"

    def test_sig_clause_with_holes(self):
        """Test SigClause with holes."""
        hole = TypedHole(
            identifier="max_depth",
            type_hint="int",
            description="recursion limit",
            kind=HoleKind.SIGNATURE,
        )
        sig = SigClause(
            name="recursive_func",
            parameters=[Parameter(name="n", type_hint="int")],
            returns="int",
            holes=[hole],
        )

        assert len(sig.holes) == 1
        assert sig.holes[0].identifier == "max_depth"

    def test_effect_clause_with_holes(self):
        """Test EffectClause with holes."""
        hole = TypedHole(
            identifier="cache_policy",
            type_hint="str",
            description="caching strategy",
            kind=HoleKind.EFFECT,
        )
        effect = EffectClause(
            description="modifies cache",
            holes=[hole],
        )

        assert len(effect.holes) == 1
        assert effect.holes[0].identifier == "cache_policy"

    def test_assert_clause_with_holes(self):
        """Test AssertClause with holes."""
        hole = TypedHole(
            identifier="bound",
            type_hint="int",
            description="upper bound",
            kind=HoleKind.ASSERTION,
        )
        assertion = AssertClause(
            predicate="x < 100",
            holes=[hole],
        )

        assert len(assertion.holes) == 1
        assert assertion.holes[0].identifier == "bound"

    def test_typed_holes_collection(self, parsed_with_holes_ir):
        """Test typed_holes() method collects all holes."""
        all_holes = parsed_with_holes_ir.typed_holes()

        assert len(all_holes) > 0

        # Should collect holes from all clauses
        intent_holes = parsed_with_holes_ir.intent.holes
        sig_holes = parsed_with_holes_ir.signature.holes

        # Total should include holes from all sources
        assert len(all_holes) >= len(intent_holes) + len(sig_holes)

    def test_hole_kind_enum(self):
        """Test HoleKind enum values."""
        assert HoleKind.INTENT.value == "intent"
        assert HoleKind.SIGNATURE.value == "signature"
        assert HoleKind.EFFECT.value == "effect"
        assert HoleKind.ASSERTION.value == "assertion"

    def test_parameter_without_description(self):
        """Test Parameter without optional description."""
        param = Parameter(name="x", type_hint="int")

        assert param.name == "x"
        assert param.type_hint == "int"
        assert param.description is None

    def test_sig_clause_without_return_type(self):
        """Test SigClause without return type."""
        sig = SigClause(
            name="void_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns=None,
        )

        assert sig.name == "void_func"
        assert sig.returns is None

    def test_sig_clause_without_parameters(self):
        """Test SigClause without parameters."""
        sig = SigClause(
            name="no_params",
            parameters=[],
            returns="int",
        )

        assert sig.name == "no_params"
        assert len(sig.parameters) == 0

    def test_ir_with_no_effects(self, simple_ir):
        """Test IR without effects clause."""
        assert len(simple_ir.effects) == 0

        ir_dict = simple_ir.to_dict()
        assert "effects" in ir_dict
        assert len(ir_dict["effects"]) == 0

    def test_ir_with_no_assertions(self):
        """Test IR without assertions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="test"),
            signature=SigClause(
                name="test",
                parameters=[],
                returns="int",
            ),
            effects=[],
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        assert len(ir.assertions) == 0

    def test_complex_ir_serialization(self, complex_ir):
        """Test serialization of complex IR with all clauses."""
        ir_dict = complex_ir.to_dict()

        assert "intent" in ir_dict
        assert "signature" in ir_dict
        assert "effects" in ir_dict
        assert "assertions" in ir_dict
        assert "metadata" in ir_dict

        # Check effects preserved
        assert len(ir_dict["effects"]) == len(complex_ir.effects)

        # Check assertions preserved
        assert len(ir_dict["assertions"]) == len(complex_ir.assertions)
