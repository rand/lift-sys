"""Quality validation framework for TypeScript code generation.

This module provides tools to validate the quality of generated TypeScript code
using a comprehensive test suite and various quality metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)


@dataclass
class ValidationResult:
    """Result of validating a single test prompt."""

    prompt_id: str
    category: str
    success: bool = False
    generated_code: str | None = None
    generation_time_ms: float = 0.0
    validation_errors: list[str] = field(default_factory=list)
    syntax_valid: bool = False
    has_expected_features: list[str] = field(default_factory=list)
    missing_features: list[str] = field(default_factory=list)
    code_length_lines: int = 0
    attempts_needed: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationSummary:
    """Summary statistics for validation run."""

    total_prompts: int = 0
    successful: int = 0
    failed: int = 0
    syntax_valid: int = 0
    avg_generation_time_ms: float = 0.0
    avg_code_length_lines: float = 0.0
    category_stats: dict[str, dict[str, int]] = field(default_factory=dict)
    feature_coverage: dict[str, int] = field(default_factory=dict)
    error_summary: dict[str, int] = field(default_factory=dict)

    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful / self.total_prompts * 100) if self.total_prompts > 0 else 0.0

    def syntax_valid_rate(self) -> float:
        """Calculate syntax validation rate as percentage."""
        return (self.syntax_valid / self.total_prompts * 100) if self.total_prompts > 0 else 0.0


class TypeScriptQualityValidator:
    """Validates TypeScript code generation quality using test prompts."""

    def __init__(
        self,
        generator: TypeScriptGenerator,
        test_prompts_path: Path | None = None,
    ):
        """
        Initialize validator.

        Args:
            generator: TypeScript code generator to test
            test_prompts_path: Path to YAML file with test prompts
        """
        self.generator = generator
        self.test_prompts_path = test_prompts_path or (
            Path(__file__).parent.parent / "fixtures" / "typescript_test_prompts.yaml"
        )
        self.test_prompts: list[dict[str, Any]] = []
        self.results: list[ValidationResult] = []

    def load_test_prompts(self) -> list[dict[str, Any]]:
        """Load test prompts from YAML file."""
        with open(self.test_prompts_path) as f:
            data = yaml.safe_load(f)
        self.test_prompts = data.get("test_prompts", [])
        return self.test_prompts

    def prompt_to_ir(self, prompt: dict[str, Any]) -> IntermediateRepresentation:
        """Convert a test prompt to IR."""
        # Build signature
        sig_data = prompt["signature"]
        parameters = [
            Parameter(name=p["name"], type_hint=p["type"]) for p in sig_data.get("parameters", [])
        ]
        signature = SigClause(
            name=sig_data["name"],
            parameters=parameters,
            returns=sig_data["returns"],
        )

        # Build intent
        intent = IntentClause(
            summary=prompt["intent"],
            rationale=prompt.get("rationale", ""),
        )

        # Build assertions
        assertions = [
            AssertClause(
                predicate=a["predicate"],
                rationale=a.get("rationale", ""),
            )
            for a in prompt.get("assertions", [])
        ]

        # Build IR
        return IntermediateRepresentation(
            intent=intent,
            signature=signature,
            assertions=assertions,
            metadata=Metadata(
                origin="test_prompt",
                language="typescript",
            ),
        )

    async def validate_prompt(
        self, prompt: dict[str, Any], max_retries: int = 3
    ) -> ValidationResult:
        """
        Validate code generation for a single prompt.

        Args:
            prompt: Test prompt dictionary
            max_retries: Maximum generation attempts

        Returns:
            ValidationResult with metrics and validation status
        """
        prompt_id = prompt.get("id", "unknown")
        category = prompt.get("category", "unknown")
        expected_features = prompt.get("expected_features", [])

        result = ValidationResult(
            prompt_id=prompt_id,
            category=category,
        )

        try:
            # Convert to IR
            ir = self.prompt_to_ir(prompt)

            # Generate code with timing
            start_time = time.time()
            generated = await self.generator.generate(ir, max_retries=max_retries)
            end_time = time.time()

            result.generated_code = generated.source_code
            result.generation_time_ms = (end_time - start_time) * 1000
            result.attempts_needed = generated.metadata.get("attempts", 1)
            result.metadata = generated.metadata

            # Validate syntax
            result.syntax_valid = self._validate_syntax(generated.source_code)

            # Check for expected features
            result.has_expected_features = [
                feat
                for feat in expected_features
                if self._check_feature(generated.source_code, feat)
            ]
            result.missing_features = [
                feat for feat in expected_features if feat not in result.has_expected_features
            ]

            # Code metrics
            result.code_length_lines = len(generated.source_code.split("\n"))

            # Overall success
            result.success = result.syntax_valid and len(result.missing_features) == 0

        except Exception as e:
            result.success = False
            result.validation_errors.append(f"Generation failed: {str(e)}")

        return result

    def _validate_syntax(self, code: str) -> bool:
        """Validate TypeScript syntax using tsc."""
        # Use generator's validation method
        return self.generator._validate_typescript_syntax(code)

    def _check_feature(self, code: str, feature: str) -> bool:
        """Check if generated code contains expected feature."""
        feature_checks = {
            "TSDoc comment": "/**" in code and "@param" in code,
            "Type annotations": ": number" in code or ": string" in code or ": boolean" in code,
            "Return statement": "return" in code,
            "Modulo operator": "%" in code,
            "Boolean return": ": boolean" in code,
            "Conditional logic": "if" in code or "?" in code,
            "Comparison operators": ">" in code or "<" in code or "==" in code or ">=" in code,
            "Negation operator": "-" in code or "!" in code,
            "Multiple conditionals": code.count("if") > 1 or "else" in code,
            "Range checking": ">=" in code and "<=" in code,
            "Array iteration": "for" in code or "forEach" in code,
            "Accumulator pattern": "reduce" in code or "sum" in code,
            "Array<number> type": "Array<number>" in code,
            "Array traversal": "for" in code or ".forEach" in code or ".map" in code,
            "Array.filter method": ".filter(" in code,
            "Arrow function": "=>" in code,
            "Array.map method": ".map(" in code,
            "Array.includes or iteration": ".includes(" in code or "for" in code,
            "Array reversal": ".reverse(" in code,
            "Array<string> type": "Array<string>" in code or "string[]" in code,
            "Promise<void> type": "Promise<void>" in code,
            "setTimeout usage": "setTimeout" in code,
            "async/await": "async" in code or "await" in code,
            "Promise<Record<string, any>>": "Promise<Record<string, any>>" in code
            or "Promise<any>" in code,
            "fetch API": "fetch(" in code,
            "async function": "async function" in code or "async " in code,
            "Promise handling": "Promise" in code or "await" in code,
            "Loop with async/await": ("for" in code or "while" in code) and "await" in code,
            "Error handling": "try" in code or "catch" in code,
            "Promise.all": "Promise.all" in code,
            "Array of promises": "Promise" in code and "Array" in code,
            "Object spread operator": "..." in code,
            "Record<string, any>": "Record<string, any>" in code,
            "Object property access": "[" in code and "]" in code or "." in code,
            "Object construction": "{" in code and "}" in code,
            "in operator or hasOwnProperty": " in " in code or "hasOwnProperty" in code,
            "Object.keys": "Object.keys" in code,
            "Array<string> return": "Array<string>" in code or "string[]" in code,
            "String slicing": ".slice(" in code or ".substring(" in code,
            "toUpperCase method": ".toUpperCase(" in code,
            "String iteration": "for" in code or ".split" in code,
            "Counter accumulation": "++" in code or "+= " in code,
            "Array conversion": ".split(" in code or "Array.from" in code,
            "reverse() method": ".reverse(" in code,
            "join() method": ".join(" in code,
            "String comparison": "==" in code or "===" in code,
            "String reversal": ".reverse(" in code,
            "String splitting": ".split(" in code,
            "Array mapping": ".map(" in code,
            "String joining": ".join(" in code,
            "Loop or recursion": "for" in code
            or "while" in code
            or (prompt_id := "factorial")
            and "factorial(" in code,
            "Multiplication": "*" in code,
            "Loop with early exit": "break" in code or "return" in code,
            "Division and modulo": "/" in code or "%" in code,
            "Array reduce": ".reduce(" in code,
            "Division": "/" in code,
            "number type": "number" in code,
            "Regex or string methods": "test(" in code or ".match(" in code or ".includes(" in code,
            "Logical AND": "&&" in code,
            "String length check": ".length" in code,
            "Regex or character checks": "test(" in code or ".match(" in code,
            "Multiple conditions": "&&" in code or "||" in code,
        }

        return feature_checks.get(feature, False)

    async def validate_all(
        self, max_prompts: int | None = None, max_retries: int = 3
    ) -> ValidationSummary:
        """
        Validate all test prompts.

        Args:
            max_prompts: Optional limit on number of prompts to test
            max_retries: Maximum generation attempts per prompt

        Returns:
            ValidationSummary with aggregated statistics
        """
        if not self.test_prompts:
            self.load_test_prompts()

        prompts_to_test = self.test_prompts[:max_prompts] if max_prompts else self.test_prompts

        print(f"Validating {len(prompts_to_test)} test prompts...")

        self.results = []
        for i, prompt in enumerate(prompts_to_test):
            print(f"  [{i + 1}/{len(prompts_to_test)}] Testing {prompt['id']}...", end=" ")
            result = await self.validate_prompt(prompt, max_retries=max_retries)
            self.results.append(result)

            status = "✓" if result.success else "✗"
            print(f"{status} ({result.generation_time_ms:.1f}ms)")

        return self._compute_summary()

    def _compute_summary(self) -> ValidationSummary:
        """Compute summary statistics from results."""
        summary = ValidationSummary(total_prompts=len(self.results))

        for result in self.results:
            # Success counts
            if result.success:
                summary.successful += 1
            else:
                summary.failed += 1

            if result.syntax_valid:
                summary.syntax_valid += 1

            # Category stats
            if result.category not in summary.category_stats:
                summary.category_stats[result.category] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                }
            summary.category_stats[result.category]["total"] += 1
            if result.success:
                summary.category_stats[result.category]["successful"] += 1
            else:
                summary.category_stats[result.category]["failed"] += 1

            # Feature coverage
            for feature in result.has_expected_features:
                summary.feature_coverage[feature] = summary.feature_coverage.get(feature, 0) + 1

            # Error summary
            for error in result.validation_errors:
                error_type = error.split(":")[0]
                summary.error_summary[error_type] = summary.error_summary.get(error_type, 0) + 1

        # Averages
        if self.results:
            summary.avg_generation_time_ms = sum(r.generation_time_ms for r in self.results) / len(
                self.results
            )
            summary.avg_code_length_lines = sum(r.code_length_lines for r in self.results) / len(
                self.results
            )

        return summary

    def print_summary(self, summary: ValidationSummary) -> None:
        """Print validation summary to console."""
        print("\n" + "=" * 80)
        print("TYPESCRIPT GENERATION QUALITY VALIDATION SUMMARY")
        print("=" * 80)

        print("\nOverall Results:")
        print(f"  Total Prompts:    {summary.total_prompts}")
        print(f"  Successful:       {summary.successful} ({summary.success_rate():.1f}%)")
        print(f"  Failed:           {summary.failed}")
        print(f"  Syntax Valid:     {summary.syntax_valid} ({summary.syntax_valid_rate():.1f}%)")

        print("\nPerformance:")
        print(f"  Avg Generation Time: {summary.avg_generation_time_ms:.1f} ms")
        print(f"  Avg Code Length:     {summary.avg_code_length_lines:.1f} lines")

        print("\nResults by Category:")
        for category, stats in sorted(summary.category_stats.items()):
            success_rate = (
                (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            )
            print(
                f"  {category:12s}: {stats['successful']:2d}/{stats['total']:2d} ({success_rate:5.1f}%)"
            )

        if summary.error_summary:
            print("\nError Summary:")
            for error_type, count in sorted(
                summary.error_summary.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {error_type}: {count}")

        print("\n" + "=" * 80)

    def export_results(self, output_path: Path) -> None:
        """Export detailed results to JSON file."""
        import json

        data = {
            "results": [
                {
                    "prompt_id": r.prompt_id,
                    "category": r.category,
                    "success": r.success,
                    "syntax_valid": r.syntax_valid,
                    "generation_time_ms": r.generation_time_ms,
                    "code_length_lines": r.code_length_lines,
                    "attempts_needed": r.attempts_needed,
                    "has_expected_features": r.has_expected_features,
                    "missing_features": r.missing_features,
                    "validation_errors": r.validation_errors,
                    "generated_code": r.generated_code,
                }
                for r in self.results
            ]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\nDetailed results exported to: {output_path}")
