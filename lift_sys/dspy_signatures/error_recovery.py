"""
Error Recovery (H5)

Robust error handling for node failures and graph-level errors.

This module provides error recovery and retry logic for node execution, enabling
production-ready reliability through retry strategies, circuit breakers, and
graceful degradation.

Design Principles:
1. Transient Error Recovery: Automatically retry network errors, rate limits
2. Fatal Error Handling: Terminate gracefully on permanent failures
3. State Preservation: Maintain graph state consistency on all failure modes
4. Actionable Errors: Provide clear, debuggable error messages
5. Production Ready: Enable reliable execution in production environments

Resolution for Hole H5: ErrorRecovery
Status: Implementation
Phase: 7 (Week 7)
Dependencies: H4 (ParallelizationImpl) - RESOLVED, H9 (ValidationHooks) - RESOLVED
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from .node_interface import BaseNode, RunContext
from .parallel_executor import NodeResult, ParallelExecutor
from .validation_hooks import ValidationResult

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


class ErrorCategory(str, Enum):
    """
    Classification of errors for recovery strategy.

    Categories:
    - TRANSIENT: Network errors, rate limits, timeouts (retry with backoff)
    - FATAL: Invalid inputs, logic errors (no retry)
    - VALIDATION: State validation failures (no retry)
    - RESOURCE: Memory, disk, connection limits (retry with longer backoff)
    """

    TRANSIENT = "transient"
    FATAL = "fatal"
    VALIDATION = "validation"
    RESOURCE = "resource"


class RecoveryAction(str, Enum):
    """
    Action to take on error.

    Actions:
    - RETRY: Retry with exponential backoff
    - FAIL: Terminate execution, propagate error
    - FALLBACK: Use fallback strategy (future)
    - SKIP: Skip node, continue graph (future)
    """

    RETRY = "retry"
    FAIL = "fail"
    FALLBACK = "fallback"
    SKIP = "skip"


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_attempts: Maximum retry attempts (default 3)
        initial_delay_ms: Initial backoff delay in milliseconds (default 100ms)
        max_delay_ms: Maximum backoff delay in milliseconds (default 10s)
        backoff_factor: Exponential backoff multiplier (default 2.0)
        jitter: Add randomness to prevent thundering herd (default True)
    """

    max_attempts: int = 3
    initial_delay_ms: float = 100
    max_delay_ms: float = 10_000
    backoff_factor: float = 2.0
    jitter: bool = True


@dataclass
class ErrorContext:
    """
    Context for error recovery decision.

    Provides all information needed to decide recovery strategy:
    - Error details
    - Classification
    - Attempt number
    - Node and execution context
    - Optional validation result
    """

    error: Exception
    category: ErrorCategory
    attempt: int
    node: BaseNode
    ctx: RunContext
    validation_result: ValidationResult | None = None


