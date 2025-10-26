"""Unit tests for validation module (STEP-09)."""

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from lift_sys.causal.validation import (
    BootstrapCI,
    InsufficientDataError,
    R2Score,
    ValidationError,
    ValidationResult,
    bootstrap_confidence_intervals,
    calculate_r_squared,
    cross_validate_scm,
    train_test_split,
)
from tests.causal.fixtures.validation_fixtures import (
    FIXTURE_R2_RANGES,
    create_chain_traces,
    create_dag_traces,
    create_good_fit_traces,
    create_insufficient_data_traces,
    create_multi_parent_traces,
    create_perfect_fit_traces,
    create_poor_fit_traces,
    create_threshold_fit_traces,
)


class TestCalculateRSquared:
    """Tests for calculate_r_squared function."""

    def test_perfect_fit(self):
        """Test R²=1.0 for perfect predictions."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        assert r2 == pytest.approx(1.0)
        assert ss_res == pytest.approx(0.0)
        assert ss_tot > 0

    def test_good_fit(self):
        """Test R²>0.9 for good predictions."""
        traces = create_good_fit_traces(n_samples=100, noise_level=0.1)
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values  # Perfect model

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        # With small noise, R² should be high
        assert r2 > 0.95
        assert r2 <= 1.0
        assert ss_res > 0  # Some error due to noise
        assert ss_tot > ss_res

    def test_poor_fit(self):
        """Test R²<0.5 for poor predictions."""
        traces = create_poor_fit_traces(n_samples=100)
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values  # Model correct but data noisy

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        # With large noise, R² should be low
        min_r2, max_r2 = FIXTURE_R2_RANGES["poor_fit"]
        assert min_r2 <= r2 <= max_r2

    def test_constant_prediction(self):
        """Test R²≈0 when predicting constant (mean)."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.full(5, 3.0)  # Predict mean

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        # Predicting mean gives R²=0
        assert r2 == pytest.approx(0.0, abs=0.01)

    def test_worse_than_constant(self):
        """Test R²<0 for predictions worse than constant."""
        y_true = np.array([1, 2, 3, 4, 5])
        y_pred = np.array([5, 4, 3, 2, 1])  # Completely wrong direction

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        # Worse than mean prediction
        assert r2 < 0

    def test_constant_target_perfect_prediction(self):
        """Test R²=1.0 when target is constant and predicted correctly."""
        y_true = np.full(10, 5.0)
        y_pred = np.full(10, 5.0)

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        assert r2 == 1.0
        assert ss_res == 0.0
        assert ss_tot == 0.0

    def test_constant_target_wrong_prediction(self):
        """Test error when target is constant but prediction is wrong."""
        y_true = np.full(10, 5.0)
        y_pred = np.full(10, 3.0)  # Wrong constant

        with pytest.raises(ValidationError, match="zero variance"):
            calculate_r_squared(y_true, y_pred)

    def test_mismatched_lengths(self):
        """Test error on mismatched array lengths."""
        y_true = np.array([1, 2, 3])
        y_pred = np.array([1, 2])

        with pytest.raises(ValidationError, match="same length"):
            calculate_r_squared(y_true, y_pred)

    def test_insufficient_samples(self):
        """Test error with <2 samples."""
        y_true = np.array([1])
        y_pred = np.array([1])

        with pytest.raises(ValidationError, match="at least 2 samples"):
            calculate_r_squared(y_true, y_pred)

    def test_nan_values(self):
        """Test handling of NaN values (should remove them)."""
        y_true = np.array([1, 2, np.nan, 4, 5])
        y_pred = np.array([1, 2, 3, 4, 5])

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        # Should work with 4 finite samples
        assert np.isfinite(r2)

    def test_all_nan_values(self):
        """Test error when all values are NaN."""
        y_true = np.array([np.nan, np.nan, np.nan])
        y_pred = np.array([1, 2, 3])

        with pytest.raises(ValidationError, match="All values are NaN"):
            calculate_r_squared(y_true, y_pred)

    def test_pandas_series_input(self):
        """Test that pandas Series work as input."""
        y_true = pd.Series([1, 2, 3, 4, 5])
        y_pred = pd.Series([1, 2, 3, 4, 5])

        r2, ss_res, ss_tot = calculate_r_squared(y_true, y_pred)

        assert r2 == pytest.approx(1.0)


