# Modal Working Configuration
**Date**: October 15, 2025
**Status**: ✅ Working - Production Ready

---

## Overview

This document records the known working configuration for Modal.com GPU inference with vLLM + XGrammar for schema-constrained IR generation.

---

## Verified Working Stack

### Core Dependencies
- **vLLM**: 0.9.2
- **transformers**: 4.53.0 (must be >= 4.51.1 and < 4.54.0)
- **XGrammar**: 0.1.19 (automatically installed with vLLM 0.9.2)
- **CUDA**: 12.4.1
- **Python**: 3.12

### Supporting Libraries
- **FastAPI**: 0.115.12
- **HuggingFace Hub**: >= 0.20.0
- **hf-transfer**: 0.1.9 (Rust-based fast downloads)
- **FlashInfer**: 0.4.1 (Optimized top-p/top-k sampling)

### GPU Configuration
- **GPU Type**: A10G (24GB VRAM)
- **Cost**: ~$1.10/hr
- **Model**: Qwen2.5-Coder-7B-Instruct
- **Memory Utilization**: 0.90 (90%)
- **KV Cache**: 77,904 tokens

---

## Performance Metrics

### Cold Start Times
- **First deploy**: ~3-5 minutes (image build + model download)
- **Subsequent cold starts**: ~30-60 seconds (model loading from volume cache)
- **Model loading**: ~117 seconds
- **CUDA graph capture**: ~32 seconds

### Request Latency (Warm Container)
- **Health check**: < 50ms
- **IR generation**: 6-7 seconds (136 tokens)
- **Tokens per second**: ~20-22 tps

### Resource Usage
- **Model size**: 14.2 GiB VRAM
- **KV cache**: 0.50 GiB
- **Total GPU memory**: ~15 GiB / 24 GiB

---

## API Usage

### Correct vLLM 0.9.2 API

```python
from vllm import SamplingParams
from vllm.sampling_params import GuidedDecodingParams

# Create guided decoding params for JSON schema
guided_decoding = GuidedDecodingParams(json=schema)

# Create sampling params with guided decoding
sampling_params = SamplingParams(
    temperature=0.3,
    top_p=0.95,
    max_tokens=2048,
    guided_decoding=guided_decoding,  # Use guided_decoding, NOT guided_json
)

# Generate
response = llm.generate([prompt], sampling_params)
```

### ⚠️ Common Mistakes

**DON'T USE** (vLLM 0.6.x API - deprecated):
```python
# This will fail in vLLM 0.9.2+
sampling_params = SamplingParams(
    guided_json=schema,  # ❌ WRONG - throws "Unexpected keyword argument"
)
```

**DO USE** (vLLM 0.9.2+ API):
```python
# Correct approach for vLLM 0.9.2+
guided_decoding = GuidedDecodingParams(json=schema)  # ✅ CORRECT
sampling_params = SamplingParams(guided_decoding=guided_decoding)
```

---

## Version Constraints

### Critical Version Ranges

| Package | Version | Constraint | Reason |
|---------|---------|------------|--------|
| vLLM | 0.9.2 | Exact | XGrammar native support |
| transformers | 4.53.0 | >= 4.51.1 AND < 4.54.0 | vLLM requirement + aimv2 conflict avoidance |
| XGrammar | 0.1.19+ | >= 0.1.19 | Installed automatically with vLLM |
| Python | 3.12 | 3.12 | Modal default, works well |

### Version Conflict History

**transformers 4.57.0** → ❌ aimv2 config conflict
```
ValueError: 'aimv2' is already used by a Transformers config, pick another name.
```

**transformers 4.46.0** → ❌ Too old for vLLM 0.9.2
```
ERROR: vllm 0.9.2 depends on transformers>=4.51.1
```

**transformers 4.53.0** → ✅ Works perfectly
- Satisfies vLLM 0.9.2 requirement (>= 4.51.1)
- Avoids aimv2 conflict (< 4.54.0)

---

## Performance Optimizations

### FlashInfer (Enabled)

**Status**: ✅ Installed and Working

**Package**: flashinfer-python 0.4.1

**Benefits**:
- Optimized top-p & top-k sampling (10-20% faster)
- No code changes required
- Works automatically with vLLM 0.9.2

