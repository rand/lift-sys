# Modal Endpoints Documentation

**Date**: 2025-10-22
**Status**: Active
**Model**: Qwen/Qwen2.5-Coder-32B-Instruct
**Backend**: vLLM 0.9.2 with XGrammar

---

## Deployed Endpoints

### Health Endpoint
**URL**: https://rand--health.modal.run
**Method**: GET
**Purpose**: Health check (does NOT load GPU model)

**Response**:
```json
{
  "status": "healthy",
  "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
  "gpu": "A100-80GB",
  "backend": "vLLM 0.9.2 with XGrammar"
}
```

**Latency**: <1s (no model loading)

---

### Generate Endpoint
**URL**: https://rand--generate.modal.run
**Method**: POST
**Purpose**: Schema-constrained IR generation with XGrammar

**Request Body**:
```json
{
  "prompt": "Natural language description of the function",
  "schema": {
    "type": "object",
    "properties": {
      "intent": {...},
      "signature": {...}
    },
    "required": ["intent", "signature"]
  },
  "max_tokens": 2048,      // optional, default 2048
  "temperature": 0.3,      // optional, default 0.3
  "top_p": 0.95           // optional, default 0.95
}
```

**Response**:
```json
{
  "ir_json": {
    "intent": {"summary": "..."},
    "signature": {"name": "...", "parameters": [...], "returns": "..."}
  },
  "tokens_used": 512,
  "generation_time_ms": 2450.5,
  "finish_reason": "stop"
}
```

**Latency**:
- **Cold start** (first call after deployment): 3-5 minutes (model download + load)
- **Cold start** (subsequent cold starts): 30-90 seconds (model load from volume)
- **Warm requests**: 2-10 seconds (model already loaded)

**Note**: The 32B model is MUCH larger than the previous 7B model, resulting in:
- Longer cold start times
- Higher quality outputs
- Higher token costs
- Expected latency increase in benchmarks

---

## Configuration

### Environment Variables

Add to `.env.local`:
```bash
# Modal.com endpoints (inference with XGrammar)
MODAL_ENDPOINT_URL=https://rand--generate.modal.run
MODAL_HEALTH_URL=https://rand--health.modal.run
```

### Testing Connectivity

```bash
# Test health endpoint (fast)
curl https://rand--health.modal.run

# Test generate endpoint (slow on cold start)
curl -X POST https://rand--generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function to add two numbers",
    "schema": {
      "type": "object",
      "properties": {
        "intent": {"type": "object", "properties": {"summary": {"type": "string"}}}
      }
    }
  }'
```

---

## Modal App Details

**App ID**: ap-ibeiutbqDfhjaNJUokFMu7
**Name**: lift-sys-inference
**State**: deployed
**Deployed**: 2025-10-17

### View Logs
```bash
modal app logs lift-sys-inference
```

### Redeploy
```bash
modal deploy lift_sys/inference/modal_app.py
```

### Test Locally
```bash
modal run lift_sys/inference/modal_app.py::test
```

---

## Known Issues & Observations

### Cold Start Behavior
- **Issue**: Generate endpoint can timeout on cold start (>2 minutes)
- **Cause**: Loading 32B model weights (~60GB) into GPU memory
- **Mitigation**:
  - Use health endpoint for connectivity tests
  - Allow 3-5 minute timeout for first request
  - Subsequent requests are much faster if model stays warm
  - Consider keeping model warm with periodic requests

### XGrammar Validation
- **Status**: ✅ Working (confirmed via health endpoint)
- **Model**: vLLM 0.9.2 has native XGrammar support
- **Validation**: Schema constraints are enforced at generation time
- **Regression tracking**: Need to validate constraint enforcement in tests

### Performance vs 7B Model
Expected changes:
- **Quality**: Higher (32B > 7B parameters)
- **Latency**: Higher (larger model, more computation)
- **Cost**: Higher (A100-80GB more expensive than L40S)
- **Baseline**: Need new benchmarks to establish 32B baseline

---

## Usage in Code

### Python (ModalProvider)
```python
import os
from lift_sys.providers.modal_provider import ModalProvider

# Initialize with endpoint from env
endpoint = os.getenv("MODAL_ENDPOINT_URL")
provider = ModalProvider(endpoint_url=endpoint)
await provider.initialize()

# Generate with schema constraints
schema = IRSchema.model_json_schema()
result = await provider.generate_structured(
    prompt="Create a function to find the maximum value in a list",
    schema=schema,
    max_tokens=2048
)
```

### Testing
```python
# Use ResponseRecorder for fast tests
@pytest.mark.integration
@pytest.mark.real_modal
async def test_modal_generation(modal_recorder):
    provider = ModalProvider()

    # First run: hits Modal (slow)
    # Subsequent runs: uses cached response (fast)
    result = await modal_recorder.get_or_record(
        key="test_simple_function",
        generator_fn=lambda: provider.generate_structured(prompt, schema)
    )
```

---

## Next Steps

1. **Baseline Benchmarks**: Run full benchmark suite with 32B model
2. **Integration Tests**: Create `test_modal_provider_real.py`
3. **Performance Monitoring**: Track latency, token usage, costs
4. **Warm-up Strategy**: Implement periodic health checks to keep model loaded

---

**Last Updated**: 2025-10-22
**Owner**: Architecture Team
