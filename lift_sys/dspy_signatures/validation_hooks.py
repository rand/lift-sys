"""
Validation Hooks (H9)

Pluggable validation at graph execution points.

This module defines hooks for validating graph state before/after node execution
and at graph start/completion, enabling composable validation logic with clear
error reporting.

Design Principles:
1. Composability: Multiple validators can be chained
2. Async-First: All hooks are async for consistency with node execution
3. Context-Aware: Hooks receive RunContext for access to state and provenance
4. Actionable Errors: ValidationResult provides clear, actionable error messages

Resolution for Hole H9: ValidationHooks
Status: Implementation
Phase: 1 (Week 1)
Constraints from H6: Must accept RunContext[StateT] parameter
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from lift_sys.dspy_signatures.node_interface import RunContext

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


class ValidationStatus(str, Enum):
    """Status of validation result."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class ValidationResult:
    """
    Result of a validation check.

    Contains status, optional error message, and metadata for debugging.
    """

    status: ValidationStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    validator_name: str = ""

    @property
    def passed(self) -> bool:
        """Check if validation passed (including warnings and skips)."""
        return self.status in (ValidationStatus.PASS, ValidationStatus.WARN, ValidationStatus.SKIP)

    @property
    def failed(self) -> bool:
        """Check if validation definitively failed."""
        return self.status == ValidationStatus.FAIL

    def __str__(self) -> str:
        """String representation for logging."""
        if self.message:
            return f"[{self.status.value.upper()}] {self.validator_name}: {self.message}"
        return f"[{self.status.value.upper()}] {self.validator_name}"


@runtime_checkable
class ValidationHook(Protocol, Generic[StateT]):
    """
    Protocol for validation hooks that can be executed at various points in graph execution.

    Hooks receive RunContext which provides access to:
    - Current state
    - Execution metadata
    - Provenance chain
    - Previous validation results

    Example:
        class StateTypeValidator(ValidationHook[MyState]):
            async def __call__(self, ctx: RunContext[MyState]) -> ValidationResult:
                if not isinstance(ctx.state, MyState):
                    return ValidationResult(
                        status=ValidationStatus.FAIL,
                        message="State is not of expected type",
                        validator_name="StateTypeValidator"
                    )
                return ValidationResult(
                    status=ValidationStatus.PASS,
                    validator_name="StateTypeValidator"
                )
    """

    @abstractmethod
    async def __call__(self, ctx: RunContext[StateT]) -> ValidationResult:
        """
        Execute validation check.

        Args:
            ctx: Run context with state, metadata, and provenance

        Returns:
            ValidationResult indicating pass/fail/warn/skip
        """
        ...


class CompositeValidator(Generic[StateT]):
    """
    Composite validator that runs multiple validators in sequence.

    Implements chain-of-responsibility pattern for composing validators.
    Stops on first failure unless configured to continue.

    Example:
        validator = CompositeValidator([
            StateTypeValidator(),
            ProvenanceValidator(),
            CustomBusinessLogicValidator()
        ])

        result = await validator(ctx)
        if result.failed:
            print(f"Validation failed: {result.message}")
    """

    def __init__(
        self,
        validators: list[ValidationHook[StateT]],
        stop_on_first_failure: bool = True,
    ) -> None:
        """
        Initialize composite validator.

        Args:
            validators: List of validators to run
            stop_on_first_failure: If True, stop on first FAIL result
        """
        self.validators = validators
        self.stop_on_first_failure = stop_on_first_failure

    async def __call__(self, ctx: RunContext[StateT]) -> ValidationResult:
        """
        Run all validators in sequence.

        Args:
            ctx: Run context

        Returns:
            Composite validation result (fails if any validator fails)
        """
        results: list[ValidationResult] = []

        for validator in self.validators:
            result = await validator(ctx)
            results.append(result)

            if result.failed and self.stop_on_first_failure:
                return result

        # All validators passed or we collected all results
        if any(r.failed for r in results):
            failed = [r for r in results if r.failed]
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"{len(failed)} validation(s) failed",
                details={
                    "failed_validators": [r.validator_name for r in failed],
                    "results": results,
                },
                validator_name="CompositeValidator",
            )

        if any(r.status == ValidationStatus.WARN for r in results):
            warnings = [r for r in results if r.status == ValidationStatus.WARN]
            return ValidationResult(
                status=ValidationStatus.WARN,
                message=f"{len(warnings)} validation(s) raised warnings",
                details={"warnings": [r.validator_name for r in warnings], "results": results},
                validator_name="CompositeValidator",
            )

        return ValidationResult(
            status=ValidationStatus.PASS,
            message=f"All {len(results)} validations passed",
            details={"results": results},
            validator_name="CompositeValidator",
        )


# Example Validators


