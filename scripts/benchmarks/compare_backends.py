"""Compare llguidance vs XGrammar backend performance.

Runs identical test prompts through both backends to measure:
- Success rate (% valid outputs)
- Time to First Token (TTFT)
- Total latency (end-to-end)
- Token throughput (tokens/second)

Usage:
    # Run benchmark with default settings
    python scripts/benchmarks/compare_backends.py

    # Specify endpoints
    python scripts/benchmarks/compare_backends.py \
        --llguidance https://rand--qwen-80b-generate.modal.run \
        --xgrammar https://rand--xgrammar-generate.modal.run

    # Custom test count
    python scripts/benchmarks/compare_backends.py --num-tests 100
"""

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel


class BenchmarkResult(BaseModel):
    """Result of a single benchmark test."""

    backend: str  # "llguidance" or "xgrammar"
    prompt: str
    schema: dict[str, Any]
    success: bool
    latency_seconds: float
    tokens_used: int | None = None
    generation_time_ms: float | None = None
    finish_reason: str | None = None
    error: str | None = None
    output: dict[str, Any] | None = None


@dataclass
class BackendStats:
    """Aggregate statistics for a backend."""

    backend: str
    total_tests: int
    successes: int
    failures: int
    success_rate: float
    avg_latency: float
    min_latency: float
    max_latency: float
    median_latency: float
    p95_latency: float
    p99_latency: float
    avg_tokens: float | None
    total_time: float


# Test prompts covering various complexity levels
TEST_PROMPTS = [
    # Simple functions (10 prompts)
    "Write a Python function that adds two numbers",
    "Write a Python function that checks if a number is even",
    "Write a Python function that reverses a string",
    "Write a Python function that finds the maximum of two numbers",
    "Write a Python function that returns True",
    "Write a Python function that concatenates two strings",
    "Write a Python function that checks if a string is empty",
    "Write a Python function that multiplies two numbers",
    "Write a Python function that returns the length of a list",
    "Write a Python function that checks if a number is positive",
    # Medium complexity (10 prompts)
    "Write a Python function that finds the maximum element in a list",
    "Write a Python function that filters even numbers from a list",
    "Write a Python function that counts occurrences of a character in a string",
    "Write a Python function that checks if a string is a palindrome",
    "Write a Python function that removes duplicates from a list",
    "Write a Python function that merges two sorted lists",
    "Write a Python function that finds the factorial of a number recursively",
    "Write a Python function that validates an email address format",
    "Write a Python function that converts Celsius to Fahrenheit",
    "Write a Python function that calculates the sum of digits in a number",
    # Complex algorithms (10 prompts)
    "Write a Python function that implements binary search on a sorted list",
    "Write a Python function that implements bubble sort",
    "Write a Python function that implements quicksort",
    "Write a Python function that finds the longest common subsequence",
    "Write a Python function that checks if a binary tree is balanced",
    "Write a Python function that implements depth-first search on a graph",
    "Write a Python function that finds all permutations of a string",
    "Write a Python function that implements a least-recently-used (LRU) cache",
    "Write a Python function that solves the N-queens problem",
    "Write a Python function that finds the shortest path in a weighted graph",
    # Edge cases (10 prompts)
    "Write a Python function that handles empty list input gracefully",
    "Write a Python function that validates non-negative integer input",
    "Write a Python function with comprehensive error handling",
    "Write a Python function that processes optional parameters",
    "Write a Python function that works with nested data structures",
    "Write a Python function that handles Unicode strings correctly",
    "Write a Python function with multiple return types based on conditions",
    "Write a Python function that manages resource cleanup with context manager",
    "Write a Python function with type hints for complex generic types",
    "Write a Python function that handles async operations with proper cancellation",
    # Real-world scenarios (10 prompts)
    "Write a Python function that parses JSON and extracts specific fields",
    "Write a Python function that validates a password meets security requirements",
    "Write a Python function that formats a date string in ISO format",
    "Write a Python function that calculates compound interest",
    "Write a Python function that generates a random alphanumeric string",
    "Write a Python function that sanitizes SQL query input",
    "Write a Python function that compresses a string using run-length encoding",
    "Write a Python function that validates a URL format",
    "Write a Python function that converts snake_case to camelCase",
    "Write a Python function that calculates file hash (SHA-256)",
]

# Standard schema for function generation
FUNCTION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type_hint": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name", "type_hint"],
            },
        },
        "returns": {"type": "string", "minLength": 1},
        "body": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
    },
    "required": ["name", "parameters", "returns", "body"],
}


