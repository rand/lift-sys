"""Statistical validation framework for optimization experiments (H17).

This module provides validation that DSPy optimization actually improves
pipeline performance, using paired t-tests and effect size measurements.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import dspy
import numpy as np
from scipy.stats import pearsonr, ttest_rel

from lift_sys.optimization.optimizer import DSPyOptimizer

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of optimization validation experiment.

    Attributes:
        p_value: Statistical significance (target < 0.05)
        effect_size: Cohen's d effect size
        baseline_mean: Mean baseline score
        optimized_mean: Mean optimized score
        baseline_std: Standard deviation of baseline scores
        optimized_std: Standard deviation of optimized scores
        improvement_pct: Percentage improvement
        significant: Whether improvement is statistically significant (p < 0.05)
        practical: Whether improvement is practically significant (Cohen's d > threshold)
        recommendation: Deployment recommendation
        baseline_scores: Individual baseline scores
        optimized_scores: Individual optimized scores
        n_examples: Number of test examples
    """

    p_value: float
    effect_size: float
    baseline_mean: float
    optimized_mean: float
    baseline_std: float
    optimized_std: float
    improvement_pct: float
    significant: bool
    practical: bool
    recommendation: str
    baseline_scores: list[float]
    optimized_scores: list[float]
    n_examples: int


