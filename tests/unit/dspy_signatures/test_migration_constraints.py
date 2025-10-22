"""
Tests for Migration Constraints (H15).

Tests cover:
1. All session fields mapped correctly (AC1)
2. Batch migration of multiple sessions (AC2)
3. Resume migrated sessions (AC3)
4. Rollback tested (AC4)
5. Edge cases (incomplete sessions, empty provenance, idempotency)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from lift_sys.dspy_signatures.execution_history import ExecutionHistory
from lift_sys.dspy_signatures.migration_constraints import (
    IncompleteMigrationError,
    RollbackError,
    is_migrated_session,
    migrate_prompt_session_to_execution_history,
    rollback_execution_history_to_prompt_session,
    validate_migration,
)
from lift_sys.ir.models import EffectClause, IntermediateRepresentation, Parameter, SigClause
from lift_sys.spec_sessions.models import (
    HoleResolution,
    IRDraft,
    PromptRevision,
    PromptSession,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_ir() -> IntermediateRepresentation:
    """Create sample IR for testing."""
    return IntermediateRepresentation(
        effects=[
            EffectClause(
                signature=SigClause(
                    name="ExtractIntent",
                    inputs=[
                        Parameter(name="prompt", type_hint="str"),
                    ],
                    outputs=[
                        Parameter(name="intent", type_hint="str"),
                        Parameter(name="confidence", type_hint="float"),
                    ],
                ),
                io_examples=[
                    {
                        "prompt": "Create user profile",
                        "intent": "create_user",
                        "confidence": 0.95,
                    }
                ],
            )
        ],
        metadata={"version": "1.0"},
    )


@pytest.fixture
def sample_prompt_session(sample_ir: IntermediateRepresentation) -> PromptSession:
    """Create sample PromptSession for testing."""
    now = datetime.now(UTC).isoformat()

    # Create revisions
    revisions = [
        PromptRevision(
            timestamp=now,
            content="Create user profile",
            revision_type="initial",
            target_hole=None,
            metadata={},
        ),
        PromptRevision(
            timestamp=now,
            content="Add confidence score",
            revision_type="constraint_add",
            target_hole="confidence_score",
            metadata={"priority": "high"},
        ),
    ]

    # Create IR drafts
    ir_drafts = [
        IRDraft(
            version=1,
            ir=sample_ir,
            validation_status="valid",
            smt_results=[],
            ambiguities=[],
            created_at=now,
            metadata={},
        ),
        IRDraft(
            version=2,
            ir=sample_ir,
            validation_status="valid",
            smt_results=[],
            ambiguities=[],
            created_at=now,
            metadata={"improved": True},
        ),
    ]

    # Create pending resolutions
    pending_resolutions = [
        HoleResolution(
            hole_id="error_handling",
            resolution_text="Add retry logic",
            resolution_type="add_constraint",
            applied=False,
            timestamp=now,
            metadata={},
        )
    ]

    return PromptSession(
        session_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status="active",
        revisions=revisions,
        ir_drafts=ir_drafts,
        current_draft=ir_drafts[1],  # Use version 2
        pending_resolutions=pending_resolutions,
        source="prompt",
        metadata={"user": "test_user"},
    )


# =============================================================================
# AC1: All Session Fields Mapped Correctly
# =============================================================================


def test_ac1_direct_field_mappings(sample_prompt_session: PromptSession):
    """AC1: Direct field mappings preserve data exactly."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    # Direct mappings
    assert history.execution_id == sample_prompt_session.session_id
    assert history.created_at == sample_prompt_session.created_at
    assert history.updated_at == sample_prompt_session.updated_at


