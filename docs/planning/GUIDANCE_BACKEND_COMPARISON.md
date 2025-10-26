# Guidance Backend Comparison

**Date**: 2025-10-23
**Status**: Research Complete
**Related**: LLGUIDANCE_MIGRATION_PLAN.md

---

## Executive Summary

This document provides a comprehensive comparison of backend options for the Guidance library to inform our llguidance migration decision. We evaluated 5 backend options across setup complexity, performance, cost, and use case fit.

**Key Finding**: For our use case (constrained code generation with high reliability requirements), we recommend:
- **Development/Testing**: llama.cpp (CPU-friendly, fast iteration)
- **Production**: Modal + Transformers with quantization (balance of performance, cost, scalability)
- **Premium Alternative**: OpenAI/GPT-4 via Guidance API mode (highest quality, fastest, but expensive)

---

## Backend Options Overview

### 1. Transformers (HuggingFace)

**What it is**: PyTorch-based library providing access to thousands of pre-trained models with GPU acceleration.

**How to Configure with Guidance**:
```python
from guidance import models

# Basic setup
lm = models.Transformers("mistralai/Mistral-7B-Instruct-v0.2")

# Advanced setup with device control
lm = models.Transformers(
    "mistralai/Mistral-7B-Instruct-v0.2",
    device="cuda",           # or "cpu", "mps" for Mac
    device_map="auto",       # auto-distribute layers
)

# With quantization (reduces memory, improves speed)
lm = models.Transformers(
    "mistralai/Mistral-7B-Instruct-v0.2",
    device_map="auto",
    load_in_4bit=True,       # 4-bit quantization
)
```

**Required Dependencies**:
```bash
uv add guidance transformers torch accelerate
# For GPU: install CUDA toolkit separately
# For quantization: uv add bitsandbytes
```

