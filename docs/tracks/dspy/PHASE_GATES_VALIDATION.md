---
track: dspy
document_type: validation_criteria
status: active
priority: P0
completion: 43%
last_updated: 2025-10-21
session_protocol: |
  For new Claude Code session:
  1. Check current phase gate status (Gate 1: 8/14 criteria satisfied, 57%)
  2. Review functional, performance, quality, documentation criteria
  3. Before completing a phase, validate ALL gate criteria
  4. Cannot proceed to next phase until current gate passes
related_docs:
  - docs/tracks/dspy/SESSION_STATE.md
  - docs/tracks/dspy/HOLE_INVENTORY.md
  - docs/tracks/dspy/META_FRAMEWORK_DESIGN_BY_HOLES.md
  - docs/MASTER_ROADMAP.md
---

# Phase Gates Validation Criteria

**Date**: 2025-10-20
**Status**: ACTIVE
**Version**: 1.0

---

## Purpose

This document defines the validation criteria ("gates") that must be met before proceeding from one phase to the next. Each gate includes:
- Functional requirements (what must work)
- Performance requirements (how well it must work)
- Quality requirements (how correct it must be)
- Documentation requirements (what must be explained)

**Principle**: Cannot proceed to Phase N+1 until Phase N gate passes.

---

## Gate Structure

Each gate consists of:

```yaml
gate:
  phase: N
  name: "{Gate Name}"
  status: [PENDING | IN_PROGRESS | PASSED | FAILED]

  functional_criteria:
    - requirement: "{Description}"
      test: "{How to verify}"
      status: [PENDING | PASS | FAIL]

  performance_criteria:
    - requirement: "{Description}"
      target: "{Numeric target}"
      measured: "{Actual value}"
      status: [PENDING | PASS | FAIL]

  quality_criteria:
    - requirement: "{Description}"
      test: "{How to verify}"
      status: [PENDING | PASS | FAIL]

  documentation_criteria:
    - requirement: "{Description}"
      artifact: "{File path}"
      status: [PENDING | PASS | FAIL]
```

---

## Gate 1: Interface Completeness

**Phase**: Phase 1 (Week 1)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F1.1**: Prototype node executes with DSPy signature
  - **Test**: Run `ExtractIntentNode` with sample prompt
  - **Expected**: Node executes, returns `IntentClause`
  - **Status**: PENDING

- [ ] **F1.2**: Graph state persists and resumes
  - **Test**: Execute → Save → Kill process → Resume
  - **Expected**: Execution continues from saved state
  - **Status**: PENDING

- [ ] **F1.3**: Validation hooks execute correctly
  - **Test**: Register pre/post validators, trigger them
  - **Expected**: Validators called at right times
  - **Status**: PENDING

### Performance Criteria

- [ ] **P1.1**: Type checking passes
  - **Target**: `mypy --strict` with 0 errors
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P1.2**: Serialization overhead acceptable
  - **Target**: <10ms for state save/load
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q1.1**: Interface satisfies type constraints
  - **Test**: Type checker validates `BaseNode[StateT]`
  - **Status**: PENDING

- [ ] **Q1.2**: No data loss in serialization
  - **Test**: Round-trip 100 times, diff states
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D1.1**: Interface contract documented
  - **Artifact**: `lift_sys/dspy_signatures/node_interface.py` (docstrings)
  - **Status**: PENDING

- [ ] **D1.2**: Validation hooks documented
  - **Artifact**: `lift_sys/validation/hooks.py` (docstrings)
  - **Status**: PENDING

- [ ] **D1.3**: Resource limits documented
  - **Artifact**: `docs/planning/RESOURCE_LIMITS.md`
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: All functional criteria PASS, ≥80% of performance/quality criteria PASS, all documentation criteria COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 2: Execution Completeness

