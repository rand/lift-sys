"""Unit tests for Constraint Validator (Phase 7)."""

from lift_sys.ir.constraint_validator import (
    ConstraintValidator,
    validate_code_against_constraints,
)
from lift_sys.ir.constraints import (
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
)
from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)


class TestReturnConstraintValidation:
    """Tests for validating return constraints."""

    def test_valid_return_with_value(self):
        """Should pass when code returns a value."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count", description="Must return count")],
        )

        code = """
def count_words(text: str) -> int:
    count = len(text.split())
    return count
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0

    def test_violation_when_no_return(self):
        """Should detect violation when no return statement."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def count_words(text: str) -> int:
    count = len(text.split())
    # Missing return!
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect missing return
        assert len(violations) == 1
        assert violations[0].constraint_type == "return_constraint"
        assert "No return statement" in violations[0].description

    def test_violation_when_only_returns_none(self):
        """Should detect violation when all returns are None."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def count_words(text: str) -> int:
    count = len(text.split())
    return None  # Wrong!
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect None return
        assert len(violations) == 1
        assert violations[0].constraint_type == "return_constraint"
        assert "return None" in violations[0].description


class TestLoopConstraintValidation:
    """Tests for validating loop behavior constraints."""

    def test_valid_early_return_pattern(self):
        """Should pass when loop has early return for FIRST_MATCH."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first index"),
            signature=SigClause(
                name="find_index",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="int",
            ),
            constraints=[
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                )
            ],
        )

        code = """
def find_index(lst, value):
    for i, item in enumerate(lst):
        if item == value:
            return i  # Early return - correct!
    return -1
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0

    def test_violation_when_missing_early_return(self):
        """Should detect violation when FIRST_MATCH doesn't have early return."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first index"),
            signature=SigClause(
                name="find_index",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="int",
            ),
            constraints=[
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                )
            ],
        )

        code = """
def find_index(lst, value):
    result = -1
    for i, item in enumerate(lst):
        if item == value:
            result = i  # Accumulates instead of early return - wrong!
    return result
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect missing early return
        assert len(violations) == 1
        assert violations[0].constraint_type == "loop_constraint"
        assert "early return" in violations[0].description.lower()

    def test_valid_accumulate_pattern(self):
        """Should pass when loop accumulates for ALL_MATCHES."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find all indices"),
            signature=SigClause(
                name="find_all_indices",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="list[int]",
            ),
            constraints=[
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.ALL_MATCHES,
                    requirement=LoopRequirement.ACCUMULATE,
                )
            ],
        )

        code = """
def find_all_indices(lst, value):
    indices = []
    for i, item in enumerate(lst):
        if item == value:
            indices.append(i)  # Accumulates - correct!
    return indices
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0

    def test_violation_when_early_return_in_accumulate(self):
        """Should detect violation when ACCUMULATE has early return."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find all indices"),
            signature=SigClause(
                name="find_all_indices",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="list[int]",
            ),
            constraints=[
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.ALL_MATCHES,
                    requirement=LoopRequirement.ACCUMULATE,
                )
            ],
        )

        code = """
def find_all_indices(lst, value):
    for i, item in enumerate(lst):
        if item == value:
            return [i]  # Early return - wrong for ALL_MATCHES!
    return []
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect wrong pattern
        assert len(violations) == 1
        assert violations[0].constraint_type == "loop_constraint"
        assert "accumulation" in violations[0].description.lower()


class TestPositionConstraintValidation:
    """Tests for validating position constraints."""

    def test_valid_not_adjacent_check(self):
        """Should pass when code checks elements are not adjacent."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email"),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            constraints=[
                PositionConstraint(
                    elements=["@", "."],
                    requirement=PositionRequirement.NOT_ADJACENT,
                    min_distance=1,
                )
            ],
        )

        code = """
