"""Route-aware optimizer for multi-provider optimization (ADR 001).

This module provides route-aware optimization capabilities, allowing pipelines
to be optimized across different provider routes (Best Available vs Modal Inference)
and selecting the best route based on quality/cost tradeoffs.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

import dspy

from lift_sys.dspy_signatures.provider_adapter import ProviderRoute
from lift_sys.optimization.metrics import (
    route_cost_best_available,
    route_cost_modal_inference,
    suggest_route_migration,
)
from lift_sys.optimization.optimizer import DSPyOptimizer, OptimizationResult

logger = logging.getLogger(__name__)


@dataclass
class RouteOptimizationResult:
    """Result of multi-route optimization.

    Attributes:
        results_by_route: Optimization results for each route tested
        recommended_route: Best route based on quality/cost analysis
        route_comparison: Comparison metrics across routes
    """

    results_by_route: dict[ProviderRoute, OptimizationResult]
    recommended_route: ProviderRoute
    route_comparison: dict[str, dict[ProviderRoute, float]]


class RouteAwareOptimizer:
    """Optimizer with route switching support (ADR 001).

    This class extends DSPyOptimizer to support multi-route optimization,
    where the same pipeline is optimized using different provider routes
    and the best route is selected based on quality/cost tradeoffs.

    According to ADR 001:
    - BEST_AVAILABLE: Use best quality model (Anthropic/OpenAI/Google) for standard tasks
    - MODAL_INFERENCE: Use Modal inference system for constrained generation

    Example:
        >>> optimizer = RouteAwareOptimizer(
        ...     optimizer_type="mipro",
        ...     quality_weight=0.7,
        ...     cost_weight=0.3,
        ... )
        >>>
        >>> result = optimizer.optimize_with_routes(
        ...     pipeline=my_pipeline,
        ...     examples=training_data,
        ...     routes=[ProviderRoute.BEST_AVAILABLE, ProviderRoute.MODAL_INFERENCE],
        ... )
        >>>
        >>> print(f"Best route: {result.recommended_route.value}")
    """

    def __init__(
        self,
        optimizer_type: str = "mipro",
        metric: Callable | None = None,
        quality_weight: float = 0.7,
        cost_weight: float = 0.3,
        **optimizer_kwargs,
    ):
        """Initialize route-aware optimizer.

        Args:
            optimizer_type: Type of optimizer to use ("mipro" or "copro")
            metric: Metric function from H10 (defaults to aggregate_metric)
            quality_weight: Weight for quality in route selection (0.0-1.0)
            cost_weight: Weight for cost in route selection (0.0-1.0)
            **optimizer_kwargs: Additional kwargs passed to DSPy optimizer

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        if abs(quality_weight + cost_weight - 1.0) > 1e-6:
            raise ValueError(f"Weights must sum to 1.0, got {quality_weight + cost_weight}")

        self.quality_weight = quality_weight
        self.cost_weight = cost_weight
        self.base_optimizer = DSPyOptimizer(
            optimizer_type=optimizer_type,
            metric=metric,
            **optimizer_kwargs,
        )

        logger.info(
            f"Initialized RouteAwareOptimizer with quality_weight={quality_weight}, "
            f"cost_weight={cost_weight}"
        )

    def optimize_with_routes(
        self,
        pipeline: dspy.Module,
        examples: list[dspy.Example],
        routes: list[ProviderRoute] | None = None,
        validation_examples: list[dspy.Example] | None = None,
    ) -> RouteOptimizationResult:
        """Optimize pipeline for each route, return best.

        This method:
        1. For each route:
           - Configures provider adapter
           - Runs optimization
           - Evaluates with route_quality()
           - Tracks cost with route_cost()
        2. Selects best route based on quality/cost tradeoff
        3. Returns results per route with recommendation

        Args:
            pipeline: DSPy module to optimize
            examples: Training examples for optimization
            routes: List of routes to test (defaults to both routes)
            validation_examples: Optional validation set

        Returns:
            RouteOptimizationResult with per-route results and recommendation

        Raises:
            ValueError: If routes is empty
        """
        # Set default routes if None, but validate if empty list
        if routes is None:
            routes = [ProviderRoute.BEST_AVAILABLE, ProviderRoute.MODAL_INFERENCE]
        elif not routes:  # Empty list check
            raise ValueError("routes cannot be empty")

        logger.info(f"Starting multi-route optimization for routes: {[r.value for r in routes]}")

        results_by_route = {}
        route_metrics = {}

        # Optimize for each route
        for route in routes:
            logger.info(f"Optimizing for route: {route.value}")

            try:
                result = self.base_optimizer.optimize(
                    pipeline=pipeline,
                    examples=examples,
                    route_strategy=route,
                    validation_examples=validation_examples,
                )

                results_by_route[route] = result

                # Calculate route-specific metrics
                quality = result.metrics_after["quality"]

                # Estimate cost based on route
                if route == ProviderRoute.BEST_AVAILABLE:
                    # Estimate tokens based on examples
                    estimated_tokens = self._estimate_tokens(examples)
                    cost = route_cost_best_available(estimated_tokens)
                else:  # MODAL_INFERENCE
                    # Use actual duration from optimization
                    duration_ms = result.duration_seconds * 1000
                    cost = route_cost_modal_inference(duration_ms)

                route_metrics[route] = {
                    "quality": quality,
                    "cost_usd": cost,
                    "normalized_score": self._normalize_score(quality, cost, route),
                }

                logger.info(
                    f"Route {route.value}: quality={quality:.3f}, cost=${cost:.4f}, "
                    f"score={route_metrics[route]['normalized_score']:.3f}"
                )

            except Exception as e:
                logger.error(f"Optimization failed for route {route.value}: {e}")
                # Continue with other routes
                route_metrics[route] = {
                    "quality": 0.0,
                    "cost_usd": float("inf"),
                    "normalized_score": 0.0,
                }

        # Select best route based on normalized scores
        recommended_route = max(route_metrics.items(), key=lambda x: x[1]["normalized_score"])[0]

        logger.info(f"Recommended route: {recommended_route.value}")

        # Prepare comparison metrics
        route_comparison = {
            "quality": {r: m["quality"] for r, m in route_metrics.items()},
            "cost_usd": {r: m["cost_usd"] for r, m in route_metrics.items()},
            "normalized_score": {r: m["normalized_score"] for r, m in route_metrics.items()},
        }

        return RouteOptimizationResult(
            results_by_route=results_by_route,
            recommended_route=recommended_route,
            route_comparison=route_comparison,
        )

    def suggest_route_changes(
        self,
        current_route: ProviderRoute,
        metrics: dict[str, float],
    ) -> ProviderRoute | None:
        """Suggest route migrations based on metrics.

        This method uses H10's suggest_route_migration() to determine if
        switching routes would improve quality/cost tradeoff.

        Args:
            current_route: Current provider route
            metrics: Metrics dictionary with keys:
                - quality: Quality score [0.0, 1.0]
                - cost_usd: Cost in USD
                - latency_ms: Latency in milliseconds
                - requires_schema: Whether task requires schema/grammar support

        Returns:
            Suggested route if migration recommended, None otherwise
        """
        suggestion = suggest_route_migration(current_route, metrics)

        if suggestion and suggestion != current_route:
            logger.info(f"Route migration suggested: {current_route.value} → {suggestion.value}")
            return suggestion

        logger.debug(f"No route migration needed for {current_route.value}")
        return None

    def _estimate_tokens(self, examples: list[dspy.Example]) -> int:
        """Estimate total tokens for examples.

        Uses rough heuristic: ~4 chars per token.

        Args:
            examples: Examples to estimate tokens for

        Returns:
            Estimated token count
        """
        total_chars = 0
        for example in examples:
            # Estimate characters from example inputs/outputs
            for _key, value in example.inputs().items():
                total_chars += len(str(value))
            if hasattr(example, "outputs"):
                for _key, value in example.outputs().items():
                    total_chars += len(str(value))

        # Rough heuristic: ~4 chars per token
        estimated_tokens = total_chars // 4
        logger.debug(f"Estimated {estimated_tokens} tokens for {len(examples)} examples")
        return estimated_tokens

    def _normalize_score(
        self,
        quality: float,
        cost: float,
        route: ProviderRoute,
    ) -> float:
        """Normalize quality and cost into a single score.

        Uses weighted combination with normalization:
        - Quality: [0.0, 1.0] (already normalized)
        - Cost: Normalized by route-specific baseline

        Args:
            quality: Quality score [0.0, 1.0]
            cost: Cost in USD
            route: Provider route (for cost normalization)

        Returns:
            Normalized score [0.0, 1.0]
        """
        # Normalize cost based on route
        if route == ProviderRoute.BEST_AVAILABLE:
            # Baseline: $0.01 per request (typical Claude API cost)
            cost_baseline = 0.01
        else:  # MODAL_INFERENCE
            # Baseline: $0.001 per request (typical Modal cost)
            cost_baseline = 0.001

        # Invert cost so lower cost = higher score
        cost_score = max(0.0, 1.0 - (cost / cost_baseline))

        # Weighted combination
        score = self.quality_weight * quality + self.cost_weight * cost_score

        return score


__all__ = ["RouteAwareOptimizer", "RouteOptimizationResult"]