**Model Selection**:
- **Recommended**: Mistral-7B-Instruct-v0.2 (best balance)
- **Premium**: Mistral-22B, Llama-3.1-70B (higher quality)
- **Budget**: Phi-3-mini (3.8B params, fast but lower quality)
- **Avoid**: Mistral-7B has known issues with complex Guidance prompts (see GitHub issue #454)

**Performance Characteristics**:
- **Latency**: 20-30s per generation (7B model, GPU)
- **Throughput**: ~2-3 tokens/second (depends on GPU)
- **Startup**: 30-60s (model loading time)
- **Quality**: High (comparable to OpenAI for many tasks)

**GPU Requirements**:
- **Minimum**: 16GB VRAM for 7B models (full precision)
- **Recommended**: 24GB VRAM (A10G, RTX 3090, RTX 4090)
- **With Quantization**: 8-12GB VRAM (4-bit quantization)
- **CPU-only**: Possible but 10-20x slower

**Memory Usage Examples**:
- Mistral-7B (FP16): ~14GB VRAM
- Mistral-7B (4-bit): ~4-6GB VRAM
- Llama-70B (4-bit): ~32GB VRAM (requires multi-GPU or system RAM offload)

**Cost**:
- **Free** (if you have GPU hardware)
- **Modal/Cloud GPU**: ~$0.50/hour (L40S, 48GB VRAM)
- **One-time hardware**: $1,000-$5,000 (consumer GPU)

**Pros**:
- ✅ Full control over model and generation
- ✅ Works offline (no API dependency)
- ✅ Best Guidance integration (KV cache optimization works)
- ✅ Huge model selection (Mistral, Llama, Phi, Qwen, etc.)
- ✅ Quantization support (reduce memory/cost)

**Cons**:
- ❌ Requires GPU for acceptable speed
- ❌ High memory usage (without quantization)
- ❌ Long startup time (model loading)
- ❌ Scaling requires managing multiple GPUs
- ❌ Some models have compatibility issues (Mistral-7B base)

**Best Use Case**:
- Production workloads with consistent GPU availability
- High-volume batch processing
- When offline/on-prem deployment required
- When fine-tuning or model customization needed

---

### 2. llama.cpp

**What it is**: C++ inference engine optimized for CPU execution with GGUF quantized models. Highly efficient and portable.

**How to Configure with Guidance**:
```python
# Option A: Via llama-cpp-guidance wrapper
from pathlib import Path
from llama_cpp_guidance.llm import LlamaCpp
import guidance

guidance.llm = LlamaCpp(
    model_path=Path("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
    n_gpu_layers=0,      # 0 = CPU only, 32 = offload 32 layers to GPU
    n_threads=8,         # CPU threads
    n_ctx=4096,          # Context window
)

program = guidance(
    "Generate TypeScript: {{~gen 'code' temperature=0.3 max_tokens=2000}}"
)
output = program()

# Option B: Via Guidance native support (if available)
from guidance import models

lm = models.LlamaCpp(
    "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    n_gpu_layers=0,
    n_threads=8,
)
```

**Required Dependencies**:
```bash
uv add guidance llama-cpp-python
# Or use compatibility wrapper:
uv add guidance llama-cpp-guidance
```

**Model Selection** (GGUF format required):
- **Download from**: https://huggingface.co/TheBloke (community GGUF conversions)
- **Recommended**: Mistral-7B-Instruct-v0.2-GGUF (Q4_K_M or Q5_K_M quantization)
- **Formats**:
  - `Q4_K_M`: 4-bit, medium quality, ~4GB (best balance)
  - `Q5_K_M`: 5-bit, higher quality, ~5GB
  - `Q8_0`: 8-bit, nearly lossless, ~8GB
  - `F16`: Full precision, ~14GB (defeats purpose of llama.cpp)

**Performance Characteristics**:
- **Latency**: 10-15s per generation (CPU, Q4_K_M)
- **Throughput**: ~5-10 tokens/second (16-core CPU)
- **Startup**: <5s (much faster than Transformers)
- **Quality**: Comparable to Transformers (same model, quantization trade-off minimal)

**GPU Requirements**:
- **GPU Optional**: Works great on CPU alone
- **With GPU offload**: Can offload layers to GPU (hybrid CPU+GPU)
- **Example**: `n_gpu_layers=32` offloads 32 layers, keeps rest on CPU
- **Memory**: ~8GB system RAM for 7B Q4_K_M model

**Quantization Levels** (memory vs quality trade-off):
| Quantization | Memory (7B) | Memory (70B) | Quality Loss | Speed |
|--------------|-------------|--------------|--------------|-------|
| Q2_K         | ~3GB        | ~20GB        | Noticeable   | Fastest |
| Q4_K_M       | ~4GB        | ~32GB        | Minimal      | Fast |
| Q5_K_M       | ~5GB        | ~40GB        | Very minimal | Medium |
| Q8_0         | ~8GB        | ~64GB        | Nearly none  | Slower |

**Cost**:
- **Free** (runs on any modern CPU)
- **No GPU required** (but optional for speed boost)
- **Low electricity** (~50W CPU vs 300W GPU)

**Pros**:
- ✅ CPU-friendly (no GPU required)
- ✅ Very fast startup (<5s)
- ✅ Low memory usage (quantized models)
- ✅ Cross-platform (Mac, Linux, Windows, even mobile)
- ✅ Efficient for edge/local deployment
- ✅ Hybrid CPU+GPU support (offload layers)

**Cons**:
- ❌ Requires GGUF format (extra conversion step)
- ❌ Slightly slower than GPU Transformers
- ❌ Limited to llama/mistral-style architectures
- ❌ Guidance integration via wrapper (may lag behind)
- ❌ Less flexible than Transformers (fewer model options)

**Best Use Case**:
- Development and testing (fast iteration, no GPU needed)
- Edge deployment (mobile, embedded, IoT)
- Cost-sensitive production (CPU instances cheaper)
- On-prem deployment with limited GPU access

---

### 3. OpenAI (GPT-3.5, GPT-4)

**What it is**: Cloud API for OpenAI's proprietary models. Guidance can use OpenAI in "API mode" (no constrained generation) or with newer structured output support.

**How to Configure with Guidance**:
```python
from guidance import models
import os

# Set API key
os.environ["OPENAI_API_KEY"] = "sk-..."

# GPT-4 Turbo (recommended for quality)
lm = models.OpenAI("gpt-4-turbo")

# GPT-3.5 Turbo (faster, cheaper)
lm = models.OpenAI("gpt-3.5-turbo")

# With custom parameters
lm = models.OpenAI(
    "gpt-4-turbo",
    temperature=0.3,
    max_tokens=2000,
)

# Use with Guidance
from guidance import gen

lm += "Generate TypeScript function to add two numbers:\n"
lm += gen("code", max_tokens=500)
```

**Required Dependencies**:
```bash
uv add guidance openai
export OPENAI_API_KEY="sk-..."
```

**Model Selection**:
- **GPT-4 Turbo**: $10/1M input tokens, $30/1M output tokens
  - Best quality, fastest, most reliable
  - **Recommended for production**
- **GPT-3.5 Turbo**: $0.50-$2/1M tokens
  - Good quality, very fast, cheapest
  - Good for high-volume/testing
- **GPT-4**: $30/1M input, $60/1M output (legacy, slower)

**Performance Characteristics**:
- **Latency**: 5-10s per generation (GPT-4 Turbo)
- **Throughput**: ~20-50 tokens/second (streaming)
- **Startup**: <1s (no model loading)
- **Quality**: **Highest** (proprietary models, extensive fine-tuning)

**GPU Requirements**:
- **None** (API-based, OpenAI manages infrastructure)

**Cost** (per 1,000 tokens):
- **GPT-4 Turbo**: $0.01 input, $0.03 output
- **GPT-3.5 Turbo**: $0.0005-$0.002 (depending on version)
- **Example**: Generating 500-token TypeScript function with 200-token prompt:
  - GPT-4 Turbo: $0.002 + $0.015 = **$0.017** per generation
  - GPT-3.5 Turbo: $0.0001 + $0.001 = **$0.0011** per generation

**Cost Comparison (21 test suite)**:
- GPT-4 Turbo: 21 tests × $0.017 = **$0.36 per suite run**
- GPT-3.5 Turbo: 21 tests × $0.0011 = **$0.023 per suite run**
- **vs Modal L40S**: ~$0.08-$0.25 per suite (depending on success rate)

**Pros**:
- ✅ **Highest quality** output (best-in-class models)
- ✅ **Fastest latency** (5-10s, no cold start)
- ✅ **Zero infrastructure** (no GPUs, no deployment)
- ✅ **Instant scaling** (OpenAI handles traffic spikes)
- ✅ **Always up-to-date** (automatic model improvements)
- ✅ Structured output support (JSON schema via API)

**Cons**:
- ❌ **Expensive at scale** (cost per token adds up)
- ❌ **No offline mode** (requires internet, API availability)
- ❌ **Limited Guidance integration** (no KV cache optimization)
- ❌ **Vendor lock-in** (proprietary models)
- ❌ **Data privacy concerns** (prompts sent to OpenAI)
- ❌ **Rate limits** (tier-based, can block high-volume use)

**Guidance Integration Notes**:
- **Standard mode**: Guidance works but treats OpenAI as "dumb" API (no constrained generation speedup)
- **Structured output**: OpenAI now supports JSON schema directly (may bypass Guidance benefits)
- **Performance**: For endpoints that don't support guidance directly, chaining lots of calls has same performance cost as any library

**Best Use Case**:
- Prototyping and MVP development (fastest time-to-value)
- Low-volume production (<1,000 generations/day)
- When quality is critical and cost is secondary
- Teams without ML/GPU infrastructure

---

### 4. Anthropic Claude (via API)

**What it is**: Anthropic's Claude models via API. Similar to OpenAI but with different strengths (longer context, better reasoning).

**How to Configure with Guidance**:
```python
# NOTE: Guidance does not have native Claude support as of 2025-10-23
# Would require custom integration or using Claude's structured output features

# Hypothetical integration (if wrapper existed):
from guidance import models
import os

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

lm = models.Anthropic("claude-3-5-sonnet-20250129")

# Alternative: Use Claude's native API (bypass Guidance)
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-3-5-sonnet-20250129",
    max_tokens=2000,
    messages=[{
        "role": "user",
        "content": "Generate TypeScript function..."
    }]
)
```

**Required Dependencies**:
```bash
uv add anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Model Selection**:
- **Claude 3.5 Sonnet**: Balanced quality/speed (recommended)
- **Claude 3 Opus**: Highest quality (expensive, slower)
- **Claude 3 Haiku**: Fastest, cheapest (lower quality)

**Performance Characteristics**:
- **Latency**: 5-15s per generation (Claude 3.5 Sonnet)
- **Throughput**: ~20-40 tokens/second
- **Startup**: <1s (API-based)
- **Quality**: Very high (competitive with GPT-4)

**GPU Requirements**:
- **None** (API-based)

**Cost**:
- **Pricing not publicly detailed in search results** (check Anthropic website)
- Expected to be comparable to OpenAI GPT-4 range

**Pros**:
- ✅ Very high quality (competitive with GPT-4)
- ✅ Longer context windows (200K tokens)
- ✅ Strong reasoning and code generation
- ✅ Zero infrastructure
- ✅ Good API ergonomics

**Cons**:
- ❌ **No native Guidance integration** (as of 2025-10-23)
- ❌ Would require custom wrapper or bypass Guidance entirely
- ❌ Expensive (similar to GPT-4)
- ❌ API-only (no offline mode)
- ❌ Vendor lock-in

**Best Use Case**:
- **Not recommended for this project** (no Guidance integration)
- Consider if building custom provider (bypassing Guidance)
- Alternative to OpenAI if prefer Anthropic models

---

### 5. vLLM

**What it is**: High-throughput inference engine optimized for serving LLMs at scale. Supports Guidance via recent integration.

**How to Configure with Guidance**:
```python
# vLLM with Guidance integration (via server)

# Step 1: Start vLLM server with Guidance backend
# bash:
# vllm serve mistralai/Mistral-7B-Instruct-v0.2 \
#   --structured-outputs-config.backend=guidance \
#   --port 8000

# Step 2: Use OpenAI-compatible API from Python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # vLLM doesn't require key
)

