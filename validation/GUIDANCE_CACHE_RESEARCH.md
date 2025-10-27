# Guidance Transformers Cache Issue - Research & Fix Plan

**Date**: 2025-10-27
**Issue**: `Cache is too small. Resetting cache (no method implemented to resize cache for type <class 'transformers.cache_utils.DynamicCache'>)`
**Status**: Root cause identified, solutions proposed

---

## Executive Summary

The cache warning is **not a fundamental bug** but a **configuration issue** caused by transformers' `DynamicCache` defaulting to an insufficient size for long-context generation. Guidance can handle this but needs to be configured with an appropriate cache type.

**Key Finding**: guidance supports StaticCache and HybridCache (which it can resize), but not DynamicCache (which is what Qwen defaults to).

---

## Root Cause Analysis

### 1. The Warning Trigger (Line 522)

**Location**: `.venv/lib/python3.13/site-packages/guidance/models/_transformers.py:522`

```python
# Line 496-527
if max_cache_shape is not None and len(token_ids) > max_cache_shape:
    if isinstance(
        past_key_values,
        (transformers_package.StaticCache, transformers_package.HybridCache),
    ):
        # CAN RESIZE: Create new cache with doubled size
        self._past_key_values = cache_type(
            config=config,
            max_batch_size=past_key_values.max_batch_size,
            max_cache_len=len(token_ids) * 2,  # Double size!
            dtype=past_key_values._dtype,
            layer_device_map=layer_device_map,
        )
    else:
        # CANNOT RESIZE: Reset cache (this is what we hit)
        warnings.warn(
            f"Cache is too small. Resetting cache (no method implemented to resize cache for type {type(past_key_values)}).",
            stacklevel=1,
        )
        self._past_key_values = None
    past_length = 0
```

**What This Means**:
- guidance **can** resize StaticCache and HybridCache dynamically
- guidance **cannot** resize DynamicCache (used by Qwen by default)
- When cache is too small and can't be resized → resets to None → generation starts from scratch

### 2. Model Default Cache Behavior

**Qwen/Qwen2.5-Coder-32B-Instruct**:
- Defaults to `DynamicCache` (transformers standard)
- DynamicCache initializes with minimal size
- Grows as needed but guidance can't control the growth

**Problem Flow**:
```
1. Model loads with DynamicCache (small initial size)
2. Guidance tries to generate with schema constraints
3. Token sequence exceeds DynamicCache max size
4. guidance checks: "Can I resize this cache type?"
5. DynamicCache not in (StaticCache, HybridCache) → NO
6. guidance resets cache to None → loses all KV state
7. Generation continues but WITHOUT cached context → slow/inefficient
```

### 3. Why This Happens