**Phase**: Phase 2 (Week 2)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F2.1**: Full graph executes end-to-end
  - **Test**: Run `ForwardModeGraph` with real prompt
  - **Expected**: Produces IR and code
  - **Status**: PENDING

- [ ] **F2.2**: Provider integration works
  - **Test**: DSPy signature calls Modal/SGLang via adapter
  - **Expected**: Response returns, XGrammar preserved
  - **Status**: PENDING

- [ ] **F2.3**: State persistence handles all types
  - **Test**: Save/load graph with IR, TypedHoles, Provenance
  - **Expected**: All Pydantic models serialize correctly
  - **Status**: PENDING

### Performance Criteria

- [ ] **P2.1**: Latency within baseline
  - **Target**: ≤110% of current baseline (16s → 17.6s acceptable)
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P2.2**: State persistence fast
  - **Target**: <100ms for save, <50ms for load
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q2.1**: XGrammar constraints preserved
  - **Test**: Compare XGrammar outputs before/after DSPy wrapper
  - **Status**: PENDING

- [ ] **Q2.2**: Execution deterministic
  - **Test**: Run same graph 10 times, verify identical outputs
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D2.1**: Provider adapter documented
  - **Artifact**: `lift_sys/providers/dspy_provider.py` (docstrings)
  - **Status**: PENDING

- [ ] **D2.2**: Execution history schema documented
  - **Artifact**: `migrations/XXX_graph_execution_history.sql`
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: All functional criteria PASS, ≥80% of performance criteria PASS, ≥90% quality criteria PASS, all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 3: Optimization Completeness

**Phase**: Phase 3 (Week 3)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F3.1**: Metrics compute correctly
  - **Test**: Score 20 hand-labeled examples
  - **Expected**: Metrics produce 0.0-1.0 scores
  - **Status**: PENDING

- [ ] **F3.2**: MIPROv2 runs successfully
  - **Test**: Optimize pipeline with 20 training examples
  - **Expected**: Optimization completes, produces optimized pipeline
  - **Status**: PENDING

- [ ] **F3.3**: Confidence scores calibrated
  - **Test**: Compare predicted confidence to actual accuracy
  - **Expected**: Calibration plot shows reasonable correlation
  - **Status**: PENDING

### Performance Criteria

- [ ] **P3.1**: Optimization time reasonable
  - **Target**: <2 hours for 50 iterations
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P3.2**: Metric computation fast
  - **Target**: <500ms per example
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q3.1**: Metrics correlate with quality
  - **Test**: Spearman correlation with manual scores
  - **Target**: ρ > 0.7
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **Q3.2**: Optimization improves scores
  - **Test**: Compare baseline vs optimized on test set
  - **Expected**: Optimized score > baseline score
  - **Status**: PENDING

- [ ] **Q3.3**: Inter-rater reliability
  - **Test**: 2 raters score same 20 examples
  - **Target**: Cohen's κ > 0.8
  - **Measured**: TBD
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D3.1**: Metrics documented
  - **Artifact**: `lift_sys/evaluation/metrics.py` (docstrings)
  - **Status**: PENDING

- [ ] **D3.2**: Optimization guide written
  - **Artifact**: `docs/planning/OPTIMIZATION_GUIDE.md`
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: All functional PASS, ≥80% performance PASS, ≥90% quality PASS (including correlation), all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 4: Parallelization Completeness

**Phase**: Phase 4 (Week 4)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F4.1**: Parallel nodes execute
  - **Test**: Run graph with parallel signature generation + constraint extraction
  - **Expected**: Both complete, states merge correctly
  - **Status**: PENDING

- [ ] **F4.2**: Concurrency limits respected
  - **Test**: Monitor concurrent LLM calls during execution
  - **Expected**: Never exceeds `max_concurrent` limit
  - **Status**: PENDING

### Performance Criteria

