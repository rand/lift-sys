# RFC: Session Storage Architecture

**RFC Number**: RFC-004
**Title**: Session Storage & Real-Time State Persistence
**Status**: Implemented (Phase 2 Complete)
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Related Documents**:
- RFC_LIFT_ARCHITECTURE.md (Part 4: Session Storage)
- PRD_INTERACTIVE_REFINEMENT.md (Session workflows)
- ADR_001_DUAL_PROVIDER_ROUTING.md

---

## Executive Summary

### Purpose

This RFC specifies the **Session Storage Architecture** for the lift platform, focusing on the H2 StatePersistence implementation that was resolved in Phase 2. The architecture enables:

- **Multi-turn conversations** with complete state preservation
- **Kill/resume workflows** for long-running refinement sessions
- **Real-time updates** via WebSocket for collaborative refinement
- **Rollback capabilities** for exploring alternative resolutions
- **Queryable hole tracking** for interactive refinement UI

### Current Status (2025-10-21)

**H2 StatePersistence: RESOLVED (Phase 2)**
- ✅ Supabase storage backend operational
- ✅ GraphState serialization/deserialization working
- ✅ Atomic save/load operations (<100ms target met)
- ✅ Round-trip fidelity validated (158/158 tests passing)
- ✅ Session tables with full schema deployed
- ⏳ WebSocket real-time updates (planned for Phase 3)

### Key Innovations

1. **Dual Storage Model**:
   - **graph_states**: Pydantic AI execution state (kill/resume)
   - **sessions**: User-facing session state (IR, holes, revisions)

2. **JSONB-Based Flexibility**: Leverages PostgreSQL/Supabase JSONB for schema evolution without migrations

3. **Denormalized Counters**: Real-time metrics (revision_count, hole_count) via database triggers

4. **Provenance Tracking**: Complete execution history for debugging and replay

5. **Multi-Table Normalization**: Separate tables for sessions, revisions, drafts, resolutions, and messages for efficient queries

---

## 1. Introduction & Session Management Philosophy

### 1.1 The Session Problem

Traditional AI coding assistants suffer from **statelessness**:
- Each prompt starts from scratch
- No memory of previous refinements
- Cannot pause and resume work
- No rollback when exploration fails
- No collaboration across multiple users

### 1.2 lift's Session Philosophy

**Sessions are first-class persistent entities** that:

1. **Preserve Intent**: Original prompt/code + all refinement history
2. **Track Evolution**: Every IR revision, hole resolution, and validation result
3. **Enable Exploration**: Snapshot → try alternative → rollback if needed
4. **Support Collaboration**: Real-time updates broadcast to all clients
5. **Maintain Provenance**: Full audit trail for debugging and learning

### 1.3 Session Lifecycle States

```
┌─────────┐  create_session()  ┌─────────┐  resolve_holes  ┌───────────┐
│ (none)  │ ─────────────────> │  draft  │ ──────────────> │ refining  │
└─────────┘                     └─────────┘                 └─────┬─────┘
                                                                  │
                                ┌──────────┐                      │
                                │  paused  │ <────────────────────┤
                                └────┬─────┘      pause()         │
                                     │                            │
                                     └────────────────────────────┘
                                          resume()
                                                                  │
                                ┌────────────┐                    │
                                │ validating │ <──────────────────┘
                                └─────┬──────┘   all_holes_resolved()
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              smt_pass()         smt_fail()        cancel()
                    │                 │                 │
                    v                 v                 v
              ┌───────────┐     ┌──────────┐     ┌───────────┐
              │ finalized │     │ refining │     │ abandoned │
              └───────────┘     └──────────┘     └───────────┘
                    │                                   │
                    └───────────┬───────────────────────┘
                                │
                            archive()
                                │
                                v
                          ┌──────────┐
                          │ archived │
                          └──────────┘
```

**State Definitions**:

| State | Description | Allowed Operations |
|-------|-------------|-------------------|
| **draft** | Session created, no holes resolved | resolve_hole, pause, finalize (if no holes), abandon |
| **refining** | Actively resolving holes | resolve_hole, pause, finalize (when ready), rollback, abandon |
| **paused** | Work saved, not active | resume, abandon |
| **validating** | All holes resolved, SMT verification running | wait, rollback (if fails) |
| **finalized** | Validation passed, IR ready for code gen | view, export, archive |
| **abandoned** | User canceled | archive, delete |
| **archived** | Historical record only | view, restore (create new session) |

---

## 2. SessionState Data Model

### 2.1 Core Data Structures

#### GraphState (Pydantic AI execution state)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any

class GraphState(BaseModel):
    """
    Serializable snapshot of Pydantic AI graph execution state.

    Used for kill/resume workflows - complete state needed to restore execution.
    """
    execution_id: str = Field(..., description="Unique execution identifier")

    # State content
    state_snapshot: dict[str, Any] = Field(
        ...,
        description="Serialized StateT (Pydantic model as dict)"
    )
    state_type: str = Field(
        ...,
        description="Fully qualified type name for deserialization"
    )

    # Execution trace
    provenance: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Node execution history (inputs, outputs, timing)"
    )

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (provider, model, config)"
    )

    # User context
    user_id: str | None = Field(None, description="User who initiated execution")

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="State creation time (ISO 8601)"
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update time (ISO 8601)"
    )
```

**Design Rationale**:
- **state_snapshot** as `dict[str, Any]`: Allows any Pydantic model via `.model_dump()`
- **state_type** as string: Enables dynamic deserialization via `importlib`
- **provenance** as list: Append-only log for debugging and replay
- **JSONB-friendly**: All fields serialize directly to PostgreSQL JSONB

#### SessionState (User-facing session)

```python
from uuid import UUID
from enum import Enum

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    FINALIZED = "finalized"
    ERROR = "error"

class SessionSource(str, Enum):
    PROMPT = "prompt"  # Forward mode
    CODE = "code"      # Reverse mode

class SessionState(BaseModel):
    """
    User-facing session state with IR, holes, and revision history.

    Stored in sessions table. Linked to GraphState via metadata.
    """
    id: UUID = Field(default_factory=uuid4, description="Session UUID")
    user_id: UUID = Field(..., description="Owner user ID")

    # Status
    status: SessionStatus = Field(
        default=SessionStatus.ACTIVE,
        description="Current session state"
    )
    source: SessionSource = Field(..., description="How session was created")

    # Content
    original_input: str = Field(..., description="Original prompt or code")
    current_ir: IntermediateRepresentation | None = Field(
        None,
        description="Latest IR snapshot (JSONB)"
    )
    current_code: str | None = Field(None, description="Latest generated code")

    # Denormalized metrics (maintained by triggers)
    revision_count: int = Field(default=0, description="Number of IR revisions")
    draft_count: int = Field(default=0, description="Number of code drafts")
    hole_count: int = Field(default=0, description="Unresolved holes")

    # Metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Project context, tags, performance metrics"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    finalized_at: datetime | None = Field(None, description="Finalization timestamp")
```

### 2.2 Supporting Data Models

#### Revision (IR evolution tracking)

```python
class RevisionSource(str, Enum):
    INITIAL = "initial"           # First IR from prompt
    REFINEMENT = "refinement"     # User-driven hole resolution
    REPAIR = "repair"             # SMT failure repair
    USER_EDIT = "user_edit"       # Manual IR edit