def test_ac1_derived_field_mappings(sample_prompt_session: PromptSession):
    """AC1: Derived field mappings correctly transform data."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    # Source → graph_type
    assert history.graph_type == "forward_mode"

    # current_draft.ir → state_snapshot
    assert history.state_snapshot == sample_prompt_session.current_draft.ir.to_dict()

    # State type
    assert history.state_type == "IntermediateRepresentation"


def test_ac1_provenance_chain_built(sample_prompt_session: PromptSession):
    """AC1: Provenance chain includes all revisions and drafts."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    expected_entries = len(sample_prompt_session.revisions) + len(sample_prompt_session.ir_drafts)
    assert len(history.provenance) == expected_entries

    # Check revision entries
    revision_entries = [e for e in history.provenance if e["type"] == "prompt_revision"]
    assert len(revision_entries) == len(sample_prompt_session.revisions)

    # Check draft entries
    draft_entries = [e for e in history.provenance if e["type"] == "ir_draft"]
    assert len(draft_entries) == len(sample_prompt_session.ir_drafts)

    # Verify chronological order
    timestamps = [e["timestamp"] for e in history.provenance]
    assert timestamps == sorted(timestamps)


def test_ac1_metadata_preserved(sample_prompt_session: PromptSession):
    """AC1: Original metadata preserved with migration metadata added."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    # Original metadata preserved
    assert history.metadata["user"] == "test_user"

    # Migration metadata added
    assert "migration" in history.metadata
    assert history.metadata["migration"]["migrated_from"] == "PromptSession"
    assert history.metadata["migration"]["original_status"] == "active"
    assert history.metadata["migration"]["draft_count"] == 2
    assert history.metadata["migration"]["revision_count"] == 2


def test_ac1_original_inputs_preserved(sample_prompt_session: PromptSession):
    """AC1: Pending resolutions stored in original_inputs."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert "pending_resolutions" in history.original_inputs
    assert len(history.original_inputs["pending_resolutions"]) == 1
    assert history.original_inputs["final_draft_version"] == 2


def test_ac1_timing_approximated(sample_prompt_session: PromptSession):
    """AC1: Timing approximated from session timestamps."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.timing.start_time == sample_prompt_session.created_at
    assert history.timing.end_time is None  # Active session, not finalized


def test_ac1_finalized_session_has_end_time(sample_prompt_session: PromptSession):
    """AC1: Finalized sessions have end_time set."""
    sample_prompt_session.status = "finalized"

    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.timing.end_time == sample_prompt_session.updated_at


# =============================================================================
# AC2: Batch Migration
# =============================================================================


def test_ac2_multiple_sessions_migrate_successfully(sample_ir: IntermediateRepresentation):
    """AC2: Multiple sessions migrate without errors."""
    sessions = [
        PromptSession.create_new(
            source="prompt",
            initial_draft=IRDraft(
                version=1,
                ir=sample_ir,
                validation_status="valid",
                smt_results=[],
                ambiguities=[],
            ),
        )
        for _ in range(10)
    ]

    successful = 0
    failed = []

    for session in sessions:
        try:
            history = migrate_prompt_session_to_execution_history(session)
            assert history.execution_id == session.session_id
            successful += 1
        except Exception as e:
            failed.append((session.session_id, str(e)))

    assert successful == 10, f"Only {successful}/10 migrated. Failures: {failed}"


def test_ac2_different_sources_migrate_correctly(sample_ir: IntermediateRepresentation):
    """AC2: Sessions from different sources migrate correctly."""
    prompt_session = PromptSession.create_new(
        source="prompt",
        initial_draft=IRDraft(
            version=1, ir=sample_ir, validation_status="valid", smt_results=[], ambiguities=[]
        ),
    )
    reverse_session = PromptSession.create_new(
        source="reverse_mode",
        initial_draft=IRDraft(
            version=1, ir=sample_ir, validation_status="valid", smt_results=[], ambiguities=[]
        ),
    )

    prompt_history = migrate_prompt_session_to_execution_history(prompt_session)
    reverse_history = migrate_prompt_session_to_execution_history(reverse_session)

    assert prompt_history.graph_type == "forward_mode"
    assert reverse_history.graph_type == "reverse_mode"


# =============================================================================
# AC3: Resume Migrated Sessions
# =============================================================================


def test_ac3_migrated_session_has_valid_state(sample_prompt_session: PromptSession):
    """AC3: Migrated session has valid state for execution."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    # Can reconstruct IR from state_snapshot
    from lift_sys.ir.models import IntermediateRepresentation

    ir = IntermediateRepresentation.from_dict(history.state_snapshot)
    assert ir.effects
    assert len(ir.effects) > 0


