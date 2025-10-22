# H5: ErrorRecovery - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 7 (Week 7)

---

## Overview

H5 (ErrorRecovery) defines robust error handling for node failures and graph-level errors, enabling production-ready reliability through retry strategies, circuit breakers, and graceful degradation.

## Goals

1. **Transient Error Recovery**: Automatically retry transient errors (network, rate limits)
2. **Fatal Error Handling**: Terminate gracefully on permanent failures
3. **State Preservation**: Maintain graph state consistency on all failure modes
4. **Actionable Errors**: Provide clear, debuggable error messages
5. **Production Ready**: Enable reliable execution in production environments

## Context

### Dependencies

**Blocked By**:
- ✅ H9 (ValidationHooks) - **RESOLVED**: Provides validation framework for error detection
- ✅ H4 (ParallelizationImpl) - **RESOLVED**: Provides NodeResult with error tracking

**Blocks**:
- Production readiness
- Reliable execution

**Related**:
- H4 ParallelExecutor: Captures errors in NodeResult
- H9 ValidationHooks: Detects invalid states
- H3 CachingStrategy: Cache hits avoid errors
- H16 ConcurrencyModel: Rate limit errors need retry

### Existing Components

From H4 (ParallelExecutor):
```python
@dataclass
class NodeResult(Generic[StateT]):
    node: BaseNode[StateT]
    next_node: BaseNode[StateT] | End
    context: RunContext[StateT]
    execution_time_ms: float
    error: Exception | None = None  # Error captured here

    @property
    def is_success(self) -> bool:
        return self.error is None
```

From H9 (ValidationHooks):
```python
@dataclass
class ValidationResult:
    status: ValidationStatus
    message: str
    details: dict[str, Any]
    validator_name: str
```

## Design

### Core Abstraction: ErrorRecovery

