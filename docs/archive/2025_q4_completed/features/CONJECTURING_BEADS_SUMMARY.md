# Conjecturing Framework: Beads Work Item Summary
## Complete Implementation Tracking

**Created**: October 17, 2025
**Epic**: lift-sys-230
**Status**: Ready for execution

---

## Overview

This document summarizes the Beads work items created for implementing the conjecturing framework based on arXiv:2510.11986.

## Epic

**lift-sys-230: Epic: Conjecturing Framework Implementation**
- Type: Epic
- Priority: P1
- Status: Open
- Labels: research, conjecturing, phase-7-followup
- External Ref: arxiv-2510.11986

Three-phase implementation to improve diagnostic visibility and success rates by separating IR generation (conjecturing) from code generation (formalisation).

---

## Phase 1: Diagnostic Enhancement

**Duration**: 1 week (8-12 hours)
**Goal**: Identify bottleneck (conjecturing vs formalisation)
**Decision**: Go/no-go for Phase 2

### Work Items

#### lift-sys-231: Phase 1: Diagnostic Enhancement with Conjecturing Metrics
- Type: Feature
- Priority: P1
- Dependencies: lift-sys-230, lift-sys-229
- Labels: diagnostic, metrics, conjecturing, phase-1

Main Phase 1 coordination task.

#### lift-sys-232: Add conjecture quality evaluation
- Type: Task
- Priority: P1
- Dependencies: lift-sys-231
- Labels: implementation, diagnostic, phase-1

Implement `evaluate_conjecture_quality()` function:
- Extract detected constraints from IR
- Compare to expected constraints (ground truth)
- Calculate constraint completeness metric

#### lift-sys-233: Add constraint preservation measurement
- Type: Task
- Priority: P1
- Dependencies: lift-sys-232
- Labels: implementation, diagnostic, phase-1

Implement `evaluate_constraint_preservation()` function:
- Measure how well code honors IR constraints
- Calculate preservation rate
- Use existing ConstraintValidator

#### lift-sys-234: Create bottleneck analysis script
- Type: Task
- Priority: P1
- Dependencies: lift-sys-232
- Labels: implementation, diagnostic, phase-1

Create `analyze_conjecturing_bottleneck.py`:
- Load and aggregate diagnostic samples
- Apply bottleneck detection logic
- Generate markdown report with recommendation

#### lift-sys-235: Collect diagnostic samples
- Type: Task
- Priority: P1
- Dependencies: lift-sys-232
- Labels: execution, diagnostic, phase-1

Collect 36 samples (12 per failing test):
- count_words
- find_index
- is_valid_email

#### lift-sys-236: Generate diagnostic report and decide
- Type: Task
- Priority: P1
- Dependencies: lift-sys-235
- Labels: analysis, decision, phase-1

Analyze results and make go/no-go decision for Phase 2.

### Phase 1 Deliverables

- [ ] Modified `debug/collect_failure_samples.py`
- [ ] New `debug/analyze_conjecturing_bottleneck.py`
- [ ] `DIAGNOSTIC_REPORT_CONJECTURING.md`
- [ ] Decision on Phase 2 (go/no-go/investigate)

### Phase 1 Success Criteria

- [ ] 36 samples collected
- [ ] Constraint completeness measured (avg across tests)
- [ ] Constraint preservation measured (avg across tests)
- [ ] Bottleneck identified with confidence level
- [ ] Clear recommendation provided

---

## Phase 2: Two-Phase IR Generation

**Duration**: 2-3 weeks (40-60 hours)
**Goal**: Implement skeleton + conjecture generation
**Prerequisite**: Phase 1 shows bottleneck = CONJECTURING

### Work Items

#### lift-sys-237: Phase 2: Two-Phase IR Generation
- Type: Feature
- Priority: P2
- Dependencies: lift-sys-231
- Labels: implementation, conjecturing, phase-2

Main Phase 2 coordination task.

#### lift-sys-238: Implement SkeletonGenerator
- Type: Task
- Priority: P2
- Dependencies: lift-sys-237
- Labels: implementation, skeleton, phase-2

Create `lift_sys/conjecturing/skeleton_generator.py`:
- Generate IR with explicit typed holes
- Preserve ambiguity rather than guessing
- Design prompt template