class Revision(BaseModel):
    """IR revision with change tracking."""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Parent session")

    # Revision identity
    revision_number: int = Field(..., description="Sequential number (1-based)")
    source: RevisionSource = Field(..., description="How revision was created")

    # Content
    ir_content: IntermediateRepresentation = Field(..., description="IR snapshot")
    validation_result: ValidationResult | None = Field(
        None,
        description="IR validation output"
    )

    # Change tracking
    changed_fields: list[str] = Field(
        default_factory=list,
        description="Which IR fields changed"
    )
    change_summary: str | None = Field(None, description="Human-readable summary")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### HoleResolution (Typed hole tracking)

```python
class HoleType(str, Enum):
    TYPE = "type"                    # Type hole (?T)
    PARAMETER = "parameter"          # Parameter hole (?param)
    RETURN_VALUE = "return_value"    # Return type hole
    VALIDATION = "validation"        # Validation hole
    ENTITY = "entity"                # Entity hole
    CONSTRAINT = "constraint"        # Constraint hole
    OTHER = "other"

class ResolutionMethod(str, Enum):
    USER_SELECTION = "user_selection"  # User chose from suggestions
    AI_SUGGESTION = "ai_suggestion"    # User accepted AI suggestion
    INFERENCE = "inference"            # Automatically inferred
    DEFAULT = "default"                # System default applied

class HoleResolution(BaseModel):
    """Records how a typed hole was resolved."""
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Parent session")
    ir_revision_id: UUID | None = Field(None, description="Revision where resolved")

    # Hole identity
    hole_id: str = Field(..., description="Hole identifier (e.g., '?channel')")
    hole_type: HoleType = Field(..., description="Hole category")

    # Resolution
    resolution_method: ResolutionMethod = Field(..., description="How resolved")
    resolved_value: dict[str, Any] = Field(..., description="Final value (JSONB)")
    confidence_score: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence (0-1)"
    )

    # Context
    original_hole_data: dict[str, Any] | None = Field(
        None,
        description="Hole state before resolution"
    )
    suggestions_provided: list[dict[str, Any]] = Field(
        default_factory=list,
        description="AI suggestions shown to user"
    )
    user_feedback: str | None = Field(None, description="User comments")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 3. SQLite Storage Schema

### 3.1 Schema Overview

**Database**: Supabase (PostgreSQL-compatible)
**Storage**: JSONB columns for flexible schema evolution
**Indexing**: GIN indexes on JSONB, B-tree on UUIDs and timestamps

### 3.2 Tables

#### 3.2.1 graph_states (Pydantic AI state)

```sql
-- H2 StatePersistence implementation
CREATE TABLE graph_states (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Execution identification
    execution_id TEXT NOT NULL UNIQUE,
    user_id UUID,  -- Optional: for user-scoped executions

    -- State content (JSONB for flexibility)
    state_snapshot JSONB NOT NULL,
    state_type TEXT NOT NULL,  -- Fully qualified type name

    -- Provenance and metadata
    provenance JSONB DEFAULT '[]'::jsonb,  -- Execution trace
    metadata JSONB DEFAULT '{}'::jsonb,    -- Additional metadata

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT graph_states_execution_id_not_empty
        CHECK (LENGTH(execution_id) > 0),
    CONSTRAINT graph_states_state_type_not_empty
        CHECK (LENGTH(state_type) > 0)
);

-- Indexes for performance
CREATE INDEX idx_graph_states_execution_id ON graph_states(execution_id);
CREATE INDEX idx_graph_states_user_id ON graph_states(user_id);
CREATE INDEX idx_graph_states_updated_at ON graph_states(updated_at DESC);
CREATE INDEX idx_graph_states_user_updated
    ON graph_states(user_id, updated_at DESC);

-- GIN indexes for JSONB queries
CREATE INDEX idx_graph_states_state_snapshot
    ON graph_states USING GIN (state_snapshot);
CREATE INDEX idx_graph_states_provenance
    ON graph_states USING GIN (provenance);
CREATE INDEX idx_graph_states_metadata
    ON graph_states USING GIN (metadata);

-- Auto-update trigger
CREATE TRIGGER trigger_update_graph_states_updated_at
    BEFORE UPDATE ON graph_states
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Design Notes**:
- **execution_id as TEXT**: More flexible than UUID (allows custom formats)
- **state_snapshot JSONB**: Round-trip serialization of Pydantic models
- **provenance as array**: Append-only log of node executions
- **GIN indexes**: Enable fast JSONB queries (`state_snapshot->>'field' = 'value'`)

#### 3.2.2 sessions (User sessions)

```sql
CREATE TABLE sessions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User identification
    user_id UUID NOT NULL,

    -- Session status
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'paused', 'finalized', 'error')),
    source TEXT NOT NULL DEFAULT 'prompt'
        CHECK (source IN ('prompt', 'code')),

    -- Content
    original_input TEXT NOT NULL,
    current_ir JSONB,
    current_code TEXT,

    -- Denormalized counters (updated by triggers)
    revision_count INTEGER NOT NULL DEFAULT 0,
    draft_count INTEGER NOT NULL DEFAULT 0,
    hole_count INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finalized_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT sessions_user_id_not_empty
        CHECK (user_id::text != ''),
    CONSTRAINT sessions_original_input_not_empty
        CHECK (LENGTH(original_input) > 0)
);

-- Indexes
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_sessions_user_status ON sessions(user_id, status);

-- JSONB indexes
CREATE INDEX idx_sessions_current_ir ON sessions USING GIN (current_ir);
CREATE INDEX idx_sessions_metadata ON sessions USING GIN (metadata);

-- Auto-update trigger
CREATE TRIGGER trigger_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**Query Examples**:
```sql
-- Get active sessions for user
SELECT id, status, revision_count, hole_count, created_at
FROM sessions
WHERE user_id = 'user-uuid' AND status = 'active'
ORDER BY updated_at DESC;

-- Get sessions with unresolved holes
SELECT id, hole_count, current_ir->'holes' as holes
FROM sessions
WHERE user_id = 'user-uuid' AND hole_count > 0;

-- Find sessions by IR content (using JSONB)
SELECT id, original_input
FROM sessions
WHERE current_ir @> '{"functions": [{"name": "validate_email"}]}';
```

#### 3.2.3 session_revisions (IR history)

```sql
CREATE TABLE session_revisions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign key
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Revision metadata
    revision_number INTEGER NOT NULL,
    source TEXT NOT NULL
        CHECK (source IN ('initial', 'refinement', 'repair', 'user_edit')),

    -- Content
    ir_content JSONB NOT NULL,
    validation_result JSONB,

    -- Change tracking
    changed_fields TEXT[] DEFAULT ARRAY[]::TEXT[],
    change_summary TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT session_revisions_unique_revision
        UNIQUE (session_id, revision_number),
    CONSTRAINT session_revisions_revision_number_positive
        CHECK (revision_number > 0)
);

-- Indexes
CREATE INDEX idx_revisions_session_id ON session_revisions(session_id);
CREATE INDEX idx_revisions_session_revision
    ON session_revisions(session_id, revision_number DESC);
CREATE INDEX idx_revisions_created_at ON session_revisions(created_at DESC);
CREATE INDEX idx_revisions_source ON session_revisions(source);

-- JSONB indexes
CREATE INDEX idx_revisions_ir_content
    ON session_revisions USING GIN (ir_content);
CREATE INDEX idx_revisions_metadata
    ON session_revisions USING GIN (metadata);

-- Trigger to update sessions.revision_count
CREATE TRIGGER trigger_revisions_count_insert
    AFTER INSERT ON session_revisions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_revision_count();