async def test_backend(
    endpoint_url: str,
    backend_name: str,
    prompt: str,
    schema: dict[str, Any],
    timeout: float = 120.0,
) -> BenchmarkResult:
    """Test a single prompt against a backend."""
    start_time = time.time()

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                endpoint_url,
                json={
                    "prompt": prompt,
                    "schema": schema,
                    "max_tokens": 1024,
                    "temperature": 0.0,  # Deterministic
                },
            )
            latency = time.time() - start_time

            if response.status_code != 200:
                return BenchmarkResult(
                    backend=backend_name,
                    prompt=prompt,
                    schema=schema,
                    success=False,
                    latency_seconds=latency,
                    error=f"HTTP {response.status_code}: {response.text}",
                )

            result = response.json()

            # Extract output (different field names for different backends)
            output = result.get("text") or result.get("ir_json")
            if not output:
                return BenchmarkResult(
                    backend=backend_name,
                    prompt=prompt,
                    schema=schema,
                    success=False,
                    latency_seconds=latency,
                    error="No output in response",
                    output=result,
                )

            # Validate output has required fields
            required_fields = schema.get("required", [])
            missing_fields = [f for f in required_fields if f not in output]

            if missing_fields:
                return BenchmarkResult(
                    backend=backend_name,
                    prompt=prompt,
                    schema=schema,
                    success=False,
                    latency_seconds=latency,
                    error=f"Missing required fields: {missing_fields}",
                    output=output,
                )

            # Success!
            return BenchmarkResult(
                backend=backend_name,
                prompt=prompt,
                schema=schema,
                success=True,
                latency_seconds=latency,
                tokens_used=result.get("tokens_used"),
                generation_time_ms=result.get("generation_time_ms"),
                finish_reason=result.get("finish_reason"),
                output=output,
            )

        except TimeoutError:
            latency = time.time() - start_time
            return BenchmarkResult(
                backend=backend_name,
                prompt=prompt,
                schema=schema,
                success=False,
                latency_seconds=latency,
                error=f"Timeout after {timeout}s",
            )
        except Exception as e:
            latency = time.time() - start_time
            return BenchmarkResult(
                backend=backend_name,
                prompt=prompt,
                schema=schema,
                success=False,
                latency_seconds=latency,
                error=str(e),
            )


def calculate_stats(results: list[BenchmarkResult]) -> BackendStats:
    """Calculate aggregate statistics from results."""
    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    successful_latencies = [r.latency_seconds for r in successes]
    all_latencies = [r.latency_seconds for r in results]

    tokens = [r.tokens_used for r in successes if r.tokens_used is not None]

    return BackendStats(
        backend=results[0].backend if results else "unknown",
        total_tests=len(results),
        successes=len(successes),
        failures=len(failures),
        success_rate=len(successes) / len(results) * 100 if results else 0,
        avg_latency=statistics.mean(successful_latencies) if successful_latencies else 0,
        min_latency=min(successful_latencies) if successful_latencies else 0,
        max_latency=max(successful_latencies) if successful_latencies else 0,
        median_latency=statistics.median(successful_latencies) if successful_latencies else 0,
        p95_latency=statistics.quantiles(all_latencies, n=20)[18] if all_latencies else 0,
        p99_latency=statistics.quantiles(all_latencies, n=100)[98] if all_latencies else 0,
        avg_tokens=statistics.mean(tokens) if tokens else None,
        total_time=sum(all_latencies),
    )


def print_comparison(llguidance_stats: BackendStats, xgrammar_stats: BackendStats):
    """Print side-by-side comparison."""
    print("\n" + "=" * 80)
    print("BENCHMARK COMPARISON: llguidance vs XGrammar")
    print("=" * 80)

    print(f"\n{'Metric':<30} {'llguidance':>20} {'XGrammar':>20}")
    print("-" * 80)

    # Success metrics
    print(
        f"{'Total Tests':<30} {llguidance_stats.total_tests:>20} {xgrammar_stats.total_tests:>20}"
    )
    print(f"{'Successes':<30} {llguidance_stats.successes:>20} {xgrammar_stats.successes:>20}")
    print(f"{'Failures':<30} {llguidance_stats.failures:>20} {xgrammar_stats.failures:>20}")
    print(
        f"{'Success Rate':<30} {llguidance_stats.success_rate:>19.1f}% {xgrammar_stats.success_rate:>19.1f}%"
    )

    # Latency metrics
    print(f"\n{'Latency (successful runs):':<30}")
    print(
        f"{'  Average':<30} {llguidance_stats.avg_latency:>19.2f}s {xgrammar_stats.avg_latency:>19.2f}s"
    )
    print(
        f"{'  Median':<30} {llguidance_stats.median_latency:>19.2f}s {xgrammar_stats.median_latency:>19.2f}s"
    )
    print(
        f"{'  Min':<30} {llguidance_stats.min_latency:>19.2f}s {xgrammar_stats.min_latency:>19.2f}s"
    )
    print(
        f"{'  Max':<30} {llguidance_stats.max_latency:>19.2f}s {xgrammar_stats.max_latency:>19.2f}s"
    )
    print(
        f"{'  P95':<30} {llguidance_stats.p95_latency:>19.2f}s {xgrammar_stats.p95_latency:>19.2f}s"
    )
    print(
        f"{'  P99':<30} {llguidance_stats.p99_latency:>19.2f}s {xgrammar_stats.p99_latency:>19.2f}s"
    )

    # Token metrics
    if llguidance_stats.avg_tokens and xgrammar_stats.avg_tokens:
        print(f"\n{'Token Usage (avg):':<30}")
        print(
            f"{'  Tokens per request':<30} {llguidance_stats.avg_tokens:>19.1f} {xgrammar_stats.avg_tokens:>19.1f}"
        )

    # Improvement calculations
    print(f"\n{'Improvement (llguidance vs XGrammar):':<30}")

    success_improvement = llguidance_stats.success_rate - xgrammar_stats.success_rate
    print(f"{'  Success rate':<30} {success_improvement:>+18.1f} percentage points")

    if xgrammar_stats.avg_latency > 0:
        latency_improvement = (
            (xgrammar_stats.avg_latency - llguidance_stats.avg_latency)
            / xgrammar_stats.avg_latency
            * 100
        )
        speedup = xgrammar_stats.avg_latency / llguidance_stats.avg_latency
        print(f"{'  Latency reduction':<30} {latency_improvement:>+18.1f}%")
        print(f"{'  Speedup':<30} {speedup:>19.1f}x")

    print("\n" + "=" * 80)