#### lift-sys-239: Implement ConjectureGenerator
- Type: Task
- Priority: P2
- Dependencies: lift-sys-237
- Labels: implementation, conjecture, phase-2

Create `lift_sys/conjecturing/conjecture_generator.py`:
- Fill typed holes using LLM + constraints
- Handle hole dependencies
- Filter candidates by constraints

#### lift-sys-240: Implement ConjectureValidator
- Type: Task
- Priority: P2
- Dependencies: lift-sys-237
- Labels: implementation, validation, phase-2

Create `lift_sys/conjecturing/conjecture_validator.py`:
- Validate IR-level constraints
- Check conjectures before code generation
- Return clear violation messages

#### lift-sys-241: Implement ConjecturingIRTranslator
- Type: Task
- Priority: P2
- Dependencies: lift-sys-238, lift-sys-239, lift-sys-240
- Labels: implementation, integration, phase-2

Create `lift_sys/conjecturing/translator.py`:
- Orchestrate full two-phase IR generation
- Integrate all components
- Main API for users

#### lift-sys-242: Implement conjecturing metrics
- Type: Task
- Priority: P2
- Dependencies: lift-sys-237
- Labels: implementation, metrics, phase-2

Create `lift_sys/conjecturing/metrics.py`:
- Conjecture accuracy measurement
- Constraint completeness tracking
- Constraint preservation tracking

#### lift-sys-243: Create comprehensive test suite
- Type: Task
- Priority: P2
- Dependencies: lift-sys-238, lift-sys-239, lift-sys-240, lift-sys-241
- Labels: testing, phase-2

Implement tests for all components:
- Unit tests (>90% coverage)
- Integration tests
- E2E tests
- Regression tests

#### lift-sys-244: Benchmark vs baseline
- Type: Task
- Priority: P2
- Dependencies: lift-sys-241, lift-sys-243
- Labels: benchmarking, evaluation, phase-2

Create `debug/benchmark_conjecturing.py`:
- Compare conjecturing to baseline translator
- Measure all key metrics
- Statistical analysis

#### lift-sys-245: Create documentation
- Type: Task
- Priority: P2
- Dependencies: lift-sys-241, lift-sys-243
- Labels: documentation, phase-2

Write `docs/CONJECTURING_USER_GUIDE.md`:
- User guide
- API reference
- Migration guide

#### lift-sys-246: Rollout and A/B testing
- Type: Task
- Priority: P2
- Dependencies: lift-sys-244, lift-sys-245
- Labels: deployment, production, phase-2

Deploy and test in production:
- Parallel deployment (week 1)
- A/B testing (week 2)
- Gradual rollout (week 3)

### Phase 2 Deliverables

- [ ] `lift_sys/conjecturing/` package
- [ ] >90% test coverage
- [ ] Benchmark results
- [ ] User guide and API docs
- [ ] Production deployment (if metrics met)

### Phase 2 Success Criteria

- [ ] IR conjecture accuracy >90%
- [ ] E2E success improvement >5% (83.3% → 88%+)
- [ ] Latency overhead <20%
- [ ] All existing tests pass
- [ ] Production-ready

---

## Phase 3: CSP Integration (Optional)

**Duration**: 4-6 weeks (120-180 hours)
**Goal**: Add sophisticated constraint propagation
**Prerequisite**: Phase 2 successful but <95% success rate

### Work Items

#### lift-sys-247: Phase 3: CSP Integration
- Type: Feature
- Priority: P3
- Dependencies: lift-sys-237
- Labels: implementation, csp, phase-3, optional

Integrate CSP-based constraint propagation:
- Complex dependency handling
- Backtracking and propagation
- Parallel hole resolution
- Target: >95% E2E success

**Note**: This is optional and depends on Phase 2 results. See `CONSTRAINT_PROPAGATION_TYPED_HOLES.md` for detailed design.

### Phase 3 Deliverables

- [ ] CSP solver integration
- [ ] Complex dependency support
- [ ] >95% E2E success rate
- [ ] Production deployment

---

## Work Item Dependency Graph

