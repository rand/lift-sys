"""Tests for IR comparison and diff engine."""

from lift_sys.ir.differ import (
    CategoryComparison,
    DiffCategory,
    DiffKind,
    DiffSeverity,
    IRComparer,
    IRDiff,
)
from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


class TestIRComparer:
    """Tests for IRComparer."""

    def test_compare_identical_irs(self):
        """Test comparing identical IRs returns no differences."""
        comparer = IRComparer()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        result = comparer.compare(ir, ir)

        assert result.is_identical()
        assert result.overall_similarity == 1.0
        assert len(result.all_diffs()) == 0
        assert not result.has_breaking_changes()

    def test_compare_different_function_names(self):
        """Test detecting function name differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func1", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func2", parameters=[], returns=None),
        )

        result = comparer.compare(ir1, ir2)

        assert not result.is_identical()
        assert result.has_breaking_changes()
        assert len(result.all_diffs()) == 1

        diff = result.all_diffs()[0]
        assert diff.kind == DiffKind.SIGNATURE_NAME
        assert diff.severity == DiffSeverity.ERROR
        assert diff.left_value == "func1"
        assert diff.right_value == "func2"

    def test_compare_different_parameter_count(self):
        """Test detecting parameter count differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns=None,
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("a", "int")],
                returns=None,
            ),
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.PARAMETER_COUNT]
        assert len(diffs) == 1
        assert diffs[0].left_value == 2
        assert diffs[0].right_value == 1
        assert diffs[0].severity == DiffSeverity.ERROR

    def test_compare_different_parameter_types(self):
        """Test detecting parameter type differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "int")],
                returns=None,
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "str")],
                returns=None,
            ),
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.PARAMETER_TYPE]
        assert len(diffs) == 1
        assert diffs[0].left_value == "int"
        assert diffs[0].right_value == "str"
        assert diffs[0].severity == DiffSeverity.WARNING

    def test_compare_different_return_types(self):
        """Test detecting return type differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns="int"),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns="str"),
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.RETURN_TYPE]
        assert len(diffs) == 1
        assert diffs[0].left_value == "int"
        assert diffs[0].right_value == "str"
        assert diffs[0].severity == DiffSeverity.WARNING

    def test_compare_different_intent_summaries(self):
        """Test detecting intent summary differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Add numbers"),
            signature=SigClause(name="func", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Subtract numbers"),
            signature=SigClause(name="func", parameters=[], returns=None),
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.INTENT_SUMMARY]
        assert len(diffs) == 1
        assert diffs[0].severity == DiffSeverity.WARNING
        assert diffs[0].left_value == "Add numbers"
        assert diffs[0].right_value == "Subtract numbers"

    def test_compare_different_assertion_count(self):
        """Test detecting assertion count differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[
                AssertClause(predicate="x > 0"),
                AssertClause(predicate="y > 0"),
            ],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0")],
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.ASSERTION_COUNT]
        assert len(diffs) == 1
        assert diffs[0].left_value == 2
        assert diffs[0].right_value == 1
        assert diffs[0].severity == DiffSeverity.WARNING

    def test_compare_different_assertion_predicates(self):
        """Test detecting assertion predicate differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0")],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x >= 0")],
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.ASSERTION_PREDICATE]
        assert len(diffs) == 1
        assert diffs[0].left_value == "x > 0"
        assert diffs[0].right_value == "x >= 0"

    def test_compare_different_effect_count(self):
        """Test detecting effect count differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            effects=[
                EffectClause(description="Read from file.txt"),
                EffectClause(description="Write to output.txt"),
            ],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            effects=[EffectClause(description="Read from file.txt")],
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.EFFECT_COUNT]
        assert len(diffs) == 1
        assert diffs[0].left_value == 2
        assert diffs[0].right_value == 1

    def test_compare_different_effect_descriptions(self):
        """Test detecting effect description differences."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            effects=[EffectClause(description="Read from file.txt")],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            effects=[EffectClause(description="Write to file.txt")],
        )

        result = comparer.compare(ir1, ir2)

        diffs = [d for d in result.all_diffs() if d.kind == DiffKind.EFFECT_DESCRIPTION]
        assert len(diffs) == 1
        assert diffs[0].left_value == "Read from file.txt"
        assert diffs[0].right_value == "Write to file.txt"

    def test_compare_with_ignore_metadata(self):
        """Test comparison with metadata ignored."""
        comparer = IRComparer(ignore_metadata=True)

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            metadata=Metadata(origin="source1"),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            metadata=Metadata(origin="source2"),
        )

        result = comparer.compare(ir1, ir2)

        # Should have no metadata differences
        assert len(result.metadata_comparison.diffs) == 0
        assert result.metadata_comparison.similarity == 1.0

    def test_compare_with_ignore_descriptions(self):
        """Test comparison with descriptions ignored."""
        comparer = IRComparer(ignore_descriptions=True)

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test", rationale="Reason 1"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0", rationale="Must be positive")],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test", rationale="Reason 2"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0", rationale="Should be positive")],
        )

        result = comparer.compare(ir1, ir2)

        # Should not have rationale differences
        rationale_diffs = [
            d
            for d in result.all_diffs()
            if d.kind in [DiffKind.INTENT_RATIONALE, DiffKind.ASSERTION_RATIONALE]
        ]
        assert len(rationale_diffs) == 0

    def test_compare_case_insensitive(self):
        """Test case-insensitive comparison."""
        comparer = IRComparer(case_sensitive=False)

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test Function"),
            signature=SigClause(name="func", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="test function"),
            signature=SigClause(name="func", parameters=[], returns=None),
        )

        result = comparer.compare(ir1, ir2)

        # Summary should match with case-insensitive comparison
        assert result.intent_comparison.similarity == 1.0

    def test_similarity_scores(self):
        """Test similarity score calculation."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "int")],
                returns="int",
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "str")],  # Different type
                returns="int",
            ),
        )

        result = comparer.compare(ir1, ir2)

        # Signature should have high but not perfect similarity
        assert 0.8 < result.signature_comparison.similarity < 1.0
        assert 0.8 < result.overall_similarity < 1.0

    def test_category_comparison_has_errors(self):
        """Test CategoryComparison.has_errors method."""
        comp = CategoryComparison(
            category=DiffCategory.SIGNATURE,
            diffs=[
                IRDiff(
                    category=DiffCategory.SIGNATURE,
                    kind=DiffKind.SIGNATURE_NAME,
                    path="signature.name",
                    left_value="a",
                    right_value="b",
                    severity=DiffSeverity.ERROR,
                )
            ],
        )

        assert comp.has_errors()

    def test_category_comparison_no_errors_with_warnings(self):
        """Test CategoryComparison with only warnings."""
        comp = CategoryComparison(
            category=DiffCategory.SIGNATURE,
            diffs=[
                IRDiff(
                    category=DiffCategory.SIGNATURE,
                    kind=DiffKind.PARAMETER_TYPE,
                    path="signature.parameters[0].type_hint",
                    left_value="int",
                    right_value="str",
                    severity=DiffSeverity.WARNING,
                )
            ],
        )

        assert not comp.has_errors()
        assert comp.has_diffs()

    def test_comparison_result_all_diffs(self):
        """Test ComparisonResult.all_diffs aggregates all categories."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test 1"),
            signature=SigClause(name="func1", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test 2"),
            signature=SigClause(name="func2", parameters=[], returns=None),
        )

        result = comparer.compare(ir1, ir2)

        all_diffs = result.all_diffs()
        assert len(all_diffs) >= 2  # At least intent and signature diffs

    def test_type_normalization(self):
        """Test that type comparisons normalize whitespace."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "dict[str, int]")],
                returns=None,
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("x", "dict[str,  int]")],  # Extra space
                returns=None,
            ),
        )

        result = comparer.compare(ir1, ir2)

        # Should match after whitespace normalization
        type_diffs = [d for d in result.all_diffs() if d.kind == DiffKind.PARAMETER_TYPE]
        assert len(type_diffs) == 0

    def test_complex_ir_comparison(self):
        """Test comprehensive comparison of complex IRs."""
        comparer = IRComparer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data", rationale="For analysis"),
            signature=SigClause(
                name="process",
                parameters=[
                    Parameter("data", "list[int]", description="Input data"),
                    Parameter("threshold", "int", description="Threshold value"),
                ],
                returns="dict[str, int]",
            ),
            assertions=[
                AssertClause(predicate="threshold > 0", rationale="Must be positive"),
                AssertClause(predicate="len(data) > 0", rationale="Must have data"),
            ],
            effects=[
                EffectClause(description="Read from input.txt"),
                EffectClause(description="Write to output.txt"),
            ],
            metadata=Metadata(origin="test", language="python"),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Process data", rationale="For analysis"),
            signature=SigClause(
                name="process",
                parameters=[
                    Parameter("data", "list[int]", description="Input data"),
                    Parameter("threshold", "float"),  # Different type, no description
                ],
                returns="dict[str, int]",
            ),
            assertions=[
                AssertClause(predicate="threshold > 0", rationale="Must be positive"),
                # Missing second assertion
            ],
            effects=[
                EffectClause(description="Read from input.txt"),
                EffectClause(description="Write to output.txt"),
            ],
            metadata=Metadata(origin="test", language="python"),
        )

        result = comparer.compare(ir1, ir2)

        # Should detect parameter type diff, assertion count diff, parameter description diff
        assert not result.is_identical()
        assert len(result.all_diffs()) >= 3
        assert result.overall_similarity < 1.0

    def test_weighted_similarity_calculation(self):
        """Test that overall similarity uses weighted average."""
        comparer = IRComparer()

        # Create IR with signature differences (highest weight)
        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func1", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func2", parameters=[], returns=None),
        )

        result = comparer.compare(ir1, ir2)

        # Signature has 35% weight, only name differs (1/3 fields)
        # So overall similarity should be around 0.88 (35% * 0.67 + 65% * 1.0)
        assert 0.85 < result.overall_similarity < 0.95
        assert result.signature_comparison.similarity < 1.0
        assert result.has_breaking_changes()  # Name change is ERROR severity