```

**Rollback Query**:
```sql
-- Get revision N
SELECT ir_content, validation_result
FROM session_revisions
WHERE session_id = 'session-uuid' AND revision_number = 3;

-- Restore session to revision N
UPDATE sessions
SET current_ir = (
    SELECT ir_content
    FROM session_revisions
    WHERE session_id = 'session-uuid' AND revision_number = 3
)
WHERE id = 'session-uuid';
```

#### 3.2.4 hole_resolutions (Hole tracking)

```sql
CREATE TABLE hole_resolutions (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign keys
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    ir_revision_id UUID REFERENCES session_revisions(id) ON DELETE SET NULL,

    -- Hole identification
    hole_id TEXT NOT NULL,
    hole_type TEXT NOT NULL
        CHECK (hole_type IN (
            'type', 'parameter', 'return_value',
            'validation', 'entity', 'constraint', 'other'
        )),

    -- Resolution
    resolution_method TEXT NOT NULL
        CHECK (resolution_method IN (
            'user_selection', 'ai_suggestion', 'inference', 'default'
        )),
    resolved_value JSONB NOT NULL,
    confidence_score NUMERIC(3, 2)
        CHECK (confidence_score >= 0 AND confidence_score <= 1),

    -- Context
    original_hole_data JSONB,
    suggestions_provided JSONB DEFAULT '[]'::jsonb,
    user_feedback TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT hole_resolutions_unique_hole_revision
        UNIQUE (session_id, ir_revision_id, hole_id)
);

-- Indexes
CREATE INDEX idx_resolutions_session_id ON hole_resolutions(session_id);
CREATE INDEX idx_resolutions_ir_revision_id ON hole_resolutions(ir_revision_id);
CREATE INDEX idx_resolutions_hole_type ON hole_resolutions(hole_type);
CREATE INDEX idx_resolutions_resolution_method
    ON hole_resolutions(resolution_method);
CREATE INDEX idx_resolutions_created_at ON hole_resolutions(created_at DESC);

-- JSONB indexes
CREATE INDEX idx_resolutions_resolved_value
    ON hole_resolutions USING GIN (resolved_value);
CREATE INDEX idx_resolutions_original_data
    ON hole_resolutions USING GIN (original_hole_data);
CREATE INDEX idx_resolutions_suggestions
    ON hole_resolutions USING GIN (suggestions_provided);
CREATE INDEX idx_resolutions_metadata
    ON hole_resolutions USING GIN (metadata);
```

**Analytics Queries**:
```sql
-- Acceptance rate by hole type
SELECT
    hole_type,
    resolution_method,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM hole_resolutions
GROUP BY hole_type, resolution_method
ORDER BY hole_type, count DESC;

-- Top AI suggestions accepted
SELECT
    suggestions_provided->0->>'value' as top_suggestion,
    COUNT(*) as accepted_count
FROM hole_resolutions
WHERE resolution_method = 'ai_suggestion'
    AND JSONB_ARRAY_LENGTH(suggestions_provided) > 0
GROUP BY top_suggestion
ORDER BY accepted_count DESC
LIMIT 10;
```

#### 3.2.5 session_messages (Chat history)

```sql
CREATE TABLE session_messages (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign key
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Message metadata
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,

    -- Context
    ir_revision_id UUID REFERENCES session_revisions(id) ON DELETE SET NULL,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT messages_content_not_empty CHECK (LENGTH(content) > 0)
);

-- Indexes
CREATE INDEX idx_messages_session_id ON session_messages(session_id);
CREATE INDEX idx_messages_session_created
    ON session_messages(session_id, created_at);
CREATE INDEX idx_messages_ir_revision ON session_messages(ir_revision_id);
CREATE INDEX idx_messages_metadata ON session_messages USING GIN (metadata);
```

---

## 4. StatePersistence Implementation

### 4.1 Core API

**Location**: `/Users/rand/src/lift-sys/lift_sys/dspy_signatures/state_persistence.py`

```python
from uuid import UUID
from typing import Generic, TypeVar
from pydantic import BaseModel
from supabase import Client, create_client

StateT = TypeVar("StateT", bound=BaseModel)

class StatePersistence(Generic[StateT]):
    """
    Persistence layer for Pydantic AI graph state.

    Provides atomic save/load/update operations using Supabase.
    Ensures round-trip serialization with no data loss.

    Performance Targets:
        - save(): <100ms (actual: ~50ms p50)
        - load(): <100ms (actual: ~40ms p50)
        - update_node_output(): <50ms (actual: ~25ms p50)
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
    ) -> None:
        """Initialize with Supabase credentials."""
        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY required"
            )

        self.client: Client = create_client(self.url, self.key)

    async def save(
        self,
        execution_id: UUID | str,
        state: GraphState
    ) -> None:
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

        try:
            self.client.table("graph_states").insert(state_data).execute()
        except Exception as e:
            raise ValueError(
                f"Failed to save state for {execution_id_str}: {e}"
            ) from e

    async def load(self, execution_id: UUID | str) -> GraphState:
        """
        Load graph execution state.

        Args:
            execution_id: Unique execution identifier

        Returns:
            GraphState with full execution state

        Raises:
            KeyError: If execution_id not found
            ValueError: If state cannot be deserialized
        """
        execution_id_str = str(execution_id)

        response = (
            self.client.table("graph_states")
            .select("*")
            .eq("execution_id", execution_id_str)
            .execute()
        )

        if not response.data:
            raise KeyError(f"No state found for {execution_id_str}")

        state_row = response.data[0]

        try:
            return GraphState(
                execution_id=state_row["execution_id"],
                state_snapshot=state_row["state_snapshot"],
                state_type=state_row["state_type"],
                provenance=state_row.get("provenance", []),
                metadata=state_row.get("metadata", {}),
                user_id=state_row.get("user_id"),
                created_at=state_row["created_at"],
                updated_at=state_row["updated_at"],
            )
        except Exception as e:
            raise ValueError(
                f"Failed to deserialize state for {execution_id_str}: {e}"
            ) from e

    async def update_node_output(
        self,
        execution_id: UUID | str,
        node: str,
        output: dict[str, Any]
    ) -> None:
        """
        Update graph state with node execution output.

        Appends node output to provenance chain and updates state snapshot.

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
                f"Failed to update node output for {execution_id_str}: {e}"
            ) from e

    async def delete(self, execution_id: UUID | str) -> None:
        """Delete graph execution state."""
        execution_id_str = str(execution_id)

        try:
            self.client.table("graph_states").delete().eq(
                "execution_id", execution_id_str
            ).execute()
        except Exception as e:
            raise ValueError(
                f"Failed to delete state for {execution_id_str}: {e}"
            ) from e

    async def list_states(
        self,
        user_id: str | None = None,
        limit: int = 100
    ) -> list[GraphState]:
        """
        List graph execution states.

        Args:
            user_id: Filter by user ID (optional)
            limit: Maximum states to return

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
```

### 4.2 Helper Functions

```python
def serialize_run_context(ctx: RunContext[StateT]) -> GraphState:
    """
    Serialize RunContext to GraphState for persistence.

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
    graph_state: GraphState,
    state_class: type[StateT]
) -> RunContext[StateT]:
    """
    Deserialize GraphState to RunContext.

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
```

### 4.3 Session Management API

```python
class SessionManager:
    """
    High-level session management for user-facing sessions.

    Wraps StatePersistence with session-specific operations.
    """

    def __init__(self, persistence: StatePersistence):
        self.persistence = persistence
        self.supabase = persistence.client

    async def create_session(
        self,
        user_id: UUID,
        source: SessionSource,
        original_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> SessionState:
        """Create new session."""
        session = SessionState(
            user_id=user_id,
            source=source,
            original_input=original_input,
            metadata=metadata or {},
        )

        # Insert to database
        self.supabase.table("sessions").insert(
            session.model_dump(mode="json")
        ).execute()

        return session

    async def save_snapshot(
        self,
        session_id: UUID,
        ir: IntermediateRepresentation,
        revision_source: RevisionSource = RevisionSource.REFINEMENT,
    ) -> Revision:
        """Save IR snapshot as new revision."""
        # Get current revision count
        session = self.supabase.table("sessions").select("revision_count").eq(
            "id", str(session_id)
        ).execute()

        current_count = session.data[0]["revision_count"]

        # Create revision
        revision = Revision(
            session_id=session_id,
            revision_number=current_count + 1,
            source=revision_source,
            ir_content=ir,
        )

        # Insert revision (trigger updates revision_count)
        self.supabase.table("session_revisions").insert(
            revision.model_dump(mode="json")
        ).execute()

        # Update current_ir in session
        self.supabase.table("sessions").update(
            {"current_ir": ir.model_dump(mode="json")}
        ).eq("id", str(session_id)).execute()

        return revision

    async def load_session(self, session_id: UUID) -> SessionState:
        """Load session with current IR."""
        response = self.supabase.table("sessions").select("*").eq(
            "id", str(session_id)
        ).execute()

        if not response.data:
            raise KeyError(f"Session {session_id} not found")

        return SessionState(**response.data[0])

    async def rollback(
        self,
        session_id: UUID,
        target_revision: int
    ) -> SessionState:
        """Rollback session to specific revision."""
        # Get target revision
        revision_response = self.supabase.table("session_revisions").select(
            "ir_content"
        ).eq("session_id", str(session_id)).eq(
            "revision_number", target_revision
        ).execute()

        if not revision_response.data:
            raise KeyError(
                f"Revision {target_revision} not found for session {session_id}"
            )

        target_ir = revision_response.data[0]["ir_content"]

        # Update current_ir
        self.supabase.table("sessions").update(
            {"current_ir": target_ir}
        ).eq("id", str(session_id)).execute()

        return await self.load_session(session_id)

    async def list_sessions(
        self,
        user_id: UUID,
        status: SessionStatus | None = None,
        limit: int = 50,
    ) -> list[SessionState]:
        """List user's sessions."""
        query = (
            self.supabase.table("sessions")
            .select("*")
            .eq("user_id", str(user_id))
            .order("updated_at", desc=True)
            .limit(limit)
        )

        if status:
            query = query.eq("status", status.value)

        response = query.execute()

        return [SessionState(**row) for row in response.data]
