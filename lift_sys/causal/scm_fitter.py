"""H21: SCMFitter - Structural Causal Model Fitting.

This module fits causal mechanisms to graphs using static analysis
and/or dynamic execution traces.

See specs/typed-holes-dowhy.md for complete H21 specification.
"""

import networkx as nx
import pandas as pd

# DoWhy import will be via subprocess (Python 3.11 venv)
# from dowhy import gcm  # Not imported directly


class FittingError(Exception):
    """Base exception for SCM fitting errors."""

    pass


class ValidationError(FittingError):
    """Raised when fitted model fails validation."""

    pass


class DataError(FittingError):
    """Raised when trace data doesn't match graph."""

    pass


class SCMFitter:
    """Fits causal mechanisms to graph.

    Type Signature (H21):
        fit: (DiGraph, Optional[DataFrame], bool) → StructuralCausalModel

    Constraints:
        - If traces provided, R² MUST be ≥0.7
        - If static_only=True, MUST work without traces
        - Must complete in <10s for 1000 traces
        - Must validate with cross-validation

    Modes:
        1. Static Mode (static_only=True, traces=None):
           - Use code analysis for mechanism inference
           - Example: `def double(x): return x*2` → linear mechanism, coef=2

        2. Dynamic Mode (traces provided):
           - Fit mechanisms from data
           - Use DoWhy gcm.auto.assign_causal_mechanisms()
           - Cross-validate on 20% hold-out set

    Performance:
        - <10s for 1000 traces, 100 nodes
        - <1s for static mode (no traces)

    Implementation Steps (Week 2):
        - STEP-06: Static mechanism inference
        - STEP-07: Execution trace collection
        - STEP-08: Dynamic mechanism fitting
        - STEP-09: Cross-validation
    """

    def fit(
        self,
        causal_graph: nx.DiGraph,
        traces: pd.DataFrame | None = None,
        static_only: bool = False,
    ):  # -> gcm.StructuralCausalModel (type via subprocess)
        """Fit structural causal model.

        Args:
            causal_graph: Causal DAG from H20
            traces: Execution traces (columns = node names)
            static_only: Use static approximation if True

        Returns:
            Fitted StructuralCausalModel (DoWhy gcm.StructuralCausalModel)

        Raises:
            FittingError: If fitting fails
            ValidationError: If R² < threshold
            DataError: If traces don't match graph nodes

        Cross-Validation:
            - 80/20 train/test split
            - R² threshold: ≥0.7
            - Bootstrap confidence intervals
        """
        raise NotImplementedError("H21 not yet resolved (Week 2: STEP-06 to STEP-09)")
