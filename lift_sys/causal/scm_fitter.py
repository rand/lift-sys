"""H21: SCMFitter - Structural Causal Model Fitting.

This module fits causal mechanisms to graphs using static analysis
and/or dynamic execution traces.

See specs/typed-holes-dowhy.md for complete H21 specification.
"""

import ast

import networkx as nx
import pandas as pd

from .static_inference import infer_mechanism

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
           - Implemented in STEP-06 ✅

        2. Dynamic Mode (traces provided):
           - Fit mechanisms from data
           - Use DoWhy gcm.auto.assign_causal_mechanisms()
           - Cross-validate on 20% hold-out set
           - Implementation: STEP-07, STEP-08, STEP-09 ⏳

    Performance:
        - <10s for 1000 traces, 100 nodes
        - <1s for static mode (no traces)

    Implementation Steps (Week 2):
        - STEP-06: Static mechanism inference ✅
        - STEP-07: Execution trace collection ⏳
        - STEP-08: Dynamic mechanism fitting ⏳
        - STEP-09: Cross-validation ⏳
    """

    def __init__(self):
        self.mechanisms: dict[str, dict] = {}  # node_id → mechanism info
        self.source_code: dict[str, str] = {}  # node_id → source code

    def fit(
        self,
        causal_graph: nx.DiGraph,
        traces: pd.DataFrame | None = None,
        static_only: bool = False,
        source_code: dict[str, str] | None = None,
    ):  # -> gcm.StructuralCausalModel (type via subprocess)
        """Fit structural causal model.

        Args:
            causal_graph: Causal DAG from H20
            traces: Execution traces (columns = node names)
            static_only: Use static approximation if True
            source_code: Optional dict of node_id → source code for static analysis

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
        if static_only or (traces is None and source_code):
            # STEP-06: Static mode ✅
            return self._fit_static(causal_graph, source_code or {})

        if traces is not None:
            # STEP-08: Dynamic mode ⏳
            raise NotImplementedError("Dynamic fitting (STEP-08) not yet implemented")

        raise FittingError("Must provide either traces or source_code for fitting")

    def _fit_static(self, causal_graph: nx.DiGraph, source_code: dict[str, str]) -> dict:
        """Fit mechanisms using static analysis (STEP-06).

        Args:
            causal_graph: Causal DAG
            source_code: Dict of node_id → source code

        Returns:
            Dict with fitted mechanisms (placeholder for DoWhy SCM)
        """
        mechanisms = {}

        for node_id in causal_graph.nodes():
            if node_id in source_code:
                code = source_code[node_id]
                try:
                    tree = ast.parse(code)
                    mechanism = infer_mechanism(tree)
                    mechanisms[node_id] = {
                        "type": mechanism.type.value,
                        "parameters": mechanism.parameters,
                        "confidence": mechanism.confidence,
                        "variables": mechanism.variables,
                        "expression": mechanism.expression,
                    }
                except SyntaxError:
                    # Invalid code, skip
                    continue

        self.mechanisms = mechanisms
        return {"mechanisms": mechanisms, "mode": "static", "graph": causal_graph}
