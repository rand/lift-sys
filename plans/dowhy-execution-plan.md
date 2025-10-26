# DoWhy Integration - Execution Plan

**Date**: 2025-10-25
**Status**: Complete
**Phase**: Phase 3 - Execution Plan
**Parent**: DOWHY_INTEGRATION_SPEC.md

---

## Document Purpose

This document breaks down DoWhy integration into **atomic, executable steps** with clear dependencies, estimates, and success criteria.

**Total Duration**: 7 weeks (35 days) for P1-P2

---

## Execution Methodology

**Approach**: Design by Typed Holes
- Each step resolves part of a typed hole
- Steps are atomic (completable in ≤1 day)
- Each step has clear acceptance criteria
- Dependencies are explicit

**Tracking**: Via Beads issues (bd tool)

---

## Phase 1: Reverse Mode Enhancement (Weeks 1-4, P1)

### Week 1: H20 - CausalGraphBuilder

**STEP-01: Setup DoWhy Environment** (1 day)
- **ID**: dowhy-001
- **Type**: Infrastructure
- **Complexity**: S
- **Dependencies**: None
- **Tasks**:
  1. Verify Python 3.11 venv exists (`.venv-dowhy`)
  2. Add DoWhy to optional dependencies in `pyproject.toml`
  3. Create `lift_sys/causal/__init__.py`
  4. Create basic package structure
- **Acceptance Criteria**:
  - [ ] DoWhy importable in Python 3.11 venv
  - [ ] Package structure created
  - [ ] No import errors
- **Risks**: None (infrastructure only)

**STEP-02: AST Node Extractor** (1 day)
- **ID**: dowhy-002
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-001
- **Tasks**:
  1. Create `lift_sys/causal/graph_builder.py`
  2. Implement `extract_nodes(ast: ast.Module) -> list[Node]`
  3. Extract: functions, variables, returns
  4. Add node type metadata
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Extracts all functions from AST
  - [ ] Extracts module-level variables
  - [ ] Adds type metadata ('function', 'variable', 'return')
  - [ ] Unit tests pass (90%+ coverage)
- **Risks**: MEDIUM (AST complexity)

**STEP-03: Data Flow Edge Extractor** (1 day)
- **ID**: dowhy-003
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-002
- **Tasks**:
  1. Implement `extract_data_flow(ast) -> list[Edge]`
  2. Analyze variable definitions and uses
  3. Track assignments and references
  4. Create edges: definition → use
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Detects variable assignments
  - [ ] Tracks variable uses
  - [ ] Creates correct data flow edges
  - [ ] Handles nested scopes
  - [ ] Unit tests pass
- **Risks**: HIGH (scope analysis is complex)

**STEP-04: Control Flow Edge Extractor** (1 day)
- **ID**: dowhy-004
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-002
- **Tasks**:
  1. Implement `extract_control_flow(ast) -> list[Edge]`
  2. Analyze if/while/for statements
  3. Create edges: condition → affected code
  4. Write unit tests
- **Acceptance Criteria**:
  - [ ] Detects conditionals (if/else)
  - [ ] Detects loops (while/for)
  - [ ] Creates control flow edges
  - [ ] Unit tests pass
- **Risks**: MEDIUM (control flow analysis)

**STEP-05: Edge Pruning Logic** (1 day)
- **ID**: dowhy-005
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-003, dowhy-004
- **Tasks**:
  1. Implement `prune_non_causal_edges(graph) -> DiGraph`
  2. Exclude logging calls
  3. Exclude pure I/O (unless affects data)
  4. Keep state mutations
  5. Write unit tests + property tests
- **Acceptance Criteria**:
  - [ ] Removes logging edges
  - [ ] Keeps state-affecting edges
  - [ ] Property test: Output is DAG
  - [ ] Unit tests pass
- **Risks**: LOW (heuristic-based)

### Week 2: H21 - SCMFitter

**STEP-06: Static Mechanism Inference** (1.5 days)
- **ID**: dowhy-006
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-005
- **Tasks**:
  1. Create `lift_sys/causal/scm_fitter.py`
  2. Implement `infer_static_mechanism(node, ast) -> Mechanism`
  3. Linear approximation for simple functions
  4. Example: `f(x) = 2*x` → LinearMechanism(coef=2)
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Infers linear mechanisms from code
  - [ ] Handles simple arithmetic
  - [ ] Returns valid DoWhy mechanisms
  - [ ] Unit tests pass
- **Risks**: MEDIUM (limited to simple cases)