response = client.chat.completions.create(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    messages=[{"role": "user", "content": "Generate TypeScript..."}],
    extra_body={
        "guided_json": {
            # JSON schema for structured output
            "type": "object",
            "properties": {
                "implementation": {
                    "type": "object",
                    "properties": {
                        "body_statements": {"type": "array"},
                        "function_signature": {"type": "object"}
                    }
                }
            }
        }
    }
)

# Alternative: Direct Guidance integration (if supported)
from guidance import models

# Connect to vLLM backend
lm = models.VLLM("http://localhost:8000", model_name="mistralai/Mistral-7B-Instruct-v0.2")
```

**Required Dependencies**:
```bash
# Server side:
uv add vllm

# Client side:
uv add openai  # Use OpenAI-compatible client
# or
uv add guidance  # If direct integration available
```

**Model Selection**:
- Any HuggingFace model supported by vLLM
- **Recommended**: Mistral-7B-Instruct-v0.2, Llama-3.1-8B
- **Note**: vLLM focuses on popular architectures (Llama, Mistral, Qwen)

**Performance Characteristics**:
- **Latency**: 10-20s per generation (depends on GPU)
- **Throughput**: **Up to 24x higher than Transformers** (with batching)
- **Startup**: 30-60s (model loading, similar to Transformers)
- **Quality**: Same as base model (no quality trade-off)
- **Scaling**: Excellent (designed for high-concurrency serving)

**Guidance Integration Status** (as of 2025-10-23):
- ✅ **Available in vLLM 0.8.5+**
- ✅ Supports Guidance as structured output backend
- ✅ Faster TTFT (time-to-first-token) than XGrammar for large schemas
- ⚠️ Integration is recent (potential bugs/limitations)
- ⚠️ GitHub issue #313 shows mixed results (text gen works, selection mode issues)

**GPU Requirements**:
- **Same as Transformers**: 16-24GB VRAM for 7B models
- **But**: Better GPU utilization (batching, paging)
- **Multi-GPU**: Excellent support (tensor parallelism)

**Cost**:
- **Free** (open source)
- **Infrastructure**: GPU costs same as Transformers
- **Advantage**: Better throughput = lower cost per generation at scale

**Pros**:
- ✅ **Highest throughput** (up to 24x vs Transformers)
- ✅ **Excellent scalability** (built for serving)
- ✅ Guidance integration available (structured outputs)
- ✅ OpenAI-compatible API (easy integration)
- ✅ Efficient memory usage (PagedAttention)
- ✅ Great for high-concurrency workloads

**Cons**:
- ❌ **Guidance integration is new** (potential instability)
- ❌ Requires server deployment (more complex than direct library)
- ❌ Overkill for low-volume use cases
- ❌ Still needs GPU (no CPU-only mode)
- ❌ GitHub issues show partial Guidance support (text gen works, selection mode doesn't)

**Best Use Case**:
- High-volume production (>100 req/sec)
- When serving multiple users concurrently
- When throughput is critical (batch processing)
- Teams with DevOps resources for deployment

**Not Recommended For**:
- This project (at least initially) due to:
  - Low-medium volume (21 tests, occasional generations)
  - Guidance integration is new/unproven
  - Added deployment complexity
  - Overkill for our scale

---

## Comparison Table

| Feature | Transformers | llama.cpp | OpenAI | Anthropic | vLLM |
|---------|--------------|-----------|--------|-----------|------|
| **Setup Complexity** | Medium | Low | Low | Low | High |
| **Latency (P50)** | 20-30s | 10-15s | 5-10s | 5-15s | 10-20s |
| **Throughput** | Low | Medium | High | High | Very High |
| **GPU Required** | Yes | No | No | No | Yes |
| **Cost (per 1K gen)** | $0.08 | Free | $0.36 | ~$0.40 | $0.08 |
| **Guidance Integration** | ✅ Excellent | ✅ Good (via wrapper) | ⚠️ Limited | ❌ None | ⚠️ New (0.8.5+) |
| **Quality** | High | High | Highest | Highest | High |
| **Offline Mode** | ✅ Yes | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Scalability** | Medium | Low | Excellent | Excellent | Excellent |
| **Best For** | Production GPU | Dev/Testing | MVP/Premium | N/A for us | High-volume prod |

**Setup Complexity Legend**:
- **Low**: Install library, run code (<30 min)
- **Medium**: Install library, configure GPU/models, test (1-2 hours)
- **High**: Deploy server, configure infrastructure, test (4-8 hours)

**Cost Basis**: Running 21-test suite, Modal L40S pricing ($0.50/hour), OpenAI API pricing, avg 500 tokens output

---

## Code Examples by Backend

### Example 1: Transformers (Recommended for Production)

```python
"""
Full example: Using Transformers backend with Guidance
"""
import asyncio
from guidance import models, gen
from pydantic import BaseModel, Field

