"""Causal inference integration for lift-sys.

This package integrates DoWhy (https://github.com/py-why/dowhy) to provide
causal analysis capabilities for code understanding and test generation.

Core Components:
- CausalGraphBuilder (H20): Converts AST to causal DAG
- SCMFitter (H21): Fits structural causal models from code/traces
- InterventionEngine (H22): Processes "what if" queries
- CausalTestGenerator (H23): Generates tests for causal paths

DoWhy runs in a separate Python 3.11 venv (.venv-dowhy) due to cvxpy
incompatibility with Python 3.13. Communication via subprocess.

Usage:
    from lift_sys.causal import CausalGraphBuilder, SCMFitter, InterventionEngine

    # Build causal graph from AST
    builder = CausalGraphBuilder()
    causal_graph = builder.build(ast_tree, call_graph)

    # Fit structural causal model
    fitter = SCMFitter()
    scm = fitter.fit(causal_graph, traces=execution_data)

    # Estimate intervention impact
    engine = InterventionEngine()
    impact = engine.estimate_impact(scm, intervention={"function_x": new_value})

See:
- docs/research/DOWHY_TECHNICAL_REVIEW.md - Technical assessment
- docs/planning/DOWHY_INTEGRATION_SPEC.md - Integration design
- specs/typed-holes-dowhy.md - H20-H24 specifications
- plans/dowhy-execution-plan.md - Implementation roadmap
"""

__version__ = "0.1.0"
__author__ = "lift-sys team"

# Components will be imported here as they're implemented
# from .graph_builder import CausalGraphBuilder  # H20 (Week 1)
# from .scm_fitter import SCMFitter  # H21 (Week 2)
# from .intervention_engine import InterventionEngine, ImpactEstimate  # H22 (Week 3)
# from .test_generator import CausalTestGenerator, CausalPath, TestCase  # H23 (Weeks 5-7)

__all__ = [
    # Will be populated as components are implemented
]