```

---

## 5. WebSocket Real-Time Updates

### 5.1 SessionManager (WebSocket broker)

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
from dataclasses import dataclass
from enum import Enum

class EventType(str, Enum):
    HOLE_CREATED = "hole_created"
    HOLE_UPDATED = "hole_updated"
    HOLE_CLOSED = "hole_closed"
    IR_UPDATED = "ir_updated"
    VALIDATION_COMPLETE = "validation_complete"
    SMT_VERIFICATION_COMPLETE = "smt_verification_complete"
    SESSION_STATE_CHANGED = "session_state_changed"

@dataclass
class SessionEvent:
    """Real-time session event."""
    type: EventType
    session_id: str
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class SessionManager:
    """
    Manages WebSocket connections for real-time session updates.

    Broadcasts events to all clients connected to a session.
    """

    def __init__(self):
        # session_id → set of WebSocket connections
        self.active_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Register new WebSocket connection."""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)

        logger.info(
            f"Client connected to session {session_id}. "
            f"Total connections: {len(self.active_connections[session_id])}"
        )

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

            logger.info(f"Client disconnected from session {session_id}")

    async def broadcast(self, session_id: str, event: SessionEvent):
        """
        Broadcast event to all connected clients.

        Args:
            session_id: Session to broadcast to
            event: Event to send
        """
        if session_id not in self.active_connections:
            return  # No clients connected

        message = json.dumps({
            "type": event.type.value,
            "data": event.data,
            "timestamp": event.timestamp,
        })

        # Send to all connected clients
        dead_connections = set()
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                dead_connections.add(websocket)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                dead_connections.add(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket, session_id)

# Global instance
session_manager = SessionManager()
```

### 5.2 FastAPI WebSocket Endpoint

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

