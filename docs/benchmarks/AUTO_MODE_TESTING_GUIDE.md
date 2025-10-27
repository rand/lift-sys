# Auto Mode Testing Guide

**Last Updated**: 2025-10-27
**Purpose**: Test vLLM's automatic backend selection for guided decoding
**Status**: Experimental - not yet tested

---

## Overview

vLLM 0.11.0+ supports an "auto" mode for `guided_decoding_backend` that automatically selects the optimal backend (llguidance or xgrammar) based on the request characteristics.

### Current Setup

```python
# lift_sys/inference/modal_qwen_vllm.py (current)
self.llm = LLM(
    model=QWEN_80B_MODEL,
    guided_decoding_backend="guidance",  # Fixed: always llguidance
    # ...
)
```

### Auto Mode

```python
# Proposed: Let vLLM choose
self.llm = LLM(
    model=QWEN_80B_MODEL,
    guided_decoding_backend="auto",  # vLLM selects best backend
    # ...
)
```

## How Auto Mode Works

vLLM's auto mode selection logic (based on vLLM source code analysis):

1. **Schema Complexity Analysis**:
   - Simple schemas → llguidance (faster compilation)
   - Complex schemas → may use xgrammar (better precompilation caching)

2. **Caching Potential**:
   - Repeated schemas → xgrammar (precompiled grammar caching)
   - Dynamic schemas → llguidance (no caching benefit)

3. **Request Patterns**:
   - Batch requests with same schema → xgrammar
   - Mixed/streaming requests → llguidance

### Expected Behavior for lift-sys

Our use case characteristics:
- ✅ **Dynamic schemas**: Every request has different schema (function signatures vary)
- ✅ **Single requests**: Not batching identical schemas
- ✅ **Streaming**: Some endpoints use streaming
- ❌ **Schema reuse**: Minimal (each function prompt is unique)

**Hypothesis**: Auto mode will predominantly select **llguidance** for our workload.

## Testing Plan

### Phase 1: Observational Testing (Low Risk)

Deploy a separate auto mode endpoint and observe:

```bash
# Deploy auto mode endpoint (doesn't affect production)
modal deploy lift_sys/inference/modal_qwen_vllm_auto.py --name qwen-auto
```

Run test suite and log backend selections:
```bash
# Run tests with logging
python scripts/benchmarks/test_auto_mode.py \
    --endpoint https://rand--qwen-auto-generate.modal.run \
    --num-tests 50 \
    --output validation/auto_mode_results.json
```

### Phase 2: A/B Comparison

Compare auto mode vs fixed llguidance:

| Metric | Fixed llguidance | Auto Mode | Expected |
|--------|------------------|-----------|----------|
| Success Rate | ~85% | ? | Similar (within 5%) |
| Avg Latency | ~14s | ? | Similar or better |
| Backend Selection | 100% llguidance | ? | >90% llguidance |
| Variability | Low | ? | Should be low |

### Phase 3: Production Evaluation

If Phase 1 & 2 show benefits:
- Deploy auto mode to production
- Monitor for 1 week
- Compare metrics vs llguidance baseline
- Decide: keep auto or revert to fixed

## Implementation Steps

### Step 1: Create Auto Mode Deployment

Copy current deployment:
```bash
cp lift_sys/inference/modal_qwen_vllm.py \
   lift_sys/inference/modal_qwen_vllm_auto.py
```

Modify for auto mode:
```python
# In modal_qwen_vllm_auto.py, change line ~89:

# BEFORE:
guided_decoding_backend="guidance",

# AFTER:
guided_decoding_backend="auto",
```

Update app name:
```python
# Line ~25:
app = modal.App("qwen-vllm-inference-auto")
```

Update labels:
```python
# Line ~110 and ~310:
label="qwen-auto-generate"  # Instead of qwen-80b-generate
```

### Step 2: Deploy Auto Mode

