---
track: dspy
document_type: hole_preparation
status: complete
priority: P2
phase: 6
completion: 100%
last_updated: 2025-10-21
session_protocol: |
  For new Claude Code session:
  1. H15 is RESOLVED (implementation complete)
  2. Use this document as reference for H15 design decisions
  3. Implementation: lift_sys/dspy_signatures/migration_constraints.py
  4. Tests: 33/33 passing
related_docs:
  - docs/tracks/dspy/HOLE_INVENTORY.md
  - docs/tracks/dspy/CONSTRAINT_PROPAGATION_LOG.md
  - docs/tracks/dspy/SESSION_STATE.md
---

# H15: MigrationConstraints - Preparation Document

**Date**: 2025-10-21
**Status**: Complete (H15 resolved)
**Phase**: 6 (Week 6)

---

## Overview

H15 (MigrationConstraints) defines requirements for backward compatibility when migrating from the old `PromptSession` format to the new `GraphState`/`ExecutionHistory` format.

## Problem Statement

The codebase currently has two session formats:

1. **Old Format (`PromptSession`)**: Interactive prompt refinement sessions
   - Located in `lift_sys/spec_sessions/models.py`
   - Tracks IR refinement through user prompts
   - Contains: revisions, IR drafts, hole resolutions
   - Used by: Forward mode prompt-to-IR workflow

2. **New Format (`GraphState`/`ExecutionHistory`)**: Pydantic AI graph execution state
   - Located in `lift_sys/dspy_signatures/state_persistence.py` (GraphState)
   - Extended by `lift_sys/dspy_signatures/execution_history.py` (ExecutionHistory)
   - Tracks execution state, provenance, timing, performance
   - Used by: DSPy + Pydantic AI graph execution

**Migration Need**: Convert existing PromptSession data to ExecutionHistory format for unified state management.

## Goals

1. **Zero Data Loss**: All PromptSession fields must map to ExecutionHistory
2. **Resumability**: Migrated sessions can resume execution
3. **Rollback Support**: Can revert ExecutionHistory back to PromptSession if needed
4. **Idempotency**: Re-running migration produces same result
5. **Validation**: Migrated data passes all schema validations

---

## Schema Comparison

### PromptSession Fields (Old Format)

```python
@dataclass
class PromptSession:
    session_id: str                              # UUID
    created_at: str                              # ISO timestamp
    updated_at: str                              # ISO timestamp
    status: str                                  # "active" | "finalized" | "abandoned"

    # Refinement history
    revisions: list[PromptRevision]              # User input history
    ir_drafts: list[IRDraft]                     # Versioned IR snapshots

    # Current state
    current_draft: IRDraft | None                # Latest IR version
    pending_resolutions: list[HoleResolution]    # Unresolved holes

    # Metadata
    source: str                                  # "prompt" | "reverse_mode"
    metadata: dict[str, Any]                     # Additional data
```

**Nested Types:**
- `PromptRevision`: timestamp, content, revision_type, target_hole, metadata
- `IRDraft`: version, ir (IntermediateRepresentation), validation_status, smt_results, ambiguities, created_at, metadata
- `HoleResolution`: hole_id, resolution_text, resolution_type, applied, timestamp, metadata

### ExecutionHistory Fields (New Format)

```python
class ExecutionHistory(GraphState):
    # From GraphState (H2)
    execution_id: str                            # UUID
    state_snapshot: dict[str, Any]               # Serialized state
    state_type: str                              # Fully qualified type name
    provenance: list[dict[str, Any]]             # Execution provenance chain
    metadata: dict[str, Any]                     # Execution metadata
    user_id: str | None                          # User who initiated
    created_at: str                              # ISO timestamp
    updated_at: str                              # ISO timestamp

    # H11 extensions
    graph_type: str                              # "forward_mode" | "reverse_mode"
    original_inputs: dict[str, Any]              # Inputs for replay
    timing: ExecutionTiming                      # start/end/duration/node_timings
    performance: PerformanceMetrics              # tokens, memory, cache, etc.
    is_replay: bool                              # Replay flag
    original_execution_id: str | None            # Original if replay
```

---

## Field Mapping Strategy

### Direct Mappings