**STEP-07: Execution Trace Collection** (1 day)
- **ID**: dowhy-007
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-006
- **Tasks**:
  1. Create `lift_sys/causal/trace_collector.py`
  2. Implement instrumentation for tracing
  3. Capture variable values during execution
  4. Format as pandas DataFrame
  5. Write integration test
- **Acceptance Criteria**:
  - [ ] Instruments code for tracing
  - [ ] Collects variable values
  - [ ] Returns DataFrame with correct schema
  - [ ] Integration test passes
- **Risks**: HIGH (runtime instrumentation)

**STEP-08: Dynamic Mechanism Fitting** (1.5 days)
- **ID**: dowhy-008
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-007
- **Tasks**:
  1. Implement `fit_dynamic_mechanism(graph, traces) -> SCM`
  2. Use `gcm.auto.assign_causal_mechanisms()`
  3. Call `gcm.fit()`
  4. Write integration test with synthetic traces
- **Acceptance Criteria**:
  - [ ] Fits SCM from traces
  - [ ] Uses DoWhy auto-assignment
  - [ ] Returns fitted SCM
  - [ ] Integration test passes
- **Risks**: LOW (DoWhy handles complexity)

**STEP-09: Cross-Validation** (1 day)
- **ID**: dowhy-009
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-008
- **Tasks**:
  1. Implement `cross_validate(scm, traces) -> float`
  2. 80/20 train/val split
  3. Compute R² on validation set
  4. Raise error if R² < 0.7
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Splits data correctly
  - [ ] Computes R² accurately
  - [ ] Enforces R² ≥ 0.7 threshold
  - [ ] Unit tests pass
- **Risks**: LOW (standard ML validation)

### Week 3: H22 - InterventionEngine + IR Integration

**STEP-10: Intervention API** (1 day)
- **ID**: dowhy-010
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-009
- **Tasks**:
  1. Create `lift_sys/causal/intervention.py`
  2. Implement `InterventionEngine.estimate_impact()`
  3. Use `gcm.interventional_samples()`
  4. Compute effect sizes
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Accepts intervention dict
  - [ ] Returns ImpactEstimate
  - [ ] Computes effect sizes correctly
  - [ ] Unit tests pass
- **Risks**: LOW (thin wrapper over DoWhy)

**STEP-11: Confidence Intervals** (1 day)
- **ID**: dowhy-011
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-010
- **Tasks**:
  1. Implement bootstrap CI estimation
  2. 100 bootstrap samples
  3. Compute 2.5th and 97.5th percentiles
  4. Add to ImpactEstimate
  5. Write statistical tests
- **Acceptance Criteria**:
  - [ ] Bootstrap implemented
  - [ ] 95% CI computed
  - [ ] Statistical test: CI coverage ≈95%
  - [ ] Unit tests pass
- **Risks**: LOW (standard bootstrap)

**STEP-12: IR Schema Extension** (1 day)
- **ID**: dowhy-012
- **Type**: Implementation
- **Complexity**: S
- **Dependencies**: dowhy-010
- **Tasks**:
  1. Add `causal_model` field to `lift_sys/ir/models.py`
  2. Add `causal_metadata` field
  3. Create `CausalMetadata` Pydantic model
  4. Write migration tests (backward compatibility)
- **Acceptance Criteria**:
  - [ ] Fields added to IR
  - [ ] Backward compatible (causal fields optional)
  - [ ] Pydantic validation passes
  - [ ] Migration tests pass
- **Risks**: LOW (additive change)

**STEP-13: SCM Serialization** (1.5 days)
- **ID**: dowhy-013
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-012
- **Tasks**:
  1. Implement `serialize_scm(scm) -> dict`
  2. Serialize graph (NetworkX → JSON)
  3. Serialize mechanisms (DoWhy → dict)
  4. Implement `deserialize_scm(dict) -> SCM`
  5. Write round-trip tests
- **Acceptance Criteria**:
  - [ ] SCM → JSON → SCM preserves structure
  - [ ] Mechanisms preserved
  - [ ] Round-trip test passes
  - [ ] No data loss
- **Risks**: HIGH (complex serialization)

**STEP-14: Lifter Integration** (0.5 days)
- **ID**: dowhy-014
- **Type**: Integration
- **Complexity**: M
- **Dependencies**: dowhy-001 through dowhy-013
- **Tasks**:
  1. Modify `Lifter.lift()` to accept `include_causal=True`
  2. Call CausalGraphBuilder
  3. Call SCMFitter
  4. Attach to IR
  5. Write integration test
