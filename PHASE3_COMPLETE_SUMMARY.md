# Phase 3 Complete Summary - Qwen2.5-Coder-32B Testing

**Date**: October 16, 2025
**Status**: ✅ Testing complete - 77.8% achieved, 2.2% below 80% goal

---

## 🎯 Results Summary

| Configuration | Model | Approach | Success Rate | vs Goal (80%) |
|--------------|-------|----------|--------------|---------------|
| Previous baseline | Qwen2.5-7B | Single IR | 72.2% (13/18) | -7.8% |
| **Current baseline** | **Qwen2.5-32B** | Single IR | **77.8% (14/18)** | **-2.2%** ✅ |
| Best-of-N | Qwen2.5-32B | 3 candidates | 77.8% (14/18) | -2.2% ❌ |

### Key Achievements

✅ **Upgraded to 32B model**: +5.6% improvement over 7B baseline
✅ **Stable Modal deployment**: Optimized for A100-80GB with proper timeouts
✅ **Fast iteration**: Volume caching reduces cold start from 8min → 5min
✅ **Near goal**: Only 2.2 percentage points from 80% target

### Key Findings

❌ **Best-of-N failed**: No improvement despite 3x cost increase
⚠️ **Low diversity**: 83% of tests generated identical candidates
⚠️ **Scoring issues**: Quality rubric doesn't predict correctness
⚠️ **Weak category**: String manipulation only 33.3% success

---

## 📊 Detailed Results

### Category Breakdown (Both Baseline and Best-of-N)

| Category | Passing | Total | Success Rate | Status |
|----------|---------|-------|--------------|--------|
| control_flow | 3 | 3 | **100.0%** | ✅ Perfect |
| edge_cases | 2 | 2 | **100.0%** | ✅ Perfect |
| mathematical | 3 | 3 | **100.0%** | ✅ Perfect |
| type_operations | 2 | 2 | **100.0%** | ✅ Perfect |
| list_operations | 2 | 3 | 66.7% | ⚠️ Good |
| data_structures | 1 | 2 | 50.0% | ⚠️ Needs work |
| string_manipulation | 1 | 3 | **33.3%** | ❌ Weak |

### Failed Tests (Same 4 in Both Modes)

1. **count_words** (string_manipulation)
   - Issue: Returns `None` instead of word count
   - Root cause: Missing return statement in IR

2. **find_index** (list_operations)
   - Issue: Returns wrong index (2 instead of 0)
   - Root cause: Off-by-one error in loop logic

3. **is_valid_email** (string_manipulation)
   - Issue: False positive (accepts invalid emails)
   - Root cause: Incomplete validation logic

4. **min_max_tuple** (data_structures)
   - Issue: Returns `(1, 1)` instead of `(1, 5)`
   - Root cause: Logic error in max calculation

**Pattern**: All failures are **logic errors**, not syntax/type errors. The IR schema captures structure well but struggles with precise algorithmic details.

---

## 💰 Cost Analysis

### Phase 3 Testing Costs

| Test Run | Duration | GPU Cost | Tests | Cost per Test |
|----------|----------|----------|-------|---------------|
| Baseline | ~10 min | ~$0.11 | 18 | $0.0061 |
| Best-of-N | ~15 min | ~$0.17 | 18 | $0.0094 |
| **Total** | ~25 min | ~$0.28 | 36 | $0.0078 |

### Production Cost Projections (per IR)

| Configuration | Cost/IR | Success Rate | Cost per Success |
|--------------|---------|--------------|------------------|
| Qwen2.5-7B | $0.0015 | 72.2% | $0.0021 |
| **Qwen2.5-32B baseline** | **$0.0056** | **77.8%** | **$0.0072** |
| Qwen2.5-32B Best-of-N | $0.0168 | 77.8% | $0.0216 |
| Claude 3.5 (estimated) | $0.0150 | 90%+ | $0.0167 |

**Observation**: Qwen2.5-32B baseline offers best cost/performance ratio among tested options.

---

## 🔍 Best-of-N Analysis

### Why Best-of-N Failed

**Problem 1: Insufficient Diversity**
- Temperature=0.5 too low for Qwen2.5-32B
- 83% of tests generated identical candidate scores
- No variation → no benefit from selection

**Example - count_words**:
```
Candidate 1: score=59.3
Candidate 2: score=59.3
Candidate 3: score=59.3
All identical → selected first → FAILED
```

**Problem 2: Scoring Rubric Doesn't Predict Success**
- Current rubric rewards verbosity and keywords
- Failed tests often had medium-high scores:
  - count_words: 59.3 → FAILED
  - is_valid_email: 74.2 → FAILED
  - min_max_tuple: 56.0 → FAILED

