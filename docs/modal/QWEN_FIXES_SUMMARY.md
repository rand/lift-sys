# Qwen vLLM Models - Fixes Applied

**Date**: 2025-10-24
**Branch**: `experiment/qwen-vllm-models`
**Status**: Ready for testing

## Issues Found

Based on the container logs you provided, two critical issues were identified:

### Issue 1: Transformers Architecture Not Recognized (80B Model)
```
ValidationError: The checkpoint you are trying to load has model type 'qwen3_next'
but Transformers does not recognize this architecture.
```

**Root cause**: The `qwen3_next` architecture is too new for transformers 4.53.0 (released version).

### Issue 2: CUDA Out of Memory (480B Model)
```
CUDA out of memory. Tried to allocate 1.17 GiB. GPU 0 has a total capacity of 79.18 GiB
of which 1.12 GiB is free. Process 1 has 78.05 GiB memory in use.
```

**Root cause**: 480B model with FP8 (~240GB) doesn't fit on 4x H100 (320GB total) due to KV cache overhead.

## Fixes Applied

### Fix 1: Install Transformers from Source

**Changed:**
```python
# Before: Pinned version
.uv_pip_install(f"transformers=={TRANSFORMERS_VERSION}")

# After: Install from git source
.run_commands("pip install --no-cache-dir git+https://github.com/huggingface/transformers.git")
```

**Impact:**
- ✅ Adds latest `qwen3_next` architecture support
- ⚠️ Adds 2-3 minutes to image build time
- ✅ Ensures compatibility with bleeding-edge Qwen models

### Fix 2: Increase GPUs for 480B Model

**Changed:**
```python
# Before: 4x H100 (320GB)
gpu="H100:4"
tensor_parallel_size=4
gpu_memory_utilization=0.85
max_model_len=8192

# After: 8x H100 (640GB) with optimizations
gpu="H100:8"
tensor_parallel_size=8
gpu_memory_utilization=0.80  # More conservative
max_model_len=32768          # Per HuggingFace docs recommendation
```

**Impact:**
- ✅ 640GB VRAM accommodates 240GB model + KV cache
- ✅ Follows HuggingFace docs recommendation (32K context if OOM)
- ⚠️ **Cost doubled**: $32/hour instead of $16/hour
- ⚠️ Longer cold start: ~20-30 minutes

### Fix 3: Optimize 80B Model Configuration

**Changed:**
```python
# Before:
gpu_memory_utilization=0.90

# After:
gpu_memory_utilization=0.85  # More conservative for stability
```

**Impact:**
- ✅ More stable model loading
- ✅ Reduces risk of OOM during KV cache growth

## Cost Impact

### Before Fixes
- 80B model: $4/hour (H100 x1)
- 480B model: $16/hour (H100 x4)

### After Fixes
- 80B model: $4/hour (H100 x1) - **unchanged**
- 480B model: $32/hour (H100 x8) - **doubled**

### Testing Budget Recommendations

**Light testing (2-3 test cases per model):**
- 80B: 30 minutes = $2
- 480B: 30 minutes = $16
- **Total: ~$18-20**

**Moderate testing (full test suites):**
- 80B: 2 hours = $8
- 480B: 1 hour = $32
- **Total: ~$40**

**Extended evaluation:**
- 80B: 4 hours = $16
- 480B: 2 hours = $64
- **Total: ~$80**

## Next Steps

### 1. Rebuild and Deploy (Required)

```bash
# Image needs rebuild due to transformers source install
modal deploy lift_sys/inference/modal_qwen_vllm.py
```

**Expected:**
- Image build: 10-12 minutes (includes transformers git install)
- 80B cold start: 8-10 minutes
- 480B cold start: 20-30 minutes

### 2. Light Testing (Recommended First)

Test just enough to validate fixes worked:

**80B Model (5-10 minutes, ~$2):**
```bash
# Test 1: Basic generation
curl -X POST https://rand--qwen-80b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms.", "max_tokens": 256}'

# Test 2: Structured output
curl -X POST https://rand--qwen-80b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "schema": {
      "type": "object",
      "properties": {"answer": {"type": "string"}},
      "required": ["answer"]
    }
  }'
```

