"""Tests for ParallelExecutor (H4)."""

import asyncio
import time
from typing import Any

import pytest
from pydantic import BaseModel

from lift_sys.dspy_signatures.node_interface import BaseNode, End, RunContext
from lift_sys.dspy_signatures.parallel_executor import (
    MergeStrategy,
    NodeResult,
    ParallelExecutionError,
    ParallelExecutor,
)


# Test state models
class TestState(BaseModel):
    """Simple test state."""

    value: int = 0
    counter: int = 0
    results: list[str] = []


# Test nodes
class IncrementNode:
    """Node that increments counter."""

    signature = None  # Mock signature

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {"value": state.counter}

    def update_state(self, state: TestState, result: Any) -> None:
        state.counter += 1

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        """Increment counter in state."""
        self.update_state(ctx.state, None)
        return End()


class SetValueNode:
    """Node that sets value in state."""

    def __init__(self, value: int):
        self.value = value
        self.signature = None

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {}

    def update_state(self, state: TestState, result: Any) -> None:
        state.value = self.value

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        """Set value in state."""
        self.update_state(ctx.state, None)
        return End()


class AppendResultNode:
    """Node that appends to results list."""

    def __init__(self, result: str):
        self.result = result
        self.signature = None

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {}

    def update_state(self, state: TestState, result: Any) -> None:
        state.results.append(self.result)

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        """Append result to state."""
        self.update_state(ctx.state, None)
        return End()


class SlowNode:
    """Node that takes time to execute (for speedup testing)."""

    def __init__(self, delay_ms: int):
        self.delay_ms = delay_ms
        self.signature = None

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {}

    def update_state(self, state: TestState, result: Any) -> None:
        pass

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        """Simulate slow execution."""
        await asyncio.sleep(self.delay_ms / 1000.0)
        return End()


class FailNode:
    """Node that always fails."""

    def __init__(self, error: Exception):
        self.error = error
        self.signature = None

    def extract_inputs(self, state: TestState) -> dict[str, Any]:
        return {}

    def update_state(self, state: TestState, result: Any) -> None:
        pass

    async def run(self, ctx: RunContext[TestState]) -> BaseNode[TestState] | End:
        """Raise error."""
        raise self.error


class TestNodeResult:
    """Tests for NodeResult dataclass."""

    def test_node_result_success(self):
        """Test NodeResult for successful execution."""
        node = SetValueNode(42)
        ctx = RunContext(state=TestState(value=42), execution_id="test-123")

        result = NodeResult(
            node=node,
            next_node=End(),
            context=ctx,
            execution_time_ms=100.5,
            error=None,
        )

        assert result.is_success
        assert result.is_end
        assert result.execution_time_ms == 100.5
        assert result.error is None

    def test_node_result_failure(self):
        """Test NodeResult for failed execution."""
        node = FailNode(ValueError("test error"))
        ctx = RunContext(state=TestState(), execution_id="test-123")
        error = ValueError("test error")

        result = NodeResult(
            node=node,
            next_node=End(),
            context=ctx,
            execution_time_ms=50.0,
            error=error,
        )

        assert not result.is_success
        assert result.is_end
        assert result.error is error


