# H7: TraceVisualizationProtocol - Preparation Document

**Date**: 2025-10-21
**Status**: Planning
**Phase**: 5 (Week 5)

---

## Overview

H7 (TraceVisualizationProtocol) defines the interface for exposing graph execution traces to UI, enabling real-time monitoring, debugging, and performance analysis.

## Goals

1. **Execution Trace Access**: Query execution traces by execution_id
2. **Node Timeline**: Get chronological node execution events
3. **State History**: Track state changes throughout execution
4. **Real-Time Updates**: Support WebSocket for live execution monitoring
5. **Filtering & Search**: Enable querying by node type, time range, performance

## Context

### Dependencies

**Blocked By**:
- ✅ H11 (ExecutionHistorySchema) - **RESOLVED**: Provides ExecutionHistory data model
- ✅ H2 (StatePersistence) - **RESOLVED**: Provides GraphState storage

**Blocks**:
- UX features (real-time graph visualization)
- Debugging tools
- Performance monitoring dashboards

**Related**:
- H4 ParallelExecutor: Generates node execution events
- H5 ErrorRecovery: Error events need to be tracked
- H3 CachingStrategy: Cache hit/miss events
- H16 ConcurrencyModel: Concurrency metrics

### Existing Components

From H11 (ExecutionHistory):
```python
class ExecutionHistory(GraphState):
    graph_type: str
    original_inputs: dict[str, Any]
    timing: ExecutionTiming
    performance: PerformanceMetrics
    is_replay: bool
    original_execution_id: str | None

class ExecutionHistoryStore(StatePersistence[StateT]):
    async def save_execution(...) -> ExecutionHistory
    async def load_execution(execution_id) -> ExecutionHistory
    async def list_executions(...) -> list[ExecutionHistory]
    async def get_slow_executions(...) -> list[ExecutionHistory]
    async def get_statistics(...) -> dict
    async def replay_execution(execution_id) -> ExecutionHistory
```

From H4 (ParallelExecutor):
```python
@dataclass
class NodeResult(Generic[StateT]):
    node: BaseNode[StateT]
    next_node: BaseNode[StateT] | End
    context: RunContext[StateT]
    execution_time_ms: float
    error: Exception | None
```

## Design

### Core Abstraction: TraceVisualizationProtocol

```python
from datetime import datetime
from typing import Protocol, Any
from uuid import UUID
from pydantic import BaseModel
from enum import Enum

class NodeEventType(str, Enum):
    """Type of node event."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"  # Cache hit

class NodeEvent(BaseModel):
    """
    Single node execution event.

    Represents a point-in-time event during node execution for timeline views.
    """
    event_id: str  # Unique event identifier
    execution_id: str  # Parent execution ID
    node_id: str  # Node identifier (e.g., "TranslateNode")
    event_type: NodeEventType
    timestamp: str  # ISO format
    duration_ms: float | None = None  # For COMPLETED/FAILED events
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    error: str | None = None  # For FAILED events
    metadata: dict[str, Any] = {}  # Cache status, retry attempt, etc.

class StateSnapshot(BaseModel):
    """
    Point-in-time state snapshot.

    Captures state at specific moments (before/after node execution).
    """
    snapshot_id: str  # Unique snapshot identifier
    execution_id: str  # Parent execution ID
    timestamp: str  # ISO format
    node_id: str  # Node that produced this state
    state: dict[str, Any]  # State snapshot
    diff: dict[str, Any] | None = None  # Changes from previous state

class ExecutionTrace(BaseModel):
    """
    Complete execution trace with all events and snapshots.

    Combines execution history, node events, and state snapshots for
    comprehensive execution visualization.
    """
    execution_id: str
    graph_type: str
    status: str  # "running", "completed", "failed"
    start_time: str
    end_time: str | None
    total_duration_ms: float | None

    # Events and snapshots
    node_events: list[NodeEvent]
    state_snapshots: list[StateSnapshot]

    # Aggregated metrics
    total_nodes: int
    failed_nodes: int
    cached_nodes: int
    total_llm_calls: int
    total_tokens: int | None

    # Original inputs
    original_inputs: dict[str, Any]
    final_state: dict[str, Any] | None

class TraceVisualizationProtocol(Protocol):
    """
    Protocol for exposing execution traces to UI.

    Defines the interface that any trace visualization service must implement.
    Supports querying execution traces, node timelines, and state history.
    """

    def get_trace(self, execution_id: UUID | str) -> ExecutionTrace:
        """
        Get complete execution trace.

        Args:
            execution_id: Unique execution identifier

        Returns:
            ExecutionTrace with all events and snapshots

        Raises:
            ValueError: If execution_id not found
        """
        ...

    def get_node_timeline(
        self,
        execution_id: UUID | str,
        node_type: str | None = None
    ) -> list[NodeEvent]:
        """
        Get chronological node execution events.

        Args:
            execution_id: Unique execution identifier
            node_type: Optional filter by node type

        Returns:
            List of NodeEvents ordered by timestamp
        """
        ...

    def get_state_history(
        self,
        execution_id: UUID | str,
        include_diffs: bool = True
    ) -> list[StateSnapshot]:
        """
        Get state snapshots throughout execution.

        Args:
            execution_id: Unique execution identifier
            include_diffs: Whether to compute state diffs

        Returns:
            List of StateSnapshots ordered by timestamp
        """
        ...

    def list_executions(
        self,
        graph_type: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ExecutionTrace]:
        """
        List executions with filtering and pagination.

        Args:
            graph_type: Filter by graph type
            status: Filter by status ("running", "completed", "failed")
            start_time: Filter executions after this time
            end_time: Filter executions before this time
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of ExecutionTraces matching filters
        """
        ...
```

