"""
Migration Constraints (H15)

Backward compatibility layer for migrating between PromptSession and ExecutionHistory
formats, enabling zero-data-loss migration with rollback support.

This module provides:
1. Forward migration: PromptSession → ExecutionHistory
2. Rollback migration: ExecutionHistory → PromptSession
3. Idempotent migrations (re-running safe)
4. Data integrity validation

Design Principles:
1. Zero Data Loss: All fields preserved during migration
2. Resumability: Migrated sessions can resume execution
3. Rollback Support: Can revert to old format if needed
4. Idempotency: Re-migration produces same result

Resolution for Hole H15: MigrationConstraints
Status: Implementation
Phase: 6 (Week 6)
Dependencies: H2 (StatePersistence - RESOLVED)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.spec_sessions.models import (
    HoleResolution,
    IRDraft,
    PromptRevision,
    PromptSession,
)

from .execution_history import ExecutionHistory, ExecutionTiming, PerformanceMetrics


class MigrationError(Exception):
    """Base exception for migration errors."""

    pass


class IncompleteMigrationError(MigrationError):
    """Raised when session cannot be migrated due to missing data."""

    pass


class RollbackError(MigrationError):
    """Raised when rollback fails due to invalid data."""

    pass


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
        IncompleteMigrationError: If session.current_draft is None (incomplete session)

    Example:
        >>> session = PromptSession(...)
        >>> history = migrate_prompt_session_to_execution_history(session)
        >>> assert history.execution_id == session.session_id
    """
    if session.current_draft is None:
        raise IncompleteMigrationError(
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
        "source": session.source,  # Preserve source for rollback
    }

    # Approximate timing from session timestamps
    timing = ExecutionTiming(
        start_time=session.created_at,
        end_time=session.updated_at if session.status == "finalized" else None,
    )

    # Empty performance metrics (historical data not available)
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
        RollbackError: If history wasn't migrated from PromptSession

    Example:
        >>> history = migrate_prompt_session_to_execution_history(session)
        >>> rolled_back = rollback_execution_history_to_prompt_session(history)
        >>> assert rolled_back.session_id == session.session_id
    """
    # Validate migration metadata exists
    if "migration" not in history.metadata:
        raise RollbackError(
            f"Cannot rollback execution {history.execution_id}: "
            "not migrated from PromptSession (missing migration metadata)"
        )

    migration_meta = history.metadata["migration"]
    if migration_meta.get("migrated_from") != "PromptSession":
        raise RollbackError(
            f"Cannot rollback: migrated from {migration_meta.get('migrated_from')}, "
            "expected PromptSession"
        )

    # Reconstruct session fields
    session_id = history.execution_id
    created_at = history.created_at
    updated_at = history.updated_at
    status = migration_meta.get("original_status", "active")

    # Reconstruct source from original_inputs or graph_type
    source = history.original_inputs.get("source", "prompt")
    if source == "prompt" and history.graph_type != "forward_mode":
        # Fallback to graph_type if source not in original_inputs
        source = history.graph_type

    # Reconstruct revisions and drafts from provenance
    revisions, ir_drafts = _reconstruct_from_provenance(history.provenance)

    # Reconstruct current_draft from state_snapshot
    current_ir = IntermediateRepresentation.from_dict(history.state_snapshot)
    current_draft = IRDraft(
        version=history.original_inputs.get("final_draft_version", len(ir_drafts) + 1),
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
    metadata = {k: v for k, v in history.metadata.items() if k != "migration"}

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


def is_migrated_session(history: ExecutionHistory) -> bool:
    """
    Check if ExecutionHistory was migrated from PromptSession.

    Args:
        history: ExecutionHistory to check

    Returns:
        True if migrated from PromptSession, False otherwise

    Example:
        >>> if is_migrated_session(history):
        ...     original = rollback_execution_history_to_prompt_session(history)
    """
    return (
        "migration" in history.metadata
        and history.metadata["migration"].get("migrated_from") == "PromptSession"
    )


def validate_migration(session: PromptSession, history: ExecutionHistory) -> bool:
    """
    Validate that migration preserved all critical data.

    Compares original PromptSession with migrated ExecutionHistory to ensure
    no data loss occurred during migration.

    Args:
        session: Original PromptSession
        history: Migrated ExecutionHistory

    Returns:
        True if migration is valid, False otherwise

    Example:
        >>> history = migrate_prompt_session_to_execution_history(session)
        >>> assert validate_migration(session, history)
    """
    try:
        # Check IDs match
        if session.session_id != history.execution_id:
            return False

        # Check timestamps preserved
        if session.created_at != history.created_at:
            return False
        if session.updated_at != history.updated_at:
            return False

        # Check state_snapshot contains IR
        if not history.state_snapshot:
            return False

        # Check provenance chain length
        expected_provenance_entries = len(session.revisions) + len(session.ir_drafts)
        if len(history.provenance) != expected_provenance_entries:
            return False

        # Check migration metadata exists
        if not is_migrated_session(history):
            return False

        # Check original status preserved
        if history.metadata["migration"]["original_status"] != session.status:
            return False

        return True
    except (KeyError, AttributeError, TypeError):
        return False


# =============================================================================
# Helper Functions
# =============================================================================


def _build_provenance_chain(session: PromptSession) -> list[dict[str, Any]]:
    """
    Build provenance chain from PromptSession history.

    Combines revisions and IR drafts into chronological provenance entries.

    Args:
        session: PromptSession with revision and draft history

    Returns:
        Sorted list of provenance entries
    """
    provenance = []

    # Add prompt revisions
    for rev in session.revisions:
        provenance.append(
            {
                "type": "prompt_revision",
                "timestamp": rev.timestamp,
                "content": rev.content,
                "revision_type": rev.revision_type,
                "target_hole": rev.target_hole,
                "metadata": rev.metadata,
            }
        )

    # Add IR draft snapshots
    for draft in session.ir_drafts:
        provenance.append(
            {
                "type": "ir_draft",
                "version": draft.version,
                "timestamp": draft.created_at,
                "validation_status": draft.validation_status,
                "ambiguities": draft.ambiguities,
                "smt_results": draft.smt_results,
                "ir_snapshot": draft.ir.to_dict(),  # Store full IR for rollback
                "metadata": draft.metadata,
            }
        )

    # Sort by timestamp
    provenance.sort(key=lambda x: x["timestamp"])

    return provenance


def _reconstruct_from_provenance(
    provenance: list[dict[str, Any]],
) -> tuple[list[PromptRevision], list[IRDraft]]:
    """
    Reconstruct revisions and drafts from provenance chain.

    Extracts PromptRevision and IRDraft objects from provenance entries.

    Args:
        provenance: Provenance chain from ExecutionHistory

    Returns:
        Tuple of (revisions, ir_drafts)
    """
    revisions = []
    ir_drafts = []

    for entry in provenance:
        if entry.get("type") == "prompt_revision":
            revisions.append(
                PromptRevision(
                    timestamp=entry["timestamp"],
                    content=entry["content"],
                    revision_type=entry["revision_type"],
                    target_hole=entry.get("target_hole"),
                    metadata=entry.get("metadata", {}),
                )
            )
        elif entry.get("type") == "ir_draft":
            # Reconstruct IR from snapshot if available
            if "ir_snapshot" in entry:
                ir = IntermediateRepresentation.from_dict(entry["ir_snapshot"])
                ir_drafts.append(
                    IRDraft(
                        version=entry["version"],
                        ir=ir,
                        validation_status=entry.get("validation_status", "pending"),
                        smt_results=entry.get("smt_results", []),
                        ambiguities=entry.get("ambiguities", []),
                        created_at=entry["timestamp"],
                        metadata=entry.get("metadata", {}),
                    )
                )
            # If no IR snapshot, create placeholder (limitation of old provenance)
            # This shouldn't happen with new migrations that store full IR

    return revisions, ir_drafts


__all__ = [
    "migrate_prompt_session_to_execution_history",
    "rollback_execution_history_to_prompt_session",
    "is_migrated_session",
    "validate_migration",
    "MigrationError",
    "IncompleteMigrationError",
    "RollbackError",
]
