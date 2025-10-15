# Modal Reference Guide

A comprehensive reference for using Modal in the lift-sys project and beyond.

**Resources:**
- Examples: https://github.com/modal-labs/modal-examples
- Guides: https://modal.com/docs/guide
- API Reference: https://modal.com/docs/reference

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [GPU Usage](#gpu-usage)
4. [Container Images](#container-images)
5. [Developing with LLMs](#developing-with-llms)
   - [Development Workflow](#development-workflow)
   - [Model Caching with Volumes](#model-caching-with-volumes)
   - [GPU Selection Strategies](#gpu-selection-strategies)
   - [Cold Start Optimization](#cold-start-optimization)
   - [Batching and Concurrency](#batching-and-concurrency)
   - [Monitoring and Debugging](#monitoring-and-debugging)
6. [Secrets Management](#secrets-management)
7. [Volumes & Storage](#volumes--storage)
8. [Web Endpoints](#web-endpoints)
9. [Scheduling](#scheduling)
10. [Best Practices](#best-practices)
11. [Common Patterns](#common-patterns)

---

## Quick Start

### Installation & Setup
```bash
pip install modal
modal setup  # Authenticate with Modal
```

### Basic Function
```python
import modal

app = modal.App("my-app")

@app.function()
def hello(name: str):
    return f"Hello {name}!"

# Run locally
@app.local_entrypoint()
def main():
    result = hello.remote("World")
    print(result)
```

### Running
```bash
modal run script.py          # Run locally
modal serve script.py        # Serve with hot reload
modal deploy script.py       # Deploy to cloud
```

---

## Core Concepts

### App Structure
`App` is the main deployment unit that bundles functions, classes, and configuration.

```python
import modal

app = modal.App("my-app")

@app.function()
def my_function():
    return "Hello"

@app.cls()
class MyClass:
    @modal.method()
    def my_method(self):
        return "World"
```

### Function Decorators

| Decorator | Purpose | Example |
|-----------|---------|---------|
| `@app.function()` | Define serverless function | `@app.function(gpu="A100")` |
| `@app.cls()` | Define serverless class | `@app.cls(gpu="T4")` |
| `@app.local_entrypoint()` | Define local entry point | For CLI execution |

### Class Lifecycle Hooks

```python
@app.cls()
class MyModel:
    @modal.enter()
    def load_model(self):
        """Called once when container starts"""
        self.model = load_heavy_model()

    @modal.method()
    def predict(self, data):
        """Called for each inference"""
        return self.model.predict(data)

    @modal.exit()
    def cleanup(self):
        """Called when container shuts down"""
        self.model.cleanup()
```

---

## GPU Usage

### Available GPU Types

| GPU | Memory | Max Count | Best For |
|-----|--------|-----------|----------|
| **T4** | 16GB | 8 | Development, small models |
| **L4** | 24GB | 8 | Cost-effective inference |
| **A10** | 24GB | 4 | General purpose |
| **L40S** | 48GB | 8 | **Recommended** - Best cost/performance |
| **A100** | 40/80GB | 8 | Training, large models |
| **H100** | 80GB | 8 | High-performance training |
| **H200** | 141GB | 8 | Largest memory needs |
| **B200** | - | 8 | Flagship, most powerful |

### Usage

```python
# Single GPU
@app.function(gpu="L40S")
def train():
    import torch
    assert torch.cuda.is_available()
    return "Training on L40S"

# Multiple GPUs
@app.function(gpu="H100:8")
def multi_gpu_train():
    import torch
    assert torch.cuda.device_count() == 8
    return "Training on 8x H100"

# GPU Fallback
@app.function(gpu=["H100", "A100", "L40S"])
def flexible_gpu():
    """Will use first available GPU from list"""
    pass
```

### Best Practices
- **L40S** recommended for most neural network workloads
- Understand your bottleneck before choosing expensive GPUs
- Memory-bound jobs may not benefit from faster GPUs
- Consider batch size and memory constraints
- Check pricing at https://modal.com/pricing

---

## Container Images

### Building Images

Modal uses a code-first approach to define container environments.

#### Python Packages (Use `uv` via `uv_pip_install`)

```python
image = modal.Image.debian_slim(python_version="3.11").uv_pip_install(
    "torch==2.1.0",
    "transformers==4.35.0",
    "numpy",
    "pandas==2.2.0",
)

@app.function(image=image)
def my_function():
    import torch
    return torch.__version__
```

#### System Packages

```python
image = modal.Image.debian_slim().apt_install(
    "git",
    "curl",
    "ffmpeg",
    "build-essential",
)
```

#### Environment Variables

```python
image = modal.Image.debian_slim().env({
    "PORT": "6443",
    "MODEL_PATH": "/models",
})
```

#### Running Commands

```python
image = (
    modal.Image.debian_slim()
    .run_commands(
        "git clone https://github.com/example/repo /repo",
        "cd /repo && make install",
    )
)
```

#### Local Files

```python
image = (
    modal.Image.debian_slim()
    .add_local_dir("./src", remote_path="/app/src")
    .add_local_file("./config.yaml", remote_path="/app/config.yaml")
    .add_local_python_source()  # Add local Python modules
)
```

#### Complex Image Example

```python
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg")
    .uv_pip_install(
        "torch==2.1.0",
        "transformers==4.35.0",
    )
    .env({"HF_HOME": "/cache"})
    .run_commands("mkdir -p /cache")
    .add_local_dir("./models", remote_path="/models")
)
```

### Image Building Best Practices
- **Pin dependency versions** for reproducibility
- **Place frequently changing layers last** to optimize caching
- Use `uv_pip_install` for Python packages (faster than pip)
- Use `run_function()` for complex setup logic
- Leverage caching by keeping stable layers first

### Pre-Built Base Images (Advanced)

For production deployments with frequent code updates, create a **pre-built base image** to cache dependencies.

**Problem:** Inline `image.pip_install()` rebuilds on every deployment
**Solution:** Build image once, reuse across deployments

```python
# lift_sys/infrastructure/modal_image.py
import modal

llm_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "sglang[all]==0.5.3.post1",  # Pin exact versions
        "transformers==4.51.2",
        "fastapi[standard]==0.115.12",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",  # Fast model downloads
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    })
)

__all__ = ["llm_image"]
```

**Build and cache the image:**
```bash
# One-time build (3-5 minutes)
modal image build lift_sys/infrastructure/modal_image.py::llm_image

# Rebuilds are instant after this
```

**Use in your app:**
```python
# modal_app.py
from lift_sys.infrastructure.modal_image import llm_image

@app.function(image=llm_image)  # Use pre-built image
def my_function():
    # Code changes deploy in seconds, not minutes
    pass
```

**Benefits:**
- ✅ **Faster deployments**: Code changes deploy in seconds
- ✅ **Faster cold starts**: No pip install on container startup
- ✅ **Reproducibility**: Exact versions locked
- ✅ **Cost savings**: Less build time = less compute time

**When to rebuild:**
- Dependency version updates
- New dependencies added
- Monthly maintenance (optional)

**lift-sys Implementation:**
See `lift_sys/infrastructure/modal_image.py` for the production-ready base image.

---

## Developing with LLMs

Modal is purpose-built for LLM workloads. This section covers best practices for deploying, serving, and iterating on LLM applications.

### Development Workflow

Modal provides three commands for different development stages:

```bash
# 1. modal run - One-time execution, iterative development
modal run script.py::my_function

# 2. modal serve - Development with hot-reload (web endpoints)
modal serve script.py

# 3. modal deploy - Production deployment
modal deploy script.py
```

**When to use each:**

| Command | Use Case | Hot Reload | Persistent |
|---------|----------|------------|------------|
| `modal run` | Testing functions, debugging, one-off tasks | ❌ No | ❌ No |
| `modal serve` | Developing web endpoints, rapid iteration | ✅ Yes | ❌ No |
| `modal deploy` | Production, scheduled jobs | ❌ No | ✅ Yes |

**Example Workflow:**
```python
import modal

app = modal.App("my-llm-app")

@app.function(gpu="A10G")
def generate_text(prompt: str):
    # Your LLM code here
    return result

@app.local_entrypoint()
def main():
    """For modal run"""
    result = generate_text.remote("Hello world")
    print(result)

@app.function()
@modal.fastapi_endpoint(method="POST")
def api_generate(prompt: str):
    """For modal serve"""
    return generate_text.remote(prompt)
```

```bash
# Development: Test the function
modal run script.py

# Development: Start web endpoint with hot-reload
modal serve script.py
# Visit https://your-workspace--api-generate.modal.run

# Production: Deploy persistently
modal deploy script.py
```

### Model Caching with Volumes

**Problem:** Models download from HuggingFace on every cold start (slow, expensive bandwidth)

**Solution:** Use Modal Volumes to cache models persistently

```python
import modal
import os

app = modal.App("llm-with-cache")

# Create volume for model cache
MODEL_DIR = "/models"
volume = modal.Volume.from_name("model-cache", create_if_missing=True)

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "transformers>=4.51.0",
    "torch==2.5.1",
    "sglang[all]>=0.5.3.post1",
)

@app.cls(
    gpu="A10G",
    image=image,
    volumes={MODEL_DIR: volume},  # Mount persistent cache
)
class ModelServer:
    @modal.enter()
    def load_model(self):
        """Load model once, cache to volume"""
        from transformers import AutoModel

        # Point HuggingFace cache to volume
        os.environ["HF_HOME"] = MODEL_DIR
        os.environ["TRANSFORMERS_CACHE"] = f"{MODEL_DIR}/transformers"

        print(f"Loading model (cached in {MODEL_DIR})")
        self.model = AutoModel.from_pretrained(
            "Qwen/Qwen3-Coder-30B-A3B-Instruct",
            cache_dir=MODEL_DIR,  # Save to volume
            trust_remote_code=True,
        )

        # Commit changes to persist cache
        volume.commit()

    @modal.method()
    def generate(self, prompt: str):
        """Inference uses cached model"""
        return self.model(prompt)
```

**Benefits:**
- **First run**: Downloads model, saves to volume (slow)
- **Subsequent runs**: Loads from volume (fast - seconds instead of minutes)
- **Cost savings**: No repeated downloads from HuggingFace

**Volume Best Practices:**
- Always call `volume.commit()` after writing model weights
- Use environment variables to point cache dirs to volume:
  - `HF_HOME` - HuggingFace home directory
  - `TRANSFORMERS_CACHE` - Transformers model cache
  - `TORCH_HOME` - PyTorch model cache
- One volume per model family (e.g., "qwen-models", "llama-models")

### GPU Selection Strategies

Modal supports flexible GPU configuration for availability and cost optimization:

#### Single GPU
```python
@app.function(gpu="A10G")  # Specific GPU
def inference():
    pass
```

#### Multiple GPUs (Tensor Parallelism)
```python
@app.function(gpu="H100:4")  # 4x H100
def multi_gpu_training():
    pass
```

#### GPU Fallback Chain
```python
# Try GPUs in order, use first available
@app.function(gpu=["H100", "A100", "A10G", "any"])
def flexible_inference():
    pass
```

**Using `modal.gpu` Helper:**
```python
import modal

# Explicit GPU objects for more control
@app.function(gpu=modal.gpu.A10G())
def inference_a10g():
    pass

@app.function(gpu=modal.gpu.H100(count=4))
def training_multi_gpu():
    pass

# Fallback with any GPU
@app.function(gpu=modal.gpu.any())
def run_on_anything():
    pass
```

**Recommendations:**
- **Development**: Use `gpu="A10G"` or `gpu=["A10G", "any"]` for cost efficiency
- **Production**: Use specific GPU with fallback: `gpu=["L40S", "A100"]`
- **Training**: Use `gpu="H100:8"` for multi-GPU parallelism
- **Inference**: L40S offers best cost/performance for most models

### Cold Start Optimization

Cold starts happen when Modal spins up a new container. For LLMs, this includes model loading.

**Optimization Strategies:**

#### 1. Keep Containers Warm
```python
@app.function(
    gpu="A10G",
    keep_warm=1,  # Keep 1 container always ready
)
def inference():
    pass
```

**Trade-offs:**
- ✅ Zero cold starts for users
- ❌ Pay for idle GPU time (~$1.10/hr for A10G)
- Use for: Production APIs with consistent traffic

#### 2. Use `scaledown_window`
```python
@app.function(
    gpu="A10G",
    scaledown_window=300,  # Keep warm for 5 minutes after last request
)
def inference():
    pass
```

**Trade-offs:**
- ✅ Balance responsiveness and cost
- ✅ No charge if no requests
- Use for: Moderate traffic, development

#### 3. Cache Models with Volumes (Best)
```python
@app.cls(
    gpu="A10G",
    volumes={"/models": volume},  # Cached model loads in seconds
)
class ModelServer:
    @modal.enter()
    def load_model(self):
        # Load from cached volume
        self.model = load_from_cache("/models")
```

**Best Practices:**
- Combine all three: volume caching + scaledown_window + (optional) keep_warm
- Profile cold start time: `modal run script.py --profile`
- Monitor cold starts in Modal dashboard

### Batching and Concurrency

Process multiple requests efficiently to maximize GPU utilization.

#### Dynamic Batching
```python
@app.function(gpu="A10G")
@modal.batched(max_batch_size=32, wait_ms=100)
def batch_inference(prompts: list[str]) -> list[str]:
    """Modal automatically batches requests"""
    # Process all prompts together on GPU
    results = model.generate(prompts)
    return results

# Clients call individually, Modal batches automatically
result = batch_inference.remote("single prompt")
```

**Benefits:**
- Automatic batching by Modal
- Better GPU utilization (process 32 requests at once)
- Lower latency for individual requests

#### Concurrent Processing
```python
@app.cls(gpu="A10G")
@modal.concurrent(max_inputs=20)  # Process up to 20 requests in parallel
class ModelServer:
    @modal.method()
    def generate(self, prompt: str):
        return self.model(prompt)
```

**Use Cases:**
- **`@modal.batched`**: Requests can be processed together (same operation)
- **`@modal.concurrent`**: Independent requests, different operations

### Monitoring and Debugging

#### View Logs in Real-Time
```bash
# Stream logs for deployed app
modal app logs my-llm-app

# Follow logs (like tail -f)
modal app logs my-llm-app --follow
```

#### Enable Detailed Output
```python
import modal

# Enable detailed logging for debugging
modal.enable_output()

@app.function(gpu="A10G")
def inference(prompt: str):
    print(f"Received prompt: {prompt}")  # Appears in logs
    result = model.generate(prompt)
    print(f"Generated {len(result)} tokens")
    return result
```

#### View App Status
```bash
# List all running apps
modal app list

# Get app details
modal app show my-llm-app

# Stop app
modal app stop my-llm-app
```

#### Profile Performance
```bash
# Profile cold start and execution time
modal run script.py --profile
```

**Output includes:**
- Container startup time
- Model loading time (`@modal.enter()`)
- Function execution time

### Complete LLM Serving Example

```python
import modal
import os

app = modal.App("production-llm-server")

# Model configuration
MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
MODEL_DIR = "/models"
volume = modal.Volume.from_name("qwen-models", create_if_missing=True)

# Container image
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "sglang[all]>=0.5.3.post1",
    "torch==2.5.1",
    "transformers>=4.51.0",
)

@app.cls(
    image=image,
    gpu=modal.gpu.A10G(),  # Or ["L40S", "A100"] for fallback
    volumes={MODEL_DIR: volume},
    scaledown_window=300,  # Keep warm 5 min after last request
    # keep_warm=1,  # Optional: always keep 1 container ready (costs more)
)
@modal.concurrent(max_inputs=20)  # Handle 20 concurrent requests
class ModelServer:
    @modal.enter()
    def load_model(self):
        """Load model on container startup"""
        from sglang import Runtime

        # Cache to volume
        os.environ["HF_HOME"] = MODEL_DIR
        os.environ["TRANSFORMERS_CACHE"] = f"{MODEL_DIR}/transformers"

        print(f"Loading {MODEL_NAME} from cache")
        self.llm = Runtime(
            model_path=MODEL_NAME,
            tp_size=1,
            context_length=8192,
            trust_remote_code=True,
            mem_fraction_static=0.90,
        )

        volume.commit()
        print("Model loaded successfully")

    @modal.method()
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text from prompt"""
        response = self.llm.generate(
            prompts=[prompt],
            sampling_params={"max_new_tokens": max_tokens, "temperature": 0.7},
        )
        return response[0]["text"]

# Web endpoint
@app.function()
@modal.fastapi_endpoint(method="POST")
def generate_api(prompt: str, max_tokens: int = 512):
    """HTTP API for text generation"""
    server = ModelServer()
    result = server.generate.remote(prompt, max_tokens)
    return {"result": result}

# Test function
@app.local_entrypoint()
def test():
    """Test the model locally"""
    server = ModelServer()
    result = server.generate.remote("Write a Python function to calculate fibonacci")
    print(result)
```

**Deploy:**
```bash
# Development with hot-reload
modal serve script.py

# Production deployment
modal deploy script.py

# Test locally
modal run script.py::test
```

**Access:**
```bash
# Get endpoint URL
modal app show production-llm-server

# Call API
curl -X POST https://your-workspace--generate-api.modal.run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world", "max_tokens": 100}'
```

---

## Secrets Management

### Creating Secrets

#### 1. Web Dashboard (Easiest)
- Navigate to Modal dashboard → Secrets panel
- Use templates for common services (AWS, OpenAI, etc.)
- Add key-value pairs manually

#### 2. Command Line

```bash
modal secret create my-secret KEY=value ANOTHER_KEY=another_value
modal secret list
modal secret delete my-secret
```

#### 3. Programmatically

```python
# From dictionary
secret = modal.Secret.from_dict({
    "API_KEY": "sk-...",
    "DB_PASSWORD": "secret123",
})

# From .env file
secret = modal.Secret.from_dotenv(".env")
```

### Using Secrets in Code

```python
@app.function(
    secrets=[
        modal.Secret.from_name("openai-secret"),
        modal.Secret.from_name("aws-credentials"),
    ]
)
def my_function():
    import os
    api_key = os.environ["OPENAI_API_KEY"]
    aws_key = os.environ["AWS_ACCESS_KEY_ID"]
    return "Secrets loaded"
```

### Best Practices
- Secrets are injected as environment variables
- Multiple secrets can be injected (later ones override earlier)
- Never commit secrets to version control
- Use Modal secrets for all credentials

---

## Volumes & Storage

Volumes provide persistent, high-performance distributed file storage.

### Creating Volumes

```bash
# CLI
modal volume create my-volume
modal volume list
```

```python
# Programmatic
vol = modal.Volume.from_name("my-volume", create_if_missing=True)
```

### Using Volumes

```python
volume = modal.Volume.from_name("my-models", create_if_missing=True)

@app.function(
    volumes={"/models": volume}
)
def save_model(model_data):
    # Write to volume
    with open("/models/model.bin", "wb") as f:
        f.write(model_data)

    # Commit changes
    volume.commit()

    return "Model saved"

@app.function(
    volumes={"/models": volume}
)
def load_model():
    # Reload to see latest changes
    volume.reload()

    with open("/models/model.bin", "rb") as f:
        model_data = f.read()

    return model_data
```

### Volume Versions

**V1 Volumes (Default):**
- Best for <50,000 files
- 500,000 file limit
- Mature and stable

**V2 Volumes (Beta):**
- No file count limit
- Better concurrent writes
- Files must be <1 TiB
- Max 32,768 files per directory

```python
# Create V2 volume
vol = modal.Volume.from_name("my-v2-volume", version=2, create_if_missing=True)
```

### Best Practices
- **Write-once, read-many** workloads
- Avoid concurrent modifications to same files
- Explicitly call `.commit()` after writes
- Call `.reload()` before reads to see latest changes
- Close files before reloading
- Use for model weights, checkpoints, logs

---

## Web Endpoints

### FastAPI Endpoints

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

web_app = FastAPI()

@web_app.get("/")
def root():
    return {"message": "Hello from Modal!"}

@web_app.post("/predict")
def predict(data: dict):
    result = model.predict(data)
    return {"prediction": result}

# Serve FastAPI app
@app.function(image=image)
@modal.asgi_app()
def fastapi_app():
    return web_app
```

### Simple Function Endpoints

```python
@app.function()
@modal.fastapi_endpoint(method="POST")
def square(x: int):
    """Accessible via POST request"""
    return {"square": x**2}

@app.function()
@modal.fastapi_endpoint(method="GET")
async def get_data(user_id: str):
    """Query params: ?user_id=123"""
    return {"user_id": user_id, "data": "..."}
```

### WSGI Apps (Flask, Django)

```python
from flask import Flask

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Hello from Flask on Modal!"

@app.function()
@modal.wsgi_app()
def flask_endpoint():
    return flask_app
```

### Custom Web Servers

```python
@app.function()
@modal.web_server(port=8080)
def custom_server():
    # Start custom HTTP server on port 8080
    import http.server
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("", 8080), handler)
    httpd.serve_forever()
```

### Authentication

```python
from modal.web_endpoint import web_endpoint

@app.function()
@modal.fastapi_endpoint()
def authenticated_endpoint(
    request: fastapi.Request,
):
    # Use Modal's built-in auth token
    token = request.headers.get("Authorization")
    # Validate token...
    return {"authenticated": True}
```

### Deployment

```bash
# Development with hot reload
modal serve script.py

# Production deployment
modal deploy script.py
```

---

## Scheduling

### Periodic Schedules

```python
# Every 5 hours
@app.function(schedule=modal.Period(hours=5))
def hourly_job():
    print("Running every 5 hours")

# Every day
@app.function(schedule=modal.Period(days=1))
def daily_job():
    print("Running daily")

# Every 30 minutes
@app.function(schedule=modal.Period(minutes=30))
def frequent_job():
    print("Running every 30 minutes")
```

### Cron Schedules

```python
# Every Monday at 8am UTC
@app.function(schedule=modal.Cron("0 8 * * 1"))
def monday_report():
    print("Weekly report")

# Every day at midnight
@app.function(schedule=modal.Cron("0 0 * * *"))
def nightly_cleanup():
    print("Daily cleanup")

# Every 15 minutes
@app.function(schedule=modal.Cron("*/15 * * * *"))
def frequent_check():
    print("Frequent check")
```

### Cron Syntax
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday=0)
│ │ │ │ │
* * * * *
```

### Deployment

```bash
# Deploy scheduled function
modal deploy script.py

# Named deployment
modal deploy --name my-scheduled-job script.py
```

### Best Practices
- Use `modal.Cron` for consistent scheduling across redeployments
- `modal.Period` resets on each deployment
- Monitor scheduled runs in Modal dashboard
- Scheduled functions can also be triggered manually
- Schedules cannot be paused (only deleted)

---

## Best Practices

### General
- **Code-first approach**: Define everything in Python, no YAML
- **Pin versions**: Always specify exact package versions
- **Use `uv`**: Faster than pip for Python package installation
- **Explicit is better**: Be explicit with GPU types, versions, configurations

### Performance
- **Optimize images**: Place stable layers first, changing layers last
- **Cache effectively**: Leverage Modal's automatic caching
- **GPU selection**: L40S for best cost/performance, understand your bottleneck
- **Batch processing**: Use `@modal.batched()` for dynamic batching
- **Concurrent inputs**: Use `@modal.concurrent()` for parallel processing

### Data Management
- **Volumes for persistence**: Use Volumes for model weights, checkpoints
- **Write-once, read-many**: Volumes optimized for this pattern
- **Commit explicitly**: Call `.commit()` after writes, `.reload()` before reads
- **Choose volume version**: V1 for <50k files, V2 for larger datasets

### Security
- **Use Modal Secrets**: Never hardcode credentials
- **Environment variables**: Access secrets via `os.environ`
- **Least privilege**: Only inject needed secrets
- **Validate inputs**: Always validate user inputs in web endpoints

### Development Workflow
```bash
modal run script.py      # Local testing
modal serve script.py    # Development with hot reload
modal deploy script.py   # Production deployment
```

### Debugging
- Use `print()` statements (they appear in logs)
- Check Modal dashboard for function logs
- Use `modal.debug()` for interactive debugging
- Test locally before deploying

---

## Common Patterns

### 1. ML Model Serving

```python
import modal

app = modal.App("ml-model-server")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("torch==2.1.0", "transformers==4.35.0")
)

volume = modal.Volume.from_name("model-cache", create_if_missing=True)

@app.cls(
    gpu="L40S",
    image=image,
    volumes={"/cache": volume},
    secrets=[modal.Secret.from_name("huggingface")],
)
class ModelServer:
    @modal.enter()
    def load_model(self):
        """Load model once on container startup"""
        from transformers import AutoModel
        self.model = AutoModel.from_pretrained(
            "bert-base-uncased",
            cache_dir="/cache",
        )

    @modal.method()
    def predict(self, text: str):
        """Inference method"""
        return self.model(text)

@app.function()
@modal.fastapi_endpoint(method="POST")
def predict_endpoint(text: str):
    """HTTP endpoint for predictions"""
    server = ModelServer()
    result = server.predict.remote(text)
    return {"prediction": result}
```

### 2. Scheduled Data Pipeline

```python
import modal

app = modal.App("data-pipeline")

volume = modal.Volume.from_name("data-volume", create_if_missing=True)

@app.function(
    schedule=modal.Cron("0 2 * * *"),  # 2am daily
    volumes={"/data": volume},
    secrets=[modal.Secret.from_name("database-creds")],
)
def daily_etl():
    """Extract, Transform, Load pipeline"""
    import os

    # Extract
    data = extract_from_database(os.environ["DB_URL"])

    # Transform
    processed = transform_data(data)

    # Load
    with open("/data/processed.parquet", "wb") as f:
        f.write(processed)

    volume.commit()

    return f"Processed {len(processed)} records"
```

### 3. Batch Processing with GPU

```python
import modal

app = modal.App("batch-processor")

image = modal.Image.debian_slim().uv_pip_install("torch", "numpy")

@app.function(
    gpu="A100",
    image=image,
    timeout=3600,  # 1 hour
)
def process_batch(items: list):
    """Process large batch on GPU"""
    import torch

    # Convert to tensors
    tensors = torch.tensor(items, device="cuda")

    # Process on GPU
    results = expensive_computation(tensors)

    return results.cpu().numpy().tolist()

@app.local_entrypoint()
def main():
    # Load 10k items
    items = load_large_dataset()

    # Process in chunks of 1000
    chunk_size = 1000
    results = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i+chunk_size]
        result = process_batch.remote(chunk)
        results.extend(result)

    print(f"Processed {len(results)} items")
```

### 4. Distributed Map-Reduce

```python
import modal

app = modal.App("map-reduce")

@app.function()
def map_task(chunk: list):
    """Map: Process individual chunk"""
    return sum(x * x for x in chunk)

@app.function()
def reduce_task(results: list):
    """Reduce: Aggregate results"""
    return sum(results)

@app.local_entrypoint()
def main():
    # Split data into chunks
    data = list(range(1000000))
    chunk_size = 10000
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

    # Map phase: process chunks in parallel
    map_results = list(map_task.map(chunks))

    # Reduce phase: aggregate results
    final_result = reduce_task.remote(map_results)

    print(f"Result: {final_result}")
```

### 5. Multi-GPU Training

```python
import modal

app = modal.App("multi-gpu-training")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install("torch==2.1.0", "torchvision")
)

volume = modal.Volume.from_name("training-checkpoints", create_if_missing=True)

@app.function(
    gpu="H100:8",
    image=image,
    volumes={"/checkpoints": volume},
    timeout=86400,  # 24 hours
)
def train_model(config: dict):
    """Multi-GPU training"""
    import torch
    import torch.distributed as dist

    # Initialize distributed training
    dist.init_process_group(backend="nccl")

    # Create model and wrap with DDP
    model = create_model(config)
    model = torch.nn.parallel.DistributedDataParallel(model)

    # Training loop
    for epoch in range(config["epochs"]):
        train_one_epoch(model, epoch)

        # Save checkpoint
        if epoch % 10 == 0:
            torch.save(model.state_dict(), f"/checkpoints/epoch_{epoch}.pt")
            volume.commit()

    return "Training complete"
```

### 6. API with Rate Limiting

```python
import modal
from fastapi import FastAPI, HTTPException
from collections import defaultdict
import time

app = modal.App("rate-limited-api")
web_app = FastAPI()

# Simple in-memory rate limiter (use Redis in production)
request_counts = defaultdict(list)

def rate_limit(client_id: str, max_requests: int = 100, window: int = 60):
    """Allow max_requests per window seconds"""
    now = time.time()

    # Clean old requests
    request_counts[client_id] = [
        ts for ts in request_counts[client_id]
        if now - ts < window
    ]

    if len(request_counts[client_id]) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    request_counts[client_id].append(now)

@web_app.post("/api/process")
def process(client_id: str, data: dict):
    rate_limit(client_id, max_requests=100, window=60)

    # Process request
    result = expensive_operation(data)
    return {"result": result}

@app.function()
@modal.asgi_app()
def api():
    return web_app
```

---

## Quick Reference

### Function Configuration

```python
@app.function(
    gpu="L40S",                          # GPU type
    cpu=4,                               # CPU cores
    memory=16384,                        # Memory in MB
    timeout=3600,                        # Timeout in seconds
    retries=3,                           # Retry failed executions
    secrets=[modal.Secret.from_name()],  # Inject secrets
    volumes={"/path": volume},           # Mount volumes
    image=image,                         # Container image
    schedule=modal.Cron("0 * * * *"),    # Schedule
    concurrency_limit=10,                # Max concurrent executions
)
def my_function():
    pass
```

### Common Commands

```bash
# Authentication
modal setup
modal token set --token-id xxx --token-secret yyy

# Running
modal run script.py
modal serve script.py              # Hot reload
modal deploy script.py

# Secrets
modal secret create name KEY=value
modal secret list
modal secret delete name

# Volumes
modal volume create name
modal volume list
modal volume delete name

# Apps
modal app list
modal app stop app-name

# Logs
modal app logs app-name
```

### Links & Resources

- **Examples Repository**: https://github.com/modal-labs/modal-examples
  - 01-14: Comprehensive learning tracks
  - Look here FIRST for patterns

- **Documentation**:
  - Guide: https://modal.com/docs/guide
  - API Reference: https://modal.com/docs/reference
  - Pricing: https://modal.com/pricing

- **Community**:
  - Slack: https://modal.com/slack
  - GitHub Issues: https://github.com/modal-labs/modal-client/issues

---

## Troubleshooting

### Common Issues

**Import errors in remote functions:**
```python
# ❌ Wrong - imports at top level not in image
import some_package

@app.function()
def my_func():
    return some_package.do_thing()

# ✅ Correct - add to image
image = modal.Image.debian_slim().uv_pip_install("some-package")

@app.function(image=image)
def my_func():
    import some_package
    return some_package.do_thing()
```

**Volume data not persisting:**
```python
# ❌ Wrong - no commit
@app.function(volumes={"/data": volume})
def save_data():
    with open("/data/file.txt", "w") as f:
        f.write("data")

# ✅ Correct - explicit commit
@app.function(volumes={"/data": volume})
def save_data():
    with open("/data/file.txt", "w") as f:
        f.write("data")
    volume.commit()
```

**Secrets not available:**
```python
# ❌ Wrong - secret not injected
@app.function()
def use_secret():
    return os.environ["API_KEY"]  # KeyError!

# ✅ Correct - inject secret
@app.function(secrets=[modal.Secret.from_name("my-secret")])
def use_secret():
    return os.environ["API_KEY"]
```

---

**Last Updated**: 2025-10-14 (Added comprehensive LLM development guide)
**Modal Version**: Latest (as of documentation fetch)
**Key Additions**: Development workflow (serve/run/deploy), model caching, GPU strategies, cold start optimization, batching, monitoring