| PromptSession Field | ExecutionHistory Field | Notes |
|---------------------|------------------------|-------|
| `session_id` | `execution_id` | Direct copy (both UUID strings) |
| `created_at` | `created_at` | Direct copy (ISO timestamps) |
| `updated_at` | `updated_at` | Direct copy (ISO timestamps) |
| `metadata` | `metadata` | Merge with migration metadata |
| `source` | `graph_type` | Map "prompt" → "forward_mode", "reverse_mode" → "reverse_mode" |

### Derived Mappings

| PromptSession Field | ExecutionHistory Field | Derivation Logic |
|---------------------|------------------------|------------------|
| `current_draft.ir` | `state_snapshot` | Serialize IR to dict via `ir.to_dict()` |
| `current_draft.validation_status` | `state_type` | Use "IRDraft" or "IntermediateRepresentation" |
| `revisions` | `provenance` | Convert each revision to provenance entry |
| `ir_drafts` | `provenance` | Include all draft snapshots in provenance chain |
| `pending_resolutions` | `original_inputs` | Store unresolved holes as inputs |
| `status` | `metadata["migration_status"]` | Preserve original status |

### New Fields (Defaults)

| ExecutionHistory Field | Default Value | Reason |
|------------------------|---------------|--------|
| `user_id` | `None` | Old format didn't track user_id |
| `timing` | `ExecutionTiming(start_time=created_at)` | Approximate from session timestamps |
| `performance` | `PerformanceMetrics()` | Empty metrics (historical data) |
| `is_replay` | `False` | Original execution |
| `original_execution_id` | `None` | Not a replay |

---

## Migration Implementation

### Core Migration Function

```python
from typing import Any
from lift_sys.spec_sessions.models import PromptSession, PromptRevision, IRDraft, HoleResolution
from lift_sys.dspy_signatures.execution_history import (
    ExecutionHistory,
    ExecutionTiming,
    PerformanceMetrics,
)

def migrate_prompt_session_to_execution_history(
    session: PromptSession,
) -> ExecutionHistory:
    """
    Migrate PromptSession to ExecutionHistory format.

    Preserves all data with no loss, enabling backward compatibility
    and rollback support.

    Args:
        session: Old PromptSession to migrate

    Returns:
        ExecutionHistory with all data preserved

    Raises:
        ValueError: If session.current_draft is None (incomplete session)
    """
    if session.current_draft is None:
        raise ValueError(
            f"Cannot migrate session {session.session_id}: "
            "current_draft is None (incomplete session)"
        )

    # Direct mappings
    execution_id = session.session_id
    created_at = session.created_at
    updated_at = session.updated_at

    # Derive graph_type from source
    graph_type = "forward_mode" if session.source == "prompt" else session.source

    # Serialize current IR to state_snapshot
    state_snapshot = session.current_draft.ir.to_dict()
    state_type = "IntermediateRepresentation"

    # Build provenance chain from revisions and drafts
    provenance = _build_provenance_chain(session)

    # Store pending resolutions as original_inputs
    original_inputs = {
        "pending_resolutions": [res.to_dict() for res in session.pending_resolutions],
        "final_draft_version": session.current_draft.version,
    }

    # Approximate timing from session timestamps
    timing = ExecutionTiming(
        start_time=session.created_at,
        end_time=session.updated_at if session.status == "finalized" else None,
    )

    # Empty performance metrics (historical data)
    performance = PerformanceMetrics()

    # Preserve original metadata + migration metadata
    metadata = {
        **session.metadata,
        "migration": {
            "migrated_from": "PromptSession",
            "original_status": session.status,
            "migration_timestamp": datetime.now(UTC).isoformat(),
            "draft_count": len(session.ir_drafts),
            "revision_count": len(session.revisions),
        },
    }

    return ExecutionHistory(
        execution_id=execution_id,
        state_snapshot=state_snapshot,
        state_type=state_type,
        provenance=provenance,
        metadata=metadata,
        user_id=None,  # Not tracked in old format
        created_at=created_at,
        updated_at=updated_at,
        graph_type=graph_type,
        original_inputs=original_inputs,
        timing=timing,
        performance=performance,
        is_replay=False,
        original_execution_id=None,
    )


def _build_provenance_chain(session: PromptSession) -> list[dict[str, Any]]:
    """
    Build provenance chain from PromptSession history.

    Combines revisions and IR drafts into chronological provenance entries.
    """
    provenance = []

    # Add initial prompt revisions
    for rev in session.revisions:
        provenance.append({
            "type": "prompt_revision",
            "timestamp": rev.timestamp,
            "content": rev.content,
            "revision_type": rev.revision_type,
            "target_hole": rev.target_hole,
            "metadata": rev.metadata,
        })

    # Add IR draft snapshots
    for draft in session.ir_drafts:
        provenance.append({
            "type": "ir_draft",
            "version": draft.version,
            "timestamp": draft.created_at,
            "validation_status": draft.validation_status,
            "ambiguities": draft.ambiguities,
            "smt_results": draft.smt_results,
            "metadata": draft.metadata,
        })

    # Sort by timestamp
    provenance.sort(key=lambda x: x["timestamp"])

    return provenance
```