```python
from enum import Enum
from dataclasses import dataclass
import logging
import asyncio
import time

class ErrorCategory(str, Enum):
    """Classification of errors for recovery strategy."""
    TRANSIENT = "transient"      # Network errors, rate limits, timeouts
    FATAL = "fatal"              # Invalid inputs, logic errors
    VALIDATION = "validation"    # State validation failures
    RESOURCE = "resource"        # Memory, disk, connection limits

class RecoveryAction(str, Enum):
    """Action to take on error."""
    RETRY = "retry"              # Retry with backoff
    FAIL = "fail"                # Terminate execution
    FALLBACK = "fallback"        # Use fallback strategy
    SKIP = "skip"                # Skip node, continue graph

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay_ms: float = 100
    max_delay_ms: float = 10_000
    backoff_factor: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd

@dataclass
class ErrorContext:
    """Context for error recovery decision."""
    error: Exception
    category: ErrorCategory
    attempt: int
    node: BaseNode
    ctx: RunContext
    validation_result: ValidationResult | None = None

class ErrorRecovery:
    """
    Error recovery and retry logic for node execution.

    Features:
    - Automatic retry with exponential backoff
    - Error classification (transient vs fatal)
    - Circuit breaker pattern
    - State preservation on failures
    - Comprehensive logging

    Example:
        >>> recovery = ErrorRecovery(retry_config=RetryConfig(max_attempts=3))
        >>> result = await recovery.execute_with_retry(node, ctx)
    """

    def __init__(
        self,
        retry_config: RetryConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        self.retry_config = retry_config or RetryConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Circuit breaker state
        self._failure_counts: dict[str, int] = {}
        self._circuit_open: dict[str, bool] = {}
        self._last_failure_time: dict[str, float] = {}

    def classify_error(self, error: Exception) -> ErrorCategory:
        """
        Classify error for recovery strategy.

        Transient errors:
        - Network errors (ConnectionError, TimeoutError)
        - Rate limit errors (429, RateLimitError)
        - Temporary service errors (503, ServiceUnavailable)

        Fatal errors:
        - Invalid inputs (ValueError, TypeError)
        - Logic errors (AssertionError, RuntimeError)
        - Authentication errors (401, 403)

        Validation errors:
        - State validation failures
        - Constraint violations

        Resource errors:
        - Memory errors (MemoryError)
        - Connection pool exhausted
        - Disk full
        """
        error_type = type(error).__name__

        # Transient errors
        if any(t in error_type for t in ["Connection", "Timeout", "RateLimit", "ServiceUnavailable"]):
            return ErrorCategory.TRANSIENT

        # Resource errors
        if any(t in error_type for t in ["Memory", "Resource", "Pool"]):
            return ErrorCategory.RESOURCE

        # Validation errors
        if "Validation" in error_type:
            return ErrorCategory.VALIDATION

        # Default to fatal for unknown errors
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
        """Check if circuit breaker is open for node."""
        if node_id not in self._circuit_open:
            return False

        # Check if circuit should transition to half-open
        if self._circuit_open[node_id]:
            last_failure = self._last_failure_time.get(node_id, 0)
            if time.time() - last_failure > 30:  # 30s timeout
                self._circuit_open[node_id] = False
                self.logger.info(f"Circuit half-open for {node_id}")

        return self._circuit_open[node_id]

    def _record_failure(self, node_id: str):
        """Record failure for circuit breaker."""
        self._failure_counts[node_id] = self._failure_counts.get(node_id, 0) + 1
        self._last_failure_time[node_id] = time.time()

        # Open circuit if too many failures in window
        if self._failure_counts[node_id] > 5:
            recent_failures = sum(
                1 for nid, t in self._last_failure_time.items()
                if nid == node_id and time.time() - t < 60
            )
            if recent_failures > 5:
                self._circuit_open[node_id] = True
                self.logger.error(f"Circuit opened for {node_id} after {recent_failures} failures")

    def _record_success(self, node_id: str):
        """Record success for circuit breaker."""
        if node_id in self._failure_counts:
            self._failure_counts[node_id] = max(0, self._failure_counts[node_id] - 1)

    async def execute_with_retry(
        self,
        node: BaseNode[StateT],
        ctx: RunContext[StateT],
        executor: ParallelExecutor[StateT],
    ) -> NodeResult[StateT]:
        """
        Execute node with automatic retry on transient errors.

        Flow:
        1. Try execute node
        2. If error: classify error
        3. If retryable: wait with backoff, retry
        4. If not retryable: return error result
        5. Preserve original context state on failure

        Args:
            node: Node to execute
            ctx: Execution context (state preserved on failure)
            executor: ParallelExecutor for node execution

        Returns:
            NodeResult (success or final error)
        """
        node_id = type(node).__name__
        attempt = 0

        while attempt < self.retry_config.max_attempts:
            attempt += 1

            # Execute node
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

            # Log error
            self.logger.warning(
                f"Node {node_id} failed (attempt {attempt}/{self.retry_config.max_attempts}): "
                f"{type(result.error).__name__}: {result.error}"
            )

            # Check if should retry
            if not self.should_retry(error_ctx):
                self.logger.error(f"Not retrying {node_id} ({category.value} error)")
                self._record_failure(node_id)
                return result

            # Calculate backoff delay
            delay_ms = self._calculate_backoff(attempt)
            self.logger.info(f"Retrying {node_id} after {delay_ms}ms")
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
        Optional jitter to prevent thundering herd

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
            import random
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def get_stats(self) -> dict[str, Any]:
        """
        Get circuit breaker statistics.

        Returns:
            Dictionary with failure counts, circuit states
        """
        return {
            "failure_counts": dict(self._failure_counts),
            "circuits_open": {k: v for k, v in self._circuit_open.items() if v},
            "total_failures": sum(self._failure_counts.values()),
        }
```

## Acceptance Criteria

### AC1: Transient errors retry successfully ✓

**Test**: Simulate transient error, verify retry succeeds
```python
async def test_ac1_transient_errors_retry():
    """
    AC1: Transient errors retry successfully.

    Test:
    1. Create node that fails first 2 times, succeeds on 3rd
    2. Execute with retry
    3. Verify 3 attempts made
    4. Verify final result is success
    """
    recovery = ErrorRecovery(retry_config=RetryConfig(max_attempts=3))

    class TransientFailureNode(MockLLMNode):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def run(self, ctx):
            self.attempts += 1
            if self.attempts < 3:
                raise ConnectionError("Transient network error")
            return End()

    node = TransientFailureNode()
    ctx = RunContext(state=TestState(), execution_id="test")
    executor = ParallelExecutor()

    result = await recovery.execute_with_retry(node, ctx, executor)

    assert result.is_success
    assert node.attempts == 3
```

### AC2: Fatal errors terminate gracefully ✓

**Test**: Simulate fatal error, verify no retry
```python
async def test_ac2_fatal_errors_terminate():
    """
    AC2: Fatal errors terminate gracefully.

    Test:
    1. Create node that raises ValueError (fatal)
    2. Execute with retry
    3. Verify only 1 attempt made
    4. Verify error preserved in result
    """
    recovery = ErrorRecovery(retry_config=RetryConfig(max_attempts=3))

    class FatalErrorNode(MockLLMNode):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        async def run(self, ctx):
            self.attempts += 1
            raise ValueError("Invalid input")

    node = FatalErrorNode()
    ctx = RunContext(state=TestState(), execution_id="test")
    executor = ParallelExecutor()

    result = await recovery.execute_with_retry(node, ctx, executor)

    assert not result.is_success
    assert node.attempts == 1  # No retry
    assert isinstance(result.error, ValueError)
```

