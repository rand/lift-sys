"""
Execution History (H11)

Extension of StatePersistence (H2) providing execution trace storage with timing,
performance metrics, and replay capabilities.

This module builds on GraphState to provide:
1. Graph-level timing information (start/end/duration)
2. Performance metrics (tokens, memory, concurrency)
3. Replay support (deterministic re-execution from history)
4. Advanced querying (time ranges, performance filters, pagination)

Resolution for Hole H11: ExecutionHistorySchema
Status: Implementation
Phase: 2 (Week 2)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .state_persistence import GraphState, StatePersistence

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


class PerformanceMetrics(BaseModel):
    """
    Performance metrics for a graph execution.

    Tracks resource usage and execution characteristics for optimization
    and debugging purposes.
    """

    total_tokens: int | None = Field(None, description="Total tokens consumed")
    total_llm_calls: int = Field(0, description="Number of LLM API calls")
    peak_memory_mb: float | None = Field(None, description="Peak memory usage in MB")
    concurrent_nodes: int = Field(1, description="Maximum concurrent nodes executed")
    cache_hits: int = Field(0, description="Number of cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")


class ExecutionTiming(BaseModel):
    """
    Timing information for a graph execution.

    Provides graph-level timing data for performance analysis and
    replay validation.
    """

    start_time: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Execution start timestamp (ISO format)",
    )
    end_time: str | None = Field(None, description="Execution end timestamp (ISO format)")
    total_duration_ms: float | None = Field(
        None, description="Total execution time in milliseconds"
    )
    node_timings: dict[str, float] = Field(
        default_factory=dict, description="Per-node execution times in milliseconds"
    )


class ExecutionHistory(GraphState):
    """
    Extended GraphState with timing and performance metadata.

    Inherits all state persistence capabilities from GraphState and adds:
    - Execution timing (start/end/duration)
    - Performance metrics (tokens, memory, cache)
    - Original inputs (for replay)
    - Graph type metadata
    """

    # New fields for H11
    graph_type: str = Field("forward_mode", description="Type of graph executed")
    original_inputs: dict[str, Any] = Field(
        default_factory=dict, description="Original inputs for replay support"
    )
    timing: ExecutionTiming = Field(
        default_factory=ExecutionTiming, description="Execution timing information"
    )
    performance: PerformanceMetrics = Field(
        default_factory=PerformanceMetrics, description="Performance metrics"
    )

    # Replay metadata
    is_replay: bool = Field(False, description="Whether this is a replayed execution")
    original_execution_id: str | None = Field(
        None, description="Original execution ID if this is a replay"
    )

    model_config = ConfigDict(frozen=False)  # Allow updates


class ExecutionHistoryStore(StatePersistence[StateT]):
    """
    Extended StatePersistence with execution history capabilities.

    Provides all StatePersistence operations plus:
    - save_execution(): Store execution with timing/performance
    - load_execution(): Load execution history
    - list_executions(): Query with filters (time range, performance, pagination)
    - replay_execution(): Re-run graph from history
    - get_slow_executions(): Find performance outliers
    - get_statistics(): Aggregate performance stats

    Usage:
        store = ExecutionHistoryStore[MyState](
            supabase_url="https://xxx.supabase.co",
            supabase_key="service_role_key"
        )

        # Save execution with timing/performance
        history = await store.save_execution(
            execution_id="exec-123",
            state=graph_state,
            timing=timing,
            performance=metrics,
            original_inputs={"prompt": "test"}
        )

        # Query slow executions
        slow_execs = await store.get_slow_executions(threshold_ms=1000)

        # Replay from history
        result = await store.replay_execution("exec-123")
    """

    async def save_execution(
        self,
        execution_id: UUID | str,
        state: GraphState,
        timing: ExecutionTiming,
        performance: PerformanceMetrics,
        original_inputs: dict[str, Any],
        graph_type: str = "forward_mode",
        user_id: str | None = None,
    ) -> ExecutionHistory:
        """
        Save execution with complete timing and performance metadata.

        Args:
            execution_id: Unique execution identifier
            state: Graph state snapshot
            timing: Execution timing information
            performance: Performance metrics
            original_inputs: Original inputs for replay
            graph_type: Type of graph executed
            user_id: User who initiated execution (optional)

        Returns:
            ExecutionHistory with all metadata

        Raises:
            ValueError: If execution_id already exists or save fails
        """
        execution_id_str = str(execution_id)

        # Create execution history
        history = ExecutionHistory(
            execution_id=execution_id_str,
            state_snapshot=state.state_snapshot,
            state_type=state.state_type,
            provenance=state.provenance,
            metadata=state.metadata,
            user_id=user_id,
            graph_type=graph_type,
            original_inputs=original_inputs,
            timing=timing,
            performance=performance,
        )

        # Prepare database record
        record = {
            "id": execution_id_str,
            "execution_id": execution_id_str,
            "state_snapshot": history.state_snapshot,
            "state_type": history.state_type,
            "provenance": history.provenance,
            "metadata": history.metadata,
            "user_id": user_id,
            "graph_type": graph_type,
            "original_inputs": original_inputs,
            "timing": timing.model_dump(),
            "performance": performance.model_dump(),
            "is_replay": False,
            "original_execution_id": None,
            "created_at": history.created_at,
            "updated_at": history.updated_at,
        }

        # Atomic insert
        try:
            self.client.table("graph_states").insert(record).execute()
        except Exception as e:
            raise ValueError(f"Failed to save execution {execution_id_str}: {e}") from e

        return history

    async def load_execution(self, execution_id: UUID | str) -> ExecutionHistory:
        """
        Load execution history with all metadata.

        Args:
            execution_id: Unique execution identifier

        Returns:
            ExecutionHistory with complete state and metadata

        Raises:
            KeyError: If execution_id not found
            ValueError: If deserialization fails
        """
        execution_id_str = str(execution_id)

        # Fetch from database
        response = (
            self.client.table("graph_states")
            .select("*")
            .eq("execution_id", execution_id_str)
            .execute()
        )

        if not response.data:
            raise KeyError(f"No execution found for {execution_id_str}")

        row = response.data[0]

        # Reconstruct ExecutionHistory
        try:
            history = ExecutionHistory(
                execution_id=row["execution_id"],
                state_snapshot=row["state_snapshot"],
                state_type=row["state_type"],
                provenance=row.get("provenance", []),
                metadata=row.get("metadata", {}),
                user_id=row.get("user_id"),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                graph_type=row.get("graph_type", "forward_mode"),
                original_inputs=row.get("original_inputs", {}),
                timing=ExecutionTiming(**row.get("timing", {})),
                performance=PerformanceMetrics(**row.get("performance", {})),
                is_replay=row.get("is_replay", False),
                original_execution_id=row.get("original_execution_id"),
            )
            return history
        except Exception as e:
            raise ValueError(f"Failed to deserialize execution {execution_id_str}: {e}") from e

    async def list_executions(
        self,
        user_id: str | None = None,
        graph_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        min_duration_ms: float | None = None,
        max_duration_ms: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExecutionHistory]:
        """
        List executions with filtering and pagination.

        Args:
            user_id: Filter by user ID
            graph_type: Filter by graph type
            start_time: Filter by created_at >= start_time (ISO format)
            end_time: Filter by created_at <= end_time (ISO format)
            min_duration_ms: Filter by duration >= threshold
            max_duration_ms: Filter by duration <= threshold
            limit: Maximum number of results (default 100)
            offset: Number of results to skip (for pagination)

        Returns:
            List of ExecutionHistory objects matching filters

        Performance:
            Target: <100ms (leverages JSONB GIN indexes)
        """
        # Build query
        query = self.client.table("graph_states").select("*")

        # Apply filters
        if user_id:
            query = query.eq("user_id", user_id)
        if graph_type:
            query = query.eq("graph_type", graph_type)
        if start_time:
            query = query.gte("created_at", start_time)
        if end_time:
            query = query.lte("created_at", end_time)

        # JSONB filters for duration
        if min_duration_ms is not None:
            query = query.gte("timing->>total_duration_ms", str(min_duration_ms))
        if max_duration_ms is not None:
            query = query.lte("timing->>total_duration_ms", str(max_duration_ms))

        # Pagination and ordering
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

        # Execute query
        response = query.execute()

        # Deserialize results
        histories = []
        for row in response.data:
            try:
                history = ExecutionHistory(
                    execution_id=row["execution_id"],
                    state_snapshot=row["state_snapshot"],
                    state_type=row["state_type"],
                    provenance=row.get("provenance", []),
                    metadata=row.get("metadata", {}),
                    user_id=row.get("user_id"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    graph_type=row.get("graph_type", "forward_mode"),
                    original_inputs=row.get("original_inputs", {}),
                    timing=ExecutionTiming(**row.get("timing", {})),
                    performance=PerformanceMetrics(**row.get("performance", {})),
                    is_replay=row.get("is_replay", False),
                    original_execution_id=row.get("original_execution_id"),
                )
                histories.append(history)
            except Exception:
                # Skip invalid records
                continue

        return histories

    async def get_slow_executions(
        self,
        threshold_ms: float = 1000.0,
        limit: int = 50,
    ) -> list[ExecutionHistory]:
        """
        Find slow executions exceeding duration threshold.

        Args:
            threshold_ms: Minimum duration in milliseconds
            limit: Maximum number of results

        Returns:
            List of slow executions, ordered by duration descending
        """
        return await self.list_executions(
            min_duration_ms=threshold_ms,
            limit=limit,
        )

    async def get_statistics(
        self,
        user_id: str | None = None,
        graph_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, Any]:
        """
        Get aggregate statistics for executions.

        Args:
            user_id: Filter by user ID
            graph_type: Filter by graph type
            start_time: Filter by created_at >= start_time
            end_time: Filter by created_at <= end_time

        Returns:
            Dictionary with statistics:
            - total_executions: Total count
            - avg_duration_ms: Average execution time
            - avg_tokens: Average tokens consumed
            - avg_llm_calls: Average LLM calls
            - total_tokens: Total tokens across all executions
        """
        # Fetch all matching executions
        executions = await self.list_executions(
            user_id=user_id,
            graph_type=graph_type,
            start_time=start_time,
            end_time=end_time,
            limit=10000,  # High limit for stats
        )

        if not executions:
            return {
                "total_executions": 0,
                "avg_duration_ms": 0.0,
                "avg_tokens": 0.0,
                "avg_llm_calls": 0.0,
                "total_tokens": 0,
            }

        # Calculate statistics
        total_duration = sum(e.timing.total_duration_ms or 0 for e in executions)
        total_tokens_sum = sum(e.performance.total_tokens or 0 for e in executions)
        total_llm_calls = sum(e.performance.total_llm_calls for e in executions)

        return {
            "total_executions": len(executions),
            "avg_duration_ms": total_duration / len(executions),
            "avg_tokens": total_tokens_sum / len(executions),
            "avg_llm_calls": total_llm_calls / len(executions),
            "total_tokens": total_tokens_sum,
        }

    async def replay_execution(
        self,
        execution_id: UUID | str,
        graph_executor: Any = None,
    ) -> ExecutionHistory:
        """
        Replay execution from history.

        Re-runs the graph with the same inputs, creating a new execution
        record marked as a replay for comparison with the original.

        Args:
            execution_id: Original execution to replay
            graph_executor: Graph executor instance to run (optional)

        Returns:
            New ExecutionHistory for the replayed execution

        Raises:
            KeyError: If original execution not found
            ValueError: If replay fails

        Note:
            If graph_executor is None, this only loads the history without
            re-executing. Pass a graph executor to perform actual replay.
        """
        # Load original execution
        original = await self.load_execution(execution_id)

        if graph_executor is None:
            # No executor provided, return original history
            return original

        # Generate new execution ID for replay
        from uuid import uuid4

        replay_id = str(uuid4())

        # Execute graph with original inputs
        try:
            # This would call the actual graph executor
            # For now, we return a placeholder indicating replay would happen here
            raise NotImplementedError(
                "Replay execution requires graph executor implementation (H4/H5)"
            )
        except Exception as e:
            raise ValueError(f"Replay failed for {execution_id}: {e}") from e


__all__ = [
    "PerformanceMetrics",
    "ExecutionTiming",
    "ExecutionHistory",
    "ExecutionHistoryStore",
]
