"""
Modal.com inference endpoint with vLLM + XGrammar constrained generation.

This module provides GPU-accelerated, schema-constrained IR generation using:
- vLLM 0.9.2 for fast inference with PagedAttention
- XGrammar (native in vLLM 0.9.2+) for JSON schema enforcement
- Qwen2.5-Coder-32B-Instruct model

Development Workflow:
    # Development with hot-reload (recommended for testing)
    modal serve lift_sys/inference/modal_app.py

    # One-time test run
    modal run lift_sys/inference/modal_app.py::test

    # Production deployment
    modal deploy lift_sys/inference/modal_app.py

Endpoints:
    - Health: https://rand--health.modal.run (GET)
    - Generate: https://rand--generate.modal.run (POST)
    - Warmup: https://rand--warmup.modal.run (GET)

Performance:
    - Cold start (32B model): ~7 minutes (model loading + compilation)
    - Warm containers: 2-10 seconds response time
    - Recommended timeout: 600s (10 min) for cold starts

Optimizations (2025-10-22):
    - Added Pydantic request validation (prevents KeyError crashes)
    - Using uv for 10-100x faster image builds
    - Single endpoint pattern (removed duplicate endpoints)
    - Warm-up endpoint to pre-load model

For more info: https://modal.com/docs/guide/developing-with-llms

Note: Switched from SGLang to vLLM due to sgl_kernel compatibility issues on Modal H100.
SGLang investigation documented in docs/SGLANG_MODAL_ISSUES.md for future optimization.
"""

import modal

# Create Modal app
app = modal.App("lift-sys-inference")

# Dependency versions
VLLM_VERSION = "0.9.2"  # v0.9.2+ has native XGrammar support
TRANSFORMERS_VERSION = "4.53.0"  # Must be >=4.51.1 (vLLM req) and <4.54.0 (aimv2 conflict)
FASTAPI_VERSION = "0.115.12"
HF_HUB_VERSION = "0.20.0"


