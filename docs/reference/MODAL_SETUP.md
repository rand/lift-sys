# Modal.com Setup Guide for LIFT System

This guide walks through setting up GPU-accelerated, schema-constrained IR generation on Modal.com.

## Prerequisites

- Modal account (sign up at https://modal.com)
- Modal CLI installed (`uv add modal` - already done ✅)

## Step 1: Authenticate with Modal

Open a terminal and run:

```bash
uv run modal token new
```

This will:
1. Open your browser for OAuth authentication
2. Create API tokens and save them to `~/.modal.toml`
3. Display your workspace name

**Note**: You only need to do this once per machine.

## Step 2: Test the Modal App Locally

Before deploying to the cloud, test locally:

```bash
uv run modal run lift_sys/inference/modal_app.py::test
```

This will:
- Load the model in a Modal container
- Generate a test IR
- Display the results

**Expected output**:
```json
{
  "ir_json": {
    "intent": {"summary": "..."},
    "signature": {"name": "add", "parameters": [...], ...}
  },
  "tokens_used": 150,
  "generation_time_ms": 450.2,
  "finish_reason": "stop"
}
```

**Note**: First run will be slow (~2-3 minutes) as Modal downloads the model. Subsequent runs use cached model.

## Step 3: Deploy to Modal

Deploy the inference endpoint:

```bash
uv run modal deploy lift_sys/inference/modal_app.py
```

This will:
1. Build the container image with vLLM + XGrammar
2. Deploy to Modal's cloud
3. Return your endpoint URLs

**Expected output**:
```
✓ Created objects.
├── 🔨 Created mount /Users/rand/src/lift-sys
├── 🔨 Created function generate_ir.
└── 🔨 Created function health.

View Deployment: https://modal.com/apps/your-workspace/lift-sys-inference

Web endpoints:
- https://your-workspace--lift-sys-inference-generate-ir.modal.run
- https://your-workspace--lift-sys-inference-health.modal.run
```

**Save these URLs** - you'll need them for configuration!

## Step 4: Test the Deployed Endpoint

Test the live endpoint with curl:

```bash
curl -X POST "https://your-workspace--lift-sys-inference-generate-ir.modal.run" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function called multiply that takes two numbers and returns their product",
    "schema": {
      "type": "object",
      "properties": {
        "intent": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
        "signature": {"type": "object", "properties": {"name": {"type": "string"}, "parameters": {"type": "array"}}, "required": ["name", "parameters"]}
      },
      "required": ["intent", "signature"]
    },
    "max_tokens": 1024,
    "temperature": 0.3
  }'
```

You should receive a JSON response with valid IR!

## Step 5: Configure LIFT API

Add the Modal endpoint to your `.env` file:

```bash
echo 'MODAL_ENDPOINT_URL="https://your-workspace--lift-sys-inference-generate-ir.modal.run"' >> .env
```

**Replace** `your-workspace` with your actual Modal workspace name from the deployment output.

## Step 6: Restart the LIFT API

Restart the API server to pick up the new configuration:

```bash
# Kill the current server (Ctrl+C in the terminal running it)
# Then restart with:
./start.sh
```

The LIFT API will now use Modal for constrained IR generation!

## Monitoring & Management

### View Logs

```bash
uv run modal app logs lift-sys-inference
```

### View Costs

Visit: https://modal.com/settings/billing

**Typical costs**:
- A10G GPU: ~$1.10/hour (only when processing requests)
- Container idle time: Billed at GPU rate (we keep warm for 5 minutes)
- **Estimated**: ~$0.001-0.002 per IR generation (very cheap!)

### Update Deployment

After making changes to `modal_app.py`:

```bash
uv run modal deploy lift_sys/inference/modal_app.py
```

### Stop All Containers (save money)

```bash
uv run modal app stop lift-sys-inference
```

Containers will auto-start on next request (with ~30s cold start).

## Model Configuration

### Current Model
- **Qwen2.5-Coder-32B-Instruct**: 32B parameters, excellent for code tasks
- **License**: Apache 2.0 (can use commercially)
- **Context**: 8K tokens

### Alternative Models

Edit `lift_sys/inference/modal_app.py` and change `MODEL_NAME`:

**Smaller/Faster** (lower cost):
```python
MODEL_NAME = "Qwen/Qwen2.5-Coder-7B-Instruct"  # 7B model, faster/cheaper
```

**Larger/Better** (higher cost):
```python
MODEL_NAME = "deepseek-ai/DeepSeek-Coder-V2-Instruct"  # 236B MoE, highest quality
GPU_CONFIG = modal.gpu.A100(count=2, size="80GB")  # Needs more GPU memory
```

### GPU Configuration

For higher traffic, use A100:

```python
GPU_CONFIG = modal.gpu.A100(count=1, size="40GB")  # ~$3/hr, 3x faster inference
```

## Troubleshooting

### "Model not found" error

Check the model name is correct on HuggingFace:
```bash
# Visit: https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct
```

### "Out of memory" error

Reduce `max_model_len` or use smaller model:
```python
max_model_len=4096,  # Reduce from 8192
```

### Slow cold starts

Increase `container_idle_timeout`:
```python
container_idle_timeout=600,  # Keep warm for 10 minutes (costs more)
```

### High costs

- Reduce `container_idle_timeout` (containers shut down faster)
- Use smaller model (7B instead of 32B)
- Use A10G instead of A100

## Next Steps

Once deployed and configured:

1. ✅ Modal endpoint is live
2. ✅ LIFT API configured with Modal URL
3. ✅ Schema-constrained IR generation working
4. 🎯 Run end-to-end tests to verify
5. 🎯 Adjust GPU/model config based on performance needs

See the main README for full system documentation.
