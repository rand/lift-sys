"""Tests for Semantic Validator - Step 2 of IR Interpreter."""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation.effect_analyzer import EffectChainAnalyzer
from lift_sys.validation.semantic_validator import SemanticValidator


class TestSemanticValidator:
    """Test semantic validation of IR."""

    def test_return_consistency_matching_types(self):
        """Test validation passes when return types match."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words", rationale=None),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split text by spaces into words"),
                EffectClause(description="Count the elements"),
                EffectClause(description="Return the count"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should pass - return type matches
        assert result.passed, f"Should pass validation: {result}"
        assert len(result.errors) == 0

    def test_return_consistency_type_mismatch(self):
        """Test detection of return type mismatch."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Get words", rationale=None),
            signature=SigClause(
                name="get_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="list[str]",  # Signature says list
            ),
            effects=[
                EffectClause(description="Split text by spaces"),
                EffectClause(description="Count the words"),
                EffectClause(description="Return the count"),  # But returns count (int)
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should warn about type mismatch
        assert any(issue.category == "type_mismatch" for issue in result.warnings)

    def test_parameter_usage_all_used(self):
        """Test that all parameters being used is detected correctly."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find value", rationale=None),
            signature=SigClause(
                name="find_value",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="bool",
            ),
            effects=[
                EffectClause(description="Iterate through items list"),
                EffectClause(description="Check if item equals target"),
                EffectClause(description="Return True if found, False otherwise"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should not warn about unused parameters
        unused_warnings = [
            issue for issue in result.warnings if issue.category == "unused_parameter"
        ]
        assert len(unused_warnings) == 0, (
            f"Should not warn about unused parameters: {unused_warnings}"
        )

    def test_parameter_usage_unused_parameter(self):
        """Test detection of unused parameter."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data", rationale=None),
            signature=SigClause(
                name="process",
                parameters=[
                    Parameter(name="data", type_hint="str"),
                    Parameter(name="unused_param", type_hint="int"),  # Not used
                ],
                returns="str",
            ),
            effects=[
                EffectClause(description="Convert data to uppercase"),
                EffectClause(description="Return the result"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should warn about unused parameter
        assert any(issue.category == "unused_parameter" for issue in result.warnings), (
            f"Should detect unused parameter: {result.warnings}"
        )

    def test_assertion_coverage_valid(self):
        """Test that valid assertion coverage is detected."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words", rationale=None),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split text by spaces into words"),
                EffectClause(description="Count the elements"),
                EffectClause(description="Return the count"),
            ],
            assertions=[
                AssertClause(
                    predicate="count is greater than or equal to 0",
                    rationale="Word count cannot be negative",
                ),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should pass - assertion references 'count' which exists
        assert result.passed, f"Should pass validation: {result}"

    def test_type_compatibility(self):
        """Test type compatibility checking."""
        validator = SemanticValidator()

        # Exact matches
        assert validator._types_compatible("int", "int")
        assert validator._types_compatible("str", "str")

        # Any compatibility
        assert validator._types_compatible("Any", "int")
        assert validator._types_compatible("str", "Any")

        # List compatibility
        assert validator._types_compatible("list[str]", "list[Any]")
        assert validator._types_compatible("list", "list[int]")

        # Numeric compatibility
        assert validator._types_compatible("float", "int")
        assert validator._types_compatible("number", "int")

        # Incompatible types
        assert not validator._types_compatible("int", "str")
        assert not validator._types_compatible("list", "dict")

    def test_validation_result_string(self):
        """Test ValidationResult string representation."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test", rationale=None),
            signature=SigClause(
                name="test_func",
                parameters=[],
                returns="int",
            ),
            effects=[
                EffectClause(description="Calculate result"),
                # Missing return effect
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should have errors (missing return)
        assert not result.passed
        assert len(result.errors) > 0

        # String should indicate failure
        result_str = str(result)
        assert "FAILED" in result_str or "❌" in result_str

    def test_full_validation_count_words_missing_return(self):
        """Test full validation on count_words with missing return."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words in string", rationale=None),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str", description="Input string")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split input string by spaces into words list"),
                EffectClause(description="Iterate through words list"),
                EffectClause(description="Count the number of elements"),
                # Missing: "Return the count"
            ],
        )

        # Run full validation
        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should fail validation
        assert not result.passed, "Should fail due to missing return"
        assert len(result.errors) > 0

        # Should have missing_return error
        assert any(issue.category == "missing_return" for issue in result.errors), (
            f"Should detect missing return: {result.errors}"
        )

        print(f"\n{result}")

    def test_full_validation_correct_ir(self):
        """Test full validation on correct IR."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words in string", rationale=None),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str", description="Input string")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split input string by spaces into words list"),
                EffectClause(description="Count the number of elements"),
                EffectClause(description="Return the count"),  # Explicit return
            ],
            assertions=[
                AssertClause(
                    predicate="count is greater than or equal to 0",
                    rationale="Word count cannot be negative",
                ),
            ],
        )

        # Run full validation
        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        validator = SemanticValidator()
        result = validator.validate(ir, trace)

        # Should pass validation
        assert result.passed, f"Should pass validation: {result}"
        assert len(result.errors) == 0

        print(f"\n{result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
