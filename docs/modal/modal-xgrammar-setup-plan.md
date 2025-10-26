# Modal.com + XGrammar Setup Plan

**Date**: October 14, 2025
**Priority**: P0 (blocking MVP)
**Status**: Planning

## Problem Statement

The LIFT system requires **constrained generation** to produce valid IR from natural language prompts. Current approach using Claude Sonnet 4 fails because:

1. **No Structured Output Support**: Anthropic API doesn't expose constrained decoding
2. **Schema Validation Fails**: LLM produces invalid JSON 3/3 times
   - Error: `"signature.name is required"`
   - Missing required fields, incorrect types
3. **No Grammar Constraints**: Cannot enforce IR schema at token level

## Solution: Modal.com + XGrammar + Qwen3-Coder

### Architecture

```
┌─────────────────┐
│   LIFT API      │
│  (FastAPI)      │
└────────┬────────┘
         │
         │ HTTP Request
         ▼
┌─────────────────────────────────┐
│   Modal.com Function            │
│                                 │
│  ┌───────────────────────────┐ │
│  │  Qwen3-Coder-30B-A3B     │ │
│  │  (Loaded with vLLM)      │ │
│  └──────────┬────────────────┘ │
│             │                   │
│  ┌──────────▼────────────────┐ │
│  │  XGrammar                 │ │
│  │  (Constrained Decoding)   │ │
│  │  - IR JSON Schema         │ │
│  │  - Grammar enforcement    │ │
│  └───────────────────────────┘ │
└─────────────────────────────────┘
         │
         │ Valid IR JSON
         ▼
    IR Parser → Forward Mode
```

### Why This Stack?

**Modal.com**:
- Serverless GPU inference (A10G, A100)
- Hot/cold starts optimized
- Simple deployment (`modal deploy`)
- Pay per second of GPU use
- Built-in load balancing

**Qwen3-Coder-30B-A3B-Instruct**:
- Instruction-tuned for code tasks
- 30B parameters - good quality/speed balance
- Supports long context (32K tokens)
- Optimized for coding/structured output
- Apache 2.0 license (can deploy commercially)

**XGrammar**:
- Token-level grammar constraints
- Enforces JSON schema during generation
- ~10% performance overhead vs unconstrained
- Supports complex grammars (nested objects, arrays)
- Integrates with vLLM

**vLLM**:
- Fast inference engine (continuous batching)
- PagedAttention for memory efficiency
- Native XGrammar support
- Production-ready

## Implementation Plan

### Phase 1: Modal.com Setup (Day 1)

#### 1.1: Create Modal Account & Setup

```bash
# Install Modal
pip install modal

# Authenticate
modal token new

# Create Modal app
modal app create lift-sys-inference
```

#### 1.2: Create Modal Function for Inference

**File**: `lift_sys/inference/modal_inference.py`

```python
"""
Modal.com inference endpoint with XGrammar constrained generation.
"""

import modal

# Create Modal app
app = modal.App("lift-sys-inference")

# Define GPU requirements
GPU_CONFIG = modal.gpu.A10G()  # or A100() for faster inference

# Define image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm==0.6.3",
        "xgrammar==0.1.5",
        "transformers",
        "torch",
    )
)


@app.function(
    image=image,
    gpu=GPU_CONFIG,
    timeout=300,  # 5 minutes
    container_idle_timeout=120,  # Keep warm for 2 min
    allow_concurrent_inputs=10,
)
@modal.web_endpoint(method="POST")
def generate_ir(request: dict) -> dict:
    """
    Generate IR from natural language using constrained generation.

    Args:
        request: {
            "prompt": str,  # Natural language prompt
            "schema": dict,  # JSON schema for IR
            "max_tokens": int,  # Max tokens to generate
            "temperature": float,  # Sampling temperature
        }

    Returns:
        {
            "ir_json": dict,  # Generated IR
            "tokens_used": int,
            "generation_time_ms": float,
        }
    """
    from vllm import LLM, SamplingParams
    import xgrammar as xgr
    import time
    import json

    # Load model (cached after first cold start)
    llm = LLM(
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        tensor_parallel_size=1,  # Single GPU
        max_model_len=8192,  # Context window
        trust_remote_code=True,
    )

    # Get schema and convert to XGrammar grammar
    schema = request["schema"]
    grammar = xgr.Grammar.from_json_schema(json.dumps(schema))

    # Prepare sampling params with grammar constraint
    sampling_params = SamplingParams(
        temperature=request.get("temperature", 0.3),
        max_tokens=request.get("max_tokens", 2000),
        guided_decoding=xgr.GuidedDecodingParams(grammar=grammar),
    )

    # Format prompt
    prompt = f"""Generate a valid JSON IR (Intermediate Representation) for the following specification:

{request['prompt']}

Requirements:
- Follow the JSON schema exactly
- Include all required fields
- Use proper types

IR JSON:
"""

    # Generate
    start_time = time.time()
    outputs = llm.generate([prompt], sampling_params)
    generation_time = (time.time() - start_time) * 1000

    # Extract generated IR
    generated_text = outputs[0].outputs[0].text
    ir_json = json.loads(generated_text)

    return {
        "ir_json": ir_json,
        "tokens_used": len(outputs[0].outputs[0].token_ids),
        "generation_time_ms": generation_time,
    }


@app.function(image=image)
def test_inference():
    """Test the inference endpoint."""
    test_request = {
        "prompt": "Create a function called add that takes two integers a and b, and returns their sum",
        "schema": {
            "type": "object",
            "properties": {
                "intent": {"type": "object"},
                "signature": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "parameters": {"type": "array"},
                        "returns": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "required": ["intent", "signature"],
        },
        "max_tokens": 1000,
        "temperature": 0.3,
    }

    result = generate_ir.local(test_request)
    print("Test result:", result)
    return result
```

