"""Unit tests for IR constraint system (Phase 7)."""

from lift_sys.ir.constraints import (
    Constraint,
    ConstraintSeverity,
    ConstraintType,
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
    ReturnRequirement,
    parse_constraint,
)
from lift_sys.ir.models import IntermediateRepresentation


class TestReturnConstraint:
    """Tests for ReturnConstraint."""

    def test_return_constraint_creation(self):
        """Test creating a return constraint."""
        constraint = ReturnConstraint(
            value_name="count",
            requirement=ReturnRequirement.MUST_RETURN,
            description="Must return count value",
        )

        assert constraint.type == ConstraintType.RETURN
        assert constraint.value_name == "count"
        assert constraint.requirement == ReturnRequirement.MUST_RETURN
        assert constraint.severity == ConstraintSeverity.ERROR
        assert constraint.description == "Must return count value"

    def test_return_constraint_default_description(self):
        """Test that default description is auto-generated."""
        constraint = ReturnConstraint(value_name="result")

        assert constraint.description == "Function must return 'result' value explicitly"

    def test_return_constraint_serialization(self):
        """Test return constraint to_dict."""
        constraint = ReturnConstraint(
            value_name="count",
            requirement=ReturnRequirement.MUST_RETURN,
            description="Must return count",
        )

        data = constraint.to_dict()

        assert data["type"] == "return_constraint"
        assert data["value_name"] == "count"
        assert data["requirement"] == "MUST_RETURN"
        assert data["description"] == "Must return count"
        assert data["severity"] == "error"

    def test_return_constraint_deserialization(self):
        """Test return constraint from_dict."""
        data = {
            "type": "return_constraint",
            "value_name": "count",
            "requirement": "MUST_RETURN",
            "description": "Must return count",
            "severity": "error",
        }

        constraint = ReturnConstraint.from_dict(data)

        assert constraint.type == ConstraintType.RETURN
        assert constraint.value_name == "count"
        assert constraint.requirement == ReturnRequirement.MUST_RETURN
        assert constraint.description == "Must return count"
        assert constraint.severity == ConstraintSeverity.ERROR

    def test_return_constraint_roundtrip(self):
        """Test return constraint serialization roundtrip."""
        original = ReturnConstraint(
            value_name="result",
            requirement=ReturnRequirement.OPTIONAL_RETURN,
            description="Optional return",
            severity=ConstraintSeverity.WARNING,
        )

        data = original.to_dict()
        restored = ReturnConstraint.from_dict(data)

        assert restored.value_name == original.value_name
        assert restored.requirement == original.requirement
        assert restored.description == original.description
        assert restored.severity == original.severity


