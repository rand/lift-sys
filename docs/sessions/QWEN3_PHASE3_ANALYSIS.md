# Qwen3-30B-FP8 Phase 3 Analysis

**Date**: October 16, 2025
**Status**: ⚠️ **MAJOR REGRESSION** - Requires investigation

---

## Results Summary

| Configuration | Model | Best-of-N | Success Rate | Tests Passing |
|--------------|-------|-----------|--------------|---------------|
| **Baseline (prev session)** | Qwen2.5-7B | No | **72.2%** | 13/18 |
| **Current test** | Qwen3-30B-FP8 | Yes (N=3) | **22.2%** | 4/18 |

**Regression: -50 percentage points**

---

## Failure Breakdown

### 1. Compilation Failures (4 tests - 22.2%)
Tests that failed to generate valid Python syntax:

- **letter_grade**: `invalid syntax (<unknown>, line 17)`
- **find_index**: `expected ':' (<unknown>, line 16)`
- **get_type_name**: `expected an indented block after 'if' statement on line 17`
- **min_max_tuple**: `expected an indented block after 'if' statement on line 15)`

### 2. Execution Failures (10 tests - 55.6%)
Tests that compiled but failed execution:

- **filter_even**: Returns `None` instead of filtered list
- **count_words**: Returns `None` instead of count
- **classify_number**: Returns `'zero'` for positive numbers
- **clamp_value**: Returns wrong values (e.g., 10 instead of 5)
- **validate_password**: Returns `'Invalid'` instead of specific errors (`'too short'`, `'no number'`, etc.)
- **average_numbers**: Returns `None` instead of average
- **is_valid_email**: False positives (accepts invalid emails)
- **fibonacci**: Off-by-one errors
- **is_prime**: False negatives (says primes aren't prime)
- **safe_int_conversion**: Returns `None` instead of `0`

### 3. Passing Tests (4 tests - 22.2%)

- ✅ **first_or_none** (edge_cases)
- ✅ **title_case** (string_manipulation)
- ✅ **factorial** (mathematical)
- ✅ **merge_dictionaries** (data_structures)

---

## Root Cause Analysis

### Key Observation: "Unresolved Holes"
Many tests show: `⚠ IR contains X unresolved holes, attempting to clear them...`

This indicates **incomplete IRs** with missing logic.

### Primary Hypothesis: IR Quality Issue
The problem appears to be **IR generation quality**, not code generation:

1. **Missing return statements**: Functions return `None` → IR didn't specify return values
2. **Incomplete control flow**: Syntax errors → IR has gaps in if/else logic
3. **Wrong literal values**: Wrong error messages → IR didn't capture exact strings

### Why is Qwen3-30B-FP8 worse than Qwen2.5-7B?

**Possible explanations:**

1. **Model compatibility**: Qwen3 may not respond well to the current IR schema/prompt
2. **Temperature mismatch**: Best-of-N uses `temperature=0.5` vs baseline's `0.3` → more diverse but less precise?
3. **FP8 quantization effects**: Reduced precision affecting logical reasoning
4. **Prompt engineering**: The prompt optimized for Qwen2.5 may not work for Qwen3
5. **Schema interpretation**: Qwen3 may interpret the JSON schema differently

---

## Test-Time Patterns

### Best-of-N Selection
From logs:
- **letter_grade**: Candidate 1: 132.3, Candidate 2: 132.2 (high scores but failed)
- **get_type_name**: Candidate 1/2: 137.3, Candidate 3: 107.3 (high scores but failed)
- **validate_password**: Candidate 1/2: 129.7, Candidate 3: 124.7 (high scores but failed)

**Insight**: High quality scores don't correlate with success! The scoring rubric may be rewarding verbose/complex IRs that don't actually work.

### Quality Score Issues
The scoring rubric rewards:
- Assertion count
- Effect detail length
- Literal keywords
- Python quirk mentions
- Edge case keywords

**Problem**: These metrics don't correlate with **correct functional logic**. An IR can score high by having many assertions/effects but still have incomplete return logic.

---

## Cost Analysis

**Test duration**: ~10 minutes total (18 tests with cold start)
**Cost**: ~$0.03 total ($0.001-0.002 per test)
**Success rate**: 22.2% (4/18)
**Cost per successful test**: $0.0075

vs. Baseline:
- **Qwen2.5-7B**: 72.2% success, ~$0.0015 per successful test
- **Qwen3-30B-FP8**: 22.2% success, ~$0.0075 per successful test (5x worse cost/success ratio)

---

## Recommended Next Steps

### Option 1: Investigate Qwen3-30B-FP8 Baseline (No Best-of-N)
**Action**: Run Phase 3 tests with Qwen3-30B-FP8 WITHOUT Best-of-N to isolate variables
**Why**: Need to know if the issue is Qwen3 itself or the Best-of-N interaction
**Expected**: If baseline Qwen3 is also <50%, the model is the problem

### Option 2: Fix Best-of-N Scoring Rubric
**Problem**: Current scoring rewards complexity, not correctness
**Action**: Revise scoring to prioritize:
- Completeness of return statements
- Proper control flow coverage
- Concrete values over abstract descriptions

### Option 3: Revert to Qwen2.5-7B + Best-of-N
**Action**: Test if Best-of-N improves the working baseline
**Expected**: 72% → 78-82% (more conservative than 90% goal, but validates approach)

### Option 4: Improve Qwen3 Prompt Engineering
**Action**: Adapt the IR generation prompt for Qwen3's strengths
**Research needed**:
- Check Qwen3 model card for recommended prompt formats
- Test with explicit "MUST include return statement" instructions
- Try few-shot examples with complete IRs

### Option 5: Use Claude 3.5 for IR Generation
**Action**: Switch to AnthropicProvider for IR generation (already implemented)
**Pros**: Known to work, higher quality, no GPU cold start
**Cons**: Higher cost (~$3/1M tokens vs $0.15/1M), API latency
**Expected**: 85-95% success rate

---

## Immediate Recommendation

**Priority 1**: Run Qwen3-30B-FP8 baseline (no Best-of-N) to isolate the root cause
```bash
uv run python run_phase3_best_of_n.py > phase3_qwen3_30b_fp8_baseline_rerun.log
```

**Priority 2**: If Qwen3 baseline is also poor (<50%), revert to Qwen2.5-7B and test Best-of-N there
```bash
# Update modal_app.py back to Qwen2.5-7B
# Then run: uv run python run_phase3_best_of_n.py --best-of-n
```

**Priority 3**: If Best-of-N doesn't help on Qwen2.5-7B either, the scoring rubric needs work

---

## Files for Reference

- Test results: `phase3_qwen3_30b_fp8_best_of_n.log`
- Modal config: `lift_sys/inference/modal_app.py`
- Best-of-N implementation: `lift_sys/forward_mode/best_of_n_translator.py`
- Quality scoring: `best_of_n_translator.py:122-217`
- Test runner: `run_phase3_best_of_n.py`

---

## Questions for User

1. **Should we revert to Qwen2.5-7B** to test if Best-of-N works on the known-good baseline?
2. **Should we debug Qwen3-30B further** with baseline tests and prompt engineering?
3. **Should we escalate to Claude 3.5** for IR generation given the time constraints?
4. **Do you want to see specific failed IR examples** to understand what Qwen3 is generating?