#### 1.3: Deploy to Modal

```bash
# Test locally first
modal run lift_sys/inference/modal_inference.py::test_inference

# Deploy
modal deploy lift_sys/inference/modal_inference.py

# Get endpoint URL
modal app show lift-sys-inference
# Returns: https://your-workspace--lift-sys-inference-generate-ir.modal.run
```

### Phase 2: Integrate with LIFT API (Day 2)

#### 2.1: Create ModalProvider

**File**: `lift_sys/providers/modal_provider.py`

```python
"""Modal.com provider for constrained IR generation."""

from __future__ import annotations
import httpx
from typing import Any
from .base import BaseProvider, ProviderCapabilities


class ModalProvider(BaseProvider):
    """Provider that uses Modal.com for constrained generation."""

    def __init__(self, endpoint_url: str):
        super().__init__(
            name="modal",
            capabilities=ProviderCapabilities(
                streaming=False,
                structured_output=True,  # XGrammar enables this!
                reasoning=True,
            ),
        )
        self.endpoint_url = endpoint_url
        self._client: httpx.AsyncClient | None = None

    async def initialize(self, credentials: dict[str, Any]) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> dict:
        """Generate structured output matching schema."""
        if not self._client:
            raise RuntimeError("Modal provider not initialized")

        response = await self._client.post(
            self.endpoint_url,
            json={
                "prompt": prompt,
                "schema": schema,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        response.raise_for_status()

        result = response.json()
        return result["ir_json"]

    async def generate_text(self, prompt: str, **kwargs: Any) -> str:
        """Generate freeform text (not used for IR generation)."""
        raise NotImplementedError("Use generate_structured for IR generation")

    async def check_health(self) -> bool:
        """Check if Modal endpoint is reachable."""
        if not self._client:
            return False
        try:
            response = await self._client.get(self.endpoint_url.replace("/generate_ir", "/health"))
            return response.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
```

#### 2.2: Update XGrammarIRTranslator to Use ModalProvider

```python
# In lift_sys/forward_mode/xgrammar_translator.py

async def translate(self, prompt: str, ...) -> IntermediateRepresentation:
    """Translate using Modal provider with XGrammar."""

    # Use provider's generate_structured if available
    if hasattr(self.provider, 'generate_structured'):
        ir_json = await self.provider.generate_structured(
            prompt=system_prompt,
            schema=self.schema,
            max_tokens=2000,
            temperature=0.3,
        )
        # Convert to IR objects
        ir = self._json_to_ir(ir_json, language=language)
        return ir
    else:
        # Fallback to current approach
        ...
```

#### 2.3: Configure in Server

```python
# In lift_sys/api/server.py lifespan

modal_endpoint = os.getenv("MODAL_ENDPOINT_URL")
if modal_endpoint:
    modal_provider = ModalProvider(endpoint_url=modal_endpoint)
    await modal_provider.initialize({})
    providers["modal"] = modal_provider
    app.state.primary_provider = "modal"  # Use Modal for IR generation
```

### Phase 3: Testing & Optimization (Day 3)

#### 3.1: Load Testing

```bash
# Test with multiple concurrent requests
for i in {1..10}; do
  curl -X POST https://your-modal-endpoint/generate_ir \
    -H "Content-Type: application/json" \
    -d '{"prompt": "test", "schema": {...}}' &
done
```

#### 3.2: Performance Tuning

- **GPU Selection**: A10G (~$1/hr) vs A100 (~$3/hr)
- **Container Idle Timeout**: Balance cost vs cold starts
- **Batch Size**: Process multiple prompts together
- **Model Quantization**: 4-bit/8-bit for faster inference

#### 3.3: Cost Analysis

**Estimated costs**:
- A10G GPU: $1.10/hour
- Container idle time: 2 minutes (keep warm between requests)
- Average generation: 5 seconds
- **Cost per generation**: ~$0.0015 (0.15 cents)
- **vs Claude API**: $0.015 per request (10x more expensive)

**Monthly estimates** (1000 requests/day):
- Modal: ~$45/month
- Claude API: ~$450/month

### Phase 4: Production Deployment (Day 4)

#### 4.1: Environment Setup

```bash
# .env
MODAL_ENDPOINT_URL="https://your-workspace--lift-sys-inference-generate-ir.modal.run"
MODAL_TOKEN="your-modal-token"
```

#### 4.2: Monitoring

- Modal dashboard for GPU metrics
- Request latency tracking
- Schema validation success rate
- Cost per request

#### 4.3: Fallback Strategy

```python
# If Modal is down, fall back to Claude
if modal_provider_available:
    ir = await modal_provider.generate_structured(...)
else:
    # Fallback to Claude with best-effort parsing
    ir = await anthropic_provider.generate_text(...)
    ir = parse_ir_from_text(ir)
```

## Success Criteria

- [ ] Modal endpoint deployed and responding
- [ ] XGrammar successfully constrains generation
- [ ] 100% IR schema validation success rate
- [ ] <3 second average generation latency
- [ ] Cost <$0.002 per IR generation
- [ ] Fallback to Claude works

## Timeline

- **Day 1**: Modal setup, basic inference endpoint
- **Day 2**: Integration with LIFT API
- **Day 3**: Testing and optimization
- **Day 4**: Production deployment

**Total**: 4 days to production-ready constrained generation

## Next Steps

1. Create Modal account
2. Test basic vLLM + XGrammar setup
3. Deploy inference endpoint
4. Integrate with LIFT API
5. Run end-to-end tests

## References

- XGrammar: https://xgrammar.mlc.ai
- Modal.com: https://modal.com/docs
- Qwen3-Coder: https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- vLLM: https://docs.vllm.ai/