class TestLoopBehaviorConstraint:
    """Tests for LoopBehaviorConstraint."""

    def test_loop_behavior_constraint_creation(self):
        """Test creating a loop behavior constraint."""
        constraint = LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN,
            loop_variable="item",
            description="Return immediately on first match",
        )

        assert constraint.type == ConstraintType.LOOP_BEHAVIOR
        assert constraint.search_type == LoopSearchType.FIRST_MATCH
        assert constraint.requirement == LoopRequirement.EARLY_RETURN
        assert constraint.loop_variable == "item"
        assert constraint.description == "Return immediately on first match"

    def test_loop_behavior_default_description_first_match(self):
        """Test default description for FIRST_MATCH."""
        constraint = LoopBehaviorConstraint(search_type=LoopSearchType.FIRST_MATCH)

        assert "FIRST match" in constraint.description
        assert "not continue" in constraint.description

    def test_loop_behavior_default_description_last_match(self):
        """Test default description for LAST_MATCH."""
        constraint = LoopBehaviorConstraint(search_type=LoopSearchType.LAST_MATCH)

        assert "LAST match" in constraint.description

    def test_loop_behavior_default_description_all_matches(self):
        """Test default description for ALL_MATCHES."""
        constraint = LoopBehaviorConstraint(search_type=LoopSearchType.ALL_MATCHES)

        assert "ALL matches" in constraint.description

    def test_loop_behavior_serialization(self):
        """Test loop behavior constraint to_dict."""
        constraint = LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN,
            loop_variable="item",
            description="Early return required",
        )

        data = constraint.to_dict()

        assert data["type"] == "loop_constraint"
        assert data["search_type"] == "FIRST_MATCH"
        assert data["requirement"] == "EARLY_RETURN"
        assert data["loop_variable"] == "item"
        assert data["description"] == "Early return required"

    def test_loop_behavior_deserialization(self):
        """Test loop behavior constraint from_dict."""
        data = {
            "type": "loop_constraint",
            "search_type": "LAST_MATCH",
            "requirement": "ACCUMULATE",
            "loop_variable": "element",
            "description": "Accumulate all results",
        }

        constraint = LoopBehaviorConstraint.from_dict(data)

        assert constraint.search_type == LoopSearchType.LAST_MATCH
        assert constraint.requirement == LoopRequirement.ACCUMULATE
        assert constraint.loop_variable == "element"

    def test_loop_behavior_roundtrip(self):
        """Test loop behavior constraint serialization roundtrip."""
        original = LoopBehaviorConstraint(
            search_type=LoopSearchType.ALL_MATCHES,
            requirement=LoopRequirement.TRANSFORM,
            loop_variable="x",
            description="Transform all elements",
        )

        data = original.to_dict()
        restored = LoopBehaviorConstraint.from_dict(data)

        assert restored.search_type == original.search_type
        assert restored.requirement == original.requirement
        assert restored.loop_variable == original.loop_variable


class TestPositionConstraint:
    """Tests for PositionConstraint."""

    def test_position_constraint_creation(self):
        """Test creating a position constraint."""
        constraint = PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.NOT_ADJACENT,
            min_distance=1,
            description="@ and . must not be adjacent",
        )

        assert constraint.type == ConstraintType.POSITION
        assert constraint.elements == ["@", "."]
        assert constraint.requirement == PositionRequirement.NOT_ADJACENT
        assert constraint.min_distance == 1
        assert constraint.max_distance is None

    def test_position_constraint_default_description_not_adjacent(self):
        """Test default description for NOT_ADJACENT."""
        constraint = PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.NOT_ADJACENT,
        )

        assert "NOT be immediately adjacent" in constraint.description
        assert "['@', '.']" in constraint.description

    def test_position_constraint_default_description_ordered(self):
        """Test default description for ORDERED."""
        constraint = PositionConstraint(
            elements=["start", "end"],
            requirement=PositionRequirement.ORDERED,
        )

        assert "must appear in this order" in constraint.description

    def test_position_constraint_default_description_min_distance(self):
        """Test default description for MIN_DISTANCE."""
        constraint = PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.MIN_DISTANCE,
            min_distance=2,
        )

        assert "at least 2 characters apart" in constraint.description

    def test_position_constraint_default_description_max_distance(self):
        """Test default description for MAX_DISTANCE."""
        constraint = PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.MAX_DISTANCE,
            max_distance=10,
        )

        assert "at most 10 characters apart" in constraint.description

    def test_position_constraint_serialization(self):
        """Test position constraint to_dict."""
        constraint = PositionConstraint(
            elements=["@", "."],
            requirement=PositionRequirement.MIN_DISTANCE,
            min_distance=2,
            max_distance=10,
            description="Distance constraint",
        )

        data = constraint.to_dict()

        assert data["type"] == "position_constraint"
        assert data["elements"] == ["@", "."]
        assert data["requirement"] == "MIN_DISTANCE"
        assert data["min_distance"] == 2
        assert data["max_distance"] == 10

    def test_position_constraint_deserialization(self):
        """Test position constraint from_dict."""
        data = {
            "type": "position_constraint",
            "elements": ["(", ")"],
            "requirement": "ORDERED",
            "min_distance": 0,
            "description": "Parentheses must be ordered",
        }

        constraint = PositionConstraint.from_dict(data)

        assert constraint.elements == ["(", ")"]
        assert constraint.requirement == PositionRequirement.ORDERED
        assert constraint.min_distance == 0

    def test_position_constraint_roundtrip(self):
        """Test position constraint serialization roundtrip."""
        original = PositionConstraint(
            elements=["<", ">"],
            requirement=PositionRequirement.NOT_ADJACENT,
            min_distance=1,
            max_distance=100,
            description="Angle brackets spacing",
        )

        data = original.to_dict()
        restored = PositionConstraint.from_dict(data)

        assert restored.elements == original.elements
        assert restored.requirement == original.requirement
        assert restored.min_distance == original.min_distance
        assert restored.max_distance == original.max_distance


