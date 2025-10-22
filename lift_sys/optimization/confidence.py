"""Confidence calibration for predictions (H12).

This module provides calibrated confidence scores for IR and code predictions,
ensuring that confidence values correlate with actual accuracy.

Example:
    >>> from lift_sys.optimization.confidence import ConfidenceCalibrator
    >>> from lift_sys.ir import IR
    >>>
    >>> # Train calibrator
    >>> calibrator = ConfidenceCalibrator()
    >>> calibrator.fit(predictions, ground_truth_scores, prediction_types)
    >>>
    >>> # Estimate confidence for new prediction
    >>> confidence = calibrator.estimate_confidence(new_ir, "ir")
    >>> print(f"Confidence: {confidence.value:.2f} (calibrated={confidence.calibrated})")
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.isotonic import IsotonicRegression

from lift_sys.ir import IntermediateRepresentation

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    """Result of confidence estimation.

    Attributes:
        value: Confidence score (0.0-1.0), calibrated to match accuracy
        calibrated: Whether score is calibrated or raw
        features: Features used for estimation
        metadata: Additional information (model type, prediction type, etc.)
    """

    value: float  # 0.0-1.0
    calibrated: bool
    features: dict[str, float]
    metadata: dict[str, str]


@dataclass
class CalibrationMetrics:
    """Calibration evaluation metrics.

    Attributes:
        brier_score: Mean squared error between confidence and accuracy (target <0.2)
        ece: Expected Calibration Error (weighted difference per bin)
        calibration_data: List of (confidence_bin, accuracy) for plotting
        correlation: Pearson correlation between confidence and accuracy
    """

    brier_score: float
    ece: float  # Expected Calibration Error
    calibration_data: list[tuple[float, float]]  # (confidence_bin, accuracy)
    correlation: float


class ConfidenceCalibrator:
    """Calibrates confidence scores to match actual accuracy.

    Uses isotonic regression to calibrate raw confidence scores
    (from feature-based models) to match actual accuracy.

    Integrates with H10 (OptimizationMetrics) to use validation dataset
    and ground truth quality scores.

    Example:
        >>> calibrator = ConfidenceCalibrator()
        >>> calibrator.fit(predictions, ground_truth_scores, types)
        >>> confidence = calibrator.estimate_confidence(new_prediction, "ir")
        >>> print(f"Confidence: {confidence.value:.2f}")
    """

    def __init__(self, method: Literal["isotonic", "logistic"] = "isotonic"):
        """Initialize calibrator.

        Args:
            method: Calibration method (isotonic or logistic regression)
        """
        self.method = method

        if method == "isotonic":
            self.ir_calibrator = IsotonicRegression(out_of_bounds="clip")
            self.code_calibrator = IsotonicRegression(out_of_bounds="clip")
        else:
            raise NotImplementedError(f"Method {method} not yet implemented")

        self.ir_fitted = False
        self.code_fitted = False

        logger.info(f"Initialized ConfidenceCalibrator with method={method}")

    def fit(
        self,
        predictions: list[IntermediateRepresentation | str],
        ground_truth_scores: list[float],
        prediction_types: list[Literal["ir", "code"]],
    ):
        """Train calibration model on labeled data.

        Args:
            predictions: List of predictions (IR or code)
            ground_truth_scores: Ground truth quality scores (from H10 metrics)
            prediction_types: Type of each prediction ("ir" or "code")

        Raises:
            ValueError: If input lists have different lengths
        """
        if not (len(predictions) == len(ground_truth_scores) == len(prediction_types)):
            raise ValueError(
                f"Input lengths don't match: {len(predictions)} predictions, "
                f"{len(ground_truth_scores)} scores, {len(prediction_types)} types"
            )

        logger.info(f"Training calibrator on {len(predictions)} examples")

        # Extract features for all predictions
        features_list = []
        for pred, pred_type in zip(predictions, prediction_types, strict=False):
            if pred_type == "ir":
                features = extract_ir_features(pred)
            else:  # code
                features = extract_code_features(pred)
            features_list.append(features)

        # Separate IR and code predictions
        ir_indices = [i for i, t in enumerate(prediction_types) if t == "ir"]
        code_indices = [i for i, t in enumerate(prediction_types) if t == "code"]

        # Compute raw confidence scores (average feature value)
        raw_confidences = [np.mean(list(f.values())) for f in features_list]

        # Fit isotonic regression for IR
        if ir_indices:
            ir_raw = np.array([raw_confidences[i] for i in ir_indices])
            ir_truth = np.array([ground_truth_scores[i] for i in ir_indices])
            self.ir_calibrator.fit(ir_raw, ir_truth)
            self.ir_fitted = True
            logger.info(f"Fitted IR calibrator on {len(ir_indices)} examples")

        # Fit isotonic regression for code
        if code_indices:
            code_raw = np.array([raw_confidences[i] for i in code_indices])
            code_truth = np.array([ground_truth_scores[i] for i in code_indices])
            self.code_calibrator.fit(code_raw, code_truth)
            self.code_fitted = True
            logger.info(f"Fitted code calibrator on {len(code_indices)} examples")

    def estimate_confidence(
        self,
        prediction: IntermediateRepresentation | str,
        prediction_type: Literal["ir", "code"],
        features: dict[str, float] | None = None,
    ) -> ConfidenceScore:
        """Estimate calibrated confidence for prediction.

        Args:
            prediction: IR or code prediction
            prediction_type: Type of prediction ("ir" or "code")
            features: Optional pre-computed features

        Returns:
            ConfidenceScore with calibrated value (0.0-1.0)
        """
        # Extract features if not provided
        if features is None:
            if prediction_type == "ir":
                features = extract_ir_features(prediction)
            else:  # code
                features = extract_code_features(prediction)

        # Compute raw confidence (average feature value)
        raw_confidence = np.mean(list(features.values()))

        # Calibrate if model is fitted
        if prediction_type == "ir" and self.ir_fitted:
            calibrated_value = float(self.ir_calibrator.predict([raw_confidence])[0])
            calibrated = True
        elif prediction_type == "code" and self.code_fitted:
            calibrated_value = float(self.code_calibrator.predict([raw_confidence])[0])
            calibrated = True
        else:
            # Not calibrated yet, return raw
            calibrated_value = raw_confidence
            calibrated = False
            logger.warning(f"Calibrator not fitted for {prediction_type}, returning raw confidence")

        return ConfidenceScore(
            value=calibrated_value,
            calibrated=calibrated,
            features=features,
            metadata={
                "method": self.method,
                "prediction_type": prediction_type,
                "raw_confidence": f"{raw_confidence:.3f}",
            },
        )

    def evaluate_calibration(
        self,
        predictions: list[IntermediateRepresentation | str],
        ground_truth_scores: list[float],
        prediction_types: list[Literal["ir", "code"]],
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Evaluate calibration quality on test set.

        Args:
            predictions: Test predictions
            ground_truth_scores: Ground truth quality scores
            prediction_types: Type of each prediction
            n_bins: Number of bins for calibration plot (default 10)

        Returns:
            CalibrationMetrics with brier_score, ece, calibration_data, correlation
        """
        # Estimate confidence for all predictions
        confidences = []
        for pred, pred_type in zip(predictions, prediction_types, strict=False):
            conf = self.estimate_confidence(pred, pred_type)
            confidences.append(conf.value)

        confidences_array = np.array(confidences)
        truth_array = np.array(ground_truth_scores)

        # Compute Brier score (mean squared error)
        brier_score = float(np.mean((confidences_array - truth_array) ** 2))

        # Compute Expected Calibration Error (ECE)
        ece, calibration_data = compute_ece(confidences, ground_truth_scores, n_bins)

        # Compute Pearson correlation
        if len(confidences) > 1:
            correlation = float(np.corrcoef(confidences_array, truth_array)[0, 1])
        else:
            correlation = 0.0

        logger.info(
            f"Calibration metrics: Brier={brier_score:.4f}, ECE={ece:.4f}, "
            f"Correlation={correlation:.4f}"
        )

        return CalibrationMetrics(
            brier_score=brier_score,
            ece=ece,
            calibration_data=calibration_data,
            correlation=correlation,
        )


