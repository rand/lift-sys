"""
Modal.com inference endpoint with vLLM + XGrammar constrained generation.

This module provides GPU-accelerated, schema-constrained IR generation using:
- vLLM for fast inference
- XGrammar for JSON schema enforcement
- Qwen2.5-Coder-32B-Instruct (or configurable model)

Deploy with: modal deploy lift_sys/inference/modal_app.py
"""

import modal

# Create Modal app
app = modal.App("lift-sys-inference")

# Model configuration
MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
MODEL_REVISION = "main"

# GPU configuration - A10G is cost-effective, A100 for faster inference
GPU_CONFIG = "A10G"  # ~$1.10/hr, good balance
# For production with high load: "A100"  # ~$3/hr

# Container image with all dependencies
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "fastapi[standard]",  # Required for web endpoints
    "vllm==0.6.4.post1",  # Includes compatible outlines version
    "torch==2.5.1",
    "transformers==4.46.3",  # Avoid yanked version
    "xgrammar==0.1.5",
)


@app.cls(
    image=image,
    gpu=GPU_CONFIG,
    timeout=600,  # 10 minutes for model loading + inference
    scaledown_window=300,  # Keep warm for 5 minutes (balance cost vs latency)
)
@modal.concurrent(max_inputs=20)  # Process multiple requests concurrently
class ConstrainedIRGenerator:
    """GPU-accelerated IR generator with schema constraints."""

    @modal.enter()
    def load_model(self):
        """Load model on container startup (cached after first cold start)."""
        import time

        from vllm import LLM

        print(f"Loading model: {MODEL_NAME}")
        start = time.time()

        self.llm = LLM(
            model=MODEL_NAME,
            revision=MODEL_REVISION,
            tensor_parallel_size=1,  # Single GPU
            max_model_len=8192,  # Context window
            trust_remote_code=True,
            dtype="auto",  # Use bfloat16 automatically on supported GPUs
            gpu_memory_utilization=0.90,  # Use 90% of GPU memory
        )

        load_time = time.time() - start
        print(f"Model loaded in {load_time:.2f}s")

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
        Generate IR from natural language with JSON schema constraints.

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

        import xgrammar as xgr
        from vllm import SamplingParams

        # Convert JSON schema to XGrammar grammar
        try:
            grammar = xgr.Grammar.from_json_schema(
                json.dumps(schema),
                indent=2,  # Pretty-print JSON
                separators=(",", ": "),
                strict_mode=True,  # Enforce all schema constraints
            )
        except Exception as e:
            return {
                "error": f"Invalid schema: {str(e)}",
                "ir_json": None,
                "tokens_used": 0,
                "generation_time_ms": 0,
                "finish_reason": "schema_error",
            }

        # Create sampling params with XGrammar constraint
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            guided_decoding_backend="xgrammar",  # Use XGrammar for constraints
            guided_grammar=grammar,
        )

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

        # Generate with constraints
        start_time = time.time()
        try:
            outputs = self.llm.generate([formatted_prompt], sampling_params)
            generation_time = (time.time() - start_time) * 1000

            # Extract result
            output = outputs[0].outputs[0]
            generated_text = output.text.strip()

            # Parse JSON
            ir_json = json.loads(generated_text)

            return {
                "ir_json": ir_json,
                "tokens_used": len(output.token_ids),
                "generation_time_ms": generation_time,
                "finish_reason": output.finish_reason,
            }

        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON generated: {str(e)}",
                "raw_output": generated_text[:500],  # First 500 chars for debugging
                "ir_json": None,
                "tokens_used": 0,
                "generation_time_ms": time.time() * 1000 - start_time,
                "finish_reason": "json_error",
            }
        except Exception as e:
            return {
                "error": f"Generation failed: {str(e)}",
                "ir_json": None,
                "tokens_used": 0,
                "generation_time_ms": time.time() * 1000 - start_time,
                "finish_reason": "error",
            }

    @modal.fastapi_endpoint(method="POST", label="generate")
    async def web_generate(self, item: dict) -> dict:
        """
        HTTP endpoint for IR generation.

        POST body:
        {
            "prompt": str,
            "schema": dict,
            "max_tokens": int,
            "temperature": float,
        }
        """
        return self.generate(
            prompt=item["prompt"],
            schema=item["schema"],
            max_tokens=item.get("max_tokens", 2048),
            temperature=item.get("temperature", 0.3),
            top_p=item.get("top_p", 0.95),
        )


# Health check endpoint - separate from GPU class to avoid triggering model load
@app.function(image=image)
@modal.fastapi_endpoint(method="GET", label="health")
def health():
    """Health check endpoint that doesn't require GPU."""
    return {"status": "healthy", "model": MODEL_NAME, "gpu": GPU_CONFIG}


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