class TestConstraintParsing:
    """Tests for constraint parsing and polymorphism."""

    def test_parse_return_constraint(self):
        """Test parsing return constraint via parse_constraint."""
        data = {
            "type": "return_constraint",
            "value_name": "result",
            "requirement": "MUST_RETURN",
            "description": "Must return result",
        }

        constraint = parse_constraint(data)

        assert isinstance(constraint, ReturnConstraint)
        assert constraint.value_name == "result"

    def test_parse_loop_behavior_constraint(self):
        """Test parsing loop behavior constraint via parse_constraint."""
        data = {
            "type": "loop_constraint",
            "search_type": "FIRST_MATCH",
            "requirement": "EARLY_RETURN",
            "description": "Early return",
        }

        constraint = parse_constraint(data)

        assert isinstance(constraint, LoopBehaviorConstraint)
        assert constraint.search_type == LoopSearchType.FIRST_MATCH

    def test_parse_position_constraint(self):
        """Test parsing position constraint via parse_constraint."""
        data = {
            "type": "position_constraint",
            "elements": ["@", "."],
            "requirement": "NOT_ADJACENT",
            "description": "Not adjacent",
        }

        constraint = parse_constraint(data)

        assert isinstance(constraint, PositionConstraint)
        assert constraint.elements == ["@", "."]

    def test_constraint_from_dict_routing(self):
        """Test Constraint.from_dict routes to correct subclass."""
        data = {
            "type": "return_constraint",
            "value_name": "x",
            "requirement": "MUST_RETURN",
            "description": "Test",
        }

        constraint = Constraint.from_dict(data)

        assert isinstance(constraint, ReturnConstraint)
        assert constraint.value_name == "x"