### Implementation: TraceVisualizationService

```python
class TraceVisualizationService:
    """
    Implementation of TraceVisualizationProtocol using ExecutionHistoryStore.

    Provides execution trace visualization backed by ExecutionHistory storage.
    Supports real-time updates via event streaming.

    Example:
        >>> store = ExecutionHistoryStore[TestState](...)
        >>> service = TraceVisualizationService(store)
        >>> trace = await service.get_trace("exec-123")
        >>> timeline = await service.get_node_timeline("exec-123", node_type="TranslateNode")
    """

    def __init__(self, history_store: ExecutionHistoryStore):
        self.store = history_store
        self._event_subscribers: dict[str, list[callable]] = {}

    async def get_trace(self, execution_id: UUID | str) -> ExecutionTrace:
        """Get complete execution trace from history store."""
        history = await self.store.load_execution(execution_id)

        # Build ExecutionTrace from ExecutionHistory
        return ExecutionTrace(
            execution_id=history.execution_id,
            graph_type=history.graph_type,
            status=self._infer_status(history),
            start_time=history.timing.start_time,
            end_time=history.timing.end_time,
            total_duration_ms=history.timing.total_duration_ms,
            node_events=self._extract_node_events(history),
            state_snapshots=self._extract_state_snapshots(history),
            total_nodes=len(history.timing.node_timings),
            failed_nodes=self._count_failed_nodes(history),
            cached_nodes=history.performance.cache_hits,
            total_llm_calls=history.performance.total_llm_calls,
            total_tokens=history.performance.total_tokens,
            original_inputs=history.original_inputs,
            final_state=history.state_snapshot,
        )

    async def get_node_timeline(
        self,
        execution_id: UUID | str,
        node_type: str | None = None
    ) -> list[NodeEvent]:
        """Extract node timeline from execution history."""
        history = await self.store.load_execution(execution_id)
        events = self._extract_node_events(history)

        if node_type:
            events = [e for e in events if e.node_id == node_type]

        return sorted(events, key=lambda e: e.timestamp)

    async def get_state_history(
        self,
        execution_id: UUID | str,
        include_diffs: bool = True
    ) -> list[StateSnapshot]:
        """Extract state snapshots from execution history."""
        history = await self.store.load_execution(execution_id)
        snapshots = self._extract_state_snapshots(history)

        if include_diffs:
            snapshots = self._compute_state_diffs(snapshots)

        return snapshots

    async def list_executions(
        self,
        graph_type: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[ExecutionTrace]:
        """List executions with filtering."""
        # Build filters for ExecutionHistoryStore
        filters = {}
        if graph_type:
            filters["graph_type"] = graph_type
        if start_time or end_time:
            filters["time_range"] = (start_time, end_time)

        # Query history store
        histories = await self.store.list_executions(
            filters=filters,
            limit=limit,
            offset=offset
        )

        # Convert to ExecutionTraces
        traces = []
        for history in histories:
            trace = await self.get_trace(history.execution_id)
            if status and trace.status != status:
                continue
            traces.append(trace)

        return traces

    # Event streaming for real-time updates
    def subscribe_to_execution(
        self,
        execution_id: str,
        callback: callable
    ):
        """
        Subscribe to real-time updates for an execution.

        Args:
            execution_id: Execution to monitor
            callback: Function called with NodeEvent on updates
        """
        if execution_id not in self._event_subscribers:
            self._event_subscribers[execution_id] = []
        self._event_subscribers[execution_id].append(callback)

    async def emit_event(self, event: NodeEvent):
        """
        Emit event to all subscribers.

        Called by ParallelExecutor during execution to push real-time updates.
        """
        execution_id = event.execution_id
        if execution_id in self._event_subscribers:
            for callback in self._event_subscribers[execution_id]:
                await callback(event)

    # Helper methods
    def _extract_node_events(self, history: ExecutionHistory) -> list[NodeEvent]:
        """Extract node events from execution history."""
        events = []
        for node_id, duration_ms in history.timing.node_timings.items():
            # Create COMPLETED event (or FAILED if in error metadata)
            event = NodeEvent(
                event_id=f"{history.execution_id}_{node_id}",
                execution_id=history.execution_id,
                node_id=node_id,
                event_type=NodeEventType.COMPLETED,
                timestamp=history.timing.start_time,  # Approximate
                duration_ms=duration_ms,
            )
            events.append(event)

        return events

    def _extract_state_snapshots(self, history: ExecutionHistory) -> list[StateSnapshot]:
        """Extract state snapshots from execution history."""
        # For now, just final state snapshot
        # Future: Store intermediate snapshots during execution
        snapshot = StateSnapshot(
            snapshot_id=f"{history.execution_id}_final",
            execution_id=history.execution_id,
            timestamp=history.timing.end_time or history.timing.start_time,
            node_id="final",
            state=history.state_snapshot,
        )
        return [snapshot]

    def _compute_state_diffs(self, snapshots: list[StateSnapshot]) -> list[StateSnapshot]:
        """Compute diffs between consecutive snapshots."""
        for i in range(1, len(snapshots)):
            prev_state = snapshots[i - 1].state
            curr_state = snapshots[i].state
            snapshots[i].diff = self._diff_states(prev_state, curr_state)

        return snapshots

    def _diff_states(self, prev: dict, curr: dict) -> dict:
        """Compute diff between two states."""
        diff = {}
        for key in curr:
            if key not in prev:
                diff[key] = {"added": curr[key]}
            elif prev[key] != curr[key]:
                diff[key] = {"old": prev[key], "new": curr[key]}

        for key in prev:
            if key not in curr:
                diff[key] = {"removed": prev[key]}

        return diff

    def _infer_status(self, history: ExecutionHistory) -> str:
        """Infer execution status from history."""
        if history.timing.end_time is None:
            return "running"

        # Check for errors in metadata
        if history.metadata.get("error"):
            return "failed"

        return "completed"

    def _count_failed_nodes(self, history: ExecutionHistory) -> int:
        """Count failed nodes from metadata."""
        return history.metadata.get("failed_nodes", 0)
```