```
lift-sys-230 (Epic: Conjecturing Framework)
│
├─ lift-sys-231 (Phase 1: Diagnostic Enhancement)
│  │
│  ├─ lift-sys-232 (Add conjecture quality eval)
│  │  │
│  │  ├─ lift-sys-233 (Add constraint preservation)
│  │  │
│  │  └─ lift-sys-234 (Create analysis script)
│  │
│  └─ lift-sys-235 (Collect samples)
│     │
│     └─ lift-sys-236 (Generate report & decide)
│        │
│        ├─ DECISION: If bottleneck = CONJECTURING → Phase 2
│        ├─ DECISION: If bottleneck = FORMALISATION → Pivot
│        └─ DECISION: If unclear → Investigate
│
├─ lift-sys-237 (Phase 2: Two-Phase IR Generation)
│  │
│  ├─ lift-sys-238 (SkeletonGenerator)
│  │
│  ├─ lift-sys-239 (ConjectureGenerator)
│  │
│  ├─ lift-sys-240 (ConjectureValidator)
│  │
│  ├─ lift-sys-241 (ConjecturingIRTranslator)
│  │  └─ Depends on: lift-sys-238, 239, 240
│  │
│  ├─ lift-sys-242 (Metrics)
│  │
│  ├─ lift-sys-243 (Test suite)
│  │  └─ Depends on: lift-sys-238, 239, 240, 241
│  │
│  ├─ lift-sys-244 (Benchmark)
│  │  └─ Depends on: lift-sys-241, 243
│  │
│  ├─ lift-sys-245 (Documentation)
│  │  └─ Depends on: lift-sys-241, 243
│  │
│  └─ lift-sys-246 (Rollout)
│     └─ Depends on: lift-sys-244, 245
│
└─ lift-sys-247 (Phase 3: CSP Integration - OPTIONAL)
   └─ Depends on: lift-sys-237 complete AND need for >95% success
```

---

## Execution Timeline

### Week 1: Phase 1 Diagnostic
**Active**: lift-sys-231 through lift-sys-236

- Mon-Tue: Implement evaluation functions (232, 233, 234)
- Wed-Thu: Collect samples and analyze (235, 236)
- Fri: Decision meeting

**Deliverable**: DIAGNOSTIC_REPORT_CONJECTURING.md

### Weeks 2-4: Phase 2 Implementation (if Phase 1 = GO)
**Active**: lift-sys-237 through lift-sys-246

Week 2:
- Implement SkeletonGenerator (238)
- Implement ConjectureGenerator (239)
- Implement ConjectureValidator (240)

Week 3:
- Implement ConjecturingIRTranslator (241)
- Implement Metrics (242)
- Create test suite (243)

Week 4:
- Run benchmarks (244)
- Write documentation (245)
- Deploy and A/B test (246)

**Deliverable**: Production-ready conjecturing translator

### Weeks 5-10: Phase 3 CSP (if Phase 2 successful but <95%)
**Active**: lift-sys-247

Weeks 5-6: CSP implementation
Weeks 7-8: Integration and testing
Weeks 9-10: Optimization and deployment

**Deliverable**: CSP-enhanced translator with >95% success

---

## Tracking Progress

### View All Work Items

```bash
# List all conjecturing work items
bd list --labels conjecturing

# Show Phase 1 tasks
bd list --labels phase-1

# Show Phase 2 tasks
bd list --labels phase-2

# Show dependency graph
bd show lift-sys-230 --deps
```

### Update Status

```bash
# Start Phase 1
bd update lift-sys-231 --status in-progress

# Complete a task
bd update lift-sys-232 --status done

# Add notes
bd update lift-sys-235 --comment "Collected 12 samples for count_words"
```

### Create Additional Tasks

If sub-tasks emerge during implementation:

```bash
bd create "Subtask name" \
  --type task \
  --deps "lift-sys-XXX" \
  --labels "phase-1" \
  --description "Details..."
```

---

## Decision Points

### After Phase 1 (lift-sys-236)

**If bottleneck = CONJECTURING (high confidence)**:
- ✅ Proceed to Phase 2 (lift-sys-237)
- Update lift-sys-237 status to `in-progress`

**If bottleneck = FORMALISATION (high confidence)**:
- ❌ Do NOT proceed to Phase 2
- Create new work items for semantic validation (Option 2)
- Document decision in DIAGNOSTIC_REPORT_CONJECTURING.md

**If unclear or systemic issues**:
- ⚠️ Investigate further
- Create follow-up diagnostic tasks
- Reassess after more data