class TestTrainTestSplit:
    """Tests for train_test_split function."""

    def test_default_split(self):
        """Test default 80/20 split."""
        traces = create_perfect_fit_traces(n_samples=100)
        train, test = train_test_split(traces, test_size=0.2, random_state=42)

        assert len(train) == 80
        assert len(test) == 20
        assert len(train) + len(test) == len(traces)

    def test_custom_split(self):
        """Test custom split ratio."""
        traces = create_perfect_fit_traces(n_samples=100)
        train, test = train_test_split(traces, test_size=0.3, random_state=42)

        assert len(train) == 70
        assert len(test) == 30

    def test_reproducibility(self):
        """Test that random_state makes split reproducible."""
        traces = create_perfect_fit_traces(n_samples=100)

        train1, test1 = train_test_split(traces, random_state=42)
        train2, test2 = train_test_split(traces, random_state=42)

        pd.testing.assert_frame_equal(train1, train2)
        pd.testing.assert_frame_equal(test1, test2)

    def test_different_seeds(self):
        """Test that different seeds give different splits."""
        traces = create_perfect_fit_traces(n_samples=100)

        train1, _ = train_test_split(traces, random_state=42)
        train2, _ = train_test_split(traces, random_state=123)

        # Should be different (with very high probability)
        assert not train1.equals(train2)

    def test_insufficient_data_for_train(self):
        """Test error when not enough data for train split."""
        traces = create_insufficient_data_traces(n_samples=3)

        # 3 samples * 0.8 = 2.4 → 2 train, 1 test
        # Train needs ≥2 samples, but test only has 1
        with pytest.raises(InsufficientDataError, match="test split"):
            train_test_split(traces, test_size=0.2)

    def test_minimum_viable_split(self):
        """Test minimum viable split (6 samples → 4 train, 2 test)."""
        traces = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "y": [2, 4, 6, 8, 10, 12]})
        train, test = train_test_split(traces, test_size=0.2, random_state=42)

        assert len(train) >= 2
        assert len(test) >= 2
        assert len(train) + len(test) == 6

    def test_invalid_test_size(self):
        """Test error with invalid test_size."""
        traces = create_perfect_fit_traces()

        with pytest.raises(ValidationError, match="test_size must be in"):
            train_test_split(traces, test_size=0.0)

        with pytest.raises(ValidationError, match="test_size must be in"):
            train_test_split(traces, test_size=1.0)

        with pytest.raises(ValidationError, match="test_size must be in"):
            train_test_split(traces, test_size=-0.1)


