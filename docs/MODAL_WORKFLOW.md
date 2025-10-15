# Modal Workflow for LIFT System
**Date**: October 14, 2025
**Reference**: https://modal.com/docs/guide/developing-with-llms

---

## Overview

This document outlines the updated approach for developing and deploying LLM inference on Modal, based on official Modal best practices.

---

## Key Improvements

### 1. Development Workflow

**Before**: Only using `modal deploy` for all changes

**After**: Three-tier workflow based on use case

```bash
# Development with hot-reload (best for iterating)
modal serve lift_sys/inference/modal_app.py

# One-time test run
modal run lift_sys/inference/modal_app.py::test

# Production deployment
modal deploy lift_sys/inference/modal_app.py
```

**Benefits**:
- Hot-reload with `modal serve` speeds up development
- Clear separation between dev and production
- Can test locally before deploying

### 2. GPU Configuration

**Before**:
```python
GPU_CONFIG = "A10G"  # String-based
```

**After**:
```python
GPU_CONFIG = modal.gpu.A10G()  # Object-based with better typing
# Can also use fallback chain:
# GPU_CONFIG = ["A10G", "A100", "any"]
```

**Benefits**:
- Better type safety
- Easier to add fallback options for availability
- Clearer configuration

### 3. Model Caching with Volumes

**New Addition**:
```python
MODELS_DIR = "/models"
volume = modal.Volume.from_name("lift-sys-models", create_if_missing=True)

@app.cls(
    volumes={MODELS_DIR: volume},  # Mount volume
    ...
)
```

**In load_model()**:
```python
# Set HuggingFace cache to use Modal volume
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = f"{MODELS_DIR}/transformers"

# After model loads...
volume.commit()  # Persist cache
```

**Benefits**:
- **First cold start**: Downloads model (~30-60s download + load)
- **Subsequent cold starts**: Loads from volume cache (~5-10s)
- **Warm requests**: Container already has model loaded (<1s)
- **Cost savings**: Reduces cold start times significantly

### 4. Container Lifecycle Management

**Pattern**:
```python
@app.cls(
    image=image,           # Custom dependencies
    gpu=GPU_CONFIG,        # GPU requirements
    volumes={...},         # Persistent storage
    timeout=600,           # Max runtime
    scaledown_window=300,  # Keep warm period
)
@modal.concurrent(max_inputs=20)  # Concurrent requests
class ConstrainedIRGenerator:
    @modal.enter()  # Called once on container start
    def load_model(self):
        ...

    @modal.method()  # Called per request
    def generate(self, ...):
        ...
```

**Lifecycle**:
1. Container starts → `@modal.enter()` loads model
2. Requests arrive → `@modal.method()` handles inference
3. No requests for 5min → Container scales down
4. New request → Container restarts (model loads from volume cache)

---

## Development Workflow Guide

### Local Development

1. **Make code changes** to `lift_sys/inference/modal_app.py`

2. **Start dev server with hot-reload**:
   ```bash
   modal serve lift_sys/inference/modal_app.py
   ```
   - Server starts at https://rand--{function}.modal.run
   - Code changes auto-reload
   - See logs in terminal

3. **Test endpoint**:
   ```bash
   curl https://rand--health.modal.run
   ```

4. **Iterate** - Make changes, they reload automatically

### Testing

1. **Run one-time test**:
   ```bash
   modal run lift_sys/inference/modal_app.py::test
   ```
   - Runs the `test()` function
   - Useful for validation before deploy

2. **Run local test script**:
   ```bash
   uv run python test_modal_endpoint.py
   ```
   - Tests all endpoints E2E
   - Measures latency
   - Validates output

### Production Deployment

1. **Deploy to production**:
   ```bash
   modal deploy lift_sys/inference/modal_app.py
   ```
   - Creates production deployment
   - Endpoints become stable
   - No auto-reload

2. **Monitor deployment**:
   ```bash
   modal app list
   modal app logs lift-sys-inference
   ```

3. **Stop if needed**:
   ```bash
   modal app stop lift-sys-inference
   ```

---

## Performance Characteristics

### Cold Start Times