### After Phase 2 (lift-sys-246)

**If success criteria met (>90% conjecture accuracy, >88% E2E)**:
- ✅ Deploy to production
- Mark Phase 2 complete
- Decide on Phase 3 based on E2E rate

**If success criteria not met**:
- ❌ Investigate issues
- Iterate on implementation
- Consider pivot to alternative approaches

**If E2E >88% but <95%**:
- ⚠️ Consider Phase 3 CSP integration
- Assess cost/benefit of 4-6 week effort
- Get stakeholder approval

---

## Key Files

### Documentation
- `CONJECTURING_RESEARCH_REPORT.md` - Research analysis
- `CONJECTURING_IMPLEMENTATION_PLAN.md` - High-level plan
- `docs/CONJECTURING_TECHNICAL_SPEC.md` - Technical specification
- `CONJECTURING_BEADS_SUMMARY.md` - This file

### Code (to be created)
- `lift_sys/conjecturing/` - Conjecturing framework package
- `debug/collect_failure_samples.py` - Diagnostic collection (modified)
- `debug/analyze_conjecturing_bottleneck.py` - Analysis script (new)
- `debug/benchmark_conjecturing.py` - Benchmarking (new)

### Tests (to be created)
- `tests/conjecturing/` - Unit and integration tests
- `tests/integration/test_conjecturing_e2e.py` - E2E tests

---

## Success Metrics

| Metric | Baseline | Phase 1 Target | Phase 2 Target | Phase 3 Target |
|--------|----------|----------------|----------------|----------------|
| E2E Success Rate | 83.3% | Measured | >88% | >95% |
| IR Conjecture Accuracy | N/A | Measured | >90% | >95% |
| Constraint Completeness | Unknown | Measured | >80% | >90% |
| Constraint Preservation | Unknown | Measured | >70% | >85% |
| Latency | Baseline | Baseline | <1.2x | <2.0x |
| Cost per Request | Baseline | Baseline | <1.5x | <2.0x |

---

## Risk Management

### Phase 1 Risks
- **Risk**: Bottleneck analysis inconclusive
- **Mitigation**: Collect more samples, refine metrics
- **Impact**: Delay Phase 2 decision by 1 week

### Phase 2 Risks
- **Risk**: Skeleton generation produces poor quality
- **Mitigation**: Iterate on prompt engineering, add examples
- **Impact**: 1-2 week delay

- **Risk**: Conjecture accuracy <90%
- **Mitigation**: Refine constraint filtering, add validation
- **Impact**: May need to revisit approach

- **Risk**: E2E success doesn't improve
- **Mitigation**: Analyze failures, may pivot to semantic validation
- **Impact**: Abandon Phase 2, pursue alternative

### Phase 3 Risks
- **Risk**: CSP complexity slows development
- **Mitigation**: Start with simple CSP, add features incrementally
- **Impact**: Extend timeline to 8-10 weeks

- **Risk**: E2E success still <95%
- **Mitigation**: Accept 88-95% as sufficient, or investigate fundamental limits
- **Impact**: May not reach 95% goal

---

## Next Steps

1. ✅ Review this summary
2. ⏳ Begin Phase 1 (lift-sys-231)
3. ⏳ Implement diagnostic enhancements (lift-sys-232, 233, 234)
4. ⏳ Collect samples (lift-sys-235)
5. ⏳ Analyze and decide (lift-sys-236)

**First Concrete Action**: Start work on lift-sys-232 (Add conjecture quality evaluation)

---

## Questions or Issues?

If questions arise during implementation:
1. Check documentation (CONJECTURING_TECHNICAL_SPEC.md)
2. Review research report (CONJECTURING_RESEARCH_REPORT.md)
3. Add comments to relevant Beads work item
4. Create new work item if significant issue discovered

---

**Status**: Ready for execution
**Next Milestone**: Phase 1 diagnostic complete (1 week)
**Success Indicator**: Clear bottleneck identification with high confidence

---

**Last Updated**: October 17, 2025
**Work Items Created**: 18 (1 epic, 2 features, 15 tasks)
**Total Estimated Effort**:
- Phase 1: 8-12 hours
- Phase 2: 40-60 hours
- Phase 3: 120-180 hours (optional)