def extract_ir_features(ir: IntermediateRepresentation) -> dict[str, float]:
    """Extract features from IR for confidence estimation.

    Features:
        - effect_count: Number of effects (normalized by max 20)
        - effect_complexity: Text length of effects (normalized)
        - signature_completeness: Signature field presence
        - constraint_count: Number of constraints (normalized by max 10)
        - parameter_count: Number of parameters (normalized by max 10)
        - assertion_count: Number of assertions (normalized by max 10)
        - intent_length: Length of intent text (normalized)

    Args:
        ir: IntermediateRepresentation instance

    Returns:
        Dictionary of feature_name -> normalized_value (0.0-1.0)
    """
    features = {}

    # Effect count (normalize by max 20)
    effect_count = len(ir.effects) if ir.effects else 0
    features["effect_count"] = min(effect_count / 20.0, 1.0)

    # Effect complexity (based on total text length of effect descriptions)
    if ir.effects:
        total_effect_text = sum(len(str(eff)) for eff in ir.effects)
        features["effect_complexity"] = min(
            total_effect_text / 500.0, 1.0
        )  # Normalize by 500 chars
    else:
        features["effect_complexity"] = 0.0

    # Signature completeness (check if signature has name and return type)
    if ir.signature:
        # SigClause has: name (str), parameters (list[Parameter]), return_type (str), holes
        has_name = bool(ir.signature.name)
        has_return_type = bool(ir.signature.return_type)
        has_parameters = bool(ir.signature.parameters)
        populated = sum([has_name, has_return_type, has_parameters])
        features["signature_completeness"] = populated / 3.0
    else:
        features["signature_completeness"] = 0.0

    # Constraint count (normalize by max 10)
    constraint_count = len(ir.constraints) if ir.constraints else 0
    features["constraint_count"] = min(constraint_count / 10.0, 1.0)

    # Parameter count (number of parameters in signature)
    param_count = 0
    if ir.signature and ir.signature.parameters:
        param_count = len(ir.signature.parameters)
    features["parameter_count"] = min(param_count / 10.0, 1.0)

    # Assertion count (normalize by max 10)
    assertion_count = len(ir.assertions) if ir.assertions else 0
    features["assertion_count"] = min(assertion_count / 10.0, 1.0)

    # Intent length (normalize by 500 chars)
    if ir.intent:
        intent_text = str(ir.intent)
        features["intent_length"] = min(len(intent_text) / 500.0, 1.0)
    else:
        features["intent_length"] = 0.0

    return features