class OptimizationValidator:
    """Validates that optimization improves pipeline performance.

    Uses paired t-test and Cohen's d to assess statistical and practical
    significance of optimization improvements per H17 requirements.

    Integrates with:
    - H8 (OptimizationAPI): Uses DSPyOptimizer for optimization
    - H10 (OptimizationMetrics): Uses metrics like ir_quality, code_quality

    Example:
        >>> from lift_sys.optimization.metrics import ir_quality
        >>> validator = OptimizationValidator(metric=ir_quality)
        >>> result = validator.validate(
        ...     pipeline=my_pipeline,
        ...     optimizer=DSPyOptimizer(),
        ...     train_examples=train_set,
        ...     test_examples=test_set,
        ... )
        >>> print(f"Improvement: {result.improvement_pct:.1f}% (p={result.p_value:.4f})")
        >>> print(f"Recommendation: {result.recommendation}")
    """

    def __init__(
        self,
        metric: Callable,
        significance_level: float = 0.05,
        min_effect_size: float = 0.2,
    ):
        """Initialize validator.

        Args:
            metric: Metric function from H10 (ir_quality, code_quality, etc.)
                   Signature: (example, prediction) -> float
            significance_level: p-value threshold (default 0.05)
            min_effect_size: Minimum Cohen's d for practical significance (default 0.2)
        """
        self.metric = metric
        self.significance_level = significance_level
        self.min_effect_size = min_effect_size

        logger.info(
            f"Initialized OptimizationValidator with significance_level={significance_level}, "
            f"min_effect_size={min_effect_size}"
        )

    def validate(
        self,
        pipeline: dspy.Module,
        optimizer: DSPyOptimizer,
        train_examples: list[dspy.Example],
        test_examples: list[dspy.Example],
    ) -> ValidationResult:
        """Run validation experiment.

        Steps:
        1. Evaluate baseline pipeline on test set
        2. Optimize pipeline using train set
        3. Evaluate optimized pipeline on test set
        4. Run paired t-test
        5. Calculate Cohen's d
        6. Generate recommendation

        Args:
            pipeline: Baseline pipeline to optimize
            optimizer: Optimizer to use (DSPyOptimizer or RouteAwareOptimizer)
            train_examples: Examples for optimization (minimum 20 per H10 constraint)
            test_examples: Held-out examples for validation (minimum 50 per acceptance criteria)

        Returns:
            ValidationResult with statistical analysis

        Raises:
            ValueError: If insufficient examples or optimization fails
        """
        # Validate inputs
        if len(train_examples) < 20:
            raise ValueError(f"Insufficient training examples: {len(train_examples)} < 20")
        if len(test_examples) < 50:
            raise ValueError(f"Insufficient test examples: {len(test_examples)} < 50")

        logger.info(
            f"Starting validation: {len(train_examples)} train, {len(test_examples)} test examples"
        )

        # Step 1: Evaluate baseline
        logger.info("Evaluating baseline pipeline...")
        baseline_scores = self._evaluate_pipeline(pipeline, test_examples)
        baseline_mean = np.mean(baseline_scores)
        baseline_std = np.std(baseline_scores, ddof=1)

        logger.info(f"Baseline: mean={baseline_mean:.3f}, std={baseline_std:.3f}")

        # Step 2: Optimize pipeline
        logger.info("Running optimization...")
        try:
            optimization_result = optimizer.optimize(
                pipeline=pipeline,
                examples=train_examples,
            )
            optimized_pipeline = optimization_result.optimized_pipeline
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise ValueError(f"Optimization failed: {e}") from e

        logger.info("Optimization complete")

        # Step 3: Evaluate optimized pipeline
        logger.info("Evaluating optimized pipeline...")
        optimized_scores = self._evaluate_pipeline(optimized_pipeline, test_examples)
        optimized_mean = np.mean(optimized_scores)
        optimized_std = np.std(optimized_scores, ddof=1)

        logger.info(f"Optimized: mean={optimized_mean:.3f}, std={optimized_std:.3f}")

        # Step 4: Run paired t-test
        statistic, p_value = ttest_rel(baseline_scores, optimized_scores, alternative="less")
        significant = p_value < self.significance_level

        logger.info(f"Paired t-test: statistic={statistic:.3f}, p={p_value:.4f}")

        # Step 5: Calculate Cohen's d
        effect_size = cohens_d(baseline_scores, optimized_scores)
        practical = effect_size >= self.min_effect_size

        logger.info(f"Effect size (Cohen's d): {effect_size:.3f}")

        # Step 6: Calculate improvement percentage
        if baseline_mean > 0:
            improvement_pct = ((optimized_mean - baseline_mean) / baseline_mean) * 100
        else:
            improvement_pct = 0.0

        # Step 7: Generate recommendation
        recommendation = self._generate_recommendation(
            significant=significant,
            practical=practical,
            improvement_pct=improvement_pct,
            p_value=p_value,
            effect_size=effect_size,
        )

        logger.info(f"Recommendation: {recommendation}")

        return ValidationResult(
            p_value=p_value,
            effect_size=effect_size,
            baseline_mean=baseline_mean,
            optimized_mean=optimized_mean,
            baseline_std=baseline_std,
            optimized_std=optimized_std,
            improvement_pct=improvement_pct,
            significant=significant,
            practical=practical,
            recommendation=recommendation,
            baseline_scores=baseline_scores,
            optimized_scores=optimized_scores,
            n_examples=len(test_examples),
        )

    def _evaluate_pipeline(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
    ) -> list[float]:
        """Evaluate pipeline on examples using configured metric.

        Args:
            pipeline: Pipeline to evaluate
            examples: Examples to evaluate on

        Returns:
            List of scores (one per example)
        """
        scores = []
        for example in examples:
            try:
                # Run pipeline
                prediction = pipeline(**example.inputs())

                # Compute metric score
                score = self.metric(example, prediction)
                scores.append(score)

            except Exception as e:
                logger.warning(f"Evaluation failed for example: {e}")
                # Assign zero score for failures
                scores.append(0.0)

        return scores

    def _generate_recommendation(
        self,
        significant: bool,
        practical: bool,
        improvement_pct: float,
        p_value: float,
        effect_size: float,
    ) -> str:
        """Generate deployment recommendation based on validation results.

        Args:
            significant: Whether improvement is statistically significant
            practical: Whether improvement is practically significant
            improvement_pct: Percentage improvement
            p_value: Statistical significance p-value
            effect_size: Cohen's d effect size

        Returns:
            Human-readable recommendation
        """
        if significant and practical and improvement_pct > 5:
            return (
                f"DEPLOY: Statistically significant (p={p_value:.4f}) and practically "
                f"meaningful (d={effect_size:.2f}) improvement of {improvement_pct:.1f}%."
            )
        elif significant and improvement_pct > 5:
            return (
                f"CONSIDER: Statistically significant (p={p_value:.4f}) improvement of "
                f"{improvement_pct:.1f}%, but small effect size (d={effect_size:.2f})."
            )
        elif practical and improvement_pct > 5:
            return (
                f"INVESTIGATE: Large effect size (d={effect_size:.2f}) but not statistically "
                f"significant (p={p_value:.4f}). May need more data."
            )
        elif improvement_pct > 0:
            return (
                f"NO DEPLOY: Improvement not significant (p={p_value:.4f}) or meaningful "
                f"(d={effect_size:.2f}). Improvement: {improvement_pct:.1f}%."
            )
        else:
            return (
                f"NO DEPLOY: No improvement detected. Change: {improvement_pct:.1f}%. "
                f"Optimization may have degraded performance."
            )


