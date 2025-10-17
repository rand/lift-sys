"""Tests for Effect Chain Analyzer - Step 1 of IR Interpreter."""

import pytest

from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.validation.effect_analyzer import EffectChainAnalyzer


class TestEffectChainAnalyzer:
    """Test symbolic execution of IR effect chains."""

    def test_count_words_missing_return(self):
        """Test detection of missing return in count_words IR."""
        # This is the failing test case - effects count but don't return
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Count the number of words in a string",
                rationale=None,
            ),
            signature=SigClause(
                name="count_words",
                parameters=[
                    Parameter(name="text", type_hint="str", description="Input string"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split input string by spaces into words list"),
                EffectClause(description="Iterate through words list"),
                EffectClause(description="Count the number of elements"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # Should detect missing return
        assert trace.has_errors(), "Should detect missing return"
        assert any(issue.category == "missing_return" for issue in trace.issues), (
            "Should flag missing_return"
        )

        # Should produce 'count' value
        assert "count" in trace.values, "Should produce 'count' value"
        assert trace.values["count"].type_hint == "int"

        # Should not have return value set
        assert trace.return_value is None, "Should not have return value (that's the bug!)"

        print(f"\n{trace}")
        print("\nIssues detected:")
        for issue in trace.issues:
            print(f"  {issue}")

    def test_count_words_with_return(self):
        """Test that explicit return is detected correctly."""
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
                EffectClause(description="Return the count"),  # Explicit return!
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # Should NOT have errors
        assert not trace.has_errors(), f"Should not have errors, got: {trace.issues}"

        # Should have return value set
        assert trace.return_value is not None, "Should have return value"
        assert trace.return_value.name == "count"

        print(f"\n{trace}")

    def test_find_index_enumerate_pattern(self):
        """Test detection of enumerate loop (potential off-by-one)."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first index of value", rationale=None),
            signature=SigClause(
                name="find_index",
                parameters=[
                    Parameter(name="items", type_hint="list[int]"),
                    Parameter(name="target", type_hint="int"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Use enumerate to iterate through list with indices"),
                EffectClause(description="Check if item equals target"),
                EffectClause(description="Return the index when found"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # Should detect operations
        assert "iterate" in trace.operations or "enumerate" in str(trace).lower()

        # Should have parameters
        assert "items" in trace.values
        assert "target" in trace.values

        print(f"\n{trace}")

    def test_parameter_initialization(self):
        """Test that parameters are initialized as symbolic values."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function", rationale=None),
            signature=SigClause(
                name="test_func",
                parameters=[
                    Parameter(name="x", type_hint="int"),
                    Parameter(name="y", type_hint="str"),
                    Parameter(name="z", type_hint="list[Any]"),
                ],
                returns="bool",
            ),
            effects=[],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # All parameters should be in trace
        assert "x" in trace.values
        assert "y" in trace.values
        assert "z" in trace.values

        # Check types
        assert trace.values["x"].type_hint == "int"
        assert trace.values["y"].type_hint == "str"
        assert trace.values["z"].type_hint == "list[Any]"

        # Check source
        assert all(v.source == "parameter" for v in trace.values.values())

    def test_type_inference(self):
        """Test type inference from effect descriptions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test types", rationale=None),
            signature=SigClause(name="test", parameters=[], returns="Any"),
            effects=[
                EffectClause(description="Split string into words list"),
                EffectClause(description="Count the integers"),
                EffectClause(description="Check if valid returns boolean"),
                EffectClause(description="Calculate the decimal result"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # Check inferred types
        if "words" in trace.values:
            assert "list" in trace.values["words"].type_hint

        if "count" in trace.values:
            assert trace.values["count"].type_hint == "int"

        # Boolean inference
        computed = [v for v in trace.values.values() if v.source == "computed"]
        has_bool = any("bool" in v.type_hint for v in computed)

        print(f"\n{trace}")
        print("\nComputed values:")
        for v in computed:
            print(f"  {v}")

    def test_operations_detection(self):
        """Test detection of operations from effect descriptions."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data", rationale=None),
            signature=SigClause(name="process", parameters=[], returns="Any"),
            effects=[
                EffectClause(description="Split the input"),
                EffectClause(description="Filter the results"),
                EffectClause(description="Map transformation"),
                EffectClause(description="Iterate through items"),
                EffectClause(description="Calculate total"),
            ],
        )

        analyzer = EffectChainAnalyzer()
        trace = analyzer.analyze(ir)

        # Check operations were detected
        assert "split" in trace.operations
        assert "filter" in trace.operations or "iterate" in trace.operations
        assert "calculate" in trace.operations or "count" in trace.operations

        print(f"\nOperations: {trace.operations}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