## Acceptance Criteria

### AC1: UI can display execution trace ✓

**Test**: Query execution trace, verify all fields present
```python
async def test_ac1_ui_can_display_execution_trace():
    """
    AC1: UI can display execution trace.

    Test:
    1. Save execution with timing/performance
    2. Query trace via get_trace()
    3. Verify trace has all required fields
    4. Verify node events present
    5. Verify state snapshots present
    """
    store = ExecutionHistoryStore[TestState](...)
    service = TraceVisualizationService(store)

    # Save execution
    history = await store.save_execution(
        execution_id="exec-123",
        state=graph_state,
        timing=ExecutionTiming(...),
        performance=PerformanceMetrics(...),
        original_inputs={"prompt": "test"}
    )

    # Get trace
    trace = await service.get_trace("exec-123")

    # Verify fields
    assert trace.execution_id == "exec-123"
    assert trace.graph_type == "forward_mode"
    assert trace.status in ["running", "completed", "failed"]
    assert trace.node_events  # Has events
    assert trace.state_snapshots  # Has snapshots
    assert trace.original_inputs == {"prompt": "test"}
```

### AC2: Real-time updates work via WebSocket ✓

**Test**: Subscribe to execution, verify events received
```python
async def test_ac2_realtime_updates_via_websocket():
    """
    AC2: Real-time updates work.

    Test:
    1. Subscribe to execution
    2. Emit node events
    3. Verify callback receives events
    4. Verify event order
    """
    service = TraceVisualizationService(store)

    received_events = []
    async def callback(event: NodeEvent):
        received_events.append(event)

    # Subscribe
    service.subscribe_to_execution("exec-123", callback)

    # Emit events
    event1 = NodeEvent(
        event_id="e1",
        execution_id="exec-123",
        node_id="node1",
        event_type=NodeEventType.STARTED,
        timestamp=datetime.now(UTC).isoformat()
    )
    event2 = NodeEvent(
        event_id="e2",
        execution_id="exec-123",
        node_id="node1",
        event_type=NodeEventType.COMPLETED,
        timestamp=datetime.now(UTC).isoformat(),
        duration_ms=100
    )

    await service.emit_event(event1)
    await service.emit_event(event2)

    # Verify received
    assert len(received_events) == 2
    assert received_events[0].event_type == NodeEventType.STARTED
    assert received_events[1].event_type == NodeEventType.COMPLETED
```