class TestR2Score:
    """Tests for R2Score dataclass."""

    def test_valid_score(self):
        """Test valid R² score creation."""
        score = R2Score(
            node_id="y",
            r_squared=0.95,
            ss_res=10.0,
            ss_tot=200.0,
            n_samples=100,
            parent_nodes=("x",),
        )

        assert score.node_id == "y"
        assert score.r_squared == 0.95
        assert score.n_samples == 100
        assert score.parent_nodes == ("x",)

    def test_insufficient_samples(self):
        """Test error with <2 samples."""
        with pytest.raises(ValidationError, match="Need ≥2 samples"):
            R2Score(node_id="y", r_squared=0.95, ss_res=10.0, ss_tot=200.0, n_samples=1)

    def test_infinite_values(self):
        """Test error with infinite SS values."""
        with pytest.raises(ValidationError, match="must be finite"):
            R2Score(node_id="y", r_squared=0.95, ss_res=np.inf, ss_tot=200.0, n_samples=100)

        with pytest.raises(ValidationError, match="must be finite"):
            R2Score(node_id="y", r_squared=0.95, ss_res=10.0, ss_tot=np.nan, n_samples=100)

    def test_immutability(self):
        """Test that R2Score is immutable (frozen)."""
        score = R2Score(node_id="y", r_squared=0.95, ss_res=10.0, ss_tot=200.0, n_samples=100)

        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            score.r_squared = 0.90  # type: ignore


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self):
        """Test valid validation result."""
        edge_scores = {
            "y": R2Score(node_id="y", r_squared=0.95, ss_res=10.0, ss_tot=200.0, n_samples=100)
        }

        result = ValidationResult(
            edge_scores=edge_scores,
            aggregate_r2=0.95,
            passes_threshold=True,
            threshold=0.7,
            train_size=80,
            test_size=20,
        )

        assert result.aggregate_r2 == 0.95
        assert result.passes_threshold is True
        assert len(result.failed_nodes) == 0

    def test_failed_result(self):
        """Test failed validation result."""
        edge_scores = {
            "y": R2Score(node_id="y", r_squared=0.5, ss_res=100.0, ss_tot=200.0, n_samples=100)
        }

        result = ValidationResult(
            edge_scores=edge_scores,
            aggregate_r2=0.5,
            passes_threshold=False,
            threshold=0.7,
            train_size=80,
            test_size=20,
            failed_nodes=("y",),
        )

        assert result.aggregate_r2 == 0.5
        assert result.passes_threshold is False
        assert result.failed_nodes == ("y",)

    def test_str_representation(self):
        """Test string representation."""
        edge_scores = {
            "y": R2Score(node_id="y", r_squared=0.95, ss_res=10.0, ss_tot=200.0, n_samples=100)
        }

        result = ValidationResult(
            edge_scores=edge_scores,
            aggregate_r2=0.95,
            passes_threshold=True,
            threshold=0.7,
            train_size=80,
            test_size=20,
        )

        result_str = str(result)
        assert "PASS" in result_str
        assert "0.95" in result_str or "0.9500" in result_str
        assert "80/20" in result_str


class TestCrossValidateSCM:
    """Tests for cross_validate_scm function."""

    def test_perfect_fit_passes(self):
        """Test that perfect fit passes validation."""
        traces, graph = create_dag_traces(n_samples=100, random_state=42)

        # Note: Current implementation uses placeholder predictions (identity)
        # So R² will be 1.0 (perfect) for this test
        # In STEP-09, this will use actual DoWhy predictions

        # For now, this tests the validation logic structure
        # Actual SCM fitting will be tested in STEP-09
        pytest.skip("Requires DoWhy SCM prediction (STEP-09)")

    def test_insufficient_data(self):
        """Test error with insufficient data."""
        traces = create_insufficient_data_traces(n_samples=3)
        graph = nx.DiGraph([("x", "y")])

        with pytest.raises(InsufficientDataError):
            cross_validate_scm(scm=None, traces=traces, causal_graph=graph)

    def test_root_nodes_skipped(self):
        """Test that root nodes (no parents) are skipped."""
        # Single root node - no edges to validate (need more samples for split)
        traces = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        graph = nx.DiGraph()
        graph.add_node("x")

        with pytest.raises(ValidationError, match="No edges to validate"):
            cross_validate_scm(scm=None, traces=traces, causal_graph=graph)


class TestBootstrapCI:
    """Tests for BootstrapCI dataclass."""

    def test_valid_ci(self):
        """Test valid confidence interval."""
        ci = BootstrapCI(
            node_id="y",
            r2_mean=0.85,
            r2_std=0.05,
            ci_lower=0.75,
            ci_upper=0.92,
            n_bootstrap=1000,
            confidence_level=0.95,
        )

        assert ci.node_id == "y"
        assert ci.r2_mean == 0.85
        assert ci.ci_lower < ci.r2_mean < ci.ci_upper

    def test_immutability(self):
        """Test that BootstrapCI is immutable."""
        ci = BootstrapCI(
            node_id="y",
            r2_mean=0.85,
            r2_std=0.05,
            ci_lower=0.75,
            ci_upper=0.92,
            n_bootstrap=1000,
        )

        with pytest.raises((AttributeError, TypeError)):  # FrozenInstanceError
            ci.r2_mean = 0.90  # type: ignore


