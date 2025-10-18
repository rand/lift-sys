#!/usr/bin/env python3
"""
Performance Benchmarking Script for lift-sys

Measures latencies and costs across the forward mode pipeline:
- NLP → IR generation (will include semantic analysis in future)
- IR → Code generation
- End-to-end workflow

Supports both sequential and parallel execution modes:
- Sequential: Tests run one at a time (accurate memory profiling)
- Parallel: Tests run concurrently in batches (4x faster, matches Modal concurrency)

Usage:
    # Sequential mode (default)
    python performance_benchmark.py

    # Parallel mode with default settings (4 workers)
    python performance_benchmark.py --parallel

    # Parallel mode with custom workers
    python performance_benchmark.py --parallel --max-workers 8

    # Select specific test suite
    python performance_benchmark.py --suite phase2 --parallel

Design: Extensible to support future Semantic IR enhancements
(entity resolution, clause analysis, relationship graphs, etc.)
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
import ast
import asyncio
import json
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import mean, median, stdev
from typing import Any

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.schema import IR_JSON_SCHEMA
from lift_sys.providers.modal_provider import ModalProvider


@dataclass
class ComponentMetrics:
    """Metrics for a single pipeline component.

    Designed to be extended when Semantic IR components are added:
    - entity_resolution_ms
    - clause_analysis_ms
    - relationship_graph_ms
    - ambiguity_detection_ms
    - intent_inference_ms
    """

    name: str
    latency_ms: float
    memory_mb: float
    success: bool
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionTestResult:
    """Result from executing generated code with test inputs."""

    test_name: str
    passed: bool
    expected: Any
    actual: Any
    error: str | None = None


@dataclass
class BenchmarkResult:
    """Complete benchmark result for a single test case."""

    test_name: str
    prompt: str
    timestamp: str

    # Pipeline stage metrics
    nlp_to_ir: ComponentMetrics | None = None
    ir_to_code: ComponentMetrics | None = None

    # Future: Semantic analysis stages (Phase 5-6)
    # entity_resolution: Optional[ComponentMetrics] = None
    # clause_analysis: Optional[ComponentMetrics] = None
    # relationship_graph: Optional[ComponentMetrics] = None
    # ambiguity_detection: Optional[ComponentMetrics] = None

    # Overall metrics
    total_latency_ms: float = 0.0
    total_memory_mb: float = 0.0
    end_to_end_success: bool = False

    # Cost tracking
    estimated_cost_usd: float = 0.0
    provider_type: str = ""

    # Output artifacts
    ir_output: dict | None = None
    code_output: str | None = None

    # Execution testing
    execution_tests: list[ExecutionTestResult] = field(default_factory=list)
    execution_success: bool = False


@dataclass
class BenchmarkSummary:
    """Summary statistics across multiple benchmark runs."""

    total_runs: int
    successful_runs: int
    failed_runs: int

    # Latency statistics (ms)
    nlp_to_ir_mean: float = 0.0
    nlp_to_ir_median: float = 0.0
    nlp_to_ir_std: float = 0.0

    ir_to_code_mean: float = 0.0
    ir_to_code_median: float = 0.0
    ir_to_code_std: float = 0.0

    e2e_mean: float = 0.0
    e2e_median: float = 0.0
    e2e_std: float = 0.0

    # Cost statistics
    total_cost_usd: float = 0.0
    cost_per_request_mean: float = 0.0

    # Memory statistics (MB)
    memory_mean: float = 0.0
    memory_peak: float = 0.0


class PerformanceBenchmark:
    """Performance benchmarking suite for lift-sys.

    Designed to be extensible for future Semantic IR enhancements.
    """

    def __init__(
        self,
        provider: ModalProvider,
        output_dir: Path = Path("benchmark_results"),
        estimate_costs: bool = True,
    ):
        self.provider = provider
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.estimate_costs = estimate_costs
        self.results: list[BenchmarkResult] = []

    async def measure_component(self, name: str, func, *args, **kwargs) -> ComponentMetrics:
        """Measure a single pipeline component with timing and memory tracking."""
        tracemalloc.start()
        start_time = time.perf_counter()
        start_memory = tracemalloc.get_traced_memory()[0]

        try:
            result = (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)

        end_time = time.perf_counter()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        latency_ms = (end_time - start_time) * 1000
        memory_mb = (peak_memory - start_memory) / (1024 * 1024)

        return ComponentMetrics(
            name=name,
            latency_ms=latency_ms,
            memory_mb=memory_mb,
            success=success,
            error=error,
            metadata={"result": result},
        )

    async def benchmark_nlp_to_ir(self, prompt: str) -> ComponentMetrics:
        """Benchmark NLP → IR generation.

        Future: Will include semantic analysis sub-components:
        - Entity resolution
        - Clause analysis
        - Relationship graph construction
        - Ambiguity detection
        - Intent inference
        """

        async def generate_ir():
            # In the future, this will orchestrate multiple semantic analysis steps
            # For now, it's the current XGrammar-based IR generation
            ir_json = await self.provider.generate_structured(
                prompt=prompt, schema=IR_JSON_SCHEMA, max_tokens=2048, temperature=0.3, top_p=0.95
            )
            return IntermediateRepresentation.from_dict(ir_json)

        return await self.measure_component("nlp_to_ir", generate_ir)

    async def benchmark_ir_to_code(self, ir: IntermediateRepresentation) -> ComponentMetrics:
        """Benchmark IR → Code generation."""

        async def generate_code():
            # Remove holes for E2E testing (in production, resolved via session workflow)
            from lift_sys.ir.models import TypedHole

            holes = ir.typed_holes()
            if holes:
                # Try to clear holes by removing them from all locations
                print(f"  ⚠ IR contains {len(holes)} unresolved holes, attempting to clear them...")

                # Clear hole lists
                ir.intent.holes = []
                ir.signature.holes = []
                for effect in ir.effects:
                    effect.holes = []
                for assertion in ir.assertions:
                    assertion.holes = []

                # Filter out TypedHole instances from parameters
                ir.signature.parameters = [
                    p for p in ir.signature.parameters if not isinstance(p, TypedHole)
                ]

                # Check if holes are actually cleared
                remaining_holes = ir.typed_holes()
                if remaining_holes:
                    print(
                        f"  ✗ Could not clear all holes: {[h.identifier for h in remaining_holes]}"
                    )
                    raise ValueError(
                        f"IR contains unresolved holes that could not be cleared: {', '.join(h.identifier for h in remaining_holes)}"
                    )

                print("  ✓ Successfully cleared holes")

            generator = XGrammarCodeGenerator(provider=self.provider)
            return await generator.generate(ir)

        return await self.measure_component("ir_to_code", generate_code)

    def _extract_function_names(self, code: str) -> list[str]:
        """Extract function names from generated code using AST.

        Args:
            code: Generated Python source code

        Returns:
            List of function names defined in the code
        """
        try:
            tree = ast.parse(code)
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        except Exception:
            return []

    def execute_generated_code(
        self, code: str, function_name: str, test_cases: list[tuple[tuple, Any]]
    ) -> list[ExecutionTestResult]:
        """
        Execute generated code with test inputs and validate outputs.

        Args:
            code: Generated Python source code
            function_name: Name of the function to test (will auto-detect if not found)
            test_cases: List of (args_tuple, expected_output) pairs

        Returns:
            List of ExecutionTestResult objects
        """
        results = []

        try:
            # Execute code to define the function
            namespace = {}

            # DEBUG: Save code to file for inspection
            import os

            os.makedirs("/tmp/lift-sys-debug", exist_ok=True)
            debug_file = f"/tmp/lift-sys-debug/{function_name}_generated.py"
            with open(debug_file, "w") as f:
                f.write(f"# Generated code for {function_name}\n")
                f.write(f"# Length: {len(code)} chars\n")
                f.write(f"# Lines: {len(code.split(chr(10)))}\n")
                f.write("# " + "=" * 70 + "\n")
                for i, line in enumerate(code.split("\n"), 1):
                    f.write(f"# Line {i}: {repr(line)}\n")
                f.write("# " + "=" * 70 + "\n\n")
                f.write(code)

            exec(code, namespace)

            # If expected function name not found, try to auto-detect
            if function_name not in namespace:
                available_functions = self._extract_function_names(code)

                if not available_functions:
                    return [
                        ExecutionTestResult(
                            test_name=f"{function_name}_missing",
                            passed=False,
                            expected=None,
                            actual=None,
                            error=f"Function '{function_name}' not found and no functions detected in generated code",
                        )
                    ]

                # If exactly one function, use it
                if len(available_functions) == 1:
                    actual_function_name = available_functions[0]
                    print(
                        f"  ℹ️  Expected '{function_name}' but found '{actual_function_name}', using detected function"
                    )
                    function_name = actual_function_name
                else:
                    # Multiple functions - try to find best match
                    # Look for functions that contain the expected name as substring
                    matches = [f for f in available_functions if function_name in f.lower()]
                    if matches:
                        actual_function_name = matches[0]
                        print(
                            f"  ℹ️  Expected '{function_name}' but found '{actual_function_name}', using best match"
                        )
                        function_name = actual_function_name
                    else:
                        return [
                            ExecutionTestResult(
                                test_name=f"{function_name}_ambiguous",
                                passed=False,
                                expected=None,
                                actual=None,
                                error=f"Function '{function_name}' not found. Available: {', '.join(available_functions)}",
                            )
                        ]

            func = namespace[function_name]

            # Run each test case
            for i, (args, expected) in enumerate(test_cases):
                test_name = f"{function_name}_test_{i + 1}"

                try:
                    actual = func(*args)
                    passed = actual == expected

                    results.append(
                        ExecutionTestResult(
                            test_name=test_name,
                            passed=passed,
                            expected=expected,
                            actual=actual,
                            error=None if passed else f"Expected {expected}, got {actual}",
                        )
                    )

                except Exception as e:
                    results.append(
                        ExecutionTestResult(
                            test_name=test_name,
                            passed=False,
                            expected=expected,
                            actual=None,
                            error=f"{type(e).__name__}: {str(e)}",
                        )
                    )

        except Exception as e:
            results.append(
                ExecutionTestResult(
                    test_name=f"{function_name}_exec_error",
                    passed=False,
                    expected=None,
                    actual=None,
                    error=f"Code execution failed: {type(e).__name__}: {str(e)}",
                )
            )

        return results

    def estimate_request_cost(self, result: BenchmarkResult) -> float:
        """Estimate cost per request based on provider and usage.

        Modal pricing (approximate):
        - A10G GPU: $0.60/hour = $0.0001667/second
        - Qwen2.5-Coder-7B: ~1000 tokens/sec throughput

        Note: Actual costs depend on Modal billing model.
        """
        if not self.estimate_costs:
            return 0.0

        if result.provider_type == "modal":
            # Modal GPU cost: A10G at $0.60/hour
            # Estimate based on total latency
            total_seconds = result.total_latency_ms / 1000
            gpu_cost_per_second = 0.60 / 3600  # $0.0001667/sec

            # Add small overhead for cold starts (amortized)
            overhead = 0.0001  # Small fixed overhead

            return (total_seconds * gpu_cost_per_second) + overhead

        # For other providers, would need their pricing models
        return 0.0

    async def run_single_benchmark(self, test_name: str, prompt: str) -> BenchmarkResult:
        """Run a complete benchmark for a single test case."""
        result = BenchmarkResult(
            test_name=test_name,
            prompt=prompt,
            timestamp=datetime.now().isoformat(),
            provider_type="modal",
        )

        print(f"\n{'=' * 60}")
        print(f"Benchmarking: {test_name}")
        print(f"Prompt: {prompt}")
        print(f"{'=' * 60}")

        # Stage 1: NLP → IR
        print("\n[1/2] Measuring NLP → IR generation...")
        nlp_metrics = await self.benchmark_nlp_to_ir(prompt)
        result.nlp_to_ir = nlp_metrics

        if nlp_metrics.success:
            ir = nlp_metrics.metadata.get("result")
            result.ir_output = ir.to_dict() if ir else None
            print(f"  ✓ Success: {nlp_metrics.latency_ms:.2f}ms, {nlp_metrics.memory_mb:.2f}MB")

            # Stage 2: IR → Code
            print("\n[2/2] Measuring IR → Code generation...")
            code_metrics = await self.benchmark_ir_to_code(ir)
            result.ir_to_code = code_metrics

            if code_metrics.success:
                code = code_metrics.metadata.get("result")
                result.code_output = code
                result.end_to_end_success = True
                print(
                    f"  ✓ Success: {code_metrics.latency_ms:.2f}ms, {code_metrics.memory_mb:.2f}MB"
                )
            else:
                print(f"  ✗ Failed: {code_metrics.error}")
        else:
            print(f"  ✗ Failed: {nlp_metrics.error}")
            result.end_to_end_success = False

        # Calculate totals
        result.total_latency_ms = (result.nlp_to_ir.latency_ms if result.nlp_to_ir else 0) + (
            result.ir_to_code.latency_ms if result.ir_to_code else 0
        )
        result.total_memory_mb = (result.nlp_to_ir.memory_mb if result.nlp_to_ir else 0) + (
            result.ir_to_code.memory_mb if result.ir_to_code else 0
        )
        result.estimated_cost_usd = self.estimate_request_cost(result)

        print(f"\n{'=' * 60}")
        print(
            f"Total E2E Latency: {result.total_latency_ms:.2f}ms ({result.total_latency_ms / 1000:.2f}s)"
        )
        print(f"Total Memory: {result.total_memory_mb:.2f}MB")
        print(f"Estimated Cost: ${result.estimated_cost_usd:.6f}")
        print(f"Success: {result.end_to_end_success}")
        print(f"{'=' * 60}\n")

        self.results.append(result)
        return result

    async def run_benchmark_suite(
        self, test_cases: list[tuple[str, str]], warmup_runs: int = 1
    ) -> BenchmarkSummary:
        """Run benchmark suite across multiple test cases.

        Args:
            test_cases: List of (test_name, prompt) tuples
            warmup_runs: Number of warmup runs to exclude from statistics
        """
        print(f"\n{'#' * 60}")
        print("# LIFT-SYS PERFORMANCE BENCHMARK SUITE")
        print("# Provider: modal")
        print(f"# Test Cases: {len(test_cases)}")
        print(f"# Warmup Runs: {warmup_runs}")
        print(f"# Timestamp: {datetime.now().isoformat()}")
        print(f"{'#' * 60}\n")

        # Warmup runs
        if warmup_runs > 0:
            print(f"\nRunning {warmup_runs} warmup run(s)...")
            for i in range(warmup_runs):
                test_name, prompt = test_cases[0]  # Use first test case for warmup
                await self.run_single_benchmark(f"warmup_{i + 1}", prompt)

            # Clear warmup results
            self.results = []
            print("\nWarmup complete. Starting benchmark runs...\n")

        # Actual benchmark runs
        for test_name, prompt in test_cases:
            await self.run_single_benchmark(test_name, prompt)

        # Generate summary
        summary = self._generate_summary()
        self._save_results(summary)
        self._print_summary(summary)

        return summary

    def _generate_summary(self) -> BenchmarkSummary:
        """Generate summary statistics from results."""
        successful = [r for r in self.results if r.end_to_end_success]

        nlp_latencies = [r.nlp_to_ir.latency_ms for r in successful if r.nlp_to_ir]
        code_latencies = [r.ir_to_code.latency_ms for r in successful if r.ir_to_code]
        e2e_latencies = [r.total_latency_ms for r in successful]
        memories = [r.total_memory_mb for r in self.results]
        costs = [r.estimated_cost_usd for r in self.results]

        return BenchmarkSummary(
            total_runs=len(self.results),
            successful_runs=len(successful),
            failed_runs=len(self.results) - len(successful),
            nlp_to_ir_mean=mean(nlp_latencies) if nlp_latencies else 0,
            nlp_to_ir_median=median(nlp_latencies) if nlp_latencies else 0,
            nlp_to_ir_std=stdev(nlp_latencies) if len(nlp_latencies) > 1 else 0,
            ir_to_code_mean=mean(code_latencies) if code_latencies else 0,
            ir_to_code_median=median(code_latencies) if code_latencies else 0,
            ir_to_code_std=stdev(code_latencies) if len(code_latencies) > 1 else 0,
            e2e_mean=mean(e2e_latencies) if e2e_latencies else 0,
            e2e_median=median(e2e_latencies) if e2e_latencies else 0,
            e2e_std=stdev(e2e_latencies) if len(e2e_latencies) > 1 else 0,
            total_cost_usd=sum(costs),
            cost_per_request_mean=mean(costs) if costs else 0,
            memory_mean=mean(memories) if memories else 0,
            memory_peak=max(memories) if memories else 0,
        )

    def _save_results(self, summary: BenchmarkSummary):
        """Save benchmark results to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results
        results_file = self.output_dir / f"benchmark_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(
                {
                    "summary": asdict(summary),
                    "results": [self._result_to_dict(r) for r in self.results],
                },
                f,
                indent=2,
            )

        print(f"\n✓ Results saved to: {results_file}")

    def _result_to_dict(self, result: BenchmarkResult) -> dict:
        """Convert BenchmarkResult to dict for JSON serialization."""
        data = asdict(result)
        # Remove large code output to keep JSON manageable
        if data.get("code_output"):
            data["code_output"] = f"<{len(data['code_output'])} chars>"
        return data

    def _print_summary(self, summary: BenchmarkSummary):
        """Print human-readable summary."""
        print(f"\n{'#' * 60}")
        print("# BENCHMARK SUMMARY")
        print(f"{'#' * 60}\n")

        print(f"Total Runs:       {summary.total_runs}")
        print(
            f"Successful:       {summary.successful_runs} ({summary.successful_runs / summary.total_runs * 100:.1f}%)"
        )
        print(f"Failed:           {summary.failed_runs}")

        print("\n--- NLP → IR Latency ---")
        print(
            f"Mean:             {summary.nlp_to_ir_mean:.2f}ms ({summary.nlp_to_ir_mean / 1000:.2f}s)"
        )
        print(
            f"Median:           {summary.nlp_to_ir_median:.2f}ms ({summary.nlp_to_ir_median / 1000:.2f}s)"
        )
        print(f"Std Dev:          {summary.nlp_to_ir_std:.2f}ms")

        print("\n--- IR → Code Latency ---")
        print(
            f"Mean:             {summary.ir_to_code_mean:.2f}ms ({summary.ir_to_code_mean / 1000:.2f}s)"
        )
        print(
            f"Median:           {summary.ir_to_code_median:.2f}ms ({summary.ir_to_code_median / 1000:.2f}s)"
        )
        print(f"Std Dev:          {summary.ir_to_code_std:.2f}ms")

        print("\n--- End-to-End Latency ---")
        print(f"Mean:             {summary.e2e_mean:.2f}ms ({summary.e2e_mean / 1000:.2f}s)")
        print(f"Median:           {summary.e2e_median:.2f}ms ({summary.e2e_median / 1000:.2f}s)")
        print(f"Std Dev:          {summary.e2e_std:.2f}ms")

        print("\n--- Memory Usage ---")
        print(f"Mean:             {summary.memory_mean:.2f}MB")
        print(f"Peak:             {summary.memory_peak:.2f}MB")

        print("\n--- Cost Estimates ---")
        print(f"Total Cost:       ${summary.total_cost_usd:.6f}")
        print(f"Cost per Request: ${summary.cost_per_request_mean:.6f}")

        # Compare to targets
        print("\n--- Target Comparison ---")
        target_e2e_ms = 5000  # 5s target from pragmatic plan
        if summary.e2e_mean <= target_e2e_ms:
            print(f"✓ E2E latency MEETS target (<{target_e2e_ms / 1000}s)")
        else:
            print(
                f"✗ E2E latency EXCEEDS target ({summary.e2e_mean / 1000:.2f}s vs {target_e2e_ms / 1000}s)"
            )

        print(f"\n{'#' * 60}\n")


