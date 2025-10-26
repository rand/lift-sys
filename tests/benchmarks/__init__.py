"""Benchmarking suite for lift-sys code generators.

This package provides comprehensive benchmarking tools for evaluating
code generation quality by comparing generated code against human-written
baselines.

Available benchmarks:
- TypeScript quality benchmark: Compare TypeScript generator output to human code
- Python quality benchmark: (future) Compare Python generator output
- Performance benchmarks: Measure generation speed and resource usage

Usage:
    from tests.benchmarks import TypeScriptQualityBenchmark

    benchmark = TypeScriptQualityBenchmark(generator)
    summary = await benchmark.run_benchmark_suite()
"""

from .typescript_human_baselines import (
    ALL_BASELINES,
    TypeScriptBaseline,
    get_baseline,
    get_baselines_by_category,
    list_all_baselines,
)
from .typescript_quality_benchmark import (
    BenchmarkSummary,
    CodeMetrics,
    ComparisonResult,
    TypeScriptQualityBenchmark,
)

__all__ = [
    # Baselines
    "TypeScriptBaseline",
    "ALL_BASELINES",
    "get_baseline",
    "get_baselines_by_category",
    "list_all_baselines",
    # Benchmark
    "TypeScriptQualityBenchmark",
    "ComparisonResult",
    "CodeMetrics",
    "BenchmarkSummary",
]
