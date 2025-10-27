---
track: dspy
document_type: hole_preparation
status: complete
priority: P1
phase: 3
completion: 100%
last_updated: 2025-10-21
session_protocol: |
  For new Claude Code session:
  1. H12 is RESOLVED (implementation complete)
  2. Use this document as reference for H12 design decisions
  3. Implementation: lift_sys/optimization/confidence.py
  4. Tests: 31/31 passing (27 unit + 4 integration)
related_docs:
  - docs/tracks/dspy/HOLE_INVENTORY.md
  - docs/tracks/dspy/CONSTRAINT_PROPAGATION_LOG.md
  - docs/tracks/dspy/SESSION_STATE.md
---

# H12: ConfidenceCalibration Preparation

**Date**: 2025-10-21
**Status**: Complete (H12 resolved)
**Phase**: Phase 3 (Week 3)
**Dependencies**: H10 (OptimizationMetrics) ✅ RESOLVED

---

## Overview

H12 implements confidence calibration for predictions, providing calibrated confidence scores (0.0-1.0) that correlate with actual accuracy. This enables the system to estimate prediction quality before ground truth is available.

### Purpose

**Problem**: System generates predictions (IR, code) but doesn't know how confident to be
**Solution**: Calibrated confidence scores that match actual accuracy (score 0.8 → 80% correct)
**Benefit**: Auto-accept high-confidence predictions, flag low-confidence for review

---

## Requirements Analysis

### From HOLE_INVENTORY.md

**Type Signature**:
```python
def score_suggestion(
    hole: TypedHole,
    suggestion: str,
    context: dict
) -> float:  # 0.0-1.0, calibrated to match accuracy
    ...
```

**Constraints**:
- MUST correlate with actual accuracy
- MUST be calibrated (score 0.8 → 80% chance correct)
- SHOULD improve with feedback
- SHOULD consider multiple factors

**Acceptance Criteria**:
- [ ] Calibration plot: predicted vs actual
- [ ] Brier score <0.2
- [ ] Improves with few-shot learning
- [ ] User study: confidence helpful (long-term)

### From Constraint Propagation (Event 8: H10 Resolution)

**Constraint from H10**:
- High confidence (>0.9) MUST correlate with `ir_quality` >0.8
- Low confidence (<0.5) MUST correlate with `ir_quality` <0.6
- Calibrate against H10 validation dataset

**Constraint from H8**:
- MAY use optimization metrics as secondary signal
- High-confidence predictions should optimize better
- Track confidence correlation with optimization improvement

---

## Design Approach

### Core Concept: Feature-Based Calibration

Instead of using the original `score_suggestion(hole, suggestion, context)` signature (which is specific to typed holes meta-framework), we'll implement confidence calibration for our current use case: **IR and code generation quality**.

**Adapted Signature**:
```python
def estimate_confidence(
    prediction: Union[IR, str],  # IR or code
    prediction_type: Literal["ir", "code"],
    features: Optional[dict] = None,
) -> ConfidenceScore:
    """
    Estimate confidence in prediction quality.

    Returns:
        ConfidenceScore with value (0.0-1.0), calibrated to match accuracy
    """
```

### Calibration Strategy

**1. Feature Extraction** (from prediction):
- IR predictions:
  - Number of effects
  - Effect complexity (nested conditions, loops)
  - Signature completeness (all fields populated)
  - Constraint count
  - Parameter type complexity
- Code predictions:
  - Lines of code
  - Cyclomatic complexity
  - AST depth
  - Number of functions
  - Syntax correctness (boolean)

**2. Calibration Model**:
- **Primary**: Isotonic Regression (non-parametric, monotonic)
  - Pros: No assumptions about distribution, preserves ordering
  - Cons: Needs sorted data, can overfit with small datasets
- **Alternative**: Logistic Regression with features
  - Pros: Interpretable, works with small data
  - Cons: Assumes logistic relationship

**3. Training Data**:
- Use H10 validation dataset (20+ IR examples, 20+ code examples)
- Ground truth: H10 metric scores (`ir_quality`, `code_quality`)
- Features: Extracted from predictions
- Target: Calibrated confidence = ir_quality score

**4. Evaluation**:
- **Brier Score**: Mean squared error between confidence and actual (target <0.2)
- **Calibration Plot**: Binned confidence vs actual accuracy
- **Expected Calibration Error (ECE)**: Weighted difference between confidence and accuracy

---

## Implementation Plan

### Step 1: Define Confidence Models (1 hour)

**File**: `lift_sys/optimization/confidence.py`