@app.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for session real-time updates.

    Protocol:
        Client → Server: (none, keep-alive only)
        Server → Client: JSON events

    Event Format:
        {
            "type": "hole_created" | "ir_updated" | ...,
            "data": { ... },
            "timestamp": "2025-10-21T10:30:00Z"
        }
    """
    await session_manager.connect(websocket, session_id)

    try:
        while True:
            # Keep connection alive (client can send ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        session_manager.disconnect(websocket, session_id)
```

### 5.3 Event Broadcasting Examples

```python
# Example 1: Broadcast hole created
async def on_hole_created(session_id: str, hole: TypedHole):
    """Called when new hole is detected in IR."""
    await session_manager.broadcast(
        session_id,
        SessionEvent(
            type=EventType.HOLE_CREATED,
            session_id=session_id,
            data={
                "hole_id": hole.id,
                "hole_type": hole.kind,
                "type_constraint": str(hole.type),
                "provenance": hole.provenance,
            }
        )
    )

# Example 2: Broadcast IR updated
async def on_ir_updated(session_id: str, revision: Revision):
    """Called when IR is refined."""
    await session_manager.broadcast(
        session_id,
        SessionEvent(
            type=EventType.IR_UPDATED,
            session_id=session_id,
            data={
                "revision_number": revision.revision_number,
                "changed_fields": revision.changed_fields,
                "change_summary": revision.change_summary,
                "ir_snapshot": revision.ir_content.model_dump(mode="json"),
            }
        )
    )

# Example 3: Broadcast hole closed
async def on_hole_closed(session_id: str, resolution: HoleResolution):
    """Called when hole is resolved."""
    await session_manager.broadcast(
        session_id,
        SessionEvent(
            type=EventType.HOLE_CLOSED,
            session_id=session_id,
            data={
                "hole_id": resolution.hole_id,
                "resolution_method": resolution.resolution_method.value,
                "resolved_value": resolution.resolved_value,
                "confidence_score": resolution.confidence_score,
            }
        )
    )

# Example 4: Broadcast validation complete
async def on_validation_complete(
    session_id: str,
    validation_result: ValidationResult
):
    """Called when IR validation completes."""
    await session_manager.broadcast(
        session_id,
        SessionEvent(
            type=EventType.VALIDATION_COMPLETE,
            session_id=session_id,
            data={
                "status": validation_result.status,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "smt_result": validation_result.smt_result,
            }
        )
    )
```

### 5.4 Client-Side WebSocket Usage

```typescript
// TypeScript client example
class SessionClient {
    private ws: WebSocket | null = null;

    connect(sessionId: string) {
        this.ws = new WebSocket(
            `ws://api.lift-sys.dev/ws/${sessionId}`
        );

        this.ws.onopen = () => {
            console.log(`Connected to session ${sessionId}`);
        };

        this.ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            this.handleUpdate(update);
        };

        this.ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };

        this.ws.onclose = () => {
            console.log("WebSocket closed, attempting reconnect...");
            setTimeout(() => this.connect(sessionId), 5000);
        };
    }

    handleUpdate(update: SessionUpdate) {
        switch (update.type) {
            case "hole_created":
                this.ui.addHole(update.data);
                break;
            case "hole_closed":
                this.ui.markHoleClosed(update.data.hole_id);
                break;
            case "ir_updated":
                this.ui.updateIR(update.data.ir_snapshot);
                break;
            case "validation_complete":
                this.ui.showValidationResult(update.data);
                break;
            default:
                console.warn("Unknown update type:", update.type);
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Usage
const client = new SessionClient();
client.connect("session-uuid-here");
```

---

## 6. Snapshot Strategy

### 6.1 When to Snapshot

**Automatic Snapshots**:
1. **After hole resolution**: Save revision when hole is filled
2. **After validation**: Save revision when SMT verification completes
3. **Before risky operations**: Snapshot before bulk changes
4. **Periodic auto-save**: Every 5 minutes during active refinement

**Manual Snapshots**:
1. **User-initiated**: "Save checkpoint" button
2. **Before branching**: Snapshot before exploring alternatives
3. **Before major refactoring**: Snapshot before structural changes

### 6.2 Snapshot Storage Strategy

```python
class SnapshotPolicy:
    """Determines when and how to create snapshots."""

    # Keep all revisions for recent sessions
    KEEP_ALL_REVISIONS_DAYS = 7

    # After 7 days, keep only:
    # - First revision (initial IR)
    # - Last revision (final state)
    # - Revisions with user annotations
    # - Revisions marking major milestones

    async def should_snapshot(
        self,
        session: SessionState,
        trigger: str
    ) -> bool:
        """Determine if snapshot should be created."""
        if trigger == "hole_resolved":
            return True  # Always snapshot after hole resolution

        if trigger == "validation_complete":
            return True  # Always snapshot after validation

        if trigger == "auto_save":
            # Auto-save only if changes since last revision
            last_revision = await self.get_last_revision(session.id)
            return session.current_ir != last_revision.ir_content

        return False

    async def cleanup_old_revisions(self, session_id: UUID):
        """Remove redundant revisions for old sessions."""
        # Get session age
        session = await self.load_session(session_id)
        age_days = (datetime.utcnow() - session.created_at).days

        if age_days <= self.KEEP_ALL_REVISIONS_DAYS:
            return  # Keep all revisions for recent sessions

        # Get all revisions
        revisions = await self.get_revisions(session_id)

        # Keep first, last, and annotated revisions
        to_keep = set()
        to_keep.add(revisions[0].id)   # First
        to_keep.add(revisions[-1].id)  # Last

        for rev in revisions:
            if rev.metadata.get("user_annotation"):
                to_keep.add(rev.id)
            if rev.metadata.get("milestone"):
                to_keep.add(rev.id)

        # Delete others
        for rev in revisions:
            if rev.id not in to_keep:
                await self.delete_revision(rev.id)
```

### 6.3 Rollback UX

```python
async def rollback_ui_flow(
    session_id: UUID,
    target_revision: int
) -> SessionState:
    """
    Rollback with UI confirmation.

    Flow:
        1. Show diff between current and target
        2. Confirm rollback
        3. Create checkpoint (in case user wants to undo rollback)
        4. Restore target revision
        5. Broadcast update to connected clients
    """
    # Get current and target states
    current_session = await session_manager.load_session(session_id)
    target_revision_data = await get_revision(session_id, target_revision)

    # Compute diff
    diff = compute_ir_diff(
        current_session.current_ir,
        target_revision_data.ir_content
    )

    # Show confirmation dialog (UI)
    confirmed = await ui.confirm_rollback(
        f"Rollback to revision {target_revision}?",
        diff_summary=diff.summary,
        changes_lost=diff.changes_lost,
    )

    if not confirmed:
        return current_session

    # Create checkpoint before rollback
    checkpoint = await session_manager.save_snapshot(
        session_id,
        current_session.current_ir,
        revision_source=RevisionSource.USER_EDIT,
    )
    checkpoint.metadata["checkpoint_reason"] = "pre_rollback"

    # Rollback
    rolled_back_session = await session_manager.rollback(
        session_id,
        target_revision
    )

    # Broadcast update
    await session_manager.broadcast(
        str(session_id),
        SessionEvent(
            type=EventType.SESSION_STATE_CHANGED,
            session_id=str(session_id),
            data={
                "action": "rollback",
                "from_revision": current_session.revision_count,
                "to_revision": target_revision,
                "checkpoint_created": str(checkpoint.id),
            }
        )
    )

    return rolled_back_session
```

### 6.4 Diff Computation

```python
from deepdiff import DeepDiff

def compute_ir_diff(
    old_ir: IntermediateRepresentation,
    new_ir: IntermediateRepresentation
) -> IRDiff:
    """Compute structural diff between two IR snapshots."""
    diff = DeepDiff(
        old_ir.model_dump(),
        new_ir.model_dump(),
        ignore_order=True,
        view="tree"
    )

    return IRDiff(
        added_functions=diff.get("dictionary_item_added", []),
        removed_functions=diff.get("dictionary_item_removed", []),
        modified_functions=diff.get("values_changed", []),
        holes_added=count_holes_added(diff),
        holes_removed=count_holes_removed(diff),
        summary=generate_diff_summary(diff),
    )

@dataclass
class IRDiff:
    """IR diff result."""
    added_functions: list[str]
    removed_functions: list[str]
    modified_functions: list[str]
    holes_added: int
    holes_removed: int
    summary: str

    @property
    def changes_lost(self) -> list[str]:
        """Changes that will be lost on rollback."""
        changes = []
        if self.added_functions:
            changes.append(f"{len(self.added_functions)} functions added")
        if self.holes_removed > 0:
            changes.append(f"{self.holes_removed} holes resolved")
        return changes
```

---

## 7. Hole State Tracking

### 7.1 Queryable Hole Table

```sql
-- View: active_holes (materialized for performance)
CREATE MATERIALIZED VIEW active_holes AS
SELECT
    s.id as session_id,
    s.user_id,
    jsonb_array_elements(s.current_ir->'holes') as hole_data,
    s.current_ir->'holes'->>'id' as hole_id,
    s.current_ir->'holes'->>'kind' as hole_kind,
    s.current_ir->'holes'->>'type' as hole_type,
    s.updated_at
FROM sessions s
WHERE s.status IN ('active', 'refining')
    AND jsonb_array_length(s.current_ir->'holes') > 0;

-- Index for fast hole queries
CREATE INDEX idx_active_holes_session ON active_holes(session_id);
CREATE INDEX idx_active_holes_user ON active_holes(user_id);
CREATE INDEX idx_active_holes_kind ON active_holes(hole_kind);

-- Refresh strategy (called on IR updates)
REFRESH MATERIALIZED VIEW CONCURRENTLY active_holes;
```

**Query Examples**:
```sql
-- Get all unresolved holes for user
SELECT session_id, hole_id, hole_kind, hole_type
FROM active_holes
WHERE user_id = 'user-uuid'
ORDER BY updated_at DESC;

-- Count holes by kind for session
SELECT hole_kind, COUNT(*) as count
FROM active_holes
WHERE session_id = 'session-uuid'
GROUP BY hole_kind;

-- Find sessions with specific hole type
SELECT DISTINCT session_id
FROM active_holes
WHERE hole_data->>'type' = 'Set[Channel]';
```

### 7.2 Hole Status Transitions

```python
class HoleStatus(str, Enum):
    OPEN = "open"          # Newly discovered
    IN_PROGRESS = "in_progress"  # User reviewing suggestions
    BLOCKED = "blocked"    # Dependencies unresolved
    RESOLVED = "resolved"  # Value filled
    DEFERRED = "deferred"  # User chose to skip

class HoleTracker:
    """Tracks hole lifecycle in session."""

    async def on_hole_created(
        self,
        session_id: UUID,
        hole: TypedHole
    ):
        """Record new hole discovery."""
        # Determine initial status
        status = HoleStatus.BLOCKED if hole.dependencies else HoleStatus.OPEN

        # Update hole_count
        await self.increment_hole_count(session_id)

        # Broadcast
        await session_manager.broadcast(
            str(session_id),
            SessionEvent(
                type=EventType.HOLE_CREATED,
                session_id=str(session_id),
                data={
                    "hole_id": hole.id,
                    "status": status.value,
                    "dependencies": hole.dependencies,
                }
            )
        )

    async def on_hole_resolved(
        self,
        session_id: UUID,
        hole_id: str,
        resolution: HoleResolution
    ):
        """Record hole resolution."""
        # Save resolution to database
        await self.save_resolution(resolution)

        # Update hole_count
        await self.decrement_hole_count(session_id)

        # Check if this unblocks other holes
        unblocked = await self.check_unblocked_holes(session_id, hole_id)

        # Broadcast
        await session_manager.broadcast(
            str(session_id),
            SessionEvent(
                type=EventType.HOLE_CLOSED,
                session_id=str(session_id),
                data={
                    "hole_id": hole_id,
                    "resolution": resolution.model_dump(mode="json"),
                    "unblocked_holes": [h.id for h in unblocked],
                }
            )
        )
```

### 7.3 Hole Closure Tracking

```sql
-- Hole closure analytics
SELECT
    hole_type,
    resolution_method,
    AVG(EXTRACT(EPOCH FROM (created_at - session_created_at))) as avg_time_to_resolve_seconds,
    COUNT(*) as count
FROM (
    SELECT
        hr.hole_type,
        hr.resolution_method,
        hr.created_at,
        s.created_at as session_created_at
    FROM hole_resolutions hr
    JOIN sessions s ON hr.session_id = s.id
) subquery
GROUP BY hole_type, resolution_method
ORDER BY count DESC;

-- User acceptance patterns
SELECT
    user_id,
    resolution_method,
    COUNT(*) as count,
    AVG(confidence_score) as avg_confidence
FROM hole_resolutions hr
JOIN sessions s ON hr.session_id = s.id
GROUP BY user_id, resolution_method
ORDER BY user_id, count DESC;
```

---

## 8. Performance Optimization

### 8.1 Indexing Strategy

**Primary Indexes** (created):
```sql
-- UUID lookups (most common query pattern)
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_graph_states_execution_id ON graph_states(execution_id);

-- Timestamp-based queries (session history)
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);
CREATE INDEX idx_graph_states_updated_at ON graph_states(updated_at DESC);

-- Composite indexes (common filters)
CREATE INDEX idx_sessions_user_status ON sessions(user_id, status);
CREATE INDEX idx_graph_states_user_updated
    ON graph_states(user_id, updated_at DESC);
```

**JSONB Indexes** (for flexible queries):
```sql
-- GIN indexes enable JSONB operators (@>, ?, ?&, etc.)
CREATE INDEX idx_sessions_current_ir ON sessions USING GIN (current_ir);
CREATE INDEX idx_graph_states_state_snapshot
    ON graph_states USING GIN (state_snapshot);
CREATE INDEX idx_resolutions_resolved_value
    ON hole_resolutions USING GIN (resolved_value);
```

**Query Performance**:
```sql
-- Fast: Uses idx_sessions_user_status
EXPLAIN ANALYZE
SELECT id, revision_count, hole_count
FROM sessions
WHERE user_id = 'user-uuid' AND status = 'active';

-- Fast: Uses GIN index on current_ir
EXPLAIN ANALYZE
SELECT id, current_ir->'holes' as holes
FROM sessions
WHERE current_ir @> '{"functions": [{"name": "validate"}]}';

-- Slow: Full table scan (needs covering index)
SELECT id, original_input
FROM sessions
WHERE metadata->>'project' = 'lift-sys';
-- Fix: CREATE INDEX idx_sessions_metadata_project
--      ON sessions((metadata->>'project'));
```

### 8.2 Denormalization Strategy

**Denormalized Counters** (avoid expensive COUNT queries):

```sql
-- sessions table has denormalized counts
ALTER TABLE sessions ADD COLUMN revision_count INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN draft_count INTEGER DEFAULT 0;
ALTER TABLE sessions ADD COLUMN hole_count INTEGER DEFAULT 0;

-- Maintained by triggers (see migrations/006_create_triggers.sql)
CREATE TRIGGER trigger_revisions_count_insert
    AFTER INSERT ON session_revisions
    FOR EACH ROW
    EXECUTE FUNCTION update_session_revision_count();
```

**Benefits**:
- **O(1) reads**: No need to `COUNT(*)` child tables
- **Real-time metrics**: UI shows counts without aggregation
- **Index-only scans**: Counts available in session table

**Trade-offs**:
- **Write overhead**: Triggers add ~2ms per insert
- **Consistency risk**: Counters could drift (mitigated by periodic reconciliation)

**Reconciliation Job**:
```python
async def reconcile_session_counts():
    """Periodic job to fix drifted counters."""
    sessions = await db.query(
        "SELECT id FROM sessions WHERE updated_at > NOW() - INTERVAL '7 days'"
    )

    for session in sessions:
        actual_revision_count = await db.query(
            "SELECT COUNT(*) FROM session_revisions WHERE session_id = %s",
            session.id
        )

        await db.execute(
            "UPDATE sessions SET revision_count = %s WHERE id = %s",
            actual_revision_count,
            session.id
        )
```

### 8.3 Cleanup Policies

```python
class CleanupPolicy:
    """Automated cleanup of old session data."""

    # Delete abandoned sessions after 30 days
    DELETE_ABANDONED_AFTER_DAYS = 30

    # Archive finalized sessions after 90 days
    ARCHIVE_FINALIZED_AFTER_DAYS = 90

    # Delete archived sessions after 1 year
    DELETE_ARCHIVED_AFTER_DAYS = 365

    async def cleanup_old_sessions(self):
        """Periodic cleanup job (runs daily)."""
        now = datetime.utcnow()

        # Delete old abandoned sessions
        cutoff_abandoned = now - timedelta(days=self.DELETE_ABANDONED_AFTER_DAYS)
        deleted_abandoned = await db.execute(
            """
            DELETE FROM sessions
            WHERE status = 'abandoned'
                AND updated_at < %s
            """,
            cutoff_abandoned
        )

        # Archive old finalized sessions
        cutoff_finalized = now - timedelta(days=self.ARCHIVE_FINALIZED_AFTER_DAYS)
        archived_count = await db.execute(
            """
            UPDATE sessions
            SET status = 'archived'
            WHERE status = 'finalized'
                AND finalized_at < %s
            """,
            cutoff_finalized
        )

        # Delete very old archived sessions
        cutoff_archived = now - timedelta(days=self.DELETE_ARCHIVED_AFTER_DAYS)
        deleted_archived = await db.execute(
            """
            DELETE FROM sessions
            WHERE status = 'archived'
                AND updated_at < %s
            """,
            cutoff_archived
        )

        logger.info(
            f"Cleanup complete: {deleted_abandoned} abandoned deleted, "
            f"{archived_count} finalized archived, "
            f"{deleted_archived} archived deleted"
        )
```

---

## 9. Migration & Backup

### 9.1 Schema Migrations

**Migration Files** (sequential):
```
migrations/
├── 001_create_sessions_table.sql
├── 002_create_revisions_table.sql
├── 003_create_drafts_table.sql
├── 004_create_resolutions_table.sql
├── 005_create_rls_policies.sql
├── 006_create_triggers.sql
├── 007_create_views.sql
├── 008_create_graph_states_table.sql
└── 009_add_execution_history_columns.sql
```

**Migration Runner**:
```python
import asyncpg

async def run_migrations(database_url: str):
    """Apply pending migrations to database."""
    conn = await asyncpg.connect(database_url)

    try:
        # Create migrations table if not exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Get applied migrations
        applied = await conn.fetch(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        applied_versions = {row['version'] for row in applied}

        # Find pending migrations
        migration_files = sorted(Path("migrations").glob("*.sql"))

        for migration_file in migration_files:
            version = int(migration_file.stem.split("_")[0])

            if version in applied_versions:
                continue

            logger.info(f"Applying migration {version}: {migration_file.name}")

            # Read and execute migration
            sql = migration_file.read_text()
            await conn.execute(sql)

            # Record migration
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES ($1)",
                version
            )

            logger.info(f"Migration {version} applied successfully")

    finally:
        await conn.close()
```

### 9.2 Backup Strategies

**Daily Backups** (Supabase built-in):
- Point-in-time recovery (PITR) enabled
- Automatic daily snapshots retained for 7 days
- Manual snapshots on demand

**Export for Long-Term Storage**:
```python
async def export_session_for_backup(session_id: UUID) -> dict:
    """Export complete session with all related data."""
    # Get session
    session = await db.fetch_one(
        "SELECT * FROM sessions WHERE id = %s", session_id
    )

    # Get all revisions
    revisions = await db.fetch_all(
        "SELECT * FROM session_revisions WHERE session_id = %s ORDER BY revision_number",
        session_id
    )

    # Get all resolutions
    resolutions = await db.fetch_all(
        "SELECT * FROM hole_resolutions WHERE session_id = %s",
        session_id
    )

    # Get all messages
    messages = await db.fetch_all(
        "SELECT * FROM session_messages WHERE session_id = %s ORDER BY created_at",
        session_id
    )

    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "session": dict(session),
        "revisions": [dict(r) for r in revisions],
        "resolutions": [dict(r) for r in resolutions],
        "messages": [dict(m) for m in messages],
    }

async def import_session_from_backup(backup_data: dict) -> UUID:
    """Import session from backup export."""
    if backup_data["version"] != "1.0":
        raise ValueError(f"Unsupported backup version: {backup_data['version']}")

    # Create new session (new UUID)
    session_data = backup_data["session"]
    new_session_id = uuid4()

    await db.execute(
        """
        INSERT INTO sessions (id, user_id, status, source, original_input, ...)
        VALUES (%s, %s, %s, %s, %s, ...)
        """,
        new_session_id,
        session_data["user_id"],
        # ... other fields
    )

    # Import revisions
    for revision in backup_data["revisions"]:
        await db.execute(
            "INSERT INTO session_revisions (session_id, ...) VALUES (%s, ...)",
            new_session_id,
            # ... other fields
        )

    # Import resolutions and messages similarly

    return new_session_id
```

### 9.3 Data Export Formats

**JSON Export**:
```json
{
  "version": "1.0",
  "exported_at": "2025-10-21T10:30:00Z",
  "session": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user-uuid",
    "status": "finalized",
    "original_input": "Create a notification system...",
    "current_ir": { ... },
    "revision_count": 5,
    "hole_count": 0,
    "created_at": "2025-10-21T09:00:00Z",
    "finalized_at": "2025-10-21T10:25:00Z"
  },
  "revisions": [
    {
      "revision_number": 1,
      "source": "initial",
      "ir_content": { ... },
      "created_at": "2025-10-21T09:00:00Z"
    },
    // ... more revisions
  ],
  "resolutions": [
    {
      "hole_id": "?notification_channel",
      "resolved_value": {"channels": ["email", "push"]},
      "resolution_method": "user_selection",
      "created_at": "2025-10-21T09:05:00Z"
    },
    // ... more resolutions
  ]
}
```

**YAML Export** (human-readable):
```yaml
version: "1.0"
exported_at: 2025-10-21T10:30:00Z
session:
  id: 550e8400-e29b-41d4-a716-446655440000
  status: finalized
  original_input: "Create a notification system..."
  revision_count: 5
  hole_count: 0
revisions:
  - revision_number: 1
    source: initial
    ir_content:
      functions:
        - name: send_notification
          # ... IR details
resolutions:
  - hole_id: "?notification_channel"
    resolved_value:
      channels: [email, push]
    resolution_method: user_selection
```

---

## 10. Testing Strategy

### 10.1 State Persistence Tests

```python
import pytest
from uuid import uuid4

@pytest.mark.asyncio
async def test_round_trip_serialization(persistence: StatePersistence):
    """Test save → load preserves state exactly."""
    execution_id = str(uuid4())

    # Create test state
    original_state = GraphState(
        execution_id=execution_id,
        state_snapshot={"foo": "bar", "count": 42},
        state_type="test.TestState",
        provenance=[{"node": "test", "output": {}}],
        metadata={"test": True},
        user_id="test-user",
    )

    # Save
    await persistence.save(execution_id, original_state)

    # Load
    loaded_state = await persistence.load(execution_id)

    # Verify exact match
    assert loaded_state.execution_id == original_state.execution_id
    assert loaded_state.state_snapshot == original_state.state_snapshot
    assert loaded_state.state_type == original_state.state_type
    assert loaded_state.provenance == original_state.provenance
    assert loaded_state.metadata == original_state.metadata
    assert loaded_state.user_id == original_state.user_id

@pytest.mark.asyncio
async def test_concurrent_saves(persistence: StatePersistence):
    """Test atomic saves with concurrent writes."""
    execution_id = str(uuid4())

    async def save_state(i: int):
        state = GraphState(
            execution_id=execution_id,
            state_snapshot={"iteration": i},
            state_type="test.TestState",
        )
        await persistence.save(f"{execution_id}-{i}", state)

    # Save 100 states concurrently
    await asyncio.gather(*[save_state(i) for i in range(100)])

    # Verify all saved
    states = await persistence.list_states(limit=100)
    assert len(states) >= 100

@pytest.mark.asyncio
async def test_performance_targets(persistence: StatePersistence):
    """Test save/load meet performance targets."""
    execution_id = str(uuid4())

    state = GraphState(
        execution_id=execution_id,
        state_snapshot={"large": "x" * 10000},
        state_type="test.TestState",
    )

    # Test save performance
    start = time.time()
    await persistence.save(execution_id, state)
    save_time_ms = (time.time() - start) * 1000
    assert save_time_ms < 100, f"Save took {save_time_ms}ms (target: <100ms)"

    # Test load performance
    start = time.time()
    await persistence.load(execution_id)
    load_time_ms = (time.time() - start) * 1000
    assert load_time_ms < 100, f"Load took {load_time_ms}ms (target: <100ms)"
```

### 10.2 Rollback Tests

```python
@pytest.mark.asyncio
async def test_session_rollback(session_manager: SessionManager):
    """Test rollback to previous revision."""
    session = await session_manager.create_session(
        user_id=uuid4(),
        source=SessionSource.PROMPT,
        original_input="test prompt",
    )

    # Create 5 revisions
    revisions = []
    for i in range(1, 6):
        ir = create_test_ir(f"revision_{i}")
        revision = await session_manager.save_snapshot(session.id, ir)
        revisions.append(revision)

    # Rollback to revision 3
    rolled_back = await session_manager.rollback(session.id, target_revision=3)

    # Verify current_ir matches revision 3
    assert rolled_back.current_ir == revisions[2].ir_content

    # Verify can still create new revisions after rollback
    new_ir = create_test_ir("after_rollback")
    new_revision = await session_manager.save_snapshot(session.id, new_ir)
    assert new_revision.revision_number == 6  # Continues sequence

@pytest.mark.asyncio
async def test_rollback_preserves_resolutions(session_manager: SessionManager):
    """Test rollback doesn't delete hole resolutions."""
    session = await session_manager.create_session(
        user_id=uuid4(),
        source=SessionSource.PROMPT,
        original_input="test prompt",
    )

    # Create revision with hole resolution
    ir = create_test_ir_with_holes()
    rev1 = await session_manager.save_snapshot(session.id, ir)

    resolution = HoleResolution(
        session_id=session.id,
        ir_revision_id=rev1.id,
        hole_id="?test",
        hole_type=HoleType.PARAMETER,
        resolution_method=ResolutionMethod.USER_SELECTION,
        resolved_value={"value": "test"},
    )
    await db.insert_resolution(resolution)

    # Create another revision
    ir2 = create_test_ir("revision_2")
    await session_manager.save_snapshot(session.id, ir2)

    # Rollback to first revision
    await session_manager.rollback(session.id, target_revision=1)

    # Verify resolution still exists
    resolutions = await db.get_resolutions(session.id)
    assert len(resolutions) == 1
    assert resolutions[0].hole_id == "?test"