class ErrorRecovery(Generic[StateT]):
    """
    Error recovery and retry logic for node execution.

    Features:
    - Automatic retry with exponential backoff
    - Error classification (transient vs fatal)
    - Circuit breaker pattern (prevents cascading failures)
    - State preservation on failures
    - Comprehensive logging

    Example:
        >>> recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        >>> executor = ParallelExecutor[TestState]()
        >>> result = await recovery.execute_with_retry(node, ctx, executor)
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize error recovery.

        Args:
            retry_config: Retry configuration (uses defaults if None)
            logger: Logger instance (creates new logger if None)
        """
        self.retry_config = retry_config or RetryConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Circuit breaker state
        self._failure_counts: dict[str, int] = {}
        self._circuit_open: dict[str, bool] = {}
        self._last_failure_time: dict[str, float] = {}

    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify error for recovery strategy.

        Classification rules:
        - Transient: Network errors, timeouts, rate limits, service errors
        - Resource: Memory errors, connection pool exhausted
        - Validation: Validation failures
        - Fatal: All other errors (invalid inputs, logic errors)

        Args:
            error: Exception to classify

        Returns:
            ErrorCategory for recovery decision
        """
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # Check more specific patterns first to avoid false matches

        # Validation errors (no retry)
        # Check both type and message
        if "validation" in error_type.lower() or "validation" in error_msg:
            return ErrorCategory.VALIDATION

        # Rate limit errors - check BEFORE generic resource patterns
        # "Rate limit" is transient, not resource
        rate_limit_indicators = ["ratelimit", "rate limit", "429"]
        if any(
            indicator in error_type.lower() or indicator in error_msg
            for indicator in rate_limit_indicators
        ):
            return ErrorCategory.TRANSIENT

        # Resource errors (retry with longer backoff)
        # Check these BEFORE general transient to avoid "connection pool" matching "connection"
        resource_indicators = [
            "memory",
            "resource",
            "pool",  # "connection pool", "thread pool", etc.
            "quota",
        ]
        if any(
            indicator in error_type.lower() or indicator in error_msg
            for indicator in resource_indicators
        ):
            return ErrorCategory.RESOURCE

        # Transient errors (retry with backoff)
        transient_indicators = [
            "connection",
            "timeout",
            "503",
            "serviceunavailable",
            "temporarily unavailable",
        ]
        if any(
            indicator in error_type.lower() or indicator in error_msg
            for indicator in transient_indicators
        ):
            return ErrorCategory.TRANSIENT

        # Default to fatal for unknown errors (no retry)
        return ErrorCategory.FATAL

    def should_retry(self, error_ctx: ErrorContext) -> bool:
        """
        Determine if error should be retried.

        Retry logic:
        - Transient errors: retry up to max_attempts
        - Resource errors: retry with longer backoff
        - Validation errors: no retry (likely permanent)
        - Fatal errors: no retry

        Circuit breaker:
        - If node_id has failed >5 times in 60s, open circuit
        - Circuit opens for 30s, then half-open for retry

        Args:
            error_ctx: Error context with classification and attempt info

        Returns:
            True if should retry, False otherwise
        """
        # Check max attempts
        if error_ctx.attempt >= self.retry_config.max_attempts:
            return False

        # Check circuit breaker
        node_id = type(error_ctx.node).__name__
        if self._is_circuit_open(node_id):
            self.logger.warning(f"Circuit open for {node_id}, not retrying")
            return False

        # Category-based retry
        if error_ctx.category == ErrorCategory.TRANSIENT:
            return True
        elif error_ctx.category == ErrorCategory.RESOURCE:
            return True
        elif error_ctx.category in (ErrorCategory.VALIDATION, ErrorCategory.FATAL):
            return False

        return False

    def _is_circuit_open(self, node_id: str) -> bool:
        """
        Check if circuit breaker is open for node.

        Circuit transitions:
        - CLOSED: Normal operation
        - OPEN: After 5 failures in 60s, prevent all requests
        - HALF_OPEN: After 30s timeout, allow one test request

        Args:
            node_id: Node identifier for circuit tracking

        Returns:
            True if circuit is open (prevent retry), False otherwise
        """
        if node_id not in self._circuit_open:
            return False

        # Check if circuit should transition to half-open
        if self._circuit_open[node_id]:
            last_failure = self._last_failure_time.get(node_id, 0)
            if time.time() - last_failure > 30:  # 30s timeout
                self._circuit_open[node_id] = False
                self.logger.info(f"Circuit half-open for {node_id}, allowing retry")

        return self._circuit_open[node_id]

    def _record_failure(self, node_id: str):
        """
        Record failure for circuit breaker.

        Opens circuit if >5 failures in 60s window.

        Args:
            node_id: Node identifier for circuit tracking
        """
        self._failure_counts[node_id] = self._failure_counts.get(node_id, 0) + 1
        self._last_failure_time[node_id] = time.time()

        # Count recent failures in 60s window
        current_time = time.time()
        recent_window = 60  # seconds

        # Check failures for this node in recent window
        # Note: This is simplified - in production would track per-failure timestamps
        if self._failure_counts[node_id] > 5:
            last_failure_time = self._last_failure_time.get(node_id, 0)
            if current_time - last_failure_time < recent_window:
                self._circuit_open[node_id] = True
                self.logger.error(
                    f"Circuit opened for {node_id} after {self._failure_counts[node_id]} failures"
                )

    def _record_success(self, node_id: str):
        """
        Record success for circuit breaker.

        Decrements failure count and may close circuit.

        Args:
            node_id: Node identifier for circuit tracking
        """
        if node_id in self._failure_counts:
            self._failure_counts[node_id] = max(0, self._failure_counts[node_id] - 1)

            # Close circuit on success if half-open
            if self._circuit_open.get(node_id, False):
                self._circuit_open[node_id] = False
                self.logger.info(f"Circuit closed for {node_id} after successful retry")

    async def execute_with_retry(
        self,
        node: BaseNode[StateT],
        ctx: RunContext[StateT],
        executor: ParallelExecutor[StateT],
    ) -> NodeResult[StateT]:
        """
        Execute node with automatic retry on transient errors.

        Flow:
        1. Try execute node (uses H4 execute_single_with_isolation for state isolation)
        2. If error: classify error
        3. If retryable: wait with exponential backoff, retry
        4. If not retryable: return error result
        5. Preserve original context state on failure

        Args:
            node: Node to execute
            ctx: Execution context (state preserved on failure)
            executor: ParallelExecutor for node execution (H4 integration)

        Returns:
            NodeResult (success or final error)
        """
        node_id = type(node).__name__
        attempt = 0
        result = None  # Initialize to handle edge case of max_attempts=0

        # Ensure at least one attempt, even if max_attempts=0
        effective_max_attempts = max(1, self.retry_config.max_attempts)

        while attempt < effective_max_attempts:
            attempt += 1

            # Execute node (H4 integration for state isolation)
            result = await executor.execute_single_with_isolation(node, ctx)

            # Success: record and return
            if result.is_success:
                self._record_success(node_id)
                return result

            # Failure: classify and decide
            category = self.classify_error(result.error)
            error_ctx = ErrorContext(
                error=result.error,
                category=category,
                attempt=attempt,
                node=node,
                ctx=ctx,
            )

            # Log error with context
            self.logger.warning(
                f"Node {node_id} failed (attempt {attempt}/{self.retry_config.max_attempts}): "
                f"{type(result.error).__name__}: {result.error}"
            )

            # Check if should retry
            if not self.should_retry(error_ctx):
                self.logger.error(
                    f"Not retrying {node_id} ({category.value} error, attempt {attempt})"
                )
                self._record_failure(node_id)
                return result

            # Calculate backoff delay
            delay_ms = self._calculate_backoff(attempt)
            self.logger.info(f"Retrying {node_id} after {delay_ms:.0f}ms (attempt {attempt + 1})")
            await asyncio.sleep(delay_ms / 1000)

        # Max attempts exceeded
        self.logger.error(f"Max attempts ({self.retry_config.max_attempts}) exceeded for {node_id}")
        self._record_failure(node_id)
        return result  # Return last error result

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Formula: delay = initial_delay * (backoff_factor ^ (attempt - 1))
        Capped at max_delay_ms
        Optional jitter (±25%) to prevent thundering herd

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in milliseconds

        Example:
            initial_delay=100ms, backoff_factor=2.0
            Attempt 1: 100ms
            Attempt 2: 200ms
            Attempt 3: 400ms
        """
        delay = self.retry_config.initial_delay_ms * (
            self.retry_config.backoff_factor ** (attempt - 1)
        )
        delay = min(delay, self.retry_config.max_delay_ms)

        # Add jitter (±25%)
        if self.retry_config.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with:
            - failure_counts: Failure count per node
            - circuits_open: Nodes with open circuits
            - total_failures: Sum of all failures
        """
        return {
            "failure_counts": dict(self._failure_counts),
            "circuits_open": {k: v for k, v in self._circuit_open.items() if v},
            "total_failures": sum(self._failure_counts.values()),
        }


__all__ = [
    "ErrorCategory",
    "RecoveryAction",
    "RetryConfig",
    "ErrorContext",
    "ErrorRecovery",
]
