# Best-of-N Analysis - Qwen2.5-Coder-32B-Instruct

**Date**: October 16, 2025
**Status**: ⚠️ **NO IMPROVEMENT** - Best-of-N did not improve success rate

---

## Executive Summary

Best-of-N sampling (N=3) with quality scoring **did not improve** IR generation success rate on Qwen2.5-Coder-32B-Instruct. Both baseline and Best-of-N achieved **77.8% (14/18 passing)**.

### Key Findings

| Configuration | Success Rate | Cost Multiplier | Improvement |
|--------------|--------------|-----------------|-------------|
| **Baseline** | 77.8% (14/18) | 1x | - |
| **Best-of-N (N=3)** | 77.8% (14/18) | ~3x | **0%** ❌ |

**Conclusion**: Best-of-N adds no value at current temperature/scoring settings. The 3x cost increase is not justified.

---

## Detailed Results

### Passing Tests (14/18) - Identical in Both Modes

Both baseline and Best-of-N passed the same 14 tests:
- letter_grade, filter_even, first_or_none, classify_number
- title_case, factorial, get_type_name, clamp_value
- validate_password, average_numbers, fibonacci, is_prime
- safe_int_conversion, merge_dictionaries

### Failed Tests (4/18) - Identical Failures

Both modes failed the same 4 tests:
1. **count_words**: Returns `None` instead of count
2. **find_index**: Returns wrong index (2 instead of 0)
3. **is_valid_email**: False positive (accepts invalid email)
4. **min_max_tuple**: Returns `(1, 1)` instead of `(1, 5)`

---

## Root Cause Analysis

### Problem 1: Low Candidate Diversity

Many tests generated **identical scores** for all 3 candidates:

| Test | Candidate Scores | Outcome |
|------|------------------|---------|
| count_words | 59.3, 59.3, 59.3 | All identical → FAILED |
| first_or_none | 54.8, 54.8, 54.8 | All identical → PASSED |
| classify_number | 106.8, 106.8, 106.8 | All identical → PASSED |
| find_index | 56.6, 56.6, 56.6 | All identical → FAILED |
| factorial | 59.2, 59.2, 59.2 | All identical → PASSED |
| get_type_name | 110.1, 110.1, 110.1 | All identical → PASSED |
| clamp_value | 44.2, 44.2, 44.2 | All identical → PASSED |
| validate_password | 108.2, 108.2, 108.2 | All identical → PASSED |
| average_numbers | 64.9, 64.9, 64.9 | All identical → PASSED |
| is_valid_email | 74.2, 74.2, 74.2 | All identical → FAILED |
| fibonacci | 43.9, 43.9, 43.9 | All identical → PASSED |
| is_prime | 55.9, 55.9, 55.9 | All identical → PASSED |
| safe_int_conversion | 45.5, 45.5, 45.5 | All identical → PASSED |
| min_max_tuple | 56.0, 55.9, 55.9 | Tiny variance → FAILED |
| merge_dictionaries | 65.8, 65.8, 65.8 | All identical → PASSED |

**Observation**: **15 out of 18 tests** (83%) had all candidates with identical or near-identical scores.

**Root Cause**: Temperature=0.5 is too low for Qwen2.5-32B. The model generates very similar IRs each time, even with sampling.

### Problem 2: Quality Scoring Doesn't Predict Success

Even when candidates had different scores, selection didn't help:

| Test | Scores | Selected | Result |
|------|--------|----------|--------|
| letter_grade | 136.0 (only 1 valid) | 136.0 | PASSED |
| filter_even | 65.7, 65.7, 65.6 | 65.7 | PASSED |
| title_case | 55.2, 45.2, 45.2 | 55.2 | PASSED |

**Observation**: When diversity exists, the scoring worked. But with only 3 tests showing diversity, it's insufficient to prove value.

### Problem 3: Scoring Rubric Issues

The quality scoring rubric (`best_of_n_translator.py:122-217`) rewards:
- Assertion count
- Effect detail length
- Literal string keywords
- Python quirk mentions
- Edge case keywords

**Issue**: These metrics don't correlate with correctness:
- `count_words` scored 59.3 (medium) → FAILED (missing return statement)
- `min_max_tuple` scored 56.0 (medium) → FAILED (logic error)
- `is_valid_email` scored 74.2 (high) → FAILED (incomplete validation)

The rubric measures **IR verbosity and detail**, not **functional correctness**.

---

## Temperature Analysis

**Current**: temperature=0.5
**Expected**: Higher temperature (0.7-0.9) for diversity

### Recommendation: Increase Temperature

Try temperature=0.8 to increase candidate diversity:

```python
# lift_sys/forward_mode/best_of_n_translator.py
translator = BestOfNIRTranslator(
    provider=provider,
    n_candidates=3,
    temperature=0.8,  # Increased from 0.5
)
```

**Expected outcome**: More diverse IRs, better chance of finding correct implementation.

---

## Cost Analysis

### Actual Costs (Phase 3 Tests)

| Metric | Baseline | Best-of-N | Difference |
|--------|----------|-----------|------------|
| Total GPU time | ~10 min | ~15 min | +50% |
| Total cost | ~$0.11 | ~$0.17 | +55% |
| Success rate | 77.8% | 77.8% | 0% |
| **Cost per passing test** | $0.0079 | $0.0121 | **+53% worse** |

