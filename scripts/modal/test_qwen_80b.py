#!/usr/bin/env python3
"""
Test script for Qwen3-Next-80B-A3B-Instruct-FP8 model on Modal.

This script tests the 80B model with various prompts and schemas to validate:
- Basic text generation
- JSON schema-constrained generation
- Code generation capabilities
- Performance metrics

Usage:
    # Test basic generation
    uv run python scripts/modal/test_qwen_80b.py

    # Or use Modal directly
    modal run lift_sys/inference/modal_qwen_vllm.py::test_80b
"""

import json
import time


def test_basic_generation():
    """Test basic text generation without schema constraints."""
    from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

    print("=" * 70)
    print("Test 1: Basic Text Generation")
    print("=" * 70)

    generator = Qwen80BGenerator()
    prompt = "Explain quantum computing in simple terms."

    start = time.time()
    result = generator.generate.remote(prompt=prompt, max_tokens=512, temperature=0.7)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text"):
        print("\n✅ Basic generation works!")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_structured_output():
    """Test JSON schema-constrained generation."""
    from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

    print("\n" + "=" * 70)
    print("Test 2: Structured Output (JSON Schema)")
    print("=" * 70)

    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_points": {"type": "array", "items": {"type": "string"}},
            "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["summary", "key_points", "sentiment", "confidence"],
    }

    prompt = """Analyze the following statement: 'AI will revolutionize software development
    by automating repetitive tasks and enabling developers to focus on creative problem solving.'"""

    generator = Qwen80BGenerator()

    start = time.time()
    result = generator.generate.remote(prompt=prompt, schema=schema, max_tokens=1024)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"\nSchema: {json.dumps(schema, indent=2)}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text") and isinstance(result["text"], dict):
        print("\n✅ Structured output works!")
        print(f"Summary: {result['text'].get('summary', 'N/A')}")
        print(f"Sentiment: {result['text'].get('sentiment', 'N/A')}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_code_generation():
    """Test code generation with schema."""
    from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

    print("\n" + "=" * 70)
    print("Test 3: Code Generation")
    print("=" * 70)

    schema = {
        "type": "object",
        "properties": {
            "function_name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
            "code": {"type": "string"},
            "test_cases": {"type": "array", "items": {"type": "string"}},
            "complexity": {"type": "string"},
        },
        "required": ["function_name", "code", "test_cases", "complexity"],
    }

    prompt = """Create a Python function that implements quicksort algorithm.
    Include test cases and complexity analysis."""

    generator = Qwen80BGenerator()

    start = time.time()
    result = generator.generate.remote(prompt=prompt, schema=schema, max_tokens=1024)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text") and isinstance(result["text"], dict):
        print("\n✅ Code generation works!")
        print(f"\nFunction: {result['text'].get('function_name', 'N/A')}")
        print(f"Complexity: {result['text'].get('complexity', 'N/A')}")
        print(f"\nCode:\n{result['text'].get('code', 'N/A')}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_performance():
    """Test model performance with multiple requests."""
    from lift_sys.inference.modal_qwen_vllm import Qwen80BGenerator

    print("\n" + "=" * 70)
    print("Test 4: Performance Test (5 requests)")
    print("=" * 70)

    generator = Qwen80BGenerator()
    prompts = [
        "What is machine learning?",
        "Explain neural networks briefly.",
        "What is the difference between AI and ML?",
        "What is deep learning?",
        "Explain transformers in NLP.",
    ]

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\nRequest {i}/{len(prompts)}: {prompt}")
        start = time.time()
        result = generator.generate.remote(prompt=prompt, max_tokens=256, temperature=0.5)
        elapsed = time.time() - start
        results.append({"prompt": prompt, "elapsed": elapsed, "result": result})
        print(f"Time: {elapsed:.2f}s")

    # Calculate statistics
    times = [r["elapsed"] for r in results]
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    print("\n" + "=" * 70)
    print("Performance Statistics:")
    print("=" * 70)
    print(f"Average response time: {avg_time:.2f}s")
    print(f"Min response time: {min_time:.2f}s")
    print(f"Max response time: {max_time:.2f}s")

    return results


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Qwen3-Next-80B-A3B-Instruct-FP8 Test Suite")
    print("Model: Qwen/Qwen3-Next-80B-A3B-Instruct-FP8")
    print("GPU: H100 80GB x1")
    print("=" * 70)

    try:
        # Run tests
        test_basic_generation()
        test_structured_output()
        test_code_generation()
        test_performance()

        print("\n" + "=" * 70)
        print("✅ All tests completed!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