def extract_code_features(code: str) -> dict[str, float]:
    """Extract features from code for confidence estimation.

    Features:
        - loc: Lines of code (normalized by max 200)
        - cyclomatic_complexity: McCabe complexity (approximated, normalized by max 20)
        - ast_depth: AST tree depth (normalized by max 10)
        - function_count: Number of functions (normalized by max 10)
        - syntax_valid: Boolean (0/1)
        - has_docstrings: Boolean (0/1)
        - import_count: Number of imports (normalized by max 10)

    Args:
        code: Python code string

    Returns:
        Dictionary of feature_name -> normalized_value (0.0-1.0)
    """
    features = {}

    # Lines of code (normalize by max 200)
    lines = code.strip().split("\n")
    non_empty_lines = [line for line in lines if line.strip()]
    features["loc"] = min(len(non_empty_lines) / 200.0, 1.0)

    # Parse AST
    try:
        tree = ast.parse(code)
        syntax_valid = True
    except SyntaxError:
        # Syntax error - return low confidence features
        features["syntax_valid"] = 0.0
        features["cyclomatic_complexity"] = 0.0
        features["ast_depth"] = 0.0
        features["function_count"] = 0.0
        features["has_docstrings"] = 0.0
        features["import_count"] = 0.0
        return features

    features["syntax_valid"] = 1.0

    # AST depth (max depth of tree)
    def get_depth(node):
        if not isinstance(node, ast.AST):
            return 0
        children = list(ast.iter_child_nodes(node))
        if not children:
            return 1
        return 1 + max(get_depth(child) for child in children)

    ast_depth = get_depth(tree)
    features["ast_depth"] = min(ast_depth / 10.0, 1.0)

    # Function count (number of FunctionDef nodes)
    function_count = sum(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
    features["function_count"] = min(function_count / 10.0, 1.0)

    # Cyclomatic complexity (approximate with If + For + While + ExceptHandler nodes)
    complexity_nodes = (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)
    complexity = sum(isinstance(node, complexity_nodes) for node in ast.walk(tree))
    features["cyclomatic_complexity"] = min(complexity / 20.0, 1.0)

    # Has docstrings (check for Expr nodes with Str values at top level or in functions)
    has_docstrings = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            if (
                ast.get_docstring(node) is not None
            ):  # ast.get_docstring handles both old and new AST
                has_docstrings = True
                break
    features["has_docstrings"] = 1.0 if has_docstrings else 0.0

    # Import count (Import + ImportFrom nodes)
    import_count = sum(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    features["import_count"] = min(import_count / 10.0, 1.0)

    return features


def compute_brier_score(
    predicted_confidences: list[float],
    actual_outcomes: list[float],
) -> float:
    """Compute Brier score (mean squared error).

    Brier score measures calibration quality. Perfect calibration has score 0.0.
    Acceptance criteria: <0.2

    Args:
        predicted_confidences: List of predicted confidence scores (0.0-1.0)
        actual_outcomes: List of actual outcome scores (0.0-1.0)

    Returns:
        Brier score (lower is better, target <0.2)
    """
    return float(np.mean((np.array(predicted_confidences) - np.array(actual_outcomes)) ** 2))


def compute_ece(
    predicted_confidences: list[float],
    actual_outcomes: list[float],
    n_bins: int = 10,
) -> tuple[float, list[tuple[float, float]]]:
    """Compute Expected Calibration Error.

    ECE = weighted average of |confidence - accuracy| per bin

    Args:
        predicted_confidences: List of predicted confidence scores
        actual_outcomes: List of actual outcome scores
        n_bins: Number of bins for calibration (default 10)

    Returns:
        Tuple of (ece, calibration_data) where:
            - ece: Expected Calibration Error (float)
            - calibration_data: List of (bin_confidence, bin_accuracy) for plotting
    """
    confidences_array = np.array(predicted_confidences)
    outcomes_array = np.array(actual_outcomes)

    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(confidences_array, bins) - 1

    calibration_data = []
    total_ece = 0.0
    total_count = len(predicted_confidences)

    for bin_idx in range(n_bins):
        bin_mask = bin_indices == bin_idx
        if np.sum(bin_mask) == 0:
            continue

        bin_confidences = confidences_array[bin_mask]
        bin_outcomes = outcomes_array[bin_mask]

        bin_confidence = float(np.mean(bin_confidences))
        bin_accuracy = float(np.mean(bin_outcomes))
        bin_count = int(np.sum(bin_mask))

        calibration_data.append((bin_confidence, bin_accuracy))
        total_ece += (bin_count / total_count) * abs(bin_confidence - bin_accuracy)

    return float(total_ece), calibration_data


def train_from_h10_dataset(
    ir_examples: list[tuple[IntermediateRepresentation, float]],
    code_examples: list[tuple[str, float]],
) -> ConfidenceCalibrator:
    """Train calibrator using H10 validation dataset.

    Args:
        ir_examples: List of (IR, ground_truth_score) from H10 validation
        code_examples: List of (code, ground_truth_score) from H10 validation

    Returns:
        Trained ConfidenceCalibrator

    Example:
        >>> from lift_sys.optimization.metrics import ir_quality, code_quality
        >>> # Collect examples with ground truth
        >>> ir_examples = [(ir1, ir_quality(ex1, pred1)), ...]
        >>> code_examples = [(code1, code_quality(ex1, pred1)), ...]
        >>> calibrator = train_from_h10_dataset(ir_examples, code_examples)
    """
    calibrator = ConfidenceCalibrator(method="isotonic")

    # Combine IR and code examples
    predictions = [ir for ir, _ in ir_examples] + [code for code, _ in code_examples]
    ground_truth = [score for _, score in ir_examples] + [score for _, score in code_examples]
    types = ["ir"] * len(ir_examples) + ["code"] * len(code_examples)

    calibrator.fit(predictions, ground_truth, types)

    logger.info(
        f"Trained calibrator from H10 dataset: {len(ir_examples)} IR + "
        f"{len(code_examples)} code examples"
    )

    return calibrator


__all__ = [
    "ConfidenceScore",
    "CalibrationMetrics",
    "ConfidenceCalibrator",
    "extract_ir_features",
    "extract_code_features",
    "compute_brier_score",
    "compute_ece",
    "train_from_h10_dataset",
]
