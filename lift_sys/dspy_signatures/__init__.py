"""
DSPy signatures module for lift-sys.

This module provides the interface between Pydantic AI graph nodes and DSPy signatures,
enabling declarative LLM task specifications with automatic optimization.
"""

from lift_sys.dspy_signatures.node_interface import (
    BaseNode,
    End,
    NextNode,
    RunContext,
)
from lift_sys.dspy_signatures.validation_hooks import (
    CompositeValidator,
    ExecutionIdValidationHook,
    ProvenanceValidationHook,
    StateValidationHook,
    ValidationHook,
    ValidationResult,
    ValidationStatus,
    run_validators,
    summarize_validation_results,
)

__all__ = [
    # Node interface
    "BaseNode",
    "RunContext",
    "NextNode",
    "End",
    # Validation hooks
    "ValidationHook",
    "ValidationResult",
    "ValidationStatus",
    "CompositeValidator",
    "StateValidationHook",
    "ProvenanceValidationHook",
    "ExecutionIdValidationHook",
    "run_validators",
    "summarize_validation_results",
]