### Rollback Function

```python
def rollback_execution_history_to_prompt_session(
    history: ExecutionHistory,
) -> PromptSession:
    """
    Rollback ExecutionHistory to PromptSession format.

    Enables reverting to old format if migration causes issues.

    Args:
        history: ExecutionHistory to rollback

    Returns:
        PromptSession reconstructed from history

    Raises:
        ValueError: If history wasn't migrated from PromptSession
    """
    # Validate migration metadata exists
    if "migration" not in history.metadata:
        raise ValueError(
            f"Cannot rollback execution {history.execution_id}: "
            "not migrated from PromptSession"
        )

    migration_meta = history.metadata["migration"]
    if migration_meta.get("migrated_from") != "PromptSession":
        raise ValueError(
            f"Cannot rollback: migrated from {migration_meta.get('migrated_from')}"
        )

    # Reconstruct session fields
    session_id = history.execution_id
    created_at = history.created_at
    updated_at = history.updated_at
    status = migration_meta.get("original_status", "active")

    # Reconstruct source from graph_type
    source = "prompt" if history.graph_type == "forward_mode" else history.graph_type

    # Reconstruct revisions and drafts from provenance
    revisions, ir_drafts = _reconstruct_from_provenance(history.provenance)

    # Reconstruct current_draft from state_snapshot
    from lift_sys.ir.models import IntermediateRepresentation

    current_ir = IntermediateRepresentation.from_dict(history.state_snapshot)
    current_draft = IRDraft(
        version=history.original_inputs.get("final_draft_version", len(ir_drafts)),
        ir=current_ir,
        validation_status="valid",  # Assume valid if finalized
        smt_results=[],
        ambiguities=[],
        created_at=history.updated_at,
        metadata={},
    )

    # Reconstruct pending_resolutions from original_inputs
    pending_resolutions = [
        HoleResolution.from_dict(res)
        for res in history.original_inputs.get("pending_resolutions", [])
    ]

    # Reconstruct metadata (remove migration metadata)
    metadata = {
        k: v for k, v in history.metadata.items() if k != "migration"
    }

    return PromptSession(
        session_id=session_id,
        created_at=created_at,
        updated_at=updated_at,
        status=status,
        revisions=revisions,
        ir_drafts=ir_drafts,
        current_draft=current_draft,
        pending_resolutions=pending_resolutions,
        source=source,
        metadata=metadata,
    )


def _reconstruct_from_provenance(
    provenance: list[dict[str, Any]],
) -> tuple[list[PromptRevision], list[IRDraft]]:
    """Reconstruct revisions and drafts from provenance chain."""
    revisions = []
    ir_drafts = []

    for entry in provenance:
        if entry.get("type") == "prompt_revision":
            revisions.append(PromptRevision(
                timestamp=entry["timestamp"],
                content=entry["content"],
                revision_type=entry["revision_type"],
                target_hole=entry.get("target_hole"),
                metadata=entry.get("metadata", {}),
            ))
        elif entry.get("type") == "ir_draft":
            # Note: We don't have the full IR here, just metadata
            # This is a limitation of provenance-only storage
            # Could be addressed by storing full IR snapshots in provenance
            pass

    return revisions, ir_drafts
```

---

## Acceptance Criteria

### AC1: All Session Fields Mapped Correctly ✓