- [ ] **P4.1**: Speedup achieved
  - **Target**: ≥2x speedup on parallel paths
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P4.2**: No performance degradation on serial paths
  - **Target**: Serial path latency ≤105% of baseline
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q4.1**: Deterministic execution
  - **Test**: Run parallel graph 100 times
  - **Expected**: Identical outputs every time
  - **Status**: PENDING

- [ ] **Q4.2**: No race conditions
  - **Test**: ThreadSanitizer or similar
  - **Expected**: 0 detected races
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D4.1**: Parallelization strategy documented
  - **Artifact**: `lift_sys/pydantic_graphs/parallel_executor.py` (docstrings)
  - **Status**: PENDING

- [ ] **D4.2**: Concurrency model documented
  - **Artifact**: `docs/planning/CONCURRENCY_MODEL.md`
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: All functional PASS, ≥90% performance PASS (must show speedup), 100% quality PASS (determinism critical), all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 5: Caching and Performance Completeness

**Phase**: Phase 5 (Week 5)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F5.1**: Cache hit/miss works
  - **Test**: Execute same graph twice, verify cache hit on second run
  - **Expected**: Second run uses cached results
  - **Status**: PENDING

- [ ] **F5.2**: Cache invalidation works
  - **Test**: Update node version, verify cache miss
  - **Expected**: Old cache entries not used
  - **Status**: PENDING

- [ ] **F5.3**: Trace visualization accessible
  - **Test**: Query execution trace via API
  - **Expected**: Trace data returned with node timeline
  - **Status**: PENDING

### Performance Criteria

- [ ] **P5.1**: Cache hit rate
  - **Target**: >60% on repeated prompts
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P5.2**: Cache speedup
  - **Target**: >2x on fully cached paths
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P5.3**: Trace query performance
  - **Target**: <100ms for trace data
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q5.1**: Cache consistency
  - **Test**: Concurrent cache writes, verify no corruption
  - **Status**: PENDING

- [ ] **Q5.2**: Trace completeness
  - **Test**: Verify all nodes appear in trace
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D5.1**: Caching strategy documented
  - **Artifact**: `lift_sys/caching/node_cache.py` (docstrings)
  - **Status**: PENDING

- [ ] **D5.2**: Trace protocol documented
  - **Artifact**: `lift_sys/api/schemas.py` (ExecutionTrace model)
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: All functional PASS, ≥80% performance PASS (cache hit rate critical), ≥90% quality PASS, all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 6: Migration and Production Completeness

**Phase**: Phase 6 (Week 6)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F6.1**: Session migration works
  - **Test**: Migrate 100 production sessions
  - **Expected**: 100% success rate, no data loss
  - **Status**: PENDING

- [ ] **F6.2**: Feature flags operational
  - **Test**: Enable for specific users, verify routing
  - **Expected**: Flagged users use new pipeline
  - **Status**: PENDING

- [ ] **F6.3**: Rollback tested
  - **Test**: Enable new pipeline, then rollback
  - **Expected**: System reverts to old pipeline
  - **Status**: PENDING

### Performance Criteria

- [ ] **P6.1**: Migration time acceptable
  - **Target**: <5 seconds per session
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P6.2**: Feature flag query fast
  - **Target**: <10ms per query
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q6.1**: No data loss
  - **Test**: Diff migrated sessions against originals
  - **Expected**: All fields preserved
  - **Status**: PENDING

- [ ] **Q6.2**: Resume after migration works
  - **Test**: Resume 10 migrated sessions
  - **Expected**: All resume successfully
  - **Status**: PENDING

- [ ] **Q6.3**: Rollback preserves state
  - **Test**: Create sessions in new format, rollback, verify accessible
  - **Expected**: No sessions lost
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D6.1**: Migration guide written
  - **Artifact**: `docs/planning/MIGRATION_GUIDE.md`
  - **Status**: PENDING

- [ ] **D6.2**: Rollback procedure documented
  - **Artifact**: `docs/planning/ROLLBACK_PROCEDURE.md`
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: 100% functional PASS (migration critical), ≥80% performance PASS, 100% quality PASS (no data loss), all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate 7: Final Validation Completeness