class TypeScriptImplementation(BaseModel):
    body_statements: list[dict]
    function_signature: dict
    imports: list[dict] = Field(default_factory=list)

async def generate_typescript_with_transformers():
    # Initialize model (one-time setup)
    lm = models.Transformers(
        "mistralai/Mistral-7B-Instruct-v0.2",
        device="cuda",           # or "cpu" for CPU-only
        device_map="auto",       # auto-distribute across GPUs
        load_in_4bit=True,       # 4-bit quantization (reduces memory)
    )

    # Generate with schema constraint
    lm += "Generate a TypeScript function that adds two numbers:\n"
    lm += gen("code", max_tokens=500, temperature=0.3)

    # Extract result
    result = lm["code"]
    return result

# Run
if __name__ == "__main__":
    result = asyncio.run(generate_typescript_with_transformers())
    print(result)
```

**Installation**:
```bash
uv add guidance transformers torch accelerate bitsandbytes
# Ensure CUDA installed for GPU support
```

**Expected Performance**:
- First call: ~60s (model loading)
- Subsequent calls: ~20-30s per generation
- Memory: ~6GB VRAM (with 4-bit quantization)

---

### Example 2: llama.cpp (Recommended for Development)

```python
"""
Full example: Using llama.cpp backend with Guidance
"""
from pathlib import Path
from llama_cpp_guidance.llm import LlamaCpp
import guidance