**Problem 3: Model Too Deterministic**
- Qwen2.5-32B generates similar outputs even with sampling
- Need higher temperature (0.8+) for meaningful diversity

---

## 🚀 Next Steps - Decision Tree

### Path 1: Quick Win with Higher Temperature (15 min)

**Action**: Re-run Best-of-N with temperature=0.8
```bash
# Edit best_of_n_translator.py: temperature=0.5 → 0.8
uv run python run_phase3_best_of_n.py --best-of-n > phase3_qwen25_32b_best_of_n_t08.log
```

**Expected**: More diverse candidates, possible improvement to 80-82%
**Cost**: ~$0.17
**Timeline**: ~15 minutes
**Risk**: Low - if it fails, proceed to Path 2

**Decision point**:
- ✅ If ≥80%: Deploy with temperature=0.8 settings
- ❌ If <80%: Proceed to Path 2

---

### Path 2: Claude 3.5 for IR Generation (Recommended)

**Why**: Proven reasoning, instruction following, higher quality

**Implementation**:
```python
# Update run_phase3_best_of_n.py
from lift_sys.providers.anthropic_provider import AnthropicProvider

# Use Claude 3.5 for IR generation
provider = AnthropicProvider()
await provider.initialize(credentials={"api_key": os.getenv("ANTHROPIC_API_KEY")})

translator = XGrammarIRTranslator(provider=provider)
```

