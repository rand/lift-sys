"""H21: SCMFitter - Structural Causal Model Fitting.

This module fits causal mechanisms to graphs using static analysis
and/or dynamic execution traces.

See specs/typed-holes-dowhy.md for complete H21 specification.
"""

import ast

import networkx as nx
import pandas as pd

from .dowhy_client import DoWhyClient, DoWhySubprocessError
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
            # STEP-08: Dynamic mode ✅
            return self._fit_dynamic(
                causal_graph,
                traces,
                quality="GOOD",
                r2_threshold=0.7,
            )

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

    def _fit_dynamic(
        self,
        causal_graph: nx.DiGraph,
        traces: pd.DataFrame,
        quality: str = "GOOD",
        r2_threshold: float = 0.7,
    ) -> dict:
        """Fit mechanisms using dynamic execution traces (STEP-08).

        Args:
            causal_graph: Causal DAG
            traces: Execution traces (DataFrame with columns = node names)
            quality: DoWhy quality setting ("GOOD", "BETTER", "BEST")
            r2_threshold: R² threshold for validation (default: 0.7)

        Returns:
            Dict with fitted model structure and validation results

        Raises:
            DataError: If traces don't match graph nodes
            ValidationError: If R² < threshold
            FittingError: If DoWhy subprocess fails
        """
        # Validate traces match graph
        graph_nodes = set(causal_graph.nodes())
        trace_columns = set(traces.columns)

        if graph_nodes != trace_columns:
            missing_in_traces = graph_nodes - trace_columns
            missing_in_graph = trace_columns - graph_nodes
            raise DataError(
                f"Graph nodes and trace columns do not match.\n"
                f"  Missing in traces: {missing_in_traces}\n"
                f"  Missing in graph: {missing_in_graph}"
            )

        # Initialize DoWhy client
        try:
            client = DoWhyClient(timeout=60.0)
        except FileNotFoundError as e:
            raise FittingError(
                f"DoWhy subprocess not available: {e}\n"
                f"Make sure .venv-dowhy exists and scripts/dowhy/fit_scm.py is present"
            )

        # Fit SCM using DoWhy subprocess
        try:
            result = client.fit_scm(
                graph=causal_graph,
                traces=traces,
                quality=quality,
                validate_r2=True,
                r2_threshold=r2_threshold,
                test_size=0.2,  # 80/20 train/test split
            )
        except DoWhySubprocessError as e:
            raise FittingError(f"DoWhy fitting failed: {e}")
        except Exception as e:
            raise FittingError(f"Unexpected error during DoWhy fitting: {e}")

        # Check validation status
        status = result.get("status")
        validation = result.get("validation", {})

        if status == "validation_failed":
            # R² below threshold
            mean_r2 = validation.get("mean_r2", 0.0)
            failed_nodes = validation.get("failed_nodes", [])
            raise ValidationError(
                f"Model validation failed: mean R²={mean_r2:.4f} "
                f"(threshold={r2_threshold})\n"
                f"Failed nodes: {failed_nodes}"
            )

        if status == "error":
            error_msg = result.get("error", "Unknown error")
            raise FittingError(f"DoWhy subprocess error: {error_msg}")

        # Store mechanisms for inspection
        scm_data = result.get("scm", {})
        self.mechanisms = scm_data.get("mechanisms", {})

        # Return full result including validation
        return {
            "mode": "dynamic",
            "graph": causal_graph,
            "scm": scm_data,
            "validation": validation,
            "metadata": result.get("metadata", {}),
            "status": status,
        }
