"""
Modal.com inference with vLLM for Qwen3 models (80B and 480B).

This module provides GPU-accelerated inference for two large Qwen models:
1. Qwen3-Next-80B-A3B-Instruct-FP8 (80B params, ~3B active MoE)
2. Qwen3-Coder-480B-A35B-Instruct-FP8 (480B params, ~35B active MoE)

Both models use:
- vLLM for efficient inference with PagedAttention
- XGrammar for JSON schema-constrained generation
- FP8 quantization for reduced memory footprint
- H100 GPUs with tensor parallelism as needed

Development Workflow:
    # Development with hot-reload
    modal serve lift_sys/inference/modal_qwen_vllm.py

    # One-time test run
    modal run lift_sys/inference/modal_qwen_vllm.py::test_80b
    modal run lift_sys/inference/modal_qwen_vllm.py::test_480b

    # Production deployment
    modal deploy lift_sys/inference/modal_qwen_vllm.py

Model Specifications:
    Qwen3-Next-80B:
    - Model: Qwen/Qwen3-Next-80B-A3B-Instruct-FP8
    - Memory: ~40-50GB (FP8)
    - GPU: H100 80GB x1
    - Tensor parallel: 1
    - Cold start: ~8-10 minutes

    Qwen3-Coder-480B:
    - Model: Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8
    - Memory: ~240GB (FP8, all MoE experts loaded)
    - GPU: H100 80GB x8
    - Tensor parallel: 8
    - Cold start: ~20-30 minutes

Endpoints:
    80B Model:
    - Health: https://rand--qwen-80b-health.modal.run (GET)
    - Generate: https://rand--qwen-80b-generate.modal.run (POST)
    - Warmup: https://rand--qwen-80b-warmup.modal.run (GET)

    480B Model:
    - Health: https://rand--qwen-480b-health.modal.run (GET)
    - Generate: https://rand--qwen-480b-generate.modal.run (POST)
    - Warmup: https://rand--qwen-480b-warmup.modal.run (GET)

Performance Notes:
    - Both models use FP8 quantization for 2x memory reduction
    - MoE architecture: All experts loaded, but only active subset used per token
    - First request triggers model download and compilation (slow)
    - Subsequent requests use cached models (fast)
    - XGrammar ensures schema-compliant JSON output
"""

import modal

# Create Modal app for Qwen model experiments
app = modal.App("qwen-vllm-inference")

# Dependency versions
VLLM_VERSION = "0.11.0"  # Latest version with improved model support
FASTAPI_VERSION = "0.115.12"
HF_HUB_VERSION = "0.20.0"