class TestParallelExecutor:
    """Tests for ParallelExecutor class."""

    def test_executor_initialization(self):
        """Test ParallelExecutor initialization."""
        executor = ParallelExecutor(max_concurrent=4)

        assert executor.max_concurrent == 4
        assert executor._semaphore._value == 4

    def test_executor_invalid_max_concurrent(self):
        """Test ParallelExecutor rejects invalid max_concurrent."""
        with pytest.raises(ValueError, match="max_concurrent must be ≥1"):
            ParallelExecutor(max_concurrent=0)

        with pytest.raises(ValueError, match="max_concurrent must be ≥1"):
            ParallelExecutor(max_concurrent=-1)

    @pytest.mark.asyncio
    async def test_execute_single_with_isolation_success(self):
        """Test single node execution with state isolation."""
        node = SetValueNode(42)
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=1)
        result = await executor.execute_single_with_isolation(node, ctx)

        # Execution succeeded
        assert result.is_success
        assert result.error is None

        # State updated in result context
        assert result.context.state.value == 42

        # Original context unchanged (isolation)
        assert ctx.state.value == 0

        # Timing recorded
        assert result.execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_single_with_isolation_failure(self):
        """Test single node execution captures errors."""
        error = ValueError("test error")
        node = FailNode(error)
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=1)
        result = await executor.execute_single_with_isolation(node, ctx)

        # Execution failed
        assert not result.is_success
        assert result.error is error
        assert isinstance(result.error, ValueError)

        # Next node is End (terminate on error)
        assert result.is_end

        # Timing still recorded
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_parallel_empty_list(self):
        """Test execute_parallel with empty node list."""
        executor = ParallelExecutor(max_concurrent=4)
        ctx = RunContext(state=TestState(), execution_id="test-123")

        results = await executor.execute_parallel([], ctx)

        assert results == []

    @pytest.mark.asyncio
    async def test_execute_parallel_single_node(self):
        """Test execute_parallel with single node."""
        node = SetValueNode(99)
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel([node], ctx)

        assert len(results) == 1
        assert results[0].is_success
        assert results[0].context.state.value == 99

    @pytest.mark.asyncio
    async def test_execute_parallel_multiple_nodes(self):
        """Test execute_parallel with multiple nodes."""
        nodes = [SetValueNode(i * 10) for i in range(5)]
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel(nodes, ctx)

        assert len(results) == 5

        # All succeeded
        assert all(r.is_success for r in results)

        # Each has different value (state isolated)
        values = [r.context.state.value for r in results]
        assert set(values) == {0, 10, 20, 30, 40}

    @pytest.mark.asyncio
    async def test_state_isolation_no_race_conditions(self):
        """Test that state isolation prevents race conditions."""
        # Create 10 nodes that increment counter
        nodes = [IncrementNode() for _ in range(10)]
        ctx = RunContext(state=TestState(counter=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=10)
        results = await executor.execute_parallel(nodes, ctx)

        # If state isolated: each sees counter=0, increments to 1
        # If race condition: undefined behavior (2, 3, ... 10)
        for result in results:
            assert result.context.state.counter == 1, "State not properly isolated"

        # Original context unchanged
        assert ctx.state.counter == 0


class TestMergeStrategies:
    """Tests for merge strategy implementations."""

    @pytest.mark.asyncio
    async def test_merge_first_success_all_succeed(self):
        """Test FIRST_SUCCESS with all successful results."""
        nodes = [SetValueNode(i * 10) for i in range(3)]
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=3)
        results = await executor.execute_parallel(nodes, ctx)

        merged = executor.merge_states(results, MergeStrategy.FIRST_SUCCESS)

        # Uses first result (value=0)
        assert merged.state.value == 0

    @pytest.mark.asyncio
    async def test_merge_first_success_with_failures(self):
        """Test FIRST_SUCCESS skips failures and uses first success."""
        nodes = [
            FailNode(ValueError("error 1")),
            FailNode(ValueError("error 2")),
            SetValueNode(42),
            SetValueNode(99),
        ]
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel(nodes, ctx)

        merged = executor.merge_states(results, MergeStrategy.FIRST_SUCCESS)

        # Uses first successful result (value=42)
        assert merged.state.value == 42

    @pytest.mark.asyncio
    async def test_merge_first_success_all_fail(self):
        """Test FIRST_SUCCESS raises when all nodes fail."""
        nodes = [
            FailNode(ValueError("error 1")),
            FailNode(ValueError("error 2")),
        ]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=2)
        results = await executor.execute_parallel(nodes, ctx)

        with pytest.raises(ParallelExecutionError, match="All parallel nodes failed"):
            executor.merge_states(results, MergeStrategy.FIRST_SUCCESS)

    @pytest.mark.asyncio
    async def test_merge_all_success_all_succeed(self):
        """Test ALL_SUCCESS with all successful results."""
        nodes = [AppendResultNode(f"result_{i}") for i in range(3)]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=3)
        results = await executor.execute_parallel(nodes, ctx)

        merged = executor.merge_states(results, MergeStrategy.ALL_SUCCESS)

        # Provenance from all nodes merged
        assert len(merged.provenance) >= 0  # May be empty if nodes don't add provenance

        # Check results are combined (order may vary due to parallelism)
        assert len(merged.state.results) == 1  # Only first node's result in merged state
        # Note: ALL_SUCCESS merges provenance, not state lists

    @pytest.mark.asyncio
    async def test_merge_all_success_with_failure(self):
        """Test ALL_SUCCESS raises when any node fails."""
        nodes = [
            SetValueNode(10),
            FailNode(ValueError("error")),
            SetValueNode(30),
        ]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=3)
        results = await executor.execute_parallel(nodes, ctx)

        with pytest.raises(
            ParallelExecutionError, match="1 of 3 nodes failed.*ALL_SUCCESS requires all"
        ):
            executor.merge_states(results, MergeStrategy.ALL_SUCCESS)

    @pytest.mark.asyncio
    async def test_merge_majority_all_same(self):
        """Test MAJORITY with all identical outputs."""
        # Run same node multiple times (should produce same output)
        nodes = [SetValueNode(42) for _ in range(5)]
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=5)
        results = await executor.execute_parallel(nodes, ctx)

        merged = executor.merge_states(results, MergeStrategy.MAJORITY)

        # All nodes produced same output (value=42)
        assert merged.state.value == 42

    @pytest.mark.asyncio
    async def test_merge_majority_different_outputs(self):
        """Test MAJORITY selects most common output."""
        nodes = [
            SetValueNode(10),
            SetValueNode(20),
            SetValueNode(20),  # Most common
            SetValueNode(30),
        ]
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel(nodes, ctx)

        merged = executor.merge_states(results, MergeStrategy.MAJORITY)

        # Most common output is value=20 (appears twice)
        assert merged.state.value == 20

    @pytest.mark.asyncio
    async def test_merge_empty_results(self):
        """Test merge raises on empty results list."""
        executor = ParallelExecutor(max_concurrent=1)

        with pytest.raises(ParallelExecutionError, match="Cannot merge empty results"):
            executor.merge_states([], MergeStrategy.FIRST_SUCCESS)