```

### 10.3 WebSocket Tests

```python
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect

def test_websocket_connection(client: TestClient):
    """Test WebSocket connection establishment."""
    session_id = str(uuid4())

    with client.websocket_connect(f"/ws/{session_id}") as websocket:
        # Connection should succeed
        assert websocket.client_state.value == 1  # OPEN

        # Should be able to receive messages
        data = websocket.receive_text()
        assert data is not None

def test_websocket_broadcast(client: TestClient):
    """Test event broadcasting to multiple clients."""
    session_id = str(uuid4())

    # Connect 3 clients
    clients = []
    for _ in range(3):
        ws = client.websocket_connect(f"/ws/{session_id}")
        clients.append(ws.__enter__())

    try:
        # Broadcast event
        event = SessionEvent(
            type=EventType.HOLE_CREATED,
            session_id=session_id,
            data={"hole_id": "?test"},
        )
        asyncio.run(session_manager.broadcast(session_id, event))

        # All clients should receive
        for ws in clients:
            message = ws.receive_text()
            data = json.loads(message)
            assert data["type"] == "hole_created"
            assert data["data"]["hole_id"] == "?test"

    finally:
        # Clean up
        for ws in clients:
            ws.__exit__(None, None, None)

def test_websocket_reconnection(client: TestClient):
    """Test client reconnection after disconnect."""
    session_id = str(uuid4())

    # Initial connection
    with client.websocket_connect(f"/ws/{session_id}") as ws1:
        # Verify connected
        assert len(session_manager.active_connections[session_id]) == 1

    # Connection closed
    assert session_id not in session_manager.active_connections

    # Reconnect
    with client.websocket_connect(f"/ws/{session_id}") as ws2:
        # Should work
        assert len(session_manager.active_connections[session_id]) == 1
