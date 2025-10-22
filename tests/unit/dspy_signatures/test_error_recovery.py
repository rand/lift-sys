"""
Tests for H5 (ErrorRecovery) - Robust error handling for node failures.

Test Coverage:
1. Error classification (TRANSIENT, FATAL, VALIDATION, RESOURCE)
2. Retry logic with exponential backoff
3. Circuit breaker pattern
4. State preservation on failures
5. All 4 acceptance criteria
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import pytest
from pydantic import BaseModel

from lift_sys.dspy_signatures.error_recovery import (
    ErrorCategory,
    ErrorContext,
    ErrorRecovery,
    RetryConfig,
)
from lift_sys.dspy_signatures.node_interface import BaseNode, End, RunContext
from lift_sys.dspy_signatures.parallel_executor import ParallelExecutor


# Test fixtures
class TestState(BaseModel):
    value: int = 0
    prompt: str = ""


class MockLLMNode(BaseNode[TestState]):
    """Mock LLM node for testing."""

    def __init__(self, latency_ms: float = 10):
        self.latency_ms = latency_ms
        self.call_count = 0
        self.signature = None  # Mock signature

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {"value": state.value, "prompt": state.prompt}

    def update_state(self, state: TestState, result: Any) -> None:
        pass

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        self.call_count += 1
        await asyncio.sleep(self.latency_ms / 1000)
        return End()


class TransientFailureNode(MockLLMNode):
    """Node that fails with transient error first N times, then succeeds."""

    def __init__(self, failures_before_success: int = 2):
        super().__init__()
        self.failures_before_success = failures_before_success
        self.attempts = 0

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise ConnectionError("Transient network error")
        return End()


class FatalErrorNode(MockLLMNode):
    """Node that always fails with fatal error."""

    def __init__(self):
        super().__init__()
        self.attempts = 0

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        self.attempts += 1
        raise ValueError("Invalid input")


class ResourceErrorNode(MockLLMNode):
    """Node that fails with resource error."""

    def __init__(self, failures_before_success: int = 2):
        super().__init__()
        self.failures_before_success = failures_before_success
        self.attempts = 0

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        self.attempts += 1
        if self.attempts <= self.failures_before_success:
            raise MemoryError("Out of memory")
        return End()


class StateModifyingFailureNode(MockLLMNode):
    """Node that modifies state before failing."""

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        ctx.state.value = 999  # Modify state
        raise RuntimeError("Failure after state modification")


# Tests
class TestErrorClassification:
    """Test error classification logic."""

    def test_classify_transient_connection_error(self):
        recovery = ErrorRecovery[TestState]()
        error = ConnectionError("Connection timeout")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_timeout_error(self):
        recovery = ErrorRecovery[TestState]()
        error = TimeoutError("Request timed out")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_rate_limit_error(self):
        recovery = ErrorRecovery[TestState]()
        error = Exception("Rate limit exceeded (429)")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_transient_service_unavailable(self):
        recovery = ErrorRecovery[TestState]()
        error = Exception("Service temporarily unavailable (503)")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.TRANSIENT

    def test_classify_resource_memory_error(self):
        recovery = ErrorRecovery[TestState]()
        error = MemoryError("Out of memory")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.RESOURCE

    def test_classify_resource_pool_exhausted(self):
        recovery = ErrorRecovery[TestState]()
        error = Exception("Connection pool exhausted")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.RESOURCE

    def test_classify_validation_error(self):
        recovery = ErrorRecovery[TestState]()
        error = Exception("Validation failed")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.VALIDATION

    def test_classify_fatal_value_error(self):
        recovery = ErrorRecovery[TestState]()
        error = ValueError("Invalid input")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.FATAL

    def test_classify_fatal_type_error(self):
        recovery = ErrorRecovery[TestState]()
        error = TypeError("Expected int, got str")
        category = recovery.classify_error(error)
        assert category == ErrorCategory.FATAL


class TestRetryLogic:
    """Test retry decision logic."""

    def test_should_retry_transient_within_max_attempts(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")
        error_ctx = ErrorContext(
            error=ConnectionError("Timeout"),
            category=ErrorCategory.TRANSIENT,
            attempt=1,
            node=node,
            ctx=ctx,
        )
        assert recovery.should_retry(error_ctx) is True

    def test_should_not_retry_after_max_attempts(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")
        error_ctx = ErrorContext(
            error=ConnectionError("Timeout"),
            category=ErrorCategory.TRANSIENT,
            attempt=3,
            node=node,
            ctx=ctx,
        )
        assert recovery.should_retry(error_ctx) is False

    def test_should_retry_resource_errors(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")
        error_ctx = ErrorContext(
            error=MemoryError("Out of memory"),
            category=ErrorCategory.RESOURCE,
            attempt=1,
            node=node,
            ctx=ctx,
        )
        assert recovery.should_retry(error_ctx) is True

    def test_should_not_retry_fatal_errors(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")
        error_ctx = ErrorContext(
            error=ValueError("Invalid input"),
            category=ErrorCategory.FATAL,
            attempt=1,
            node=node,
            ctx=ctx,
        )
        assert recovery.should_retry(error_ctx) is False

    def test_should_not_retry_validation_errors(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")
        error_ctx = ErrorContext(
            error=Exception("Validation failed"),
            category=ErrorCategory.VALIDATION,
            attempt=1,
            node=node,
            ctx=ctx,
        )
        assert recovery.should_retry(error_ctx) is False


class TestBackoffCalculation:
    """Test exponential backoff calculation."""

    def test_backoff_exponential_growth(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(initial_delay_ms=100, backoff_factor=2.0, jitter=False)
        )

        # Attempt 1: 100ms
        delay1 = recovery._calculate_backoff(1)
        assert delay1 == 100

        # Attempt 2: 200ms
        delay2 = recovery._calculate_backoff(2)
        assert delay2 == 200

        # Attempt 3: 400ms
        delay3 = recovery._calculate_backoff(3)
        assert delay3 == 400

    def test_backoff_capped_at_max_delay(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(
                initial_delay_ms=100,
                backoff_factor=2.0,
                max_delay_ms=500,
                jitter=False,
            )
        )

        # Attempt 10 would be 51200ms, but capped at 500ms
        delay = recovery._calculate_backoff(10)
        assert delay == 500

    def test_backoff_with_jitter(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(initial_delay_ms=100, backoff_factor=2.0, jitter=True)
        )

        delay = recovery._calculate_backoff(1)
        # With 25% jitter, delay should be in range [75, 125]
        assert 75 <= delay <= 125

    def test_backoff_minimum_zero(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(initial_delay_ms=0, jitter=False)
        )
        delay = recovery._calculate_backoff(1)
        assert delay >= 0


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_opens_after_multiple_failures(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=1))
        node = MockLLMNode()
        node_id = type(node).__name__

        # Record 6 failures to open circuit (threshold is 5)
        for _ in range(6):
            recovery._record_failure(node_id)

        # Circuit should be open
        assert recovery._is_circuit_open(node_id) is True

    def test_circuit_half_open_after_timeout(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=1))
        node = MockLLMNode()
        node_id = type(node).__name__

        # Open circuit
        for _ in range(6):
            recovery._record_failure(node_id)
        assert recovery._is_circuit_open(node_id) is True

        # Simulate 31s timeout (circuit breaker timeout is 30s)
        recovery._last_failure_time[node_id] = time.time() - 31

        # Circuit should be half-open (allowing retry)
        assert recovery._is_circuit_open(node_id) is False

    def test_circuit_closes_on_success(self):
        recovery = ErrorRecovery[TestState]()
        node = MockLLMNode()
        node_id = type(node).__name__

        # Open circuit
        for _ in range(6):
            recovery._record_failure(node_id)
        recovery._circuit_open[node_id] = True

        # Record success
        recovery._record_success(node_id)

        # Circuit should be closed
        assert recovery._circuit_open[node_id] is False

    def test_circuit_prevents_retry(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(), execution_id="test")

        # Open circuit
        node_id = type(node).__name__
        for _ in range(6):
            recovery._record_failure(node_id)

        error_ctx = ErrorContext(
            error=ConnectionError("Timeout"),
            category=ErrorCategory.TRANSIENT,
            attempt=1,
            node=node,
            ctx=ctx,
        )

        # Should not retry due to open circuit
        assert recovery.should_retry(error_ctx) is False


class TestExecuteWithRetry:
    """Test execute_with_retry main loop."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        recovery = ErrorRecovery[TestState]()
        node = MockLLMNode()
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        assert result.is_success
        assert node.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_transient_error_then_succeed(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(max_attempts=3, initial_delay_ms=10)
        )
        node = TransientFailureNode(failures_before_success=2)
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        assert result.is_success
        assert node.attempts == 3  # Failed 2 times, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_no_retry_on_fatal_error(self):
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))
        node = FatalErrorNode()
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        assert not result.is_success
        assert node.attempts == 1  # No retry
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_max_attempts_exceeded(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(max_attempts=2, initial_delay_ms=10)
        )
        node = TransientFailureNode(failures_before_success=5)
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        assert not result.is_success
        assert node.attempts == 2  # Max attempts
        assert isinstance(result.error, ConnectionError)

    @pytest.mark.asyncio
    async def test_retry_resource_error(self):
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(max_attempts=3, initial_delay_ms=10)
        )
        node = ResourceErrorNode(failures_before_success=2)
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        assert result.is_success
        assert node.attempts == 3  # Failed 2 times, succeeded on 3rd