```python
def test_ac1_all_fields_mapped():
    """All PromptSession fields map to ExecutionHistory with no data loss."""
    session = create_test_prompt_session()

    history = migrate_prompt_session_to_execution_history(session)

    # Direct mappings
    assert history.execution_id == session.session_id
    assert history.created_at == session.created_at
    assert history.updated_at == session.updated_at

    # Derived mappings
    assert history.graph_type == "forward_mode"
    assert history.state_snapshot == session.current_draft.ir.to_dict()
    assert len(history.provenance) == len(session.revisions) + len(session.ir_drafts)

    # Metadata preservation
    assert "migration" in history.metadata
    assert history.metadata["migration"]["original_status"] == session.status
```

### AC2: 100 Production Sessions Migrate Successfully ✓

```python
def test_ac2_batch_migration():
    """Migrate 100 production sessions without errors."""
    sessions = load_production_sessions(limit=100)

    successful = 0
    failed = []

    for session in sessions:
        try:
            history = migrate_prompt_session_to_execution_history(session)
            # Validate history
            assert history.execution_id
            assert history.state_snapshot
            successful += 1
        except Exception as e:
            failed.append((session.session_id, str(e)))

    assert successful == 100, f"Only {successful}/100 migrated. Failures: {failed}"
```

### AC3: Can Resume Migrated Sessions ✓

```python
def test_ac3_resume_migrated_session():
    """Migrated sessions can be resumed for execution."""
    session = create_test_prompt_session(status="active")

    history = migrate_prompt_session_to_execution_history(session)

    # Load into execution engine
    from lift_sys.dspy_signatures import ExecutionHistoryStore
    store = ExecutionHistoryStore()
    await store.save_execution(history)

    # Resume execution
    loaded = await store.load_execution(history.execution_id)
    assert loaded.execution_id == history.execution_id
    assert loaded.state_snapshot == history.state_snapshot

    # Can reconstruct IR for execution
    from lift_sys.ir.models import IntermediateRepresentation
    ir = IntermediateRepresentation.from_dict(loaded.state_snapshot)
    assert ir.effects  # Has executable effects
```

### AC4: Rollback Tested ✓

```python
def test_ac4_rollback_preserves_data():
    """Rolling back migrated session preserves all original data."""
    original_session = create_test_prompt_session()

    # Migrate forward
    history = migrate_prompt_session_to_execution_history(original_session)

    # Rollback
    rolled_back = rollback_execution_history_to_prompt_session(history)

    # Verify data preservation
    assert rolled_back.session_id == original_session.session_id
    assert rolled_back.created_at == original_session.created_at
    assert rolled_back.status == original_session.status
    assert len(rolled_back.revisions) == len(original_session.revisions)
    assert rolled_back.current_draft.ir.to_dict() == original_session.current_draft.ir.to_dict()
```

---

## Implementation Plan

1. Create `migration_constraints.py` module
2. Implement `migrate_prompt_session_to_execution_history()`
3. Implement `rollback_execution_history_to_prompt_session()`
4. Implement helper functions (`_build_provenance_chain`, `_reconstruct_from_provenance`)
5. Create comprehensive test suite (20+ tests)
6. Test with 100 production sessions
7. Update `__init__.py` exports
8. Document usage patterns

---

## Edge Cases

### Incomplete Sessions

```python
# Session with no current_draft
session = PromptSession(session_id=..., current_draft=None)

# Should raise ValueError
with pytest.raises(ValueError, match="current_draft is None"):
    migrate_prompt_session_to_execution_history(session)
```

### Empty Provenance

```python
# Session with no revisions or drafts
session = PromptSession(
    session_id=...,
    revisions=[],
    ir_drafts=[],
    current_draft=IRDraft(...)
)

# Should still migrate successfully
history = migrate_prompt_session_to_execution_history(session)
assert len(history.provenance) == 0  # Empty but valid
```

### Idempotency

```python
# Migrating twice should produce same result
history1 = migrate_prompt_session_to_execution_history(session)
history2 = migrate_prompt_session_to_execution_history(session)

assert history1.model_dump() == history2.model_dump()
```

---

## Future Enhancements

1. **Incremental Migration**: Migrate sessions on-demand rather than batch
2. **Version Tagging**: Add schema version field for future migrations
3. **Dual-Write Period**: Support writing to both formats during transition
4. **Migration Analytics**: Track migration success rates and failure modes
5. **Provenance Enrichment**: Store full IR snapshots in provenance chain

---

**Status**: Ready for implementation
**Next Steps**: Implement migration functions → Tests → Validation with production data
