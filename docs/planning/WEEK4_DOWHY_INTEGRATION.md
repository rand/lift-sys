# Week 4: DoWhy Integration Layer

**Date**: 2025-10-26
**Status**: Planning
**Phase**: P1 - DoWhy Reverse Mode Enhancement
**Dependencies**: Week 1-3 Complete (H20, H21, H22)

---

## Overview

Week 4 focuses on **integrating** the foundational DoWhy components (H20-H22) into the lift-sys reverse mode system, creating a seamless user experience for causal queries.

### What We Built (Weeks 1-3)
- ✅ **H20 (CausalGraphExtractor)**: AST → Causal DAG conversion
- ✅ **H21 (SCMFitter)**: Static + dynamic mechanism fitting
- ✅ **H22 (InterventionEngine)**: Intervention queries with <100ms latency

### What We're Building (Week 4)
- **Integration Layer**: Connect H20-H22 into reverse mode pipeline
- **Causal Query API**: User-facing interface for causal questions
- **End-to-End Tests**: Full pipeline validation
- **Documentation**: User guide for causal capabilities

---

## User Experience Goals

### Before (Current Reverse Mode)
```python
lifter = Lifter.from_repo("repo/")
ir = lifter.lift("main.py")
# ir contains: AST, call graph, type signatures
```

### After (Week 4 Target)
```python
lifter = Lifter.from_repo("repo/")
ir = lifter.lift("main.py", include_causal=True)

# NEW: Causal impact analysis
affected = ir.causal_impact("validate_input")
# Returns: {'process_data': 0.85, 'generate_output': 0.72, ...}

# NEW: Intervention queries
intervention = ir.causal_intervention({'validate_input': True})
# Returns: InterventionResult with samples + statistics

# NEW: Causal graph access
graph = ir.causal_graph
# Returns: nx.DiGraph with causal edges
```

---

## Architecture

### Component: CausalEnhancer

**Purpose**: Orchestrates H20-H22 to add causal capabilities to existing IR.

```python
class CausalEnhancer:
    """Adds causal analysis capabilities to reverse mode."""

    def __init__(self):
        self.graph_extractor = CausalGraphExtractor()
        self.scm_fitter = SCMFitter()
        self.intervention_engine = InterventionEngine()

    def enhance(
        self,
        ir: IR,
        traces: Optional[pd.DataFrame] = None,
        mode: str = "auto"
    ) -> EnhancedIR:
        """Add causal capabilities to IR.

        Args:
            ir: Base IR from reverse mode
            traces: Optional execution traces
            mode: "static", "dynamic", or "auto"

        Returns:
            EnhancedIR with causal query methods
        """
        # 1. Extract causal graph (H20)
        graph = self.graph_extractor.extract(ir)

        # 2. Fit SCM (H21)
        if traces is not None or mode == "dynamic":
            scm = self.scm_fitter.fit(graph, traces=traces)
        else:
            scm = self.scm_fitter.fit(
                graph,
                static_only=True,
                source_code=ir.get_source_code()
            )

        # 3. Return enhanced IR
        return EnhancedIR(
            base_ir=ir,
            causal_graph=graph,
            scm=scm,
            intervention_engine=self.intervention_engine
        )


class EnhancedIR:
    """IR with causal query capabilities."""

    def causal_impact(self, node: str) -> dict[str, float]:
        """Get causal impact scores for downstream nodes."""
        pass

    def causal_intervention(
        self,
        interventions: dict[str, Any]
    ) -> InterventionResult:
        """Execute causal intervention query."""
        return self.intervention_engine.execute(
            self.scm,
            interventions,
            self.causal_graph
        )

    @property
    def causal_graph(self) -> nx.DiGraph:
        """Access causal graph."""
        return self._graph
```

---

## Week 4 Implementation Plan

### STEP-14: CausalEnhancer Implementation
**Goal**: Create orchestration layer for H20-H22

**Tasks**:
- [ ] Implement `CausalEnhancer` class
- [ ] Implement `EnhancedIR` class with causal methods
- [ ] Add `include_causal` parameter to `Lifter.lift()`
- [ ] Handle mode selection (static/dynamic/auto)
- [ ] Error handling and fallbacks

**Tests**:
- [ ] Unit tests for CausalEnhancer
- [ ] Integration tests with existing reverse mode
- [ ] Mode selection logic tests

**Acceptance Criteria**:
- [ ] `Lifter.lift(..., include_causal=True)` works
- [ ] Returns EnhancedIR with causal methods
- [ ] Graceful degradation if DoWhy unavailable

---

### STEP-15: Causal Query API
**Goal**: Implement user-facing query methods

**Tasks**:
- [ ] Implement `EnhancedIR.causal_impact()`
- [ ] Implement `EnhancedIR.causal_intervention()`
- [ ] Implement `EnhancedIR.causal_graph` property
- [ ] Add `EnhancedIR.causal_paths()` (high-importance paths)
- [ ] Add visualization helpers (optional)

