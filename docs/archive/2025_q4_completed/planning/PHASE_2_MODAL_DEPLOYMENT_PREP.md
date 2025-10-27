# Modal Production Deployment Prep (lift-sys-374)

**Date**: 2025-10-26
**Status**: Research Complete
**Related Issue**: lift-sys-374
**Estimated Effort**: 6-8 hours

---

## Current Modal Setup

### Deployed Functions

**App 1: lift-sys-inference** (`lift_sys/inference/modal_app.py`)
- **Purpose**: Primary IR generation endpoint using Qwen2.5-Coder-32B
- **GPU**: A100-80GB (1x) - $4/hr when running
- **Resources**:
  - Timeout: 1200s (20 min)
  - Concurrency: 20 max concurrent inputs
  - Scaledown: 600s (10 min keep-warm window)
- **Model**: Qwen/Qwen2.5-Coder-32B-Instruct
- **Backend**: vLLM 0.9.2 + XGrammar for constrained generation
- **Endpoints**:
  - Health: `https://rand--health.modal.run` (GET)
  - Generate: `https://rand--generate.modal.run` (POST)
  - Warmup: `https://rand--warmup.modal.run` (GET)

**App 2: qwen-vllm-inference** (`lift_sys/inference/modal_qwen_vllm.py`)
- **Purpose**: Experimental endpoints for larger Qwen3 models
- **80B Model** (`Qwen3-Next-80B-A3B-Instruct-FP8`):
  - GPU: H100 x2 (tensor parallelism) - ~$8/hr
  - Timeout: 1800s (30 min)
  - Concurrency: 10 max
  - Endpoints: `qwen-80b-health`, `qwen-80b-generate`, `qwen-80b-warmup`
- **480B Model** (`Qwen3-Coder-480B-A35B-Instruct-FP8`):
  - GPU: H100 x8 (tensor parallelism) - ~$32/hr
  - Timeout: 3600s (60 min)
  - Concurrency: 3 max
  - Endpoints: `qwen-480b-health`, `qwen-480b-generate`, `qwen-480b-warmup`

**App 3: lift-sys** (`lift_sys/modal_app.py`)
- **Purpose**: Infrastructure bootstrap (Dicts, Volumes, settings)
- **Not deployed**: Bootstrap only, no functions deployed currently

### Current Configuration

**GPU Types**:
- Primary: A100-80GB (lift-sys-inference)
- Experimental: H100 (Qwen3 models)

**Timeouts**:
- 32B model: 1200s (20 min)
- 80B model: 1800s (30 min)
- 480B model: 3600s (60 min)

**Memory**:
- 32B: gpu_memory_utilization=0.90 (~72GB used on A100-80GB)
- 80B: gpu_memory_utilization=0.85 (~135GB across 2x H100)
- 480B: gpu_memory_utilization=0.80 (~512GB across 8x H100)

**Secrets**:
- `huggingface`: HuggingFace API key (last used 2025-10-24)
- `vllm-dev`: Development environment variables
- `supabase`: Database credentials (URL, ANON_KEY, SERVICE_KEY)

**Volumes**:
- `lift-sys-models`: Model cache for primary inference (32B model)
- `lift-sys-torch-cache`: Torch compilation cache
- `qwen-vllm-models`: Shared cache for Qwen3 experimental models
- `qwen-vllm-torch-cache`: Torch cache for Qwen3 models
- `lift-sys-token-store`: OAuth token storage (Modal Dict)
- `lift-sys-user-prefs`: User preferences (Modal Dict)

### Dev vs Prod Gaps

**Gap 1: No production apps currently deployed**
- Status: All apps stopped (no running containers)
- Current: Development-only usage via `modal serve` and `modal run`
- Needed: Persistent deployment via `modal deploy`

**Gap 2: Hard-coded development endpoints**
- Found in: `lift_sys/dspy_signatures/provider_adapter.py:26`
- Example: `endpoint_url="https://rand--generate.modal.run"`
- Problem: Dev endpoints hard-coded in source files
- Fix: Use environment variable `MODAL_ENDPOINT_URL`

**Gap 3: Environment-based configuration not fully implemented**
- Current: Some env var support (`MODAL_ENDPOINT_URL`, `LIFT_SYS_*`)
- Missing: Production vs staging environment separation
- Missing: Deployment-specific secrets management

**Gap 4: No monitoring/logging configured for production**
- Current: Basic print statements in functions
- Missing: Structured logging with timestamps
- Missing: Error tracking (no Sentry/Honeycomb integration yet)
- Missing: Performance metrics collection

**Gap 5: Expensive keep-warm strategy**
- Current: `scaledown_window=600` (10 min) - balance cost/latency
- Problem: No `keep_warm` for guaranteed sub-second response
- Trade-off: Adding `keep_warm=1` costs ~$2,880/month for A100

**Gap 6: No staging environment**
- Current: Single "prod" deployment (when deployed)
- Missing: Separate staging deployment for testing
- Missing: Blue/green or canary deployment strategy

**Gap 7: Base image optimization incomplete**
- Current: `USE_CUSTOM_BASE = True` in modal_app.py
- Issue: Custom base image (`lift_sys/infrastructure/modal_image.py`) uses SGLang (deprecated)
- Conflict: Main app switched to vLLM, but base image still references SGLang
- Impact: Slower builds (87s) when `USE_CUSTOM_BASE = False`