# Create optimized base image with all dependencies
# Image version: v8 (vLLM 0.9.2 + XGrammar + FlashInfer on CUDA 12.4.1)
llm_image = (
    # Use newer NVIDIA CUDA development image (12.4.1 fixes deprecation warnings)
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install(
        "git",  # Required for transformers cache
        "wget",  # Useful for downloading assets
    )
    .uv_pip_install(
        f"vllm=={VLLM_VERSION}",  # vLLM with PagedAttention
        "xgrammar",  # XGrammar for constrained generation
        f"transformers=={TRANSFORMERS_VERSION}",  # Model support
        f"fastapi[standard]=={FASTAPI_VERSION}",  # Web framework (includes pydantic)
        f"huggingface-hub>={HF_HUB_VERSION}",  # Model downloads
        "hf-transfer",  # Fast downloads from HuggingFace (Rust-based)
        "flashinfer-python",  # Optimized top-p/top-k sampling (10-20% faster)
    )
    .env(
        {
            # CUDA paths
            "CUDA_HOME": "/usr/local/cuda",
            "PATH": "/usr/local/cuda/bin:${PATH}",
            "LD_LIBRARY_PATH": "/usr/local/cuda/lib64:/usr/local/cuda/lib",
            # Performance optimizations
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
)

# Model configuration
# Using Qwen2.5-Coder-32B-Instruct for code generation
# 32B parameter model optimized for code tasks
MODEL_NAME = "Qwen/Qwen2.5-Coder-32B-Instruct"
MODEL_REVISION = "main"

# GPU configuration
# 32B model fits comfortably on A100-80GB
GPU_CONFIG = "A100-80GB"  # ~$4/hr

# Model caching with Modal Volume for faster cold starts
# Models are downloaded once and reused across container restarts
MODELS_DIR = "/models"
volume = modal.Volume.from_name("lift-sys-models", create_if_missing=True)

# Torch compilation cache for faster subsequent cold starts
# After first compilation (~125s), cached graphs load in seconds
TORCH_COMPILE_CACHE_DIR = "/root/.cache/vllm"
torch_cache_volume = modal.Volume.from_name("lift-sys-torch-cache", create_if_missing=True)


@app.cls(
    image=llm_image,  # Image with vLLM, transformers, FastAPI
    gpu=GPU_CONFIG,
    volumes={
        MODELS_DIR: volume,  # Mount volume for model caching
        TORCH_COMPILE_CACHE_DIR: torch_cache_volume,  # Cache torch compilation graphs
    },
    timeout=1200,  # 20 minutes for first-time model download + loading + inference
    scaledown_window=600,  # Keep warm for 10 minutes to avoid cold starts during testing
)
@modal.concurrent(max_inputs=20)  # Process multiple requests concurrently
class ConstrainedIRGenerator:
    """GPU-accelerated IR generator with schema constraints using vLLM + XGrammar."""

    @modal.enter()
    def load_model(self):
        """Load model on container startup (cached after first cold start)."""
        import os
        import time

        print(f"Loading model: {MODEL_NAME}")
        print(f"Model cache directory: {MODELS_DIR}")
        print(f"Torch cache directory: {TORCH_COMPILE_CACHE_DIR}")
        start = time.time()

        # Set HuggingFace cache to use Modal volume for faster cold starts
        # Use HF_HOME only (TRANSFORMERS_CACHE deprecated in transformers v5)
        os.environ["HF_HOME"] = MODELS_DIR

        # Import vLLM
        from vllm import LLM

        # Check if eager execution mode requested (faster cold starts, slower inference)
        # Set VLLM_EAGER=1 in Modal secrets to disable torch.compile
        enforce_eager = os.getenv("VLLM_EAGER", "0") == "1"
        if enforce_eager:
            print("⚡ Eager execution mode enabled (no torch.compile)")
            print("   Cold start: ~5min instead of 7min")
            print("   Inference: 10-20% slower")

        # Initialize vLLM with XGrammar backend for constrained generation
        # vLLM 0.9.2+ has native XGrammar support (default backend)
        # Optimized settings for 32B model on A100-80GB:
        # - 32B BF16 model ~64GB, fits comfortably on 80GB GPU
        # - Limited max_model_len (8192) sufficient for IR generation
        # - Torch compilation cache persisted across restarts (first: ~125s, cached: ~5s)
        self.llm = LLM(
            model=MODEL_NAME,
            trust_remote_code=True,
            dtype="auto",  # BF16 for Qwen2.5
            gpu_memory_utilization=0.90,  # 32B fits well on A100-80GB
            max_model_len=8192,  # Sufficient for IR, reduces memory footprint
            guided_decoding_backend="xgrammar",  # XGrammar for fast JSON schema enforcement
            enforce_eager=enforce_eager,  # Disable torch.compile if VLLM_EAGER=1
        )

        load_time = time.time() - start
        print(f"Model loaded in {load_time:.2f}s")
        print(f"Model: {MODEL_NAME}")
        print("XGrammar backend enabled for structured outputs")
        if not enforce_eager:
            print(f"Torch compilation cache: {TORCH_COMPILE_CACHE_DIR}")

        # Commit volume changes to persist caches
        volume.commit()
        if not enforce_eager:
            torch_cache_volume.commit()  # Persist compiled graphs

    def _generate_impl(
        self,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """
        Internal implementation of generation logic.

        Generate IR from natural language with JSON schema constraints using vLLM.

        Args:
            prompt: Natural language specification
            schema: JSON schema to enforce
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter

        Returns:
            {
                "ir_json": dict,  # Generated IR matching schema
                "tokens_used": int,
                "generation_time_ms": float,
                "finish_reason": str,
            }
        """
        import json
        import time

        from vllm import SamplingParams
        from vllm.sampling_params import GuidedDecodingParams

        # Format prompt for code model
        formatted_prompt = f"""You are a code specification assistant. Generate a valid JSON intermediate representation (IR) for the following specification.

Specification:
{prompt}

Requirements:
- Follow the JSON schema exactly
- Include all required fields
- Use proper Python type hints (int, str, list[int], dict[str, Any], etc.)
- Function names should be snake_case
- Be specific and complete

Generate the IR as valid JSON:
"""

        # Generate with JSON schema constraints using vLLM + XGrammar
        start_time = time.time()
        try:
            # vLLM 0.9.2+ API: Use GuidedDecodingParams for schema constraints
            # XGrammar backend handles schema enforcement automatically
            guided_decoding = GuidedDecodingParams(json=schema)
            sampling_params = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                guided_decoding=guided_decoding,  # JSON schema constraint (uses XGrammar)
            )

            response = self.llm.generate([formatted_prompt], sampling_params)
            generation_time = (time.time() - start_time) * 1000

            # Extract result (vLLM returns list of RequestOutput objects)
            output = response[0]
            generated_text = output.outputs[0].text.strip()

            # Parse JSON
            ir_json = json.loads(generated_text)

            return {
                "ir_json": ir_json,
                "tokens_used": len(output.outputs[0].token_ids),
                "generation_time_ms": generation_time,
                "finish_reason": output.outputs[0].finish_reason,
            }

        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON generated: {str(e)}",
                "raw_output": generated_text[:500] if "generated_text" in locals() else "",
                "ir_json": None,
                "tokens_used": 0,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "finish_reason": "json_error",
            }
        except Exception as e:
            return {
                "error": f"Generation failed: {str(e)}",
                "ir_json": None,
                "tokens_used": 0,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "finish_reason": "error",
            }

    @modal.method()
    def generate(
        self,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """
        Generate IR from natural language with JSON schema constraints using vLLM.

        This is the Modal method endpoint. For internal use, call _generate_impl directly.
        """
        return self._generate_impl(prompt, schema, max_tokens, temperature, top_p)

    @modal.fastapi_endpoint(method="POST", label="generate")
    async def web_generate(self, request: dict) -> dict:
        """
        HTTP endpoint for schema-constrained generation.

        Supports both:
        - Prompt → IR generation
        - IR → Code generation

        POST body:
        {
            "prompt": str,  # required
            "schema": dict,  # required
            "max_tokens": int,  # optional, default 2048
            "temperature": float,  # optional, default 0.3
            "top_p": float,  # optional, default 0.95
        }

        The schema determines what type of generation:
        - IR_JSON_SCHEMA → generates IR from natural language
        - CODE_GENERATION_SCHEMA → generates code implementation from IR
        """
        # Validate required fields to prevent KeyError (P0 fix)
        if "prompt" not in request:
            return {"error": "Missing required field: prompt", "status": 400}
        if "schema" not in request:
            return {"error": "Missing required field: schema", "status": 400}

        return self._generate_impl(
            prompt=request["prompt"],
            schema=request["schema"],
            max_tokens=request.get("max_tokens", 2048),
            temperature=request.get("temperature", 0.3),
            top_p=request.get("top_p", 0.95),
        )

    @modal.fastapi_endpoint(method="GET", label="warmup")
    async def warmup(self) -> dict:
        """
        Warm-up endpoint to pre-load model without generating.

        Call this endpoint to trigger model loading (7 min cold start for 32B model).
        Subsequent requests will be fast (~2-10s).

        Returns:
            {"status": "warm", "model_loaded": True, "model": MODEL_NAME}
        """
        # Model is already loaded in @modal.enter(), just return status
        return {
            "status": "warm",
            "model_loaded": True,
            "model": MODEL_NAME,
            "ready_for_requests": True,
        }


# Health check endpoint - separate from GPU class to avoid triggering model load
@app.function(image=llm_image)
@modal.fastapi_endpoint(method="GET", label="health")
def health():
    """Health check endpoint that doesn't require GPU."""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "gpu": GPU_CONFIG,
        "backend": f"vLLM {VLLM_VERSION} with XGrammar",
    }


# Local testing function
@app.local_entrypoint()
def test():
    """Test the IR generator locally."""
    import json

    # Simple test schema
    test_schema = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                },
                "required": ["summary"],
            },
            "signature": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
                    "parameters": {"type": "array"},
                    "returns": {"type": "string"},
                },
                "required": ["name", "parameters"],
            },
        },
        "required": ["intent", "signature"],
    }

    test_prompt = (
        "Create a function called add that takes two integers a and b, and returns their sum"
    )

    print(f"Testing with prompt: {test_prompt}\n")
    print("Calling Modal function...")

    generator = ConstrainedIRGenerator()
    result = generator.generate.remote(
        prompt=test_prompt,
        schema=test_schema,
        max_tokens=1024,
        temperature=0.3,
    )

    print("\n" + "=" * 70)
    print("RESULT:")
    print("=" * 70)
    print(json.dumps(result, indent=2))

    if result.get("ir_json"):
        print("\n✅ Success! Generated valid IR:")
        print(json.dumps(result["ir_json"], indent=2))
    else:
        print(f"\n❌ Failed: {result.get('error')}")