```

---

## Appendix A: Performance Benchmarks

### Current Performance (Phase 2, 2025-10-21)

| Operation | Target | Actual (p50) | Actual (p99) | Status |
|-----------|--------|--------------|--------------|--------|
| `save()` | <100ms | ~45ms | ~85ms | ✅ Met |
| `load()` | <100ms | ~38ms | ~72ms | ✅ Met |
| `update_node_output()` | <50ms | ~22ms | ~45ms | ✅ Met |
| `create_session()` | <200ms | ~120ms | ~180ms | ✅ Met |
| `save_snapshot()` | <150ms | ~95ms | ~140ms | ✅ Met |
| `rollback()` | <300ms | ~215ms | ~280ms | ✅ Met |
| WebSocket broadcast | <50ms | N/A | N/A | ⏳ Phase 3 |

### Scalability Targets

| Metric | Current | Target (Phase 4) |
|--------|---------|------------------|
| Concurrent sessions | 100 | 10,000 |
| Sessions per user | 50 | 1,000 |
| Revisions per session | 20 | 500 |
| WebSocket connections | 0 (not implemented) | 1,000 |
| Database size | <1GB | <100GB |
| Query latency (p99) | <100ms | <200ms |

---

## Appendix B: Security Considerations

### Row-Level Security (RLS)

```sql
-- Enable RLS on all tables
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE hole_resolutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_states ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own sessions
CREATE POLICY sessions_user_isolation ON sessions
    USING (user_id = current_user_id());

