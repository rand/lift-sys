# Modal Deployment Guide

Quick reference for deploying lift-sys inference endpoints to Modal.

## Prerequisites

```bash
# Install Modal CLI
pip install modal

# Authenticate (one-time setup)
modal setup
```

## First-Time Deployment

### Step 1: Build the Base Image

```bash
# Build optimized base image with all dependencies (3-5 minutes, one-time)
modal image build lift_sys/infrastructure/modal_image.py::llm_image
```

This creates a cached image with:
- SGLang 0.5.3.post1
- Transformers 4.51.2
- PyTorch + CUDA
- FastAPI
- All required dependencies

**You only need to do this once**, or when dependencies change.

### Step 2: Verify the Image

```bash
# Test that dependencies are correctly installed
modal run lift_sys/infrastructure/modal_image.py::test_image
```

Expected output:
```
✅ SGLang version: 0.5.3.post1
✅ Transformers version: 4.51.2
✅ PyTorch version: 2.x.x
   CUDA available: True
✅ FastAPI version: 0.115.12
```

### Step 3: Test the Inference Endpoint Locally

```bash
# Run test function to verify model loading and generation
modal run lift_sys/inference/modal_app.py::test
```

This:
- Spins up a GPU container
- Loads the Qwen3 GGUF model (first time: downloads to volume)
- Runs a test generation
- Shuts down

### Step 4: Deploy to Production

```bash
# Deploy inference endpoint (persistent)
modal deploy lift_sys/inference/modal_app.py
```

This creates persistent endpoints:
- Health: `https://rand--health.modal.run` (GET)
- Generate: `https://rand--generate.modal.run` (POST)

## Development Workflow

### Option A: Hot-Reload Development (Recommended)

```bash
# Start development server with automatic reload on code changes
modal serve lift_sys/inference/modal_app.py
```

- Changes to Python code automatically reload
- Fast iteration cycle
- Temporary endpoints (shut down on Ctrl+C)
- Perfect for debugging

### Option B: One-Off Testing

```bash
# Run specific test function
modal run lift_sys/inference/modal_app.py::test

# Run with custom parameters (modify test() function first)
modal run lift_sys/inference/modal_app.py
```

## Testing the Deployed Endpoint

### Health Check

```bash
curl https://rand--health.modal.run
```

Expected response:
```json
{
  "status": "healthy",
  "model": "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
  "gpu": "A10G",
  "backend": "SGLang with XGrammar"
}
```

### Generate IR from Prompt

```bash
curl -X POST https://rand--generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function that validates email addresses",
    "schema": {
      "type": "object",
      "properties": {
        "intent": {
          "type": "object",
          "properties": {"summary": {"type": "string"}},
          "required": ["summary"]
        },
        "signature": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "parameters": {"type": "array"},
            "returns": {"type": "string"}
          },
          "required": ["name", "parameters"]
        }
      },
      "required": ["intent", "signature"]
    },
    "max_tokens": 1024,
    "temperature": 0.3
  }'
```

## Monitoring

### View Logs

```bash
# Stream logs in real-time
modal app logs lift-sys-inference --follow

# View recent logs
modal app logs lift-sys-inference

# View logs for specific time range
modal app logs lift-sys-inference --since 1h
```

### Check App Status

```bash
# List all deployed apps
modal app list

# Show app details
modal app show lift-sys-inference

# View endpoint URLs
modal app show lift-sys-inference
```

### Stop the App

```bash
# Stop the deployed app (endpoints become unavailable)
modal app stop lift-sys-inference

# Restart by redeploying
modal deploy lift_sys/inference/modal_app.py
```

## Updating the Deployment

### Code Changes Only

```bash
# Fast redeploy (uses cached image, ~10-20 seconds)
modal deploy lift_sys/inference/modal_app.py
```

### Dependency Updates

If you update dependencies in `lift_sys/infrastructure/modal_image.py`:

```bash
# 1. Rebuild base image
modal image build lift_sys/infrastructure/modal_image.py::llm_image

# 2. Redeploy inference endpoint
modal deploy lift_sys/inference/modal_app.py
```

### Model Updates

To change the model (e.g., different quantization or model variant):

1. Update `MODEL_NAME` and `MODEL_FILE` in `modal_app.py`
2. Redeploy:
   ```bash
   modal deploy lift_sys/inference/modal_app.py
   ```
3. First request will download new model to volume

## Performance Tuning

### Reduce Cold Start Time

**Current:** ~30-60 seconds (model loading from volume)

