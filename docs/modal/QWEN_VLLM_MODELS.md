# Qwen vLLM Models on Modal

**Date**: 2025-10-23
**Status**: Experimental
**Branch**: `experiment/qwen-vllm-models`

## Overview

Testing two large Qwen models on Modal with vLLM for high-performance inference:

1. **Qwen3-Next-80B-A3B-Instruct-FP8** - General-purpose language model
2. **Qwen3-Coder-480B-A35B-Instruct-FP8** - Code-specialized model

Both models use:
- **vLLM 0.9.2** for efficient inference with PagedAttention
- **XGrammar** for JSON schema-constrained generation
- **FP8 quantization** for 2x memory reduction
- **H100 GPUs** with tensor parallelism as needed

## Model Specifications

### Qwen3-Next-80B-A3B-Instruct-FP8

**Model Details:**
- HuggingFace: `Qwen/Qwen3-Next-80B-A3B-Instruct-FP8`
- Total parameters: ~80B
- Active parameters: ~3B (MoE architecture)
- Quantization: FP8
- Memory requirement: ~40-50GB

**Infrastructure:**
- GPU: H100 80GB x1
- Tensor parallel: 1
- Cold start: ~8-10 minutes (first load)
- Warm inference: 2-5 seconds

**Use Cases:**
- General-purpose text generation
- Question answering
- Structured data extraction
- Analysis and summarization

### Qwen3-Coder-480B-A35B-Instruct-FP8

**Model Details:**
- HuggingFace: `Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8`
- Total parameters: ~480B
- Active parameters: ~35B (MoE architecture)
- Quantization: FP8
- Memory requirement: ~240GB (all experts loaded)

**Infrastructure:**
- GPU: H100 80GB x4 (tensor parallel)
- Total VRAM: 320GB (accommodates 240GB model + KV cache)
- Tensor parallel: 4
- Cold start: ~15-20 minutes (first load)
- Warm inference: 3-8 seconds

**Use Cases:**
- Code generation
- Algorithm implementation
- Code refactoring
- Intermediate representation (IR) generation
- Code analysis and optimization

## Quick Start

### 1. Deploy to Modal

```bash
# Deploy both models
modal deploy lift_sys/inference/modal_qwen_vllm.py

# Or develop with hot-reload
modal serve lift_sys/inference/modal_qwen_vllm.py
```

### 2. Test Models Locally

```bash
# Test 80B model
modal run lift_sys/inference/modal_qwen_vllm.py::test_80b

# Test 480B model
modal run lift_sys/inference/modal_qwen_vllm.py::test_480b
```

### 3. Run Comprehensive Tests

```bash
# Test suite for 80B model
uv run python scripts/modal/test_qwen_80b.py

# Test suite for 480B model
uv run python scripts/modal/test_qwen_480b.py
```

## API Endpoints

### Qwen3-Next-80B Endpoints

**Health Check:**
```bash
curl https://rand--qwen-80b-health.modal.run
```

**Generate (Text):**
```bash
curl -X POST https://rand--qwen-80b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing in simple terms.",
    "max_tokens": 512,
    "temperature": 0.7
  }'
```

**Generate (Structured with Schema):**
```bash
curl -X POST https://rand--qwen-80b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the capital of France?",
    "schema": {
      "type": "object",
      "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "number"}
      },
      "required": ["answer", "confidence"]
    },
    "max_tokens": 256
  }'
```

**Warmup (Pre-load Model):**
```bash
curl https://rand--qwen-80b-warmup.modal.run
```

### Qwen3-Coder-480B Endpoints

**Health Check:**
```bash
curl https://rand--qwen-480b-health.modal.run
```

**Generate (Code):**
```bash
curl -X POST https://rand--qwen-480b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function for binary search.",
    "max_tokens": 1024,
    "temperature": 0.3
  }'
```

**Generate (IR for lift-sys):**
```bash
curl -X POST https://rand--qwen-480b-generate.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a function to filter a CSV file",
    "schema": {
      "type": "object",
      "properties": {
        "intent": {"type": "object"},
        "signature": {"type": "object"},
        "effects": {"type": "array"}
      },
      "required": ["intent", "signature", "effects"]
    },
    "max_tokens": 1024
  }'
```

**Warmup:**
```bash
curl https://rand--qwen-480b-warmup.modal.run
```

## Python Client Usage

### Basic Generation (80B)

```python
from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

generator = Qwen80BGenerator()

# Simple generation
result = generator.generate.remote(
    prompt="What is machine learning?",
    max_tokens=512,
    temperature=0.7
)

print(result["text"])
```

### Structured Output with Schema (80B)

```python
from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

generator = Qwen80BGenerator()

schema = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
    },
    "required": ["summary", "sentiment", "confidence"]
}

result = generator.generate.remote(
    prompt="Analyze this text: AI will transform software development.",
    schema=schema,
    max_tokens=512
)

print(result["text"])  # Guaranteed to match schema
```

### Code Generation (480B)

```python
from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

generator = Qwen480BGenerator()

schema = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string"},
        "code": {"type": "string"},
        "complexity": {"type": "string"}
    },
    "required": ["function_name", "code", "complexity"]
}

result = generator.generate.remote(
    prompt="Implement quicksort in Python with complexity analysis.",
    schema=schema,
    max_tokens=1024,
    temperature=0.3
)

print(f"Function: {result['text']['function_name']}")
print(f"Code:\n{result['text']['code']}")
print(f"Complexity: {result['text']['complexity']}")
```

