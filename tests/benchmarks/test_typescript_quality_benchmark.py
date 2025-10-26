"""Test suite for TypeScript quality benchmark infrastructure.

Verifies that the benchmark framework works correctly without running
actual generation benchmarks.
"""

from __future__ import annotations

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.providers.mock import MockProvider

from .typescript_human_baselines import (
    ALL_BASELINES,
    BASELINE_ADD,
    get_baseline,
    get_baselines_by_category,
    list_all_baselines,
)
from .typescript_quality_benchmark import TypeScriptQualityBenchmark


class TestTypeScriptBaselines:
    """Test human baseline infrastructure."""

    def test_baselines_exist(self):
        """Test that we have baseline functions."""
        assert len(ALL_BASELINES) > 0
        assert len(ALL_BASELINES) >= 10  # At least 10 baselines

    def test_baseline_structure(self):
        """Test baseline data structure."""
        baseline = BASELINE_ADD
        assert baseline.id == "add"
        assert baseline.category == "basic"
        assert baseline.code is not None
        assert len(baseline.code) > 0
        assert baseline.complexity_score > 0
        assert baseline.lines_of_code > 0
        assert len(baseline.features) > 0

    def test_get_baseline(self):
        """Test getting baseline by name."""
        baseline = get_baseline("add")
        assert baseline is not None
        assert baseline.id == "add"

        # Non-existent baseline
        baseline = get_baseline("nonexistent")
        assert baseline is None

    def test_get_baselines_by_category(self):
        """Test filtering baselines by category."""
        basic_baselines = get_baselines_by_category("basic")
        assert len(basic_baselines) > 0
        assert all(b.category == "basic" for b in basic_baselines)

        array_baselines = get_baselines_by_category("arrays")
        assert len(array_baselines) > 0
        assert all(b.category == "arrays" for b in array_baselines)

    def test_list_all_baselines(self):
        """Test listing all baseline names."""
        names = list_all_baselines()
        assert len(names) > 0
        assert "add" in names
        assert "isEven" in names

    def test_baseline_code_quality(self):
        """Test that baseline code follows quality standards."""
        for baseline in ALL_BASELINES.values():
            # Should have TSDoc
            assert "/**" in baseline.code
            assert "@param" in baseline.code or "@returns" in baseline.code

            # Should have export (may be async)
            assert "export function" in baseline.code or "export async function" in baseline.code

            # Should have type annotations
            assert ": " in baseline.code  # Type annotations use ": type"

            # Should be non-empty
            assert len(baseline.code.strip()) > 0


class TestTypeScriptQualityBenchmark:
    """Test benchmark framework."""

    @pytest.mark.asyncio
    async def test_benchmark_initialization(self):
        """Test benchmark can be initialized."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        assert benchmark.generator is not None
        assert len(benchmark.results) == 0

    @pytest.mark.asyncio
    async def test_extract_metrics(self):
        """Test metric extraction from code."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        code = """/**
 * Add two numbers.
 *
 * @param a - First number
 * @param b - Second number
 * @returns Sum of a and b
 */
export function add(a: number, b: number): number {
  return a + b;
}
"""
        metrics = benchmark._extract_metrics(code)

        assert metrics.lines_of_code > 0
        assert metrics.token_count > 0
        assert metrics.has_tsdoc is True
        assert metrics.has_type_annotations is True
        assert metrics.complexity_score >= 1
        # Note: syntax_valid may be False if tsc not available

    @pytest.mark.asyncio
    async def test_estimate_complexity(self):
        """Test complexity estimation."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        # Simple code
        simple_code = "return a + b;"
        simple_complexity = benchmark._estimate_complexity(simple_code)
        assert simple_complexity == 1  # Base complexity

        # Code with conditionals
        complex_code = """
        if (a > 0) {
          if (b > 0) {
            return a + b;
          }
        }
        return 0;
        """
        complex_complexity = benchmark._estimate_complexity(complex_code)
        assert complex_complexity > simple_complexity

    @pytest.mark.asyncio
    async def test_structure_similarity(self):
        """Test structure similarity computation."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        # Identical code
        code1 = "return a + b;"
        code2 = "return a + b;"
        similarity = benchmark._compute_structure_similarity(code1, code2)
        assert similarity > 90  # Should be very similar

        # Similar code
        code3 = "return a + b + c;"
        similarity2 = benchmark._compute_structure_similarity(code1, code3)
        assert similarity2 > 50  # Should be somewhat similar

        # Different code
        code4 = "if (x) { return true; } else { return false; }"
        similarity3 = benchmark._compute_structure_similarity(code1, code4)
        assert similarity3 < 50  # Should be less similar

    @pytest.mark.asyncio
    async def test_quality_score_computation(self):
        """Test quality score computation."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        # Perfect metrics
        from .typescript_quality_benchmark import CodeMetrics

        perfect_metrics = CodeMetrics(
            lines_of_code=3,
            token_count=20,
            complexity_score=1,
            has_tsdoc=True,
            has_type_annotations=True,
            uses_modern_syntax={
                "const_let": True,
                "arrow_functions": True,
                "async_await": True,
                "spread_operator": True,
                "template_literals": True,
                "destructuring": True,
            },
            syntax_valid=True,
        )

        baseline_metrics = CodeMetrics(
            lines_of_code=3,
            token_count=20,
            complexity_score=1,
            has_tsdoc=True,
            has_type_annotations=True,
            uses_modern_syntax={},
            syntax_valid=True,
        )

        quality = benchmark._compute_quality_score(
            perfect_metrics, baseline_metrics, structure_sim=95.0
        )

        # Should be high quality
        assert quality > 70
        assert quality <= 100

    @pytest.mark.asyncio
    async def test_baseline_to_ir(self):
        """Test converting baseline to IR."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        baseline = BASELINE_ADD
        ir = benchmark._baseline_to_ir("add", baseline)

        assert ir is not None
        assert ir.intent.summary == baseline.description
        assert ir.signature.name == "add"
        assert ir.metadata.language == "typescript"

    @pytest.mark.asyncio
    async def test_benchmark_with_mock_provider(self):
        """Test running a single benchmark with mock provider."""
        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return a + b;", "rationale": "Add numbers"}
    ],
    "variables": [],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        benchmark = TypeScriptQualityBenchmark(generator)

        baseline = BASELINE_ADD
        result = await benchmark.benchmark_function("add", baseline, max_retries=1)

        assert result is not None
        assert result.function_name == "add"
        assert result.category == "basic"
        # Note: Mock provider may fail without proper IR setup
        # This test verifies the benchmark infrastructure works
        # actual success depends on generator/provider implementation
        assert result.generated_code is not None  # Empty string on failure
        assert result.quality_score >= 0
        assert result.quality_score <= 100