---

## Production Requirements

### Resource Configuration

```python
# Recommended Modal config for production (32B model)
@app.cls(
    image=llm_image,
    gpu="A100-80GB",  # Or ["L40S", "A100"] for cost/fallback
    volumes={
        MODELS_DIR: volume,
        TORCH_COMPILE_CACHE_DIR: torch_cache_volume,
    },
    timeout=1200,
    scaledown_window=600,
    # keep_warm=1,  # Optional: costs ~$2,880/month
    secrets=[modal.Secret.from_name("prod-modal-secrets")],
)
@modal.concurrent(max_inputs=20)
class ConstrainedIRGenerator:
    # ... implementation
```

### Secrets Needed

**Secret 1: `prod-modal-secrets`**
```bash
modal secret create prod-modal-secrets \
  VLLM_EAGER="0" \
  ENVIRONMENT="production"
```

**Secret 2: `staging-modal-secrets`**
```bash
modal secret create staging-modal-secrets \
  VLLM_EAGER="1" \
  ENVIRONMENT="staging"
```

### Environment Variables

| Variable | Dev Value | Prod Value | Purpose |
|----------|-----------|------------|---------|
| `MODAL_ENDPOINT_URL` | `http://localhost:8001` | `https://rand--generate.modal.run` | Modal inference endpoint |
| `LIFT_SYS_ALLOWED_ORIGINS` | `http://localhost:3000` | `https://lift-sys.vercel.app` | CORS origins |
| `ENVIRONMENT` | `development` | `production` | Runtime environment flag |
| `VLLM_EAGER` | `"1"` | `"0"` | vLLM optimization mode |

---

## Deployment Plan

### Deployment Commands

```bash
# Step 1: Deploy primary inference endpoint (production)
modal deploy lift_sys/inference/modal_app.py

# Step 2: Verify deployment
modal app list | grep lift-sys-inference
curl https://rand--health.modal.run

# Step 3: Warm up the model
curl https://rand--warmup.modal.run
```

### Staging Strategy

```python
# In modal_app.py
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
APP_NAME = f"lift-sys-inference-{ENVIRONMENT}" if ENVIRONMENT != "production" else "lift-sys-inference"
GPU_CONFIG = "A100-80GB" if ENVIRONMENT == "production" else "A10G"
```

### Rollback Plan

```bash
# Stop current deployment
modal app stop lift-sys-inference

# Deploy previous version
git checkout <commit-hash>
modal deploy lift_sys/inference/modal_app.py
```

### Health Monitoring

```bash
# Check health
curl https://rand--health.modal.run

# Monitor logs
modal app logs lift-sys-inference --follow

# Check for errors
modal app logs lift-sys-inference --since 1h | grep ERROR
```

---

## Implementation Checklist

**Phase 1: Preparation (1-2 hours)**
- [ ] Audit hard-coded endpoint URLs in codebase
- [ ] Replace with `os.getenv("MODAL_ENDPOINT_URL")` pattern
- [ ] Create production and staging Modal secrets
- [ ] Review and update Supabase secrets

**Phase 2: Environment Setup (30 min)**
- [ ] Add `ENVIRONMENT` variable support to modal_app.py
- [ ] Create staging deployment configuration
- [ ] Set up environment-specific secrets
- [ ] Create health check script

**Phase 3: Staging Deployment (1 hour)**
- [ ] Deploy staging environment (A10G GPU)
- [ ] Run integration tests against staging
- [ ] Load test staging endpoint
- [ ] Verify cost estimates

**Phase 4: Production Deployment (2 hours)**
- [ ] Deploy production environment (A100-80GB)
- [ ] Run health checks
- [ ] Warm up model
- [ ] Update FastAPI backend environment variables
- [ ] Test end-to-end flow
- [ ] Monitor logs for 30 minutes

**Phase 5: Monitoring & Documentation (1 hour)**
- [ ] Set up log monitoring alerts
- [ ] Document rollback procedures
- [ ] Create deployment runbook
- [ ] Add health check to CI/CD

---

## Estimated Effort

**Total: 6-8 hours**

**Breakdown:**
- Preparation & code cleanup: 2 hours
- Environment configuration: 1 hour
- Staging deployment & testing: 1-2 hours
- Production deployment: 2 hours
- Monitoring setup: 1 hour
- Documentation: 1 hour

---

## Risks

**Risk 1: Cold start latency impacts user experience**
- **Severity**: Medium
- **Mitigation**: Use `scaledown_window=600`, add loading indicator in UI

**Risk 2: Hard-coded dev endpoints cause production failures**
- **Severity**: High
- **Mitigation**: Audit all occurrences, use environment variables

**Risk 3: Cost overrun from unexpected usage**
- **Severity**: High
- **Mitigation**: Set up billing alerts, monitor daily spend

**Risk 4: Environment variable misconfiguration**
- **Severity**: Medium
- **Mitigation**: Use checklist, add validation in startup code

---

## Next Steps

1. Review this preparation document
2. Decide on deployment timeline (staging → prod)
3. Allocate budget for production deployment costs
4. Schedule deployment during low-traffic window
5. Assign owner for deployment execution
