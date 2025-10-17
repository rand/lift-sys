"""Unit tests for Constraint Detector (Phase 7)."""

from lift_sys.ir.constraint_detector import ConstraintDetector, detect_and_apply_constraints
from lift_sys.ir.constraints import (
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
)
from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)


class TestReturnConstraintDetection:
    """Tests for detecting return constraints."""

    def test_detects_return_for_count_function(self):
        """Should detect return constraint for 'count' function."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the number of words in a string"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[EffectClause(description="Split text into words and count them")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        # Should detect return constraint
        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 1
        assert return_constraints[0].value_name == "count"

    def test_detects_return_for_compute_function(self):
        """Should detect return constraint for functions that compute values."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Compute the sum of all elements"),
            signature=SigClause(
                name="compute_sum",
                parameters=[Parameter(name="numbers", type_hint="list[int]")],
                returns="int",
            ),
            effects=[EffectClause(description="Iterate and sum all numbers")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 1
        assert return_constraints[0].value_name == "sum"

    def test_no_return_constraint_when_explicit_return_mentioned(self):
        """Should NOT detect constraint when return is already explicit."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate factorial"),
            signature=SigClause(
                name="factorial",
                parameters=[Parameter(name="n", type_hint="int")],
                returns="int",
            ),
            effects=[EffectClause(description="Multiply numbers from 1 to n and return result")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        # Should NOT detect return constraint (return already mentioned)
        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 0

    def test_no_return_constraint_for_none_return_type(self):
        """Should NOT detect constraint for None return type."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Print the count of items"),
            signature=SigClause(
                name="print_count",
                parameters=[Parameter(name="items", type_hint="list")],
                returns="None",
            ),
            effects=[EffectClause(description="Count items and print to console")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 0

    def test_no_return_constraint_when_no_compute_keywords(self):
        """Should NOT detect constraint without compute keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Print hello world"),
            signature=SigClause(
                name="greet",
                parameters=[],
                returns="str",
            ),
            effects=[EffectClause(description="Display greeting message")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 0


class TestLoopBehaviorConstraintDetection:
    """Tests for detecting loop behavior constraints."""

    def test_detects_first_match_constraint(self):
        """Should detect FIRST_MATCH for 'find first' keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find the first index of a value in a list"),
            signature=SigClause(
                name="find_index",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="int",
            ),
            effects=[EffectClause(description="Iterate through list to find first occurrence")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 1
        assert loop_constraints[0].search_type == LoopSearchType.FIRST_MATCH
        assert loop_constraints[0].requirement == LoopRequirement.EARLY_RETURN

    def test_detects_last_match_constraint(self):
        """Should detect LAST_MATCH for 'last' keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find the last occurrence of a character"),
            signature=SigClause(
                name="find_last",
                parameters=[
                    Parameter(name="text", type_hint="str"),
                    Parameter(name="char", type_hint="str"),
                ],
                returns="int",
            ),
            effects=[EffectClause(description="Loop through string to find last match")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 1
        assert loop_constraints[0].search_type == LoopSearchType.LAST_MATCH
        assert loop_constraints[0].requirement == LoopRequirement.ACCUMULATE

    def test_detects_all_matches_constraint(self):
        """Should detect ALL_MATCHES for 'all' keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find all indices where value appears"),
            signature=SigClause(
                name="find_all_indices",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="list[int]",
            ),
            effects=[EffectClause(description="Iterate to collect all matching indices")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 1
        assert loop_constraints[0].search_type == LoopSearchType.ALL_MATCHES
        assert loop_constraints[0].requirement == LoopRequirement.ACCUMULATE

    def test_no_loop_constraint_without_loop_keywords(self):
        """Should NOT detect constraint without loop keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate sum of two numbers"),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[EffectClause(description="Add a and b")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 0

    def test_extracts_loop_variable_from_effects(self):
        """Should extract loop variable name from effects."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first even number"),
            signature=SigClause(
                name="find_first_even",
                parameters=[Parameter(name="numbers", type_hint="list[int]")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Iterate over items and return first even number found")
            ],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 1
        # Should extract "items" from "iterate over items"
        assert loop_constraints[0].loop_variable == "items"


class TestPositionConstraintDetection:
    """Tests for detecting position constraints."""

    def test_detects_email_validation_constraint(self):
        """Should detect adjacency constraint for email validation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email address format"),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            effects=[EffectClause(description="Check that @ and . are present and not adjacent")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        pos_constraints = [c for c in constraints if isinstance(c, PositionConstraint)]
        assert len(pos_constraints) == 1
        assert pos_constraints[0].elements == ["@", "."]
        assert pos_constraints[0].requirement == PositionRequirement.NOT_ADJACENT

    def test_detects_parentheses_matching_constraint(self):
        """Should detect ordering constraint for parentheses."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check if parentheses are balanced"),
            signature=SigClause(
                name="is_balanced",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="bool",
            ),
            effects=[EffectClause(description="Check balanced parentheses with correct position")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        pos_constraints = [c for c in constraints if isinstance(c, PositionConstraint)]
        assert len(pos_constraints) == 1
        assert pos_constraints[0].elements == ["(", ")"]
        assert pos_constraints[0].requirement == PositionRequirement.ORDERED

    def test_no_position_constraint_without_position_keywords(self):
        """Should NOT detect constraint without position keywords."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Reverse a string"),
            signature=SigClause(
                name="reverse_string",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="str",
            ),
            effects=[EffectClause(description="Return characters in reverse order")],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        pos_constraints = [c for c in constraints if isinstance(c, PositionConstraint)]
        assert len(pos_constraints) == 0


class TestMultipleConstraintDetection:
    """Tests for detecting multiple constraints together."""

    def test_detects_both_return_and_loop_constraints(self):
        """Should detect both return and loop constraints when applicable."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count occurrences of first matching pattern"),
            signature=SigClause(
                name="count_first_match",
                parameters=[
                    Parameter(name="text", type_hint="str"),
                    Parameter(name="pattern", type_hint="str"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Iterate to find first occurrence and count characters")
            ],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        # Should detect both constraints
        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]

        assert len(return_constraints) == 1
        assert len(loop_constraints) == 1

    def test_detects_all_three_constraint_types(self):
        """Should detect return, loop, and position constraints together."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first valid email and compute its index"),
            signature=SigClause(
                name="find_first_valid_email",
                parameters=[Parameter(name="emails", type_hint="list[str]")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Iterate through emails, check @ and . are not adjacent")
            ],
        )

        detector = ConstraintDetector()
        constraints = detector.detect_constraints(ir)

        # Should detect all three types
        return_constraints = [c for c in constraints if isinstance(c, ReturnConstraint)]
        loop_constraints = [c for c in constraints if isinstance(c, LoopBehaviorConstraint)]
        pos_constraints = [c for c in constraints if isinstance(c, PositionConstraint)]

        assert len(return_constraints) == 1
        assert len(loop_constraints) == 1
        assert len(pos_constraints) == 1


class TestDetectAndApplyConstraints:
    """Tests for the convenience function."""

    def test_applies_constraints_to_ir(self):
        """Should add detected constraints to IR."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[EffectClause(description="Split and count")],
        )

        # IR starts with no constraints
        assert len(ir.constraints) == 0

        # Apply detection
        result_ir = detect_and_apply_constraints(ir)

        # Should return same IR object (for chaining)
        assert result_ir is ir

        # Should have added constraints
        assert len(ir.constraints) > 0

    def test_does_not_add_duplicate_constraints(self):
        """Should not add duplicate constraint types."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[EffectClause(description="Split and count")],
        )

        # Apply detection twice
        detect_and_apply_constraints(ir)
        initial_count = len(ir.constraints)

        detect_and_apply_constraints(ir)

        # Count should not increase (no duplicates)
        assert len(ir.constraints) == initial_count

    def test_preserves_existing_constraints(self):
        """Should preserve manually added constraints."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[EffectClause(description="Split and count")],
        )

        # Manually add a constraint
        manual_constraint = PositionConstraint(
            elements=["x", "y"],
            requirement=PositionRequirement.ORDERED,
        )
        ir.constraints.append(manual_constraint)

        # Apply detection
        detect_and_apply_constraints(ir)

        # Manual constraint should still be there
        assert manual_constraint in ir.constraints


class TestHelperMethods:
    """Tests for detector helper methods."""

    def test_extract_value_name_finds_count(self):
        """Should extract 'count' from text."""
        detector = ConstraintDetector()
        name = detector._extract_value_name("count the items", "")
        assert name == "count"

    def test_extract_value_name_finds_index(self):
        """Should extract 'index' from text."""
        detector = ConstraintDetector()
        name = detector._extract_value_name("find the index", "")
        assert name == "index"

    def test_extract_value_name_defaults_to_result(self):
        """Should default to 'result' when nothing found."""
        detector = ConstraintDetector()
        name = detector._extract_value_name("do something", "")
        assert name == "result"

    def test_extract_loop_variable_from_for_each(self):
        """Should extract variable from 'for each X' pattern."""
        detector = ConstraintDetector()
        var = detector._extract_loop_variable("for each item in the list")
        assert var == "item"

    def test_extract_loop_variable_from_iterate_over(self):
        """Should extract variable from 'iterate over X' pattern."""
        detector = ConstraintDetector()
        var = detector._extract_loop_variable("iterate over elements")
        assert var == "elements"

    def test_is_email_validation_detects_email(self):
        """Should detect email-related text."""
        detector = ConstraintDetector()
        assert detector._is_email_validation("validate email address")
        assert detector._is_email_validation("check if @ is present")

    def test_is_parentheses_matching_detects_parens(self):
        """Should detect parentheses-related text."""
        detector = ConstraintDetector()
        assert detector._is_parentheses_matching("check balanced parentheses")
        assert detector._is_parentheses_matching("match opening and closing brackets")
