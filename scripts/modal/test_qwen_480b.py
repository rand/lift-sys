#!/usr/bin/env python3
"""
Test script for Qwen3-Coder-480B-A35B-Instruct-FP8 model on Modal.

This script tests the 480B coder model with code-specific prompts and schemas to validate:
- Code generation capabilities
- Algorithm implementation
- JSON schema-constrained code output
- Performance metrics for large model

Usage:
    # Test code generation
    uv run python scripts/modal/test_qwen_480b.py

    # Or use Modal directly
    modal run lift_sys/inference/modal_qwen_vllm.py::test_480b
"""

import json
import time


def test_basic_code_generation():
    """Test basic code generation without schema constraints."""
    from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

    print("=" * 70)
    print("Test 1: Basic Code Generation")
    print("=" * 70)

    generator = Qwen480BGenerator()
    prompt = """Write a Python function to implement a binary search tree with insert,
    search, and delete operations."""

    start = time.time()
    result = generator.generate.remote(prompt=prompt, max_tokens=1024, temperature=0.3)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text"):
        print("\n✅ Basic code generation works!")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_algorithm_implementation():
    """Test algorithm implementation with structured output."""
    from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

    print("\n" + "=" * 70)
    print("Test 2: Algorithm Implementation (Structured)")
    print("=" * 70)

    schema = {
        "type": "object",
        "properties": {
            "algorithm_name": {"type": "string"},
            "implementation": {"type": "string"},
            "time_complexity": {"type": "string"},
            "space_complexity": {"type": "string"},
            "test_cases": {"type": "array", "items": {"type": "object"}},
            "edge_cases": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "algorithm_name",
            "implementation",
            "time_complexity",
            "space_complexity",
            "test_cases",
        ],
    }

    prompt = """Implement Dijkstra's shortest path algorithm in Python.
    Include time/space complexity, test cases, and edge cases."""

    generator = Qwen480BGenerator()

    start = time.time()
    result = generator.generate.remote(prompt=prompt, schema=schema, max_tokens=2048)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"\nSchema: {json.dumps(schema, indent=2)}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text") and isinstance(result["text"], dict):
        print("\n✅ Structured algorithm implementation works!")
        print(f"Algorithm: {result['text'].get('algorithm_name', 'N/A')}")
        print(f"Time complexity: {result['text'].get('time_complexity', 'N/A')}")
        print(f"Space complexity: {result['text'].get('space_complexity', 'N/A')}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_code_refactoring():
    """Test code refactoring capabilities."""
    from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

    print("\n" + "=" * 70)
    print("Test 3: Code Refactoring")
    print("=" * 70)

    schema = {
        "type": "object",
        "properties": {
            "original_issues": {"type": "array", "items": {"type": "string"}},
            "refactored_code": {"type": "string"},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "performance_gain": {"type": "string"},
        },
        "required": ["original_issues", "refactored_code", "improvements"],
    }

    prompt = """Refactor the following Python code for better performance and readability:

def process_data(items):
    result = []
    for i in range(len(items)):
        if items[i] % 2 == 0:
            result.append(items[i] * 2)
    for i in range(len(result)):
        for j in range(i+1, len(result)):
            if result[i] > result[j]:
                temp = result[i]
                result[i] = result[j]
                result[j] = temp
    return result

Provide: issues, refactored code, improvements, and performance analysis."""

    generator = Qwen480BGenerator()

    start = time.time()
    result = generator.generate.remote(prompt=prompt, schema=schema, max_tokens=1024)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt[:200]}...")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text") and isinstance(result["text"], dict):
        print("\n✅ Code refactoring works!")
        print(f"\nIssues found: {len(result['text'].get('original_issues', []))}")
        print(f"Improvements: {len(result['text'].get('improvements', []))}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_ir_generation():
    """Test intermediate representation generation (lift-sys use case)."""
    from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

    print("\n" + "=" * 70)
    print("Test 4: IR Generation (lift-sys use case)")
    print("=" * 70)

    schema = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["summary", "description"],
            },
            "signature": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z_][a-z0-9_]*$"},
                    "parameters": {"type": "array"},
                    "returns": {"type": "string"},
                },
                "required": ["name", "parameters", "returns"],
            },
            "effects": {"type": "array"},
        },
        "required": ["intent", "signature", "effects"],
    }

    prompt = """Create a function that reads a CSV file, filters rows based on a condition,
    and writes the result to a new file. The condition should be configurable."""

    generator = Qwen480BGenerator()

    start = time.time()
    result = generator.generate.remote(prompt=prompt, schema=schema, max_tokens=1024)
    elapsed = time.time() - start

    print(f"\nPrompt: {prompt}")
    print(f"Response time: {elapsed:.2f}s")
    print(f"\nResult:\n{json.dumps(result, indent=2)}")

    if result.get("text") and isinstance(result["text"], dict):
        print("\n✅ IR generation works!")
        print(f"Function: {result['text'].get('signature', {}).get('name', 'N/A')}")
        print(f"Summary: {result['text'].get('intent', {}).get('summary', 'N/A')}")
    else:
        print(f"\n❌ Failed: {result.get('error')}")

    return result


def test_performance():
    """Test model performance with code generation tasks."""
    from lift_sys.inference.modal_qwen_vllm import Qwen480BGenerator

    print("\n" + "=" * 70)
    print("Test 5: Performance Test (3 code generation requests)")
    print("=" * 70)

    generator = Qwen480BGenerator()
    prompts = [
        "Write a Python function to implement merge sort.",
        "Create a class for a simple LRU cache in Python.",
        "Implement a function to validate balanced parentheses in a string.",
    ]

    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\nRequest {i}/{len(prompts)}: {prompt}")
        start = time.time()
        result = generator.generate.remote(prompt=prompt, max_tokens=512, temperature=0.3)
        elapsed = time.time() - start
        results.append({"prompt": prompt, "elapsed": elapsed, "result": result})
        print(f"Time: {elapsed:.2f}s")
        if result.get("text"):
            print(f"Tokens: {result.get('tokens_used', 'N/A')}")

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
    print("Qwen3-Coder-480B-A35B-Instruct-FP8 Test Suite")
    print("Model: Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8")
    print("GPU: H100 80GB x4 (tensor parallel)")
    print("=" * 70)

    try:
        # Run tests
        test_basic_code_generation()
        test_algorithm_implementation()
        test_code_refactoring()
        test_ir_generation()
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
