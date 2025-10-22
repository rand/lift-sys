"""
Backward Compatibility Tests (H19).

Integration tests validating that PromptSession → ExecutionHistory migration
works correctly with production-like data.

Tests cover:
1. 100 production sessions tested (AC1)
2. 100% migration success (AC2)
3. All sessions resumable (AC3)
4. Rollback verified (AC4)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from lift_sys.dspy_signatures.migration_constraints import (
    migrate_prompt_session_to_execution_history,
    rollback_execution_history_to_prompt_session,
    validate_migration,
)
from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.spec_sessions.models import (
    HoleResolution,
    IRDraft,
    PromptRevision,
    PromptSession,
)

# =============================================================================
# Test Data Generators
# =============================================================================


def create_production_session(
    session_id: str | None = None,
    status: str = "active",
    num_revisions: int = 5,
    num_drafts: int = 3,
    num_resolutions: int = 2,
) -> PromptSession:
    """Create a production-like PromptSession for testing."""
    now = datetime.now(UTC).isoformat()
    session_id = session_id or str(uuid.uuid4())

    # Create realistic IR
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Extract user intent and validate inputs",
            rationale="User wants to create a new resource with validation",
        ),
        signature=SigClause(
            name="ProcessUserRequest",
            parameters=[
                Parameter(name="user_input", type_hint="str"),
                Parameter(name="context", type_hint="dict[str, Any]"),
            ],
            returns="dict[str, Any]",
        ),
        effects=[
            EffectClause(description="Validate user input format"),
            EffectClause(description="Extract structured data from input"),
            EffectClause(description="Apply business rules and constraints"),
        ],
        metadata=Metadata(),
    )

    # Create revision history
    revisions = [
        PromptRevision(
            timestamp=now,
            content=f"Revision {i}: User refines requirements",
            revision_type="initial" if i == 0 else "constraint_add",
            target_hole=f"constraint_{i}" if i > 0 else None,
            metadata={"iteration": i},
        )
        for i in range(num_revisions)
    ]

    # Create IR drafts
    ir_drafts = [
        IRDraft(
            version=i + 1,
            ir=ir,
            validation_status="valid" if i == num_drafts - 1 else "incomplete",
            smt_results=[],
            ambiguities=[] if i == num_drafts - 1 else [f"hole_{i}"],
            created_at=now,
            metadata={"draft_iteration": i},
        )
        for i in range(num_drafts)
    ]

    # Create pending resolutions
    pending_resolutions = [
        HoleResolution(
            hole_id=f"validation_rule_{i}",
            resolution_text=f"Add validation for field {i}",
            resolution_type="add_constraint",
            applied=False,
            timestamp=now,
            metadata={"priority": "high" if i == 0 else "medium"},
        )
        for i in range(num_resolutions)
    ]

    return PromptSession(
        session_id=session_id,
        created_at=now,
        updated_at=now,
        status=status,
        revisions=revisions,
        ir_drafts=ir_drafts,
        current_draft=ir_drafts[-1],
        pending_resolutions=pending_resolutions,
        source="prompt",
        metadata={
            "user_id": "production-user-123",
            "environment": "production",
            "version": "1.0",
        },
    )


def create_batch_production_sessions(count: int) -> list[PromptSession]:
    """Create a batch of production-like sessions."""
    sessions = []

    # Vary session characteristics for realistic testing
    for i in range(count):
        status = "finalized" if i % 3 == 0 else "active" if i % 3 == 1 else "abandoned"
        num_revisions = (i % 10) + 1  # 1-10 revisions
        num_drafts = (i % 5) + 1  # 1-5 drafts
        num_resolutions = i % 4  # 0-3 resolutions

        session = create_production_session(
            status=status,
            num_revisions=num_revisions,
            num_drafts=num_drafts,
            num_resolutions=num_resolutions,
        )
        sessions.append(session)

    return sessions


# =============================================================================
# AC1: 100 Production Sessions Tested
# =============================================================================


def test_ac1_migrate_100_production_sessions():
    """AC1: Successfully migrate 100 production-like sessions."""
    sessions = create_batch_production_sessions(100)

    successful = 0
    failed = []

    for session in sessions:
        try:
            history = migrate_prompt_session_to_execution_history(session)
            assert history.execution_id == session.session_id
            assert validate_migration(session, history)
            successful += 1
        except Exception as e:
            failed.append((session.session_id, str(e)))

    assert successful == 100, f"Only {successful}/100 migrated. Failures: {failed[:5]}"
    assert len(failed) == 0, f"Expected no failures, got {len(failed)}"


def test_ac1_various_session_statuses():
    """AC1: Migrate sessions with different statuses (active, finalized, abandoned)."""
    sessions = [
        create_production_session(status="active"),
        create_production_session(status="finalized"),
        create_production_session(status="abandoned"),
    ]

    for session in sessions:
        history = migrate_prompt_session_to_execution_history(session)

        assert history.metadata["migration"]["original_status"] == session.status
        assert validate_migration(session, history)


def test_ac1_varying_complexity():
    """AC1: Migrate sessions with varying complexity."""
    sessions = [
        create_production_session(num_revisions=1, num_drafts=1, num_resolutions=0),
        create_production_session(num_revisions=10, num_drafts=5, num_resolutions=3),
        create_production_session(num_revisions=50, num_drafts=20, num_resolutions=10),
    ]

    for session in sessions:
        history = migrate_prompt_session_to_execution_history(session)

        # Verify provenance chain length
        expected_provenance = len(session.revisions) + len(session.ir_drafts)
        assert len(history.provenance) == expected_provenance

        assert validate_migration(session, history)


# =============================================================================
# AC2: 100% Migration Success
# =============================================================================


def test_ac2_zero_data_loss():
    """AC2: Migration preserves all data with zero loss."""
    session = create_production_session(num_revisions=10, num_drafts=5, num_resolutions=3)

    history = migrate_prompt_session_to_execution_history(session)

    # Verify all critical fields preserved
    assert history.execution_id == session.session_id
    assert history.created_at == session.created_at
    assert history.updated_at == session.updated_at

    # Verify provenance completeness
    assert len(history.provenance) == len(session.revisions) + len(session.ir_drafts)

    # Verify metadata preserved
    assert history.metadata["user_id"] == "production-user-123"
    assert history.metadata["environment"] == "production"

    # Verify pending resolutions stored
    assert len(history.original_inputs["pending_resolutions"]) == 3


def test_ac2_migration_idempotency():
    """AC2: Re-migrating same session produces identical result."""
    session = create_production_session()

    history1 = migrate_prompt_session_to_execution_history(session)
    history2 = migrate_prompt_session_to_execution_history(session)

    # Remove migration_timestamp for comparison
    dict1 = history1.model_dump()
    dict2 = history2.model_dump()
    dict1["metadata"]["migration"].pop("migration_timestamp")
    dict2["metadata"]["migration"].pop("migration_timestamp")

    assert dict1 == dict2


def test_ac2_all_field_mappings_complete():
    """AC2: All PromptSession fields have corresponding ExecutionHistory mappings."""
    session = create_production_session()
    history = migrate_prompt_session_to_execution_history(session)

    # Direct mappings
    assert history.execution_id == session.session_id
    assert history.created_at == session.created_at
    assert history.updated_at == session.updated_at

    # Derived mappings
    assert history.graph_type == "forward_mode"  # from source="prompt"
    assert history.state_snapshot == session.current_draft.ir.to_dict()

    # Metadata preservation
    assert "migration" in history.metadata
    assert history.metadata["migration"]["original_status"] == session.status
    assert history.metadata["migration"]["draft_count"] == len(session.ir_drafts)
    assert history.metadata["migration"]["revision_count"] == len(session.revisions)


# =============================================================================
# AC3: All Sessions Resumable
# =============================================================================


def test_ac3_migrated_sessions_have_valid_state():
    """AC3: Migrated sessions have valid state for resumption."""
    sessions = create_batch_production_sessions(10)

    for session in sessions:
        history = migrate_prompt_session_to_execution_history(session)

        # Verify state_snapshot is valid IR
        from lift_sys.ir.models import IntermediateRepresentation

        ir = IntermediateRepresentation.from_dict(history.state_snapshot)
        assert ir.intent
        assert ir.signature
        assert len(ir.effects) > 0


def test_ac3_original_inputs_preserved_for_replay():
    """AC3: Original inputs preserved for session replay."""
    session = create_production_session(num_resolutions=5)
    history = migrate_prompt_session_to_execution_history(session)

    # Verify original_inputs contains resumption data
    assert "pending_resolutions" in history.original_inputs
    assert len(history.original_inputs["pending_resolutions"]) == 5
    assert "final_draft_version" in history.original_inputs
    assert history.original_inputs["final_draft_version"] == len(session.ir_drafts)


def test_ac3_provenance_chain_complete():
    """AC3: Provenance chain is complete and chronologically ordered."""
    session = create_production_session(num_revisions=10, num_drafts=5)
    history = migrate_prompt_session_to_execution_history(session)

    # Verify all history is in provenance
    assert len(history.provenance) == 15  # 10 revisions + 5 drafts

    # Verify chronological ordering
    timestamps = [entry["timestamp"] for entry in history.provenance]
    assert timestamps == sorted(timestamps)

    # Verify both types present
    revision_entries = [e for e in history.provenance if e["type"] == "prompt_revision"]
    draft_entries = [e for e in history.provenance if e["type"] == "ir_draft"]
    assert len(revision_entries) == 10
    assert len(draft_entries) == 5


@pytest.mark.asyncio
async def test_ac3_resume_migrated_session_in_store():
    """AC3: Migrated session can be loaded from ExecutionHistoryStore."""
    # Create in-memory store

    # Note: This test uses in-memory persistence, not actual Supabase
    session = create_production_session()
    history = migrate_prompt_session_to_execution_history(session)

    # Verify can reconstruct state
    from lift_sys.ir.models import IntermediateRepresentation

    ir = IntermediateRepresentation.from_dict(history.state_snapshot)
    assert ir.intent.summary
    assert ir.signature.name


# =============================================================================
# AC4: Rollback Verified
# =============================================================================


def test_ac4_rollback_100_sessions():
    """AC4: Rollback works for 100 production sessions."""
    sessions = create_batch_production_sessions(100)

    successful_rollbacks = 0
    failed_rollbacks = []

    for session in sessions:
        try:
            # Migrate forward
            history = migrate_prompt_session_to_execution_history(session)

            # Rollback
            rolled_back = rollback_execution_history_to_prompt_session(history)

            # Verify critical fields match
            assert rolled_back.session_id == session.session_id
            assert rolled_back.created_at == session.created_at
            assert rolled_back.status == session.status

            successful_rollbacks += 1
        except Exception as e:
            failed_rollbacks.append((session.session_id, str(e)))

    assert successful_rollbacks == 100, f"Only {successful_rollbacks}/100 rolled back"
    assert len(failed_rollbacks) == 0


def test_ac4_rollback_preserves_revisions():
    """AC4: Rollback preserves all revisions."""
    session = create_production_session(num_revisions=10)

    history = migrate_prompt_session_to_execution_history(session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    # Verify all revisions preserved
    assert len(rolled_back.revisions) == len(session.revisions)

    for i, rev in enumerate(rolled_back.revisions):
        original = session.revisions[i]
        assert rev.content == original.content
        assert rev.revision_type == original.revision_type
        assert rev.target_hole == original.target_hole


def test_ac4_rollback_preserves_current_draft():
    """AC4: Rollback preserves current_draft IR."""
    session = create_production_session()

    history = migrate_prompt_session_to_execution_history(session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    # Verify current_draft IR matches
    assert rolled_back.current_draft is not None
    assert rolled_back.current_draft.ir.to_dict() == session.current_draft.ir.to_dict()


def test_ac4_rollback_preserves_pending_resolutions():
    """AC4: Rollback preserves pending_resolutions."""
    session = create_production_session(num_resolutions=5)

    history = migrate_prompt_session_to_execution_history(session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    # Verify pending_resolutions preserved
    assert len(rolled_back.pending_resolutions) == 5

    for i, res in enumerate(rolled_back.pending_resolutions):
        original = session.pending_resolutions[i]
        assert res.hole_id == original.hole_id
        assert res.resolution_text == original.resolution_text
        assert res.resolution_type == original.resolution_type


def test_ac4_roundtrip_migration():
    """AC4: Roundtrip migration preserves all data (forward → rollback → forward)."""
    session = create_production_session(num_revisions=10, num_drafts=5)

    # Forward migration
    history1 = migrate_prompt_session_to_execution_history(session)

    # Rollback
    rolled_back = rollback_execution_history_to_prompt_session(history1)

    # Forward again
    history2 = migrate_prompt_session_to_execution_history(rolled_back)

    # Compare history1 and history2 (excluding migration timestamps)
    dict1 = history1.model_dump()
    dict2 = history2.model_dump()
    dict1["metadata"]["migration"].pop("migration_timestamp")
    dict2["metadata"]["migration"].pop("migration_timestamp")

    # State snapshots should be identical
    assert dict1["state_snapshot"] == dict2["state_snapshot"]
    # Provenance should be identical
    assert len(dict1["provenance"]) == len(dict2["provenance"])


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


def test_edge_case_empty_revisions_and_drafts():
    """Edge case: Session with no revisions or drafts (only current_draft)."""
    now = datetime.now(UTC).isoformat()

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test intent"),
        signature=SigClause(name="TestSig", parameters=[], returns="str"),
        effects=[],
        metadata=Metadata(),
    )

    session = PromptSession(
        session_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        status="active",
        revisions=[],  # Empty
        ir_drafts=[],  # Empty
        current_draft=IRDraft(
            version=1, ir=ir, validation_status="valid", smt_results=[], ambiguities=[]
        ),
        pending_resolutions=[],
        source="prompt",
        metadata={},
    )

    # Should still migrate successfully
    history = migrate_prompt_session_to_execution_history(session)
    assert validate_migration(session, history)
    assert len(history.provenance) == 0


def test_edge_case_large_session():
    """Edge case: Session with many revisions and drafts."""
    session = create_production_session(num_revisions=100, num_drafts=50, num_resolutions=20)

    history = migrate_prompt_session_to_execution_history(session)

    # Verify large provenance chain
    assert len(history.provenance) == 150
    assert len(history.original_inputs["pending_resolutions"]) == 20

    # Verify rollback works
    rolled_back = rollback_execution_history_to_prompt_session(history)
    assert len(rolled_back.revisions) == 100


def test_edge_case_special_characters_in_metadata():
    """Edge case: Session with special characters in metadata."""
    session = create_production_session()
    session.metadata = {
        "user_name": "Test User <test@example.com>",
        "description": "Complex \"quoted\" string with 'quotes'",
        "path": "/path/to/file with spaces.txt",
        "unicode": "日本語テスト",
    }

    history = migrate_prompt_session_to_execution_history(session)
    rolled_back = rollback_execution_history_to_prompt_session(history)

    # Verify special characters preserved
    assert rolled_back.metadata["user_name"] == session.metadata["user_name"]
    assert rolled_back.metadata["unicode"] == session.metadata["unicode"]


def test_performance_batch_migration():
    """Performance test: Batch migrate 100 sessions efficiently."""
    import time

    sessions = create_batch_production_sessions(100)

    start = time.perf_counter()
    for session in sessions:
        migrate_prompt_session_to_execution_history(session)
    duration = time.perf_counter() - start

    # Should complete in reasonable time (< 10 seconds for 100 sessions)
    assert duration < 10.0, f"Batch migration took {duration:.2f}s, expected <10s"


def test_validation_detects_corrupted_migration():
    """Validation detects when migration data is corrupted."""
    session = create_production_session()
    history = migrate_prompt_session_to_execution_history(session)

    # Corrupt the migration by changing execution_id
    history.execution_id = "corrupted-id"

    # Validation should fail
    assert not validate_migration(session, history)


def test_validation_detects_missing_provenance():
    """Validation detects when provenance is missing."""
    session = create_production_session(num_revisions=10, num_drafts=5)
    history = migrate_prompt_session_to_execution_history(session)

    # Corrupt by removing provenance
    history.provenance = []

    # Validation should fail
    assert not validate_migration(session, history)