def is_valid_email(email: str) -> bool:
    at_idx = email.find('@')
    dot_idx = email.find('.')
    if at_idx == -1 or dot_idx == -1:
        return False
    return abs(at_idx - dot_idx) > 1  # Checks not adjacent - correct!
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0

    def test_violation_when_missing_position_check(self):
        """Should detect violation when position check is missing."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Validate email"),
            signature=SigClause(
                name="is_valid_email",
                parameters=[Parameter(name="email", type_hint="str")],
                returns="bool",
            ),
            constraints=[
                PositionConstraint(
                    elements=["@", "."],
                    requirement=PositionRequirement.NOT_ADJACENT,
                    min_distance=1,
                )
            ],
        )

        code = """
def is_valid_email(email: str) -> bool:
    # Only checks presence, not position!
    return '@' in email and '.' in email
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect missing position check
        assert len(violations) == 1
        assert violations[0].constraint_type == "position_constraint"
        assert "not be adjacent" in violations[0].description


class TestMultipleConstraints:
    """Tests for validating multiple constraints together."""

    def test_all_constraints_satisfied(self):
        """Should pass when all constraints are satisfied."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first valid email index"),
            signature=SigClause(
                name="find_first_valid_email",
                parameters=[Parameter(name="emails", type_hint="list[str]")],
                returns="int",
            ),
            constraints=[
                ReturnConstraint(value_name="index"),
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                ),
                PositionConstraint(
                    elements=["@", "."],
                    requirement=PositionRequirement.NOT_ADJACENT,
                    min_distance=1,
                ),
            ],
        )

        code = """
def find_first_valid_email(emails: list[str]) -> int:
    for i, email in enumerate(emails):
        at_idx = email.find('@')
        dot_idx = email.find('.')
        if at_idx != -1 and dot_idx != -1 and abs(at_idx - dot_idx) > 1:
            return i  # Early return with valid email
    return -1
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0

    def test_multiple_violations_detected(self):
        """Should detect all violations when multiple constraints fail."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first valid email index"),
            signature=SigClause(
                name="find_first_valid_email",
                parameters=[Parameter(name="emails", type_hint="list[str]")],
                returns="int",
            ),
            constraints=[
                ReturnConstraint(value_name="index"),
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                ),
            ],
        )

        code = """
def find_first_valid_email(emails: list[str]) -> int:
    result = -1
    for email in emails:
        if '@' in email:
            result = 0  # Accumulates instead of early return
    # Missing return statement!
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect multiple violations
        assert len(violations) >= 2
        violation_types = {v.constraint_type for v in violations}
        assert "return_constraint" in violation_types
        assert "loop_constraint" in violation_types


class TestConvenienceFunction:
    """Tests for the convenience function."""

    def test_returns_valid_and_no_violations(self):
        """Should return (True, []) when code is valid."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def count_words(text: str) -> int:
    return len(text.split())
"""

        is_valid, violations = validate_code_against_constraints(code, ir)

        assert is_valid is True
        assert len(violations) == 0

    def test_returns_invalid_with_violations(self):
        """Should return (False, violations) when code has errors."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def count_words(text: str) -> int:
    count = len(text.split())
    # Missing return!
"""

        is_valid, violations = validate_code_against_constraints(code, ir)

        assert is_valid is False
        assert len(violations) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_syntax_error_in_code(self):
        """Should handle syntax errors gracefully."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def count_words(text: str) -> int
    return len(text.split())  # Missing colon!
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should report syntax error
        assert len(violations) > 0
        assert violations[0].constraint_type == "syntax_error"

    def test_function_not_found(self):
        """Should detect when function is not in generated code."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            constraints=[ReturnConstraint(value_name="count")],
        )

        code = """
def wrong_function_name(text: str) -> int:
    return len(text.split())
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should detect missing function
        assert len(violations) > 0
        assert violations[0].constraint_type == "missing_function"
        assert "count_words" in violations[0].description

    def test_no_constraints(self):
        """Should pass when IR has no constraints."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Simple function"),
            signature=SigClause(
                name="simple_func",
                parameters=[],
                returns="None",
            ),
            constraints=[],  # No constraints
        )

        code = """
def simple_func():
    print("Hello")
"""

        validator = ConstraintValidator()
        violations = validator.validate(code, ir)

        # Should have no violations
        assert len(violations) == 0
