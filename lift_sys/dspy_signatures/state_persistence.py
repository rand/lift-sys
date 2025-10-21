"""
State Persistence (H2)

Mechanism for persisting and restoring Pydantic AI graph state.

This module provides atomic, type-safe save/restore functionality for graph execution
state, enabling kill/resume workflows and execution history tracking.

Design Principles:
1. Round-Trip Serialization: No data loss on save → load → save
2. Type Safety: Preserves Pydantic model types (RunContext, StateT, etc.)
3. Atomicity: No partial states - operations succeed or fail completely
4. Performance: <100ms for save/load operations

Resolution for Hole H2: StatePersistence
Status: Implementation
Phase: 2 (Week 2)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from supabase import Client, create_client

from .node_interface import RunContext

# Type variables
StateT = TypeVar("StateT", bound=BaseModel)


class GraphState(BaseModel):
    """
    Serializable snapshot of graph execution state.

    Contains all information needed to restore execution:
    - Current state (StateT)
    - Execution context (RunContext metadata)
    - Provenance chain
    - Execution metadata
    """

    execution_id: str = Field(..., description="Unique execution identifier")
    state_snapshot: dict[str, Any] = Field(..., description="Serialized state (StateT)")
    state_type: str = Field(..., description="Fully qualified state type name")
    provenance: list[dict[str, Any]] = Field(
        default_factory=list, description="Execution provenance chain"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    user_id: str | None = Field(None, description="User who initiated execution")
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="State creation time"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="State update time"
    )

    model_config = ConfigDict(frozen=False)  # Allow updates


class NodeOutput(BaseModel):
    """
    Record of a single node's execution output.

    Stored separately to enable efficient querying and partial updates.
    """

    node_name: str = Field(..., description="Name of node that produced output")
    signature_name: str = Field(..., description="DSPy signature executed")
    inputs: dict[str, Any] = Field(..., description="Inputs passed to signature")
    outputs: dict[str, Any] = Field(..., description="Outputs from signature execution")
    execution_time_ms: float | None = Field(None, description="Execution time in milliseconds")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(), description="Execution timestamp"
    )


class StatePersistence(Generic[StateT]):
    """
    Persistence layer for Pydantic AI graph state.

    Provides atomic save/load/update operations for graph execution state using Supabase
    as the backing store. Ensures round-trip serialization with no data loss.

    Type Parameters:
        StateT: Pydantic model representing the graph state

    Usage:
        # Initialize with Supabase credentials
        persistence = StatePersistence[MyState](
            supabase_url="https://xxx.supabase.co",
            supabase_key="service_role_key"
        )

        # Save state
        await persistence.save(execution_id, state)

        # Load state
        state = await persistence.load(execution_id)

        # Update node output
        await persistence.update_node_output(execution_id, "ExtractIntent", output_dict)

    Performance:
        - save(): <100ms (target: <50ms)
        - load(): <100ms (target: <50ms)
        - update_node_output(): <50ms (target: <25ms)
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
    ) -> None:
        """
        Initialize state persistence with Supabase credentials.

        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase service role key (defaults to SUPABASE_SERVICE_KEY env var)

        Raises:
            ValueError: If credentials not provided and env vars not set
        """
        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided "
                "or set as environment variables"
            )

        self.client: Client = create_client(self.url, self.key)

    async def save(self, execution_id: UUID | str, state: GraphState) -> None:
        """
        Save graph execution state atomically.

        Stores complete state snapshot including:
        - State data (serialized Pydantic model)
        - Provenance chain
        - Execution metadata

        Args:
            execution_id: Unique execution identifier
            state: Graph state to persist

        Raises:
            ValueError: If state cannot be serialized
            Exception: If database operation fails
        """
        execution_id_str = str(execution_id)

        # Prepare state record
        state_data = {
            "id": execution_id_str,
            "execution_id": execution_id_str,
            "state_snapshot": state.state_snapshot,
            "state_type": state.state_type,
            "provenance": state.provenance,
            "metadata": state.metadata,
            "user_id": state.user_id,
            "created_at": state.created_at,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Atomic insert (fails if execution_id already exists)
        try:
            self.client.table("graph_states").insert(state_data).execute()
        except Exception as e:
            raise ValueError(f"Failed to save state for execution {execution_id_str}: {e}") from e

    async def load(self, execution_id: UUID | str) -> GraphState:
        """
        Load graph execution state.

        Retrieves complete state snapshot including provenance and metadata.

        Args:
            execution_id: Unique execution identifier

        Returns:
            GraphState with full execution state

        Raises:
            KeyError: If execution_id not found
            ValueError: If state cannot be deserialized
        """
        execution_id_str = str(execution_id)

        # Fetch state record
        response = (
            self.client.table("graph_states")
            .select("*")
            .eq("execution_id", execution_id_str)
            .execute()
        )

        if not response.data:
            raise KeyError(f"No state found for execution {execution_id_str}")

        state_row = response.data[0]

        # Reconstruct GraphState
        try:
            state = GraphState(
                execution_id=state_row["execution_id"],
                state_snapshot=state_row["state_snapshot"],
                state_type=state_row["state_type"],
                provenance=state_row.get("provenance", []),
                metadata=state_row.get("metadata", {}),
                user_id=state_row.get("user_id"),
                created_at=state_row["created_at"],
                updated_at=state_row["updated_at"],
            )
            return state
        except Exception as e:
            raise ValueError(
                f"Failed to deserialize state for execution {execution_id_str}: {e}"
            ) from e

    async def update_node_output(
        self, execution_id: UUID | str, node: str, output: dict[str, Any]
    ) -> None:
        """
        Update graph state with node execution output.

        Appends node output to provenance chain and updates state snapshot if provided.

        Args:
            execution_id: Unique execution identifier
            node: Node name that produced output
            output: Output dictionary from node execution

        Raises:
            KeyError: If execution_id not found
            ValueError: If update fails
        """
        execution_id_str = str(execution_id)

        # Fetch current state
        current_state = await self.load(execution_id_str)

        # Create node output record
        node_output = NodeOutput(
            node_name=node,
            signature_name=output.get("signature_name", "unknown"),
            inputs=output.get("inputs", {}),
            outputs=output.get("outputs", {}),
            execution_time_ms=output.get("execution_time_ms"),
        )

        # Add to provenance
        current_state.provenance.append(node_output.model_dump())

        # Update state snapshot if provided
        if "state_updates" in output:
            current_state.state_snapshot.update(output["state_updates"])

        # Update timestamp
        current_state.updated_at = datetime.now(UTC).isoformat()

        # Atomic update
        try:
            self.client.table("graph_states").update(
                {
                    "provenance": current_state.provenance,
                    "state_snapshot": current_state.state_snapshot,
                    "updated_at": current_state.updated_at,
                }
            ).eq("execution_id", execution_id_str).execute()
        except Exception as e:
            raise ValueError(
                f"Failed to update node output for execution {execution_id_str}: {e}"
            ) from e

    async def delete(self, execution_id: UUID | str) -> None:
        """
        Delete graph execution state.

        Removes all state data for the given execution.

        Args:
            execution_id: Unique execution identifier

        Raises:
            KeyError: If execution_id not found
        """
        execution_id_str = str(execution_id)

        try:
            self.client.table("graph_states").delete().eq(
                "execution_id", execution_id_str
            ).execute()
        except Exception as e:
            raise ValueError(f"Failed to delete state for execution {execution_id_str}: {e}") from e

    async def list_states(self, user_id: str | None = None, limit: int = 100) -> list[GraphState]:
        """
        List graph execution states.

        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum number of states to return

        Returns:
            List of GraphState objects, ordered by updated_at descending
        """
        query = (
            self.client.table("graph_states")
            .select("*")
            .order("updated_at", desc=True)
            .limit(limit)
        )

        if user_id:
            query = query.eq("user_id", user_id)

        response = query.execute()

        states = []
        for row in response.data:
            try:
                state = GraphState(
                    execution_id=row["execution_id"],
                    state_snapshot=row["state_snapshot"],
                    state_type=row["state_type"],
                    provenance=row.get("provenance", []),
                    metadata=row.get("metadata", {}),
                    user_id=row.get("user_id"),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                states.append(state)
            except Exception:
                # Skip invalid states
                continue

        return states


# Helper functions for working with RunContext


def serialize_run_context(ctx: RunContext[StateT]) -> GraphState:
    """
    Serialize RunContext to GraphState for persistence.

    Args:
        ctx: RunContext to serialize

    Returns:
        GraphState ready for persistence

    Example:
        ctx = RunContext(state=MyState(...), execution_id="exec-123")
        graph_state = serialize_run_context(ctx)
        await persistence.save(ctx.execution_id, graph_state)
    """
    return GraphState(
        execution_id=ctx.execution_id,
        state_snapshot=ctx.state.model_dump(),
        state_type=f"{ctx.state.__class__.__module__}.{ctx.state.__class__.__name__}",
        provenance=ctx.provenance,
        metadata=ctx.metadata,
        user_id=ctx.user_id,
    )


def deserialize_run_context(
    graph_state: GraphState, state_class: type[StateT]
) -> RunContext[StateT]:
    """
    Deserialize GraphState to RunContext.

    Args:
        graph_state: Persisted graph state
        state_class: Pydantic model class for state

    Returns:
        RunContext with restored state

    Example:
        graph_state = await persistence.load("exec-123")
        ctx = deserialize_run_context(graph_state, MyState)
    """
    state = state_class(**graph_state.state_snapshot)

    return RunContext(
        state=state,
        execution_id=graph_state.execution_id,
        user_id=graph_state.user_id,
        metadata=graph_state.metadata,
        provenance=graph_state.provenance,
    )


__all__ = [
    "GraphState",
    "NodeOutput",
    "StatePersistence",
    "serialize_run_context",
    "deserialize_run_context",
]