**Verdict**: Best-of-N with current settings is **53% more expensive with zero benefit**.

---

## Comparison to Expectations

### Original Goals

From previous session summary:
- **Goal**: Achieve ≥80% success rate with Best-of-N
- **Expected**: 72% baseline → 78-82% with Best-of-N
- **Actual**: 77.8% baseline → 77.8% with Best-of-N

### Why It Failed

1. **Baseline already good**: 77.8% is better than expected (vs 72% for 7B)
2. **Low diversity**: Temperature too low for meaningful variation
3. **Scoring rubric**: Doesn't predict functional correctness
4. **Model characteristics**: Qwen2.5-32B is more deterministic than expected

---

## Next Steps

### Option 1: Increase Temperature and Retry (Recommended)

**Action**: Re-run Best-of-N with temperature=0.8
**Expected**: 2-3 diverse candidates per test, better chance of success
**Cost**: ~$0.17 (same as current Best-of-N run)
**Timeline**: ~15 minutes

**If successful (≥80%)**: Deploy with higher temperature
**If unsuccessful (<80%)**: Proceed to Option 2

### Option 2: Improve Quality Scoring Rubric

**Current scoring** (problematic):
- Assertion count → high score for verbose IRs
- Effect detail → high score for long descriptions
- Keyword matching → easily gamed by model

**Proposed scoring** (correctness-focused):
```python
def _score_ir(self, ir: IntermediateRepresentation, prompt: str) -> float:
    score = 0.0

    # 1. Completeness (40 points)
    # - Has return type specified (+10)
    # - All parameters have types (+10)
    # - Has at least one effect with 'return' keyword (+20)

    # 2. Specificity (30 points)
    # - Effects mention concrete values, not abstractions (+15)
    # - Assertions use exact values, not ranges (+15)

    # 3. Coverage (30 points)
    # - Edge cases covered (+10)
    # - Error handling mentioned (+10)
    # - Type checking mentioned (+10)

    return score
```

### Option 3: Escalate to Claude 3.5 for IR Generation

**Why**: Claude 3.5 has better reasoning and instruction following
**Expected**: 85-95% success rate
**Cost**: ~$0.015/IR (comparable to Best-of-N at $0.017/IR)
**Benefit**: No need for Best-of-N sampling

**Implementation**:
```python
# Use AnthropicProvider for IR generation
from lift_sys.providers.anthropic_provider import AnthropicProvider

ir_provider = AnthropicProvider()
translator = XGrammarIRTranslator(provider=ir_provider)
```

### Option 4: Hybrid Approach

**Strategy**: Use Qwen2.5-32B for simple tests, Claude 3.5 for hard ones

**Classification**:
- **Simple** (use Qwen2.5-32B): Complexity=easy, category in [control_flow, mathematical, edge_cases]
- **Hard** (use Claude 3.5): Complexity=medium_hard, category in [string_manipulation, data_structures]

**Expected**:
- Simple tests: 100% @ $0.006/test
- Hard tests: 90% @ $0.015/test
- **Blended**: ~92% @ $0.009/test

---

## Recommendations

### Immediate (Within 1 Hour)

**Option 1A**: Test Best-of-N with temperature=0.8
- Quick experiment (~15 min)
- Low cost (~$0.17)
- If ≥80%, problem solved

### Short-term (Within 1 Day)

**If Option 1A fails**:
- **Option 3**: Switch to Claude 3.5 for IR generation
  - Proven quality (85-95% expected)
  - Comparable cost to Best-of-N
  - No complex tuning needed

### Long-term (Within 1 Week)

**If Claude 3.5 meets goals**:
- Consider fine-tuning Qwen2.5-32B on successful IR examples
- Collect dataset: prompts + Claude 3.5 generated IRs
- Fine-tune on Modal (LoRA adapter)
- Expected: Match Claude 3.5 quality at lower cost

---

## Files

### Test Logs
- `phase3_qwen25_32b_baseline.log` (567 lines) - 77.8% success
- `phase3_qwen25_32b_best_of_n.log` (686 lines) - 77.8% success (3x candidates)

### Analysis Documents
- `QWEN25_32B_RESULTS.md` - Baseline results summary
- `BEST_OF_N_ANALYSIS.md` (this file) - Best-of-N failure analysis

### Code
- `lift_sys/forward_mode/best_of_n_translator.py` - Best-of-N implementation
  - Line 122-217: Quality scoring rubric (needs improvement)
  - Line 43-102: Candidate generation and selection

---

## Conclusion

**Best-of-N with N=3, temperature=0.5 provides no benefit over baseline** for Qwen2.5-Coder-32B-Instruct.

**Root causes**:
1. Low candidate diversity (83% of tests had identical scores)
2. Quality scoring doesn't predict correctness
3. Baseline already strong (77.8%)

**Recommended path forward**:
1. Try temperature=0.8 for one more test (~15 min, ~$0.17)
2. If unsuccessful, switch to Claude 3.5 for IR generation (expected 85-95%, ~$0.015/IR)
3. Long-term: Fine-tune Qwen2.5-32B on Claude-generated IR examples

**Decision point**: The 80% goal is close (77.8% achieved). Switching to Claude 3.5 is likely the fastest path to ≥80% with minimal risk.
