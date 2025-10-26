"""Causal inference integration for lift-sys.

This package integrates DoWhy (https://github.com/py-why/dowhy) to provide
causal analysis capabilities for code understanding and test generation.

Core Components:
- CausalGraphBuilder (H20): Converts AST to causal DAG ✅
- SCMFitter (H21): Fits structural causal models from code/traces ✅
- InterventionEngine (H22): Processes "what if" queries ✅
- CausalEnhancer (Week 4): Orchestration layer for reverse mode ✅
- EnhancedIR (Week 4): IR with causal query methods ✅
- CausalTestGenerator (H23): Generates tests for causal paths (Future)

DoWhy runs in a separate Python 3.11 venv (.venv-dowhy) due to cvxpy
incompatibility with Python 3.13. Communication via subprocess.

Usage (Reverse Mode Integration):
    from lift_sys.causal import CausalEnhancer, EnhancedIR
    from lift_sys import Lifter

    # Initialize enhancer
    enhancer = CausalEnhancer()

    # Lift code and enhance with causal capabilities
    lifter = Lifter.from_repo("my_project/")
    ir = lifter.lift("main.py")

    # Add causal analysis
    result = enhancer.enhance(
        ir=ir,
        ast_tree=lifter.ast_tree,
        traces=execution_traces,  # Optional
        mode="auto"  # "static", "dynamic", or "auto"
    )

    # Create enhanced IR
    enhanced_ir = EnhancedIR.from_enhancement_result(result)

    # Query causal impact
    if enhanced_ir.has_causal_capabilities:
        affected = enhanced_ir.causal_impact("function_name")
        print(f"Downstream impact: {affected}")

        # Execute intervention
        result = enhanced_ir.causal_intervention({"var": 5.0})
        print(f"Result: {result.statistics}")

Direct Usage (Low-Level API):
    from lift_sys.causal import CausalGraphBuilder, SCMFitter, InterventionEngine

    # Build causal graph from AST
    builder = CausalGraphBuilder()
    causal_graph = builder.build(ast_tree, call_graph)

    # Fit structural causal model
    fitter = SCMFitter()
    scm = fitter.fit(causal_graph, traces=execution_data)

    # Execute intervention
    engine = InterventionEngine()
    result = engine.execute(scm, intervention={"x": 5.0}, graph=causal_graph)

See:
- docs/causal/CAUSAL_ANALYSIS_GUIDE.md - User guide with examples
- docs/causal/API_REFERENCE.md - Complete API documentation
- docs/planning/WEEK4_DOWHY_INTEGRATION.md - Integration architecture
- docs/research/DOWHY_TECHNICAL_REVIEW.md - Technical assessment
- specs/typed-holes-dowhy.md - H20-H24 specifications
"""

__version__ = "0.2.0"  # Week 4: Integration layer complete
__author__ = "lift-sys team"

# Core components (H20-H22) - Weeks 1-3 ✅
# Integration layer (Week 4) ✅
from .causal_enhancer import CausalEnhancementError, CausalEnhancer

# DoWhy client for subprocess communication
from .dowhy_client import DoWhyClient, DoWhySubprocessError
from .enhanced_ir import EnhancedIR
from .graph_builder import CausalGraphBuilder, CyclicGraphError, GraphBuildError
from .intervention_engine import (
    InterventionEngine,
    InterventionError,
    ParseError,
    ValidationError,
)
from .intervention_spec import (
    HardIntervention,
    InterventionResult,
    InterventionSpec,
    SoftIntervention,
)
from .scm_fitter import DataError, FittingError, SCMFitter

__all__ = [
    # Core components (H20-H22)
    "CausalGraphBuilder",
    "GraphBuildError",
    "CyclicGraphError",
    "SCMFitter",
    "FittingError",
    "ValidationError",
    "DataError",
    "InterventionEngine",
    "InterventionError",
    "ParseError",
    "InterventionSpec",
    "HardIntervention",
    "SoftIntervention",
    "InterventionResult",
    # Integration layer (Week 4)
    "CausalEnhancer",
    "CausalEnhancementError",
    "EnhancedIR",
    # DoWhy client
    "DoWhyClient",
    "DoWhySubprocessError",
]