**Classes**:
```python
from dataclasses import dataclass
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field

@dataclass
class ConfidenceScore:
    """Result of confidence estimation.

    Attributes:
        value: Confidence score (0.0-1.0), calibrated to match accuracy
        calibrated: Whether score is calibrated or raw
        features: Features used for estimation
        metadata: Additional information (model type, etc.)
    """
    value: float  # 0.0-1.0
    calibrated: bool
    features: dict[str, float]
    metadata: dict

class ConfidenceCalibrator:
    """Calibrates confidence scores to match actual accuracy.

    Uses isotonic regression to calibrate raw confidence scores
    (from feature-based models) to match actual accuracy.

    Example:
        >>> calibrator = ConfidenceCalibrator()
        >>> calibrator.fit(predictions, ground_truth_scores)
        >>> confidence = calibrator.estimate_confidence(new_prediction, "ir")
        >>> print(f"Confidence: {confidence.value:.2f}")
    """

    def __init__(self, method: Literal["isotonic", "logistic"] = "isotonic"):
        """Initialize calibrator.

        Args:
            method: Calibration method (isotonic or logistic regression)
        """
        ...

    def fit(
        self,
        predictions: list[Union[IR, str]],
        ground_truth_scores: list[float],
        prediction_types: list[Literal["ir", "code"]],
    ):
        """Train calibration model on labeled data.

        Args:
            predictions: List of predictions (IR or code)
            ground_truth_scores: Ground truth quality scores (from H10 metrics)
            prediction_types: Type of each prediction ("ir" or "code")
        """
        ...

    def estimate_confidence(
        self,
        prediction: Union[IR, str],
        prediction_type: Literal["ir", "code"],
        features: Optional[dict] = None,
    ) -> ConfidenceScore:
        """Estimate calibrated confidence for prediction.

        Args:
            prediction: IR or code prediction
            prediction_type: Type of prediction
            features: Optional pre-computed features

        Returns:
            ConfidenceScore with calibrated value
        """
        ...

    def evaluate_calibration(
        self,
        predictions: list[Union[IR, str]],
        ground_truth_scores: list[float],
        prediction_types: list[Literal["ir", "code"]],
    ) -> CalibrationMetrics:
        """Evaluate calibration quality.

        Returns:
            CalibrationMetrics with brier_score, ece, calibration_plot_data
        """
        ...

@dataclass
class CalibrationMetrics:
    """Calibration evaluation metrics.

    Attributes:
        brier_score: Mean squared error (target <0.2)
        ece: Expected Calibration Error
        calibration_data: List of (confidence_bin, accuracy) for plotting
        correlation: Pearson correlation between confidence and accuracy
    """
    brier_score: float
    ece: float  # Expected Calibration Error
    calibration_data: list[tuple[float, float]]  # (confidence_bin, accuracy)
    correlation: float
```

### Step 2: Implement Feature Extraction (2 hours)

**Functions**:
```python
def extract_ir_features(ir: IR) -> dict[str, float]:
    """Extract features from IR for confidence estimation.

    Features:
        - effect_count: Number of effects
        - effect_complexity: Average nesting depth
        - signature_completeness: Fraction of fields populated
        - constraint_count: Number of constraints
        - parameter_complexity: Type complexity score
        - has_loops: Boolean (0/1)
        - has_conditions: Boolean (0/1)

    Returns:
        Dictionary of feature_name -> normalized_value (0.0-1.0)
    """
    ...

def extract_code_features(code: str) -> dict[str, float]:
    """Extract features from code for confidence estimation.

    Features:
        - loc: Lines of code (normalized)
        - cyclomatic_complexity: McCabe complexity (normalized)
        - ast_depth: AST tree depth (normalized)
        - function_count: Number of functions
        - syntax_valid: Boolean (0/1)
        - has_docstrings: Boolean (0/1)
        - import_count: Number of imports

    Returns:
        Dictionary of feature_name -> normalized_value (0.0-1.0)
    """
    ...
```

### Step 3: Implement Calibration Models (2 hours)

**Isotonic Regression**:
```python
from sklearn.isotonic import IsotonicRegression

class IsotonicCalibrator:
    """Isotonic regression calibration (non-parametric, monotonic)."""

    def __init__(self):
        self.ir_calibrator = IsotonicRegression(out_of_bounds="clip")
        self.code_calibrator = IsotonicRegression(out_of_bounds="clip")
        self.ir_fitted = False
        self.code_fitted = False

    def fit(self, features_list, ground_truth, prediction_types):
        # Separate IR and code predictions
        ir_indices = [i for i, t in enumerate(prediction_types) if t == "ir"]
        code_indices = [i for i, t in enumerate(prediction_types) if t == "code"]

        # Compute raw confidence (average feature value)
        raw_confidences = [np.mean(list(f.values())) for f in features_list]

        # Fit isotonic regression
        if ir_indices:
            ir_raw = [raw_confidences[i] for i in ir_indices]
            ir_truth = [ground_truth[i] for i in ir_indices]
            self.ir_calibrator.fit(ir_raw, ir_truth)
            self.ir_fitted = True

        if code_indices:
            code_raw = [raw_confidences[i] for i in code_indices]
            code_truth = [ground_truth[i] for i in code_indices]
            self.code_calibrator.fit(code_raw, code_truth)
            self.code_fitted = True

    def predict(self, features, prediction_type):
        raw_confidence = np.mean(list(features.values()))

        if prediction_type == "ir" and self.ir_fitted:
            return self.ir_calibrator.predict([raw_confidence])[0]
        elif prediction_type == "code" and self.code_fitted:
            return self.code_calibrator.predict([raw_confidence])[0]
        else:
            # Not calibrated yet, return raw
            return raw_confidence
```

