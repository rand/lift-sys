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
5. [Secrets Management](#secrets-management)
6. [Volumes & Storage](#volumes--storage)
7. [Web Endpoints](#web-endpoints)
8. [Scheduling](#scheduling)
9. [Best Practices](#best-practices)
10. [Common Patterns](#common-patterns)

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

**Last Updated**: 2025-10-14
**Modal Version**: Latest (as of documentation fetch)