- **Acceptance Criteria**:
  - [ ] `lift()` accepts `include_causal` parameter
  - [ ] Causal analysis runs end-to-end
  - [ ] IR has causal_model populated
  - [ ] Integration test passes
- **Risks**: LOW (orchestration only)

### Week 4: Testing & Documentation

**STEP-15: Performance Benchmarks** (1 day)
- **ID**: dowhy-015
- **Type**: Testing
- **Complexity**: M
- **Dependencies**: dowhy-014
- **Tasks**:
  1. Create `tests/performance/test_causal_performance.py`
  2. Benchmark graph building (100 files)
  3. Benchmark SCM fitting (1000 traces)
  4. Benchmark intervention queries
  5. Validate: All <30s for 100 files
- **Acceptance Criteria**:
  - [ ] Graph building <1s for 100 files
  - [ ] SCM fitting <10s for 1000 traces
  - [ ] Intervention <100ms
  - [ ] End-to-end <30s
- **Risks**: MEDIUM (may need optimization)

**STEP-16: Accuracy Validation** (1 day)
- **ID**: dowhy-016
- **Type**: Testing
- **Complexity**: M
- **Dependencies**: dowhy-014
- **Tasks**:
  1. Create `tests/validation/test_causal_accuracy.py`
  2. Manual review: Label 100 edges (causal or not)
  3. Compare against CausalGraphBuilder output
  4. Compute precision/recall
  5. Validate: ≥90% precision, ≥85% recall
- **Acceptance Criteria**:
  - [ ] Edge precision ≥90%
  - [ ] Edge recall ≥85%
  - [ ] SCM R² ≥0.7 (with traces)
  - [ ] Validation tests pass
- **Risks**: HIGH (requires manual review)

**STEP-17: Real Codebase Testing** (1 day)
- **ID**: dowhy-017
- **Type**: Testing
- **Complexity**: L
- **Dependencies**: dowhy-016
- **Tasks**:
  1. Test on 3 real codebases (10-100 files each)
  2. Validate causal graphs manually
  3. Run intervention queries
  4. Document findings
- **Acceptance Criteria**:
  - [ ] Runs successfully on 3 codebases
  - [ ] No crashes
  - [ ] Causal graphs reasonable (manual review)
  - [ ] Performance acceptable
- **Risks**: HIGH (real-world complexity)

**STEP-18: Documentation** (1.5 days)
- **ID**: dowhy-018
- **Type**: Documentation
- **Complexity**: M
- **Dependencies**: dowhy-017
- **Tasks**:
  1. Write user guide (`docs/guides/CAUSAL_ANALYSIS.md`)
  2. API reference (docstrings)
  3. Tutorial with examples
  4. FAQ section
- **Acceptance Criteria**:
  - [ ] User guide complete
  - [ ] All public APIs documented
  - [ ] 3+ working examples
  - [ ] FAQ covers common issues
- **Risks**: LOW

**STEP-19: Code Review & Polish** (0.5 days)
- **ID**: dowhy-019
- **Type**: Refinement
- **Complexity**: S
- **Dependencies**: dowhy-018
- **Tasks**:
  1. Code review (self or peer)
  2. Refactor based on feedback
  3. Final polish (naming, formatting)
  4. Tag release
- **Acceptance Criteria**:
  - [ ] Code review approved
  - [ ] No P0/P1 bugs
  - [ ] All tests passing
  - [ ] Ready for release
- **Risks**: LOW

---

## Phase 2: Test Generation (Weeks 5-7, P2)

### Week 5: H23 - CausalPathExtractor

**STEP-20: Path Extraction Algorithm** (1.5 days)
- **ID**: dowhy-020
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-019
- **Tasks**:
  1. Create `lift_sys/causal/path_extractor.py`
  2. Implement `extract_paths(scm) -> list[CausalPath]`
  3. Use NetworkX `all_simple_paths()`
  4. Create CausalPath dataclass
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Finds all paths from roots to leaves
  - [ ] Returns CausalPath objects
  - [ ] Handles graphs with 100+ nodes
  - [ ] Unit tests pass
- **Risks**: MEDIUM (exponential path count)

**STEP-21: Importance Scoring** (1.5 days)
- **ID**: dowhy-021
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-020
- **Tasks**:
  1. Implement `score_importance(path, scm) -> float`
  2. Compute direct causal effect
  3. Compute indirect effects
  4. Normalize to 0-1 scale
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Computes effect sizes correctly
  - [ ] Scores in range [0, 1]
  - [ ] High-impact paths score higher
  - [ ] Unit tests pass