| Scenario | Time | Notes |
|----------|------|-------|
| **First ever deploy** | 60-90s | Download model + load to GPU |
| **Subsequent cold starts** | 10-20s | Load from volume cache |
| **Warm container** | <100ms | Model already loaded |

### Request Latency

| Operation | Time | Notes |
|-----------|------|-------|
| **Health check** | <50ms | No GPU, lightweight |
| **IR generation (cold)** | 15-25s | Includes model load from cache |
| **IR generation (warm)** | 2-5s | Just inference |
| **Code generation (warm)** | 3-7s | Constrained generation |

### Cost

| Component | Cost | Notes |
|-----------|------|-------|
| **A10G GPU** | ~$1.10/hr | Only while running |
| **Volume storage** | ~$0.10/GB/month | Model cache (~60GB) |
| **Per-request (warm)** | ~$0.001-0.003 | Assuming 2-5s @ $1.10/hr |
| **Idle cost** | $0 | Serverless, pay only when running |

**Optimization**: 5-minute scaledown window balances:
- Responsiveness (model stays warm for bursts)
- Cost (scales to zero after inactivity)

---

## Volume Management

### Model Cache Volume

**Purpose**: Persist downloaded models across container restarts

**Commands**:
```bash
# List volumes
modal volume list

# Inspect volume
modal volume ls lift-sys-models /models

# Delete volume (forces re-download)
modal volume delete lift-sys-models
```

**Directory Structure**:
```
/models/
├── transformers/
│   └── models--Qwen--Qwen3-Coder-30B-A3B-Instruct/
│       ├── snapshots/
│       └── refs/
└── hub/
```

**Best Practices**:
- Commit volume after model loads: `volume.commit()`
- Don't commit on every request (performance)
- Delete and recreate if corrupted

---

## Debugging Tips

### View Logs

```bash
# Real-time logs
modal app logs lift-sys-inference --follow

# Recent logs
modal app logs lift-sys-inference
```

### Check Container Status

```bash
# List running apps
modal app list

# Show app details
modal app show lift-sys-inference
```

### Test Locally First

```bash
# Use modal run to test without deploying
modal run lift_sys/inference/modal_app.py::test
```

### Enable Verbose Output

Add to code:
```python
import modal
modal.enable_output()  # Shows all logs
```

---

## Common Issues

### Issue: "Model not found"
**Cause**: HuggingFace cache not set correctly
**Fix**: Ensure `os.environ["HF_HOME"] = MODELS_DIR` before loading

### Issue: "GPU out of memory"
**Cause**: Model too large for A10G (24GB)
**Fix**:
- Reduce `context_length` from 8192 to 4096
- Or switch to A100: `GPU_CONFIG = modal.gpu.A100()`

### Issue: "Slow cold starts"
**Cause**: Model downloading every time
**Fix**: Ensure volume is mounted and `volume.commit()` is called

### Issue: "Import error for sglang"
**Cause**: Container image doesn't have dependencies
**Fix**: Verify `sglang[all]>=0.5.3.post1` in `image.pip_install()`

---

## Comparison: vLLM vs SGLang on Modal

| Feature | vLLM | SGLang |
|---------|------|--------|
| **Qwen3 Support** | ❌ No | ✅ Yes |
| **XGrammar** | Via plugin | Built-in default |
| **JSON Decoding** | Standard | 3-10x faster |
| **Caching** | PagedAttention | RadixAttention (better) |
| **Setup Complexity** | More config | Simpler |
| **Community** | Larger | Rapidly growing |

**Decision**: SGLang chosen for native Qwen3 support and faster constrained generation.

---

## Next Steps

1. **Complete deployment** of SGLang-based Modal app
2. **Run E2E tests** with `test_modal_endpoint.py`
3. **Measure real performance** vs estimates
4. **Document actual metrics** for cost planning
5. **Iterate on prompts** for better IR quality

---

## References

- [Modal LLM Development Guide](https://modal.com/docs/guide/developing-with-llms)
- [SGLang Documentation](https://docs.sglang.ai)
- [XGrammar Documentation](https://xgrammar.mlc.ai)
- [Modal GPU Configuration](https://modal.com/docs/guide/gpu)
- [Modal Volumes](https://modal.com/docs/guide/volumes)

---

**Updated**: October 14, 2025
**Status**: Ready for deployment testing