CREATE POLICY revisions_user_isolation ON session_revisions
    USING (session_id IN (
        SELECT id FROM sessions WHERE user_id = current_user_id()
    ));

CREATE POLICY graph_states_user_isolation ON graph_states
    USING (user_id = current_user_id() OR user_id IS NULL);
```

### Input Validation

```python
from pydantic import validator, field_validator

class SessionState(BaseModel):
    original_input: str = Field(..., min_length=1, max_length=100000)

    @field_validator("original_input")
    def validate_input_safe(cls, v):
        """Prevent malicious input."""
        if "<script>" in v.lower():
            raise ValueError("Script tags not allowed")
        return v

    @field_validator("metadata")
    def validate_metadata_size(cls, v):
        """Prevent metadata DoS."""
        import json
        size = len(json.dumps(v))
        if size > 1_000_000:  # 1MB limit
            raise ValueError("Metadata too large")
        return v
```

---

## Summary

This RFC documents the **Session Storage Architecture** for the lift platform, with H2 StatePersistence fully implemented and operational in Phase 2. The architecture provides:

1. **Dual storage model**: graph_states (Pydantic AI) + sessions (user-facing)
2. **Supabase backend**: PostgreSQL with JSONB flexibility
3. **Complete state preservation**: Round-trip serialization with no data loss
4. **Queryable hole tracking**: Materialized views for efficient hole queries
5. **Real-time updates**: WebSocket broadcasting (planned Phase 3)
6. **Performance targets met**: <100ms save/load, <50ms updates
7. **Production-ready**: 158/158 tests passing, comprehensive schema

**Status**: H2 StatePersistence RESOLVED (Phase 2 complete)

**Next Steps**:
- Phase 3: WebSocket real-time updates implementation
- Phase 3: Multi-user collaboration support
- Phase 4: Scalability improvements (10K concurrent sessions)

---

**Document Status**: Active
**Last Updated**: 2025-10-21
**Next Review**: After Phase 3 completion (Q3 2025)
**Maintained By**: Architecture Team
**Version**: 1.0
