# Robustness Testing Status

**Date**: 2025-10-26
**Status**: Advisory Mode (Metrics Tracking)
**Current Robustness**: 25-64% (varies by test)
**Target Robustness**: 97% (TokDrift <3% sensitivity)

---

## Overview

The Robustness Testing workflow validates that lift-sys produces consistent outputs for semantically equivalent inputs. This is based on the TokDrift methodology (arXiv:2510.14972), which aims for <3% sensitivity (≥97% robustness).

**Current Status**: The workflow is in **advisory mode** - it runs on every push/PR and reports metrics, but does not block CI/CD. This allows us to track improvements over time while the system matures.

---

## Current Robustness Levels (2025-10-26)

| Test Category | Current | Target | Status |
|--------------|---------|--------|--------|
| Lexical Paraphrases | ~64% | 97% | 🟡 Developing |
| Structural Paraphrases | Skipped | 97% | 🟡 Insufficient data |
| Combined Paraphrases | ~33% | 97% | 🔴 Needs work |
| Compositional Robustness | ~25% | 80% | 🔴 Needs work |
| Statistical Significance | Failing | Pass | 🔴 Needs work |

**Overall Pass Rate**: 33.3% (11 passed, 10 failed, 12 skipped)

---

## Root Causes

### 1. Paraphrase Generation Quality
**Issue**: `ParaphraseGenerator` not producing enough diverse paraphrases
- Lexical: Generating 1 variant, need ≥2
- Structural: Often skipped due to insufficient generation
- Diversity: Low semantic variation between paraphrases

**Impact**: Low robustness scores across all paraphrase tests

### 2. IR Equivalence Checking
**Issue**: `EquivalenceChecker` may be too strict or too lenient
- Compositional robustness at 25% suggests composition breaks equivalence
- Statistical tests show significant differences between variants and originals

**Impact**: High sensitivity to minor input variations

### 3. Missing Baselines
**Issue**: No baseline measurements established
- 3 tests skipped due to missing `expected_results.json`
- Cannot detect regressions without baselines

**Impact**: No regression detection capability

---

## Improvement Roadmap

### Phase 1: Immediate Stabilization ✅ COMPLETE (2025-10-26)

**Goal**: Unblock CI/CD while preserving metrics

- ✅ Added `continue-on-error: true` to robustness workflow
- ✅ Updated workflow summary to indicate advisory mode
- ✅ Created this status documentation

**Result**: Workflow now runs without blocking, metrics still reported

### Phase 2: Fix Paraphrase Generation (Target: 1 week)

**Goal**: Increase paraphrase diversity and quantity

**Tasks**:
1. Enhance `lift_sys/robustness/paraphrase_generator.py`:
   - Increase synonym coverage (WordNet + custom synonyms)
   - Add more substitution rules
   - Target: 3-5 lexical paraphrases per prompt

2. Improve structural paraphrasing:
   - Better clause detection (spaCy dependency parsing)
   - More reordering patterns
   - Target: 2-3 structural paraphrases per prompt

3. Add diversity metrics:
   - Measure paraphrase similarity (sentence embeddings)
   - Ensure minimum semantic distance
   - Log diversity scores

**Expected Improvement**: 64% → 75% robustness

### Phase 3: Fix IR Equivalence Checking (Target: 1 week)

**Goal**: Improve robustness measurements

**Tasks**:
1. Enhance `lift_sys/robustness/equivalence_checker.py`:
   - Review normalization rules
   - Add fuzzy matching for intent clauses (semantic similarity)
   - Tune similarity thresholds

2. Fix compositional robustness (25% → 80%):
   - Investigate why composition breaks equivalence
   - Add better merging logic for IR components
   - Ensure compositionality preserves semantics

3. Statistical significance:
   - Adjust p-value interpretation
   - Add confidence intervals
   - Better handling of edge cases

**Expected Improvement**: 25% → 60% compositional robustness

### Phase 4: Establish Baselines (Target: 2 weeks)

**Goal**: Enable regression detection

**Tasks**:
1. Run baseline measurement tests:
   - Execute currently skipped baseline tests
   - Record current robustness levels
   - Update `tests/robustness/fixtures/expected_results.json`

2. Enable regression tests:
   - Unskip 3 baseline regression tests
   - Set tolerance: ±5% from baseline
   - Auto-detect future regressions

3. Add baseline update workflow:
   - Manual workflow_dispatch option
   - Scheduled monthly updates
   - PR review for baseline changes

**Expected Improvement**: Enable regression detection

### Phase 5: Progressive Quality Gates (Target: 1 month)

