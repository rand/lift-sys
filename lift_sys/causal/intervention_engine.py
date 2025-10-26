"""H22: InterventionEngine - Causal Query Processing.

This module processes "what if" intervention queries using fitted SCMs.

See specs/typed-holes-dowhy.md for complete H22 specification.
"""

from dataclasses import dataclass
from typing import Any

# DoWhy import will be via subprocess (Python 3.11 venv)
# from dowhy import gcm


class InterventionError(Exception):
    """Base exception for intervention errors."""

    pass


class NodeNotFoundError(InterventionError):
    """Raised when intervened node doesn't exist in graph."""

    pass


@dataclass
class ImpactEstimate:
    """Result of causal intervention.

    Attributes:
        affected_nodes: Mapping of node → effect size (standardized)
        confidence_intervals: Mapping of node → (lower, upper) 95% CI
        sample_size: Number of samples used for estimation
        intervention: Original intervention specification
    """

    affected_nodes: dict[str, float]  # node → effect size (Cohen's d)
    confidence_intervals: dict[str, tuple[float, float]]  # node → (2.5%, 97.5%)
    sample_size: int
    intervention: dict[str, Any]


class InterventionEngine:
    """Processes causal queries.

    Type Signature (H22):
        estimate_impact: (SCM, dict, int) → ImpactEstimate

    Constraints:
        - Must complete in <100ms
        - Confidence intervals MUST be 95% (bootstrap)
        - Effect sizes MUST be standardized (Cohen's d)
        - All downstream nodes MUST be included

    Performance:
        - <100ms for simple queries (single intervention, <10 downstream nodes)
        - <1s for complex queries (multiple interventions, >50 downstream nodes)

    Statistical Constraints:
        - Bootstrap iterations: 100 (for CI estimation)
        - CI coverage: 95% nominal
        - Effect size: (μ_intervention - μ_baseline) / σ_baseline

    Implementation Steps (Week 3):
        - STEP-10: Intervention API implementation
        - STEP-11: Confidence interval estimation
    """

    def estimate_impact(
        self,
        scm,  # gcm.StructuralCausalModel (via subprocess)
        intervention: dict[str, Any],
        num_samples: int = 1000,
    ) -> ImpactEstimate:
        """Estimate impact of intervention.

        Args:
            scm: Fitted SCM from H21
            intervention: Node → value mapping (e.g., {"function_x": 42})
            num_samples: Samples for estimation (default 1000)

        Returns:
            Impact estimate with effect sizes and confidence intervals

        Raises:
            InterventionError: If intervention invalid
            NodeNotFoundError: If intervened node doesn't exist

        Example:
            >>> impact = engine.estimate_impact(
            ...     scm,
            ...     intervention={"validate": None},  # Skip validation
            ...     num_samples=1000
            ... )
            >>> impact.affected_nodes
            {"process": -0.8, "result": -1.2}  # Large negative effect
            >>> impact.confidence_intervals
            {"process": (-1.0, -0.6), "result": (-1.5, -0.9)}
        """
        raise NotImplementedError("H22 not yet resolved (Week 3: STEP-10 to STEP-11)")