**Phase**: Phase 7 (Week 7)
**Status**: ⏳ PENDING

### Functional Criteria

- [ ] **F7.1**: Statistical validation passes
  - **Test**: A/B test baseline vs optimized on 50 test examples
  - **Expected**: p < 0.05, effect size > 0.3
  - **Status**: PENDING

- [ ] **F7.2**: Error recovery works
  - **Test**: Inject failures, verify graceful degradation
  - **Expected**: System recovers or fails safely
  - **Status**: PENDING

### Performance Criteria

- [ ] **P7.1**: End-to-end success rate
  - **Target**: ≥85% (from 60% baseline)
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **P7.2**: Latency improvement
  - **Target**: ≤80% of baseline (16s → 12.8s)
  - **Measured**: TBD
  - **Status**: PENDING

### Quality Criteria

- [ ] **Q7.1**: Statistical significance
  - **Test**: Paired t-test on test set
  - **Target**: p < 0.05
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **Q7.2**: Effect size
  - **Test**: Cohen's d on test set
  - **Target**: d > 0.5 (medium effect)
  - **Measured**: TBD
  - **Status**: PENDING

- [ ] **Q7.3**: All gates passed
  - **Test**: Review Gates 1-6
  - **Expected**: All PASSED
  - **Status**: PENDING

### Documentation Criteria

- [ ] **D7.1**: Optimization results documented
  - **Artifact**: `docs/planning/OPTIMIZATION_RESULTS.md`
  - **Status**: PENDING

- [ ] **D7.2**: Production deployment guide
  - **Artifact**: `docs/planning/DEPLOYMENT_GUIDE.md`
  - **Status**: PENDING

- [ ] **D7.3**: All holes documented as resolved
  - **Artifact**: `docs/planning/HOLE_INVENTORY.md` (all status=RESOLVED)
  - **Status**: PENDING

### Gate Verdict

**Pass Condition**: 100% functional PASS, ≥90% performance PASS (success rate critical), 100% quality PASS (significance required), all documentation COMPLETE

**Status**: ⏳ Not yet evaluated

---

## Gate Execution Process

### Before Starting Phase N

1. Review Gate N criteria
2. Understand all requirements
3. Plan tests to validate each criterion
4. Set up measurement infrastructure

### During Phase N

1. Track progress against criteria
2. Run tests as features complete
3. Update gate status in this document
4. Raise blockers early if criteria at risk

### At End of Phase N

1. Run all gate tests
2. Measure all performance targets
3. Review all documentation artifacts
4. Update gate status (PASS/FAIL)
5. If FAIL, create remediation plan

### Proceeding to Phase N+1

**Required**: Gate N status = PASSED

**If Gate FAILED**:
1. Do NOT proceed to next phase
2. Create action plan to address failures
3. Retry gate validation
4. Only proceed after PASS

---

## Gate Status Dashboard

| Gate | Phase | Status | Pass Rate | Blockers |
|------|-------|--------|-----------|----------|
| Gate 1 | Week 1 | ⏳ PENDING | 0/12 | None |
| Gate 2 | Week 2 | ⏳ PENDING | 0/10 | Gate 1 |
| Gate 3 | Week 3 | ⏳ PENDING | 0/11 | Gate 2 |
| Gate 4 | Week 4 | ⏳ PENDING | 0/9 | Gate 3 |
| Gate 5 | Week 5 | ⏳ PENDING | 0/10 | Gate 4 |
| Gate 6 | Week 6 | ⏳ PENDING | 0/11 | Gate 5 |
| Gate 7 | Week 7 | ⏳ PENDING | 0/12 | Gates 1-6 |

**Overall Progress**: 0/75 criteria passed (0%)

---

**Document Status**: ACTIVE - Update after each phase
**Owner**: Architecture team
**Last Updated**: 2025-10-20