### AC3: State preserved on all failure modes ✓

**Test**: Verify state unchanged after failure
```python
async def test_ac3_state_preserved_on_failure():
    """
    AC3: State preserved on all failure modes.

    Test:
    1. Create initial state with value=42
    2. Node fails and would modify state
    3. Verify state still has value=42 (unchanged)
    """
    recovery = ErrorRecovery()

    class StateModifyingFailureNode(MockLLMNode):
        async def run(self, ctx):
            ctx.state.value = 999  # Try to modify
            raise RuntimeError("Failure after state modification")

    node = StateModifyingFailureNode()
    initial_state = TestState(value=42)
    ctx = RunContext(state=initial_state, execution_id="test")
    executor = ParallelExecutor()

    result = await recovery.execute_with_retry(node, ctx, executor)

    # Original context state should be unchanged
    assert ctx.state.value == 42
    # Result context is isolated
    assert result.context.state.value == 999
```

### AC4: Error messages actionable ✓

**Test**: Verify error messages include context
```python
async def test_ac4_error_messages_actionable(caplog):
    """
    AC4: Error messages actionable.

    Test:
    1. Execute node that fails
    2. Verify log messages include:
       - Node name
       - Attempt number
       - Error type and message
       - Retry decision
    """
    import logging
    caplog.set_level(logging.WARNING)

    recovery = ErrorRecovery(retry_config=RetryConfig(max_attempts=2))

    class FailingNode(MockLLMNode):
        async def run(self, ctx):
            raise TimeoutError("Request timed out after 30s")

    node = FailingNode()
    ctx = RunContext(state=TestState(), execution_id="test")
    executor = ParallelExecutor()

    await recovery.execute_with_retry(node, ctx, executor)

    # Check logs
    assert "FailingNode failed" in caplog.text
    assert "attempt 1/2" in caplog.text
    assert "TimeoutError" in caplog.text
    assert "Retrying" in caplog.text or "Not retrying" in caplog.text
```

## Implementation Plan

### Phase 1: Core ErrorRecovery
1. Create ErrorCategory, RecoveryAction enums
2. Create RetryConfig, ErrorContext dataclasses
3. Create ErrorRecovery class with classify_error()

### Phase 2: Retry Logic
1. Implement should_retry() with category-based logic
2. Implement _calculate_backoff() with exponential backoff
3. Implement execute_with_retry() main loop

### Phase 3: Circuit Breaker
1. Add circuit breaker state tracking
2. Implement _is_circuit_open(), _record_failure(), _record_success()
3. Integrate with should_retry()

### Phase 4: Testing
1. Unit tests: Error classification, retry logic, backoff calculation
2. Integration tests: execute_with_retry with H4 ParallelExecutor
3. Circuit breaker tests: Verify circuit opens/closes correctly
4. All acceptance criteria tests

### Phase 5: Documentation
1. Update HOLE_INVENTORY.md
2. Create H5_COMPLETION_SUMMARY.md
3. Export from `lift_sys.dspy_signatures`

## Constraints Propagated

### From H4: ParallelizationImpl

**Constraint**: MUST use execute_single_with_isolation for state isolation

**Reasoning**: State must be isolated per retry attempt

**Impact**: execute_with_retry() calls executor.execute_single_with_isolation()

### To Future: H7 Telemetry

**Constraint**: SHOULD export error/retry metrics

**Reasoning**: Error rates are critical operational metrics

**Impact**: get_stats() provides metrics for H7 integration

## Alternative Designs Considered

### 1. Decorator-Based Retry
**Pros**: Simple, composable
**Cons**: Less control over retry logic
**Decision**: Use class-based approach for flexibility

### 2. Async Context Manager
**Pros**: Pythonic, automatic cleanup
**Cons**: Less explicit control flow
**Decision**: Explicit execute_with_retry() for clarity

### 3. Separate Circuit Breaker Class
**Pros**: Better separation of concerns
**Cons**: More complexity
**Decision**: Integrate into ErrorRecovery for simplicity

## Future Enhancements

1. **Fallback Strategies**: Try alternative nodes on persistent failures
2. **Adaptive Backoff**: Adjust backoff based on error rates
3. **Bulkhead Pattern**: Isolate failures to prevent cascading
4. **Dead Letter Queue**: Store failed requests for later analysis
5. **Metrics Integration**: Export to H7 observability

---

**Status**: Ready for implementation
**Next Steps**: Implement ErrorRecovery → Create tests → Integrate with H4
