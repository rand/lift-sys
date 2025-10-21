"""Optimization module for lift-sys pipeline.

This module provides:
- Quality metrics (IR, code, end-to-end)
- Route-aware cost metrics (ADR 001)
- Metric aggregation and validation
- DSPy optimizer wrappers (MIPROv2, COPRO)
- Route-aware optimization (multi-provider)
"""

from lift_sys.optimization.metrics import (
    # Aggregation
    aggregate_metric,
    # Code quality metrics
    code_quality,
    code_test_pass_rate,
    constraint_match,
    # End-to-end metrics
    end_to_end,
    intent_match,
    # Core quality metrics
    ir_quality,
    latency_penalty,
    # Route-aware metrics (ADR 001)
    route_cost,
    route_cost_best_available,
    route_cost_modal_inference,
    route_quality,
    semantic_similarity,
    signature_match,
    structure_match,
    style_conformance,
    suggest_route_migration,
    syntax_correctness,
)
from lift_sys.optimization.optimizer import DSPyOptimizer, OptimizationResult
from lift_sys.optimization.route_optimizer import (
    RouteAwareOptimizer,
    RouteOptimizationResult,
)

__all__ = [
    # Core quality
    "ir_quality",
    "intent_match",
    "signature_match",
    "structure_match",
    "constraint_match",
    # Code quality
    "code_quality",
    "syntax_correctness",
    "code_test_pass_rate",
    "semantic_similarity",
    "style_conformance",
    # End-to-end
    "end_to_end",
    "latency_penalty",
    # Route-aware
    "route_cost",
    "route_cost_best_available",
    "route_cost_modal_inference",
    "route_quality",
    "suggest_route_migration",
    # Aggregation
    "aggregate_metric",
    # Optimizers (H8)
    "DSPyOptimizer",
    "OptimizationResult",
    "RouteAwareOptimizer",
    "RouteOptimizationResult",
]