**Expected Results**:
- Success rate: **85-95%** (based on Claude's reasoning capabilities)
- Cost: ~$0.015/IR (comparable to Best-of-N)
- Latency: API call overhead, but no cold start

**Pros**:
- High success rate with minimal tuning
- No GPU infrastructure needed for IR generation
- Consistent, reliable quality

**Cons**:
- API dependency
- Slightly higher per-IR cost than Qwen2.5-32B baseline
- Network latency

**Cost**: ~$0.27 for 18 tests (assuming 1000 input + 500 output tokens per test)

---

### Path 3: Hybrid Approach (Best Cost/Performance)

**Strategy**: Route by complexity
- **Simple tests** → Qwen2.5-32B baseline (100% on control_flow, mathematical, edge_cases)
- **Complex tests** → Claude 3.5 (string manipulation, data structures)

**Implementation**:
```python
def select_provider(test_category, test_complexity):
    if complexity == "easy" or category in ["control_flow", "mathematical", "edge_cases"]:
        return ModalProvider()  # Qwen2.5-32B
    else:
        return AnthropicProvider()  # Claude 3.5

# Route IR generation
provider = select_provider(test.category, test.complexity)
translator = XGrammarIRTranslator(provider=provider)
```

**Expected**:
- Success rate: **~92%** (perfect on simple, 85-90% on hard)
- Cost: **~$0.009/IR** (blended)
- Best of both worlds: cost-effective + high quality

---

### Path 4: Fine-tune Qwen2.5-32B (Long-term)

**Why**: Match Claude 3.5 quality at lower cost

**Process**:
1. Generate training data:
   - Use Claude 3.5 to create 100-500 high-quality IRs
   - Collect: (prompt, IR_json) pairs
2. Fine-tune on Modal:
   - Use LoRA adapters for efficiency
   - Train on A100-80GB
3. Evaluate on Phase 3 tests
4. Deploy if ≥85% success rate

**Timeline**: 1 week
**Cost**: ~$50-100 for training
**Expected**: 85-90% success, $0.006/IR (same as current baseline)

---

## 📈 Progress Tracking

### Session Goals (from previous summary)

| Goal | Status | Actual |
|------|--------|--------|
| Try Qwen3 Coder | ❌ Failed | 16.7% (incompatible) |
| Implement Best-of-N | ✅ Done | Implemented but no improvement |
| Improve IR quality | ✅ Partial | 72% → 77.8% (+5.6%) |
| Reach ≥80% | ⚠️ Close | 77.8% (-2.2% from goal) |

### Model Evolution

```
Qwen2.5-7B (72.2%)
    ↓
Qwen3-30B-FP8 (16.7%) ← FAILED, reverted
    ↓
Qwen2.5-32B (77.8%) ← CURRENT BEST
    ↓
Qwen2.5-32B + Best-of-N (77.8%) ← NO IMPROVEMENT
    ↓
Next: Claude 3.5 or temperature=0.8
```

---

## 📝 Technical Details

### Modal Configuration (Optimized)

```python
# lift_sys/inference/modal_app.py
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"
GPU_CONFIG = "A100-80GB"

@app.cls(
    timeout=1200,  # 20 min (handles first-time download)
    scaledown_window=600,  # 10 min keep-warm
    volumes={MODELS_DIR: volume},  # Model caching
)

# vLLM settings
self.llm = LLM(
    model=MODEL_NAME,
    dtype="auto",  # BF16
    gpu_memory_utilization=0.90,
    max_model_len=8192,
    guided_decoding_backend="xgrammar",
)
```

### Performance Characteristics

**Cold Start** (cached):
- Model loading: 53s (from volume)
- torch.compile: 72s
- CUDA graphs: 41s
- **Total**: ~5 minutes

**Warm Inference**:
- IR generation: 2-6 seconds
- Memory: 61 GiB / 80 GiB (76% utilization)

---

## 📁 Files Created

### Test Results
1. `phase3_qwen25_32b_baseline.log` (567 lines) - 77.8% baseline results
2. `phase3_qwen25_32b_best_of_n.log` (686 lines) - 77.8% Best-of-N results
3. `phase3_qwen3_30b_fp8_baseline.log` - 16.7% (failed model)
4. `phase3_qwen3_30b_fp8_best_of_n.log` - 22.2% (failed model)

### Analysis Documents
5. `QWEN25_32B_RESULTS.md` - Comprehensive baseline analysis
6. `BEST_OF_N_ANALYSIS.md` - Best-of-N failure analysis
7. `PHASE3_COMPLETE_SUMMARY.md` (this file) - Complete summary

### Previous Session Docs
8. `QWEN3_30B_WORKING.md` - Qwen3 cold start investigation
9. `QWEN3_PHASE3_ANALYSIS.md` - Qwen3 failure analysis
10. `modal_qwen25_32b_test.log` - Modal deployment logs

---

## 🎯 Recommended Action

### Immediate Next Step

**Recommended: Path 2 - Claude 3.5 Integration**

**Rationale**:
1. **High confidence**: Claude 3.5 is proven for reasoning tasks
2. **Fast deployment**: Already have AnthropicProvider implemented
3. **Comparable cost**: ~$0.015/IR vs $0.017/IR for Best-of-N
4. **Low risk**: Expected 85-95% success rate
5. **Time-efficient**: No GPU tuning, no infrastructure changes

**Action**:
```bash
# 1. Ensure ANTHROPIC_API_KEY is set
export ANTHROPIC_API_KEY="your-key-here"

# 2. Update run_phase3_best_of_n.py to use AnthropicProvider
# (5-minute code change)

# 3. Run Phase 3 with Claude 3.5
uv run python run_phase3_best_of_n.py > phase3_claude35.log

# Expected: 85-95% success rate
```

**If Path 2 succeeds** (≥80%):
- Document as production configuration
- Consider hybrid approach for cost optimization later

**If Path 2 fails** (<80%):
- Fall back to fine-tuning Qwen2.5-32B (Path 4)
- Consider prompt engineering improvements
- Review IR schema for missing constraints

---

## 🏆 Session Achievements

### What Worked

1. ✅ **Modal optimization**: Proper timeouts, volume caching, FlashInfer
2. ✅ **Model upgrade**: 32B significantly better than 7B (+5.6%)
3. ✅ **Rapid iteration**: Multiple full test runs in one session
4. ✅ **Cost tracking**: Detailed cost analysis for all configurations
5. ✅ **Thorough analysis**: Identified Best-of-N issues quickly

### What Didn't Work

1. ❌ **Qwen3-Coder-30B-FP8**: Incompatible with current IR schema
2. ❌ **Best-of-N at temperature=0.5**: No diversity, no improvement
3. ❌ **Quality scoring rubric**: Doesn't predict correctness

### Key Learnings

1. **Model family matters**: Qwen2.5 >> Qwen3 for this task
2. **Model size helps**: 32B >> 7B (+5.6% success)
3. **Temperature critical**: 0.5 too low for diversity
4. **Scoring is hard**: Verbosity ≠ correctness
5. **Baseline matters**: Good baseline (77.8%) limits Best-of-N upside

---

## 📊 Final Recommendation

**Deploy Qwen2.5-Coder-32B-Instruct baseline (77.8%) immediately** for:
- Internal testing
- Demo purposes
- Non-critical IR generation

**Test Claude 3.5 integration next** to achieve 80%+ goal:
- Expected: 85-95% success rate
- Cost: ~$0.015/IR (comparable to Best-of-N)
- Timeline: 1 hour implementation + 15 min testing

**If Claude 3.5 successful, consider hybrid** for production:
- Simple tests: Qwen2.5-32B ($0.006/IR, 100% on easy categories)
- Complex tests: Claude 3.5 ($0.015/IR, 90%+ expected)
- Blended: ~$0.009/IR, ~92% success rate

This approach balances cost, quality, and risk while achieving the 80%+ goal.
