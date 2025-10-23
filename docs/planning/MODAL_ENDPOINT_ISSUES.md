# Modal Endpoint Issues - Critical Findings

**Date**: 2025-10-22
**Context**: E2E Validation Phase 1 - Modal endpoint testing
**Severity**: HIGH - Blocks real integration testing

---

## Issue 1: Missing Request Validation (P0) - ✅ FIXED

**Status**: Fixed in commit 5093fcf (2025-10-22)

**Problem**: Endpoint crashed with `KeyError: 'schema'` when schema was not provided

**Original Error**:
```python
File "/root/modal_app.py", line 281, in web_generate
    schema=item["schema"],
           ~~~~^^^^^^^^^^
KeyError: 'schema'
```

**Root Cause**: `web_generate()` didn't validate required fields before accessing them

**Impact**:
- Unhelpful error messages
- Crashes with 500 instead of returning 400 Bad Request
- Difficult to debug for API users

**Fix Applied**:
```python
# lift_sys/inference/modal_app.py:288-292
# Validate required fields to prevent KeyError (P0 fix)
if "prompt" not in request:
    return {"error": "Missing required field: prompt", "status": 400}
if "schema" not in request:
    return {"error": "Missing required field: schema", "status": 400}
```

**Additional Improvements**:
- Removed duplicate endpoint pattern (cleaner architecture)
- Changed from `.pip_install` to `.uv_pip_install` (10-100x faster builds: 87s vs ~10+ min)
- Added warm-up endpoint: https://rand--warmup.modal.run

**Bead**: lift-sys-298 (closed)

---

## Issue 2: Extreme Cold Start Times (P1)

**Problem**: 32B model takes 7+ minutes to load on cold start

**Metrics** (from logs):
- Model loading: **423.71 seconds** (~7 minutes)
- Breakdown:
  - Loading safetensors: 43.36s (14 shards @ 2-3s each)
  - Model init: 45.39s (61GB memory allocation)
  - Torch compile: 156.36s (bytecode transform + graph compilation)
  - KV cache init: 1.00GB
  - CUDA graph capture: 46s
  - Total: **7 minutes 3 seconds**

**Comparison** (7B vs 32B):
| Metric | 7B Model | 32B Model | Difference |
|--------|----------|-----------|------------|
| Cold start | 30-60s | 420s (7min) | **7-14x slower** |
| Model size | ~14GB | ~61GB | **4.4x larger** |
| GPU | L40S | A100-80GB | Different hardware |

**Impact**:
- First request after deployment: 7+ minutes
- Tests with cold endpoints will timeout
- Benchmark suite will be MUCH slower if endpoints go cold
- Need much higher timeouts (10+ minutes)

**Mitigations**:
1. **Keep model warm**: Periodic health checks or requests
2. **Increase timeouts**: 600s (10 min) for cold starts, 120s for warm
3. **Use smaller model for dev**: Consider 7B for development, 32B for production
4. **Pre-warm before benchmarks**: Call health endpoint, wait for model load

**Recommendation**:
```python
# Before running benchmarks:
# 1. Call generate endpoint once to trigger load
# 2. Wait 10 minutes
# 3. Verify model is warm (subsequent calls <10s)
# 4. Run benchmarks
```

---

## Issue 3: Timeout Handling (P2)

**Problem**: curl and Python clients timeout before model finishes loading

**Current Timeouts**:
- curl `--max-time`: 120s (too short for cold start)
- Python httpx default: 5s (way too short)
- Modal function timeout: 600s (10 min, OK)

**Fix Required**:
```python
# lift_sys/providers/modal_provider.py
import httpx

class ModalProvider(BaseProvider):
    def __init__(self, endpoint_url: str, timeout: int = 600):
        self.client = httpx.AsyncClient(timeout=timeout)  # 10 min timeout
```

**Testing**:
```bash
# For cold starts
curl --max-time 600 https://rand--generate.modal.run ...

# For warm requests
curl --max-time 30 https://rand--generate.modal.run ...
```

---

## Issue 4: No Model Warm-Up Mechanism (P2) - ✅ FIXED

**Status**: Fixed in commit 5093fcf (2025-10-22)