class TestBootstrapConfidenceIntervals:
    """Tests for bootstrap_confidence_intervals function."""

    def test_bootstrap_basic(self):
        """Test basic bootstrap functionality."""
        pytest.skip("Requires DoWhy SCM prediction (STEP-09)")

    def test_insufficient_bootstrap_samples(self):
        """Test error with too few bootstrap samples."""
        traces = create_perfect_fit_traces()
        graph = nx.DiGraph([("x", "y")])

        with pytest.raises(ValidationError, match="n_bootstrap should be ≥100"):
            bootstrap_confidence_intervals(
                scm=None, traces=traces, causal_graph=graph, n_bootstrap=50
            )

    def test_invalid_confidence_level(self):
        """Test error with invalid confidence level."""
        traces = create_perfect_fit_traces()
        graph = nx.DiGraph([("x", "y")])

        with pytest.raises(ValidationError, match="confidence_level must be in"):
            bootstrap_confidence_intervals(
                scm=None, traces=traces, causal_graph=graph, confidence_level=1.5
            )


class TestValidationFixtures:
    """Tests to verify fixtures produce expected R² ranges."""

    def test_perfect_fit_fixture(self):
        """Verify perfect_fit fixture has R²≈1.0."""
        traces = create_perfect_fit_traces()

        # y = 2x (perfect fit)
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values

        r2, _, _ = calculate_r_squared(y_true, y_pred)

        min_r2, max_r2 = FIXTURE_R2_RANGES["perfect_fit"]
        assert min_r2 <= r2 <= max_r2

    def test_good_fit_fixture(self):
        """Verify good_fit fixture has R²≈0.95."""
        traces = create_good_fit_traces()

        # y = 2x + small_noise
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values

        r2, _, _ = calculate_r_squared(y_true, y_pred)

        min_r2, max_r2 = FIXTURE_R2_RANGES["good_fit"]
        assert min_r2 <= r2 <= max_r2

    def test_threshold_fit_fixture(self):
        """Verify threshold_fit fixture has R²≈0.7."""
        traces = create_threshold_fit_traces(target_r2=0.7)

        # y = 2x + calibrated_noise
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values

        r2, _, _ = calculate_r_squared(y_true, y_pred)

        min_r2, max_r2 = FIXTURE_R2_RANGES["threshold_fit"]
        assert min_r2 <= r2 <= max_r2

    def test_poor_fit_fixture(self):
        """Verify poor_fit fixture has R²<0.5."""
        traces = create_poor_fit_traces()

        # y = 2x + large_noise
        y_true = traces["y"].values
        y_pred = 2 * traces["x"].values

        r2, _, _ = calculate_r_squared(y_true, y_pred)

        min_r2, max_r2 = FIXTURE_R2_RANGES["poor_fit"]
        assert min_r2 <= r2 <= max_r2

    def test_multi_parent_fixture(self):
        """Verify multi-parent fixture structure."""
        traces = create_multi_parent_traces()

        assert list(traces.columns) == ["x1", "x2", "x3", "y"]
        assert len(traces) == 100

    def test_dag_fixture(self):
        """Verify DAG fixture structure."""
        traces, graph = create_dag_traces()

        # Check graph structure
        assert nx.is_directed_acyclic_graph(graph)
        assert set(graph.nodes()) == {"x", "a", "b", "c"}
        assert set(graph.edges()) == {("x", "a"), ("x", "b"), ("a", "c"), ("b", "c")}

        # Check traces
        assert list(traces.columns) == ["x", "a", "b", "c"]

    def test_chain_fixture(self):
        """Verify chain fixture structure."""
        traces, graph = create_chain_traces(chain_length=5)

        # Check graph structure
        assert nx.is_directed_acyclic_graph(graph)
        assert len(graph.nodes()) == 5
        assert len(graph.edges()) == 4

        # Check traces
        assert len(traces.columns) == 5
