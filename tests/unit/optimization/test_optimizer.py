"""Unit tests for DSPyOptimizer and RouteAwareOptimizer (H8)."""

from unittest.mock import Mock, patch

import dspy
import pytest

from lift_sys.dspy_signatures.provider_adapter import ProviderRoute
from lift_sys.optimization import (
    DSPyOptimizer,
    OptimizationResult,
    RouteAwareOptimizer,
    RouteOptimizationResult,
)
from lift_sys.optimization.metrics import aggregate_metric, end_to_end


class TestDSPyOptimizer:
    """Tests for DSPyOptimizer wrapper class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        optimizer = DSPyOptimizer()
        assert optimizer.optimizer_type == "mipro"
        assert optimizer.metric == aggregate_metric
        assert optimizer.optimizer_kwargs == {}

    def test_init_custom_metric(self):
        """Test initialization with custom metric."""
        optimizer = DSPyOptimizer(metric=end_to_end)
        assert optimizer.metric == end_to_end

    def test_init_copro(self):
        """Test initialization with COPRO optimizer."""
        optimizer = DSPyOptimizer(optimizer_type="copro", breadth=5, depth=2)
        assert optimizer.optimizer_type == "copro"
        assert optimizer.optimizer_kwargs["breadth"] == 5
        assert optimizer.optimizer_kwargs["depth"] == 2

    def test_init_invalid_type(self):
        """Test initialization with invalid optimizer type."""
        with pytest.raises(ValueError, match="optimizer_type must be"):
            DSPyOptimizer(optimizer_type="invalid")

    def test_default_metric(self):
        """Test default metric is aggregate_metric."""
        optimizer = DSPyOptimizer()
        assert optimizer._default_metric() == aggregate_metric

    @patch("lift_sys.optimization.optimizer.MIPROv2")
    def test_create_optimizer_mipro(self, mock_mipro):
        """Test creating MIPROv2 optimizer instance."""
        optimizer = DSPyOptimizer(
            optimizer_type="mipro",
            num_candidates=5,
            init_temperature=1.2,
        )

        optimizer._create_optimizer()

        mock_mipro.assert_called_once_with(
            metric=aggregate_metric,
            num_candidates=5,
            init_temperature=1.2,
        )

    @patch("lift_sys.optimization.optimizer.COPRO")
    def test_create_optimizer_copro(self, mock_copro):
        """Test creating COPRO optimizer instance."""
        optimizer = DSPyOptimizer(
            optimizer_type="copro",
            breadth=8,
            depth=4,
        )

        optimizer._create_optimizer()

        mock_copro.assert_called_once_with(
            metric=aggregate_metric,
            breadth=8,
            depth=4,
        )

    def test_get_compile_kwargs_mipro(self):
        """Test getting compile kwargs for MIPROv2."""
        optimizer = DSPyOptimizer(optimizer_type="mipro", num_trials=15)
        kwargs = optimizer._get_compile_kwargs()
        assert kwargs == {"num_trials": 15}

    def test_get_compile_kwargs_copro(self):
        """Test getting compile kwargs for COPRO."""
        optimizer = DSPyOptimizer(optimizer_type="copro")
        kwargs = optimizer._get_compile_kwargs()
        assert kwargs == {}

    def test_get_num_trials_mipro(self):
        """Test getting number of trials for MIPROv2."""
        optimizer = DSPyOptimizer(optimizer_type="mipro", num_trials=20)
        assert optimizer._get_num_trials() == 20

    def test_get_num_trials_copro(self):
        """Test getting number of trials for COPRO (breadth * depth)."""
        optimizer = DSPyOptimizer(optimizer_type="copro", breadth=10, depth=3)
        assert optimizer._get_num_trials() == 30

    def test_get_config(self):
        """Test getting optimizer configuration."""
        optimizer = DSPyOptimizer(
            optimizer_type="mipro",
            num_candidates=5,
            num_trials=15,
        )
        config = optimizer._get_config()
        assert config["optimizer_type"] == "mipro"
        assert config["metric"] == "aggregate_metric"
        assert config["num_candidates"] == 5
        assert config["num_trials"] == 15

    @patch("lift_sys.optimization.optimizer.logger")
    def test_configure_route(self, mock_logger):
        """Test route configuration placeholder."""
        optimizer = DSPyOptimizer()
        optimizer._configure_route(ProviderRoute.BEST_AVAILABLE)
        # Should log debug message
        mock_logger.debug.assert_called_once()

    def test_evaluate_pipeline_simple(self):
        """Test pipeline evaluation with simple metric."""

        # Create mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.return_value = {"output": "result"}

        # Create mock examples
        examples = [
            dspy.Example(input="test1", output="result1").with_inputs("input"),
            dspy.Example(input="test2", output="result2").with_inputs("input"),
        ]

        # Create optimizer with mock metric
        mock_metric = Mock(return_value=0.8)
        optimizer = DSPyOptimizer(metric=mock_metric)

        # Evaluate
        metrics = optimizer._evaluate_pipeline(mock_pipeline, examples)

        assert metrics["quality"] == 0.8  # Average of two 0.8 scores
        assert metrics["n_evaluated"] == 2
        assert metrics["n_failed"] == 0
        assert mock_metric.call_count == 2

    def test_evaluate_pipeline_with_failures(self):
        """Test pipeline evaluation when some examples fail."""

        # Create mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.side_effect = [
            {"output": "result1"},
            Exception("Failed"),
            {"output": "result3"},
        ]

        # Create mock examples
        examples = [
            dspy.Example(input="test1", output="result1").with_inputs("input"),
            dspy.Example(input="test2", output="result2").with_inputs("input"),
            dspy.Example(input="test3", output="result3").with_inputs("input"),
        ]

        # Create optimizer with mock metric
        mock_metric = Mock(return_value=0.9)
        optimizer = DSPyOptimizer(metric=mock_metric)

        # Evaluate
        metrics = optimizer._evaluate_pipeline(mock_pipeline, examples)

        # 2 successes at 0.9, 1 failure at 0.0 = avg 0.6
        assert metrics["quality"] == 0.6
        assert metrics["n_evaluated"] == 3
        assert metrics["n_failed"] == 1

    @patch("lift_sys.optimization.optimizer.MIPROv2")
    def test_optimize_success(self, mock_mipro_class):
        """Test successful optimization run."""

        # Mock the optimizer instance
        mock_optimizer = Mock()
        mock_optimized_pipeline = Mock()
        mock_optimizer.compile.return_value = mock_optimized_pipeline
        mock_mipro_class.return_value = mock_optimizer

        # Create mock pipeline and examples
        mock_pipeline = Mock()
        mock_pipeline.return_value = {"output": "result"}
        mock_optimized_pipeline.return_value = {"output": "better_result"}

        examples = [
            dspy.Example(input="test1", output="result1").with_inputs("input"),
        ]

        # Create optimizer
        mock_metric = Mock(side_effect=[0.5, 0.9])  # Before, after
        optimizer = DSPyOptimizer(metric=mock_metric)

        # Run optimization
        result = optimizer.optimize(
            pipeline=mock_pipeline,
            examples=examples,
            route_strategy=ProviderRoute.BEST_AVAILABLE,
        )

        # Verify result
        assert isinstance(result, OptimizationResult)
        assert result.optimized_pipeline == mock_optimized_pipeline
        assert result.metrics_before["quality"] == 0.5
        assert result.metrics_after["quality"] == 0.9
        assert result.route_used == ProviderRoute.BEST_AVAILABLE
        assert result.optimizer_type == "mipro"
        assert result.num_trials == 10  # Default
        assert result.duration_seconds > 0

    def test_optimize_empty_examples(self):
        """Test optimization with empty examples raises error."""
        optimizer = DSPyOptimizer()
        mock_pipeline = Mock()

        with pytest.raises(ValueError, match="examples cannot be empty"):
            optimizer.optimize(pipeline=mock_pipeline, examples=[])

    @patch("lift_sys.optimization.optimizer.MIPROv2")
    def test_optimize_failure(self, mock_mipro_class):
        """Test optimization failure handling."""

        # Mock optimizer to raise exception
        mock_optimizer = Mock()
        mock_optimizer.compile.side_effect = Exception("Optimization failed")
        mock_mipro_class.return_value = mock_optimizer

        # Create mock pipeline and examples
        mock_pipeline = Mock()
        examples = [
            dspy.Example(input="test1", output="result1").with_inputs("input"),
        ]

        # Create optimizer
        optimizer = DSPyOptimizer()

        # Run optimization - should raise RuntimeError
        with pytest.raises(RuntimeError, match="Optimization failed"):
            optimizer.optimize(pipeline=mock_pipeline, examples=examples)


class TestRouteAwareOptimizer:
    """Tests for RouteAwareOptimizer class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        optimizer = RouteAwareOptimizer()
        assert optimizer.quality_weight == 0.7
        assert optimizer.cost_weight == 0.3
        assert optimizer.base_optimizer.optimizer_type == "mipro"

    def test_init_custom_weights(self):
        """Test initialization with custom weights."""
        optimizer = RouteAwareOptimizer(quality_weight=0.6, cost_weight=0.4)
        assert optimizer.quality_weight == 0.6
        assert optimizer.cost_weight == 0.4

    def test_init_invalid_weights(self):
        """Test initialization with weights that don't sum to 1.0."""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            RouteAwareOptimizer(quality_weight=0.6, cost_weight=0.5)

    def test_estimate_tokens(self):
        """Test token estimation from examples."""
        optimizer = RouteAwareOptimizer()

        examples = [
            dspy.Example(input="test input 1", output="test output 1").with_inputs("input"),
            dspy.Example(input="test input 2", output="test output 2").with_inputs("input"),
        ]

        tokens = optimizer._estimate_tokens(examples)
        # Each example has ~14 chars input + ~15 chars output = ~29 chars
        # 2 examples = ~58 chars / 4 = ~14 tokens
        assert tokens > 0
        assert tokens < 100  # Reasonable estimate

    def test_normalize_score_best_available(self):
        """Test score normalization for Best Available route."""
        optimizer = RouteAwareOptimizer(quality_weight=0.7, cost_weight=0.3)

        # Quality 0.8, cost $0.01 (at baseline)
        score = optimizer._normalize_score(0.8, 0.01, ProviderRoute.BEST_AVAILABLE)
        # quality_score = 0.8, cost_score = 0.0 (at baseline)
        # score = 0.7 * 0.8 + 0.3 * 0.0 = 0.56
        assert abs(score - 0.56) < 0.01

    def test_normalize_score_modal_inference(self):
        """Test score normalization for Modal Inference route."""
        optimizer = RouteAwareOptimizer(quality_weight=0.7, cost_weight=0.3)

        # Quality 0.9, cost $0.0005 (half of baseline)
        score = optimizer._normalize_score(0.9, 0.0005, ProviderRoute.MODAL_INFERENCE)
        # quality_score = 0.9, cost_score = 0.5 (half baseline = 0.5)
        # score = 0.7 * 0.9 + 0.3 * 0.5 = 0.78
        assert abs(score - 0.78) < 0.01

    def test_suggest_route_changes_no_change(self):
        """Test route suggestion when no change needed."""
        optimizer = RouteAwareOptimizer()

        metrics = {
            "quality": 0.9,
            "cost_usd": 0.005,
            "latency_ms": 1000,
            "requires_schema": False,
        }

        suggestion = optimizer.suggest_route_changes(
            ProviderRoute.BEST_AVAILABLE,
            metrics,
        )

        # High quality, low cost - no change needed
        assert suggestion is None

    def test_suggest_route_changes_to_modal(self):
        """Test route suggestion to Modal when schema required."""
        optimizer = RouteAwareOptimizer()

        metrics = {
            "quality": 0.8,
            "cost_usd": 0.01,
            "latency_ms": 2000,
            "requires_schema": True,  # Forces Modal
        }

        suggestion = optimizer.suggest_route_changes(
            ProviderRoute.BEST_AVAILABLE,
            metrics,
        )

        assert suggestion == ProviderRoute.MODAL_INFERENCE

    @patch.object(DSPyOptimizer, "optimize")
    def test_optimize_with_routes_single_route(self, mock_optimize):
        """Test multi-route optimization with single route."""

        # Mock optimization result
        mock_result = OptimizationResult(
            optimized_pipeline=Mock(),
            metrics_before={"quality": 0.5, "n_evaluated": 1, "n_failed": 0},
            metrics_after={"quality": 0.9, "n_evaluated": 1, "n_failed": 0},
            route_used=ProviderRoute.BEST_AVAILABLE,
            optimizer_type="mipro",
            num_trials=10,
            duration_seconds=5.0,
            config={"optimizer_type": "mipro"},
        )
        mock_optimize.return_value = mock_result

        # Create optimizer
        optimizer = RouteAwareOptimizer()

        # Create mock examples
        examples = [
            dspy.Example(input="test", output="result").with_inputs("input"),
        ]

        # Run optimization
        result = optimizer.optimize_with_routes(
            pipeline=Mock(),
            examples=examples,
            routes=[ProviderRoute.BEST_AVAILABLE],
        )

        # Verify result
        assert isinstance(result, RouteOptimizationResult)
        assert result.recommended_route == ProviderRoute.BEST_AVAILABLE
        assert ProviderRoute.BEST_AVAILABLE in result.results_by_route
        assert "quality" in result.route_comparison
        assert "cost_usd" in result.route_comparison
        assert "normalized_score" in result.route_comparison

    @patch.object(DSPyOptimizer, "optimize")
    def test_optimize_with_routes_multi_route(self, mock_optimize):
        """Test multi-route optimization with multiple routes."""

        # Mock optimization results for different routes
        def mock_optimize_side_effect(pipeline, examples, route_strategy, **kwargs):
            if route_strategy == ProviderRoute.BEST_AVAILABLE:
                return OptimizationResult(
                    optimized_pipeline=Mock(),
                    metrics_before={"quality": 0.5, "n_evaluated": 1, "n_failed": 0},
                    metrics_after={"quality": 0.95, "n_evaluated": 1, "n_failed": 0},
                    route_used=ProviderRoute.BEST_AVAILABLE,
                    optimizer_type="mipro",
                    num_trials=10,
                    duration_seconds=3.0,
                    config={},
                )
            else:  # MODAL_INFERENCE
                return OptimizationResult(
                    optimized_pipeline=Mock(),
                    metrics_before={"quality": 0.5, "n_evaluated": 1, "n_failed": 0},
                    metrics_after={"quality": 0.85, "n_evaluated": 1, "n_failed": 0},
                    route_used=ProviderRoute.MODAL_INFERENCE,
                    optimizer_type="mipro",
                    num_trials=10,
                    duration_seconds=2.0,
                    config={},
                )

        mock_optimize.side_effect = mock_optimize_side_effect

        # Create optimizer
        optimizer = RouteAwareOptimizer()

        # Create mock examples
        examples = [
            dspy.Example(input="test", output="result").with_inputs("input"),
        ]

        # Run optimization
        result = optimizer.optimize_with_routes(
            pipeline=Mock(),
            examples=examples,
            routes=[ProviderRoute.BEST_AVAILABLE, ProviderRoute.MODAL_INFERENCE],
        )

        # Verify result
        assert isinstance(result, RouteOptimizationResult)
        assert len(result.results_by_route) == 2
        assert ProviderRoute.BEST_AVAILABLE in result.results_by_route
        assert ProviderRoute.MODAL_INFERENCE in result.results_by_route

        # Best Available should be recommended (higher quality despite higher cost)
        assert result.recommended_route == ProviderRoute.BEST_AVAILABLE

    def test_optimize_with_routes_empty_routes(self):
        """Test optimization with empty routes list raises error."""
        optimizer = RouteAwareOptimizer()

        with pytest.raises(ValueError, match="routes cannot be empty"):
            optimizer.optimize_with_routes(
                pipeline=Mock(),
                examples=[dspy.Example(input="test").with_inputs("input")],
                routes=[],
            )

    @patch.object(DSPyOptimizer, "optimize")
    def test_optimize_with_routes_failure_handling(self, mock_optimize):
        """Test handling of optimization failure for one route."""

        # Mock to fail for first route, succeed for second
        def mock_optimize_side_effect(pipeline, examples, route_strategy, **kwargs):
            if route_strategy == ProviderRoute.BEST_AVAILABLE:
                raise Exception("Optimization failed")
            else:
                return OptimizationResult(
                    optimized_pipeline=Mock(),
                    metrics_before={"quality": 0.5, "n_evaluated": 1, "n_failed": 0},
                    metrics_after={"quality": 0.8, "n_evaluated": 1, "n_failed": 0},
                    route_used=ProviderRoute.MODAL_INFERENCE,
                    optimizer_type="mipro",
                    num_trials=10,
                    duration_seconds=2.0,
                    config={},
                )

        mock_optimize.side_effect = mock_optimize_side_effect

        # Create optimizer
        optimizer = RouteAwareOptimizer()

        # Create mock examples
        examples = [
            dspy.Example(input="test", output="result").with_inputs("input"),
        ]

        # Run optimization - should continue despite one route failing
        result = optimizer.optimize_with_routes(
            pipeline=Mock(),
            examples=examples,
            routes=[ProviderRoute.BEST_AVAILABLE, ProviderRoute.MODAL_INFERENCE],
        )

        # Should recommend Modal (the one that succeeded)
        assert result.recommended_route == ProviderRoute.MODAL_INFERENCE
