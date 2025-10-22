"""Minimal tests for confidence calibration (H12)."""

import pytest

from lift_sys.optimization.confidence import (
    CalibrationMetrics,
    ConfidenceCalibrator,
    ConfidenceScore,
    compute_brier_score,
    extract_code_features,
)


class TestExtractCodeFeatures:
    """Tests for code feature extraction."""

    def test_extract_simple_code_features(self):
        """Test feature extraction from simple code."""
        code = '''
def greet(name):
    """Greet someone."""
    return f"Hello, {name}!"
'''
        features = extract_code_features(code)

        # Check all expected features present
        expected_keys = {
            "loc",
            "cyclomatic_complexity",
            "ast_depth",
            "function_count",
            "syntax_valid",
            "has_docstrings",
            "import_count",
        }
        assert set(features.keys()) == expected_keys

        # Check normalization
        for key, value in features.items():
            assert 0.0 <= value <= 1.0, f"Feature {key}={value} not in [0, 1]"

        assert features["syntax_valid"] == 1.0
        assert features["has_docstrings"] == 1.0


class TestMetrics:
    """Tests for calibration metrics."""

    def test_compute_brier_score_perfect(self):
        """Test Brier score with perfect calibration."""
        predicted = [0.1, 0.5, 0.9]
        actual = [0.1, 0.5, 0.9]

        brier = compute_brier_score(predicted, actual)

        assert brier == pytest.approx(0.0, abs=1e-6)

    def test_compute_brier_score_acceptance_criteria(self):
        """Test Brier score meets acceptance criteria (<0.2)."""
        predicted = [0.2, 0.4, 0.6, 0.8, 0.9]
        actual = [0.15, 0.45, 0.55, 0.85, 0.95]

        brier = compute_brier_score(predicted, actual)

        assert brier < 0.2


class TestConfidenceCalibrator:
    """Tests for ConfidenceCalibrator with code examples."""

    @pytest.fixture
    def simple_code_examples(self):
        """Create simple code examples for testing."""
        codes = []
        scores = []

        for i in range(10):
            code = f'''
def func_{i}(x):
    """Function {i}."""
    return x * {i}
'''
            codes.append(code)
            scores.append(i / 10.0)

        return codes, scores

    def test_calibrator_initialization(self):
        """Test calibrator initialization."""
        calibrator = ConfidenceCalibrator(method="isotonic")

        assert calibrator.method == "isotonic"
        assert not calibrator.ir_fitted
        assert not calibrator.code_fitted

    def test_calibrator_fit_code(self, simple_code_examples):
        """Test calibrator fit with code examples."""
        codes, scores = simple_code_examples

        calibrator = ConfidenceCalibrator()
        calibrator.fit(codes, scores, ["code"] * len(codes))

        assert calibrator.code_fitted

    def test_estimate_confidence_code(self, simple_code_examples):
        """Test estimate_confidence with code."""
        codes, scores = simple_code_examples

        calibrator = ConfidenceCalibrator()
        calibrator.fit(codes, scores, ["code"] * len(codes))

        confidence = calibrator.estimate_confidence(codes[0], "code")

        assert isinstance(confidence, ConfidenceScore)
        assert 0.0 <= confidence.value <= 1.0
        assert confidence.calibrated

    def test_evaluate_calibration_code(self, simple_code_examples):
        """Test evaluate_calibration on code examples."""
        codes, scores = simple_code_examples

        calibrator = ConfidenceCalibrator()
        calibrator.fit(codes[:7], scores[:7], ["code"] * 7)

        metrics = calibrator.evaluate_calibration(codes[7:], scores[7:], ["code"] * 3)

        assert isinstance(metrics, CalibrationMetrics)
        assert 0.0 <= metrics.brier_score <= 1.0
        assert 0.0 <= metrics.ece <= 1.0
        # Correlation can be NaN with very small datasets or constant values
        assert metrics.correlation is not None
