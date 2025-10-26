# Known Issues and Future Work

**Last Updated**: 2025-10-25
**Status**: Active tracking document for blockers, bugs, and optimization opportunities

**📌 For comprehensive status, see [CURRENT_STATE.md](CURRENT_STATE.md) and [docs/issues/BACKEND_STATUS.md](docs/issues/BACKEND_STATUS.md)**

---

## Critical Issues (Blocking Progress)

### 1. ✅ RESOLVED: ICS Blocker: H2 - DecorationApplication Bug (lift-sys-310)

**Discovered**: 2025-10-25
**Resolved**: 2025-10-25
**Severity**: **P1 CRITICAL** (was blocking ICS Phase 1)
**Status**: ✅ **RESOLVED**

**Details**:
- Decorations not applying correctly in ProseMirror editor
- Root cause: Plugin closure captured initial semanticAnalysis value (null)
- Fix: Used ref to always read current value
- Additional fixes: CSS class name mismatches, mock patterns, constraint positions

**Resolution**:
- 4 commits fixing decoration application
- Test improvement: 55% → 77% pass rate (10 failed → 5 failed)
- 5 of 9 target tests now passing (entities, modals, constraints, tooltips)
- Core H2 blocker completely resolved

**Remaining**:
- 3 typed hole tests (widget positioning, P2 refinement)
- 1 autocomplete test (H5, separate issue)
- 1 integration timing test (likely flakiness)

**Impact**:
- ✅ ICS Phase 1 can now proceed
- ✅ Real-time semantic analysis working
- ✅ Semantic highlighting functional
- ✅ Zone B (STEP-04 through STEP-07) unblocked

**Documentation**: `docs/planning/STEP_03_H2_FIX_SUMMARY.md`
**Tracking**: Beads issue lift-sys-310 (closed)

---

### 2. ICS Blocker: H5 - Autocomplete Popup Bug (lift-sys-316)

**Discovered**: 2025-10-25 (ICS Phase 4 planning)
**Severity**: **P2 CRITICAL** (blocks ICS autocomplete)
**Status**: Identified, fix pending

**Details**:
- Autocomplete popup not displaying correctly
- Blocks STEP-09 in ICS execution plan (3-hour fix estimated)
- Blocks autocomplete testing and E2E preparation

**Impact**:
- ICS autocomplete feature non-functional
- User experience for typed hole resolution degraded

**Priority**: **P1** (high priority blocker)
**Tracking**: Beads issue lift-sys-316, ICS execution plan STEP-09

---

## Backend Persistent Failures

### 3. find_index - Off-by-One Error

**Severity**: **P1** (80% success rate degraded)
**Status**: Root cause identified, fix pending

**Details**:
- Function: Find index of element in list
- Expected: `find_index([1, 2, 3], 2) → 1`
- Actual: Returns incorrect index (off-by-one error)
- Root Cause: IR generation or code template issue with index calculation

**Impact**:
- Contributes to 20% execution failure rate
- Affects list operation correctness

**Priority**: **P1** (backend stabilization)
**Tracking**: `docs/testing/PERSISTENT_FAILURES_ANALYSIS.md`

---

### 4. get_type_name - Type Handling

**Severity**: **P1** (80% success rate degraded)
**Status**: Root cause identified, fix pending

**Details**:
- Function: Get name of Python type
- Expected: `get_type_name(int) → "int"`, `get_type_name(str) → "str"`
- Actual: Incorrect type name handling
- Root Cause: IR type representation or code generation gap

**Impact**:
- Contributes to 20% execution failure rate
- Affects type introspection operations

**Priority**: **P1** (backend stabilization)
**Tracking**: `docs/testing/PERSISTENT_FAILURES_ANALYSIS.md`

---

### 5. is_valid_email - Edge Case Validation

**Severity**: **P2** (specific edge cases)
**Status**: Root cause identified, fix pending

**Details**:
- Function: Validate email address
- Expected: Handle all RFC-compliant emails
- Actual: Fails on edge cases (special characters, internationalization)
- Root Cause: Incomplete validation logic in generated code

**Impact**:
- Contributes to 20% execution failure rate (occasionally)
- Affects email validation correctness

**Priority**: **P2** (backend quality)
**Tracking**: `docs/testing/PERSISTENT_FAILURES_ANALYSIS.md`

---

## Infrastructure Uncertainty

### 6. XGrammar Status Unclear

**Discovered**: 2025-10-25 (cleanup review)
**Severity**: **P1** (foundation uncertainty)
**Status**: Investigation needed

**Details**:
- Constrained generation system (XGrammar) may not be fully functional
- Recent work included llguidance migration attempts
- Experiments with bigger instances and different models suggest issues
- May be contributing to 20% execution failures