# Step 1: Download GGUF model
# From: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF
# Save to: models/mistral-7b-instruct-v0.2.Q4_K_M.gguf

# Step 2: Initialize Guidance with llama.cpp
guidance.llm = LlamaCpp(
    model_path=Path("models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"),
    n_gpu_layers=0,          # 0 = CPU only, 32 = offload to GPU
    n_threads=8,             # Use 8 CPU threads
    n_ctx=4096,              # Context window
)

# Step 3: Use Guidance as normal
program = guidance('''
Generate a TypeScript function that adds two numbers.

Requirements:
- Use TypeScript syntax
- Include type annotations
- Return the sum

{{~gen 'code' temperature=0.3 max_tokens=500}}
''')

result = program()
print(result["code"])
```

**Installation**:
```bash
uv add guidance llama-cpp-guidance

# Download model
mkdir -p models
cd models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf
```

**Expected Performance**:
- First call: ~5s (fast model loading)
- Subsequent calls: ~10-15s per generation (CPU)
- Memory: ~8GB RAM (system RAM, not VRAM)

---

### Example 3: OpenAI (Recommended for MVP)

```python
"""
Full example: Using OpenAI backend with Guidance
"""
import os
from guidance import models, gen

# Set API key
os.environ["OPENAI_API_KEY"] = "sk-..."