# Build optimized image for vLLM inference
# Using CUDA 12.4.1 for H100 compatibility
# Using vLLM 0.11.0 which is compatible with latest transformers
llm_image = (
    modal.Image.from_registry("nvidia/cuda:12.4.1-devel-ubuntu22.04", add_python="3.12")
    .apt_install(
        "git",  # Required for transformers cache and git install
        "wget",  # Useful for downloads
    )
    .uv_pip_install(
        f"vllm=={VLLM_VERSION}",  # vLLM 0.11.0 with improved compatibility
        "xgrammar",  # XGrammar for constrained generation
        f"fastapi[standard]=={FASTAPI_VERSION}",  # Web framework
        f"huggingface-hub>={HF_HUB_VERSION}",  # Model downloads
        "hf-transfer",  # Fast downloads from HuggingFace
        "flashinfer-python",  # Optimized sampling (10-20% faster)
    )
    # vLLM 0.11.0 ships with compatible transformers, no need for git install
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

# Model configurations
QWEN_80B_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct-FP8"
QWEN_480B_MODEL = "Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8"

# Shared model caching volume
MODELS_DIR = "/models"
volume = modal.Volume.from_name("qwen-vllm-models", create_if_missing=True)

# Torch compilation cache for faster cold starts
TORCH_COMPILE_CACHE_DIR = "/root/.cache/vllm"
torch_cache_volume = modal.Volume.from_name("qwen-vllm-torch-cache", create_if_missing=True)


# =============================================================================
# Qwen3-Next-80B-A3B-Instruct-FP8 (80B params, ~3B active)
# =============================================================================


@app.cls(
    image=llm_image,
    gpu="H100:2",  # 2x H100 80GB with tensor parallelism
    volumes={
        MODELS_DIR: volume,
        TORCH_COMPILE_CACHE_DIR: torch_cache_volume,
    },
    timeout=1800,  # 30 minutes for first download/load
    scaledown_window=600,  # Keep warm for 10 minutes
)
@modal.concurrent(max_inputs=10)
class Qwen80BGenerator:
    """
    Qwen3-Next-80B-A3B inference with vLLM + XGrammar.

    Model: Qwen/Qwen3-Next-80B-A3B-Instruct-FP8
    GPU: H100 80GB x2 (tensor parallel)
    Memory: ~75GB model weights (MoE loads all experts)
    Tensor parallel: 2
    """

    @modal.enter()
    def load_model(self):
        """Load 80B model on container startup."""
        import os
        import time

        print(f"Loading model: {QWEN_80B_MODEL}")
        print(f"Model cache directory: {MODELS_DIR}")
        print("GPU: 2x H100 80GB (tensor parallel)")
        start = time.time()

        # Set HuggingFace cache to Modal volume
        os.environ["HF_HOME"] = MODELS_DIR

        # Import vLLM
        from vllm import LLM

        # Check eager mode setting
        enforce_eager = os.getenv("VLLM_EAGER", "0") == "1"
        if enforce_eager:
            print("⚡ Eager execution mode enabled (no torch.compile)")

        # Initialize vLLM for 80B FP8 model
        # - FP8 quantization but MoE loads ALL expert weights (~75GB)
        # - Requires 2x H100 to fit model + KV cache
        # - Tensor parallelism splits weights across GPUs
        self.llm = LLM(
            model=QWEN_80B_MODEL,
            trust_remote_code=True,
            dtype="auto",  # Use FP8 as specified in model config
            gpu_memory_utilization=0.85,  # Conservative for stability
            max_model_len=8192,  # Sufficient for most tasks
            tensor_parallel_size=2,  # Split across 2 GPUs
            guided_decoding_backend="xgrammar",  # XGrammar for JSON schema
            enforce_eager=enforce_eager,
        )

        load_time = time.time() - start
        print(f"✅ Model loaded in {load_time:.2f}s")
        print(f"Model: {QWEN_80B_MODEL}")
        print("XGrammar backend enabled for structured outputs")

        # Commit volume changes
        volume.commit()
        if not enforce_eager:
            torch_cache_volume.commit()

    def _generate_impl(
        self,
        prompt: str,
        schema: dict | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """
        Generate text with optional JSON schema constraints.

        Args:
            prompt: Input text
            schema: Optional JSON schema for constrained generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter

        Returns:
            {
                "text": str,  # Generated text (or JSON if schema provided)
                "tokens_used": int,
                "generation_time_ms": float,
                "finish_reason": str,
            }
        """
        import json
        import time

        from vllm import SamplingParams
        from vllm.sampling_params import GuidedDecodingParams

        start_time = time.time()
        try:
            # Configure sampling with optional schema constraint
            guided_decoding = None
            if schema:
                guided_decoding = GuidedDecodingParams(json=schema)

            sampling_params = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                guided_decoding=guided_decoding,
            )

            # Generate
            response = self.llm.generate([prompt], sampling_params)
            generation_time = (time.time() - start_time) * 1000

            # Extract result
            output = response[0]
            generated_text = output.outputs[0].text.strip()

            # Parse JSON if schema was provided
            result_data = generated_text
            if schema:
                try:
                    result_data = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    return {
                        "error": f"Invalid JSON generated: {str(e)}",
                        "raw_output": generated_text[:500],
                        "text": None,
                        "tokens_used": 0,
                        "generation_time_ms": generation_time,
                        "finish_reason": "json_error",
                    }

            return {
                "text": result_data,
                "tokens_used": len(output.outputs[0].token_ids),
                "generation_time_ms": generation_time,
                "finish_reason": output.outputs[0].finish_reason,
            }

        except Exception as e:
            return {
                "error": f"Generation failed: {str(e)}",
                "text": None,
                "tokens_used": 0,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "finish_reason": "error",
            }

    @modal.method()
    def generate(
        self,
        prompt: str,
        schema: dict | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """Modal method endpoint for generation."""
        return self._generate_impl(prompt, schema, max_tokens, temperature, top_p)

    @modal.fastapi_endpoint(method="POST", label="qwen-80b-generate")
    async def web_generate(self, request: dict) -> dict:
        """
        HTTP endpoint for generation.

        POST body:
        {
            "prompt": str,  # required
            "schema": dict,  # optional - JSON schema for constrained generation
            "max_tokens": int,  # optional, default 2048
            "temperature": float,  # optional, default 0.3
            "top_p": float,  # optional, default 0.95
        }
        """
        if "prompt" not in request:
            return {"error": "Missing required field: prompt", "status": 400}

        return self._generate_impl(
            prompt=request["prompt"],
            schema=request.get("schema"),
            max_tokens=request.get("max_tokens", 2048),
            temperature=request.get("temperature", 0.3),
            top_p=request.get("top_p", 0.95),
        )

    @modal.fastapi_endpoint(method="GET", label="qwen-80b-warmup")
    async def warmup(self) -> dict:
        """Warm-up endpoint to pre-load model."""
        return {
            "status": "warm",
            "model_loaded": True,
            "model": QWEN_80B_MODEL,
            "gpu": "H100 x1",
            "ready_for_requests": True,
        }


# Health check for 80B model
@app.function(image=llm_image)
@modal.fastapi_endpoint(method="GET", label="qwen-80b-health")
def health_80b():
    """Health check endpoint (doesn't require GPU)."""
    return {
        "status": "healthy",
        "model": QWEN_80B_MODEL,
        "gpu": "H100 x1",
        "backend": f"vLLM {VLLM_VERSION} with XGrammar",
    }


# =============================================================================
# Qwen3-Coder-480B-A35B-Instruct-FP8 (480B params, ~35B active)
# =============================================================================


@app.cls(
    image=llm_image,
    gpu="H100:8",  # 8x H100 80GB with tensor parallelism (640GB total VRAM)
    volumes={
        MODELS_DIR: volume,
        TORCH_COMPILE_CACHE_DIR: torch_cache_volume,
    },
    timeout=3600,  # 60 minutes for first download/load
    scaledown_window=600,  # Keep warm for 10 minutes
)
@modal.concurrent(max_inputs=3)  # Fewer concurrent for large model
class Qwen480BGenerator:
    """
    Qwen3-Coder-480B-A35B inference with vLLM + XGrammar.

    Model: Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8
    GPU: H100 80GB x8 (tensor parallel)
    Memory: ~240GB (FP8, all experts loaded)
    Tensor parallel: 8
    """

    @modal.enter()
    def load_model(self):
        """Load 480B model on container startup with tensor parallelism."""
        import os
        import time

        print(f"Loading model: {QWEN_480B_MODEL}")
        print(f"Model cache directory: {MODELS_DIR}")
        print("GPU: 8x H100 80GB (tensor parallel)")
        start = time.time()

        # Set HuggingFace cache to Modal volume
        os.environ["HF_HOME"] = MODELS_DIR

        # Import vLLM
        from vllm import LLM

        # Check eager mode setting
        enforce_eager = os.getenv("VLLM_EAGER", "0") == "1"
        if enforce_eager:
            print("⚡ Eager execution mode enabled (no torch.compile)")

        # Initialize vLLM for 480B FP8 MoE model
        # - FP8 reduces memory by ~2x vs BF16
        # - MoE loads all experts (~480B params) but only ~35B active
        # - Need 8x H100 80GB (640GB total) for ~240GB model + KV cache
        # - Using 32K context as recommended in docs to avoid OOM
        self.llm = LLM(
            model=QWEN_480B_MODEL,
            trust_remote_code=True,
            dtype="auto",  # Use FP8 as specified in model config
            gpu_memory_utilization=0.80,  # Conservative for multi-GPU stability
            max_model_len=32768,  # Reduced from 262K to avoid OOM (per docs)
            tensor_parallel_size=8,  # Distribute across 8 H100s
            guided_decoding_backend="xgrammar",  # XGrammar for JSON schema
            enforce_eager=enforce_eager,
        )

        load_time = time.time() - start
        print(f"✅ Model loaded in {load_time:.2f}s")
        print(f"Model: {QWEN_480B_MODEL}")
        print("Tensor parallel: 8 GPUs")
        print("XGrammar backend enabled for structured outputs")

        # Commit volume changes
        volume.commit()
        if not enforce_eager:
            torch_cache_volume.commit()

    def _generate_impl(
        self,
        prompt: str,
        schema: dict | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """
        Generate text with optional JSON schema constraints.

        Args:
            prompt: Input text
            schema: Optional JSON schema for constrained generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter

        Returns:
            {
                "text": str,  # Generated text (or JSON if schema provided)
                "tokens_used": int,
                "generation_time_ms": float,
                "finish_reason": str,
            }
        """
        import json
        import time

        from vllm import SamplingParams
        from vllm.sampling_params import GuidedDecodingParams

        start_time = time.time()
        try:
            # Configure sampling with optional schema constraint
            guided_decoding = None
            if schema:
                guided_decoding = GuidedDecodingParams(json=schema)

            sampling_params = SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                guided_decoding=guided_decoding,
            )

            # Generate
            response = self.llm.generate([prompt], sampling_params)
            generation_time = (time.time() - start_time) * 1000

            # Extract result
            output = response[0]
            generated_text = output.outputs[0].text.strip()

            # Parse JSON if schema was provided
            result_data = generated_text
            if schema:
                try:
                    result_data = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    return {
                        "error": f"Invalid JSON generated: {str(e)}",
                        "raw_output": generated_text[:500],
                        "text": None,
                        "tokens_used": 0,
                        "generation_time_ms": generation_time,
                        "finish_reason": "json_error",
                    }

            return {
                "text": result_data,
                "tokens_used": len(output.outputs[0].token_ids),
                "generation_time_ms": generation_time,
                "finish_reason": output.outputs[0].finish_reason,
            }

        except Exception as e:
            return {
                "error": f"Generation failed: {str(e)}",
                "text": None,
                "tokens_used": 0,
                "generation_time_ms": (time.time() - start_time) * 1000,
                "finish_reason": "error",
            }

    @modal.method()
    def generate(
        self,
        prompt: str,
        schema: dict | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        top_p: float = 0.95,
    ) -> dict:
        """Modal method endpoint for generation."""
        return self._generate_impl(prompt, schema, max_tokens, temperature, top_p)

    @modal.fastapi_endpoint(method="POST", label="qwen-480b-generate")
    async def web_generate(self, request: dict) -> dict:
        """
        HTTP endpoint for generation.

        POST body:
        {
            "prompt": str,  # required
            "schema": dict,  # optional - JSON schema for constrained generation
            "max_tokens": int,  # optional, default 2048
            "temperature": float,  # optional, default 0.3
            "top_p": float,  # optional, default 0.95
        }
        """
        if "prompt" not in request:
            return {"error": "Missing required field: prompt", "status": 400}

        return self._generate_impl(
            prompt=request["prompt"],
            schema=request.get("schema"),
            max_tokens=request.get("max_tokens", 2048),
            temperature=request.get("temperature", 0.3),
            top_p=request.get("top_p", 0.95),
        )

    @modal.fastapi_endpoint(method="GET", label="qwen-480b-warmup")
    async def warmup(self) -> dict:
        """Warm-up endpoint to pre-load model."""
        return {
            "status": "warm",
            "model_loaded": True,
            "model": QWEN_480B_MODEL,
            "gpu": "H100 x8 (tensor parallel)",
            "ready_for_requests": True,
        }


# Health check for 480B model
@app.function(image=llm_image)
@modal.fastapi_endpoint(method="GET", label="qwen-480b-health")
def health_480b():
    """Health check endpoint (doesn't require GPU)."""
    return {
        "status": "healthy",
        "model": QWEN_480B_MODEL,
        "gpu": "H100 x8 (tensor parallel)",
        "backend": f"vLLM {VLLM_VERSION} with XGrammar",
    }


# =============================================================================
# Local test functions
# =============================================================================


@app.local_entrypoint()
def test_80b():
    """Test the 80B model locally."""
    import json

    print("=" * 70)
    print("Testing Qwen3-Next-80B-A3B-Instruct-FP8")
    print("=" * 70)

    # Test schema for structured output
    test_schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string"},
        },
        "required": ["answer", "confidence", "reasoning"],
    }

    test_prompt = """What is the capital of France? Provide your answer with confidence level and reasoning."""

    print(f"\nPrompt: {test_prompt}")
    print(f"\nSchema: {json.dumps(test_schema, indent=2)}")
    print("\nCalling Modal function...")

    generator = Qwen80BGenerator()
    result = generator.generate.remote(
        prompt=test_prompt, schema=test_schema, max_tokens=512, temperature=0.3
    )

    print("\n" + "=" * 70)
    print("RESULT:")
    print("=" * 70)
    print(json.dumps(result, indent=2))

    if result.get("text"):
        print("\n✅ Success!")
    else:
        print(f"\n❌ Failed: {result.get('error')}")


@app.local_entrypoint()
def test_480b():
    """Test the 480B model locally."""
    import json

    print("=" * 70)
    print("Testing Qwen3-Coder-480B-A35B-Instruct-FP8")
    print("=" * 70)

    # Test schema for code generation
    test_schema = {
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "explanation": {"type": "string"},
            "complexity": {"type": "string"},
        },
        "required": ["code", "explanation", "complexity"],
    }

    test_prompt = """Write a Python function to implement binary search on a sorted list. Include complexity analysis."""

    print(f"\nPrompt: {test_prompt}")
    print(f"\nSchema: {json.dumps(test_schema, indent=2)}")
    print("\nCalling Modal function...")

    generator = Qwen480BGenerator()
    result = generator.generate.remote(
        prompt=test_prompt, schema=test_schema, max_tokens=1024, temperature=0.3
    )

    print("\n" + "=" * 70)
    print("RESULT:")
    print("=" * 70)
    print(json.dumps(result, indent=2))

    if result.get("text"):
        print("\n✅ Success!")
        print("\nGenerated code:")
        print(result["text"].get("code", "N/A"))
    else:
        print(f"\n❌ Failed: {result.get('error')}")