**Option 1: Keep warm** (costs ~$1.10/hr for idle A10G)
```python
@app.cls(
    keep_warm=1,  # Always keep 1 container ready
    # ... other config
)
```

**Option 2: Increase scaledown window** (already at 5 minutes)
```python
@app.cls(
    scaledown_window=600,  # Keep warm for 10 minutes
    # ... other config
)
```

### Improve Throughput

**Option 1: Use larger GPU** (faster inference, higher cost)
```python
GPU_CONFIG = "A100"  # ~$3/hr instead of $1.10/hr
```

**Option 2: Enable multi-GPU** (for very high load)
```python
GPU_CONFIG = modal.gpu.A10G(count=2)  # 2x A10G
```

**Option 3: Increase concurrency**
```python
@modal.concurrent(max_inputs=40)  # Process more requests in parallel
```

## Cost Optimization

### Current Configuration
- **GPU:** A10G (~$1.10/hr when running)
- **Scaledown:** 5 minutes after last request
- **Idle cost:** $0 (scales to zero)
- **Average request:** ~2-3 seconds on GPU

### Estimated Costs

**Low traffic** (10 requests/day):
- Total GPU time: ~30 seconds/day
- Monthly cost: ~$0.05

**Medium traffic** (100 requests/day, spread throughout day):
- Container stays warm due to scaledown_window
- Average uptime: ~4 hours/day
- Monthly cost: ~$130

**High traffic** (1000 requests/day):
- Container almost always warm
- Average uptime: ~20 hours/day
- Monthly cost: ~$660
- Consider: `keep_warm=1` for consistent latency

### Cost Reduction Strategies

1. **Batch requests** when possible
2. **Use smaller GPU** for development (T4 @ $0.60/hr)
3. **Reduce scaledown_window** if traffic is sparse
4. **Profile cold starts** and optimize model loading

```bash
# Profile to see where time is spent
modal run lift_sys/inference/modal_app.py::test --profile
```

## Troubleshooting

### Container fails to start

**Check logs:**
```bash
modal app logs lift-sys-inference --since 10m
```

**Common issues:**
- GPU not available: Add fallback in `GPU_CONFIG = ["A10G", "A100", "any"]`
- Image not built: Run `modal image build ...`
- Import errors: Verify base image includes all dependencies

### Slow cold starts

**Current:** ~30-60 seconds is expected for first request after idle

**To improve:**
- Use `keep_warm=1` for always-ready container
- Increase `scaledown_window` to keep containers alive longer
- Check if model is cached in volume: `modal volume list`

### High costs

**Check usage:**
```bash
# View app metrics in Modal dashboard
modal app show lift-sys-inference
```

**Reduce costs:**
- Decrease `scaledown_window` if traffic is sparse
- Use smaller GPU for development
- Set `keep_warm=0` (default)

### Model loading fails

**Check volume:**
```bash
modal volume list
modal volume ls lift-sys-models
```

**Clear cache and retry:**
```bash
# Delete and recreate volume (WARNING: model will be re-downloaded)
modal volume delete lift-sys-models
modal deploy lift_sys/inference/modal_app.py
```

## Advanced Configuration

### Use Different Model

```python
# In modal_app.py
MODEL_NAME = "unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
MODEL_FILE = "Qwen3-Coder-30B-A3B-Instruct-Q8_0.gguf"  # Higher quality, more memory
```

### Enable GPU Fallback

```python
# Try multiple GPUs in order
GPU_CONFIG = ["L40S", "A100", "A10G", "any"]
```

### Customize Scaledown Behavior

```python
@app.cls(
    scaledown_window=0,  # Shut down immediately after request
    # or
    scaledown_window=1800,  # Keep warm for 30 minutes
)
```

## References

- Modal Documentation: https://modal.com/docs/guide
- Modal Pricing: https://modal.com/pricing
- SGLang Documentation: https://sgl-project.github.io/
- lift-sys Modal Reference: `MODAL_REFERENCE.md`
- Base Image Implementation: `../lift_sys/infrastructure/modal_image.py`

## Quick Command Reference

```bash
# Build base image (one-time)
modal image build lift_sys/infrastructure/modal_image.py::llm_image

# Test locally
modal run lift_sys/inference/modal_app.py::test

# Development with hot-reload
modal serve lift_sys/inference/modal_app.py

# Deploy to production
modal deploy lift_sys/inference/modal_app.py

# View logs
modal app logs lift-sys-inference --follow

# Check status
modal app show lift-sys-inference

# Stop app
modal app stop lift-sys-inference

# Test endpoint
curl https://rand--health.modal.run
```
