# lift-sys Causal Inference Integration

**Status**: Week 1 (STEP-01 complete, STEP-02+ in progress)
**DoWhy Version**: 0.13
**Python Requirement**: 3.11 (separate venv)

## Overview

This package integrates [DoWhy](https://github.com/py-why/dowhy) to provide causal analysis capabilities for code understanding, impact analysis, and test generation.

**Key Capabilities**:
- Convert code AST to causal DAG
- Fit structural causal models from static analysis or execution traces
- Answer "what if" questions (interventional queries)
- Generate tests targeting causally important code paths

## Architecture

```
lift_sys/causal/
├── __init__.py               # Package metadata
├── graph_builder.py          # H20: CausalGraphBuilder (Week 1)
├── scm_fitter.py             # H21: SCMFitter (Week 2)
├── intervention_engine.py    # H22: InterventionEngine (Week 3)
└── test_generator.py         # H23: CausalTestGenerator (Weeks 5-7)
```

## Python 3.11 Requirement

**Why separate venv?**
DoWhy depends on `cvxpy`, which doesn't support Python 3.13 yet. The main lift-sys project uses Python 3.13, so we maintain a separate Python 3.11 venv for DoWhy.

**Setup**:
```bash
# Create Python 3.11 venv (already done)
uv venv --python 3.11 .venv-dowhy

# Activate and install DoWhy
source .venv-dowhy/bin/activate
uv pip install dowhy pandas numpy

# Verify
python --version  # Should show Python 3.11.x
python -c "import dowhy; print(dowhy.__version__)"  # Should show 0.13
```

**Communication Pattern**:
The lift-sys codebase (Python 3.13) communicates with DoWhy (Python 3.11) via subprocess:
- Serialize causal graph/data to JSON
- Call `.venv-dowhy/bin/python script.py`
- Deserialize results from stdout
- Overhead: ~100ms per invocation (acceptable)

## Usage (When Implemented)

```python
from lift_sys.causal import CausalGraphBuilder, SCMFitter, InterventionEngine

# 1. Build causal graph from AST (H20)
builder = CausalGraphBuilder()
causal_graph = builder.build(ast_tree, call_graph)

# 2. Fit structural causal model (H21)
fitter = SCMFitter()
scm = fitter.fit(causal_graph, traces=execution_data)

# 3. Estimate intervention impact (H22)
engine = InterventionEngine()
impact = engine.estimate_impact(
    scm,
    intervention={"function_x": new_value},
    num_samples=1000
)

print(f"Affected nodes: {impact.affected_nodes}")
print(f"Confidence intervals: {impact.confidence_intervals}")
```

## Implementation Roadmap

**Week 1 (H20 - CausalGraphBuilder)**:
- ✅ STEP-01: Setup environment and package structure
- ⏳ STEP-02: Implement AST node extraction
- ⏳ STEP-03: Implement data flow edge extraction
- ⏳ STEP-04: Implement control flow edge extraction
- ⏳ STEP-05: Implement causal edge pruning

**Week 2 (H21 - SCMFitter)**:
- ⏳ STEP-06: Static mechanism inference
- ⏳ STEP-07: Execution trace collection
- ⏳ STEP-08: Dynamic SCM fitting
- ⏳ STEP-09: Cross-validation

**Week 3 (H22 - InterventionEngine + IR Integration)**:
- ⏳ STEP-10: Intervention API
- ⏳ STEP-11: Confidence intervals
- ⏳ STEP-12: IR schema extension
- ⏳ STEP-13: SCM serialization
- ⏳ STEP-14: Lifter integration

**Week 4 (Testing & Documentation)**:
- ⏳ STEP-15: Performance benchmarks
- ⏳ STEP-16: Accuracy validation
- ⏳ STEP-17: Real codebase testing
- ⏳ STEP-18: Documentation
- ⏳ STEP-19: Code review & polish

**Weeks 5-7 (H23 - CausalTestGenerator)**:
- ⏳ STEP-20 to STEP-31: Test generation implementation

## References

**Planning Documents**:
- [Technical Review](../../docs/research/DOWHY_TECHNICAL_REVIEW.md) - DoWhy assessment
- [Integration Spec](../../docs/planning/DOWHY_INTEGRATION_SPEC.md) - Design overview
- [Beads Roadmap](../../docs/planning/DOWHY_BEADS_ROADMAP.md) - Issue tracking

**Specifications**:
- [Typed Holes](../../specs/typed-holes-dowhy.md) - H20-H24 specifications
- [Reverse Mode Spec](../../specs/dowhy-reverse-mode-spec.md) - P1 details
- [Test Generation Spec](../../specs/dowhy-test-generation-spec.md) - P2 details

**Execution**:
- [Execution Plan](../../plans/dowhy-execution-plan.md) - 31 atomic steps

**Testing**:
- [Exploration Script](../../debug/dowhy_exploration.py) - Working demo

## Success Metrics

**Technical (P1)**:
- Causal graph accuracy: ≥90% precision, ≥85% recall
- SCM R²: ≥0.7 (with traces)
- Intervention query latency: <100ms
- End-to-end: <30s for 100-file codebase

**Technical (P2)**:
- Generated tests pass: ≥95% on original code
- Regression detection: ≥90% of introduced bugs
- Causal coverage improvement: ≥20% over baseline
- Test generation: <1s per test

## Development

**Run tests**:
```bash
# Unit tests (when implemented)
uv run pytest tests/causal/

# Integration tests
uv run pytest tests/integration/test_causal_*.py
```

**Beads Issues**: lift-sys-340 through lift-sys-370 (31 total)

**Current**: Week 1, STEP-01 complete