# Initialize model
lm = models.OpenAI("gpt-4-turbo", temperature=0.3)

# Generate code
lm += "Generate a TypeScript function that adds two numbers:\n"
lm += gen("code", max_tokens=500)

# Extract result
result = lm["code"]
print(result)
```

**Installation**:
```bash
uv add guidance openai
export OPENAI_API_KEY="sk-..."
```

**Expected Performance**:
- First call: ~5-10s
- Subsequent calls: ~5-10s (consistent, no cold start)
- Cost: ~$0.017 per generation (GPT-4 Turbo)

---

### Example 4: vLLM (For High-Volume Production)

```bash
# Step 1: Start vLLM server (one-time setup)
vllm serve mistralai/Mistral-7B-Instruct-v0.2 \
    --structured-outputs-config.backend=guidance \
    --gpu-memory-utilization=0.9 \
    --port 8000
```

```python
"""
Step 2: Use OpenAI-compatible client to call vLLM
"""
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # vLLM doesn't require real key
)

response = client.chat.completions.create(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    messages=[{
        "role": "user",
        "content": "Generate a TypeScript function that adds two numbers"
    }],
    temperature=0.3,
    max_tokens=500,
    extra_body={
        "guided_json": {
            # Structured output schema
            "type": "object",
            "properties": {
                "implementation": {
                    "type": "object",
                    "properties": {
                        "body_statements": {"type": "array"},
                        "function_signature": {"type": "object"}
                    }
                }
            },
            "required": ["implementation"]
        }
    }
)

print(response.choices[0].message.content)
```

**Installation**:
```bash
# Server:
uv add vllm

# Client:
uv add openai
```

**Expected Performance**:
- First call: ~20s (with warm server)
- Concurrent requests: Up to 24x throughput vs single Transformers instance
- Cost: Same GPU costs, but better utilization

---

## Recommendations

### For Development/Testing (Recommended: llama.cpp)

**Why**:
- ✅ No GPU required (runs on laptop CPU)
- ✅ Fast iteration (5s startup, 10-15s per gen)
- ✅ Zero cost (free, no API fees)
- ✅ Offline-friendly (no internet required)
- ✅ Easy setup (download model, run)

**Setup**:
```bash
# 1. Install
uv add guidance llama-cpp-guidance

# 2. Download model (one-time)
mkdir -p models
wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf -O models/mistral-7b.gguf

# 3. Use in code (see Example 2)
```

**Estimated Timeline**: 30 minutes to working code

---

### For Production (Recommended: Modal + Transformers)

**Why**:
- ✅ Best Guidance integration (KV cache optimization works)
- ✅ Proven reliability (mature stack)
- ✅ Scalable (Modal handles GPU allocation)
- ✅ Cost-effective at our scale (~$0.08 per test suite)
- ✅ Quantization support (reduce costs further)

**Architecture**:
```
┌─────────────────┐
│ GuidanceProvider│
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Modal Function  │
│ + Transformers  │
│ + Guidance      │
│ + 4-bit quant   │
└─────────────────┘
```

**Setup** (see LLGUIDANCE_MIGRATION_PLAN.md Phase 5):
```python
# modal_guidance_app.py
import modal

app = modal.App("lift-sys-guidance")

guidance_image = (
    modal.Image.debian_slim()
    .pip_install("guidance", "transformers", "torch", "accelerate", "bitsandbytes")
)

@app.function(
    image=guidance_image,
    gpu="L40S",              # 48GB VRAM, $0.50/hour
    secrets=[modal.Secret.from_name("supabase")],
    timeout=300,
)
async def generate_with_guidance(prompt: str, schema: dict) -> dict:
    from guidance import models, gen

    # Load model (cached after first call)
    lm = models.Transformers(
        "mistralai/Mistral-7B-Instruct-v0.2",
        load_in_4bit=True,   # Reduce memory + cost
    )

    lm += prompt
    lm += gen("output", max_tokens=2000, temperature=0.3)

    return {"result": lm["output"]}
