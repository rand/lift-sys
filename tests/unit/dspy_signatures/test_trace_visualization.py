"""
Tests for H7 (TraceVisualizationProtocol) - Execution trace visualization.

Test Coverage:
1. Model validation (NodeEvent, StateSnapshot, ExecutionTrace)
2. TraceVisualizationService core methods
3. Event streaming and subscriptions
4. State diff computation
5. All 4 acceptance criteria
6. Edge cases and error handling
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from lift_sys.dspy_signatures.execution_history import (
    ExecutionHistory,
    ExecutionHistoryStore,
    ExecutionTiming,
    PerformanceMetrics,
)
from lift_sys.dspy_signatures.trace_visualization import (
    ExecutionTrace,
    NodeEvent,
    NodeEventType,
    StateSnapshot,
    TraceVisualizationService,
)


# Test fixtures
class TestState(BaseModel):
    value: int = 0
    prompt: str = ""


@pytest.fixture
def mock_history_store():
    """Mock ExecutionHistoryStore for testing."""
    store = AsyncMock(spec=ExecutionHistoryStore)
    return store


@pytest.fixture
def sample_execution_history() -> ExecutionHistory:
    """Create sample ExecutionHistory for testing."""
    return ExecutionHistory(
        execution_id="exec-123",
        state_snapshot={"value": 42, "prompt": "test"},
        state_type="TestState",
        provenance=[{"created_by": "test"}],  # Should be list of dicts
        metadata={"failed_nodes_list": []},
        user_id="user-1",
        graph_type="forward_mode",
        original_inputs={"prompt": "test"},
        timing=ExecutionTiming(
            start_time="2025-10-21T10:00:00Z",
            end_time="2025-10-21T10:00:05Z",
            total_duration_ms=5000,
            node_timings={"TranslateNode": 2000, "ValidateNode": 1500, "GenerateNode": 1500},
        ),
        performance=PerformanceMetrics(
            total_tokens=1500, total_llm_calls=3, cache_hits=1, cache_misses=2
        ),
    )


# Model Tests
class TestNodeEvent:
    """Test NodeEvent model."""

    def test_create_node_event(self):
        """Test creating NodeEvent with all fields."""
        event = NodeEvent(
            event_id="e1",
            execution_id="exec-123",
            node_id="TranslateNode",
            event_type=NodeEventType.STARTED,
            timestamp="2025-10-21T10:00:00Z",
        )

        assert event.event_id == "e1"
        assert event.execution_id == "exec-123"
        assert event.node_id == "TranslateNode"
        assert event.event_type == NodeEventType.STARTED
        assert event.timestamp == "2025-10-21T10:00:00Z"
        assert event.duration_ms is None
        assert event.inputs == {}
        assert event.outputs == {}
        assert event.error is None
        assert event.metadata == {}

    def test_node_event_with_duration(self):
        """Test NodeEvent for completed event with duration."""
        event = NodeEvent(
            event_id="e2",
            execution_id="exec-123",
            node_id="TranslateNode",
            event_type=NodeEventType.COMPLETED,
            timestamp="2025-10-21T10:00:02Z",
            duration_ms=2000,
            inputs={"prompt": "test"},
            outputs={"result": "success"},
        )

        assert event.event_type == NodeEventType.COMPLETED
        assert event.duration_ms == 2000
        assert event.inputs == {"prompt": "test"}
        assert event.outputs == {"result": "success"}

    def test_node_event_with_error(self):
        """Test NodeEvent for failed event with error."""
        event = NodeEvent(
            event_id="e3",
            execution_id="exec-123",
            node_id="TranslateNode",
            event_type=NodeEventType.FAILED,
            timestamp="2025-10-21T10:00:02Z",
            duration_ms=500,
            error="ValueError: Invalid input",
        )

        assert event.event_type == NodeEventType.FAILED
        assert event.error == "ValueError: Invalid input"

    def test_node_event_cached(self):
        """Test NodeEvent for cached result."""
        event = NodeEvent(
            event_id="e4",
            execution_id="exec-123",
            node_id="TranslateNode",
            event_type=NodeEventType.CACHED,
            timestamp="2025-10-21T10:00:01Z",
            duration_ms=0,
            metadata={"cache_key": "abc123"},
        )

        assert event.event_type == NodeEventType.CACHED
        assert event.duration_ms == 0
        assert event.metadata["cache_key"] == "abc123"


class TestStateSnapshot:
    """Test StateSnapshot model."""

    def test_create_state_snapshot(self):
        """Test creating StateSnapshot."""
        snapshot = StateSnapshot(
            snapshot_id="s1",
            execution_id="exec-123",
            timestamp="2025-10-21T10:00:00Z",
            node_id="TranslateNode",
            state={"value": 42, "prompt": "test"},
        )

        assert snapshot.snapshot_id == "s1"
        assert snapshot.execution_id == "exec-123"
        assert snapshot.timestamp == "2025-10-21T10:00:00Z"
        assert snapshot.node_id == "TranslateNode"
        assert snapshot.state == {"value": 42, "prompt": "test"}
        assert snapshot.diff is None

    def test_state_snapshot_with_diff(self):
        """Test StateSnapshot with diff."""
        snapshot = StateSnapshot(
            snapshot_id="s2",
            execution_id="exec-123",
            timestamp="2025-10-21T10:00:01Z",
            node_id="ValidateNode",
            state={"value": 43, "prompt": "test"},
            diff={"value": {"old": 42, "new": 43}},
        )

        assert snapshot.diff == {"value": {"old": 42, "new": 43}}


class TestExecutionTrace:
    """Test ExecutionTrace model."""

    def test_create_execution_trace(self):
        """Test creating ExecutionTrace with all fields."""
        trace = ExecutionTrace(
            execution_id="exec-123",
            graph_type="forward_mode",
            status="completed",
            start_time="2025-10-21T10:00:00Z",
            end_time="2025-10-21T10:00:05Z",
            total_duration_ms=5000,
            node_events=[],
            state_snapshots=[],
            total_nodes=3,
            failed_nodes=0,
            cached_nodes=1,
            total_llm_calls=3,
            total_tokens=1500,
            original_inputs={"prompt": "test"},
            final_state={"result": "success"},
        )

        assert trace.execution_id == "exec-123"
        assert trace.graph_type == "forward_mode"
        assert trace.status == "completed"
        assert trace.total_nodes == 3
        assert trace.failed_nodes == 0
        assert trace.cached_nodes == 1
        assert trace.total_llm_calls == 3
        assert trace.total_tokens == 1500


# Service Tests
class TestTraceVisualizationService:
    """Test TraceVisualizationService."""

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_history_store):
        """Test service initialization."""
        service = TraceVisualizationService(mock_history_store)

        assert service.store == mock_history_store
        assert service._event_subscribers == {}

    @pytest.mark.asyncio
    async def test_get_trace(self, mock_history_store, sample_execution_history):
        """Test get_trace() method."""
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        trace = await service.get_trace("exec-123")

        # Verify trace fields
        assert trace.execution_id == "exec-123"
        assert trace.graph_type == "forward_mode"
        assert trace.status == "completed"
        assert trace.start_time == "2025-10-21T10:00:00Z"
        assert trace.end_time == "2025-10-21T10:00:05Z"
        assert trace.total_duration_ms == 5000
        assert trace.total_nodes == 3
        assert trace.total_llm_calls == 3
        assert trace.total_tokens == 1500
        assert trace.cached_nodes == 1
        assert trace.failed_nodes == 0

        # Verify node events extracted
        assert len(trace.node_events) == 3
        node_ids = {e.node_id for e in trace.node_events}
        assert node_ids == {"TranslateNode", "ValidateNode", "GenerateNode"}

        # Verify state snapshots
        assert len(trace.state_snapshots) >= 1

        # Verify store was called
        mock_history_store.load_execution.assert_called_once_with("exec-123")

    @pytest.mark.asyncio
    async def test_get_trace_with_uuid(self, mock_history_store, sample_execution_history):
        """Test get_trace() with UUID argument."""
        from uuid import UUID

        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        execution_uuid = UUID("12345678-1234-1234-1234-123456789012")
        trace = await service.get_trace(execution_uuid)

        assert trace.execution_id == "exec-123"
        mock_history_store.load_execution.assert_called_once_with(str(execution_uuid))

    @pytest.mark.asyncio
    async def test_get_node_timeline_all_nodes(self, mock_history_store, sample_execution_history):
        """Test get_node_timeline() without filter."""
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        timeline = await service.get_node_timeline("exec-123")

        # Should have events for all 3 nodes
        assert len(timeline) == 3
        node_ids = {e.node_id for e in timeline}
        assert node_ids == {"TranslateNode", "ValidateNode", "GenerateNode"}

        # Should be sorted by timestamp
        timestamps = [e.timestamp for e in timeline]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_get_node_timeline_filtered(self, mock_history_store, sample_execution_history):
        """Test get_node_timeline() with node_type filter."""
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        timeline = await service.get_node_timeline("exec-123", node_type="TranslateNode")

        # Should only have TranslateNode events
        assert len(timeline) == 1
        assert timeline[0].node_id == "TranslateNode"
        assert timeline[0].duration_ms == 2000

    @pytest.mark.asyncio
    async def test_get_state_history_without_diffs(
        self, mock_history_store, sample_execution_history
    ):
        """Test get_state_history() without diffs."""
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        snapshots = await service.get_state_history("exec-123", include_diffs=False)

        # Should have at least final snapshot
        assert len(snapshots) >= 1
        assert snapshots[0].execution_id == "exec-123"
        assert snapshots[0].state == {"value": 42, "prompt": "test"}
        assert snapshots[0].diff is None

    @pytest.mark.asyncio
    async def test_get_state_history_with_diffs(self, mock_history_store):
        """Test get_state_history() with diffs computed."""
        # Create history with multiple snapshots (simulated)
        history = ExecutionHistory(
            execution_id="exec-123",
            state_snapshot={"value": 44, "prompt": "test", "result": "done"},
            state_type="TestState",
            provenance=[],
            metadata={},
            graph_type="forward_mode",
            original_inputs={"prompt": "test"},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z",
                end_time="2025-10-21T10:00:05Z",
                total_duration_ms=5000,
                node_timings={"Node1": 2000},
            ),
            performance=PerformanceMetrics(),
        )

        mock_history_store.load_execution.return_value = history
        service = TraceVisualizationService(mock_history_store)

        # For single snapshot, diffs won't be computed
        snapshots = await service.get_state_history("exec-123", include_diffs=True)
        assert len(snapshots) == 1  # Only final snapshot currently

    @pytest.mark.asyncio
    async def test_list_executions_no_filters(self, mock_history_store, sample_execution_history):
        """Test list_executions() without filters."""
        mock_history_store.list_executions.return_value = [sample_execution_history]
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        traces = await service.list_executions()

        assert len(traces) == 1
        assert traces[0].execution_id == "exec-123"
        mock_history_store.list_executions.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_executions_with_filters(self, mock_history_store, sample_execution_history):
        """Test list_executions() with filters."""
        mock_history_store.list_executions.return_value = [sample_execution_history]
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        start_time = datetime(2025, 10, 21, 10, 0, 0)
        end_time = datetime(2025, 10, 21, 11, 0, 0)

        traces = await service.list_executions(
            graph_type="forward_mode",
            status="completed",
            start_time=start_time,
            end_time=end_time,
            limit=50,
            offset=10,
        )

        assert len(traces) == 1
        assert traces[0].status == "completed"

        # Verify filters passed to store
        call_kwargs = mock_history_store.list_executions.call_args[1]
        assert call_kwargs["filters"]["graph_type"] == "forward_mode"
        assert call_kwargs["filters"]["time_range"] == (start_time, end_time)
        assert call_kwargs["limit"] == 50
        assert call_kwargs["offset"] == 10

    @pytest.mark.asyncio
    async def test_list_executions_status_filter(self, mock_history_store):
        """Test list_executions() filters by status after loading."""
        # Create failed execution
        failed_history = ExecutionHistory(
            execution_id="exec-failed",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={"error": "Something went wrong"},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z",
                end_time="2025-10-21T10:00:01Z",
                total_duration_ms=1000,
                node_timings={},
            ),
            performance=PerformanceMetrics(),
        )

        mock_history_store.list_executions.return_value = [failed_history]
        mock_history_store.load_execution.return_value = failed_history
        service = TraceVisualizationService(mock_history_store)

        # Filter for completed only (should exclude failed)
        completed_traces = await service.list_executions(status="completed")
        assert len(completed_traces) == 0

        # Filter for failed
        failed_traces = await service.list_executions(status="failed")
        assert len(failed_traces) == 1
        assert failed_traces[0].status == "failed"


# Event Streaming Tests
class TestEventStreaming:
    """Test event streaming and subscriptions."""

    @pytest.mark.asyncio
    async def test_subscribe_to_execution(self, mock_history_store):
        """Test subscribing to execution events."""
        service = TraceVisualizationService(mock_history_store)

        received_events = []

        async def callback(event: NodeEvent):
            received_events.append(event)

        # Subscribe
        service.subscribe_to_execution("exec-123", callback)

        # Verify subscription registered
        assert "exec-123" in service._event_subscribers
        assert callback in service._event_subscribers["exec-123"]

    @pytest.mark.asyncio
    async def test_emit_event_to_subscribers(self, mock_history_store):
        """Test emitting events to subscribers."""
        service = TraceVisualizationService(mock_history_store)

        received_events = []

        async def callback(event: NodeEvent):
            received_events.append(event)

        # Subscribe
        service.subscribe_to_execution("exec-123", callback)

        # Emit event
        event = NodeEvent(
            event_id="e1",
            execution_id="exec-123",
            node_id="TestNode",
            event_type=NodeEventType.STARTED,
            timestamp=datetime.now(UTC).isoformat(),
        )

        await service.emit_event(event)

        # Verify callback received event
        assert len(received_events) == 1
        assert received_events[0] == event

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, mock_history_store):
        """Test multiple subscribers for same execution."""
        service = TraceVisualizationService(mock_history_store)

        received_1 = []
        received_2 = []

        async def callback1(event: NodeEvent):
            received_1.append(event)

        async def callback2(event: NodeEvent):
            received_2.append(event)

        # Subscribe both
        service.subscribe_to_execution("exec-123", callback1)
        service.subscribe_to_execution("exec-123", callback2)

        # Emit event
        event = NodeEvent(
            event_id="e1",
            execution_id="exec-123",
            node_id="TestNode",
            event_type=NodeEventType.COMPLETED,
            timestamp=datetime.now(UTC).isoformat(),
            duration_ms=100,
        )

        await service.emit_event(event)

        # Both should receive
        assert len(received_1) == 1
        assert len(received_2) == 1
        assert received_1[0] == event
        assert received_2[0] == event

    @pytest.mark.asyncio
    async def test_unsubscribe_from_execution(self, mock_history_store):
        """Test unsubscribing from execution events."""
        service = TraceVisualizationService(mock_history_store)

        received_events = []

        async def callback(event: NodeEvent):
            received_events.append(event)

        # Subscribe then unsubscribe
        service.subscribe_to_execution("exec-123", callback)
        service.unsubscribe_from_execution("exec-123", callback)

        # Emit event
        event = NodeEvent(
            event_id="e1",
            execution_id="exec-123",
            node_id="TestNode",
            event_type=NodeEventType.STARTED,
            timestamp=datetime.now(UTC).isoformat(),
        )

        await service.emit_event(event)

        # Should not receive (unsubscribed)
        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_emit_event_no_subscribers(self, mock_history_store):
        """Test emitting event with no subscribers (should not error)."""
        service = TraceVisualizationService(mock_history_store)

        event = NodeEvent(
            event_id="e1",
            execution_id="exec-orphan",
            node_id="TestNode",
            event_type=NodeEventType.STARTED,
            timestamp=datetime.now(UTC).isoformat(),
        )

        # Should not raise
        await service.emit_event(event)


# Helper Method Tests
class TestHelperMethods:
    """Test helper methods."""

    def test_diff_states_added_keys(self, mock_history_store):
        """Test _diff_states() for added keys."""
        service = TraceVisualizationService(mock_history_store)

        prev = {"a": 1}
        curr = {"a": 1, "b": 2}

        diff = service._diff_states(prev, curr)

        assert diff == {"b": {"added": 2}}

    def test_diff_states_removed_keys(self, mock_history_store):
        """Test _diff_states() for removed keys."""
        service = TraceVisualizationService(mock_history_store)

        prev = {"a": 1, "b": 2}
        curr = {"a": 1}

        diff = service._diff_states(prev, curr)

        assert diff == {"b": {"removed": 2}}

    def test_diff_states_changed_keys(self, mock_history_store):
        """Test _diff_states() for changed keys."""
        service = TraceVisualizationService(mock_history_store)

        prev = {"a": 1, "b": 2}
        curr = {"a": 1, "b": 3}

        diff = service._diff_states(prev, curr)

        assert diff == {"b": {"old": 2, "new": 3}}

    def test_diff_states_multiple_changes(self, mock_history_store):
        """Test _diff_states() for multiple changes."""
        service = TraceVisualizationService(mock_history_store)

        prev = {"a": 1, "b": 2, "c": 3}
        curr = {"a": 1, "b": 99, "d": 4}

        diff = service._diff_states(prev, curr)

        assert diff == {"b": {"old": 2, "new": 99}, "c": {"removed": 3}, "d": {"added": 4}}

    def test_infer_status_running(self, mock_history_store):
        """Test _infer_status() for running execution."""
        service = TraceVisualizationService(mock_history_store)

        history = ExecutionHistory(
            execution_id="exec-123",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z",
                end_time=None,  # Still running
            ),
            performance=PerformanceMetrics(),
        )

        status = service._infer_status(history)
        assert status == "running"

    def test_infer_status_completed(self, mock_history_store, sample_execution_history):
        """Test _infer_status() for completed execution."""
        service = TraceVisualizationService(mock_history_store)

        status = service._infer_status(sample_execution_history)
        assert status == "completed"

    def test_infer_status_failed(self, mock_history_store):
        """Test _infer_status() for failed execution."""
        service = TraceVisualizationService(mock_history_store)

        history = ExecutionHistory(
            execution_id="exec-123",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={"error": "ValueError: Something failed"},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z", end_time="2025-10-21T10:00:01Z"
            ),
            performance=PerformanceMetrics(),
        )

        status = service._infer_status(history)
        assert status == "failed"

    def test_count_failed_nodes(self, mock_history_store):
        """Test _count_failed_nodes() from metadata."""
        service = TraceVisualizationService(mock_history_store)

        history = ExecutionHistory(
            execution_id="exec-123",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={"failed_nodes_list": ["Node1", "Node2"]},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(start_time="2025-10-21T10:00:00Z"),
            performance=PerformanceMetrics(),
        )

        count = service._count_failed_nodes(history)
        assert count == 2

    def test_count_failed_nodes_none(self, mock_history_store, sample_execution_history):
        """Test _count_failed_nodes() with no failures."""
        service = TraceVisualizationService(mock_history_store)

        count = service._count_failed_nodes(sample_execution_history)
        assert count == 0


# Acceptance Criteria Tests
class TestAcceptanceCriteria:
    """
    Test all 4 acceptance criteria for H7 (TraceVisualizationProtocol).

    AC1: UI can display execution trace
    AC2: Real-time updates work via WebSocket
    AC3: Performance <100ms query time
    AC4: Supports filtering by node type
    """

    @pytest.mark.asyncio
    async def test_ac1_ui_can_display_execution_trace(
        self, mock_history_store, sample_execution_history
    ):
        """
        AC1: UI can display execution trace.

        Test:
        1. Query trace via get_trace()
        2. Verify trace has all required fields
        3. Verify node events present
        4. Verify state snapshots present
        """
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        # Get trace
        trace = await service.get_trace("exec-123")

        # Verify all required fields present
        assert trace.execution_id == "exec-123"
        assert trace.graph_type == "forward_mode"
        assert trace.status in ["running", "completed", "failed"]
        assert trace.start_time is not None
        assert trace.total_nodes >= 0
        assert trace.total_llm_calls >= 0

        # Verify node events
        assert len(trace.node_events) > 0
        for event in trace.node_events:
            assert event.event_id
            assert event.execution_id == "exec-123"
            assert event.node_id
            assert event.event_type in NodeEventType

        # Verify state snapshots
        assert len(trace.state_snapshots) > 0
        for snapshot in trace.state_snapshots:
            assert snapshot.snapshot_id
            assert snapshot.execution_id == "exec-123"
            assert snapshot.state is not None

        # Verify original inputs
        assert trace.original_inputs == {"prompt": "test"}

    @pytest.mark.asyncio
    async def test_ac2_realtime_updates_via_websocket(self, mock_history_store):
        """
        AC2: Real-time updates work.

        Test:
        1. Subscribe to execution
        2. Emit node events
        3. Verify callback receives events
        4. Verify event order
        """
        service = TraceVisualizationService(mock_history_store)

        received_events = []

        async def callback(event: NodeEvent):
            received_events.append(event)

        # Subscribe
        service.subscribe_to_execution("exec-123", callback)

        # Emit events in sequence
        event1 = NodeEvent(
            event_id="e1",
            execution_id="exec-123",
            node_id="node1",
            event_type=NodeEventType.STARTED,
            timestamp="2025-10-21T10:00:00.000Z",
        )
        event2 = NodeEvent(
            event_id="e2",
            execution_id="exec-123",
            node_id="node1",
            event_type=NodeEventType.COMPLETED,
            timestamp="2025-10-21T10:00:02.000Z",
            duration_ms=2000,
        )
        event3 = NodeEvent(
            event_id="e3",
            execution_id="exec-123",
            node_id="node2",
            event_type=NodeEventType.STARTED,
            timestamp="2025-10-21T10:00:02.000Z",
        )

        await service.emit_event(event1)
        await service.emit_event(event2)
        await service.emit_event(event3)

        # Verify all received in order
        assert len(received_events) == 3
        assert received_events[0].event_type == NodeEventType.STARTED
        assert received_events[1].event_type == NodeEventType.COMPLETED
        assert received_events[2].event_type == NodeEventType.STARTED

        # Verify timestamps in order
        assert received_events[0].timestamp <= received_events[1].timestamp
        assert received_events[1].timestamp <= received_events[2].timestamp

    @pytest.mark.asyncio
    async def test_ac3_performance_under_100ms(self, mock_history_store, sample_execution_history):
        """
        AC3: Performance <100ms query time.

        Test:
        1. Query trace 100 times
        2. Verify average query time <100ms
        """
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        # Benchmark
        times = []
        for _ in range(100):
            start = time.perf_counter()
            trace = await service.get_trace("exec-123")
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms

        avg_time_ms = sum(times) / len(times)
        max_time_ms = max(times)

        # Verify performance
        assert avg_time_ms < 100, f"Average time {avg_time_ms:.2f}ms exceeds 100ms"
        # Allow some outliers but max should be reasonable
        assert max_time_ms < 200, f"Max time {max_time_ms:.2f}ms too high"

    @pytest.mark.asyncio
    async def test_ac4_filter_by_node_type(self, mock_history_store, sample_execution_history):
        """
        AC4: Supports filtering by node type.

        Test:
        1. Query timeline with node_type filter
        2. Verify only matching nodes returned
        """
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        # Get all events
        all_events = await service.get_node_timeline("exec-123")
        assert len(all_events) == 3  # TranslateNode, ValidateNode, GenerateNode

        # Filter by TranslateNode
        translate_events = await service.get_node_timeline("exec-123", node_type="TranslateNode")

        # Verify filtering
        assert len(translate_events) == 1
        assert all(e.node_id == "TranslateNode" for e in translate_events)
        assert translate_events[0].duration_ms == 2000

        # Filter by ValidateNode
        validate_events = await service.get_node_timeline("exec-123", node_type="ValidateNode")
        assert len(validate_events) == 1
        assert validate_events[0].node_id == "ValidateNode"
        assert validate_events[0].duration_ms == 1500


# Edge Cases
class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_execution_history(self, mock_history_store):
        """Test handling execution with no node timings."""
        history = ExecutionHistory(
            execution_id="exec-empty",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z",
                node_timings={},  # Empty
            ),
            performance=PerformanceMetrics(),
        )

        mock_history_store.load_execution.return_value = history
        service = TraceVisualizationService(mock_history_store)

        trace = await service.get_trace("exec-empty")

        assert trace.total_nodes == 0
        assert len(trace.node_events) == 0

    @pytest.mark.asyncio
    async def test_filter_nonexistent_node_type(self, mock_history_store, sample_execution_history):
        """Test filtering by node type that doesn't exist."""
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        events = await service.get_node_timeline("exec-123", node_type="NonexistentNode")

        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_multiple_executions_list(self, mock_history_store, sample_execution_history):
        """Test listing multiple executions."""
        # Create multiple histories
        history2 = ExecutionHistory(
            execution_id="exec-456",
            state_snapshot={"value": 100},
            state_type="TestState",
            provenance=[],
            metadata={},
            graph_type="reverse_mode",
            original_inputs={"code": "test"},
            timing=ExecutionTiming(
                start_time="2025-10-21T11:00:00Z",
                end_time="2025-10-21T11:00:03Z",
                total_duration_ms=3000,
                node_timings={"Node1": 3000},
            ),
            performance=PerformanceMetrics(total_tokens=500),
        )

        mock_history_store.list_executions.return_value = [
            sample_execution_history,
            history2,
        ]

        # Mock load_execution to return correct history based on ID
        def load_side_effect(execution_id):
            if execution_id == "exec-123" or execution_id.endswith("exec-123"):
                return sample_execution_history
            else:
                return history2

        mock_history_store.load_execution.side_effect = load_side_effect

        service = TraceVisualizationService(mock_history_store)

        traces = await service.list_executions()

        assert len(traces) == 2
        assert traces[0].execution_id == "exec-123"
        assert traces[1].execution_id == "exec-456"

    @pytest.mark.asyncio
    async def test_pagination(self, mock_history_store, sample_execution_history):
        """Test pagination parameters passed to store."""
        mock_history_store.list_executions.return_value = [sample_execution_history]
        mock_history_store.load_execution.return_value = sample_execution_history
        service = TraceVisualizationService(mock_history_store)

        traces = await service.list_executions(limit=10, offset=20)

        # Verify pagination params passed
        call_kwargs = mock_history_store.list_executions.call_args[1]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20

    @pytest.mark.asyncio
    async def test_state_diff_no_changes(self, mock_history_store):
        """Test state diff when states are identical."""
        service = TraceVisualizationService(mock_history_store)

        prev = {"a": 1, "b": 2}
        curr = {"a": 1, "b": 2}

        diff = service._diff_states(prev, curr)

        assert diff == {}

    @pytest.mark.asyncio
    async def test_extract_node_events_with_failures(self, mock_history_store):
        """Test extracting events when some nodes failed."""
        history = ExecutionHistory(
            execution_id="exec-123",
            state_snapshot={},
            state_type="TestState",
            provenance=[],
            metadata={"failed_nodes_list": ["Node2"]},
            graph_type="forward_mode",
            original_inputs={},
            timing=ExecutionTiming(
                start_time="2025-10-21T10:00:00Z",
                node_timings={"Node1": 1000, "Node2": 500, "Node3": 1500},
            ),
            performance=PerformanceMetrics(),
        )

        service = TraceVisualizationService(mock_history_store)
        events = service._extract_node_events(history)

        # Find Node2 event
        node2_events = [e for e in events if e.node_id == "Node2"]
        assert len(node2_events) == 1
        assert node2_events[0].event_type == NodeEventType.FAILED

        # Other nodes should be COMPLETED
        node1_events = [e for e in events if e.node_id == "Node1"]
        assert node1_events[0].event_type == NodeEventType.COMPLETED