**Impact**:
- IR generation semantic correctness uncertain
- Backend reliability foundation unclear
- May require migration to llguidance

**Priority**: **P1** (investigate immediately)
**Tracking**: See `docs/issues/BACKEND_STATUS.md` Root Cause Analysis

---

## Known Gaps (132 Backend Issues)

### 7. Backend Implementation Gaps

**Discovered**: 2025-10-25 (Beads triage)
**Severity**: **P2** (systematic gaps)
**Status**: Tracked, prioritization needed

**Details**:
- 132 Beads issues labeled `backend-gap` represent incomplete features
- Distribution across phases:
  - Phase 1 (NLP → IR): 27 issues
  - Phase 2 (Validation): 18 issues
  - Phase 3 (Code Gen): 21 issues
  - Phase 4 (AST Repair): 20 issues
  - Phase 5 (Assertions): 18 issues
  - Phase 6 (Symbolic): 15 issues
  - Phase 7 (Constraints): 9 issues
  - Phase 8 (Learning): 6 issues

**Impact**:
- Many features designed but not implemented
- Edge cases not handled
- Integration points missing
- Performance optimizations needed

**Priority**: **P2** (systematic closure)
**Tracking**: Beads issues with `backend-gap` label, see `docs/issues/BACKEND_STATUS.md`

---

## Future Optimization Opportunities

### 3. Phase 3.3: IR Generation Quality Improvement

**Status**: Planned but deferred
**Priority**: P2

**Goal**: Reduce false positive constraint generation at IR creation time

**Approach**:
1. Improve IR generation prompts to distinguish semantic vs structural requirements
2. Guide IR generator toward Assertions for semantic requirements
3. Reserve PositionConstraints for actual code structure checks

**Current Workaround**: Phase 3.2 semantic filtering successfully eliminates false positives at validation time

**Why Deferred**:
- Phase 3.2 filtering achieves the goal (44% latency reduction, 43.7% cost reduction)
- Fixing at IR generation is "nice to have" but not critical
- Current approach is production-ready

**When to Revisit**:
- If semantic filtering misses edge cases
- If IR generation quality becomes a bottleneck
- During future IR prompt refinement work

**Tracking**: See PHASE3_PLANNING.md lines 183-214, PHASE3_2_RESULTS.md lines 335-344

---

### 4. Parallel Benchmark Mode Testing at Scale

**Status**: Implemented but needs validation
**Priority**: P3

**Details**:
- Parallel mode works for Phase 2 suite (10 tests)
- Need to validate with larger test suites (50+, 100+ tests)
- Need to measure actual speedup vs theoretical (4x with max-workers=4)
- Need to stress test Modal concurrency limits

**Required Work**:
1. Create larger test suite (50+ tests)
2. Run sequential vs parallel benchmarks
3. Measure actual speedup and resource usage
4. Document optimal batch sizes for different suite sizes
5. Validate result aggregation accuracy at scale

**Priority**: P3 (nice to have for performance testing)

---

## Resolved Issues (for reference)

### ✅ Phase 5: IR Interpreter Impact (RESOLVED)

**Status**: Completed October 18, 2025
**Result**: 100% detection rate achieved

Completed tasks (all closed):
- lift-sys-243: IR Interpreter core logic
- lift-sys-244: Comprehensive test suite
- lift-sys-245: Integration with ValidatedCodeGenerator
- lift-sys-246: Testing on 3 failing cases
- lift-sys-247: Impact measurement

**Outcome**: IR Interpreter successfully validates semantics before code generation

---

### ✅ Phase 3.1: Loop Constraint False Positives (RESOLVED)

**Status**: Completed October 18, 2025
**Result**: 24.5% latency reduction

**Solution**: Filter loop constraints when IR has no loop-related effects

---

### ✅ Phase 3.2: Semantic Position Constraint False Positives (RESOLVED)

**Status**: Completed October 18, 2025
**Result**: 25.8% additional latency reduction (44.0% total)

**Solution**: Enhanced semantic filtering with keyword detection and output value pattern detection

---

## Review Schedule

**Monthly Review**: First Monday of each month
- Review active issues
- Update priorities based on impact
- Move resolved issues to archive
- Add newly discovered issues

**Next Review**: November 4, 2025

---

## Issue Prioritization Guide

**P0 (Critical)**: Blocking production deployment or causing data loss
**P1 (High)**: Significant performance impact or user-facing bugs
**P2 (Medium)**: Optimization opportunities, minor bugs, polish
**P3 (Low)**: Nice-to-have features, future improvements

---

**Maintained by**: Development team
**Format**: Markdown
**Location**: `/Users/rand/src/lift-sys/KNOWN_ISSUES.md`