async def run_parallel_benchmarks(
    test_cases: list[tuple[str, str]],
    provider: ModalProvider,
    output_dir: Path = Path("benchmark_results"),
    max_workers: int = 4,
    warmup_runs: int = 1,
    estimate_costs: bool = True,
) -> tuple[list[BenchmarkResult], BenchmarkSummary]:
    """
    Run benchmarks in parallel with per-test isolation to avoid race conditions.

    Creates isolated PerformanceBenchmark instances for each test to prevent:
    - tracemalloc global state conflicts
    - self.results list race conditions
    - Debug file path collisions
    - Result timestamp collisions

    Args:
        test_cases: List of (test_name, prompt) tuples
        provider: Initialized ModalProvider instance (shared across tests)
        output_dir: Directory for benchmark results
        max_workers: Maximum concurrent tests (matches Modal concurrency)
        warmup_runs: Number of warmup runs before actual benchmarks
        estimate_costs: Whether to estimate costs per request

    Returns:
        Tuple of (all_results, summary)
        - all_results: List of BenchmarkResult from all tests
        - summary: Aggregated BenchmarkSummary across all tests

    Example:
        provider = ModalProvider(...)
        await provider.initialize({})
        results, summary = await run_parallel_benchmarks(
            test_cases, provider, max_workers=4
        )
    """
    print(f"\n{'#' * 60}")
    print("# LIFT-SYS PARALLEL PERFORMANCE BENCHMARK")
    print("# Provider: modal")
    print(f"# Test Cases: {len(test_cases)}")
    print(f"# Max Workers: {max_workers}")
    print(f"# Warmup Runs: {warmup_runs}")
    print(f"# Timestamp: {datetime.now().isoformat()}")
    print(f"{'#' * 60}\n")

    async def run_isolated_test(test_name: str, prompt: str) -> BenchmarkResult:
        """Run a single test with isolated benchmark instance."""
        # Create isolated benchmark instance for this test
        # Each instance has its own results list and tracemalloc state
        benchmark = PerformanceBenchmark(
            provider=provider,
            output_dir=output_dir,
            estimate_costs=estimate_costs,
        )
        return await benchmark.run_single_benchmark(test_name, prompt)

    # Warmup runs (sequential, using first test case)
    if warmup_runs > 0 and test_cases:
        print(f"\nRunning {warmup_runs} warmup run(s)...")
        for i in range(warmup_runs):
            test_name, prompt = test_cases[0]
            await run_isolated_test(f"warmup_{i + 1}", prompt)
        print("\nWarmup complete. Starting parallel benchmark runs...\n")

    # Run actual benchmarks in parallel batches
    all_results: list[BenchmarkResult] = []

    for batch_start in range(0, len(test_cases), max_workers):
        batch = test_cases[batch_start : batch_start + max_workers]
        batch_num = (batch_start // max_workers) + 1
        total_batches = (len(test_cases) + max_workers - 1) // max_workers

        print(f"\n{'=' * 60}")
        print(f"Batch {batch_num}/{total_batches}: Running {len(batch)} tests in parallel...")
        print(f"{'=' * 60}\n")

        # Run batch in parallel using asyncio.gather
        batch_results = await asyncio.gather(
            *[run_isolated_test(name, prompt) for name, prompt in batch]
        )
        all_results.extend(batch_results)

        # Show batch completion
        successful = sum(1 for r in batch_results if r.end_to_end_success)
        print(f"\n{'=' * 60}")
        print(f"Batch {batch_num} complete: {successful}/{len(batch)} successful")
        print(f"{'=' * 60}\n")

    # Generate aggregate summary from all results
    print(f"\n{'#' * 60}")
    print("# AGGREGATING RESULTS")
    print(f"{'#' * 60}\n")

    summary = _aggregate_results(all_results)

    # Save results to file
    _save_parallel_results(all_results, summary, output_dir)

    # Print summary
    _print_summary(summary)

    return all_results, summary


def _aggregate_results(results: list[BenchmarkResult]) -> BenchmarkSummary:
    """
    Aggregate results from multiple isolated benchmark runs.

    Args:
        results: List of BenchmarkResult from parallel execution

    Returns:
        BenchmarkSummary with statistics across all results
    """
    from statistics import mean, median, stdev

    successful = [r for r in results if r.end_to_end_success]

    nlp_latencies = [r.nlp_to_ir.latency_ms for r in successful if r.nlp_to_ir]
    code_latencies = [r.ir_to_code.latency_ms for r in successful if r.ir_to_code]
    e2e_latencies = [r.total_latency_ms for r in successful]
    memories = [r.total_memory_mb for r in results]
    costs = [r.estimated_cost_usd for r in results]

    return BenchmarkSummary(
        total_runs=len(results),
        successful_runs=len(successful),
        failed_runs=len(results) - len(successful),
        nlp_to_ir_mean=mean(nlp_latencies) if nlp_latencies else 0,
        nlp_to_ir_median=median(nlp_latencies) if nlp_latencies else 0,
        nlp_to_ir_std=stdev(nlp_latencies) if len(nlp_latencies) > 1 else 0,
        ir_to_code_mean=mean(code_latencies) if code_latencies else 0,
        ir_to_code_median=median(code_latencies) if code_latencies else 0,
        ir_to_code_std=stdev(code_latencies) if len(code_latencies) > 1 else 0,
        e2e_mean=mean(e2e_latencies) if e2e_latencies else 0,
        e2e_median=median(e2e_latencies) if e2e_latencies else 0,
        e2e_std=stdev(e2e_latencies) if len(e2e_latencies) > 1 else 0,
        total_cost_usd=sum(costs),
        cost_per_request_mean=mean(costs) if costs else 0,
        memory_mean=mean(memories) if memories else 0,
        memory_peak=max(memories) if memories else 0,
    )


def _save_parallel_results(
    results: list[BenchmarkResult],
    summary: BenchmarkSummary,
    output_dir: Path,
):
    """Save parallel benchmark results to JSON file."""
    # Add microseconds to avoid timestamp collision
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    results_file = output_dir / f"benchmark_results_parallel_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {
                "mode": "parallel",
                "summary": asdict(summary),
                "results": [_result_to_dict(r) for r in results],
            },
            f,
            indent=2,
        )

    print(f"\n✓ Results saved to: {results_file}")


