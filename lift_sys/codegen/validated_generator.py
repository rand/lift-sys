"""
Validated Code Generator - Code generation with execution-based validation.

Wraps XGrammarCodeGenerator with a validation-regeneration loop:
1. Generate test cases from IR
2. Generate code with XGrammar
3. Execute code with test cases
4. If tests fail, regenerate with error feedback
5. Return validated code or best attempt with warnings
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..ir.models import IntermediateRepresentation
from ..validation.constraint_filter import filter_applicable_constraints
from ..validation.ir_interpreter import IRInterpreter
from .execution_validator import ExecutionValidator, ValidationResult
from .models import GeneratedCode
from .test_generator import TestCaseGenerator

if TYPE_CHECKING:
    from .xgrammar_generator import XGrammarCodeGenerator


@dataclass
class GenerationAttempt:
    """A single code generation attempt with validation results."""

    code: str
    """Generated code"""

    validation_result: ValidationResult
    """Results from executing tests"""

    attempt_number: int
    """Which attempt this was (1-indexed)"""

    temperature: float
    """Temperature used for this attempt"""


class ValidatedCodeGenerator:
    """
    Code generator with execution-based validation and regeneration.

    Wraps XGrammarCodeGenerator to add test-based validation:
    - Generates test cases from IR automatically
    - Executes generated code with tests
    - Regenerates on failure with helpful error feedback
    - Returns validated code or best attempt with warnings
    """

    def __init__(
        self,
        base_generator: XGrammarCodeGenerator,
        test_generator: TestCaseGenerator | None = None,
        validator: ExecutionValidator | None = None,
        max_attempts: int = 3,
        skip_ir_validation: bool = False,
    ):
        """
        Initialize validated code generator.

        Args:
            base_generator: XGrammarCodeGenerator to wrap
            test_generator: Test case generator (creates default if None)
            validator: Execution validator (creates default if None)
            max_attempts: Maximum regeneration attempts (default: 3)
            skip_ir_validation: If True, skip IR semantic validation (default: False)
        """
        self.base_generator = base_generator
        self.test_generator = test_generator or TestCaseGenerator()
        self.validator = validator or ExecutionValidator(timeout_seconds=1.0)
        self.max_attempts = max_attempts
        self.skip_ir_validation = skip_ir_validation
        self.ir_interpreter = IRInterpreter()

        # Telemetry tracking
        self.irs_validated = 0
        self.irs_rejected = 0
        self.rejection_categories: dict[str, int] = {}

    async def generate(
        self,
        ir: IntermediateRepresentation,
        temperature: float = 0.3,
        **kwargs,
    ) -> GeneratedCode:
        """
        Generate code with validation-regeneration loop.

        Algorithm:
        0. Validate IR semantics (new Phase 5 step)
        1. Generate test cases from IR
        2. For attempt in 1..max_attempts:
           a. Generate code (increase temperature for diversity)
           b. Validate with test cases
           c. If pass: return code immediately
           d. If fail: regenerate with error feedback
        3. If all attempts fail: return best attempt with warnings

        Args:
            ir: Intermediate representation to translate
            temperature: Base sampling temperature (increases on retries)
            **kwargs: Additional arguments passed to base generator

        Returns:
            GeneratedCode with validated implementation or best attempt
        """
        # Step 0: Validate IR semantics before code generation (Phase 5)
        if not self.skip_ir_validation:
            self.irs_validated += 1
            interpretation = self.ir_interpreter.interpret(ir)

            if interpretation.has_errors():
                # IR validation failed - reject and don't generate code
                self.irs_rejected += 1

                # Track error categories
                for error in interpretation.errors:
                    self.rejection_categories[error.category] = (
                        self.rejection_categories.get(error.category, 0) + 1
                    )

                print(
                    f"  ⚠️  IR validation failed with {len(interpretation.errors)} error(s). "
                    f"Skipping code generation."
                )
                for error in interpretation.errors[:3]:  # Show first 3 errors
                    print(f"     • [{error.category}] {error.message}")

                # Return error stub explaining why generation was skipped
                return GeneratedCode(
                    source_code=f"# IR Validation Failed - Code generation skipped\n"
                    f"# Function: {ir.signature.name}\n"
                    f"# Errors detected: {len(interpretation.errors)}\n"
                    f"#\n"
                    + "\n".join(f"# - {e.message}" for e in interpretation.errors[:5])
                    + "\n\n"
                    f"def {ir.signature.name}({', '.join(p.name for p in ir.signature.parameters)}):\n"
                    f'    raise NotImplementedError("IR validation failed - see comments above")\n',
                    language="python",
                    metadata={
                        "ir_origin": ir.metadata.origin,
                        "generator": "validated_ir_rejected",
                        "ir_validation_errors": len(interpretation.errors),
                        "error_categories": [e.category for e in interpretation.errors],
                    },
                    warnings=[
                        f"IR semantic validation failed with {len(interpretation.errors)} error(s)",
                        *[f"[{e.category}] {e.message}" for e in interpretation.errors[:3]],
                    ],
                )

            # Log warnings but continue (non-blocking)
            if interpretation.has_warnings():
                print(f"  ℹ️  IR validation passed with {len(interpretation.warnings)} warning(s)")
                for warning in interpretation.warnings[:2]:
                    print(f"     • [{warning.category}] {warning.message}")

        # Step 0.5: Filter non-applicable constraints (Phase 3.1)
        if ir.constraints:
            original_count = len(ir.constraints)
            filtered_constraints = filter_applicable_constraints(ir, ir.constraints)
            filtered_count = len(filtered_constraints)

            if filtered_count < original_count:
                print(
                    f"  🔧 Filtered constraints: {original_count} → {filtered_count} "
                    f"({original_count - filtered_count} non-applicable)"
                )

                # Create a modified IR with filtered constraints for code generation
                # Preserve original IR structure but with filtered constraints
                ir = IntermediateRepresentation(
                    intent=ir.intent,
                    signature=ir.signature,
                    effects=ir.effects,
                    assertions=ir.assertions,
                    metadata=ir.metadata,
                    constraints=filtered_constraints,  # Use filtered constraints
                )

        # Step 1: Generate test cases from IR
        test_cases = self.test_generator.generate_test_cases(ir)

        if not test_cases:
            # No tests generated - fall back to base generator
            print("  ℹ️  No test cases generated - using base generator")
            return await self.base_generator.generate(ir, temperature=temperature, **kwargs)

        print(f"  🧪 Generated {len(test_cases)} test cases for validation")

        # Track all attempts to find the best one
        attempts: list[GenerationAttempt] = []
        validation_feedback = ""

        # Step 2: Validation-regeneration loop
        for attempt_num in range(1, self.max_attempts + 1):
            # Calculate temperature for this attempt (increase for diversity)
            attempt_temperature = temperature + ((attempt_num - 1) * 0.15)
            attempt_temperature = min(attempt_temperature, 0.9)  # Cap at 0.9

            print(
                f"\n  🔄 Attempt {attempt_num}/{self.max_attempts} "
                f"(temperature: {attempt_temperature:.2f})"
            )

            # Step 2a: Generate code
            # Inject validation feedback into base generator if available
            if validation_feedback and hasattr(self.base_generator, "_validation_feedback"):
                self.base_generator._validation_feedback = validation_feedback

            try:
                generated = await self.base_generator.generate(
                    ir, temperature=attempt_temperature, **kwargs
                )
            except Exception as e:
                print(f"  ❌ Generation failed: {e}")
                if attempt_num == self.max_attempts:
                    # Last attempt failed - return error
                    return GeneratedCode(
                        source_code=f"# Generation failed after {self.max_attempts} attempts\n"
                        f"# Last error: {e}\n",
                        language="python",
                        metadata={
                            "ir_origin": ir.metadata.origin,
                            "generator": "validated_failed",
                            "error": str(e),
                        },
                        warnings=[f"All {self.max_attempts} generation attempts failed"],
                    )
                continue

            # Step 2b: Validate with test cases
            validation_result = self.validator.validate(
                code=generated.source_code,
                function_name=ir.signature.name,
                test_cases=test_cases,
            )

            # Store this attempt
            attempts.append(
                GenerationAttempt(
                    code=generated.source_code,
                    validation_result=validation_result,
                    attempt_number=attempt_num,
                    temperature=attempt_temperature,
                )
            )

            # Step 2c: Check if tests passed
            if validation_result.passed:
                print(
                    f"  ✅ All {validation_result.total_tests} tests passed! "
                    f"(attempt {attempt_num})"
                )

                # Return validated code with success metadata
                return GeneratedCode(
                    source_code=generated.source_code,
                    language="python",
                    metadata={
                        **generated.metadata,
                        "validated": True,
                        "validation_attempts": attempt_num,
                        "tests_passed": validation_result.total_tests,
                        "total_tests": validation_result.total_tests,
                    },
                    warnings=generated.warnings,
                )

            # Step 2d: Tests failed - prepare feedback for next attempt
            print(
                f"  ❌ {len(validation_result.failed_tests)}/{validation_result.total_tests} "
                f"tests failed"
            )

            # Show first few failures
            for failed in validation_result.failed_tests[:2]:
                print(f"     • {failed.test_case.description}")
                print(f"       {failed.error_message}")

            if attempt_num < self.max_attempts:
                # Prepare detailed feedback for regeneration
                validation_feedback = self._create_regeneration_feedback(
                    validation_result, attempt_num
                )
                print("\n  📝 Regenerating with error feedback...")

        # Step 3: All attempts failed - return best attempt with warnings
        print(f"\n  ⚠️  All {self.max_attempts} attempts failed validation")

        # Find best attempt (fewest failures)
        best_attempt = min(
            attempts, key=lambda a: len(a.validation_result.failed_tests), default=None
        )

        if not best_attempt:
            # No attempts succeeded at all
            return GeneratedCode(
                source_code=f"# All {self.max_attempts} generation attempts failed\n",
                language="python",
                metadata={
                    "ir_origin": ir.metadata.origin,
                    "generator": "validated_failed",
                },
                warnings=["All generation attempts failed"],
            )

        # Return best attempt with detailed warnings
        warnings = [
            f"Code validation failed after {self.max_attempts} attempts",
            f"Best attempt: {best_attempt.attempt_number} "
            f"({best_attempt.validation_result.total_tests - len(best_attempt.validation_result.failed_tests)}"
            f"/{best_attempt.validation_result.total_tests} tests passed)",
        ]

        if best_attempt.validation_result.error_summary:
            warnings.append(f"Remaining issues:\n{best_attempt.validation_result.error_summary}")

        return GeneratedCode(
            source_code=best_attempt.code,
            language="python",
            metadata={
                "ir_origin": ir.metadata.origin,
                "generator": "validated_best_effort",
                "validated": False,
                "validation_attempts": self.max_attempts,
                "tests_passed": best_attempt.validation_result.total_tests
                - len(best_attempt.validation_result.failed_tests),
                "total_tests": best_attempt.validation_result.total_tests,
                "best_attempt": best_attempt.attempt_number,
            },
            warnings=warnings,
        )

    def _create_regeneration_feedback(
        self, validation_result: ValidationResult, attempt_num: int
    ) -> str:
        """
        Create detailed feedback for code regeneration.

        Formats validation failures into actionable guidance for the LLM.

        Args:
            validation_result: Results from validation
            attempt_num: Current attempt number

        Returns:
            Formatted feedback string
        """
        parts = [f"\n\n{'=' * 60}"]
        parts.append(f"VALIDATION FEEDBACK (Attempt {attempt_num})")
        parts.append("=" * 60)

        # Add error summary if available (has categorized guidance)
        if validation_result.error_summary:
            parts.append("\n" + validation_result.error_summary)
        else:
            # Fallback: show raw failures
            parts.append(
                f"\nCode validation failed: {len(validation_result.failed_tests)} test(s) failed"
            )
            for failed in validation_result.failed_tests[:3]:
                parts.append(f"\n  • Test: {failed.test_case.description}")
                parts.append(f"    Input: {failed.test_case.inputs}")
                if failed.test_case.expected_output is not None:
                    parts.append(f"    Expected: {failed.test_case.expected_output}")
                    parts.append(f"    Got: {failed.actual_output}")
                parts.append(f"    Error: {failed.error_message}")

        parts.append("\n" + "=" * 60)
        parts.append("Please fix these issues in the next generation attempt.")
        parts.append("=" * 60 + "\n")

        return "\n".join(parts)

    def get_ir_validation_stats(self) -> dict[str, int | dict[str, int]]:
        """
        Get IR validation telemetry statistics.

        Returns:
            Dictionary with validation statistics including:
            - irs_validated: Total IRs validated
            - irs_rejected: IRs rejected due to errors
            - rejection_rate: Percentage of IRs rejected
            - rejection_categories: Count per error category
        """
        rejection_rate = (
            (self.irs_rejected / self.irs_validated * 100) if self.irs_validated > 0 else 0.0
        )

        return {
            "irs_validated": self.irs_validated,
            "irs_rejected": self.irs_rejected,
            "rejection_rate": round(rejection_rate, 2),
            "rejection_categories": dict(self.rejection_categories),
        }

    def print_ir_validation_report(self) -> None:
        """Print a formatted IR validation statistics report."""
        stats = self.get_ir_validation_stats()

        print("\n" + "=" * 60)
        print("IR Validation Statistics")
        print("=" * 60)
        print(f"Total IRs validated:    {stats['irs_validated']}")
        print(f"IRs rejected:           {stats['irs_rejected']}")
        print(f"Rejection rate:         {stats['rejection_rate']:.1f}%")

        if stats["rejection_categories"]:
            print("\nRejection categories:")
            for category, count in sorted(
                stats["rejection_categories"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  • {category}: {count}")

        print("=" * 60 + "\n")


__all__ = ["ValidatedCodeGenerator", "GenerationAttempt"]