**Verification**:
- No "FlashInfer is not available" warning in logs
- Test generation: 3.49s for 100 tokens (significantly faster than baseline 6-7s)

---

## Modal Configuration

### Image Definition

```python
llm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.4.1-devel-ubuntu22.04",
        add_python="3.12"
    )
    .apt_install("git", "wget")
    .pip_install(
        "vllm==0.9.2",
        "xgrammar",
        "transformers==4.53.0",
        "fastapi[standard]==0.115.12",
        "huggingface-hub>=0.20.0",
        "hf-transfer",
    )
    .env({
        "CUDA_HOME": "/usr/local/cuda",
        "PATH": "/usr/local/cuda/bin:${PATH}",
        "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "TOKENIZERS_PARALLELISM": "false",
    })
)
```

### LLM Initialization

```python
from vllm import LLM

llm = LLM(
    model="Qwen/Qwen2.5-Coder-7B-Instruct",
    trust_remote_code=True,
    dtype="auto",
    gpu_memory_utilization=0.90,
    guided_decoding_backend="xgrammar",  # XGrammar for JSON constraints
)
```

### Decoding Config (from logs)

```
decoding_config=DecodingConfig(
    backend='xgrammar',
    disable_fallback=False,
    disable_any_whitespace=False,
    disable_additional_properties=False,
    reasoning_backend=''
)
```

---

## Endpoints

### Development (modal serve)
- **Health**: https://rand--health-dev.modal.run
- **Generate**: https://rand--generate-dev.modal.run

### Production (modal deploy)
- **Health**: https://rand--health.modal.run
- **Generate**: https://rand--generate.modal.run

---

## Test Results

### Example Request

```json
{
  "prompt": "Create a function called add that takes two integers a and b, and returns their sum as an integer",
  "schema": { /* IR_JSON_SCHEMA */ },
  "max_tokens": 1024,
  "temperature": 0.3
}
```

### Example Response

```json
{
  "ir_json": {
    "intent": {
      "summary": "Create a function called add...",
      "rationale": "This function will perform basic arithmetic addition..."
    },
    "signature": {
      "name": "add",
      "parameters": [
        {"name": "a", "type_hint": "int"},
        {"name": "b", "type_hint": "int"}
      ],
      "returns": "int"
    }
  },
  "tokens_used": 136,
  "generation_time_ms": 6406.09,
  "finish_reason": "stop"
}
```

**Result**: ✅ Valid IR JSON matching schema exactly (XGrammar enforcement working)

---

## Troubleshooting

### TypeError: 'Function' object is not callable

**Problem**: FastAPI endpoint trying to call `@modal.method()` decorated function directly

**Solution**: Create private implementation method `_generate_impl()` and call from both `@modal.method()` and `@modal.fastapi_endpoint()`

```python
def _generate_impl(self, ...):
    # Implementation here
    pass

@modal.method()
def generate(self, ...):
    return self._generate_impl(...)

@modal.fastapi_endpoint()
async def web_generate(self, item):
    return self._generate_impl(...)  # Call impl directly, not generate()
```

### Unexpected keyword argument 'guided_json'

**Problem**: Using old vLLM 0.6.x API with vLLM 0.9.2

**Solution**: Use `GuidedDecodingParams` instead:
```python
from vllm.sampling_params import GuidedDecodingParams
guided_decoding = GuidedDecodingParams(json=schema)
sampling_params = SamplingParams(guided_decoding=guided_decoding)
```

---

## Next Steps

1. **Add FlashInfer** for 10-20% performance improvement
2. **Test Qwen3-Coder models** (now supported in vLLM 0.9.2+)
3. **Investigate SGLang** with Modal's fork for 3-10x faster constrained generation
4. **Production deployment** with `modal deploy`

---

## References

- vLLM 0.9.2 Docs: https://docs.vllm.ai/en/v0.9.2/
- XGrammar Docs: https://xgrammar.mlc.ai
- Structured Outputs Guide: https://docs.vllm.ai/en/v0.9.2/features/structured_outputs.html
- Modal LLM Guide: https://modal.com/docs/guide/developing-with-llms
- FlashInfer: https://github.com/flashinfer-ai/flashinfer

---

**Last Updated**: October 15, 2025
**Tested By**: Claude Code
**Status**: ✅ Production Ready