## Configuration

### vLLM Parameters

Both models use these default parameters (configurable):

```python
# Sampling parameters
max_tokens: int = 2048          # Maximum tokens to generate
temperature: float = 0.3        # Sampling temperature (0.0 = deterministic)
top_p: float = 0.95            # Nucleus sampling parameter

# Model loading
gpu_memory_utilization: float = 0.90  # 80B model
gpu_memory_utilization: float = 0.85  # 480B model
max_model_len: int = 8192       # Context length
```

### Environment Variables

Set via Modal secrets or environment:

```bash
# Enable eager execution (faster cold start, slower inference)
VLLM_EAGER=1  # Default: 0 (use torch.compile)
```

### Scaledown and Keep-Warm

**Current settings:**
```python
scaledown_window=600  # Keep warm for 10 minutes after last request
# keep_warm=1         # Optional: always keep 1 container ready (costs more)
```

**Cost considerations:**
- 80B model on H100: ~$4/hour
- 480B model on 4x H100: ~$16/hour
- Scaledown window avoids cold starts during testing
- Remove in production or adjust based on traffic

## Performance Metrics

### Expected Latency

**80B Model (H100 x1):**
- Cold start: 8-10 minutes (model download + load + compile)
- Warm start: 2-5 seconds
- Generation: 20-50 tokens/second

**480B Model (H100 x4):**
- Cold start: 15-20 minutes (large model + tensor parallel setup)
- Warm start: 3-8 seconds
- Generation: 15-40 tokens/second

### Optimization Tips

1. **Pre-warm models**: Call `/warmup` endpoint before critical workloads
2. **Cache models**: First run downloads to Modal volume, subsequent runs load from cache
3. **Batch requests**: Use `@modal.concurrent` for parallel processing
4. **Adjust scaledown**: Tune `scaledown_window` based on usage patterns
5. **Monitor costs**: H100 GPUs are expensive - stop dev deployments when not testing

## Cost Estimation

**GPU Costs (Modal pricing):**
- H100 80GB: ~$4.00/hour
- 4x H100 80GB: ~$16.00/hour

**Example scenarios:**

**Development/Testing:**
- 80B model, 2 hours testing: ~$8
- 480B model, 1 hour testing: ~$16
- Total daily testing budget: ~$50-100

**Production (light traffic):**
- 80B model, scaledown_window=300s: ~$4-8/hour (depending on traffic)
- 480B model: Use only for critical, high-value tasks

**Production (high traffic):**
- Consider `keep_warm=1` to eliminate cold starts
- 80B: ~$96/day (24 hours)
- 480B: ~$384/day (24 hours)

## Troubleshooting

### Model fails to load

**Error:** Out of memory (OOM)

**Solutions:**
1. Check GPU configuration (80B needs H100 x1, 480B needs H100 x4)
2. Reduce `gpu_memory_utilization` (try 0.80)
3. Reduce `max_model_len` (try 4096)

### Slow cold starts

**Expected:** First cold start is slow (model download + compilation)

**Optimizations:**
1. Models are cached in Modal volumes after first download
2. Torch compilation is cached after first run
3. Set `VLLM_EAGER=1` for faster cold start (slower inference)

### Schema constraint failures

**Error:** Generated JSON doesn't match schema

**Debugging:**
1. Check `raw_output` in error response
2. Simplify schema for testing
3. Increase `max_tokens` if output is truncated
4. Check vLLM/XGrammar compatibility with schema features

### High costs

**Solutions:**
1. Reduce `scaledown_window` (default: 600s)
2. Stop deployments when not testing: `modal app stop qwen-vllm-inference`
3. Use 80B model for most tasks, 480B only for complex code generation
4. Monitor usage in Modal dashboard

## Next Steps

### Testing Plan

1. **Phase 1: Model Validation** ✅
   - Deploy both models
   - Test basic generation
   - Validate schema constraints
   - Measure performance

2. **Phase 2: Integration Testing** (Current)
   - Compare with Qwen2.5-Coder-32B baseline
   - Test IR generation quality
   - Benchmark latency and cost
   - Evaluate code generation quality

3. **Phase 3: Production Evaluation**
   - A/B test against current model
   - Cost-benefit analysis
   - Decide on production deployment

### Evaluation Criteria

**Quality:**
- IR generation accuracy
- Code correctness and style
- Schema compliance rate

**Performance:**
- Latency (p50, p95, p99)
- Throughput (requests/second)
- Cold start frequency

**Cost:**
- Cost per request
- Total daily cost
- Cost vs. baseline model

## References

- Modal vLLM docs: https://modal.com/docs/examples/vllm_inference
- vLLM GitHub: https://github.com/vllm-project/vllm
- XGrammar: https://github.com/mlc-ai/xgrammar
- Qwen models: https://huggingface.co/Qwen
- Modal LLM Almanac: https://modal.com/llm-almanac

## Maintenance

**When to rebuild:**
- Dependency updates (vLLM, transformers)
- Model version changes
- Configuration optimizations

**Cleanup:**
```bash
# Stop running deployments
modal app stop qwen-vllm-inference

# List volumes
modal volume list

# Delete volumes if needed (models will re-download)
modal volume delete qwen-vllm-models
modal volume delete qwen-vllm-torch-cache
```

---

**Last Updated**: 2025-10-23
**Author**: Claude Code (following lift-sys development guidelines)
**Status**: Experimental - awaiting evaluation results
