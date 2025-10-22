"""Sensitivity analysis for robustness testing.

Measures how sensitive IR generation and code generation are to input variations.
Based on TokDrift methodology (arXiv:2510.14972).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from scipy.stats import wilcoxon

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.robustness.equivalence_checker import EquivalenceChecker


@dataclass
class SensitivityResult:
    """Results of sensitivity analysis."""

    total_variants: int
    """Total number of variants tested"""

    equivalent_count: int
    """Number of variants that are equivalent"""

    non_equivalent_count: int
    """Number of variants that are NOT equivalent"""

    sensitivity: float
    """Sensitivity score (0.0 to 1.0, lower is better)"""

    robustness: float
    """Robustness score (0.0 to 1.0, higher is better)"""

    variants_tested: list[Any]
    """List of variants that were tested"""

    equivalence_results: list[bool]
    """Per-variant equivalence results"""

    def __str__(self) -> str:
        return (
            f"SensitivityResult(\n"
            f"  total={self.total_variants}, "
            f"  equivalent={self.equivalent_count}, "
            f"  non_equivalent={self.non_equivalent_count}\n"
            f"  sensitivity={self.sensitivity:.2%}, "
            f"  robustness={self.robustness:.2%}\n"
            f")"
        )


@dataclass
class StatisticalTestResult:
    """Results of statistical significance test."""

    test_name: str
    """Name of statistical test (e.g., 'Wilcoxon signed-rank')"""

    statistic: float
    """Test statistic value"""

    p_value: float
    """p-value (probability of observing result under null hypothesis)"""

    significant: bool
    """Whether result is statistically significant (p < 0.05)"""

    interpretation: str
    """Human-readable interpretation of result"""


class SensitivityAnalyzer:
    """
    Analyzes sensitivity of IR/code generation to input variations.

    Measures robustness by:
    1. Generating variants (paraphrases, IR variants, etc.)
    2. Checking equivalence of outputs
    3. Computing sensitivity metrics
    4. Running statistical tests for significance
    """

    def __init__(
        self,
        equivalence_checker: EquivalenceChecker | None = None,
        normalize_naming: bool = True,
    ):
        """
        Initialize sensitivity analyzer.

        Args:
            equivalence_checker: Checker for IR/code equivalence.
                If None, creates default checker.
            normalize_naming: Whether to normalize naming in IR comparison
        """
        self.checker = equivalence_checker or EquivalenceChecker(normalize_naming=normalize_naming)

    def measure_ir_sensitivity(
        self,
        prompts: list[str],
        generate_ir: Callable[[str], IntermediateRepresentation],
    ) -> SensitivityResult:
        """
        Measure IR generation sensitivity to prompt variations.

        Args:
            prompts: List of prompt variants (original + paraphrases)
            generate_ir: Function that generates IR from a prompt

        Returns:
            Sensitivity analysis result

        Raises:
            ValueError: If prompts list is empty or has only one item
        """
        if len(prompts) < 2:
            raise ValueError("Need at least 2 prompts (original + 1 variant)")

        # Generate IRs from all prompts
        irs = []
        for prompt in prompts:
            try:
                ir = generate_ir(prompt)
                irs.append(ir)
            except Exception as e:
                # If IR generation fails, treat as non-equivalent
                print(f"Warning: IR generation failed for prompt: {e}")
                irs.append(None)

        # Compare all variants to the original (first IR)
        original_ir = irs[0]
        if original_ir is None:
            raise ValueError("Original prompt failed to generate IR")

        equivalence_results = []
        for ir in irs[1:]:
            if ir is None:
                equivalence_results.append(False)
            else:
                is_equiv = self.checker.ir_equivalent(original_ir, ir)
                equivalence_results.append(is_equiv)

        # Compute metrics
        equivalent_count = sum(equivalence_results)
        non_equivalent_count = len(equivalence_results) - equivalent_count
        total_variants = len(equivalence_results)

        sensitivity = non_equivalent_count / total_variants if total_variants > 0 else 0.0
        robustness = 1.0 - sensitivity

        return SensitivityResult(
            total_variants=total_variants,
            equivalent_count=equivalent_count,
            non_equivalent_count=non_equivalent_count,
            sensitivity=sensitivity,
            robustness=robustness,
            variants_tested=irs[1:],
            equivalence_results=equivalence_results,
        )

    def measure_code_sensitivity(
        self,
        ir_variants: list[IntermediateRepresentation],
        generate_code: Callable[[IntermediateRepresentation], str],
        test_inputs: list[dict],
        timeout_seconds: int = 5,
    ) -> SensitivityResult:
        """
        Measure code generation sensitivity to IR variations.

        Args:
            ir_variants: List of IR variants (original + variants)
            generate_code: Function that generates code from IR
            test_inputs: Test inputs for code execution
            timeout_seconds: Timeout for code execution

        Returns:
            Sensitivity analysis result

        Raises:
            ValueError: If ir_variants list is empty or has only one item
        """
        if len(ir_variants) < 2:
            raise ValueError("Need at least 2 IR variants (original + 1 variant)")

        # Generate code from all IR variants
        codes = []
        for ir in ir_variants:
            try:
                code = generate_code(ir)
                codes.append(code)
            except Exception as e:
                print(f"Warning: Code generation failed for IR: {e}")
                codes.append(None)

        # Compare all variant codes to the original
        original_code = codes[0]
        if original_code is None:
            raise ValueError("Original IR failed to generate code")

        equivalence_results = []
        for code in codes[1:]:
            if code is None:
                equivalence_results.append(False)
            else:
                try:
                    is_equiv = self.checker.code_equivalent(
                        original_code, code, test_inputs, timeout_seconds
                    )
                    equivalence_results.append(is_equiv)
                except Exception as e:
                    print(f"Warning: Code equivalence check failed: {e}")
                    equivalence_results.append(False)

        # Compute metrics
        equivalent_count = sum(equivalence_results)
        non_equivalent_count = len(equivalence_results) - equivalent_count
        total_variants = len(equivalence_results)

        sensitivity = non_equivalent_count / total_variants if total_variants > 0 else 0.0
        robustness = 1.0 - sensitivity

        return SensitivityResult(
            total_variants=total_variants,
            equivalent_count=equivalent_count,
            non_equivalent_count=non_equivalent_count,
            sensitivity=sensitivity,
            robustness=robustness,
            variants_tested=codes[1:],
            equivalence_results=equivalence_results,
        )

    def wilcoxon_test(
        self,
        original_scores: list[float],
        variant_scores: list[float],
        alternative: str = "two-sided",
    ) -> StatisticalTestResult:
        """
        Run Wilcoxon signed-rank test for statistical significance.

        Tests whether differences between original and variant scores
        are statistically significant.

        Args:
            original_scores: Accuracy/quality scores for original
            variant_scores: Accuracy/quality scores for variants
            alternative: Test type ('two-sided', 'less', 'greater')

        Returns:
            Statistical test result

        Raises:
            ValueError: If score lists have different lengths or are empty
        """
        if len(original_scores) != len(variant_scores):
            raise ValueError("Score lists must have same length")

        if len(original_scores) < 3:
            raise ValueError("Need at least 3 samples for Wilcoxon test")

        # Compute differences
        differences = [o - v for o, v in zip(original_scores, variant_scores, strict=False)]

        # Check if all differences are zero
        if all(d == 0 for d in differences):
            return StatisticalTestResult(
                test_name="Wilcoxon signed-rank",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation="No differences detected (all variants identical)",
            )

        # Run Wilcoxon signed-rank test
        try:
            statistic, p_value = wilcoxon(differences, alternative=alternative)
        except ValueError as e:
            # Handle case where all values are the same
            return StatisticalTestResult(
                test_name="Wilcoxon signed-rank",
                statistic=0.0,
                p_value=1.0,
                significant=False,
                interpretation=f"Test could not be performed: {e}",
            )

        # Interpret results
        significant = p_value < 0.05
        if significant:
            if alternative == "two-sided":
                interpretation = (
                    f"Significant difference detected (p={p_value:.4f}). "
                    "Variants perform differently from original."
                )
            elif alternative == "less":
                interpretation = f"Variants perform significantly worse (p={p_value:.4f})"
            else:  # greater
                interpretation = f"Variants perform significantly better (p={p_value:.4f})"
        else:
            interpretation = (
                f"No significant difference (p={p_value:.4f}). Performance is robust to variations."
            )

        return StatisticalTestResult(
            test_name="Wilcoxon signed-rank",
            statistic=float(statistic),
            p_value=float(p_value),
            significant=significant,
            interpretation=interpretation,
        )

    def compute_robustness_score(self, sensitivity_results: list[SensitivityResult]) -> float:
        """
        Compute overall robustness score from multiple sensitivity results.

        Args:
            sensitivity_results: List of sensitivity analysis results

        Returns:
            Overall robustness score (0.0 to 1.0, higher is better)
        """
        if not sensitivity_results:
            return 0.0

        # Average robustness across all results
        total_robustness = sum(r.robustness for r in sensitivity_results)
        return total_robustness / len(sensitivity_results)

    def compare_sensitivity(
        self, result1: SensitivityResult, result2: SensitivityResult
    ) -> dict[str, float]:
        """
        Compare two sensitivity results.

        Args:
            result1: First sensitivity result
            result2: Second sensitivity result

        Returns:
            Dictionary with comparison metrics
        """
        return {
            "sensitivity_diff": result2.sensitivity - result1.sensitivity,
            "robustness_diff": result2.robustness - result1.robustness,
            "sensitivity_change_pct": (
                (result2.sensitivity - result1.sensitivity) / result1.sensitivity * 100
                if result1.sensitivity > 0
                else 0.0
            ),
            "robustness_change_pct": (
                (result2.robustness - result1.robustness) / result1.robustness * 100
                if result1.robustness > 0
                else 0.0
            ),
        }