def test_ac3_migrated_session_has_execution_id(sample_prompt_session: PromptSession):
    """AC3: Migrated session has valid execution_id for tracking."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.execution_id
    assert len(history.execution_id) > 0  # Not empty


def test_ac3_migrated_session_has_original_inputs(sample_prompt_session: PromptSession):
    """AC3: Migrated session preserves original inputs for replay."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.original_inputs
    assert "pending_resolutions" in history.original_inputs
    assert "final_draft_version" in history.original_inputs


# =============================================================================
# AC4: Rollback Tested
# =============================================================================


def test_ac4_rollback_preserves_session_id(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves session_id."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert rolled_back.session_id == sample_prompt_session.session_id


def test_ac4_rollback_preserves_timestamps(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves created_at and updated_at."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert rolled_back.created_at == sample_prompt_session.created_at
    assert rolled_back.updated_at == sample_prompt_session.updated_at


def test_ac4_rollback_preserves_status(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves original status."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert rolled_back.status == sample_prompt_session.status


def test_ac4_rollback_preserves_revisions(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves all revisions."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert len(rolled_back.revisions) == len(sample_prompt_session.revisions)
    for i, rev in enumerate(rolled_back.revisions):
        original = sample_prompt_session.revisions[i]
        assert rev.content == original.content
        assert rev.revision_type == original.revision_type


def test_ac4_rollback_preserves_current_draft(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves current_draft IR."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert rolled_back.current_draft is not None
    assert (
        rolled_back.current_draft.ir.to_dict() == sample_prompt_session.current_draft.ir.to_dict()
    )


def test_ac4_rollback_preserves_pending_resolutions(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves pending_resolutions."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert len(rolled_back.pending_resolutions) == len(sample_prompt_session.pending_resolutions)
    assert (
        rolled_back.pending_resolutions[0].hole_id
        == sample_prompt_session.pending_resolutions[0].hole_id
    )


def test_ac4_rollback_preserves_metadata(sample_prompt_session: PromptSession):
    """AC4: Rollback preserves original metadata (excluding migration metadata)."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    assert rolled_back.metadata["user"] == "test_user"
    assert "migration" not in rolled_back.metadata  # Migration metadata removed


def test_ac4_rollback_fails_on_non_migrated_session():
    """AC4: Rollback fails if session wasn't migrated from PromptSession."""
    from lift_sys.dspy_signatures.execution_history import ExecutionTiming

    # Create ExecutionHistory without migration metadata
    history = ExecutionHistory(
        execution_id=str(uuid.uuid4()),
        state_snapshot={},
        state_type="IntermediateRepresentation",
        provenance=[],
        metadata={},  # No migration metadata
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        timing=ExecutionTiming(),
    )

    with pytest.raises(RollbackError, match="not migrated from PromptSession"):
        rollback_execution_history_to_prompt_session(history)


# =============================================================================
# Validation
# =============================================================================


def test_validate_migration_succeeds_for_valid_migration(sample_prompt_session: PromptSession):
    """validate_migration returns True for valid migration."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert validate_migration(sample_prompt_session, history) is True


def test_validate_migration_fails_for_mismatched_ids(sample_prompt_session: PromptSession):
    """validate_migration returns False if IDs don't match."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    history.execution_id = "different-id"

    assert validate_migration(sample_prompt_session, history) is False


def test_validate_migration_fails_for_wrong_timestamp(sample_prompt_session: PromptSession):
    """validate_migration returns False if timestamps don't match."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    history.created_at = "2020-01-01T00:00:00Z"

    assert validate_migration(sample_prompt_session, history) is False


def test_validate_migration_fails_for_missing_provenance(sample_prompt_session: PromptSession):
    """validate_migration returns False if provenance count is wrong."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)
    history.provenance = []

    assert validate_migration(sample_prompt_session, history) is False


def test_is_migrated_session_returns_true(sample_prompt_session: PromptSession):
    """is_migrated_session returns True for migrated sessions."""
    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert is_migrated_session(history) is True


def test_is_migrated_session_returns_false_for_non_migrated():
    """is_migrated_session returns False for non-migrated sessions."""
    from lift_sys.dspy_signatures.execution_history import ExecutionTiming

    history = ExecutionHistory(
        execution_id=str(uuid.uuid4()),
        state_snapshot={},
        state_type="IntermediateRepresentation",
        provenance=[],
        metadata={},  # No migration metadata
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        timing=ExecutionTiming(),
    )

    assert is_migrated_session(history) is False


# =============================================================================
# Edge Cases
# =============================================================================


def test_incomplete_session_raises_error(sample_ir: IntermediateRepresentation):
    """Migrating session with no current_draft raises error."""
    session = PromptSession(
        session_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        status="active",
        revisions=[],
        ir_drafts=[],
        current_draft=None,  # Incomplete
        pending_resolutions=[],
        source="prompt",
        metadata={},
    )

    with pytest.raises(IncompleteMigrationError, match="current_draft is None"):
        migrate_prompt_session_to_execution_history(session)


def test_empty_provenance_migrates_successfully(sample_ir: IntermediateRepresentation):
    """Session with no revisions or drafts still migrates."""
    session = PromptSession(
        session_id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        status="active",
        revisions=[],  # Empty
        ir_drafts=[],  # Empty
        current_draft=IRDraft(
            version=1, ir=sample_ir, validation_status="valid", smt_results=[], ambiguities=[]
        ),
        pending_resolutions=[],
        source="prompt",
        metadata={},
    )

    history = migrate_prompt_session_to_execution_history(session)

    assert len(history.provenance) == 0  # Empty but valid


def test_idempotency_same_result_on_remigration(sample_prompt_session: PromptSession):
    """Migrating same session twice produces same result."""
    history1 = migrate_prompt_session_to_execution_history(sample_prompt_session)
    history2 = migrate_prompt_session_to_execution_history(sample_prompt_session)

    # Compare serialized versions (excluding migration_timestamp which will differ)
    dict1 = history1.model_dump()
    dict2 = history2.model_dump()

    # Remove migration_timestamp for comparison
    dict1["metadata"]["migration"].pop("migration_timestamp")
    dict2["metadata"]["migration"].pop("migration_timestamp")

    assert dict1 == dict2


def test_abandoned_session_status_preserved(sample_prompt_session: PromptSession):
    """Abandoned sessions preserve status through migration."""
    sample_prompt_session.status = "abandoned"

    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.metadata["migration"]["original_status"] == "abandoned"

    rolled_back = rollback_execution_history_to_prompt_session(history)
    assert rolled_back.status == "abandoned"


def test_finalized_session_status_preserved(sample_prompt_session: PromptSession):
    """Finalized sessions preserve status through migration."""
    sample_prompt_session.status = "finalized"

    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.metadata["migration"]["original_status"] == "finalized"
    assert history.timing.end_time == sample_prompt_session.updated_at


def test_empty_pending_resolutions(sample_prompt_session: PromptSession):
    """Sessions with no pending resolutions migrate correctly."""
    sample_prompt_session.pending_resolutions = []

    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert len(history.original_inputs["pending_resolutions"]) == 0

    rolled_back = rollback_execution_history_to_prompt_session(history)
    assert len(rolled_back.pending_resolutions) == 0


def test_large_metadata_preserved(sample_prompt_session: PromptSession):
    """Large metadata objects are preserved through migration."""
    sample_prompt_session.metadata = {
        "user": "test_user",
        "tags": ["important", "test", "migration"],
        "config": {"max_retries": 3, "timeout": 30},
        "notes": "This is a test session with lots of metadata",
    }

    history = migrate_prompt_session_to_execution_history(sample_prompt_session)

    assert history.metadata["user"] == "test_user"
    assert history.metadata["tags"] == ["important", "test", "migration"]
    assert history.metadata["config"]["max_retries"] == 3

    rolled_back = rollback_execution_history_to_prompt_session(history)
    assert rolled_back.metadata == sample_prompt_session.metadata