**480B Model (10-15 minutes, ~$8-16):**
```bash
# Test 1: Code generation
curl -X POST https://rand--qwen-480b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python function for binary search.", "max_tokens": 512}'

# Test 2: Structured code output
curl -X POST https://rand--qwen-480b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Implement quicksort in Python",
    "schema": {
      "type": "object",
      "properties": {"code": {"type": "string"}},
      "required": ["code"]
    }
  }'
```

### 3. Evaluate Viability

**For 80B Model:**
- ✅ Reasonable cost ($4/hour)
- ✅ Single GPU simplicity
- ❓ Quality vs. current Qwen2.5-Coder-32B

**Decision criteria:**
- Does output quality justify cost?
- Is it better than current model?
- Worth the complexity?

**For 480B Model:**
- ⚠️ Very expensive ($32/hour = $768/day if kept warm)
- ⚠️ Complex (8-GPU tensor parallelism)
- ⚠️ Long cold starts (20-30 minutes)
- ❓ Quality needs to be SIGNIFICANTLY better to justify

**Decision criteria:**
- Is quality 8x better than 32B model? (cost ratio)
- Can you amortize cost across many requests?
- Is this for critical, high-value tasks only?

## Recommendations

### For 80B Model
**Recommendation: Worth testing**

Pros:
- Reasonable cost
- Simple single-GPU deployment
- 80B with FP8 could be sweet spot

Suggested approach:
1. Deploy and test (30 min, ~$2)
2. Compare quality with Qwen2.5-Coder-32B
3. If better: Run comprehensive tests
4. If not better: Stop deployment, stick with 32B

### For 480B Model
**Recommendation: Test cautiously**

Pros:
- Most powerful code model available
- Could be game-changer for complex tasks

Cons:
- Very expensive ($32/hour)
- Complex setup (8 GPUs)
- Long cold starts

Suggested approach:
1. Test with 1-2 complex code tasks only
2. Compare with 80B and 32B models
3. Only continue if quality is dramatically better
4. Consider using ONLY for:
   - Complex algorithm design
   - Architecture generation
   - Critical production IR generation
5. Keep scaledown_window short (5 minutes max)

### Cost-Conscious Strategy

**Phase 1: Quick validation (~$20 budget)**
1. Deploy both models
2. Run 2-3 test cases each
3. Assess if they work at all
4. **Stop deployment immediately** if issues persist

**Phase 2: Quality comparison (~$40 budget)**
- If Phase 1 successful:
  1. Run test suites
  2. Compare with current model
  3. Decide on viability

**Phase 3: Production evaluation (~$100 budget)**
- If Phase 2 shows promise:
  1. Test with real IR generation tasks
  2. Measure success rates
  3. Calculate ROI
  4. Make production decision

## Troubleshooting

### If 80B model still fails

**Check:**
1. Image rebuilt with transformers from source?
2. Transformers version: `pip show transformers` should show git commit
3. Model downloads successfully?

**Solutions:**
- Force rebuild: `modal image build ...`
- Check Modal logs for detailed errors
- Try with `VLLM_EAGER=1` for faster cold start

### If 480B model still OOMs

**Options (in order):**
1. Already at 8x H100 - this is the limit
2. Reduce `max_model_len` further (try 16384)
3. Reduce `gpu_memory_utilization` to 0.75
4. **Accept limitation**: Model may be too large for Modal H100 limits

**Alternative:**
- Consider if 480B is practical for your use case
- 80B model might be the sweet spot (cost/performance)

## Files Changed

```
modified: lift_sys/inference/modal_qwen_vllm.py
  - Install transformers from source
  - 480B: 8x H100, 32K context, 0.80 gpu_mem_util
  - 80B: 0.85 gpu_mem_util

modified: docs/modal/QWEN_VLLM_MODELS.md
  - Updated specs and costs
  - Added transformers compatibility notes
  - Updated troubleshooting guide

new: docs/modal/QWEN_FIXES_SUMMARY.md (this file)
```

## Summary

✅ **Fixed:** Both critical issues addressed
⚠️ **Cost:** 480B model now 2x more expensive ($32/hour)
🎯 **Ready:** Deploy and test with light workload first
💡 **Recommendation:** Test 80B thoroughly, test 480B cautiously

**Next command:**
```bash
modal deploy lift_sys/inference/modal_qwen_vllm.py
```

Then run light tests, evaluate viability, and decide whether to proceed with comprehensive testing.
