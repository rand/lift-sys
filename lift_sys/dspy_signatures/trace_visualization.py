"""
Trace Visualization Protocol (H7)

Interface for exposing graph execution traces to UI, enabling real-time monitoring,
debugging, and performance analysis.

This module provides:
1. Protocol for trace visualization services
2. Models for execution traces, node events, state snapshots
3. Real-time event streaming via subscriptions
4. Integration with ExecutionHistoryStore (H11)

Design Principles:
1. Query Performance: <100ms for trace queries
2. Real-Time Updates: Event streaming for live execution monitoring
3. Filtering & Search: Support node type, time range, status filters
4. State Diffs: Compute state changes between snapshots
5. UI-Friendly: Clean JSON-serializable models

Resolution for Hole H7: TraceVisualizationProtocol
Status: Implementation
Phase: 5 (Week 5)
Dependencies: H11 (ExecutionHistorySchema) - RESOLVED, H2 (StatePersistence) - RESOLVED
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from .execution_history import ExecutionHistory, ExecutionHistoryStore

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


class NodeEventType(str, Enum):
    """
    Type of node execution event.

    Events:
    - STARTED: Node execution began
    - COMPLETED: Node execution finished successfully
    - FAILED: Node execution failed with error
    - CACHED: Node result served from cache (no execution)
    """

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


class NodeEvent(BaseModel):
    """
    Single node execution event for timeline visualization.

    Represents a point-in-time event during node execution. Events are
    chronologically ordered to form an execution timeline.

    Example:
        >>> event = NodeEvent(
        ...     event_id="exec-123_node1_started",
        ...     execution_id="exec-123",
        ...     node_id="TranslateNode",
        ...     event_type=NodeEventType.STARTED,
        ...     timestamp="2025-10-21T10:00:00Z"
        ... )
    """

    event_id: str = Field(..., description="Unique event identifier")
    execution_id: str = Field(..., description="Parent execution ID")
    node_id: str = Field(..., description="Node identifier (e.g., 'TranslateNode')")
    event_type: NodeEventType = Field(..., description="Type of event")
    timestamp: str = Field(..., description="Event timestamp (ISO format)")
    duration_ms: float | None = Field(None, description="Duration for COMPLETED/FAILED events")
    inputs: dict[str, Any] = Field(default_factory=dict, description="Node inputs")
    outputs: dict[str, Any] = Field(default_factory=dict, description="Node outputs")
    error: str | None = Field(None, description="Error message for FAILED events")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (cache status, retry attempt)"
    )


class StateSnapshot(BaseModel):
    """
    Point-in-time state snapshot for state history visualization.

    Captures graph state at specific moments (before/after node execution).
    Diffs show what changed between consecutive snapshots.

    Example:
        >>> snapshot = StateSnapshot(
        ...     snapshot_id="exec-123_final",
        ...     execution_id="exec-123",
        ...     timestamp="2025-10-21T10:00:05Z",
        ...     node_id="final",
        ...     state={"value": 42, "prompt": "test"}
        ... )
    """

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    execution_id: str = Field(..., description="Parent execution ID")
    timestamp: str = Field(..., description="Snapshot timestamp (ISO format)")
    node_id: str = Field(..., description="Node that produced this state")
    state: dict[str, Any] = Field(..., description="State snapshot")
    diff: dict[str, Any] | None = Field(None, description="Changes from previous state")


class ExecutionTrace(BaseModel):
    """
    Complete execution trace with all events and snapshots.

    Combines execution history, node events, and state snapshots for
    comprehensive execution visualization. Provides aggregated metrics
    for dashboard displays.

    Example:
        >>> trace = ExecutionTrace(
        ...     execution_id="exec-123",
        ...     graph_type="forward_mode",
        ...     status="completed",
        ...     start_time="2025-10-21T10:00:00Z",
        ...     end_time="2025-10-21T10:00:05Z",
        ...     total_duration_ms=5000,
        ...     node_events=[...],
        ...     state_snapshots=[...],
        ...     total_nodes=3,
        ...     failed_nodes=0,
        ...     cached_nodes=1,
        ...     total_llm_calls=2,
        ...     total_tokens=1500,
        ...     original_inputs={"prompt": "test"},
        ...     final_state={"result": "success"}
        ... )
    """

    execution_id: str = Field(..., description="Unique execution identifier")
    graph_type: str = Field(..., description="Type of graph executed")
    status: str = Field(..., description="Execution status (running/completed/failed)")
    start_time: str = Field(..., description="Execution start time (ISO format)")
    end_time: str | None = Field(None, description="Execution end time (ISO format)")
    total_duration_ms: float | None = Field(
        None, description="Total execution time in milliseconds"
    )

    # Events and snapshots
    node_events: list[NodeEvent] = Field(
        default_factory=list, description="Chronological node execution events"
    )
    state_snapshots: list[StateSnapshot] = Field(
        default_factory=list, description="State snapshots throughout execution"
    )

    # Aggregated metrics
    total_nodes: int = Field(0, description="Total nodes executed")
    failed_nodes: int = Field(0, description="Number of failed nodes")
    cached_nodes: int = Field(0, description="Number of cached nodes (cache hits)")
    total_llm_calls: int = Field(0, description="Total LLM API calls")
    total_tokens: int | None = Field(None, description="Total tokens consumed")

    # Inputs and outputs
    original_inputs: dict[str, Any] = Field(
        default_factory=dict, description="Original execution inputs"
    )
    final_state: dict[str, Any] | None = Field(None, description="Final state snapshot")


class TraceVisualizationProtocol(Protocol):
    """
    Protocol for exposing execution traces to UI.

    Defines the interface that any trace visualization service must implement.
    Supports querying execution traces, node timelines, state history, and
    real-time event streaming.

    Implementations should provide:
    - Execution trace queries (<100ms)
    - Node timeline filtering by node type
    - State snapshot history with diffs
    - Real-time event subscriptions
    - List executions with filters and pagination
    """

    async def get_trace(self, execution_id: UUID | str) -> ExecutionTrace:
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

    async def get_node_timeline(
        self, execution_id: UUID | str, node_type: str | None = None
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

    async def get_state_history(
        self, execution_id: UUID | str, include_diffs: bool = True
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

    async def list_executions(
        self,
        graph_type: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
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


class TraceVisualizationService:
    """
    Implementation of TraceVisualizationProtocol using ExecutionHistoryStore.

    Provides execution trace visualization backed by ExecutionHistory storage.
    Supports real-time updates via event streaming and efficient querying with
    filters.

    Example:
        >>> from lift_sys.dspy_signatures import ExecutionHistoryStore
        >>> store = ExecutionHistoryStore[TestState](...)
        >>> service = TraceVisualizationService(store)
        >>>
        >>> # Get complete trace
        >>> trace = await service.get_trace("exec-123")
        >>>
        >>> # Get timeline filtered by node type
        >>> timeline = await service.get_node_timeline("exec-123", node_type="TranslateNode")
        >>>
        >>> # Subscribe to real-time updates
        >>> async def on_event(event: NodeEvent):
        ...     print(f"Node {event.node_id}: {event.event_type}")
        >>> service.subscribe_to_execution("exec-123", on_event)
    """

    def __init__(self, history_store: ExecutionHistoryStore):
        """
        Initialize trace visualization service.

        Args:
            history_store: ExecutionHistoryStore for data access
        """
        self.store = history_store
        self._event_subscribers: dict[str, list[callable]] = {}

    async def get_trace(self, execution_id: UUID | str) -> ExecutionTrace:
        """
        Get complete execution trace from history store.

        Loads execution history and constructs ExecutionTrace with all
        node events, state snapshots, and aggregated metrics.

        Args:
            execution_id: Unique execution identifier

        Returns:
            ExecutionTrace with complete execution data

        Raises:
            ValueError: If execution_id not found in history store
        """
        execution_id_str = str(execution_id)
        history = await self.store.load_execution(execution_id_str)

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
        self, execution_id: UUID | str, node_type: str | None = None
    ) -> list[NodeEvent]:
        """
        Extract node timeline from execution history.

        Provides chronological list of node execution events, optionally
        filtered by node type.

        Args:
            execution_id: Unique execution identifier
            node_type: Optional filter by node type

        Returns:
            List of NodeEvents ordered by timestamp
        """
        execution_id_str = str(execution_id)
        history = await self.store.load_execution(execution_id_str)
        events = self._extract_node_events(history)

        if node_type:
            events = [e for e in events if e.node_id == node_type]

        return sorted(events, key=lambda e: e.timestamp)

    async def get_state_history(
        self, execution_id: UUID | str, include_diffs: bool = True
    ) -> list[StateSnapshot]:
        """
        Extract state snapshots from execution history.

        Provides state snapshots throughout execution, optionally with
        diffs showing changes between consecutive states.

        Args:
            execution_id: Unique execution identifier
            include_diffs: Whether to compute state diffs

        Returns:
            List of StateSnapshots ordered by timestamp
        """
        execution_id_str = str(execution_id)
        history = await self.store.load_execution(execution_id_str)
        snapshots = self._extract_state_snapshots(history)

        if include_diffs and len(snapshots) > 1:
            snapshots = self._compute_state_diffs(snapshots)

        return snapshots

    async def list_executions(
        self,
        graph_type: str | None = None,
        status: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionTrace]:
        """
        List executions with filtering and pagination.

        Queries ExecutionHistoryStore with filters and converts results
        to ExecutionTrace format for UI consumption.

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
        # Build filters for ExecutionHistoryStore
        filters = {}
        if graph_type:
            filters["graph_type"] = graph_type
        if start_time or end_time:
            filters["time_range"] = (start_time, end_time)

        # Query history store
        histories = await self.store.list_executions(filters=filters, limit=limit, offset=offset)

        # Convert to ExecutionTraces and filter by status
        traces = []
        for history in histories:
            trace = await self.get_trace(history.execution_id)
            if status and trace.status != status:
                continue
            traces.append(trace)

        return traces

    # Event streaming for real-time updates

    def subscribe_to_execution(self, execution_id: str, callback: callable):
        """
        Subscribe to real-time updates for an execution.

        Registers callback to be called when new events are emitted for
        the specified execution. Useful for WebSocket integration.

        Args:
            execution_id: Execution to monitor
            callback: Async function called with NodeEvent on updates
        """
        if execution_id not in self._event_subscribers:
            self._event_subscribers[execution_id] = []
        self._event_subscribers[execution_id].append(callback)

    def unsubscribe_from_execution(self, execution_id: str, callback: callable):
        """
        Unsubscribe from execution updates.

        Args:
            execution_id: Execution to stop monitoring
            callback: Callback to remove
        """
        if execution_id in self._event_subscribers:
            if callback in self._event_subscribers[execution_id]:
                self._event_subscribers[execution_id].remove(callback)

    async def emit_event(self, event: NodeEvent):
        """
        Emit event to all subscribers.

        Called by ParallelExecutor during execution to push real-time updates.
        All registered callbacks for this execution will be invoked.

        Args:
            event: NodeEvent to emit
        """
        execution_id = event.execution_id
        if execution_id in self._event_subscribers:
            for callback in self._event_subscribers[execution_id]:
                await callback(event)

    # Helper methods

    def _extract_node_events(self, history: ExecutionHistory) -> list[NodeEvent]:
        """
        Extract node events from execution history.

        Converts node timing data into NodeEvent objects for timeline visualization.

        Args:
            history: ExecutionHistory to extract from

        Returns:
            List of NodeEvents
        """
        events = []
        for node_id, duration_ms in history.timing.node_timings.items():
            # Check if node failed (from metadata)
            failed_nodes = history.metadata.get("failed_nodes_list", [])
            event_type = (
                NodeEventType.FAILED if node_id in failed_nodes else NodeEventType.COMPLETED
            )

            # Create event
            event = NodeEvent(
                event_id=f"{history.execution_id}_{node_id}",
                execution_id=history.execution_id,
                node_id=node_id,
                event_type=event_type,
                timestamp=history.timing.start_time,  # Approximate (full timeline not yet stored)
                duration_ms=duration_ms,
            )
            events.append(event)

        return events

    def _extract_state_snapshots(self, history: ExecutionHistory) -> list[StateSnapshot]:
        """
        Extract state snapshots from execution history.

        Currently extracts final state snapshot. Future enhancement: store
        intermediate snapshots during execution.

        Args:
            history: ExecutionHistory to extract from

        Returns:
            List of StateSnapshots
        """
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
        """
        Compute diffs between consecutive snapshots.

        Modifies snapshots in-place to add diff field showing changes from
        previous state.

        Args:
            snapshots: List of StateSnapshots

        Returns:
            Modified list with diffs computed
        """
        for i in range(1, len(snapshots)):
            prev_state = snapshots[i - 1].state
            curr_state = snapshots[i].state
            snapshots[i].diff = self._diff_states(prev_state, curr_state)

        return snapshots

    def _diff_states(self, prev: dict, curr: dict) -> dict:
        """
        Compute diff between two states.

        Returns dictionary with keys:
        - {key: {"added": value}} for new keys
        - {key: {"old": old_value, "new": new_value}} for changed keys
        - {key: {"removed": value}} for deleted keys

        Args:
            prev: Previous state
            curr: Current state

        Returns:
            Dictionary with state changes
        """
        diff = {}

        # Check for added/changed keys
        for key in curr:
            if key not in prev:
                diff[key] = {"added": curr[key]}
            elif prev[key] != curr[key]:
                diff[key] = {"old": prev[key], "new": curr[key]}

        # Check for removed keys
        for key in prev:
            if key not in curr:
                diff[key] = {"removed": prev[key]}

        return diff

    def _infer_status(self, history: ExecutionHistory) -> str:
        """
        Infer execution status from history.

        Returns:
            "running" if no end_time
            "failed" if error in metadata
            "completed" otherwise
        """
        if history.timing.end_time is None:
            return "running"

        # Check for errors in metadata
        if history.metadata.get("error"):
            return "failed"

        return "completed"

    def _count_failed_nodes(self, history: ExecutionHistory) -> int:
        """
        Count failed nodes from metadata.

        Args:
            history: ExecutionHistory to check

        Returns:
            Number of failed nodes
        """
        failed_nodes_list = history.metadata.get("failed_nodes_list", [])
        return len(failed_nodes_list)


__all__ = [
    "NodeEventType",
    "NodeEvent",
    "StateSnapshot",
    "ExecutionTrace",
    "TraceVisualizationProtocol",
    "TraceVisualizationService",
]
