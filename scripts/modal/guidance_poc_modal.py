"""
Modal-based llguidance POC Test

Runs the Guidance TypeScript generation POC on Modal with GPU.
This avoids local model download issues and tests in a production-like environment.
"""

import os

import modal

# Create Modal app
app = modal.App("guidance-poc")

# Create image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "guidance>=0.1.15",
    "transformers>=4.40.0",
    "torch>=2.0.0",
    "accelerate>=0.20.0",
    "huggingface-hub>=0.20.0",
)

# HuggingFace token secret
hf_secret = modal.Secret.from_name("huggingface")


@app.function(
    image=image,
    gpu="T4",  # T4 for cost-effective POC (can upgrade to L40S if needed)
    secrets=[hf_secret],
    timeout=1800,  # 30 minutes max
)
def run_guidance_poc():
    """
    Run the Guidance POC test with TypeScript schema.

    Returns:
        dict: Test results with success status, timing, and validation results
    """
    import json
    import time

    from guidance import gen, models

    results = {
        "success": False,
        "steps": {},
        "errors": [],
        "total_time": 0,
    }

    start_total = time.time()

    print("=" * 70)
    print("  Guidance TypeScript POC - Modal Execution")
    print("=" * 70)

    # Step 0: Authentication
    print("\n" + "=" * 70)
    print("  Step 0: HuggingFace Authentication")
    print("=" * 70)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        results["errors"].append("HF_TOKEN not set")
        return results

    try:
        from huggingface_hub import login

        login(token=hf_token)
        print("✅ Authenticated with HuggingFace")
        results["steps"]["auth"] = {"success": True}
    except Exception as e:
        error_msg = f"Authentication failed: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

    # Step 1: Model Loading
    print("\n" + "=" * 70)
    print("  Step 1: Model Loading")
    print("=" * 70)
    print("Loading model: TinyLlama/TinyLlama-1.1B-Chat-v1.0 (GPU mode)")
    print("NOTE: Using TinyLlama for faster POC validation")

    try:
        start_load = time.time()
        lm = models.Transformers(
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            device_map="auto",  # Auto-select GPU
            trust_remote_code=True,
            token=hf_token,
        )
        load_time = time.time() - start_load
        print(f"✅ Model loaded in {load_time:.2f}s")
        results["steps"]["model_load"] = {
            "success": True,
            "time": load_time,
            "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        }
    except Exception as e:
        error_msg = f"Model loading failed: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

    # Step 2: Schema Definition
    print("\n" + "=" * 70)
    print("  Step 2: TypeScript Schema Setup")
    print("=" * 70)

    # Simplified TypeScript generation schema
    typescript_schema = {
        "type": "object",
        "properties": {
            "function_name": {"type": "string"},
            "parameters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["name", "type"],
                },
            },
            "return_type": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["function_name", "parameters", "return_type", "body"],
    }

    print(f"✅ Schema configured with {len(typescript_schema['properties'])} properties")
    results["steps"]["schema"] = {"success": True}

    # Step 3: Prompt Generation
    print("\n" + "=" * 70)
    print("  Step 3: Prompt Generation")
    print("=" * 70)

    prompt = """Generate a TypeScript function that adds two numbers.

The function should:
- Be named 'add'
- Take two parameters: a (number) and b (number)
- Return the sum as a number
- Have a simple implementation: return a + b

Respond with a JSON object describing the function."""

    print(f"✅ Prompt ready ({len(prompt)} chars)")
    results["steps"]["prompt"] = {"success": True, "length": len(prompt)}

    # Step 4: Schema-Constrained Generation
    print("\n" + "=" * 70)
    print("  Step 4: Schema-Constrained Generation")
    print("=" * 70)

    try:
        start_gen = time.time()

        # Apply prompt
        lm += prompt

        # Generate with schema constraints
        print("Generating TypeScript function with schema constraints...")
        lm += gen(name="output", schema=typescript_schema, max_tokens=200)

        gen_time = time.time() - start_gen
        print(f"✅ Generation completed in {gen_time:.2f}s")
        results["steps"]["generation"] = {
            "success": True,
            "time": gen_time,
        }
    except Exception as e:
        error_msg = f"Generation failed: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

    # Step 5: Output Validation
    print("\n" + "=" * 70)
    print("  Step 5: Output Validation")
    print("=" * 70)

    try:
        output = lm["output"]
        print(f"Generated output type: {type(output)}")

        # Parse if string
        if isinstance(output, str):
            output = json.loads(output)

        print("\nGenerated structure:")
        print(json.dumps(output, indent=2))

        # Validate schema compliance
        validation_checks = {
            "Has 'function_name'": "function_name" in output,
            "Has 'parameters'": "parameters" in output,
            "Parameters is array": isinstance(output.get("parameters"), list),
            "Has 'return_type'": "return_type" in output,
            "Has 'body'": "body" in output,
            "Function name is 'add'": output.get("function_name") == "add",
            "Has 2 parameters": len(output.get("parameters", [])) == 2,
        }

        print("\nValidation Results:")
        all_passed = True
        for check, passed in validation_checks.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check}")
            all_passed = all_passed and passed

        results["steps"]["validation"] = {
            "success": all_passed,
            "checks": validation_checks,
            "output": output,
        }

        if not all_passed:
            results["errors"].append("Some validation checks failed")
    except Exception as e:
        error_msg = f"Validation failed: {e}"
        print(f"❌ {error_msg}")
        results["errors"].append(error_msg)
        return results

    # Summary
    total_time = time.time() - start_total
    results["total_time"] = total_time
    results["success"] = len(results["errors"]) == 0

    print("\n" + "=" * 70)
    print("  POC Summary")
    print("=" * 70)

    if results["success"]:
        print("✅ SUCCESS: Guidance POC completed successfully!")
        print("\nTiming breakdown:")
        print(f"  Model loading:  {results['steps']['model_load']['time']:.2f}s")
        print(f"  Generation:     {results['steps']['generation']['time']:.2f}s")
        print(f"  Total:          {total_time:.2f}s")
    else:
        print("❌ FAILURE: POC encountered errors")
        for error in results["errors"]:
            print(f"  - {error}")

    return results


@app.local_entrypoint()
def main():
    """Run the POC and print results."""
    print("Launching Guidance POC on Modal...")
    result = run_guidance_poc.remote()

    print("\n" + "=" * 70)
    print("  Final Results")
    print("=" * 70)
    print(f"Success: {result['success']}")
    print(f"Total time: {result['total_time']:.2f}s")

    if result["errors"]:
        print("\nErrors:")
        for error in result["errors"]:
            print(f"  - {error}")

    return 0 if result["success"] else 1