```bash
# Deploy without affecting production
modal deploy lift_sys/inference/modal_qwen_vllm_auto.py --name qwen-auto

# Endpoints created:
# - https://rand--qwen-auto-generate.modal.run
# - https://rand--qwen-auto-health.modal.run
```

### Step 3: Create Test Script

```python
# scripts/benchmarks/test_auto_mode.py
"""Test vLLM auto mode backend selection."""

import asyncio
import httpx

async def test_auto_mode():
    # Send identical requests to observe backend selection
    # Check if latency/success rate is consistent
    # Log any differences from fixed llguidance mode
    pass
```

### Step 4: Run Tests

```bash
# Quick smoke test (10 requests)
python scripts/benchmarks/test_auto_mode.py \
    --endpoint https://rand--qwen-auto-generate.modal.run \
    --num-tests 10

# Full test suite (50 requests)
python scripts/benchmarks/test_auto_mode.py \
    --endpoint https://rand--qwen-auto-generate.modal.run \
    --num-tests 50 \
    --output validation/auto_mode_results_$(date +%Y%m%d).json
```

### Step 5: Analyze Results

Check:
1. **Backend selection pattern**: Does it use llguidance consistently?
2. **Performance**: Is it faster/slower/same as fixed llguidance?
3. **Reliability**: Any unexpected failures?
4. **Variability**: Is performance consistent across requests?

### Step 6: Decide

**If auto mode is better or equal**:
- Update production deployment to use auto mode
- Document benefits
- Update .env with new endpoint

**If auto mode is worse**:
- Document findings
- Keep fixed llguidance mode
- Stop auto mode endpoint to save costs

## Expected Results

Based on our workload characteristics:

### Most Likely Outcome
- Auto mode selects llguidance for 95%+ of requests
- Performance identical to fixed llguidance
- **Recommendation**: No benefit, keep fixed llguidance (simpler)

### Best Case Outcome
- Auto mode provides 5-10% latency improvement
- Backend selection adapts intelligently
- **Recommendation**: Switch to auto mode in production

### Worst Case Outcome
- Auto mode adds overhead (backend selection logic)
- Performance degrades or becomes inconsistent
- **Recommendation**: Stick with fixed llguidance

## Cost Considerations

**Testing Cost**:
- Deploy auto mode endpoint: Free (Modal allows multiple apps)
- H100 GPU time: ~$2-3/hour
- Testing duration: ~1 hour for full suite
- **Total**: ~$3 for comprehensive testing

**Production Cost**:
- No additional cost if auto mode performs same as llguidance
- Could save cost if auto selects more efficient backend mix

## Risks

**Low Risk**:
- Testing on separate endpoint (doesn't affect production)
- Easy to stop auto mode endpoint
- Can revert immediately if issues

**Medium Risk**:
- Auto mode selection overhead could add latency
- Inconsistent backend selection could cause variability

**Mitigation**:
- Test thoroughly before production
- Monitor closely after deployment
- Have rollback plan ready

## Current Status

- ✅ **Documentation**: Complete
- ❌ **Auto mode deployment**: Not created
- ❌ **Test script**: Not created
- ❌ **Test results**: Not available

**Next Steps**:
1. Decide if auto mode testing is worth the effort
2. If yes, create auto mode deployment file
3. Deploy and run tests
4. Document findings

## Alternative: Skip Auto Mode Testing

**Rationale for skipping**:
- llguidance already performs well (85% success, ~14s latency)
- Our workload doesn't benefit from schema caching (dynamic schemas)
- Auto mode likely will just select llguidance anyway
- Testing requires deployment and GPU time ($3-5)

**Recommendation**: Document auto mode as "future optimization" but don't test now. Focus on other priorities.

---

## References

- **vLLM Auto Mode**: https://docs.vllm.ai/en/latest/serving/guided_decoding.html
- **Current llguidance**: `lift_sys/inference/modal_qwen_vllm.py`
- **Benchmark Scripts**: `scripts/benchmarks/`
- **Phase 3 Results**: `validation/PHASE3_LLGUIDANCE_MIGRATION_RESULTS.md`
