"""CausalEnhancer - Orchestration layer for causal analysis integration.

This module provides the main integration point for adding causal analysis
capabilities to lift-sys reverse mode. It orchestrates the three core components:
- H20 (CausalGraphBuilder): AST → Causal DAG
- H21 (SCMFitter): Graph + Traces → Fitted SCM
- H22 (InterventionEngine): SCM + Intervention → Results

See docs/planning/WEEK4_DOWHY_INTEGRATION.md for complete design.
"""

import ast
import logging
from typing import Any

import networkx as nx
import pandas as pd

from lift_sys.ir.models import IntermediateRepresentation

from .graph_builder import CausalGraphBuilder, GraphBuildError
from .intervention_engine import InterventionEngine
from .scm_fitter import FittingError, SCMFitter

logger = logging.getLogger(__name__)


class CausalEnhancementError(Exception):
    """Base exception for causal enhancement errors."""

    pass


class CausalEnhancer:
    """Orchestrates causal analysis capabilities for reverse mode.

    This class integrates the three core causal components (H20-H22) and provides
    a high-level API for adding causal analysis to lifted code specifications.

    Architecture:
        IR + AST + Traces → CausalEnhancer → EnhancedIR
                               ↓
        ├─→ H20: CausalGraphBuilder (AST → DAG)
        ├─→ H21: SCMFitter (DAG + Traces → SCM)
        └─→ H22: InterventionEngine (SCM + Query → Results)

    Modes:
        - static: Use static analysis only (no execution traces required)
        - dynamic: Use execution traces for precise mechanism fitting
        - auto: Choose mode based on trace availability

    Usage:
        enhancer = CausalEnhancer()

        # Static mode (no traces)
        enhanced_ir = enhancer.enhance(
            ir=ir,
            ast_tree=ast_tree,
            mode="static"
        )

        # Dynamic mode (with traces)
        enhanced_ir = enhancer.enhance(
            ir=ir,
            ast_tree=ast_tree,
            traces=execution_traces,
            mode="dynamic"
        )

    Performance:
        - Static mode: <1s (no subprocess calls)
        - Dynamic mode: <10s for 1000 traces, 100 nodes

    Error Handling:
        - Graceful degradation: Returns base IR with warnings if causal fails
        - Circuit breaker: Prevents repeated DoWhy subprocess failures
        - Comprehensive logging: All failures logged with actionable context
    """

    def __init__(
        self,
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 3,
    ):
        """Initialize causal enhancer.

        Args:
            enable_circuit_breaker: Enable circuit breaker for DoWhy calls
            circuit_breaker_threshold: Number of failures before opening circuit
        """
        self.graph_builder = CausalGraphBuilder()
        self.scm_fitter = SCMFitter()
        self.intervention_engine = InterventionEngine()

        # Circuit breaker state (future enhancement)
        self.enable_circuit_breaker = enable_circuit_breaker
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_failures = 0
        self._circuit_breaker_open = False

    def enhance(
        self,
        ir: IntermediateRepresentation,
        ast_tree: ast.Module,
        call_graph: nx.DiGraph | None = None,
        traces: pd.DataFrame | None = None,
        mode: str = "auto",
        source_code: dict[str, str] | None = None,
    ) -> dict:
        """Add causal analysis capabilities to IR.

        Args:
            ir: Base IR from reverse mode
            ast_tree: Python AST for graph extraction
            call_graph: Optional call graph (if available from reverse mode)
            traces: Optional execution traces (columns = variable names)
            mode: "static", "dynamic", or "auto" (default)
            source_code: Optional dict of node_id → source code for static analysis

        Returns:
            Dict with causal data:
                {
                    "ir": IntermediateRepresentation,
                    "causal_graph": nx.DiGraph,
                    "scm": dict (fitted SCM from H21),
                    "intervention_engine": InterventionEngine,
                    "mode": str ("static" or "dynamic"),
                    "metadata": dict (timing, warnings, etc.)
                }

        Raises:
            CausalEnhancementError: If enhancement fails completely
                (Note: Partial failures result in warnings, not exceptions)

        Mode Selection:
            - "static": Use static analysis only (no traces required)
            - "dynamic": Use execution traces (requires traces parameter)
            - "auto": Use dynamic if traces available, else static

        Graceful Degradation:
            If causal analysis fails, returns IR with causal_graph=None and logs warning.
            Core lift-sys functionality is never blocked by causal failures.
        """
        metadata: dict[str, Any] = {"warnings": [], "mode": mode}

        # Check circuit breaker
        if self._circuit_breaker_open:
            logger.warning(
                f"Circuit breaker open: DoWhy subprocess unavailable "
                f"(failures: {self._circuit_breaker_failures})"
            )
            metadata["warnings"].append("causal_unavailable_circuit_breaker")
            return self._return_base_ir(ir, metadata)

        # Mode selection
        if mode == "auto":
            mode = "dynamic" if traces is not None else "static"
            metadata["mode"] = mode
            logger.info(f"Auto mode selected: {mode}")

        try:
            # STEP 1: Extract causal graph (H20)
            logger.info("Extracting causal graph from AST...")
            if call_graph is None:
                call_graph = nx.DiGraph()  # Empty call graph if not provided

            try:
                causal_graph = self.graph_builder.build(
                    ast_tree=ast_tree,
                    call_graph=call_graph,
                )
                logger.info(
                    f"Causal graph extracted: {len(causal_graph.nodes())} nodes, "
                    f"{len(causal_graph.edges())} edges"
                )
            except GraphBuildError as e:
                logger.warning(f"Graph extraction failed: {e}")
                metadata["warnings"].append("graph_extraction_failed")
                return self._return_base_ir(ir, metadata)

            # STEP 2: Fit SCM (H21)
            logger.info(f"Fitting SCM (mode={mode})...")
            try:
                if mode == "static":
                    scm = self.scm_fitter.fit(
                        causal_graph=causal_graph,
                        static_only=True,
                        source_code=source_code or {},
                    )
                elif mode == "dynamic":
                    if traces is None:
                        raise CausalEnhancementError("Dynamic mode requires execution traces")
                    scm = self.scm_fitter.fit(
                        causal_graph=causal_graph,
                        traces=traces,
                        static_only=False,
                    )
                else:
                    raise ValueError(
                        f"Invalid mode: {mode} (must be 'static', 'dynamic', or 'auto')"
                    )

                logger.info(f"SCM fitted successfully (mode={scm.get('mode')})")

            except FittingError as e:
                logger.warning(f"SCM fitting failed: {e}")
                metadata["warnings"].append("scm_fitting_failed")
                # Return graph but no SCM
                return {
                    "ir": ir,
                    "causal_graph": causal_graph,
                    "scm": None,
                    "intervention_engine": self.intervention_engine,
                    "mode": mode,
                    "metadata": metadata,
                }

            # Success! Return enhanced IR data
            return {
                "ir": ir,
                "causal_graph": causal_graph,
                "scm": scm,
                "intervention_engine": self.intervention_engine,
                "mode": mode,
                "metadata": metadata,
            }

        except Exception as e:
            # Unexpected error - log and increment circuit breaker
            logger.error(f"Causal enhancement failed unexpectedly: {e}", exc_info=True)

            if self.enable_circuit_breaker:
                self._circuit_breaker_failures += 1
                if self._circuit_breaker_failures >= self.circuit_breaker_threshold:
                    self._circuit_breaker_open = True
                    logger.error(
                        f"Circuit breaker opened after {self._circuit_breaker_failures} failures"
                    )

            metadata["warnings"].append("causal_enhancement_failed")
            return self._return_base_ir(ir, metadata)

    def _return_base_ir(
        self,
        ir: IntermediateRepresentation,
        metadata: dict,
    ) -> dict:
        """Return base IR without causal capabilities (graceful degradation).

        Args:
            ir: Base IR
            metadata: Metadata dict with warnings

        Returns:
            Dict with ir and None for causal components
        """
        return {
            "ir": ir,
            "causal_graph": None,
            "scm": None,
            "intervention_engine": None,
            "mode": None,
            "metadata": metadata,
        }

    def reset_circuit_breaker(self):
        """Reset circuit breaker state (for testing or manual recovery)."""
        self._circuit_breaker_failures = 0
        self._circuit_breaker_open = False
        logger.info("Circuit breaker reset")
