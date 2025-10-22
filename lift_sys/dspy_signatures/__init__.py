"""
DSPy signatures module for lift-sys.

This module provides the interface between Pydantic AI graph nodes and DSPy signatures,
enabling declarative LLM task specifications with automatic optimization.
"""

from lift_sys.dspy_signatures.caching import (
    CachedParallelExecutor,
    CacheEntry,
    CachingStrategy,
    InMemoryCache,
    NoOpCache,
)
from lift_sys.dspy_signatures.concurrency_model import (
    ANTHROPIC_TIER1_LIMITS,
    MODAL_GPU_LIMITS,
    OPENAI_TIER1_LIMITS,
    PROVIDER_LIMITS_REGISTRY,
    ConcurrencyModel,
    ProviderRateLimits,
    ProviderType,
    get_concurrency_model,
)
from lift_sys.dspy_signatures.error_recovery import (
    ErrorCategory,
    ErrorContext,
    ErrorRecovery,
    RecoveryAction,
    RetryConfig,
)
from lift_sys.dspy_signatures.feature_flags import (
    FeatureFlag,
    FeatureFlagConfig,
    RolloutStrategy,
)
from lift_sys.dspy_signatures.migration_constraints import (
    IncompleteMigrationError,
    MigrationError,
    RollbackError,
    is_migrated_session,
    migrate_prompt_session_to_execution_history,
    rollback_execution_history_to_prompt_session,
    validate_migration,
)
from lift_sys.dspy_signatures.node_interface import (
    BaseNode,
    End,
    NextNode,
    RunContext,
)
from lift_sys.dspy_signatures.parallel_executor import (
    MergeStrategy,
    NodeResult,
    ParallelExecutionError,
    ParallelExecutor,
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
from lift_sys.dspy_signatures.trace_visualization import (
    ExecutionTrace,
    NodeEvent,
    NodeEventType,
    StateSnapshot,
    TraceVisualizationProtocol,
    TraceVisualizationService,
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
    # Parallel execution (H4)
    "ParallelExecutor",
    "NodeResult",
    "MergeStrategy",
    "ParallelExecutionError",
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
    # Resource limits (H14)
    "ResourceLimits",
    "ResourceUsage",
    "ResourceType",
    "ResourceEnforcer",
    "LimitStatus",
    "LimitCheckResult",
    "ResourcePresets",
    "MODAL_DEFAULT_LIMITS",
    # Concurrency model (H16)
    "ConcurrencyModel",
    "ProviderType",
    "ProviderRateLimits",
    "get_concurrency_model",
    "ANTHROPIC_TIER1_LIMITS",
    "OPENAI_TIER1_LIMITS",
    "MODAL_GPU_LIMITS",
    "PROVIDER_LIMITS_REGISTRY",
    # Caching (H3)
    "CachingStrategy",
    "InMemoryCache",
    "NoOpCache",
    "CacheEntry",
    "CachedParallelExecutor",
    # Error recovery (H5)
    "ErrorRecovery",
    "ErrorCategory",
    "RecoveryAction",
    "RetryConfig",
    "ErrorContext",
    # Feature flags (H13)
    "FeatureFlag",
    "FeatureFlagConfig",
    "RolloutStrategy",
    # Migration constraints (H15)
    "migrate_prompt_session_to_execution_history",
    "rollback_execution_history_to_prompt_session",
    "is_migrated_session",
    "validate_migration",
    "MigrationError",
    "IncompleteMigrationError",
    "RollbackError",
    # Trace visualization (H7)
    "TraceVisualizationProtocol",
    "TraceVisualizationService",
    "ExecutionTrace",
    "NodeEvent",
    "NodeEventType",
    "StateSnapshot",
]