### AC3: Performance <100ms query time ✓

**Test**: Benchmark get_trace() query performance
```python
async def test_ac3_performance_under_100ms():
    """
    AC3: Performance <100ms query time.

    Test:
    1. Save execution
    2. Query trace 100 times
    3. Verify average query time <100ms
    """
    import time

    service = TraceVisualizationService(store)

    # Save execution
    await store.save_execution(...)

    # Benchmark
    times = []
    for _ in range(100):
        start = time.perf_counter()
        trace = await service.get_trace("exec-123")
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    avg_time_ms = sum(times) / len(times)
    assert avg_time_ms < 100
```

### AC4: Supports filtering by node type ✓

**Test**: Filter node timeline by node type
```python
async def test_ac4_filter_by_node_type():
    """
    AC4: Supports filtering by node type.

    Test:
    1. Save execution with multiple node types
    2. Query timeline with node_type filter
    3. Verify only matching nodes returned
    """
    service = TraceVisualizationService(store)

    # Get all events
    all_events = await service.get_node_timeline("exec-123")

    # Filter by node type
    translate_events = await service.get_node_timeline("exec-123", node_type="TranslateNode")

    # Verify filtering
    assert all(e.node_id == "TranslateNode" for e in translate_events)
    assert len(translate_events) < len(all_events)
```

## Implementation Plan

### Phase 1: Core Protocol & Models
1. Create NodeEventType enum
2. Create NodeEvent, StateSnapshot, ExecutionTrace models
3. Create TraceVisualizationProtocol protocol

### Phase 2: Service Implementation
1. Create TraceVisualizationService class
2. Implement get_trace() using ExecutionHistoryStore
3. Implement get_node_timeline() with filtering
4. Implement get_state_history() with diffs

### Phase 3: Real-Time Updates
1. Add event subscription mechanism
2. Implement emit_event() for real-time push
3. Integration point for ParallelExecutor (future)

### Phase 4: Query & Filtering
1. Implement list_executions() with filters
2. Add pagination support
3. Add performance indexing hints

### Phase 5: Testing
1. Unit tests: All protocol methods
2. Integration tests: With ExecutionHistoryStore
3. Performance tests: <100ms query time
4. All acceptance criteria tests

### Phase 6: Documentation
1. Update HOLE_INVENTORY.md
2. Create H7_COMPLETION_SUMMARY.md
3. Export from `lift_sys.dspy_signatures`

## Constraints Propagated

### From H11: ExecutionHistorySchema

**Constraint**: MUST use ExecutionHistory as data source

**Reasoning**: All trace data comes from execution history

**Impact**: TraceVisualizationService wraps ExecutionHistoryStore

### To Future: WebSocket Integration

**Constraint**: SHOULD support WebSocket streaming

**Reasoning**: Real-time updates required for live monitoring

**Impact**: emit_event() provides hook for WebSocket broadcast

## Alternative Designs Considered

### 1. GraphQL with Subscriptions
**Pros**: Native real-time support, flexible queries
**Cons**: Additional complexity, dependency
**Decision**: Use Protocol + REST API for simplicity

### 2. Server-Sent Events (SSE)
**Pros**: Simpler than WebSocket, HTTP-based
**Cons**: Unidirectional only
**Decision**: Deferred - can add later

### 3. Polling-Based Updates
**Pros**: Simple, no WebSocket needed
**Cons**: Higher latency, more load
**Decision**: Use event subscription for real-time, polling as fallback

## Future Enhancements

1. **Intermediate State Snapshots**: Capture state after each node
2. **Event Replay**: Visual replay of execution timeline
3. **Performance Heatmap**: Visualize slow nodes
4. **Comparison View**: Compare two executions side-by-side
5. **Metrics Dashboard**: Aggregate metrics across executions
6. **Alerting**: Notify on slow executions or errors

---

**Status**: Ready for implementation
**Next Steps**: Implement TraceVisualizationProtocol → Create tests → Integrate with H11