class TestStatistics:
    """Test circuit breaker statistics."""

    def test_get_stats_initial_state(self):
        recovery = ErrorRecovery[TestState]()
        stats = recovery.get_stats()

        assert stats["failure_counts"] == {}
        assert stats["circuits_open"] == {}
        assert stats["total_failures"] == 0

    def test_get_stats_after_failures(self):
        recovery = ErrorRecovery[TestState]()
        node = MockLLMNode()
        node_id = type(node).__name__

        # Record 3 failures
        for _ in range(3):
            recovery._record_failure(node_id)

        stats = recovery.get_stats()
        assert stats["failure_counts"][node_id] == 3
        assert stats["total_failures"] == 3

    def test_get_stats_with_open_circuit(self):
        recovery = ErrorRecovery[TestState]()
        node = MockLLMNode()
        node_id = type(node).__name__

        # Open circuit
        for _ in range(6):
            recovery._record_failure(node_id)

        stats = recovery.get_stats()
        assert node_id in stats["circuits_open"]
        assert stats["circuits_open"][node_id] is True


# Acceptance Criteria Tests
class TestAcceptanceCriteria:
    """
    Test all 4 acceptance criteria for H5 (ErrorRecovery).

    AC1: Transient errors retry successfully
    AC2: Fatal errors terminate gracefully
    AC3: State preserved on all failure modes
    AC4: Error messages actionable
    """

    @pytest.mark.asyncio
    async def test_ac1_transient_errors_retry_successfully(self):
        """
        AC1: Transient errors retry successfully.

        Test:
        1. Create node that fails first 2 times, succeeds on 3rd
        2. Execute with retry
        3. Verify 3 attempts made
        4. Verify final result is success
        """
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(max_attempts=3, initial_delay_ms=10)
        )

        node = TransientFailureNode(failures_before_success=2)
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        # Verify success after retries
        assert result.is_success
        assert node.attempts == 3

    @pytest.mark.asyncio
    async def test_ac2_fatal_errors_terminate_gracefully(self):
        """
        AC2: Fatal errors terminate gracefully.

        Test:
        1. Create node that raises ValueError (fatal)
        2. Execute with retry
        3. Verify only 1 attempt made
        4. Verify error preserved in result
        """
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=3))

        node = FatalErrorNode()
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        # Verify no retry on fatal error
        assert not result.is_success
        assert node.attempts == 1  # No retry
        assert isinstance(result.error, ValueError)

    @pytest.mark.asyncio
    async def test_ac3_state_preserved_on_failure(self):
        """
        AC3: State preserved on all failure modes.

        Test:
        1. Create initial state with value=42
        2. Node fails and would modify state
        3. Verify state still has value=42 (unchanged)
        """
        recovery = ErrorRecovery[TestState]()

        node = StateModifyingFailureNode()
        initial_state = TestState(value=42)
        ctx = RunContext(state=initial_state, execution_id="test")
        executor = ParallelExecutor[TestState]()

        result = await recovery.execute_with_retry(node, ctx, executor)

        # Original context state should be unchanged (due to H4 isolation)
        assert ctx.state.value == 42

        # Result context is isolated and has modified value
        assert result.context.state.value == 999

    @pytest.mark.asyncio
    async def test_ac4_error_messages_actionable(self, caplog):
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
        caplog.set_level(logging.WARNING)

        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(max_attempts=2, initial_delay_ms=10)
        )

        node = TransientFailureNode(failures_before_success=5)  # Will fail all attempts
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        await recovery.execute_with_retry(node, ctx, executor)

        # Check logs for actionable information
        log_text = caplog.text
        assert "TransientFailureNode failed" in log_text
        assert "attempt 1/2" in log_text or "attempt 2/2" in log_text
        assert "ConnectionError" in log_text
        # Retry decision should be present (either "Retrying", "Not retrying", or "Max attempts")
        assert "Retrying" in log_text or "Not retrying" in log_text or "Max attempts" in log_text


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_max_attempts(self):
        """Even with 0 max_attempts, should attempt at least once."""
        recovery = ErrorRecovery[TestState](retry_config=RetryConfig(max_attempts=0))
        node = MockLLMNode()
        ctx = RunContext(state=TestState(value=42), execution_id="test")
        executor = ParallelExecutor[TestState]()

        # Should still execute (while loop runs at least once)
        result = await recovery.execute_with_retry(node, ctx, executor)
        assert result.is_success

    @pytest.mark.asyncio
    async def test_very_high_backoff_factor(self):
        """Backoff should be capped at max_delay_ms."""
        recovery = ErrorRecovery[TestState](
            retry_config=RetryConfig(
                max_attempts=3,
                initial_delay_ms=100,
                backoff_factor=10.0,
                max_delay_ms=500,
                jitter=False,
            )
        )

        # Attempt 2 would be 1000ms, but capped at 500ms
        delay = recovery._calculate_backoff(2)
        assert delay == 500

    @pytest.mark.asyncio
    async def test_multiple_nodes_independent_circuits(self):
        """Circuit breakers should be independent per node type."""
        recovery = ErrorRecovery[TestState]()

        node1 = MockLLMNode()
        node2 = FatalErrorNode()

        node1_id = type(node1).__name__
        node2_id = type(node2).__name__

        # Open circuit for node1
        for _ in range(6):
            recovery._record_failure(node1_id)

        # node1 circuit open, node2 circuit closed
        assert recovery._is_circuit_open(node1_id) is True
        assert recovery._is_circuit_open(node2_id) is False

    @pytest.mark.asyncio
    async def test_success_decrements_failure_count(self):
        """Successful executions should decrement failure count."""
        recovery = ErrorRecovery[TestState]()
        node = MockLLMNode()
        node_id = type(node).__name__

        # Record 3 failures
        for _ in range(3):
            recovery._record_failure(node_id)
        assert recovery._failure_counts[node_id] == 3

        # Record 2 successes
        recovery._record_success(node_id)
        recovery._record_success(node_id)

        # Failure count should be 1 (3 - 2)
        assert recovery._failure_counts[node_id] == 1