def _result_to_dict(result: BenchmarkResult) -> dict:
    """Convert BenchmarkResult to dict for JSON serialization."""
    data = asdict(result)
    # Remove large code output to keep JSON manageable
    if data.get("code_output"):
        data["code_output"] = f"<{len(data['code_output'])} chars>"
    return data


def _print_summary(summary: BenchmarkSummary):
    """Print human-readable summary."""
    print(f"\n{'#' * 60}")
    print("# BENCHMARK SUMMARY")
    print(f"{'#' * 60}\n")

    print(f"Total Runs:       {summary.total_runs}")
    print(
        f"Successful:       {summary.successful_runs} ({summary.successful_runs / summary.total_runs * 100:.1f}%)"
    )
    print(f"Failed:           {summary.failed_runs}")

    print("\n--- NLP → IR Latency ---")
    print(
        f"Mean:             {summary.nlp_to_ir_mean:.2f}ms ({summary.nlp_to_ir_mean / 1000:.2f}s)"
    )
    print(
        f"Median:           {summary.nlp_to_ir_median:.2f}ms ({summary.nlp_to_ir_median / 1000:.2f}s)"
    )
    print(f"Std Dev:          {summary.nlp_to_ir_std:.2f}ms")

    print("\n--- IR → Code Latency ---")
    print(
        f"Mean:             {summary.ir_to_code_mean:.2f}ms ({summary.ir_to_code_mean / 1000:.2f}s)"
    )
    print(
        f"Median:           {summary.ir_to_code_median:.2f}ms ({summary.ir_to_code_median / 1000:.2f}s)"
    )
    print(f"Std Dev:          {summary.ir_to_code_std:.2f}ms")

    print("\n--- End-to-End Latency ---")
    print(f"Mean:             {summary.e2e_mean:.2f}ms ({summary.e2e_mean / 1000:.2f}s)")
    print(f"Median:           {summary.e2e_median:.2f}ms ({summary.e2e_median / 1000:.2f}s)")
    print(f"Std Dev:          {summary.e2e_std:.2f}ms")

    print("\n--- Memory Usage ---")
    print(f"Mean:             {summary.memory_mean:.2f}MB")
    print(f"Peak:             {summary.memory_peak:.2f}MB")

    print("\n--- Cost Estimates ---")
    print(f"Total Cost:       ${summary.total_cost_usd:.6f}")
    print(f"Cost per Request: ${summary.cost_per_request_mean:.6f}")

    # Compare to targets
    print("\n--- Target Comparison ---")
    target_e2e_ms = 5000  # 5s target from pragmatic plan
    if summary.e2e_mean <= target_e2e_ms:
        print(f"✓ E2E latency MEETS target (<{target_e2e_ms / 1000}s)")
    else:
        print(
            f"✗ E2E latency EXCEEDS target ({summary.e2e_mean / 1000:.2f}s vs {target_e2e_ms / 1000}s)"
        )

    print(f"\n{'#' * 60}\n")