class TestIRIntegration:
    """Tests for constraint integration with IntermediateRepresentation."""

    def test_ir_with_constraints(self):
        """Test creating IR with constraints."""
        from lift_sys.ir.models import IntentClause, Parameter, SigClause

        intent = IntentClause(summary="Test function")
        signature = SigClause(
            name="test_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        )

        constraints = [
            ReturnConstraint(value_name="result", description="Must return result"),
            LoopBehaviorConstraint(
                search_type=LoopSearchType.FIRST_MATCH,
                description="Early return",
            ),
        ]

        ir = IntermediateRepresentation(
            intent=intent,
            signature=signature,
            constraints=constraints,
        )

        assert len(ir.constraints) == 2
        assert isinstance(ir.constraints[0], ReturnConstraint)
        assert isinstance(ir.constraints[1], LoopBehaviorConstraint)

    def test_ir_serialization_with_constraints(self):
        """Test IR serialization includes constraints."""
        from lift_sys.ir.models import IntentClause, Parameter, SigClause

        intent = IntentClause(summary="Test function")
        signature = SigClause(
            name="test_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        )

        constraints = [
            ReturnConstraint(value_name="result"),
        ]

        ir = IntermediateRepresentation(
            intent=intent,
            signature=signature,
            constraints=constraints,
        )

        data = ir.to_dict()

        assert "constraints" in data
        assert len(data["constraints"]) == 1
        assert data["constraints"][0]["type"] == "return_constraint"
        assert data["constraints"][0]["value_name"] == "result"

    def test_ir_deserialization_with_constraints(self):
        """Test IR deserialization restores constraints."""
        payload = {
            "intent": {"summary": "Test", "rationale": None, "holes": []},
            "signature": {
                "name": "test_func",
                "parameters": [],
                "returns": "int",
                "holes": [],
            },
            "effects": [],
            "assertions": [],
            "metadata": {},
            "constraints": [
                {
                    "type": "return_constraint",
                    "value_name": "result",
                    "requirement": "MUST_RETURN",
                    "description": "Must return result",
                    "severity": "error",
                },
                {
                    "type": "loop_constraint",
                    "search_type": "FIRST_MATCH",
                    "requirement": "EARLY_RETURN",
                    "description": "Early return",
                    "severity": "error",
                },
            ],
        }

        ir = IntermediateRepresentation.from_dict(payload)

        assert len(ir.constraints) == 2
        assert isinstance(ir.constraints[0], ReturnConstraint)
        assert ir.constraints[0].value_name == "result"
        assert isinstance(ir.constraints[1], LoopBehaviorConstraint)
        assert ir.constraints[1].search_type == LoopSearchType.FIRST_MATCH

    def test_ir_roundtrip_with_constraints(self):
        """Test IR serialization roundtrip preserves constraints."""
        from lift_sys.ir.models import IntentClause, Parameter, SigClause

        intent = IntentClause(summary="Test function")
        signature = SigClause(
            name="test_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        )

        constraints = [
            ReturnConstraint(value_name="result"),
            PositionConstraint(elements=["@", "."], requirement=PositionRequirement.NOT_ADJACENT),
        ]

        original_ir = IntermediateRepresentation(
            intent=intent,
            signature=signature,
            constraints=constraints,
        )

        data = original_ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(data)

        assert len(restored_ir.constraints) == 2
        assert isinstance(restored_ir.constraints[0], ReturnConstraint)
        assert restored_ir.constraints[0].value_name == "result"
        assert isinstance(restored_ir.constraints[1], PositionConstraint)
        assert restored_ir.constraints[1].elements == ["@", "."]

    def test_ir_without_constraints_backward_compatibility(self):
        """Test that IR without constraints field works (backward compatibility)."""
        payload = {
            "intent": {"summary": "Test", "rationale": None, "holes": []},
            "signature": {
                "name": "test_func",
                "parameters": [],
                "returns": "int",
                "holes": [],
            },
            "effects": [],
            "assertions": [],
            "metadata": {},
            # No constraints field
        }

        ir = IntermediateRepresentation.from_dict(payload)

        assert ir.constraints == []

    def test_ir_with_invalid_constraint_skips_it(self):
        """Test that invalid constraints are skipped with warning."""
        payload = {
            "intent": {"summary": "Test", "rationale": None, "holes": []},
            "signature": {
                "name": "test_func",
                "parameters": [],
                "returns": "int",
                "holes": [],
            },
            "effects": [],
            "assertions": [],
            "metadata": {},
            "constraints": [
                {
                    "type": "return_constraint",
                    "value_name": "result",
                    "requirement": "MUST_RETURN",
                    "description": "Valid constraint",
                    "severity": "error",
                },
                {
                    "type": "invalid_type",  # Invalid constraint type
                    "description": "This should be skipped",
                },
            ],
        }

        # Should not raise exception, just skip invalid constraint
        ir = IntermediateRepresentation.from_dict(payload)

        # Valid constraint should be present
        assert len(ir.constraints) == 1
        assert isinstance(ir.constraints[0], ReturnConstraint)


class TestConstraintSeverity:
    """Tests for constraint severity levels."""

    def test_error_severity(self):
        """Test ERROR severity constraint."""
        constraint = ReturnConstraint(
            value_name="result",
            severity=ConstraintSeverity.ERROR,
        )

        assert constraint.severity == ConstraintSeverity.ERROR
        data = constraint.to_dict()
        assert data["severity"] == "error"

    def test_warning_severity(self):
        """Test WARNING severity constraint."""
        constraint = ReturnConstraint(
            value_name="result",
            severity=ConstraintSeverity.WARNING,
        )

        assert constraint.severity == ConstraintSeverity.WARNING
        data = constraint.to_dict()
        assert data["severity"] == "warning"

    def test_default_severity_is_error(self):
        """Test that default severity is ERROR."""
        constraint = ReturnConstraint(value_name="result")

        assert constraint.severity == ConstraintSeverity.ERROR
