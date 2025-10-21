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
from lift_sys.dspy_signatures.resource_limits import (
    MODAL_DEFAULT_LIMITS,
    LimitCheckResult,
    LimitStatus,
    ResourceEnforcer,
    ResourceLimits,
    ResourcePresets,
    ResourceType,
    ResourceUsage,
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
    # Resource limits
    "ResourceLimits",
    "ResourceUsage",
    "ResourceType",
    "ResourceEnforcer",
    "LimitStatus",
    "LimitCheckResult",
    "ResourcePresets",
    "MODAL_DEFAULT_LIMITS",
]