### Step 4: Implement Evaluation Metrics (1 hour)

**Brier Score**:
```python
def compute_brier_score(
    predicted_confidences: list[float],
    actual_outcomes: list[float],  # 0.0-1.0 scores
) -> float:
    """Compute Brier score (mean squared error).

    Target: <0.2 (from acceptance criteria)
    """
    return np.mean((np.array(predicted_confidences) - np.array(actual_outcomes)) ** 2)
```

**Expected Calibration Error (ECE)**:
```python
def compute_ece(
    predicted_confidences: list[float],
    actual_outcomes: list[float],
    n_bins: int = 10,
) -> tuple[float, list[tuple[float, float]]]:
    """Compute Expected Calibration Error.

    ECE = weighted average of |confidence - accuracy| per bin

    Returns:
        (ece, calibration_data) where calibration_data is list of (bin_confidence, bin_accuracy)
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(predicted_confidences, bins) - 1

    calibration_data = []
    total_ece = 0.0
    total_count = len(predicted_confidences)

    for bin_idx in range(n_bins):
        bin_mask = bin_indices == bin_idx
        if np.sum(bin_mask) == 0:
            continue

        bin_confidences = np.array(predicted_confidences)[bin_mask]
        bin_outcomes = np.array(actual_outcomes)[bin_mask]

        bin_confidence = np.mean(bin_confidences)
        bin_accuracy = np.mean(bin_outcomes)
        bin_count = len(bin_confidences)

        calibration_data.append((bin_confidence, bin_accuracy))
        total_ece += (bin_count / total_count) * abs(bin_confidence - bin_accuracy)

    return total_ece, calibration_data
```

### Step 5: Integration with H10 Metrics (1 hour)

**Use H10 validation dataset for training**:
```python
# In lift_sys/optimization/confidence.py

def train_from_h10_dataset(
    ir_examples: list[tuple[IR, float]],  # (IR, ir_quality_score)
    code_examples: list[tuple[str, float]],  # (code, code_quality_score)
) -> ConfidenceCalibrator:
    """Train calibrator using H10 validation dataset.

    Args:
        ir_examples: List of (IR, ground_truth_score) from H10 validation
        code_examples: List of (code, ground_truth_score) from H10 validation

    Returns:
        Trained ConfidenceCalibrator
    """
    calibrator = ConfidenceCalibrator(method="isotonic")

    # Combine IR and code examples
    predictions = [ir for ir, _ in ir_examples] + [code for code, _ in code_examples]
    ground_truth = [score for _, score in ir_examples] + [score for _, score in code_examples]
    types = ["ir"] * len(ir_examples) + ["code"] * len(code_examples)

    calibrator.fit(predictions, ground_truth, types)
    return calibrator
```

---

## Testing Strategy

### Unit Tests (tests/unit/optimization/test_confidence.py)

**Feature Extraction Tests**:
- Test `extract_ir_features()` with simple/complex IR
- Test `extract_code_features()` with valid/invalid code
- Verify feature normalization (all values 0.0-1.0)
- Test edge cases (empty IR, syntax errors)

**Calibration Model Tests**:
- Test `IsotonicCalibrator.fit()` with synthetic data
- Test `IsotonicCalibrator.predict()` with calibrated/uncalibrated
- Test calibration preserves monotonicity
- Test out-of-bounds handling (clip to [0, 1])

**Metrics Tests**:
- Test `compute_brier_score()` with perfect/random predictions
- Test `compute_ece()` with well-calibrated/poorly-calibrated data
- Test calibration plot data generation

**ConfidenceCalibrator Tests**:
- Test full workflow: fit → estimate → evaluate
- Test with H10 dataset (IR and code examples)
- Test acceptance criteria: Brier score <0.2
- Test calibration alignment: high confidence → high quality

### Integration Tests (tests/integration/test_confidence_e2e.py)