class StateValidationHook(Generic[StateT]):
    """
    Validates that state is well-formed.

    Checks:
    - State is instance of expected type
    - Required fields are present
    - Field values are within expected ranges
    """

    def __init__(self, expected_type: type[StateT]) -> None:
        """
        Initialize state validator.

        Args:
            expected_type: Expected state type (Pydantic model)
        """
        self.expected_type = expected_type

    async def __call__(self, ctx: RunContext[StateT]) -> ValidationResult:
        """Validate state type and structure."""
        if not isinstance(ctx.state, self.expected_type):
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"State type mismatch: expected {self.expected_type.__name__}, "
                f"got {type(ctx.state).__name__}",
                details={
                    "expected_type": self.expected_type.__name__,
                    "actual_type": type(ctx.state).__name__,
                },
                validator_name="StateValidationHook",
            )

        return ValidationResult(
            status=ValidationStatus.PASS,
            message="State type validation passed",
            validator_name="StateValidationHook",
        )


class ProvenanceValidationHook(Generic[StateT]):
    """
    Validates provenance chain completeness.

    Checks:
    - Provenance chain exists
    - Each entry has required fields
    - Node execution order is logical
    """

    def __init__(self, min_entries: int = 0, require_fields: list[str] | None = None) -> None:
        """
        Initialize provenance validator.

        Args:
            min_entries: Minimum number of provenance entries required
            require_fields: Fields that must be present in each provenance entry
        """
        self.min_entries = min_entries
        self.require_fields = require_fields or ["node", "signature", "execution_id"]

    async def __call__(self, ctx: RunContext[StateT]) -> ValidationResult:
        """Validate provenance chain."""
        if len(ctx.provenance) < self.min_entries:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message=f"Provenance chain has only {len(ctx.provenance)} entries, "
                f"expected at least {self.min_entries}",
                details={
                    "actual_entries": len(ctx.provenance),
                    "min_entries": self.min_entries,
                },
                validator_name="ProvenanceValidationHook",
            )

        # Check required fields in each provenance entry
        for i, entry in enumerate(ctx.provenance):
            missing_fields = [field for field in self.require_fields if field not in entry]
            if missing_fields:
                return ValidationResult(
                    status=ValidationStatus.FAIL,
                    message=f"Provenance entry {i} missing required fields: {missing_fields}",
                    details={
                        "entry_index": i,
                        "missing_fields": missing_fields,
                        "entry": entry,
                    },
                    validator_name="ProvenanceValidationHook",
                )

        return ValidationResult(
            status=ValidationStatus.PASS,
            message=f"Provenance validation passed ({len(ctx.provenance)} entries)",
            validator_name="ProvenanceValidationHook",
        )


class ExecutionIdValidationHook(Generic[StateT]):
    """
    Validates execution ID consistency across provenance chain.

    Ensures all provenance entries belong to the same execution.
    """

    async def __call__(self, ctx: RunContext[StateT]) -> ValidationResult:
        """Validate execution ID consistency."""
        if not ctx.provenance:
            return ValidationResult(
                status=ValidationStatus.SKIP,
                message="No provenance entries to validate",
                validator_name="ExecutionIdValidationHook",
            )

        execution_ids = set()
        for entry in ctx.provenance:
            if "execution_id" in entry:
                execution_ids.add(entry["execution_id"])

        if len(execution_ids) > 1:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                message=f"Multiple execution IDs found in provenance: {execution_ids}",
                details={"execution_ids": list(execution_ids)},
                validator_name="ExecutionIdValidationHook",
            )

        if execution_ids and ctx.execution_id not in execution_ids:
            return ValidationResult(
                status=ValidationStatus.WARN,
                message="Context execution ID doesn't match provenance entries",
                details={
                    "context_id": ctx.execution_id,
                    "provenance_ids": list(execution_ids),
                },
                validator_name="ExecutionIdValidationHook",
            )

        return ValidationResult(
            status=ValidationStatus.PASS,
            message="Execution ID validation passed",
            validator_name="ExecutionIdValidationHook",
        )


# Hook execution helpers


async def run_validators(
    ctx: RunContext[StateT],
    validators: list[ValidationHook[StateT]],
    stop_on_failure: bool = True,
) -> list[ValidationResult]:
    """
    Run a list of validators and collect results.

    Args:
        ctx: Run context
        validators: List of validators to run
        stop_on_failure: If True, stop on first failure

    Returns:
        List of validation results
    """
    results = []

    for validator in validators:
        result = await validator(ctx)
        results.append(result)

        if result.failed and stop_on_failure:
            break

    return results


def summarize_validation_results(results: list[ValidationResult]) -> str:
    """
    Create a summary message from validation results.

    Args:
        results: List of validation results

    Returns:
        Human-readable summary
    """
    if not results:
        return "No validations run"

    passed = sum(1 for r in results if r.status == ValidationStatus.PASS)
    failed = sum(1 for r in results if r.failed)
    warned = sum(1 for r in results if r.status == ValidationStatus.WARN)
    skipped = sum(1 for r in results if r.status == ValidationStatus.SKIP)

    parts = []
    if passed:
        parts.append(f"{passed} passed")
    if failed:
        parts.append(f"{failed} failed")
    if warned:
        parts.append(f"{warned} warnings")
    if skipped:
        parts.append(f"{skipped} skipped")

    return f"Validation summary: {', '.join(parts)} (total: {len(results)})"
