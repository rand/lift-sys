"""DSPy optimizer wrapper for lift-sys pipeline optimization.

This module provides wrappers around DSPy's MIPROv2 and COPRO optimizers,
integrating them with lift-sys metrics (H10), route-aware optimization (ADR 001),
and execution history tracking (H11).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import dspy
from dspy.teleprompt import COPRO, MIPROv2

from lift_sys.dspy_signatures.provider_adapter import ProviderRoute
from lift_sys.optimization.metrics import aggregate_metric

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of a pipeline optimization run.

    Attributes:
        optimized_pipeline: The optimized DSPy module
        metrics_before: Metric scores before optimization
        metrics_after: Metric scores after optimization
        route_used: Provider route used during optimization (ADR 001)
        optimizer_type: Type of optimizer used ("mipro" or "copro")
        num_trials: Number of optimization trials run
        duration_seconds: Total optimization duration
        config: Optimizer configuration used
    """

    optimized_pipeline: dspy.Module
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    route_used: ProviderRoute
    optimizer_type: str
    num_trials: int
    duration_seconds: float
    config: dict[str, Any]


class DSPyOptimizer:
    """Wrapper around DSPy optimizers with lift-sys integration.

    This class wraps DSPy's MIPROv2 and COPRO optimizers, providing:
    - Integration with H10 optimization metrics
    - Route-aware optimization per ADR 001
    - Execution history tracking per H11
    - Before/after metric comparison

    Example:
        >>> from lift_sys.optimization import DSPyOptimizer
        >>> from lift_sys.optimization.metrics import end_to_end
        >>>
        >>> optimizer = DSPyOptimizer(
        ...     optimizer_type="mipro",
        ...     metric=end_to_end,
        ...     num_candidates=3,
        ...     init_temperature=1.4,
        ... )
        >>>
        >>> result = optimizer.optimize(
        ...     pipeline=my_pipeline,
        ...     examples=training_data,
        ...     route_strategy=ProviderRoute.BEST_AVAILABLE,
        ... )
        >>>
        >>> print(f"Improvement: {result.metrics_after['quality'] - result.metrics_before['quality']:.3f}")
    """

    def __init__(
        self,
        optimizer_type: str = "mipro",
        metric: Callable | None = None,
        **optimizer_kwargs,
    ):
        """Initialize optimizer wrapper.

        Args:
            optimizer_type: Type of optimizer to use ("mipro" or "copro")
            metric: Metric function from H10 (defaults to aggregate_metric)
            **optimizer_kwargs: Additional kwargs passed to DSPy optimizer
                For MIPROv2: num_candidates, init_temperature, num_trials, etc.
                For COPRO: breadth, depth, etc.

        Raises:
            ValueError: If optimizer_type is not "mipro" or "copro"
        """
        if optimizer_type not in ("mipro", "copro"):
            raise ValueError(f"optimizer_type must be 'mipro' or 'copro', got: {optimizer_type}")

        self.optimizer_type = optimizer_type
        self.metric = metric or self._default_metric()
        self.optimizer_kwargs = optimizer_kwargs

        # Get metric name safely (handle mocks and callables)
        metric_name = getattr(self.metric, "__name__", str(self.metric))
        logger.info(f"Initialized {optimizer_type.upper()} optimizer with metric={metric_name}")

    def optimize(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        route_strategy: ProviderRoute | None = None,
        validation_examples: list[dspy.Example] | None = None,
    ) -> OptimizationResult:
        """Optimize a DSPy pipeline using configured optimizer.

        This method:
        1. Configures provider route if specified (ADR 001)
        2. Evaluates baseline metrics
        3. Runs DSPy optimization (MIPROv2 or COPRO)
        4. Evaluates optimized metrics
        5. Tracks optimization run in execution history (H11)

        Args:
            pipeline: DSPy module to optimize
            examples: Training examples for optimization
            route_strategy: Provider route to use (ADR 001), defaults to BEST_AVAILABLE
            validation_examples: Optional validation set (defaults to using examples)

        Returns:
            OptimizationResult with optimized pipeline and metrics

        Raises:
            ValueError: If examples is empty
            RuntimeError: If optimization fails
        """
        if not examples:
            raise ValueError("examples cannot be empty")

        route = route_strategy or ProviderRoute.BEST_AVAILABLE
        validation_examples = validation_examples or examples

        logger.info(
            f"Starting optimization: type={self.optimizer_type}, "
            f"n_train={len(examples)}, n_val={len(validation_examples)}, "
            f"route={route.value}"
        )

        # Configure provider route (ADR 001)
        self._configure_route(route)

        # Evaluate baseline metrics
        start_time = datetime.now()
        metrics_before = self._evaluate_pipeline(pipeline, validation_examples)
        logger.info(f"Baseline metrics: {metrics_before}")

        # Initialize and run DSPy optimizer
        try:
            optimizer = self._create_optimizer()
            optimized_pipeline = optimizer.compile(
                student=pipeline,
                trainset=examples,
                **self._get_compile_kwargs(),
            )
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise RuntimeError(f"Optimization failed: {e}") from e

        # Evaluate optimized metrics
        metrics_after = self._evaluate_pipeline(optimized_pipeline, validation_examples)
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"Optimized metrics: {metrics_after}")
        logger.info(f"Optimization completed in {duration:.1f}s")

        # Track in execution history (H11)
        # TODO: Integrate with ExecutionHistory when available
        # execution_history.record_optimization(...)

        # Calculate number of trials run
        num_trials = self._get_num_trials()

        result = OptimizationResult(
            optimized_pipeline=optimized_pipeline,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            route_used=route,
            optimizer_type=self.optimizer_type,
            num_trials=num_trials,
            duration_seconds=duration,
            config=self._get_config(),
        )

        return result

    def _default_metric(self) -> Callable:
        """Get default metric function (H10 aggregate_metric)."""
        return aggregate_metric

    def _configure_route(self, route: ProviderRoute) -> None:
        """Configure provider adapter with specified route (ADR 001).

        Args:
            route: Provider route to configure
        """
        # TODO: Integrate with ProviderAdapter when route configuration is available
        # For now, this is a placeholder for future integration
        logger.debug(f"Configured route: {route.value}")

    def _create_optimizer(self) -> MIPROv2 | COPRO:
        """Create DSPy optimizer instance based on type.

        Returns:
            Initialized MIPROv2 or COPRO optimizer
        """
        if self.optimizer_type == "mipro":
            # MIPROv2 default configuration
            # Note: DSPy has 'auto' parameter that conflicts with manual settings
            # We disable auto to allow manual control
            return MIPROv2(
                metric=self.metric,
                auto=False,  # Disable auto to allow manual num_candidates/num_trials
                num_candidates=self.optimizer_kwargs.get("num_candidates", 3),
                init_temperature=self.optimizer_kwargs.get("init_temperature", 1.4),
            )
        else:  # copro
            # COPRO default configuration
            return COPRO(
                metric=self.metric,
                breadth=self.optimizer_kwargs.get("breadth", 10),
                depth=self.optimizer_kwargs.get("depth", 3),
            )

    def _get_compile_kwargs(self) -> dict[str, Any]:
        """Get kwargs for optimizer.compile() call.

        Returns:
            Dictionary of kwargs specific to optimizer type
        """
        if self.optimizer_type == "mipro":
            return {
                "num_trials": self.optimizer_kwargs.get("num_trials", 10),
            }
        else:  # copro
            # COPRO doesn't take num_trials in compile
            return {}

    def _get_num_trials(self) -> int:
        """Get number of trials that were run.

        Returns:
            Number of optimization trials
        """
        if self.optimizer_type == "mipro":
            return self.optimizer_kwargs.get("num_trials", 10)
        else:  # copro
            # COPRO trials = breadth * depth
            breadth = self.optimizer_kwargs.get("breadth", 10)
            depth = self.optimizer_kwargs.get("depth", 3)
            return breadth * depth

    def _get_config(self) -> dict[str, Any]:
        """Get optimizer configuration for result tracking.

        Returns:
            Dictionary of optimizer configuration
        """
        config = {
            "optimizer_type": self.optimizer_type,
            "metric": self.metric.__name__,
        }
        config.update(self.optimizer_kwargs)
        return config

    def _evaluate_pipeline(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
    ) -> dict[str, float]:
        """Evaluate pipeline on examples using configured metric.

        Args:
            pipeline: Pipeline to evaluate
            examples: Examples to evaluate on

        Returns:
            Dictionary of metric scores
        """
        # Run metric on each example and average
        scores = []
        for example in examples:
            try:
                # For DSPy examples, the metric typically takes (example, prediction, trace)
                # For initial evaluation, we run the pipeline and get prediction
                prediction = pipeline(**example.inputs())
                score = self.metric(example, prediction)
                scores.append(score)
            except Exception as e:
                logger.warning(f"Evaluation failed for example: {e}")
                scores.append(0.0)

        avg_score = sum(scores) / len(scores) if scores else 0.0

        return {
            "quality": avg_score,
            "n_evaluated": len(scores),
            "n_failed": len([s for s in scores if s == 0.0]),
        }


__all__ = ["DSPyOptimizer", "OptimizationResult"]