**Tests**:
- [ ] Test causal_impact() with known graphs
- [ ] Test causal_intervention() with various formats
- [ ] Test graph property access
- [ ] Test error cases (invalid nodes, etc.)

**Acceptance Criteria**:
- [ ] All query methods functional
- [ ] Results match expected causal behavior
- [ ] Clear error messages for invalid queries

---

### STEP-16: End-to-End Integration Tests
**Goal**: Validate complete pipeline from code → causal queries

**Tasks**:
- [ ] Create test repositories (small codebases)
- [ ] Test: code → graph → scm → intervention
- [ ] Test: static mode (no traces)
- [ ] Test: dynamic mode (with traces)
- [ ] Test: mode auto-selection
- [ ] Test: multi-file codebases
- [ ] Test: error propagation

**Tests**:
- [ ] 5+ complete pipeline tests
- [ ] Performance benchmarks (<30s for 100 files)
- [ ] Memory usage tests

**Acceptance Criteria**:
- [ ] All E2E tests passing
- [ ] Performance requirements met
- [ ] No memory leaks

---

### STEP-17: Documentation
**Goal**: User-facing documentation for causal capabilities

**Tasks**:
- [ ] Write "Causal Analysis Guide"
- [ ] Write "API Reference" for causal methods
- [ ] Create example notebooks
- [ ] Add docstrings to all public APIs
- [ ] Update main README with causal features

**Deliverables**:
- [ ] `docs/causal/CAUSAL_ANALYSIS_GUIDE.md`
- [ ] `docs/causal/API_REFERENCE.md`
- [ ] `examples/causal_queries.ipynb`

**Acceptance Criteria**:
- [ ] Complete documentation coverage
- [ ] Runnable examples
- [ ] Clear user guidance

---

## Parallelization Strategy

### Main Thread (This Session)
- Design `CausalEnhancer` architecture (STEP-14)
- Implement core integration logic
- Create basic API structure (STEP-15)

### Sub-Agent 1: Integration Research
**Task**: Research best practices for integrating causal analysis into existing systems
**Deliverables**:
- Survey of integration patterns
- Recommendations for lift-sys integration
- Error handling strategies

### Sub-Agent 2: E2E Test Design
**Task**: Design comprehensive end-to-end test scenarios
**Deliverables**:
- Test scenario descriptions
- Test repository structures
- Expected behaviors and assertions

### Sub-Agent 3: Documentation Structure
**Task**: Create documentation outline and examples
**Deliverables**:
- Documentation structure
- Example code snippets
- User story scenarios

---

## Success Criteria (Week 4)

### Functional
- [ ] `Lifter.lift(..., include_causal=True)` works end-to-end
- [ ] All causal query methods functional
- [ ] Static and dynamic modes both working
- [ ] Error handling graceful and informative

### Performance
- [ ] Graph extraction: <5s for 100-file repo
- [ ] SCM fitting: <10s for 1000 traces
- [ ] Intervention queries: <100ms (from Week 3)
- [ ] Full analysis: <30s for 100-file repo

### Quality
- [ ] 90%+ test coverage for new code
- [ ] All E2E tests passing
- [ ] No regressions in existing reverse mode
- [ ] Complete documentation

### User Experience
- [ ] Clear, intuitive API
- [ ] Helpful error messages
- [ ] Working examples
- [ ] < 10 lines of code for basic queries

---

## Timeline

**Day 1-2**: STEP-14 (CausalEnhancer implementation)
**Day 3-4**: STEP-15 (Query API implementation)
**Day 5-6**: STEP-16 (E2E tests + performance tuning)
**Day 7**: STEP-17 (Documentation + polish)

**Total**: 7 days (parallel with sub-agents)

---

## Next Steps (After Week 4)

### P1 Complete ✅
After Week 4, P1 (DoWhy Reverse Mode Enhancement) is complete:
- H20-H22 implemented and tested
- Integration layer functional
- User-facing API available
- Fully documented

### Future Work (P2+)
- **P2**: CausalTestGenerator (H23) - Test generation from causal graphs
- **P3**: CausalValidator (H24) - Validate refactoring preserves causality
- **P4-P5**: Semantic analysis integration (longer-term)

---

## Dependencies

### Internal
- ✅ H20 (CausalGraphExtractor) - Week 1
- ✅ H21 (SCMFitter) - Week 2
- ✅ H22 (InterventionEngine) - Week 3
- Existing reverse mode infrastructure

### External
- DoWhy (Python 3.11 subprocess)
- NetworkX (graph operations)
- Pandas (trace data)

### Risks
- **DoWhy availability**: Mitigated by graceful degradation
- **Performance**: Mitigated by static mode fallback
- **Integration complexity**: Mitigated by clear separation of concerns

---

## Notes

- Keep integration layer thin - delegate to H20-H22
- Prioritize user experience over internal elegance
- Document all failure modes
- Performance is critical - cache aggressively
- Make `include_causal=False` the safe default