**From transformers docs** (https://huggingface.co/docs/transformers/main/en/kv_cache):
- DynamicCache: Default, grows automatically BUT transformers controls growth, not guidance
- StaticCache: Fixed size, guidance can create new one with larger size
- HybridCache: Hybrid approach, guidance can create new one with larger size

**Key Insight**: guidance needs a cache type it can **reinitialize** when it detects size issues. DynamicCache doesn't allow this from outside the transformers generation loop.

---

## Evidence from GitHub

### Issue #986: `past_key_values` deprecation
- Transformers 4.44.0+ deprecated tuple-based caching
- Now requires Cache classes (DynamicCache, StaticCache, HybridCache)
- Some models (T5) have compatibility issues with new Cache API

### PR #1149: Cache method updates
- Merged 2025-03-10
- Updated `get_max_length` → `get_max_cache_shape`
- Shows guidance maintainers are actively tracking transformers cache changes

**Status**: guidance is being actively maintained for transformers cache API evolution

---

## Proposed Solutions

### Solution 1: Use StaticCache (Recommended for POC)

**Approach**: Pre-allocate cache with sufficient size for expected generation

**Implementation**:
```python
from transformers import StaticCache

# Modify guidance POC script
lm = models.Transformers(
    "Qwen/Qwen2.5-Coder-32B-Instruct",
    device_map="auto",
    trust_remote_code=True,
    token=hf_token,
    # Pass generation_config with StaticCache
    generation_config={
        "cache_implementation": "static",
        "max_cache_len": 4096,  # Sufficient for most schemas
    }
)
```

**Pros**:
- guidance can resize StaticCache when needed
- Eliminates the warning
- Predictable memory usage

**Cons**:
- Pre-allocates memory (may be wasteful for short generations)
- Requires estimating max context length

**When to Use**: POC validation where we know approximate schema sizes

### Solution 2: Use HybridCache

**Approach**: Use hybrid cache that combines static + dynamic behavior

**Implementation**:
```python
# Similar to Solution 1 but with:
generation_config={
    "cache_implementation": "hybrid",
    "max_cache_len": 2048,  # Initial size
}
```

**Pros**:
- More memory-efficient than StaticCache
- guidance can still resize when needed
- Better for variable-length generation

**Cons**:
- Slightly more complex behavior
- May have model-specific compatibility issues

**When to Use**: Production deployment with varying prompt sizes

### Solution 3: Pre-initialize Cache in guidance

**Approach**: Modify guidance's _model method to set up cache explicitly

**Implementation** (requires forking guidance or monkey-patching):
```python
def _model_with_cache(self, model, cache_len=4096, **kwargs):
    if isinstance(model, str):
        model_obj = transformers_package.AutoModelForCausalLM.from_pretrained(model, **kwargs)

        # Initialize StaticCache before guidance uses model
        from transformers import StaticCache
        cache = StaticCache(
            config=model_obj.config,
            max_batch_size=1,
            max_cache_len=cache_len,
            dtype=model_obj.dtype,
            device=model_obj.device,
        )
        # Attach to model (model-specific, may not work for all)
        model_obj._past_key_values = cache

        return model_obj
    return model
```

**Pros**:
- Fixes issue at guidance level
- Works across all usage patterns

**Cons**:
- Requires modifying guidance internals
- May break with guidance updates
- Not officially supported

**When to Use**: If Solutions 1-2 don't work and we need a workaround

### Solution 4: Use vLLM with llguidance (BEST for Production)

**Approach**: Bypass guidance library entirely, use vLLM + llguidance directly

**Implementation**:
```python
# In Modal deployment
from vllm import LLM, SamplingParams
import llguidance

engine = LLM(
    model="Qwen/Qwen2.5-Coder-32B-Instruct",
    gpu_memory_utilization=0.9,
    # vLLM handles caching internally
)

# Use llguidance directly with vLLM
# (vLLM 0.9.2+ has native llguidance support)
```

**Pros**:
- vLLM is production-grade with optimized caching
- llguidance is the actual constraint library (50μs/token)
- No guidance library limitations
- Direct comparison with XGrammar baseline (same infrastructure)

**Cons**:
- Different API than guidance library
- Requires learning vLLM + llguidance integration

**When to Use**: Production deployment, final migration target

---

## Recommended Approach

### For POC (Phase 3.1 Completion):

**Use Solution 1** (StaticCache with sufficient size):

1. Modify `scripts/modal/guidance_poc_modal.py`:
   ```python
   lm = models.Transformers(
       "Qwen/Qwen2.5-Coder-32B-Instruct",
       device_map="auto",
       trust_remote_code=True,
       token=hf_token,
       attn_implementation="flash_attention_2",  # Also helps with memory
       torch_dtype="auto",
   )

   # Generate with StaticCache
   # Note: may need to pass cache_implementation through model.generate()
   ```

2. Test with simplified schema first
3. If successful, test with full TypeScript schema
4. Document results vs XGrammar baseline

**Success Criteria**:
- ✅ No cache warnings
- ✅ Generation completes successfully
- ✅ Valid JSON output matching schema
- ✅ Success rate >50% (vs 4.8% XGrammar baseline)

**Timeline**: 1-2 hours implementation + testing

### For Production (Phase 3.2+):

**Use Solution 4** (vLLM + llguidance directly):

This is the correct long-term architecture and what we should implement for the actual migration.

---

## Testing Plan

### Test 1: Simplified Schema (5 min)
```python
simple_schema = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["function_name", "body"]
}
```
**Goal**: Verify cache configuration works at all

### Test 2: Medium Schema (10 min)
```python
# Use Modal POC's current schema (4 properties)
```
**Goal**: Verify cache can handle moderately complex schemas

### Test 3: Full TypeScript Schema (15 min)
```python
# Use production TYPESCRIPT_GENERATION_SCHEMA
```
**Goal**: Verify cache can handle production complexity

### Test 4: Multiple Generations (15 min)
```python
# Run 5 generations back-to-back
```
**Goal**: Verify cache persists correctly across generations

---

## Implementation Priority

1. **Immediate** (1-2 hours): Solution 1 - StaticCache in Modal POC
2. **Short-term** (1 day): Complete POC validation with all test cases
3. **Medium-term** (3-5 days): Solution 4 - vLLM + llguidance integration
4. **Long-term** (ongoing): Monitor guidance library updates for improved DynamicCache support

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| StaticCache still fails | Low | High | Fall back to Solution 4 (vLLM) |
| Model doesn't support StaticCache | Low | Medium | Try HybridCache (Solution 2) |
| Guidance has other issues | Medium | Medium | Solution 4 bypasses guidance entirely |
| vLLM integration complex | Low | Medium | Extensive vLLM docs + existing Modal setup |

---

## Decision Matrix

| Solution | POC Speed | Production Viability | Complexity | Risk |
|----------|-----------|---------------------|------------|------|
| **Solution 1: StaticCache** | ✅ Fast (1-2h) | ⚠️ Medium | 🟢 Low | 🟢 Low |
| **Solution 2: HybridCache** | ✅ Fast (1-2h) | ✅ High | 🟡 Medium | 🟡 Medium |
| **Solution 3: Monkey-patch** | ⚠️ Medium (4h) | ❌ Low | 🔴 High | 🔴 High |
| **Solution 4: vLLM direct** | ⚠️ Medium (1-2d) | ✅ Highest | 🟡 Medium | 🟢 Low |

**Recommendation**:
- **Now**: Solution 1 (StaticCache) for POC completion
- **Next**: Solution 4 (vLLM + llguidance) for production migration

---

## References

- **Guidance Source**: `.venv/lib/python3.13/site-packages/guidance/models/_transformers.py`
- **Transformers KV Cache Docs**: https://huggingface.co/docs/transformers/main/en/kv_cache
- **Guidance Issue #986**: https://github.com/guidance-ai/guidance/issues/986
- **Guidance PR #1149**: https://github.com/guidance-ai/guidance/pull/1149
- **vLLM llguidance Integration**: https://docs.vllm.ai (check for llguidance support)

---

## Next Actions

1. **Update Modal POC script** with StaticCache configuration
2. **Run Test 1** (simplified schema) to verify fix
3. **Run Tests 2-4** if Test 1 succeeds
4. **Document results** in Phase 3.1 status
5. **Make go/no-go decision** on guidance vs vLLM direct
6. **Begin Phase 3.2** with chosen approach

**Status**: Ready to implement Solution 1 for POC validation