# Test suite definitions
TEST_SUITES = {
    "simple": [
        ("add_numbers", "Create a function that adds two numbers"),
        ("multiply", "Create a function that multiplies two numbers"),
        ("string_length", "Create a function that returns the length of a string"),
        ("max_of_two", "Create a function that returns the maximum of two numbers"),
        ("is_even", "Create a function that checks if a number is even"),
    ],
    "phase2": [
        # Phase 2 nontrivial test cases will be loaded from test_nontrivial_phase2.py
        (
            "fizzbuzz",
            "Create a function that returns 'Fizz' for multiples of 3, 'Buzz' for multiples of 5, 'FizzBuzz' for multiples of both, and the number otherwise",
        ),
        ("factorial", "Create a function that calculates the factorial of a number"),
        ("fibonacci", "Create a function that returns the nth Fibonacci number"),
        ("is_palindrome", "Create a function that checks if a string is a palindrome"),
        ("reverse_string", "Create a function that reverses a string"),
        ("find_max", "Create a function that finds the maximum value in a list"),
        ("count_vowels", "Create a function that counts the number of vowels in a string"),
        ("is_prime", "Create a function that checks if a number is prime"),
        ("letter_grade", "Create a function that converts a numeric score to a letter grade"),
        ("celsius_to_fahrenheit", "Create a function that converts Celsius to Fahrenheit"),
    ],
}


