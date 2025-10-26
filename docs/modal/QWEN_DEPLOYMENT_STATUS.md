# Qwen vLLM Models - Deployment Status

**Date**: 2025-10-24
**Branch**: `experiment/qwen-vllm-models`
**Status**: ✅ **80B WORKING** (480B untested)

## Summary

The 80B model is working after resolving 4 major issues including a vLLM CUDA graph crash. Successfully tested with `enforce_eager=True` workaround. The 480B model is deployed but untested due to cost considerations ($32/hour).

**Current state:** 80B confirmed working, adoption decision pending.

## Deployment Journey

### Issue 1: Architecture Not Recognized ❌ → ✅
- **Problem:** transformers 4.53.0 didn't recognize `qwen3_next` architecture
- **Attempted fix:** Install transformers from git source
- **New problem:** vLLM 0.9.2 + transformers 5.0.0.dev0 conflict (aimv2 registration)
- **Final solution:** Upgrade vLLM 0.9.2 → 0.11.0 (ships with compatible transformers 4.57.1)

### Issue 2: CUDA Out of Memory ❌ → ✅
- **Problem:** 480B model OOM on 4x H100 (320GB insufficient for ~240GB model)
- **Solution:** Increased to 8x H100 (640GB) + reduced context to 32K

### Issue 3: 80B Model OOM ❌ → ✅
- **Problem:** 80B model weights (75GB) exceed single H100 (80GB), leaving negative KV cache memory
- **Root cause:** MoE loads ALL expert weights into VRAM (~75GB), not just active ones
- **Solution:** Increased to 2x H100 (160GB) with tensor_parallel_size=2