- **Risks**: HIGH (complex causal calculations)

**STEP-22: Priority Assignment** (1 day)
- **ID**: dowhy-022
- **Type**: Implementation
- **Complexity**: S
- **Dependencies**: dowhy-021
- **Tasks**:
  1. Implement `assign_priority(importance) -> str`
  2. HIGH if importance > 0.7
  3. MEDIUM if 0.3 < importance ≤ 0.7
  4. LOW if importance ≤ 0.3
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Returns "HIGH" | "MEDIUM" | "LOW"
  - [ ] Thresholds correct
  - [ ] Unit tests pass
- **Risks**: LOW (simple logic)

**STEP-23: Performance Optimization** (1 day)
- **ID**: dowhy-023
- **Type**: Optimization
- **Complexity**: M
- **Dependencies**: dowhy-022
- **Tasks**:
  1. Cache intervention results
  2. Parallelize importance scoring
  3. Limit to top N paths
  4. Benchmark: <2s for 100-node graph
- **Acceptance Criteria**:
  - [ ] Caching reduces redundant work
  - [ ] Parallelization speeds up scoring
  - [ ] <2s for 100 nodes, 200 paths
  - [ ] Performance tests pass
- **Risks**: MEDIUM (parallelization complexity)

### Week 6: TestCaseGenerator

**STEP-24: Input Generation** (1.5 days)
- **ID**: dowhy-024
- **Type**: Implementation
- **Complexity**: L
- **Dependencies**: dowhy-023
- **Tasks**:
  1. Create `lift_sys/causal/test_generator.py`
  2. Implement `find_activating_inputs(path) -> dict`
  3. Analyze conditionals on path
  4. Generate inputs satisfying conditions
  5. Fallback: Random sampling
  6. Write unit tests
- **Acceptance Criteria**:
  - [ ] Generates valid inputs
  - [ ] Inputs activate target path
  - [ ] Handles conditionals (if/else)
  - [ ] Unit tests pass
- **Risks**: HIGH (symbolic execution is hard)

**STEP-25: Output Prediction** (1 day)
- **ID**: dowhy-025
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-024
- **Tasks**:
  1. Implement `predict_output(scm, inputs) -> Any`
  2. Run SCM forward simulation
  3. Return predicted leaf node value
  4. Write unit tests
- **Acceptance Criteria**:
  - [ ] Predicts outputs correctly
  - [ ] Uses SCM mechanisms
  - [ ] Unit tests pass
- **Risks**: LOW (SCM handles this)

**STEP-26: Test Code Generation** (1.5 days)
- **ID**: dowhy-026
- **Type**: Implementation
- **Complexity**: M
- **Dependencies**: dowhy-025
- **Tasks**:
  1. Implement `generate_test_code(test_case) -> str`
  2. Use string templating for pytest
  3. Format inputs and assertions
  4. Validate syntax with ast.parse()
  5. Write unit tests
- **Acceptance Criteria**:
  - [ ] Generates syntactically valid Python
  - [ ] Uses pytest format
  - [ ] Includes descriptive docstrings
  - [ ] ast.parse() succeeds
  - [ ] Unit tests pass
- **Risks**: MEDIUM (code generation)

**STEP-27: Integration** (1 day)
- **ID**: dowhy-027
- **Type**: Integration
- **Complexity**: M
- **Dependencies**: dowhy-026
- **Tasks**:
  1. Create `CausalTestGenerator` class
  2. Implement `generate_from_ir(ir) -> TestSuite`
  3. Orchestrate path extraction + test generation
  4. Write integration tests
- **Acceptance Criteria**:
  - [ ] End-to-end test generation works
  - [ ] Returns TestSuite object
  - [ ] Integration tests pass
- **Risks**: LOW (orchestration)

### Week 7: Integration & Validation

**STEP-28: Integration with Validation Pipeline** (1 day)
- **ID**: dowhy-028
- **Type**: Integration
- **Complexity**: M
- **Dependencies**: dowhy-027
- **Tasks**:
  1. Modify `lift_sys/validation/` to use causal tests
  2. Add CLI flag: `--causal-tests`
  3. Write end-to-end test
- **Acceptance Criteria**:
  - [ ] CLI accepts `--causal-tests` flag
  - [ ] Generated tests run via pytest
  - [ ] End-to-end test passes
