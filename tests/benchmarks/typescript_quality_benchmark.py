"""Quality benchmarking for TypeScript code generator.

This module compares generated TypeScript code against human-written baselines
using various quality metrics:

- AST similarity (structural comparison)
- Cyclomatic complexity (code simplicity)
- Line count and token count (conciseness)
- Idiomatic patterns (TypeScript best practices)
- Type annotation coverage
- Modern syntax usage

The goal is to quantify how close generated code is to human-quality code
and identify areas for improvement.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    SigClause,
)

from .typescript_human_baselines import ALL_BASELINES, TypeScriptBaseline


@dataclass
class CodeMetrics:
    """Metrics for a piece of TypeScript code."""

    lines_of_code: int
    token_count: int
    complexity_score: int
    has_tsdoc: bool
    has_type_annotations: bool
    uses_modern_syntax: dict[str, bool]
    syntax_valid: bool


@dataclass
class ComparisonResult:
    """Result of comparing generated code to human baseline."""

    function_name: str
    category: str
    success: bool

    # Generation metadata
    generation_time_ms: float
    attempts_needed: int

    # Code metrics
    generated_metrics: CodeMetrics
    baseline_metrics: CodeMetrics

    # Comparison scores (0-100)
    structure_similarity: float  # How similar is the structure?
    complexity_ratio: float  # Generated complexity / baseline complexity
    conciseness_ratio: float  # Generated LOC / baseline LOC
    quality_score: float  # Overall quality (0-100)

    # Code samples
    generated_code: str
    baseline_code: str

    # Issues found
    issues: list[str] = field(default_factory=list)


@dataclass
class BenchmarkSummary:
    """Summary of all benchmark comparisons."""

    total_functions: int
    successful: int
    failed: int

    # Average metrics
    avg_quality_score: float
    avg_structure_similarity: float
    avg_complexity_ratio: float
    avg_conciseness_ratio: float
    avg_generation_time_ms: float

    # Distribution
    quality_distribution: dict[str, int]  # Bins: excellent, good, fair, poor
    category_scores: dict[str, float]  # Per-category quality scores

    # Common issues
    common_issues: dict[str, int]

    def success_rate(self) -> float:
        """Calculate success rate."""
        return (self.successful / self.total_functions * 100) if self.total_functions > 0 else 0.0


class TypeScriptQualityBenchmark:
    """Benchmark TypeScript generator quality against human baselines."""

    def __init__(
        self,
        generator: TypeScriptGenerator,
        output_dir: Path = Path("benchmark_results"),
    ):
        """
        Initialize benchmark.

        Args:
            generator: TypeScript generator to benchmark
            output_dir: Directory for benchmark results
        """
        self.generator = generator
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.results: list[ComparisonResult] = []

    def _extract_metrics(self, code: str, is_baseline: bool = False) -> CodeMetrics:
        """
        Extract quality metrics from TypeScript code.

        Args:
            code: TypeScript source code
            is_baseline: Whether this is human baseline code

        Returns:
            CodeMetrics with quality indicators
        """
        lines = [line for line in code.split("\n") if line.strip()]
        loc = len(lines)

        # Count tokens (rough approximation)
        tokens = re.findall(r"\w+|[^\w\s]", code)
        token_count = len(tokens)

        # Check for TSDoc
        has_tsdoc = "/**" in code and "@param" in code

        # Check for type annotations
        has_type_annotations = bool(
            re.search(r":\s*(number|string|boolean|Array<|Promise<|Record<)", code)
        )

        # Check modern syntax
        modern_syntax = {
            "const_let": "const " in code or "let " in code,
            "arrow_functions": "=>" in code,
            "async_await": "async " in code or "await " in code,
            "spread_operator": "..." in code,
            "template_literals": "`" in code and "${" in code,
            "destructuring": re.search(r"(const|let)\s+\{.*\}\s*=", code) is not None,
        }

        # Estimate cyclomatic complexity (simplified)
        complexity = self._estimate_complexity(code)

        # Validate syntax
        syntax_valid = self._validate_syntax(code)

        return CodeMetrics(
            lines_of_code=loc,
            token_count=token_count,
            complexity_score=complexity,
            has_tsdoc=has_tsdoc,
            has_type_annotations=has_type_annotations,
            uses_modern_syntax=modern_syntax,
            syntax_valid=syntax_valid,
        )

    def _estimate_complexity(self, code: str) -> int:
        """
        Estimate cyclomatic complexity (simplified).

        Complexity = 1 + number of decision points (if, for, while, case, &&, ||, ?)

        Args:
            code: TypeScript source code

        Returns:
            Estimated complexity score
        """
        complexity = 1

        # Decision points
        complexity += len(re.findall(r"\bif\b", code))
        complexity += len(re.findall(r"\bfor\b", code))
        complexity += len(re.findall(r"\bwhile\b", code))
        complexity += len(re.findall(r"\bcase\b", code))
        complexity += len(re.findall(r"\?", code))  # Ternary
        complexity += len(re.findall(r"&&", code))
        complexity += len(re.findall(r"\|\|", code))

        return complexity

    def _validate_syntax(self, code: str) -> bool:
        """
        Validate TypeScript syntax using tsc.

        Args:
            code: TypeScript source code

        Returns:
            True if syntax is valid
        """
        try:
            # Use generator's validation method
            return self.generator._validate_typescript_syntax(code)
        except Exception:
            return False

    def _compute_structure_similarity(self, generated: str, baseline: str) -> float:
        """
        Compute structural similarity between generated and baseline code.

        Uses a simple token-based approach:
        - Compare token sequences
        - Normalize for whitespace/formatting
        - Score based on common tokens and structure

        Args:
            generated: Generated code
            baseline: Human baseline code

        Returns:
            Similarity score (0-100)
        """

        # Extract tokens (identifiers and operators)
        def tokenize(code: str) -> list[str]:
            # Remove comments and normalize whitespace
            code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
            code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
            # Extract meaningful tokens
            return re.findall(r"\w+|[+\-*/%<>=!&|?:]", code)

        gen_tokens = tokenize(generated)
        base_tokens = tokenize(baseline)

        # Compute Jaccard similarity on token sets
        gen_set = set(gen_tokens)
        base_set = set(base_tokens)

        if not gen_set and not base_set:
            return 100.0

        intersection = len(gen_set & base_set)
        union = len(gen_set | base_set)

        jaccard = intersection / union if union > 0 else 0.0

        # Bonus for similar token sequences (order matters)
        sequence_score = 0.0
        if gen_tokens and base_tokens:
            matches = sum(1 for g, b in zip(gen_tokens, base_tokens, strict=False) if g == b)
            sequence_score = matches / max(len(gen_tokens), len(base_tokens))

        # Weighted combination
        similarity = (0.6 * jaccard + 0.4 * sequence_score) * 100
        return min(100.0, similarity)

    def _compute_quality_score(
        self, gen_metrics: CodeMetrics, base_metrics: CodeMetrics, structure_sim: float
    ) -> float:
        """
        Compute overall quality score (0-100).

        Factors:
        - Structure similarity (40%)
        - Complexity ratio (20%)
        - Has TSDoc (15%)
        - Has type annotations (15%)
        - Modern syntax (10%)

        Args:
            gen_metrics: Generated code metrics
            base_metrics: Baseline code metrics
            structure_sim: Structure similarity score

        Returns:
            Quality score (0-100)
        """
        score = 0.0

        # Structure similarity (40%)
        score += structure_sim * 0.4

        # Complexity ratio (20%) - prefer lower complexity
        if base_metrics.complexity_score > 0:
            complexity_ratio = gen_metrics.complexity_score / base_metrics.complexity_score
            # Penalize if much more complex, but don't reward if simpler
            complexity_score = max(0, 100 - abs(complexity_ratio - 1.0) * 50)
            score += complexity_score * 0.2
        else:
            score += 20  # Neutral if baseline has no complexity

        # TSDoc (15%)
        if gen_metrics.has_tsdoc:
            score += 15

        # Type annotations (15%)
        if gen_metrics.has_type_annotations:
            score += 15

        # Modern syntax (10%)
        modern_count = sum(gen_metrics.uses_modern_syntax.values())
        total_modern = len(gen_metrics.uses_modern_syntax)
        modern_score = (modern_count / total_modern) * 10 if total_modern > 0 else 0
        score += modern_score

        return min(100.0, score)

    async def benchmark_function(
        self, function_name: str, baseline: TypeScriptBaseline, max_retries: int = 3
    ) -> ComparisonResult:
        """
        Benchmark generation for a single function against baseline.

        Args:
            function_name: Name of function to generate
            baseline: Human baseline to compare against
            max_retries: Maximum generation attempts

        Returns:
            ComparisonResult with quality comparison
        """
        print(f"\nBenchmarking: {function_name}")
        print(f"  Category: {baseline.category}")
        print(f"  Description: {baseline.description}")

        # Create IR from baseline metadata
        ir = self._baseline_to_ir(function_name, baseline)

        # Generate code with timing
        start_time = time.time()
        try:
            generated = await self.generator.generate(ir, max_retries=max_retries)
            end_time = time.time()

            gen_code = generated.source_code
            gen_time_ms = (end_time - start_time) * 1000
            attempts = generated.metadata.get("attempts", 1)
            success = True
        except Exception as e:
            end_time = time.time()
            gen_code = ""
            gen_time_ms = (end_time - start_time) * 1000
            attempts = max_retries
            success = False
            print(f"  ✗ Generation failed: {e}")

        # Extract metrics
        gen_metrics = self._extract_metrics(gen_code)
        base_metrics = self._extract_metrics(baseline.code, is_baseline=True)

        # Compute comparisons
        structure_sim = (
            self._compute_structure_similarity(gen_code, baseline.code) if success else 0.0
        )

        complexity_ratio = (
            gen_metrics.complexity_score / base_metrics.complexity_score
            if base_metrics.complexity_score > 0
            else 1.0
        )

        conciseness_ratio = (
            gen_metrics.lines_of_code / base_metrics.lines_of_code
            if base_metrics.lines_of_code > 0
            else 1.0
        )

        quality_score = (
            self._compute_quality_score(gen_metrics, base_metrics, structure_sim)
            if success
            else 0.0
        )

        # Identify issues
        issues = []
        if not gen_metrics.syntax_valid:
            issues.append("Invalid TypeScript syntax")
        if not gen_metrics.has_tsdoc:
            issues.append("Missing TSDoc comments")
        if not gen_metrics.has_type_annotations:
            issues.append("Missing type annotations")
        if complexity_ratio > 1.5:
            issues.append(f"Complexity too high ({complexity_ratio:.1f}x baseline)")
        if conciseness_ratio > 2.0:
            issues.append(f"Code too verbose ({conciseness_ratio:.1f}x baseline)")

        # Create result
        result = ComparisonResult(
            function_name=function_name,
            category=baseline.category,
            success=success,
            generation_time_ms=gen_time_ms,
            attempts_needed=attempts,
            generated_metrics=gen_metrics,
            baseline_metrics=base_metrics,
            structure_similarity=structure_sim,
            complexity_ratio=complexity_ratio,
            conciseness_ratio=conciseness_ratio,
            quality_score=quality_score,
            generated_code=gen_code,
            baseline_code=baseline.code,
            issues=issues,
        )

        # Print summary
        print(f"  ✓ Generated in {gen_time_ms:.1f}ms ({attempts} attempts)")
        print(f"  Quality Score: {quality_score:.1f}/100")
        print(f"  Structure Similarity: {structure_sim:.1f}%")
        print(f"  Complexity Ratio: {complexity_ratio:.2f}x")
        print(f"  Conciseness Ratio: {conciseness_ratio:.2f}x")
        if issues:
            print(f"  Issues: {', '.join(issues)}")

        self.results.append(result)
        return result

    def _baseline_to_ir(
        self, function_name: str, baseline: TypeScriptBaseline
    ) -> IntermediateRepresentation:
        """
        Convert baseline to IR for generation.

        This is a simplified conversion - in practice, the IR would come from
        the test prompts YAML file.

        Args:
            function_name: Function name
            baseline: Human baseline

        Returns:
            IntermediateRepresentation for generation
        """
        # For now, create simple IR based on baseline metadata
        # In production, use test_prompts.yaml data
        return IntermediateRepresentation(
            intent=IntentClause(
                summary=baseline.description,
                rationale="",
            ),
            signature=SigClause(
                name=function_name,
                parameters=[],  # Would be populated from test prompt
                returns="any",  # Would be populated from test prompt
            ),
            assertions=[],
            metadata=Metadata(origin="benchmark", language="typescript"),
        )

    async def run_benchmark_suite(
        self, function_names: list[str] | None = None, max_retries: int = 3
    ) -> BenchmarkSummary:
        """
        Run benchmark suite on multiple functions.

        Args:
            function_names: Optional list of function names to benchmark.
                           If None, benchmarks all available baselines.
            max_retries: Maximum generation attempts per function

        Returns:
            BenchmarkSummary with aggregated results
        """
        # Determine which functions to benchmark
        if function_names is None:
            function_names = list(ALL_BASELINES.keys())

        print(f"\n{'=' * 80}")
        print("TYPESCRIPT GENERATOR QUALITY BENCHMARK")
        print(f"{'=' * 80}")
        print(f"Functions to benchmark: {len(function_names)}")
        print("Comparing against human-written baselines")
        print(f"{'=' * 80}\n")

        # Run benchmarks
        self.results = []
        for func_name in function_names:
            baseline = ALL_BASELINES.get(func_name)
            if baseline is None:
                print(f"⚠ No baseline found for {func_name}, skipping")
                continue

            await self.benchmark_function(func_name, baseline, max_retries)

        # Generate summary
        summary = self._generate_summary()
        self._save_results(summary)
        self._print_summary(summary)

        return summary

    def _generate_summary(self) -> BenchmarkSummary:
        """Generate summary from all results."""
        successful = [r for r in self.results if r.success]

        # Average metrics
        avg_quality = (
            sum(r.quality_score for r in successful) / len(successful) if successful else 0.0
        )
        avg_structure = (
            sum(r.structure_similarity for r in successful) / len(successful) if successful else 0.0
        )
        avg_complexity = (
            sum(r.complexity_ratio for r in successful) / len(successful) if successful else 1.0
        )
        avg_conciseness = (
            sum(r.conciseness_ratio for r in successful) / len(successful) if successful else 1.0
        )
        avg_time = (
            sum(r.generation_time_ms for r in self.results) / len(self.results)
            if self.results
            else 0.0
        )

        # Quality distribution
        quality_dist = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        for r in successful:
            if r.quality_score >= 80:
                quality_dist["excellent"] += 1
            elif r.quality_score >= 60:
                quality_dist["good"] += 1
            elif r.quality_score >= 40:
                quality_dist["fair"] += 1
            else:
                quality_dist["poor"] += 1

        # Category scores
        category_scores: dict[str, list[float]] = {}
        for r in successful:
            if r.category not in category_scores:
                category_scores[r.category] = []
            category_scores[r.category].append(r.quality_score)

        avg_category_scores = {
            cat: sum(scores) / len(scores) for cat, scores in category_scores.items()
        }

        # Common issues
        issue_counts: dict[str, int] = {}
        for r in self.results:
            for issue in r.issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        return BenchmarkSummary(
            total_functions=len(self.results),
            successful=len(successful),
            failed=len(self.results) - len(successful),
            avg_quality_score=avg_quality,
            avg_structure_similarity=avg_structure,
            avg_complexity_ratio=avg_complexity,
            avg_conciseness_ratio=avg_conciseness,
            avg_generation_time_ms=avg_time,
            quality_distribution=quality_dist,
            category_scores=avg_category_scores,
            common_issues=issue_counts,
        )

    def _save_results(self, summary: BenchmarkSummary) -> None:
        """Save benchmark results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed JSON results
        json_file = self.output_dir / f"typescript_quality_benchmark_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(
                {
                    "summary": asdict(summary),
                    "results": [
                        {
                            "function_name": r.function_name,
                            "category": r.category,
                            "success": r.success,
                            "quality_score": r.quality_score,
                            "structure_similarity": r.structure_similarity,
                            "complexity_ratio": r.complexity_ratio,
                            "conciseness_ratio": r.conciseness_ratio,
                            "generation_time_ms": r.generation_time_ms,
                            "attempts_needed": r.attempts_needed,
                            "generated_metrics": asdict(r.generated_metrics),
                            "baseline_metrics": asdict(r.baseline_metrics),
                            "issues": r.issues,
                            "generated_code": r.generated_code,
                            "baseline_code": r.baseline_code,
                        }
                        for r in self.results
                    ],
                },
                f,
                indent=2,
            )

        print(f"\n✓ Detailed results saved to: {json_file}")

    def _print_summary(self, summary: BenchmarkSummary) -> None:
        """Print human-readable summary."""
        print(f"\n{'=' * 80}")
        print("BENCHMARK SUMMARY")
        print(f"{'=' * 80}\n")

        print(f"Total Functions:        {summary.total_functions}")
        print(f"Successful:             {summary.successful} ({summary.success_rate():.1f}%)")
        print(f"Failed:                 {summary.failed}")

        print("\n--- Quality Metrics ---")
        print(f"Avg Quality Score:      {summary.avg_quality_score:.1f}/100")
        print(f"Avg Structure Similarity: {summary.avg_structure_similarity:.1f}%")
        print(f"Avg Complexity Ratio:   {summary.avg_complexity_ratio:.2f}x baseline")
        print(f"Avg Conciseness Ratio:  {summary.avg_conciseness_ratio:.2f}x baseline")

        print("\n--- Performance ---")
        print(f"Avg Generation Time:    {summary.avg_generation_time_ms:.1f}ms")

        print("\n--- Quality Distribution ---")
        for grade, count in summary.quality_distribution.items():
            pct = (count / summary.successful * 100) if summary.successful > 0 else 0
            print(f"  {grade.capitalize():12s}: {count:2d} ({pct:5.1f}%)")

        print("\n--- Scores by Category ---")
        for category, score in sorted(summary.category_scores.items()):
            print(f"  {category:12s}: {score:5.1f}/100")

        if summary.common_issues:
            print("\n--- Common Issues ---")
            for issue, count in sorted(
                summary.common_issues.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                pct = count / summary.total_functions * 100
                print(f"  {issue:40s}: {count:2d} ({pct:5.1f}%)")

        print(f"\n{'=' * 80}\n")


# ============================================================================
# CLI Entry Point
# ============================================================================


async def main():
    """Run TypeScript quality benchmark from command line."""
    import argparse

    from lift_sys.providers.mock import MockProvider

    parser = argparse.ArgumentParser(
        description="Benchmark TypeScript generator quality against human baselines"
    )
    parser.add_argument(
        "--functions",
        nargs="+",
        help="Specific functions to benchmark (default: all)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum generation attempts per function",
    )

    args = parser.parse_args()

    # Initialize generator with mock provider (use real provider in production)
    provider = MockProvider()
    generator = TypeScriptGenerator(provider)

    # Run benchmark
    benchmark = TypeScriptQualityBenchmark(generator, output_dir=args.output_dir)
    await benchmark.run_benchmark_suite(
        function_names=args.functions,
        max_retries=args.max_retries,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