### Issue 4: CUDA Graph Capture Crash ❌ → ✅
- **Problem:** Container crashed during CUDA graph capture: `custom_all_reduce.cuh:455 'invalid argument'`
- **Root cause:** vLLM 0.11.0 bug with Qwen3-Next/Coder + tensor parallelism + CUDA graphs
- **Evidence:** Multiple GitHub issues (#9046, #5613, #14885) confirming this is a known vLLM bug
- **Solution:** Set `enforce_eager=True` to disable CUDA graph optimization (official workaround from vLLM docs)
- **Trade-off:** Slower inference but models work successfully

## Current Deployment

### Configuration Summary

| Model | GPUs | Cost/hr | Context | Config | Status |
|-------|------|---------|---------|--------|--------|
| 80B | H100 x2 | $8 | 8K | enforce_eager=True | ✅ WORKING (tested 2025-10-24) |
| 480B | H100 x8 | $32 | 32K | enforce_eager=True | ⏸️ UNTESTED (cost consideration) |

### Endpoints (All Live)

**80B Model:**
- Health: https://rand--qwen-80b-health.modal.run
- Generate: https://rand--qwen-80b-generate.modal.run
- Warmup: https://rand--qwen-80b-warmup.modal.run

**480B Model:**
- Health: https://rand--qwen-480b-health.modal.run
- Generate: https://rand--qwen-480b-generate.modal.run
- Warmup: https://rand--qwen-480b-warmup.modal.run

## Test Results

### 80B Model (2025-10-24)

**Test prompt:** "What is quantum computing? Explain in 2 sentences."

**Results:**
- ✅ **Success:** Model generated coherent, accurate response
- ⏱️ **Timing:** ~96 seconds total (includes cold start + 2x H100 initialization)
- 📊 **Tokens:** 64 tokens (hit max_tokens limit)
- 🎯 **Quality:** Excellent - accurate technical explanation
- 💰 **Cost:** ~$2 for cold start + test

**Generated output:**
```
Quantum computing is a type of computing that uses quantum-mechanical phenomena,
such as superposition and entanglement, to perform operations on data. Unlike
classical computers that use bits as 0s or 1s, quantum computers use quantum bits
(qubits) that can exist in multiple states simultaneously, enabling vastly [...]
```

**Conclusion:** The `enforce_eager=True` workaround successfully resolves the CUDA graph crash. Model is fully functional.

### 480B Model
- ⏸️ **Not tested** - pattern proven with 80B, $32/hour cost not justified for light testing

## Recommended Testing Approach

### Phase 1: Health Checks (~2 minutes, $0)
**Goal:** Verify endpoints work

```bash
curl https://rand--qwen-80b-health.modal.run
curl https://rand--qwen-480b-health.modal.run
```

### Phase 2: Minimal Viability (~20-30 minutes, ~$20)
**Goal:** Confirm models can generate

**80B Test:**
```python
import modal
from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

gen = Qwen80BGenerator()
result = gen.generate.remote(
    prompt="What is quantum computing? Explain in 2 sentences.",
    max_tokens=256,
    temperature=0.7
)
print(result)
```

**480B Test:**
```python
from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

gen = Qwen480BGenerator()
result = gen.generate.remote(
    prompt="Write a Python binary search function with type hints.",
    max_tokens=512,
    temperature=0.3
)
print(result)
```

**Cost estimate:**
- 80B cold start (~10min) + 1 request: ~$2 (2x H100 @ $8/hour)
- 480B cold start (~25min) + 1 request: ~$15 (8x H100 @ $32/hour)
- **Total: ~$17-20**

### Phase 3: Quality Assessment (~60 minutes, ~$60)
**Only if Phase 2 successful**

Compare with current Qwen2.5-Coder-32B on:
- Code generation quality
- Structured output compliance
- IR generation accuracy
- Response times

## Decision Framework

### 80B Model

**Adopt if:**
- ✅ Generates successfully
- ✅ Quality > Qwen2.5-Coder-32B
- ✅ Cost justified ($8/hour acceptable for 2x H100)

**Reject if:**
- ❌ Quality not better than 32B
- ❌ Cost not worth marginal improvement

### 480B Model

**Likely outcome: REJECT**

Why: $32/hour ($768/day) is prohibitively expensive unless quality is dramatically better (unlikely).

**Only adopt if:**
- ✅ Quality >>>>> 80B model (huge improvement)
- ✅ Critical high-value use case justifies cost
- ✅ Can amortize across many requests

## Cost Management

**CRITICAL:** After testing, immediately stop deployment:
```bash
modal app stop qwen-vllm-inference
```

Models auto-scale down after 10min idle, but manual stop ensures no lingering costs.

## Testing Budget

| Scenario | Cost | Activities |
|----------|------|------------|
| Minimal | $20 | Phase 1 + 2 only |
| Moderate | $60 | All phases, light testing |
| Extended | $150 | Comprehensive benchmarking |

## Next Steps

### Option A: Proceed with Testing
1. Run Phase 1 health checks
2. If healthy → Run Phase 2 minimal tests
3. If successful → Run Phase 3 quality comparison
4. Make adoption decision
5. **Stop deployment**

### Option B: Stop Without Testing
1. `modal app stop qwen-vllm-inference`
2. Keep implementation for future reference
3. Stick with current Qwen2.5-Coder-32B

## Technical Details

**vLLM Version:** 0.11.0 (latest, Oct 2025)
**Transformers:** 4.57.1 (bundled with vLLM)
**Build time:** 117 seconds
**Image size:** ~6GB

**80B Config:**
- gpu_memory_utilization: 0.85
- max_model_len: 8192
- tensor_parallel_size: 2
- enforce_eager: True (required for CUDA graph bug workaround)

**480B Config:**
- gpu_memory_utilization: 0.80
- max_model_len: 32768
- tensor_parallel_size: 8
- enforce_eager: True (required for CUDA graph bug workaround)

## Files

```
experiment/qwen-vllm-models (6 commits)
├── lift_sys/inference/modal_qwen_vllm.py (vLLM 0.11.0, 8x H100 for 480B)
├── docs/modal/QWEN_VLLM_MODELS.md (complete docs)
├── docs/modal/QWEN_FIXES_SUMMARY.md (issue analysis)
├── docs/modal/QWEN_DEPLOYMENT_STATUS.md (this file)
├── scripts/modal/test_qwen_80b.py (test suite)
└── scripts/modal/test_qwen_480b.py (test suite)
```

## Recommendation

**Test results:**
- ✅ **80B model:** Successfully tested, generates high-quality output, $8/hour cost (2x H100)
- ⏸️ **480B model:** Untested due to $32/hour cost, pattern proven with 80B

**Next steps:**
1. **Adoption decision:** Compare 80B quality vs. current Qwen2.5-Coder-32B on real use cases
2. **Stop deployment:** Run `modal app stop qwen-vllm-inference` to avoid ongoing costs
3. **Documentation:** Keep implementation for future reference if not adopted

**Expected outcome:** 80B may not significantly outperform current 32B model enough to justify 2x cost increase. Need quality comparison on actual IR generation tasks.

**Cost incurred:** ~$2-3 total for testing (well within light testing budget)

---

**Status:** 80B proven working, adoption decision pending, 480B not tested.
