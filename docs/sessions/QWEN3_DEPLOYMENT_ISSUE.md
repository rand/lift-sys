# Qwen3-30B Deployment Issue

**Date**: October 16, 2025
**Status**: ⚠️ BLOCKED - Reverted to Qwen2.5-7B

---

## Problem Summary

Attempted to deploy Qwen3-Coder-30B-A3B-Instruct to Modal as requested, but the generate endpoint hangs and never responds.

### What Works
- ✅ Modal deployment succeeds (completes in ~2s)
- ✅ Health endpoint responds correctly
- ✅ Model info shows in health endpoint: `Qwen/Qwen3-Coder-30B-A3B-Instruct` on A100-80GB

### What Fails
- ❌ Generate endpoint hangs indefinitely (tested with 5+ minute timeout)
- ❌ No response to POST requests
- ❌ Unable to retrieve logs (modal app logs command times out)

---

## Investigation

### Test Results

**curl test** (generate endpoint with minimal JSON):
```bash
curl -X POST --max-time 300 -d @test_modal_curl.json https://rand--generate.modal.run
# Result: Hung for 2 minutes 30 seconds, 0 bytes received
```

**Python test** (simple IR generation):
```python
provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
await provider.initialize(credentials={})
translator = XGrammarIRTranslator(provider)
ir = await translator.translate("Create a function called add...")
# Result: Timed out after 2 minutes
```

### Possible Root Causes

1. **Model name issue**: Used `"Qwen/Qwen3-Coder-30B-A3B-Instruct"` but user linked to GGUF version:
   - User's link: https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF
   - vLLM doesn't support GGUF format directly
   - May need to use non-GGUF version or different model path

2. **Model size**: Even as MoE (30B total, ~3B active), full params must load into VRAM
   - A100-80GB should be sufficient, but model may be OOMing during initialization
   - Cold start may exceed Modal's default timeouts

3. **vLLM compatibility**: Qwen3 might not be fully supported by vLLM 0.9.2 yet
   - Model may be too new
   - May need different vLLM version or configuration

---

## Resolution

**Temporary**: Reverted to Qwen2.5-Coder-7B-Instruct on A10G
- Known to work (previously deployed successfully)
- Allows testing of Best-of-N implementation
- Phase 3 baseline: 72.2% (13/18 passing)

**Modal app** (`lift_sys/inference/modal_app.py`):
```python
# Reverted configuration
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"
GPU_CONFIG = "A10G"  # $1.10/hr
```

---

## Next Steps (Options)

### Option 1: Try Qwen2.5-32B-Instruct
**Pros**: Known to work with vLLM, larger than 7B for better quality
**Cons**: Not as good as Qwen3, still not the model you requested
**Config**:
```python
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"
GPU_CONFIG = "A100-80GB"
```

### Option 2: Debug Qwen3 model path
**Investigate**:
- Check if `Qwen/Qwen3-Coder-30B-A3B-Instruct` exists (non-GGUF)
- Try `unsloth/Qwen3-Coder-30B-A3B-Instruct` (without -GGUF suffix)
- Check vLLM's supported models list for Qwen3 compatibility

### Option 3: Use Claude 3.5 for IR generation
**Pros**: Best quality, known to work, remote API (no GPU needed)
**Cons**: Higher cost (~$3/1M tokens vs $0.15/1M), API latency
**Implementation**: Already have AnthropicProvider ready

### Option 4: Proceed with Qwen2.5-7B + Best-of-N
**Pros**: Can test Best-of-N implementation now, unblocks testing
**Cons**: Not the model upgrade you wanted
**Expected**: Still 72-78% Phase 3 (Best-of-N might add +5-10%)

---

## Recommendation

1. **Short term**: Test Best-of-N with Qwen2.5-7B to validate the implementation works
2. **Parallel investigation**: Research correct Qwen3 model path or try Qwen2.5-32B
3. **Decision point**: If Best-of-N + Qwen2.5-7B achieves <80%, escalate to Claude 3.5 for IR generation

---

## Files Modified

- `lift_sys/inference/modal_app.py` - Reverted MODEL_NAME and GPU_CONFIG
- `lift_sys/forward_mode/best_of_n_translator.py` - Best-of-N implementation (ready to test)
- `run_phase3_best_of_n.py` - Test runner with Best-of-N support