**End-to-End Calibration**:
- Load H10 validation dataset
- Train calibrator
- Evaluate on held-out set
- Verify Brier score <0.2
- Generate calibration plot
- Verify correlation >0.7 with ground truth

**Correlation with H10 Metrics**:
- High confidence (>0.9) → ir_quality >0.8
- Low confidence (<0.5) → ir_quality <0.6
- Mid confidence (0.6-0.8) → ir_quality 0.5-0.7

---

## Acceptance Criteria Validation

### AC1: Calibration plot (predicted vs actual)

**Implementation**:
```python
def plot_calibration(calibration_data: list[tuple[float, float]]):
    """Generate calibration plot.

    X-axis: Predicted confidence
    Y-axis: Actual accuracy
    Diagonal: Perfect calibration
    """
    # In tests, just verify data structure
    # In production, use matplotlib
```

**Test**: Verify `CalibrationMetrics.calibration_data` has correct structure

### AC2: Brier score <0.2

**Test**: `test_brier_score_acceptance()`
```python
def test_brier_score_acceptance():
    """Verify Brier score meets acceptance criteria."""
    calibrator = train_from_h10_dataset(ir_examples, code_examples)
    metrics = calibrator.evaluate_calibration(test_predictions, test_scores, test_types)
    assert metrics.brier_score < 0.2  # Acceptance criteria
```

### AC3: Improves with few-shot learning

**Test**: Train with 5 examples → add 5 more → verify Brier score decreases

```python
def test_improves_with_feedback():
    """Verify calibration improves with more data."""
    # Train with 5 examples
    calibrator_small = train_with_n_examples(5)
    metrics_small = calibrator_small.evaluate_calibration(test_set)

    # Train with 10 examples
    calibrator_large = train_with_n_examples(10)
    metrics_large = calibrator_large.evaluate_calibration(test_set)

    # Should improve
    assert metrics_large.brier_score < metrics_small.brier_score
```

### AC4: User study (long-term)

**Deferred**: Requires user interface and real usage data. Document as future work.

---

## Dependencies and Integration

### Uses (Blocked By - Now Resolved)

**H10: OptimizationMetrics** ✅
- Uses validation dataset for training
- Ground truth: `ir_quality()` and `code_quality()` scores
- Feature extraction inspired by H10 metrics

### Provides (Blocks)

**Suggestion Quality**:
- Confidence scores enable auto-accept/reject decisions
- High-confidence predictions skip human review
- Low-confidence predictions flagged for manual check

**Optional Integration with H8**:
- Track confidence correlation with optimization improvement
- High-confidence predictions should optimize better

---

## Implementation Timeline

**Total Estimate**: 7-8 hours

1. **Define Models** (1h): ConfidenceScore, ConfidenceCalibrator, CalibrationMetrics
2. **Feature Extraction** (2h): extract_ir_features, extract_code_features
3. **Calibration Models** (2h): IsotonicCalibrator implementation
4. **Evaluation Metrics** (1h): Brier score, ECE, calibration plot data
5. **H10 Integration** (1h): train_from_h10_dataset, use validation data
6. **Testing** (1-2h): Unit tests (20+), integration tests (5+)

---

## Known Limitations

1. **Small Dataset**: H10 has 20+ IR, 20+ code examples (minimum for calibration)
   - Mitigation: Use isotonic regression (works with small data)
   - Future: Collect more labeled examples

2. **Feature Engineering**: Simple features may not capture all quality signals
   - Mitigation: Start simple, add features based on correlation analysis
   - Future: Use learned representations (embeddings)

3. **No Online Learning**: Calibrator doesn't update with new feedback
   - Mitigation: Periodic retraining with accumulated data
   - Future: Implement online calibration updates

4. **Separate IR/Code Models**: Different calibrators for IR vs code
   - Mitigation: Reasonable since quality metrics differ
   - Future: Unified model with prediction_type as feature

---

## Future Enhancements

1. **Learned Features**: Replace hand-crafted features with embeddings
2. **Online Calibration**: Update calibrator with user feedback
3. **Multi-Task Learning**: Joint model for IR and code
4. **Uncertainty Quantification**: Confidence intervals, not just point estimates
5. **Active Learning**: Use confidence to select examples for labeling

---

## References

- **Calibration**: Guo et al. "On Calibration of Modern Neural Networks" (ICML 2017)
- **Brier Score**: Brier (1950) "Verification of forecasts"
- **Isotonic Regression**: Scikit-learn IsotonicRegression documentation
- **H10 Metrics**: `docs/planning/H10_OPTIMIZATION_METRICS_SPEC.md`

---

**Document Status**: ACTIVE - Planning complete, ready for implementation
**Owner**: Session 3 (2025-10-21)
**Next Steps**: Implement ConfidenceCalibrator in lift_sys/optimization/confidence.py