**Problem**: No way to pre-warm the model before running benchmarks

**Desired Behavior**:
1. ~~Health endpoint triggers model load (not needed - health is lightweight)~~
2. ✅ Warm-up endpoint specifically for loading model
3. ✅ Status endpoint showing if model is loaded

**Fix Applied**:
```python
# lift_sys/inference/modal_app.py:309-326
@modal.fastapi_endpoint(method="GET", label="warmup")
async def warmup(self) -> dict:
    """
    Warm-up endpoint to pre-load model without generating.

    Call this endpoint to trigger model loading (7 min cold start for 32B model).
    Subsequent requests will be fast (~2-10s).

    Returns:
        {"status": "warm", "model_loaded": True, "model": MODEL_NAME}
    """
    # Model is already loaded in @modal.enter(), just return status
    return {
        "status": "warm",
        "model_loaded": True,
        "model": MODEL_NAME,
        "ready_for_requests": True,
    }
```

**Endpoint**: https://rand--warmup.modal.run

**Bead**: lift-sys-299 (closed)

---

## Immediate Actions

**P0 (Blocking)**:
- [x] Fix request validation (Pydantic models) - lift-sys-298 ✅ DONE
- [x] Document cold start times in MODAL_ENDPOINTS.md ✅ DONE
- [ ] Test with increased timeout (600s) - IN PROGRESS (warm-up running)

**P1 (Important)**:
- [x] Add warm-up mechanism - lift-sys-299 ✅ DONE
- [ ] Update ModalProvider with longer timeout (600s)
- [ ] Create pre-benchmark warm-up script

**P2 (Nice-to-have)**:
- [ ] Consider dual deployment (7B dev, 32B prod)
- [x] Add model status endpoint (warm-up returns status) ✅ DONE
- [ ] Implement keep-warm scheduler

**Completed (2025-10-22)**:
- ✅ Request validation prevents KeyError crashes
- ✅ 10-100x faster image builds (uv: 87s vs pip: 10+ min)
- ✅ Warm-up endpoint: https://rand--warmup.modal.run
- ✅ Removed duplicate endpoints (cleaner architecture)

---

## Testing Strategy Update

**Original Plan**: Direct API testing
**Revised Plan**: Use ResponseRecorder caching

**Rationale**:
- Cold starts make real-time testing impractical (7 min wait)
- ResponseRecorder allows:
  - First run: Record responses (slow, 7+ min)
  - Subsequent runs: Use cache (fast, <1s)
  - CI/CD: Offline testing with fixtures
- Best of both worlds: Real validation + fast iteration

**Workflow**:
```bash
# One-time: Record real responses (wait 7+ min for cold start)
RECORD_FIXTURES=true pytest tests/integration/test_modal_provider_real.py -v

# All subsequent runs: Use cached responses (fast)
pytest tests/integration/test_modal_provider_real.py -v

# Weekly: Refresh fixtures
RECORD_FIXTURES=true pytest -m real_modal
```

---

## Updated Baseline Benchmark Plan

**Original**: Run benchmarks immediately
**Revised**: Pre-warm model first

**Steps**:
1. Call generate endpoint to trigger load (wait 7 min)
2. Verify model is warm (test request <10s)
3. Run benchmark suite
4. Expected time: 7 min warm-up + 10 tests @ 10-20s = ~10-12 minutes total

**Alternative**: Record baseline once, use cached responses for development

---

## Summary

**Critical Finding**: 32B model has **7-minute cold starts**, making real-time testing impractical.

**Impact on E2E Plan**:
- ✅ Modal endpoint works (once loaded)
- ⚠️ Cold starts are 7-14x slower than expected
- ⚠️ Request validation is broken (crashes on missing fields)
- ✅ XGrammar is working (backend enabled)

**Recommendation**:
1. Fix P0 issues (request validation)
2. Use ResponseRecorder for all integration tests
3. Pre-warm model before benchmarks
4. Document cold start behavior prominently

---

**Status**: Issues documented, fixes prioritized
**Next**: Create bead for P0 fix, update MODAL_ENDPOINTS.md
**Owner**: Architecture Team
