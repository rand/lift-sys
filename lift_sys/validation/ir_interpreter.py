"""
IR Interpreter - Semantic Validation Before Code Generation

Combines Effect Chain Analyzer, Semantic Validator, and Logic Error Detector
to validate IR before code generation.

Usage:
    interpreter = IRInterpreter()
    result = interpreter.interpret(ir)

    if result.has_errors():
        # Reject IR, don't generate code
        print(f"Semantic validation failed: {result.errors}")
    else:
        # Proceed with code generation
        code = generator.generate(ir)
"""

from __future__ import annotations

from dataclasses import dataclass

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.validation.effect_analyzer import EffectChainAnalyzer, ExecutionTrace, SemanticIssue
from lift_sys.validation.logic_error_detector import LogicErrorDetector
from lift_sys.validation.semantic_validator import SemanticValidator, ValidationResult


@dataclass
class InterpretationResult:
    """Result of IR interpretation."""

    ir: IntermediateRepresentation
    """The IR that was interpreted"""

    trace: ExecutionTrace
    """Symbolic execution trace"""

    validation: ValidationResult
    """Semantic validation result"""

    all_issues: list[SemanticIssue]
    """All issues (from trace + validation + logic detection)"""

    def has_errors(self) -> bool:
        """Check if any errors were detected."""
        return any(issue.severity == "error" for issue in self.all_issues)

    def has_warnings(self) -> bool:
        """Check if any warnings were detected."""
        return any(issue.severity == "warning" for issue in self.all_issues)

    @property
    def errors(self) -> list[SemanticIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.all_issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[SemanticIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.all_issues if issue.severity == "warning"]

    def __str__(self) -> str:
        status = "❌ FAILED" if self.has_errors() else "✅ PASSED"
        lines = [f"IR Interpretation: {status}"]

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  {error}")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  {warning}")

        # Add summary
        lines.append("\nExecution Trace:")
        lines.append(f"  Values: {len(self.trace.values)}")
        lines.append(
            f"  Operations: {', '.join(self.trace.operations) if self.trace.operations else 'None'}"
        )
        lines.append(f"  Return: {self.trace.return_value or 'None'}")

        return "\n".join(lines)


class IRInterpreter:
    """
    IR Interpreter for semantic validation.

    Combines:
    1. Effect Chain Analyzer - builds symbolic execution trace
    2. Semantic Validator - checks IR consistency
    3. Logic Error Detector - detects common bug patterns

    Use this before code generation to catch semantic errors early.
    """

    def __init__(self):
        """Initialize IR interpreter with all components."""
        self.analyzer = EffectChainAnalyzer()
        self.validator = SemanticValidator()
        self.detector = LogicErrorDetector()

    def interpret(self, ir: IntermediateRepresentation) -> InterpretationResult:
        """
        Interpret IR and validate semantics.

        Args:
            ir: Intermediate representation to interpret

        Returns:
            InterpretationResult with trace, validation, and issues
        """
        # Step 1: Build symbolic execution trace
        trace = self.analyzer.analyze(ir)

        # Step 2: Validate semantics
        validation = self.validator.validate(ir, trace)

        # Step 3: Detect logic error patterns
        logic_issues = self.detector.detect_all_patterns(ir, trace)

        # Combine all issues
        all_issues = list(validation.issues) + logic_issues

        # Remove duplicates (same category + message)
        seen = set()
        unique_issues = []
        for issue in all_issues:
            key = (issue.category, issue.message)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        return InterpretationResult(
            ir=ir,
            trace=trace,
            validation=validation,
            all_issues=unique_issues,
        )

    def should_generate_code(self, result: InterpretationResult) -> bool:
        """
        Determine if code generation should proceed.

        Args:
            result: Interpretation result

        Returns:
            True if code generation should proceed, False otherwise
        """
        # Block code generation if there are errors
        # Warnings are okay - they're non-blocking
        return not result.has_errors()