- **Risks**: LOW

**STEP-29: Real Codebase Testing** (1 day)
- **ID**: dowhy-029
- **Type**: Testing
- **Complexity**: L
- **Dependencies**: dowhy-028
- **Tasks**:
  1. Generate tests for 3 real codebases
  2. Validate: ≥95% pass on original code
  3. Introduce bugs: Validate ≥90% detection
  4. Measure causal coverage improvement
- **Acceptance Criteria**:
  - [ ] ≥95% generated tests pass
  - [ ] ≥90% detect regressions
  - [ ] ≥20% causal coverage improvement
  - [ ] Validation tests pass
- **Risks**: HIGH (real-world validation)

**STEP-30: Documentation** (1.5 days)
- **ID**: dowhy-030
- **Type**: Documentation
- **Complexity**: M
- **Dependencies**: dowhy-029
- **Tasks**:
  1. Write test generation guide
  2. API reference
  3. Tutorial with examples
  4. FAQ
- **Acceptance Criteria**:
  - [ ] Guide complete
  - [ ] APIs documented
  - [ ] 3+ examples
  - [ ] FAQ covers common issues
- **Risks**: LOW

**STEP-31: Code Review & Release** (0.5 days)
- **ID**: dowhy-031
- **Type**: Refinement
- **Complexity**: S
- **Dependencies**: dowhy-030
- **Tasks**:
  1. Code review
  2. Final polish
  3. Tag release v2.0 (includes P1+P2)
- **Acceptance Criteria**:
  - [ ] Code review approved
  - [ ] All tests passing
  - [ ] Release tagged
- **Risks**: LOW

---

## Parallelization Opportunities

**Week 1-2**: Can parallelize within weeks (e.g., STEP-03 and STEP-04 independent)

**Week 5**: STEP-20, STEP-21, STEP-22 must be sequential (each depends on previous)

**Week 6**: STEP-24, STEP-25, STEP-26 must be sequential

**Weeks 4 & 7**: Testing/documentation can partially overlap with prior week

---

## Critical Path

```
STEP-01 → STEP-02 → STEP-03 → STEP-05 → STEP-06 → STEP-08 → STEP-09 →
STEP-10 → STEP-13 → STEP-14 → STEP-15 → STEP-16 → STEP-17 →
STEP-20 → STEP-21 → STEP-24 → STEP-25 → STEP-26 → STEP-27 → STEP-29
```

**Critical Path Duration**: ~30 days (allowing some parallelization)

---

## Risk Assessment by Step

**HIGH RISK** (need extra attention):
- STEP-03: Data flow analysis (complex)
- STEP-07: Execution tracing (runtime instrumentation)
- STEP-13: SCM serialization (complex data structure)
- STEP-16: Accuracy validation (requires manual review)
- STEP-17: Real codebase testing (unknown issues)
- STEP-21: Importance scoring (complex math)
- STEP-24: Input generation (symbolic execution)
- STEP-29: Real codebase testing (validation)

**MEDIUM RISK**:
- STEP-02, 04, 05, 06, 08, 09, 10, 11, 14, 15, 20, 23, 26, 27, 28, 30

**LOW RISK**:
- STEP-01, 12, 18, 19, 22, 25, 31

---

## Contingency Plans

**If STEP-03 (Data Flow) too complex**:
- Fallback: Use simpler heuristic (function calls only)
- Impact: Lower accuracy, but functional

**If STEP-07 (Tracing) fails**:
- Fallback: Static-only mode (no traces)
- Impact: Lower accuracy, but usable

**If STEP-13 (Serialization) too hard**:
- Fallback: Don't serialize SCM, recompute on load
- Impact: Slower, but functional

**If STEP-16 (Accuracy) fails validation**:
- Iterate: Improve graph builder based on errors
- Timeline impact: +1-2 days

---

## Success Metrics

**Phase 1 Complete**:
- [ ] All STEP-01 through STEP-19 done
- [ ] Causal graph accuracy ≥90%
- [ ] SCM R² ≥0.7
- [ ] Performance <30s for 100 files
- [ ] 3 real codebases validated

**Phase 2 Complete**:
- [ ] All STEP-20 through STEP-31 done
- [ ] ≥95% generated tests pass
- [ ] ≥90% detect regressions
- [ ] ≥20% causal coverage improvement
- [ ] User satisfaction >8/10

---

**Execution Plan Status**: COMPLETE
**Next**: Generate Beads issues and artifacts
