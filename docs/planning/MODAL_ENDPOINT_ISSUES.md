# Modal Endpoint Issues - Critical Findings

**Date**: 2025-10-22
**Context**: E2E Validation Phase 1 - Modal endpoint testing
**Severity**: HIGH - Blocks real integration testing

---

## Issue 1: Missing Request Validation (P0)

**Problem**: Endpoint crashes with `KeyError: 'schema'` when schema is not provided

**Error**:
```python
File "/root/modal_app.py", line 281, in web_generate
    schema=item["schema"],
           ~~~~^^^^^^^^^^
KeyError: 'schema'
```

**Root Cause**: `generate_web_endpoint()` and `web_generate()` don't validate required fields before accessing them

**Impact**:
- Unhelpful error messages
- Crashes instead of returning 400 Bad Request
- Difficult to debug for API users

**Fix Required**:
```python
# lift_sys/inference/modal_app.py
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    """Validated request model for generate endpoint."""
    prompt: str = Field(..., description="Natural language prompt")
    schema: dict = Field(..., description="JSON schema for XGrammar constraints")
    max_tokens: int = Field(default=2048, ge=1, le=8192)
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)

@app.function(image=llm_image)
@modal.fastapi_endpoint(method="POST", label="generate")
def generate_web_endpoint(request: GenerateRequest) -> dict:
    """FastAPI will automatically validate and return 422 if invalid."""
    generator = ConstrainedIRGenerator()
    return generator.generate.remote(
        prompt=request.prompt,
        schema=request.schema,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
    )
```

**Bead**: lift-sys-298 (to be created)

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

## Issue 4: No Model Warm-Up Mechanism (P2)

**Problem**: No way to pre-warm the model before running benchmarks

**Desired Behavior**:
1. Health endpoint triggers model load (currently doesn't)
2. Warm-up endpoint specifically for loading model
3. Status endpoint showing if model is loaded

**Fix Required**:
```python
# Add warm-up endpoint
@app.function(image=llm_image)
@modal.fastapi_endpoint(method="GET", label="warmup")
def warmup():
    """Trigger model load without generating."""
    generator = ConstrainedIRGenerator()
    # Model loads on class instantiation
    return {
        "status": "warm",
        "model_loaded": True,
        "ready_for_requests": True
    }
```

---

## Immediate Actions

**P0 (Blocking)**:
- [ ] Fix request validation (Pydantic models) - lift-sys-298
- [ ] Test with increased timeout (600s)
- [ ] Document cold start times in MODAL_ENDPOINTS.md

**P1 (Important)**:
- [ ] Add warm-up mechanism
- [ ] Update ModalProvider with longer timeout
- [ ] Create pre-benchmark warm-up script

**P2 (Nice-to-have)**:
- [ ] Consider dual deployment (7B dev, 32B prod)
- [ ] Add model status endpoint
- [ ] Implement keep-warm scheduler

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