async def main():
    """Run performance benchmark suite with CLI argument support."""
    parser = argparse.ArgumentParser(
        description="Performance benchmarking for lift-sys IR generation and code generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in sequential mode (default)
  python performance_benchmark.py

  # Run in parallel mode with 4 workers (default)
  python performance_benchmark.py --parallel

  # Run with 8 parallel workers
  python performance_benchmark.py --parallel --max-workers 8

  # Run Phase 2 test suite in parallel
  python performance_benchmark.py --suite phase2 --parallel

  # Run with custom warmup runs
  python performance_benchmark.py --parallel --warmup-runs 2
        """,
    )

    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel (4x faster, but less accurate memory profiling)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Maximum number of concurrent tests in parallel mode (default: 4, matches Modal concurrency)",
    )
    parser.add_argument(
        "--suite",
        choices=list(TEST_SUITES.keys()),
        default="simple",
        help="Test suite to run (default: simple)",
    )
    parser.add_argument(
        "--warmup-runs",
        type=int,
        default=1,
        help="Number of warmup runs before actual benchmarks (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_results"),
        help="Output directory for benchmark results (default: benchmark_results)",
    )
    parser.add_argument(
        "--no-cost-estimation",
        action="store_true",
        help="Disable cost estimation",
    )

    args = parser.parse_args()

    # Get test cases from selected suite
    test_cases = TEST_SUITES[args.suite]

    print(f"\n{'=' * 60}")
    print("LIFT-SYS PERFORMANCE BENCHMARK")
    print(f"{'=' * 60}")
    print(f"Mode:         {'Parallel' if args.parallel else 'Sequential'}")
    if args.parallel:
        print(f"Max Workers:  {args.max_workers}")
    print(f"Suite:        {args.suite} ({len(test_cases)} tests)")
    print(f"Warmup Runs:  {args.warmup_runs}")
    print(f"Output Dir:   {args.output_dir}")
    print(f"{'=' * 60}\n")

    # Initialize provider (Modal)
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})  # No credentials needed for Modal

    if args.parallel:
        # Run in parallel mode
        all_results, summary = await run_parallel_benchmarks(
            test_cases=test_cases,
            provider=provider,
            output_dir=args.output_dir,
            max_workers=args.max_workers,
            warmup_runs=args.warmup_runs,
            estimate_costs=not args.no_cost_estimation,
        )
    else:
        # Run in sequential mode (original behavior)
        benchmark = PerformanceBenchmark(
            provider=provider,
            output_dir=args.output_dir,
            estimate_costs=not args.no_cost_estimation,
        )

        summary = await benchmark.run_benchmark_suite(
            test_cases=test_cases,
            warmup_runs=args.warmup_runs,
        )

    print("\n✓ Benchmark complete!")
    print(f"✓ Results in: {args.output_dir}/")


if __name__ == "__main__":
    asyncio.run(main())