async def main():
    """Run benchmark comparison."""
    parser = argparse.ArgumentParser(description="Compare llguidance vs XGrammar backends")
    parser.add_argument(
        "--llguidance",
        default="https://rand--qwen-80b-generate.modal.run",
        help="llguidance endpoint URL",
    )
    parser.add_argument(
        "--xgrammar",
        default="https://rand--xgrammar-generate.modal.run",
        help="XGrammar endpoint URL (must be deployed separately)",
    )
    parser.add_argument(
        "--num-tests",
        type=int,
        default=50,
        help="Number of test prompts to run (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for detailed results (JSON)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Timeout per request in seconds (default: 120)",
    )

    args = parser.parse_args()

    # Select test prompts
    prompts = TEST_PROMPTS[: args.num_tests]

    print("\n🔬 Starting benchmark comparison")
    print(f"   llguidance endpoint: {args.llguidance}")
    print(f"   XGrammar endpoint: {args.xgrammar}")
    print(f"   Number of tests: {len(prompts)}")
    print(f"   Timeout: {args.timeout}s")
    print()

    # Run llguidance tests
    print("Testing llguidance backend...")
    llguidance_results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"  [{i}/{len(prompts)}] Testing: {prompt[:60]}...")
        result = await test_backend(
            args.llguidance, "llguidance", prompt, FUNCTION_SCHEMA, args.timeout
        )
        llguidance_results.append(result)
        status = "✅" if result.success else "❌"
        print(f"    {status} {result.latency_seconds:.2f}s")

    # Run XGrammar tests
    print("\nTesting XGrammar backend...")
    xgrammar_results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"  [{i}/{len(prompts)}] Testing: {prompt[:60]}...")
        result = await test_backend(
            args.xgrammar, "xgrammar", prompt, FUNCTION_SCHEMA, args.timeout
        )
        xgrammar_results.append(result)
        status = "✅" if result.success else "❌"
        print(f"    {status} {result.latency_seconds:.2f}s")

    # Calculate statistics
    llguidance_stats = calculate_stats(llguidance_results)
    xgrammar_stats = calculate_stats(xgrammar_results)

    # Print comparison
    print_comparison(llguidance_stats, xgrammar_stats)

    # Save detailed results
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "llguidance_endpoint": args.llguidance,
                "xgrammar_endpoint": args.xgrammar,
                "num_tests": len(prompts),
                "timeout": args.timeout,
            },
            "llguidance": {
                "stats": {
                    "total_tests": llguidance_stats.total_tests,
                    "successes": llguidance_stats.successes,
                    "failures": llguidance_stats.failures,
                    "success_rate": llguidance_stats.success_rate,
                    "avg_latency": llguidance_stats.avg_latency,
                    "median_latency": llguidance_stats.median_latency,
                    "min_latency": llguidance_stats.min_latency,
                    "max_latency": llguidance_stats.max_latency,
                    "p95_latency": llguidance_stats.p95_latency,
                    "p99_latency": llguidance_stats.p99_latency,
                    "avg_tokens": llguidance_stats.avg_tokens,
                },
                "results": [r.model_dump() for r in llguidance_results],
            },
            "xgrammar": {
                "stats": {
                    "total_tests": xgrammar_stats.total_tests,
                    "successes": xgrammar_stats.successes,
                    "failures": xgrammar_stats.failures,
                    "success_rate": xgrammar_stats.success_rate,
                    "avg_latency": xgrammar_stats.avg_latency,
                    "median_latency": xgrammar_stats.median_latency,
                    "min_latency": xgrammar_stats.min_latency,
                    "max_latency": xgrammar_stats.max_latency,
                    "p95_latency": xgrammar_stats.p95_latency,
                    "p99_latency": xgrammar_stats.p99_latency,
                    "avg_tokens": xgrammar_stats.avg_tokens,
                },
                "results": [r.model_dump() for r in xgrammar_results],
            },
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n📊 Detailed results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
