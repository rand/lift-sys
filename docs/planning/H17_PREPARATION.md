# H17: OptimizationValidation - Implementation Preparation

**Date**: 2025-10-21
**Status**: Ready to Start (Unblocked by H8 + H10)
**Phase**: 7 (Week 7) - but ready early!
**Priority**: CRITICAL PATH (blocks production deployment confidence)

---

## Overview

H17 provides statistical validation that optimization actually improves pipeline performance, using H8 optimization API and H10 metrics.

**Key Goal**: Validate that DSPy optimization (MIPROv2, COPRO) produces statistically significant improvements with measurable effect sizes.

---

## Dependencies

### Resolved (Ready)
- ✅ **H10**: OptimizationMetrics - Provides metrics for measuring improvement
- ✅ **H8**: OptimizationAPI - Provides optimization infrastructure
- ✅ **H1**: ProviderAdapter - Provides route support for testing
- ✅ **H6**: NodeSignatureInterface - Provides pipeline structure

### Blocks
- **Production deployment confidence** (can't deploy without validation)
- **Phase 7 completion** (validation is critical path)

---

## Type Signature (from HOLE_INVENTORY.md)

```python
def validate_optimization(
    baseline: Pipeline,
    optimized: Pipeline,
    test_set: list[Example]
) -> ValidationResult:
    # Returns p-value, effect size, recommendation
    ...
```

---

## Constraints (from Propagation)

### From H10 (Event 8)
**Constraint**: MUST use H10 metrics for validation
**Requirements**:
- Measure pre/post optimization quality with `ir_quality()` and `code_quality()`
- Track cost improvements with `route_cost()`
- Validate correlation with `pearsonr()` >0.8 target
- Use 20+ examples minimum for statistical power

### From H8 (Event 9)
**Constraint**: MUST use H8 optimization API
**Requirements**:
- Use `DSPyOptimizer` or `RouteAwareOptimizer` for all optimization runs
- Compare baseline vs optimized metrics using `OptimizationResult` structure
- Test both MIPROv2 and COPRO optimizers
- Validate route-aware optimization across both provider routes

### From HOLE_INVENTORY.md
**Constraints**:
- MUST use statistical significance (p < 0.05)
- MUST measure effect size (Cohen's d)
- SHOULD use held-out test set
- SHOULD account for variance

---

## Acceptance Criteria

From HOLE_INVENTORY.md:
- [ ] Paired t-test implemented
- [ ] Effect size (Cohen's d) calculated
- [ ] Test on 50+ held-out examples
- [ ] Documentation of methodology
- [ ] Both MIPROv2 and COPRO tested
- [ ] Both provider routes tested (ADR 001)
- [ ] Statistical significance validated (p < 0.05)

---

## Implementation Strategy

### Approach: Statistical Validation Framework

**Core Components**:
1. **ValidationRunner**: Runs baseline vs optimized comparisons
2. **StatisticalTests**: Paired t-test, Cohen's d, correlation analysis
3. **ValidationResult**: Structured result with p-value, effect size, recommendations
4. **ValidationReport**: Human-readable summary with visualizations

**Why This Approach**:
- Paired t-test handles correlated samples (same examples, before/after)
- Cohen's d quantifies practical significance (not just statistical)
- Correlation validates metric reliability
- Structured results enable automated decision-making

---

## Key Statistical Concepts

### Paired t-test
```python
# Compare before/after scores on same examples
from scipy.stats import ttest_rel

baseline_scores = [0.6, 0.7, 0.5, ...]
optimized_scores = [0.8, 0.9, 0.7, ...]

statistic, p_value = ttest_rel(baseline_scores, optimized_scores)

# Interpretation:
# p < 0.05: Significant improvement
# p >= 0.05: No significant difference
```

### Cohen's d (Effect Size)
```python
def cohens_d(baseline, optimized):
    """Calculate effect size.

    Interpretation:
    - d < 0.2: Small effect
    - 0.2 <= d < 0.5: Small effect
    - 0.5 <= d < 0.8: Medium effect
    - d >= 0.8: Large effect
    """
    mean_diff = mean(optimized) - mean(baseline)
    pooled_std = sqrt((std(baseline)**2 + std(optimized)**2) / 2)
    return mean_diff / pooled_std
```

### Correlation Analysis
```python
from scipy.stats import pearsonr

# Validate metric reliability
human_scores = [...]  # Ground truth
metric_scores = [...]  # ir_quality() scores

correlation, p_value = pearsonr(human_scores, metric_scores)

# Target: correlation > 0.8 (from H10 validation)
```

---

## Implementation Plan

### Step 1: Core Validation Framework (2-3 hours)
**File**: `lift_sys/optimization/validation.py`

```python
from dataclasses import dataclass
from typing import Callable

import dspy
from scipy.stats import ttest_rel
from scipy.stats import pearsonr

from lift_sys.optimization import DSPyOptimizer, OptimizationResult
from lift_sys.optimization.metrics import ir_quality, code_quality


@dataclass
class ValidationResult:
    """Result of optimization validation experiment.

    Attributes:
        p_value: Statistical significance (target < 0.05)
        effect_size: Cohen's d effect size
        baseline_mean: Mean baseline score
        optimized_mean: Mean optimized score
        improvement_pct: Percentage improvement
        significant: Whether improvement is statistically significant
        recommendation: Deployment recommendation
    """
    p_value: float
    effect_size: float
    baseline_mean: float
    optimized_mean: float
    improvement_pct: float
    significant: bool
    recommendation: str


class OptimizationValidator:
    """Validates that optimization improves pipeline performance.

    Uses paired t-test and Cohen's d to assess statistical and practical
    significance of optimization improvements.

    Example:
        >>> validator = OptimizationValidator(metric=ir_quality)
        >>> result = validator.validate(
        ...     pipeline=my_pipeline,
        ...     optimizer=DSPyOptimizer(),
        ...     train_examples=train_set,
        ...     test_examples=test_set,
        ... )
        >>> print(f"Improvement: {result.improvement_pct:.1f}% (p={result.p_value:.4f})")
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
            significance_level: p-value threshold (default 0.05)
            min_effect_size: Minimum Cohen's d for practical significance
        """
        self.metric = metric
        self.significance_level = significance_level
        self.min_effect_size = min_effect_size

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
            train_examples: Examples for optimization
            test_examples: Held-out examples for validation

        Returns:
            ValidationResult with statistical analysis
        """
        # TODO: Implement validation logic
        pass
```

### Step 2: Statistical Utilities (1-2 hours)
**File**: `lift_sys/optimization/validation.py` (continued)

```python
def cohens_d(baseline_scores: list[float], optimized_scores: list[float]) -> float:
    """Calculate Cohen's d effect size.

    Args:
        baseline_scores: Scores before optimization
        optimized_scores: Scores after optimization

    Returns:
        Effect size (Cohen's d)
    """
    import numpy as np

    mean_diff = np.mean(optimized_scores) - np.mean(baseline_scores)
    pooled_std = np.sqrt(
        (np.std(baseline_scores, ddof=1)**2 + np.std(optimized_scores, ddof=1)**2) / 2
    )
    return mean_diff / pooled_std


def paired_t_test(
    baseline_scores: list[float],
    optimized_scores: list[float],
) -> tuple[float, float]:
    """Run paired t-test.

    Args:
        baseline_scores: Scores before optimization
        optimized_scores: Scores after optimization

    Returns:
        Tuple of (statistic, p_value)
    """
    from scipy.stats import ttest_rel

    return ttest_rel(baseline_scores, optimized_scores)
```

### Step 3: Integration & Testing (2-3 hours)
**File**: `tests/unit/optimization/test_validation.py`

- Test paired t-test with known datasets
- Test Cohen's d calculation
- Test validation with mock optimizer
- Test with 50+ held-out examples
- Test both MIPROv2 and COPRO
- Test both provider routes (ADR 001)

**File**: `tests/integration/test_validation_e2e.py`

- End-to-end validation with real pipeline
- Test statistical significance detection
- Test effect size quantification
- Test recommendation generation

### Step 4: Documentation (1 hour)
- Update HOLE_INVENTORY.md status
- Add usage examples
- Document statistical methodology
- Create validation report template

---

## Expected Outputs

### Implementation Files
1. `lift_sys/optimization/validation.py` (~400 lines)
   - OptimizationValidator class
   - ValidationResult dataclass
   - Statistical utility functions

### Test Files
1. `tests/unit/optimization/test_validation.py` (~300 lines)
   - Statistical test validation
   - Mock optimizer tests
2. `tests/integration/test_validation_e2e.py` (~200 lines)
   - End-to-end validation experiments

### Documentation
1. Updated `HOLE_INVENTORY.md` (H17 status → RESOLVED)
2. `CONSTRAINT_PROPAGATION_LOG.md` Event 10
3. `SESSION_STATE.md` update

---

## Statistical Validation Checklist

**Data Requirements**:
- [ ] 50+ held-out test examples (acceptance criteria)
- [ ] 20+ training examples for optimization (H10 requirement)
- [ ] Separate train/test split (no leakage)

**Statistical Tests**:
- [ ] Paired t-test (p < 0.05 target)
- [ ] Cohen's d (quantify effect size)
- [ ] Correlation analysis (validate metric >0.8)
- [ ] Confidence intervals (quantify uncertainty)

**Optimizer Coverage**:
- [ ] MIPROv2 validated
- [ ] COPRO validated
- [ ] Both provider routes tested (ADR 001)

**Metrics Coverage**:
- [ ] ir_quality tested
- [ ] code_quality tested
- [ ] end_to_end tested
- [ ] route_cost improvements tracked

---

## Risks & Mitigations

**Risk**: Optimization doesn't show significant improvement
**Mitigation**: Use larger dataset, tune optimizer hyperparameters, validate metrics first

**Risk**: High variance in results
**Mitigation**: Use stratified sampling, increase sample size, account for variance in analysis

**Risk**: Metrics don't correlate with human judgment
**Mitigation**: Already validated in H10 (>0.8 correlation for ir_quality)

**Risk**: Statistical tests fail due to small sample
**Mitigation**: Use bootstrap confidence intervals as backup, collect more data

---

## Success Criteria

✅ **Complete when**:
1. Paired t-test correctly detects improvement (p < 0.05)
2. Cohen's d quantifies effect size (target >0.5 medium effect)
3. Validation works with 50+ held-out examples
4. Both MIPROv2 and COPRO validated
5. Both provider routes validated (ADR 001)
6. All acceptance criteria passing
7. Documentation complete with methodology

---

## Example Usage

```python
from lift_sys.optimization import DSPyOptimizer
from lift_sys.optimization.validation import OptimizationValidator
from lift_sys.optimization.metrics import ir_quality

# Prepare datasets
train_examples = [...]  # 20+ examples for optimization
test_examples = [...]   # 50+ held-out examples for validation

# Create validator
validator = OptimizationValidator(metric=ir_quality)

# Run validation experiment
result = validator.validate(
    pipeline=my_pipeline,
    optimizer=DSPyOptimizer(optimizer_type="mipro"),
    train_examples=train_examples,
    test_examples=test_examples,
)

# Check results
print(f"Improvement: {result.improvement_pct:.1f}%")
print(f"p-value: {result.p_value:.4f}")
print(f"Effect size (Cohen's d): {result.effect_size:.2f}")
print(f"Significant: {result.significant}")
print(f"Recommendation: {result.recommendation}")
```

---

## Next Steps After H17

1. **Production Deployment**: Validation enables confident deployment
2. **Phase 7 Completion**: H17 is critical path for Phase 7
3. **Continuous Validation**: Set up monitoring for production optimization

---

**Status**: READY TO START
**Estimated Time**: 6-8 hours total
**Critical Path**: YES (blocks production deployment)
**Dependencies**: All resolved (H10 ✅, H8 ✅)