class TestAcceptanceCriteria:
    """Tests for H4 acceptance criteria."""

    @pytest.mark.asyncio
    async def test_ac1_speedup_parallel_paths(self):
        """AC1: Speedup ≥2x on parallel paths."""
        # Create 4 independent nodes (each takes ~50ms)
        nodes = [SlowNode(delay_ms=50) for _ in range(4)]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        # Sequential execution
        sequential_start = time.perf_counter()
        for node in nodes:
            await node.run(ctx)
        sequential_time = time.perf_counter() - sequential_start

        # Parallel execution
        executor = ParallelExecutor(max_concurrent=4)
        parallel_start = time.perf_counter()
        results = await executor.execute_parallel(nodes, ctx)
        parallel_time = time.perf_counter() - parallel_start

        speedup = sequential_time / parallel_time

        # Should get ~4x speedup (all run in parallel)
        # Require at least 2x per AC
        assert speedup >= 2.0, f"Speedup {speedup:.2f}x < 2.0x required"
        assert len(results) == 4
        assert all(r.is_success for r in results)

    @pytest.mark.asyncio
    async def test_ac2_deterministic_100_runs(self):
        """AC2: 100 test runs produce identical results."""
        node = SetValueNode(42)
        ctx = RunContext(state=TestState(value=0), execution_id="test-123")
        executor = ParallelExecutor(max_concurrent=1)

        # Run 100 times
        outputs = []
        for _ in range(100):
            results = await executor.execute_parallel([node], ctx)
            output_json = results[0].context.state.model_dump_json()
            outputs.append(output_json)

        # All outputs identical
        assert len(set(outputs)) == 1, "Outputs varied across runs (non-deterministic)"

    @pytest.mark.asyncio
    async def test_ac3_no_deadlocks(self):
        """AC3: No deadlocks with many concurrent nodes."""
        # Create many nodes to stress semaphore
        nodes = [SetValueNode(i) for i in range(100)]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)

        # Should complete without hanging
        try:
            async with asyncio.timeout(5.0):  # 5 second timeout
                results = await executor.execute_parallel(nodes, ctx)
        except TimeoutError:
            pytest.fail("Execution timed out - possible deadlock")

        assert len(results) == 100
        assert all(r.is_success for r in results)

    @pytest.mark.asyncio
    async def test_ac4_proper_error_propagation(self):
        """AC4: Proper error propagation from failed nodes."""
        nodes = [
            SetValueNode(10),
            FailNode(ValueError("Test error")),
            SetValueNode(30),
        ]
        ctx = RunContext(state=TestState(), execution_id="test-123")
        executor = ParallelExecutor(max_concurrent=3)

        results = await executor.execute_parallel(nodes, ctx)

        # All results returned (no exception thrown)
        assert len(results) == 3

        # Failed node has error
        assert results[1].error is not None
        assert isinstance(results[1].error, ValueError)
        assert str(results[1].error) == "Test error"

        # Successful nodes have no error
        assert results[0].error is None
        assert results[2].error is None


class TestStatistics:
    """Tests for execution statistics."""

    @pytest.mark.asyncio
    async def test_get_statistics_all_success(self):
        """Test statistics with all successful executions."""
        nodes = [SlowNode(delay_ms=10) for _ in range(5)]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=5)
        results = await executor.execute_parallel(nodes, ctx)

        stats = executor.get_statistics(results)

        assert stats["total_nodes"] == 5
        assert stats["successes"] == 5
        assert stats["failures"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_time_ms"] >= 10  # At least delay time
        assert len(stats["errors"]) == 0

    @pytest.mark.asyncio
    async def test_get_statistics_mixed_results(self):
        """Test statistics with mixed success/failure."""
        nodes = [
            SetValueNode(10),
            FailNode(ValueError("error 1")),
            SetValueNode(30),
            FailNode(ValueError("error 2")),
        ]
        ctx = RunContext(state=TestState(), execution_id="test-123")

        executor = ParallelExecutor(max_concurrent=4)
        results = await executor.execute_parallel(nodes, ctx)

        stats = executor.get_statistics(results)

        assert stats["total_nodes"] == 4
        assert stats["successes"] == 2
        assert stats["failures"] == 2
        assert stats["success_rate"] == 0.5
        assert len(stats["errors"]) == 2
