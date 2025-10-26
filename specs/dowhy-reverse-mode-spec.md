# DoWhy Reverse Mode Enhancement - Technical Specification

**Date**: 2025-10-25
**Status**: Draft v1.0
**Phase**: Phase 2 - Full Specification
**Priority**: P1 (HIGHEST VALUE)
**Parent**: DOWHY_INTEGRATION_SPEC.md

---

## Document Purpose

This document provides the **complete technical specification** for integrating DoWhy causal inference capabilities into lift-sys reverse mode.

**Scope**: Priority 1 only (Reverse Mode Enhancement)

**Out of Scope**: Test generation (P2), constraint validation (P3), semantic analysis (P4-P5)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Requirements](#2-requirements)
3. [Architecture](#3-architecture)
4. [Component Specifications](#4-component-specifications)
5. [Data Models](#5-data-models)
6. [API Design](#6-api-design)
7. [Dependencies](#7-dependencies)
8. [Test Plan](#8-test-plan)
9. [Acceptance Criteria](#9-acceptance-criteria)

---

## 1. Overview

### 1.1 Goal

Enable reverse mode to answer **causal questions** about code:
- "What code is affected if I change function X?"
- "Why did this function return value Y?"
- "What would happen if I refactor module Z?"

### 1.2 Approach

**Current Reverse Mode**: AST → Call Graph → IR (structural only)

**Enhanced Reverse Mode**: AST → Causal Graph → Fitted SCM → IR (causal + structural)

### 1.3 User Experience

**Before**:
```python
lifter = Lifter.from_repo("repo/")
ir = lifter.lift("main.py")
# ir.metadata contains: AST, call graph, signatures
```

**After**:
```python
lifter = Lifter.from_repo("repo/")
ir = lifter.lift("main.py", include_causal=True)

# New capability: Causal queries
affected = ir.causal_impact("validate_input")
# Returns: {'process_data': 0.85, 'generate_output': 0.72, ...}

intervention = ir.causal_intervention({'validate_input': True})
# Returns: Distribution of downstream outputs
```

### 1.4 Success Metrics

**Technical**:
- Causal graph accuracy: 90%+ correct edges
- SCM R²: > 0.7 (70% variance explained)
- Query latency: < 100ms per intervention
- Full analysis: < 30s for 100-file codebase

**User**:
- 50% time reduction in impact analysis
- 85%+ accuracy vs manual analysis
- User satisfaction: 8+/10

---

## 2. Requirements

### 2.1 Functional Requirements

**FR1: Causal Graph Construction**
- MUST convert AST + call graph → causal DAG
- MUST identify causal edges (exclude logging, I/O side effects)
- MUST handle cyclic dependencies gracefully
- MUST support multi-file analysis

**FR2: Causal Mechanism Fitting**
- MUST fit SCM from execution traces (when available)
- MUST support static-only mode (no traces)
- MUST use linear approximation for performance
- MUST validate fitted models (cross-validation R² > 0.7)

**FR3: Intervention Queries**
- MUST support "do(X=x)" interventions
- MUST estimate effect on all downstream nodes
- MUST return confidence intervals
- MUST handle multiple simultaneous interventions

**FR4: Counterfactual Queries**
- SHOULD support "what if X was different?" queries
- SHOULD work with execution traces
- MAY use approximations when exact answer unavailable

**FR5: IR Integration**
- MUST add causal_model field to IR
- MUST serialize/deserialize SCM to JSON
- MUST preserve existing IR functionality
- MUST be backward compatible (causal optional)

### 2.2 Non-Functional Requirements

**NFR1: Performance**
- Causal graph construction: < 1s for 100-file codebase
- SCM fitting: < 10s for 1000 traces
- Intervention query: < 100ms
- Memory: < 500MB for 1000-file codebase

**NFR2: Accuracy**
- Causal edge precision: 90%+
- Causal edge recall: 85%+
- SCM R²: > 0.7 (when traces available)
- Intervention predictions: 85%+ accuracy vs reality

**NFR3: Reliability**
- Graceful degradation (fall back to static if no traces)
- Handle missing data in traces
- Validate assumptions with sensitivity analysis
- No crashes on malformed code

**NFR4: Maintainability**
- 90%+ test coverage
- Type hints on all public APIs
- Comprehensive documentation
- Clear error messages

---

## 3. Architecture

### 3.1 System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        lift-sys                             │
│                                                             │
│  ┌──────────────┐                    ┌─────────────────┐   │
│  │  Forward     │                    │   Reverse       │   │
│  │  Mode        │                    │   Mode          │   │
│  │              │                    │                 │   │
│  │  NL → IR     │                    │  Code → IR      │   │
│  │     ↓        │                    │      ↓          │   │
│  │  IR → Code   │                    │  ┌──────────┐   │   │
│  └──────────────┘                    │  │ Causal   │   │   │
│                                      │  │ Analysis │◄──┼───┼─── DoWhy
│  ┌──────────────┐                    │  │ (NEW)    │   │   │   (Python 3.11)
│  │  Validation  │                    │  └──────────┘   │   │
│  │              │                    │      ↓          │   │
│  └──────────────┘                    │  Enhanced IR    │   │
│                                      └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Reverse Mode (Enhanced)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Lifter (existing)                                   │   │
│  │  - AST extraction                                    │   │
│  │  - Call graph construction                           │   │
│  │  - Signature extraction                              │   │
│  └─────────────┬────────────────────────────────────────┘   │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  CausalGraphBuilder (H20) ◄────── AST + Call Graph  │   │
│  │  - Identify causal edges                             │   │
│  │  - Prune non-causal dependencies                     │   │
│  │  - Build NetworkX DAG                                │   │
│  └─────────────┬────────────────────────────────────────┘   │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SCMFitter (H21) ◄────────────── Execution Traces   │   │
│  │  - Assign causal mechanisms                          │   │
│  │  - Fit mechanisms to data                            │   │
│  │  - Validate with cross-validation                    │   │
│  └─────────────┬────────────────────────────────────────┘   │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  InterventionEngine (H22)                            │   │
│  │  - Process intervention queries                      │   │
│  │  - Estimate downstream effects                       │   │
│  │  - Compute confidence intervals                      │   │
│  └─────────────┬────────────────────────────────────────┘   │
│                │                                             │
│                ▼                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Enhanced IR                                         │   │
│  │  - Structural metadata (existing)                    │   │
│  │  - Causal model (NEW)                                │   │
│  │  - Causal metadata (NEW)                             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 H20: CausalGraphBuilder

**Purpose**: Convert AST + call graph → causal DAG

**Type Signature**:
```python
class CausalGraphBuilder:
    def build(
        self,
        ast: ast.Module,
        call_graph: nx.DiGraph,
        control_flow: Optional[nx.DiGraph] = None
    ) -> nx.DiGraph:
        """Build causal graph from code structure.

        Args:
            ast: Python AST
            call_graph: Function call graph
            control_flow: Optional control flow graph

        Returns:
            Causal DAG (NetworkX DiGraph) with node types and edge types

        Raises:
            ValueError: If graph is cyclic (not a DAG)
            GraphBuildError: If construction fails
        """
```

**Node Types**:
- `function`: Function definition
- `variable`: Module-level variable or parameter
- `return`: Function return value
- `effect`: Side effect (I/O, state change)

**Edge Types**:
- `data_flow`: Data dependency (A produces data used by B)
- `control_flow`: Control dependency (A controls if B executes)
- `call`: Function call (A calls B)

**Edge Pruning Rules**:
1. **Exclude logging**: No edges to logging calls
2. **Exclude pure I/O**: No edges from I/O unless it affects computation
3. **Include state changes**: Include edges from state mutations
4. **Include conditional**: Include edges from control flow that affects data

**Algorithm**:
```
1. Initialize DAG
2. Add nodes:
   - For each function in AST: add function node
   - For each variable: add variable node
   - For each return: add return node
3. Add edges from call graph:
   - For each call (A → B): add call edge
4. Add data flow edges:
   - Analyze variable usage
   - Add edges from definitions to uses
5. Add control flow edges:
   - Analyze if/while/for statements
   - Add edges from condition to affected code
6. Prune non-causal edges:
   - Apply pruning rules
7. Validate DAG (no cycles)
8. Return causal graph
```

**Constraints**:
- MUST be acyclic (DAG)
- MUST have at least one root node (no incoming edges)
- MUST have at least one leaf node (no outgoing edges)
- Edge count should be O(N log N) where N = node count

**Testing**:
- Unit test: Simple function (linear data flow)
- Unit test: Conditional flow (if/else)
- Unit test: Loop (while/for)
- Integration test: Multi-function codebase
- Edge case: Recursive functions (should warn, not crash)
- Edge case: Circular imports (handle gracefully)

---

### 4.2 H21: SCMFitter

**Purpose**: Fit causal mechanisms from execution traces

**Type Signature**:
```python
from dowhy import gcm
import pandas as pd

class SCMFitter:
    def fit(
        self,
        causal_graph: nx.DiGraph,
        traces: Optional[pd.DataFrame] = None,
        static_only: bool = False
    ) -> gcm.StructuralCausalModel:
        """Fit structural causal model.

        Args:
            causal_graph: Causal DAG from H20
            traces: Execution traces (DataFrame with columns = node names)
            static_only: If True, use static approximation (no traces needed)

        Returns:
            Fitted StructuralCausalModel

        Raises:
            FittingError: If fitting fails
            ValidationError: If cross-validation R² < threshold
        """
```

**Static Mode (No Traces)**:
- Use linear approximation: Y = f(X) ≈ a*X + b
- Estimate coefficients from type hints and code structure
- Example: `def double(x: int) -> int: return x * 2` → a=2, b=0

**Dynamic Mode (With Traces)**:
- Use `gcm.auto.assign_causal_mechanisms()`
- Fit with `gcm.fit()`
- Prefer linear models for speed (unless R² < 0.7)

**Cross-Validation**:
- Split traces: 80% train, 20% validation
- Compute R² on validation set
- Require R² > 0.7 (otherwise warn user)

**Algorithm**:
```
1. Create StructuralCausalModel(causal_graph)
2. If static_only:
   a. For each node, infer mechanism from code
   b. Use linear approximation
3. Else (dynamic mode):
   a. Validate traces (columns match nodes)
   b. Auto-assign mechanisms
   c. Fit to traces
   d. Cross-validate
4. Return fitted SCM
```

**Constraints**:
- MUST handle missing data (drop rows or impute)
- MUST validate R² > 0.7 (configurable threshold)
- MUST complete in < 10s for 1000 traces
- SHOULD use linear models when possible (fast)

**Testing**:
- Unit test: Static mode (no traces)
- Unit test: Dynamic mode (with synthetic traces)
- Unit test: Cross-validation
- Integration test: Real codebase + traces
- Performance test: 1000 traces, 100 nodes (< 10s)

---

### 4.3 H22: InterventionEngine

**Purpose**: Process intervention queries and estimate effects

**Type Signature**:
```python
from typing import Any, Dict

@dataclass
class ImpactEstimate:
    """Result of causal intervention query."""
    affected_nodes: dict[str, float]  # node → effect size
    confidence_intervals: dict[str, tuple[float, float]]  # node → (low, high)
    sample_size: int
    intervention: dict[str, Any]

class InterventionEngine:
    def estimate_impact(
        self,
        scm: gcm.StructuralCausalModel,
        intervention: dict[str, Any],
        num_samples: int = 1000
    ) -> ImpactEstimate:
        """Estimate impact of intervention.

        Args:
            scm: Fitted structural causal model
            intervention: Dict mapping node names to intervention values
                         e.g., {'validate_input': True}
            num_samples: Number of samples for estimation

        Returns:
            Impact estimate with effect sizes and confidence intervals

        Raises:
            InterventionError: If intervention invalid
        """
```

**Effect Size Computation**:
1. Generate samples without intervention: `P(Y)`
2. Generate samples with intervention: `P(Y | do(X=x))`
3. Compute effect: `E[Y | do(X=x)] - E[Y]`
4. Standardize: `effect / std(Y)` (Cohen's d)

**Confidence Intervals**:
- Bootstrap: Resample 100 times
- Compute 95% CI: `[percentile(2.5), percentile(97.5)]`

**Algorithm**:
```
1. Validate intervention (nodes exist in SCM)
2. Generate baseline samples: P(Y)
3. Generate intervention samples: P(Y | do(X=x))
4. For each downstream node:
   a. Compute effect size
   b. Bootstrap confidence interval
5. Return ImpactEstimate
```

**Constraints**:
- MUST complete in < 100ms for simple queries
- MUST return confidence intervals
- SHOULD identify all downstream nodes automatically
- MAY cache results for repeated queries

**Testing**:
- Unit test: Single intervention
- Unit test: Multiple simultaneous interventions
- Unit test: Confidence interval coverage (95% nominal)
- Integration test: Complex graph (20+ nodes)
- Performance test: < 100ms per query

---

## 5. Data Models

### 5.1 Enhanced IR Schema

```python
from pydantic import BaseModel, Field
from typing import Optional
from dowhy import gcm
import networkx as nx

class CausalMetadata(BaseModel):
    """Metadata about fitted causal model."""

    graph_json: dict  # NetworkX graph serialized to JSON
    mechanism_types: dict[str, str]  # node → mechanism type
    fitted_at: datetime
    trace_count: int  # Number of traces used for fitting
    validation_r2: float  # Cross-validation R²
    static_only: bool  # True if no traces used

    class Config:
        frozen = True

class IR(BaseModel):
    """Enhanced IR with causal model (backward compatible)."""

    # Existing fields (unchanged)
    intent: str
    signature: Signature
    effects: tuple[Effect, ...]
    assertions: tuple[Assertion, ...]
    constraints: tuple[Constraint, ...]
    metadata: Optional[dict] = None

    # NEW: Causal model (optional)
    causal_model: Optional[dict] = None  # Serialized SCM
    causal_metadata: Optional[CausalMetadata] = None

    def get_causal_scm(self) -> Optional[gcm.StructuralCausalModel]:
        """Deserialize causal model."""
        if not self.causal_model:
            return None
        # Deserialize from JSON
        return deserialize_scm(self.causal_model)

    def estimate_impact(
        self,
        intervention: dict[str, Any],
        num_samples: int = 1000
    ) -> Optional[ImpactEstimate]:
        """Convenience method for causal queries."""
        scm = self.get_causal_scm()
        if not scm:
            return None
        engine = InterventionEngine()
        return engine.estimate_impact(scm, intervention, num_samples)
```

### 5.2 Serialization

**SCM → JSON**:
```python
def serialize_scm(scm: gcm.StructuralCausalModel) -> dict:
    """Serialize SCM to JSON-compatible dict."""
    return {
        'graph': nx.node_link_data(scm.graph),
        'mechanisms': {
            node: serialize_mechanism(mech)
            for node, mech in scm.causal_mechanism.items()
        }
    }

def deserialize_scm(data: dict) -> gcm.StructuralCausalModel:
    """Deserialize SCM from JSON dict."""
    graph = nx.node_link_graph(data['graph'])
    scm = gcm.StructuralCausalModel(graph)
    for node, mech_data in data['mechanisms'].items():
        mech = deserialize_mechanism(mech_data)
        scm.set_causal_mechanism(node, mech)
    return scm
```

---

## 6. API Design

### 6.1 Lifter API (Enhanced)

```python
class Lifter:
    """Enhanced Lifter with causal analysis."""

    def lift(
        self,
        module_path: str,
        *,
        include_causal: bool = False,
        traces: Optional[pd.DataFrame] = None,
        static_only: bool = False
    ) -> IR:
        """Lift code to IR with optional causal analysis.

        Args:
            module_path: Path to Python module
            include_causal: If True, perform causal analysis
            traces: Optional execution traces for fitting
            static_only: If True, use static approximation

        Returns:
            IR with optional causal model
        """
        # Existing logic
        ast_tree = self._parse_ast(module_path)
        call_graph = self._build_call_graph(ast_tree)
        ir = self._construct_ir(ast_tree, call_graph)

        # NEW: Causal analysis
        if include_causal:
            causal_graph = CausalGraphBuilder().build(
                ast_tree, call_graph
            )
            scm = SCMFitter().fit(
                causal_graph, traces, static_only
            )
            ir.causal_model = serialize_scm(scm)
            ir.causal_metadata = CausalMetadata(
                graph_json=nx.node_link_data(causal_graph),
                mechanism_types={...},
                fitted_at=datetime.now(),
                trace_count=len(traces) if traces else 0,
                validation_r2=compute_r2(scm, traces),
                static_only=static_only
            )

        return ir
```

### 6.2 Query API

```python
# Example usage
lifter = Lifter.from_repo("https://github.com/user/repo")

# Lift with causal analysis
ir = lifter.lift("main.py", include_causal=True, static_only=True)

# Query 1: Impact analysis
impact = ir.estimate_impact({'validate_input': True})
print(f"Affected nodes: {impact.affected_nodes}")
# Output: {'process_data': 0.85, 'generate_output': 0.72}

# Query 2: What if analysis
scm = ir.get_causal_scm()
samples = gcm.interventional_samples(
    scm,
    {'config_value': 100},
    num_samples_to_draw=500
)
print(f"Output distribution: {samples['output'].describe()}")
```

---

## 7. Dependencies

### 7.1 Internal Dependencies

- `lift_sys/reverse_mode/lifter.py` (MODIFY)
- `lift_sys/ir/models.py` (MODIFY - add causal fields)
- `networkx` (already in use)

### 7.2 External Dependencies

**DoWhy** (Python 3.11):
- `dowhy>=0.13`
- `pandas>=2.0`
- `numpy>=1.24`
- `scikit-learn>=1.3` (for cross-validation)

**Installation**:
```bash
# Separate venv for DoWhy (Python 3.11)
uv venv --python 3.11 .venv-dowhy
uv pip install --python .venv-dowhy/bin/python dowhy pandas numpy scikit-learn
```

### 7.3 Integration Strategy

**Option: Subprocess Communication**
- Run DoWhy analysis in separate Python 3.11 process
- Communicate via JSON over stdin/stdout
- Pros: No version conflicts
- Cons: ~100ms process startup overhead

**Implementation**:
```python
def run_causal_analysis(
    graph_json: dict,
    traces_json: Optional[dict]
) -> dict:
    """Run causal analysis in Python 3.11 subprocess."""
    result = subprocess.run(
        ['.venv-dowhy/bin/python', 'scripts/causal_worker.py'],
        input=json.dumps({'graph': graph_json, 'traces': traces_json}),
        capture_output=True,
        text=True,
        timeout=60
    )
    return json.loads(result.stdout)
```

---

## 8. Test Plan

### 8.1 Unit Tests

**H20: CausalGraphBuilder** (`tests/causal/test_graph_builder.py`):
- [ ] test_simple_linear_flow() - A → B → C
- [ ] test_branching_flow() - if/else statements
- [ ] test_loop_detection() - while/for loops
- [ ] test_function_calls() - A calls B
- [ ] test_edge_pruning() - Exclude logging calls
- [ ] test_cyclic_detection() - Should raise error
- [ ] test_multi_file() - Cross-file dependencies

**H21: SCMFitter** (`tests/causal/test_scm_fitter.py`):
- [ ] test_static_mode() - No traces, linear approximation
- [ ] test_dynamic_mode() - With synthetic traces
- [ ] test_cross_validation() - R² > 0.7
- [ ] test_missing_data() - Handle NaN in traces
- [ ] test_nonlinear_mechanism() - When R² low, try nonlinear

**H22: InterventionEngine** (`tests/causal/test_intervention.py`):
- [ ] test_single_intervention() - do(X=x)
- [ ] test_multiple_interventions() - do(X=x, Y=y)
- [ ] test_confidence_intervals() - Bootstrap 95% CI
- [ ] test_effect_size_computation() - Cohen's d
- [ ] test_performance() - < 100ms per query

### 8.2 Integration Tests

**End-to-End** (`tests/integration/test_causal_reverse_mode.py`):
- [ ] test_lift_with_causal_static() - No traces
- [ ] test_lift_with_causal_dynamic() - With traces
- [ ] test_serialization_roundtrip() - IR → JSON → IR
- [ ] test_query_after_deserialization() - Queries work after load

**Real Codebases** (`tests/integration/test_real_codebases.py`):
- [ ] test_small_codebase() - 10 files, validate accuracy
- [ ] test_medium_codebase() - 100 files, validate performance
- [ ] test_large_codebase() - 1000 files, validate scalability

### 8.3 Performance Tests

**Benchmarks** (`tests/performance/test_causal_performance.py`):
- [ ] benchmark_graph_building() - 100 files in < 1s
- [ ] benchmark_scm_fitting() - 1000 traces in < 10s
- [ ] benchmark_intervention_query() - < 100ms
- [ ] benchmark_end_to_end() - 100 files in < 30s

### 8.4 Validation Tests

**Accuracy** (`tests/validation/test_causal_accuracy.py`):
- [ ] test_edge_accuracy() - 90%+ precision/recall
- [ ] test_scm_r2() - R² > 0.7 on real data
- [ ] test_intervention_accuracy() - 85%+ vs ground truth

---

## 9. Acceptance Criteria

### 9.1 Functional

- [ ] **F1**: CausalGraphBuilder constructs valid DAG from AST
- [ ] **F2**: SCMFitter works in static-only mode (no traces)
- [ ] **F3**: SCMFitter fits from traces with R² > 0.7
- [ ] **F4**: InterventionEngine returns impact estimates
- [ ] **F5**: IR serialization/deserialization preserves causal model
- [ ] **F6**: Queries work on deserialized IR
- [ ] **F7**: Backward compatible (causal_model=None supported)

### 9.2 Performance

- [ ] **P1**: Graph building < 1s for 100 files
- [ ] **P2**: SCM fitting < 10s for 1000 traces
- [ ] **P3**: Intervention query < 100ms
- [ ] **P4**: End-to-end < 30s for 100 files
- [ ] **P5**: Memory < 500MB for 1000 files

### 9.3 Quality

- [ ] **Q1**: 90%+ test coverage (all components)
- [ ] **Q2**: All public APIs have type hints
- [ ] **Q3**: All public APIs documented (docstrings)
- [ ] **Q4**: Integration tests pass on 3 real codebases
- [ ] **Q5**: No critical bugs (P0/P1) in backlog

### 9.4 Accuracy

- [ ] **A1**: Causal edge precision > 90%
- [ ] **A2**: Causal edge recall > 85%
- [ ] **A3**: SCM R² > 0.7 (with traces)
- [ ] **A4**: Intervention predictions 85%+ accurate

### 9.5 User Experience

- [ ] **UX1**: API intuitive (< 5 min to first query)
- [ ] **UX2**: Error messages actionable
- [ ] **UX3**: Examples in documentation
- [ ] **UX4**: User satisfaction > 8/10

---

## 10. Timeline & Milestones

**Week 1**: H20 (CausalGraphBuilder)
- [ ] Day 1-2: Implementation
- [ ] Day 3: Unit tests
- [ ] Day 4: Integration tests
- [ ] Day 5: Documentation

**Week 2**: H21 (SCMFitter)
- [ ] Day 1-2: Static mode implementation
- [ ] Day 3: Dynamic mode + cross-validation
- [ ] Day 4: Unit tests
- [ ] Day 5: Integration tests

**Week 3**: H22 (InterventionEngine) + IR Integration
- [ ] Day 1-2: InterventionEngine implementation
- [ ] Day 3: IR schema modifications
- [ ] Day 4: Serialization/deserialization
- [ ] Day 5: End-to-end tests

**Week 4**: Testing & Documentation
- [ ] Day 1: Performance benchmarks
- [ ] Day 2: Accuracy validation
- [ ] Day 3: Real codebase testing
- [ ] Day 4: Documentation + examples
- [ ] Day 5: Code review + polish

**Total: 4 weeks (20 days)**

---

**Specification Status**: DRAFT v1.0
**Next Steps**: Review, iterate, implement H20
**Approval Required**: YES (stakeholder sign-off)
