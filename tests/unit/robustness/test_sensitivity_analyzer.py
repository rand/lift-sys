"""Tests for SensitivityAnalyzer."""

import pytest

from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from lift_sys.robustness.equivalence_checker import EquivalenceChecker
from lift_sys.robustness.sensitivity_analyzer import SensitivityAnalyzer


class TestSensitivityAnalyzer:
    """Test SensitivityAnalyzer functionality."""

    def test_initialization(self):
        """Test analyzer initialization."""
        analyzer = SensitivityAnalyzer()
        assert analyzer.checker is not None
        assert isinstance(analyzer.checker, EquivalenceChecker)

    def test_initialization_with_custom_checker(self):
        """Test initialization with custom equivalence checker."""
        checker = EquivalenceChecker(normalize_naming=False)
        analyzer = SensitivityAnalyzer(equivalence_checker=checker)
        assert analyzer.checker is checker

    def test_measure_ir_sensitivity_all_equivalent(self):
        """Test IR sensitivity when all variants produce equivalent IRs."""

        # Create a generator that always returns same IR
        def generate_ir(prompt: str) -> IntermediateRepresentation:
            return IntermediateRepresentation(
                intent=IntentClause(summary="Test"),
                signature=SigClause(name="test", parameters=[], returns="None"),
                effects=[],
                assertions=[],
            )

        prompts = [
            "Create a test function",
            "Make a test function",
            "Implement a test function",
        ]

        analyzer = SensitivityAnalyzer()
        result = analyzer.measure_ir_sensitivity(prompts, generate_ir)

        assert result.total_variants == 2  # 2 variants (excluding original)
        assert result.equivalent_count == 2
        assert result.non_equivalent_count == 0
        assert result.sensitivity == 0.0
        assert result.robustness == 1.0

    def test_measure_ir_sensitivity_none_equivalent(self):
        """Test IR sensitivity when no variants are equivalent."""
        counter = [0]

        def generate_ir(prompt: str) -> IntermediateRepresentation:
            counter[0] += 1
            return IntermediateRepresentation(
                intent=IntentClause(summary=f"Test {counter[0]}"),  # Different each time
                signature=SigClause(name=f"test_{counter[0]}", parameters=[], returns="None"),
                effects=[],
                assertions=[],
            )

        prompts = [
            "Create a test function",
            "Make a test function",
            "Implement a test function",
        ]

        analyzer = SensitivityAnalyzer()
        result = analyzer.measure_ir_sensitivity(prompts, generate_ir)

        assert result.total_variants == 2
        assert result.equivalent_count == 0
        assert result.non_equivalent_count == 2
        assert result.sensitivity == 1.0
        assert result.robustness == 0.0

    def test_measure_ir_sensitivity_partial(self):
        """Test IR sensitivity with partial equivalence."""
        counter = [0]

        def generate_ir(prompt: str) -> IntermediateRepresentation:
            counter[0] += 1
            # First two are same, third is different
            if counter[0] <= 2:
                name = "test"
            else:
                name = "different_test"

            return IntermediateRepresentation(
                intent=IntentClause(summary="Test"),
                signature=SigClause(name=name, parameters=[], returns="None"),
                effects=[],
                assertions=[],
            )

        prompts = [
            "Create a test function",
            "Make a test function",
            "Implement a test function",
        ]

        analyzer = SensitivityAnalyzer(normalize_naming=False)  # Strict naming
        result = analyzer.measure_ir_sensitivity(prompts, generate_ir)

        assert result.total_variants == 2
        assert result.non_equivalent_count == 1
        assert result.equivalent_count == 1
        assert result.sensitivity == 0.5
        assert result.robustness == 0.5

    def test_measure_ir_sensitivity_too_few_prompts(self):
        """Test error when too few prompts provided."""

        def generate_ir(prompt: str) -> IntermediateRepresentation:
            return IntermediateRepresentation(
                intent=IntentClause(summary="Test"),
                signature=SigClause(name="test", parameters=[], returns="None"),
                effects=[],
                assertions=[],
            )

        analyzer = SensitivityAnalyzer()

        with pytest.raises(ValueError, match="at least 2 prompts"):
            analyzer.measure_ir_sensitivity(["single prompt"], generate_ir)

        with pytest.raises(ValueError, match="at least 2 prompts"):
            analyzer.measure_ir_sensitivity([], generate_ir)

    def test_measure_code_sensitivity_all_equivalent(self):
        """Test code sensitivity when all variants produce equivalent code."""
        ir_variants = [
            IntermediateRepresentation(
                intent=IntentClause(summary="Sort"),
                signature=SigClause(
                    name=name, parameters=[Parameter(name="nums", type_hint="list")], returns="list"
                ),
                effects=[],
                assertions=[],
            )
            for name in ["sort", "sort_function", "do_sort"]
        ]

        def generate_code(ir: IntermediateRepresentation) -> str:
            # All generate functionally equivalent code
            return f"""
def {ir.signature.name}(nums):
    return sorted(nums)
"""

        test_inputs = [{"nums": [3, 1, 4, 1, 5]}]

        analyzer = SensitivityAnalyzer()
        result = analyzer.measure_code_sensitivity(
            ir_variants, generate_code, test_inputs, timeout_seconds=5
        )

        assert result.total_variants == 2
        assert result.equivalent_count == 2
        assert result.non_equivalent_count == 0
        assert result.sensitivity == 0.0
        assert result.robustness == 1.0

    def test_measure_code_sensitivity_too_few_variants(self):
        """Test error when too few IR variants provided."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="None"),
            effects=[],
            assertions=[],
        )

        def generate_code(ir: IntermediateRepresentation) -> str:
            return "def test(): pass"

        analyzer = SensitivityAnalyzer()

        with pytest.raises(ValueError, match="at least 2 IR variants"):
            analyzer.measure_code_sensitivity([ir], generate_code, [], timeout_seconds=5)

    def test_wilcoxon_test_significant_difference(self):
        """Test Wilcoxon test with significant differences."""
        original_scores = [0.9, 0.85, 0.88, 0.92, 0.87]
        variant_scores = [0.7, 0.65, 0.68, 0.72, 0.67]  # Clearly worse

        analyzer = SensitivityAnalyzer()
        result = analyzer.wilcoxon_test(original_scores, variant_scores)

        assert result.test_name == "Wilcoxon signed-rank"
        assert result.p_value < 0.05
        assert result.significant is True
        assert "Significant difference" in result.interpretation

    def test_wilcoxon_test_no_difference(self):
        """Test Wilcoxon test when no differences exist."""
        scores = [0.85, 0.88, 0.90, 0.87, 0.89]

        analyzer = SensitivityAnalyzer()
        result = analyzer.wilcoxon_test(scores, scores)  # Same scores

        assert result.p_value == 1.0
        assert result.significant is False
        assert (
            "No differences" in result.interpretation
            or "could not be performed" in result.interpretation
        )

    def test_wilcoxon_test_too_few_samples(self):
        """Test Wilcoxon test error with too few samples."""
        original_scores = [0.9, 0.85]
        variant_scores = [0.8, 0.75]

        analyzer = SensitivityAnalyzer()

        with pytest.raises(ValueError, match="at least 3 samples"):
            analyzer.wilcoxon_test(original_scores, variant_scores)

    def test_wilcoxon_test_mismatched_lengths(self):
        """Test Wilcoxon test error with mismatched score lengths."""
        original_scores = [0.9, 0.85, 0.88]
        variant_scores = [0.8, 0.75]  # Different length

        analyzer = SensitivityAnalyzer()

        with pytest.raises(ValueError, match="same length"):
            analyzer.wilcoxon_test(original_scores, variant_scores)

    def test_compute_robustness_score(self):
        """Test computation of overall robustness score."""
        from lift_sys.robustness.sensitivity_analyzer import SensitivityResult

        results = [
            SensitivityResult(
                total_variants=10,
                equivalent_count=9,
                non_equivalent_count=1,
                sensitivity=0.1,
                robustness=0.9,
                variants_tested=[],
                equivalence_results=[],
            ),
            SensitivityResult(
                total_variants=10,
                equivalent_count=8,
                non_equivalent_count=2,
                sensitivity=0.2,
                robustness=0.8,
                variants_tested=[],
                equivalence_results=[],
            ),
        ]

        analyzer = SensitivityAnalyzer()
        overall_robustness = analyzer.compute_robustness_score(results)

        assert overall_robustness == 0.85  # (0.9 + 0.8) / 2

    def test_compute_robustness_score_empty(self):
        """Test robustness score computation with empty list."""
        analyzer = SensitivityAnalyzer()
        overall_robustness = analyzer.compute_robustness_score([])
        assert overall_robustness == 0.0

    def test_compare_sensitivity(self):
        """Test comparison of two sensitivity results."""
        from lift_sys.robustness.sensitivity_analyzer import SensitivityResult

        result1 = SensitivityResult(
            total_variants=10,
            equivalent_count=8,
            non_equivalent_count=2,
            sensitivity=0.2,
            robustness=0.8,
            variants_tested=[],
            equivalence_results=[],
        )

        result2 = SensitivityResult(
            total_variants=10,
            equivalent_count=9,
            non_equivalent_count=1,
            sensitivity=0.1,
            robustness=0.9,
            variants_tested=[],
            equivalence_results=[],
        )

        analyzer = SensitivityAnalyzer()
        comparison = analyzer.compare_sensitivity(result1, result2)

        assert comparison["sensitivity_diff"] == -0.1  # Improved (lower)
        assert comparison["robustness_diff"] == 0.1  # Improved (higher)
        assert comparison["sensitivity_change_pct"] == -50.0  # 50% reduction
        assert comparison["robustness_change_pct"] == 12.5  # 12.5% increase

    def test_sensitivity_result_str(self):
        """Test string representation of SensitivityResult."""
        from lift_sys.robustness.sensitivity_analyzer import SensitivityResult

        result = SensitivityResult(
            total_variants=10,
            equivalent_count=9,
            non_equivalent_count=1,
            sensitivity=0.1,
            robustness=0.9,
            variants_tested=[],
            equivalence_results=[],
        )

        result_str = str(result)
        assert "total=10" in result_str
        assert "equivalent=9" in result_str
        assert "non_equivalent=1" in result_str
        assert "sensitivity=10.00%" in result_str
        assert "robustness=90.00%" in result_str