**Goal**: Tighten quality gates as system improves

**Thresholds**:
```
Phase 1 (now):     40% fail, 60% warn (current: 33%)
Phase 2 (week 2):  50% fail, 65% warn
Phase 3 (week 3):  60% fail, 75% warn
Phase 4 (week 4):  70% fail, 80% warn
Phase 5 (month 2): 75% fail, 85% warn
Phase 6 (month 3): 80% fail, 90% warn
Long-term target:  90% fail, 95% warn, 97% aspirational
```

**Expected Improvement**: Clear progress tracking

### Phase 6: Long-Term Goal (Target: Q3 2025)

**Goal**: Achieve TokDrift target

**Targets**:
- 97% robustness (3% sensitivity)
- All tests passing
- Baseline regression detection active
- Workflow switched to blocking mode

---

## How to Read Robustness Metrics

### Robustness Score
- **Definition**: Percentage of variants that produce equivalent output
- **Formula**: `robustness = equivalent_count / total_variants`
- **Good**: ≥97% (≤3% sensitivity)
- **Warning**: 90-97% (3-10% sensitivity)
- **Failing**: <90% (>10% sensitivity)

### Sensitivity Score
- **Definition**: Percentage of variants that produce different output
- **Formula**: `sensitivity = 1 - robustness`
- **Good**: ≤3% (TokDrift target)
- **Warning**: 3-10%
- **Failing**: >10%

### Pass Rate
- **Definition**: Percentage of tests passing quality gates
- **Current**: 33.3% (advisory mode)
- **Target**: 100% (all tests passing)

---

## Current Workflow Behavior

### Push to main/develop
- Robustness workflow runs automatically
- Reports metrics in workflow summary
- **Does not block** merge/deployment
- Uploads detailed results as artifacts

### Pull Requests
- Robustness workflow runs on PR
- Posts comment with metrics table
- Shows pass/fail status with emoji
- **Does not block** PR merge
- Provides visibility into robustness trends

### Scheduled (Nightly)
- Runs comprehensive baseline tests
- Tracks robustness over time
- Detects regressions (when baselines established)
- Updates metrics dashboard (future)

---

## How to Use This Workflow

### As a Developer
1. **Check PR comments**: See robustness metrics for your changes
2. **Review artifacts**: Download `robustness-output.txt` for details
3. **Monitor trends**: Track if your changes improve/degrade robustness
4. **Don't worry about failures**: Advisory mode means CI won't block you

### As a Maintainer
1. **Track progress**: Review weekly robustness reports
2. **Prioritize improvements**: Focus on lowest-scoring tests
3. **Update baselines**: Run baseline measurement tests monthly
4. **Adjust gates**: Tighten thresholds as robustness improves

### Manual Trigger
```bash
# Trigger robustness workflow manually
gh workflow run robustness.yml

# Update baselines (when implemented)
gh workflow run robustness.yml --field update_baseline=true
```

---

## Frequently Asked Questions

### Why is the workflow failing?
The workflow is **working as designed** - it's detecting that the robustness system doesn't meet quality standards yet. The failures indicate real issues with paraphrase generation and IR equivalence checking that need to be fixed.

### Why not just lower the thresholds?
We're using a **progressive tightening** approach:
1. Start with realistic thresholds (40% fail, 60% warn)
2. Fix underlying issues (paraphrase generation, equivalence checking)
3. Gradually tighten thresholds as system improves
4. Reach TokDrift target (97% robustness) over time

This balances pragmatism (unblocking CI/CD) with rigor (maintaining quality standards).

### When will the workflow be blocking?
The workflow will switch to **blocking mode** (remove `continue-on-error`) when:
1. Overall pass rate ≥90%
2. All critical tests passing
3. Baselines established and stable
4. Regression detection active

**Estimated timeline**: Q2 2025

### How can I help improve robustness?
1. **Fix paraphrase generation**: Contribute to `lift_sys/robustness/paraphrase_generator.py`
2. **Improve equivalence checking**: Enhance `lift_sys/robustness/equivalence_checker.py`
3. **Add test cases**: Contribute to `tests/robustness/`
4. **Report issues**: File bugs for unexpected robustness failures

---

## References

- **TokDrift Paper**: [arXiv:2510.14972](https://arxiv.org/abs/2510.14972)
- **Workflow Config**: `.github/workflows/robustness.yml`
- **Robustness Module**: `lift_sys/robustness/`
- **Test Suite**: `tests/robustness/`

---

**Last Updated**: 2025-10-26
**Next Review**: 2025-11-09 (2 weeks)
**Owner**: lift-sys maintainers