def cohens_d(baseline_scores: list[float], optimized_scores: list[float]) -> float:
    """Calculate Cohen's d effect size.

    Cohen's d quantifies the practical significance of the difference between
    two groups, accounting for variance.

    Interpretation:
    - d < 0.2: Negligible effect
    - 0.2 <= d < 0.5: Small effect
    - 0.5 <= d < 0.8: Medium effect
    - d >= 0.8: Large effect

    Args:
        baseline_scores: Scores before optimization
        optimized_scores: Scores after optimization

    Returns:
        Effect size (Cohen's d)

    Raises:
        ValueError: If arrays are different lengths or empty
    """
    if len(baseline_scores) != len(optimized_scores):
        raise ValueError(
            f"Array lengths don't match: {len(baseline_scores)} != {len(optimized_scores)}"
        )
    if len(baseline_scores) == 0:
        raise ValueError("Cannot calculate effect size on empty arrays")

    baseline_array = np.array(baseline_scores)
    optimized_array = np.array(optimized_scores)

    mean_diff = np.mean(optimized_array) - np.mean(baseline_array)

    # Pooled standard deviation
    pooled_std = np.sqrt(
        (np.std(baseline_array, ddof=1) ** 2 + np.std(optimized_array, ddof=1) ** 2) / 2
    )

    # Avoid division by zero
    if pooled_std == 0:
        return 0.0

    return mean_diff / pooled_std


def paired_t_test(
    baseline_scores: list[float],
    optimized_scores: list[float],
    alternative: str = "less",
) -> tuple[float, float]:
    """Run paired t-test to compare baseline vs optimized scores.

    The paired t-test handles correlated samples (same examples evaluated
    before and after optimization), which is more powerful than independent
    t-tests for this use case.

    Args:
        baseline_scores: Scores before optimization
        optimized_scores: Scores after optimization
        alternative: Alternative hypothesis ("less", "greater", "two-sided")
                    Default "less" tests if baseline < optimized

    Returns:
        Tuple of (statistic, p_value)

    Raises:
        ValueError: If arrays are different lengths or too small
    """
    if len(baseline_scores) != len(optimized_scores):
        raise ValueError(
            f"Array lengths don't match: {len(baseline_scores)} != {len(optimized_scores)}"
        )
    if len(baseline_scores) < 2:
        raise ValueError(f"Need at least 2 samples, got {len(baseline_scores)}")

    return ttest_rel(baseline_scores, optimized_scores, alternative=alternative)


def validate_metric_correlation(
    human_scores: list[float],
    metric_scores: list[float],
    min_correlation: float = 0.8,
) -> tuple[float, float, bool]:
    """Validate that metric correlates with human judgment.

    This validates the metric itself (from H10) by checking correlation
    with human-labeled ground truth.

    Args:
        human_scores: Human-assigned quality scores
        metric_scores: Metric-computed scores
        min_correlation: Minimum acceptable correlation (default 0.8 from H10)

    Returns:
        Tuple of (correlation, p_value, passes_threshold)

    Raises:
        ValueError: If arrays are different lengths or empty
    """
    if len(human_scores) != len(metric_scores):
        raise ValueError(f"Array lengths don't match: {len(human_scores)} != {len(metric_scores)}")
    if len(human_scores) < 3:
        raise ValueError(f"Need at least 3 samples for correlation, got {len(human_scores)}")

    correlation, p_value = pearsonr(human_scores, metric_scores)
    passes = correlation >= min_correlation

    return correlation, p_value, passes


__all__ = [
    "OptimizationValidator",
    "ValidationResult",
    "cohens_d",
    "paired_t_test",
    "validate_metric_correlation",
]
