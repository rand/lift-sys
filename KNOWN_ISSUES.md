# Known Issues and Future Work

**Last Updated**: 2025-10-18
**Status**: Active tracking document for deferred issues and optimizations

---

## Active Issues

### 1. fibonacci Regression in Phase 3.2 (+23.8% latency)

**Discovered**: October 18, 2025 (Phase 3.2 testing)
**Severity**: Low (isolated to single test)
**Status**: Monitoring

**Details**:
- fibonacci latency increased from 100.80s (Phase 3.1) to 124.81s (Phase 3.2)
- Regression: +23.8% (+23.9s)
- Constraint filtering removed 1 constraint, but generation took longer

**Evidence**:
```
Phase 3.1: ✓ Success: 91432.24ms (no filtering)
Phase 3.2: 🔧 Filtered constraints: 1 → 0 (1 non-applicable)
           ✓ Success: 115315.39ms
```

**Hypotheses**:
1. Statistical variance in LLM generation (fibonacci is complex, recursive logic)
2. Filtered constraint may have been helpful for guiding code structure
3. Single-sample benchmark noise (no warmup specifically for fibonacci)

**Investigation Plan** (deferred):
1. Run fibonacci-only benchmark 10 times with Phase 3.2 filtering
2. Calculate mean and variance vs Phase 3.1 baseline
3. Inspect generated code quality (AST repairs needed?)
4. Check if constraint description had beneficial guidance
5. Consider fibonacci-specific constraint tuning if regression persists

**Priority**: P2 (monitor in future benchmarks)
**Tracking**: See PHASE3_2_RESULTS.md lines 169-210

---

### 2. Result Aggregation for Parallel Benchmarks (lift-sys-232)

**Discovered**: October 18, 2025 (parallel benchmark work)
**Severity**: Low (feature incomplete)
**Status**: In progress (but can be deferred)

**Details**:
- Parallel benchmark execution works (lift-sys-231 closed)
- Result aggregation function needed to combine results from isolated instances
- CLI flags implemented (lift-sys-233 closed)
- Aggregation task still marked in_progress

**Current State**:
- Parallel execution: ✅ Working
- Isolated instances: ✅ Working
- Result aggregation: ⚠️ Incomplete

**Required Work**:
- Implement `aggregate_results()` function
- Merge BenchmarkResult lists from multiple instances
- Generate single BenchmarkSummary with correct statistics
- Preserve all timing and cost data

**Priority**: P2 (parallel mode works, aggregation is polish)
**Tracking**: Beads issue lift-sys-232

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