```

**Cost Estimate**:
- L40S GPU: $0.50/hour
- Per generation: ~30s = $0.0042
- 21-test suite: 21 × 30s = 10.5 min = $0.087
- **vs current XGrammar**: ~$0.25 (due to 95% failure rate wasting compute)

**Estimated Timeline**: 2-3 days (including testing)

---

### Premium Alternative (OpenAI GPT-4 Turbo)

**When to Use**:
- Need highest quality output
- Willing to pay for convenience
- Want fastest time-to-market (no infrastructure)
- Volume is low (<1,000 generations/month)

**Cost Comparison** (monthly):
| Scenario | OpenAI Cost | Modal Cost | Break-even |
|----------|-------------|------------|------------|
| 100 gen/mo | $1.70 | $0.42 | - |
| 1,000 gen/mo | $17.00 | $4.20 | - |
| 10,000 gen/mo | $170.00 | $42.00 | - |
| 100,000 gen/mo | $1,700.00 | $420.00 | OpenAI 4x more expensive |

**Recommendation**: Use for POC/MVP, migrate to Modal + Transformers for production scale.

---

## Migration Path

### Phase 1: POC (Days 1-2)
**Goal**: Validate Guidance works with our schemas

**Action**: Use **llama.cpp** for fastest iteration
- Download Mistral-7B GGUF model
- Test with TypeScript schema
- Measure success rate (target: >80%)

**Deliverable**: LLGUIDANCE_POC_RESULTS.md

---

### Phase 2: Production Setup (Days 3-7)
**Goal**: Deploy GuidanceProvider with Modal + Transformers

**Action**:
1. Create `GuidanceProvider` class
2. Deploy Modal function with Transformers + 4-bit quantization
3. Test with all 4 languages (TypeScript, Rust, Go, Java)
4. Measure success rate (target: >95%)

**Deliverable**: Production-ready GuidanceProvider

---

### Phase 3: Optimization (Days 8-10)
**Goal**: Optimize cost and latency

**Action**:
- Benchmark different quantization levels (4-bit vs 8-bit)
- Test alternative models (Mistral-22B, Llama-70B)
- Add response caching
- Monitor and tune

**Deliverable**: LLGUIDANCE_PERFORMANCE_REPORT.md

---

## Open Questions

### Q1: Should we support multiple backends?

**Recommendation**: Yes, but prioritize:
1. **llama.cpp** (development/testing)
2. **Modal + Transformers** (production)
3. **OpenAI** (optional fallback for quality comparison)

**Implementation**: Make backend configurable via environment variable:
```python
GUIDANCE_BACKEND=llama_cpp  # or "transformers", "openai"
```

---

### Q2: What quantization level should we use?

**Recommendation**: Start with **4-bit (Q4_K_M)**
- Minimal quality loss (~2-3%)
- 4x memory reduction
- 2-3x faster inference
- Proven in production (widely used)

**Test plan**: Compare outputs side-by-side with full-precision baseline

---

### Q3: Should we use vLLM?

**Recommendation**: **Not initially**
- Guidance integration is new (0.8.5+, potential instability)
- Overkill for our scale (21 tests, occasional generations)
- Added deployment complexity
- Can revisit if we hit scale issues (>100 req/sec)

---

## References

### Documentation
- **Guidance Library**: https://github.com/guidance-ai/guidance
- **llguidance (Rust core)**: https://github.com/guidance-ai/llguidance
- **llama.cpp**: https://github.com/ggml-org/llama.cpp
- **vLLM**: https://docs.vllm.ai/
- **vLLM Guidance Integration**: https://github.com/vllm-project/vllm/pull/14779

### Model Sources
- **Mistral Models**: https://huggingface.co/mistralai
- **GGUF Models (llama.cpp)**: https://huggingface.co/TheBloke
- **OpenAI Pricing**: https://openai.com/api/pricing/

### Benchmarks
- **llama.cpp vs Transformers**: https://github.com/ggml-org/llama.cpp/discussions/2240
- **vLLM Performance**: https://docs.vllm.ai/en/latest/features/structured_outputs.html
- **SGLang Benchmarks**: https://medium.com/@saidines12/sglang-vs-vllm-part-1-benchmark-performance-3231a41033ca

---

**Next Steps**:
1. Review this comparison with team
2. Decide on Phase 1 POC backend (recommend: llama.cpp)
3. Proceed with LLGUIDANCE_MIGRATION_PLAN.md Phase 1
4. Document POC results for production decision

---

**Document Status**: COMPLETE
**Owner**: Architecture Team
**Next Update**: After Phase 1 POC complete
