"""Tests for SupabaseSessionStore."""

import os
import uuid
from datetime import UTC, datetime

import pytest

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.spec_sessions import (
    HoleResolution,
    IRDraft,
    PromptRevision,
    PromptSession,
    SupabaseSessionStore,
)

# Skip all tests if Supabase credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_KEY"),
    reason="Supabase credentials not configured",
)


@pytest.fixture
def test_user_id():
    """Generate a unique user ID for test isolation."""
    return str(uuid.uuid4())


@pytest.fixture
def store(test_user_id):
    """Create a SupabaseSessionStore instance for testing."""
    return SupabaseSessionStore(user_id=test_user_id)


@pytest.fixture
def sample_session(test_user_id):
    """Create a sample PromptSession for testing."""
    session = PromptSession.create_new(
        source="prompt",
        metadata={"test": True, "user_id": test_user_id},
    )

    # Add a revision
    revision = PromptRevision(
        timestamp=datetime.now(UTC).isoformat() + "Z",
        content="Create a function to calculate fibonacci numbers",
        revision_type="initial",
    )
    session.add_revision(revision)

    # Add an IR draft
    ir = IntermediateRepresentation(
        function_name="fibonacci",
        parameters=[{"name": "n", "type": "int"}],
        return_type="int",
        preconditions=["n >= 0"],
        postconditions=[],
        effects=[],
    )

    draft = IRDraft(
        version=1,
        ir=ir,
        validation_status="valid",
        ambiguities=[],
    )
    session.add_draft(draft)

    # Add a hole resolution
    resolution = HoleResolution(
        hole_id="hole_1",
        resolution_text="Use iterative approach for performance",
        resolution_type="clarify_intent",
    )
    session.add_resolution(resolution)

    return session


class TestSupabaseSessionStoreBasicOperations:
    """Test basic CRUD operations."""

    def test_create_session(self, store, sample_session):
        """Test creating a new session."""
        session_id = store.create(sample_session)
        assert session_id == sample_session.session_id
        assert uuid.UUID(session_id)  # Valid UUID

    def test_get_session(self, store, sample_session):
        """Test retrieving a session by ID."""
        # Create session first
        store.create(sample_session)

        # Retrieve it
        retrieved = store.get(sample_session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id
        assert retrieved.status == sample_session.status
        assert retrieved.source == sample_session.source
        assert len(retrieved.revisions) == len(sample_session.revisions)
        assert len(retrieved.ir_drafts) == len(sample_session.ir_drafts)
        assert len(retrieved.pending_resolutions) == len(sample_session.pending_resolutions)

    def test_get_nonexistent_session(self, store):
        """Test retrieving a non-existent session returns None."""
        fake_id = str(uuid.uuid4())
        retrieved = store.get(fake_id)
        assert retrieved is None

    def test_update_session(self, store, sample_session):
        """Test updating an existing session."""
        # Create session
        store.create(sample_session)

        # Modify session
        sample_session.status = "finalized"
        new_revision = PromptRevision(
            timestamp=datetime.now(UTC).isoformat() + "Z",
            content="Add memoization",
            revision_type="hole_fill",
        )
        sample_session.add_revision(new_revision)

        # Update in database
        store.update(sample_session)

        # Verify update
        retrieved = store.get(sample_session.session_id)
        assert retrieved.status == "finalized"
        assert len(retrieved.revisions) == 2
        assert retrieved.revisions[-1].content == "Add memoization"

    def test_update_nonexistent_session_raises_error(self, store):
        """Test updating a non-existent session raises KeyError."""
        fake_session = PromptSession.create_new()
        with pytest.raises(KeyError, match="not found"):
            store.update(fake_session)

    def test_delete_session(self, store, sample_session):
        """Test deleting a session."""
        # Create session
        store.create(sample_session)

        # Verify it exists
        assert store.get(sample_session.session_id) is not None

        # Delete it
        store.delete(sample_session.session_id)

        # Verify it's gone
        assert store.get(sample_session.session_id) is None


class TestSupabaseSessionStoreListOperations:
    """Test list operations."""

    def test_list_active_sessions(self, store, test_user_id):
        """Test listing active sessions."""
        # Create multiple sessions
        active1 = PromptSession.create_new(metadata={"user_id": test_user_id})
        active2 = PromptSession.create_new(metadata={"user_id": test_user_id})
        finalized = PromptSession.create_new(metadata={"user_id": test_user_id})
        finalized.finalize()

        store.create(active1)
        store.create(active2)
        store.create(finalized)

        # List active sessions
        active_sessions = store.list_active()

        assert len(active_sessions) == 2
        session_ids = {s.session_id for s in active_sessions}
        assert active1.session_id in session_ids
        assert active2.session_id in session_ids
        assert finalized.session_id not in session_ids

    def test_list_all_sessions(self, store, test_user_id):
        """Test listing all sessions regardless of status."""
        # Create multiple sessions with different statuses
        active = PromptSession.create_new(metadata={"user_id": test_user_id})
        finalized = PromptSession.create_new(metadata={"user_id": test_user_id})
        finalized.finalize()
        abandoned = PromptSession.create_new(metadata={"user_id": test_user_id})
        abandoned.abandon()

        store.create(active)
        store.create(finalized)
        store.create(abandoned)

        # List all sessions
        all_sessions = store.list_all()

        assert len(all_sessions) == 3
        statuses = {s.status for s in all_sessions}
        assert statuses == {"active", "finalized", "abandoned"}

    def test_list_sessions_without_user_id_raises_error(self):
        """Test that listing sessions without user_id raises ValueError."""
        store_no_user = SupabaseSessionStore()
        with pytest.raises(ValueError, match="user_id must be set"):
            store_no_user.list_active()


class TestSupabaseSessionStoreRevisionTracking:
    """Test revision tracking functionality."""

    def test_multiple_revisions(self, store, sample_session):
        """Test storing and retrieving multiple revisions."""
        # Add more revisions
        for i in range(3):
            revision = PromptRevision(
                timestamp=datetime.now(UTC).isoformat() + "Z",
                content=f"Revision {i + 2}",
                revision_type="hole_fill",
            )
            sample_session.add_revision(revision)

        store.create(sample_session)

        # Retrieve and verify
        retrieved = store.get(sample_session.session_id)
        assert len(retrieved.revisions) == 4  # 1 initial + 3 added
        assert retrieved.revisions[0].revision_type == "initial"
        assert retrieved.revisions[-1].content == "Revision 3"

    def test_revision_ordering(self, store, sample_session):
        """Test that revisions are returned in correct order."""
        timestamps = []
        for i in range(5):
            revision = PromptRevision(
                timestamp=datetime.now(UTC).isoformat() + "Z",
                content=f"Step {i + 2}",
                revision_type="hole_fill",
            )
            timestamps.append(revision.timestamp)
            sample_session.add_revision(revision)

        store.create(sample_session)

        retrieved = store.get(sample_session.session_id)
        retrieved_contents = [r.content for r in retrieved.revisions]

        # Should be in order from earliest to latest
        expected_order = ["Create a function to calculate fibonacci numbers"] + [
            f"Step {i}" for i in range(2, 7)
        ]
        assert retrieved_contents == expected_order


class TestSupabaseSessionStoreDraftTracking:
    """Test IR draft tracking functionality."""

    def test_multiple_drafts(self, store, sample_session):
        """Test storing and retrieving multiple IR drafts."""
        # Add more drafts
        for i in range(3):
            ir = IntermediateRepresentation(
                function_name=f"fibonacci_v{i + 2}",
                parameters=[{"name": "n", "type": "int"}],
                return_type="int",
                preconditions=["n >= 0"],
                postconditions=[],
                effects=[],
            )
            draft = IRDraft(version=i + 2, ir=ir, validation_status="valid")
            sample_session.add_draft(draft)

        store.create(sample_session)

        # Retrieve and verify
        retrieved = store.get(sample_session.session_id)
        assert len(retrieved.ir_drafts) == 4  # 1 initial + 3 added
        assert retrieved.current_draft.version == 4
        assert retrieved.current_draft.ir.function_name == "fibonacci_v4"

    def test_draft_validation_status(self, store):
        """Test storing drafts with different validation statuses."""
        session = PromptSession.create_new()

        statuses = ["pending", "valid", "contradictory", "incomplete"]
        for i, status in enumerate(statuses):
            ir = IntermediateRepresentation(
                function_name=f"test_func_{i}",
                parameters=[],
                return_type="void",
                preconditions=[],
                postconditions=[],
                effects=[],
            )
            draft = IRDraft(version=i + 1, ir=ir, validation_status=status)
            session.add_draft(draft)

        store.create(session)

        retrieved = store.get(session.session_id)
        retrieved_statuses = [d.validation_status for d in retrieved.ir_drafts]
        assert retrieved_statuses == statuses


class TestSupabaseSessionStoreHoleResolutions:
    """Test hole resolution tracking functionality."""

    def test_multiple_resolutions(self, store, sample_session):
        """Test storing and retrieving multiple hole resolutions."""
        # Add more resolutions
        resolution_types = [
            "add_constraint",
            "refine_signature",
            "specify_effect",
        ]
        for i, res_type in enumerate(resolution_types):
            resolution = HoleResolution(
                hole_id=f"hole_{i + 2}",
                resolution_text=f"Resolution for hole {i + 2}",
                resolution_type=res_type,
            )
            sample_session.add_resolution(resolution)

        store.create(sample_session)

        # Retrieve and verify
        retrieved = store.get(sample_session.session_id)
        assert len(retrieved.pending_resolutions) == 4  # 1 initial + 3 added

    def test_resolution_applied_status(self, store, sample_session):
        """Test storing applied resolution status."""
        # Mark resolution as applied
        sample_session.mark_resolution_applied("hole_1")

        store.create(sample_session)

        retrieved = store.get(sample_session.session_id)
        assert retrieved.pending_resolutions[0].applied is True


class TestSupabaseSessionStoreDataIntegrity:
    """Test data integrity and edge cases."""

    def test_empty_session(self, store):
        """Test creating a session with no revisions/drafts/resolutions."""
        session = PromptSession.create_new()
        store.create(session)

        retrieved = store.get(session.session_id)
        assert retrieved is not None
        assert len(retrieved.revisions) == 0
        assert len(retrieved.ir_drafts) == 0
        assert len(retrieved.pending_resolutions) == 0

    def test_metadata_preservation(self, store):
        """Test that metadata is preserved correctly."""
        metadata = {
            "custom_field": "value",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }
        session = PromptSession.create_new(metadata=metadata)
        store.create(session)

        retrieved = store.get(session.session_id)
        assert retrieved.metadata == metadata

    def test_timestamp_preservation(self, store, sample_session):
        """Test that timestamps are preserved correctly."""
        original_created = sample_session.created_at
        original_updated = sample_session.updated_at

        store.create(sample_session)

        retrieved = store.get(sample_session.session_id)
        assert retrieved.created_at == original_created
        assert retrieved.updated_at == original_updated

    def test_concurrent_sessions_different_users(self):
        """Test that different users can create sessions independently."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        store1 = SupabaseSessionStore(user_id=user1_id)
        store2 = SupabaseSessionStore(user_id=user2_id)

        session1 = PromptSession.create_new(metadata={"user": "user1"})
        session2 = PromptSession.create_new(metadata={"user": "user2"})

        store1.create(session1)
        store2.create(session2)

        # Each user should only see their own sessions
        user1_sessions = store1.list_all()
        user2_sessions = store2.list_all()

        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1
        assert user1_sessions[0].session_id == session1.session_id
        assert user2_sessions[0].session_id == session2.session_id


class TestSupabaseSessionStoreErrorHandling:
    """Test error handling and edge cases."""

    def test_create_without_user_id_raises_error(self):
        """Test that creating a session without user_id raises ValueError."""
        store_no_user = SupabaseSessionStore()
        session = PromptSession.create_new()

        with pytest.raises(ValueError, match="user_id must be set"):
            store_no_user.create(session)

    def test_missing_credentials_raises_error(self, monkeypatch):
        """Test that missing credentials raises ValueError."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

        with pytest.raises(ValueError, match="must be provided"):
            SupabaseSessionStore()


@pytest.mark.integration
class TestSupabaseSessionStoreIntegration:
    """Integration tests for full workflows."""

    def test_full_session_lifecycle(self, store, test_user_id):
        """Test a complete session lifecycle from creation to finalization."""
        # Create new session
        session = PromptSession.create_new(
            source="prompt",
            metadata={"user_id": test_user_id, "test": "full_lifecycle"},
        )

        # Add initial revision
        rev1 = PromptRevision(
            timestamp=datetime.now(UTC).isoformat() + "Z",
            content="Build a REST API for user management",
            revision_type="initial",
        )
        session.add_revision(rev1)

        # Add initial draft
        ir1 = IntermediateRepresentation(
            function_name="create_user",
            parameters=[{"name": "user_data", "type": "dict"}],
            return_type="User",
            preconditions=["user_data is valid"],
            postconditions=["user exists in database"],
            effects=["database.insert(user)"],
        )
        draft1 = IRDraft(version=1, ir=ir1, validation_status="incomplete")
        session.add_draft(draft1)

        # Create in database
        store.create(session)

        # Add refinement revision
        rev2 = PromptRevision(
            timestamp=datetime.now(UTC).isoformat() + "Z",
            content="Add email validation",
            revision_type="hole_fill",
            target_hole="validation_hole",
        )
        session.add_revision(rev2)

        # Add refined draft
        ir2 = IntermediateRepresentation(
            function_name="create_user",
            parameters=[{"name": "user_data", "type": "dict"}],
            return_type="User",
            preconditions=[
                "user_data is valid",
                "email matches regex pattern",
            ],
            postconditions=["user exists in database"],
            effects=["validate_email(user_data.email)", "database.insert(user)"],
        )
        draft2 = IRDraft(version=2, ir=ir2, validation_status="valid")
        session.add_draft(draft2)

        # Add resolution
        resolution = HoleResolution(
            hole_id="validation_hole",
            resolution_text="Use RFC 5322 email regex",
            resolution_type="add_constraint",
        )
        session.add_resolution(resolution)

        # Update in database
        store.update(session)

        # Finalize session
        session.finalize()
        store.update(session)

        # Verify final state
        retrieved = store.get(session.session_id)
        assert retrieved.status == "finalized"
        assert len(retrieved.revisions) == 2
        assert len(retrieved.ir_drafts) == 2
        assert len(retrieved.pending_resolutions) == 1
        assert retrieved.current_draft.version == 2
        assert retrieved.current_draft.validation_status == "valid"

        # Clean up
        store.delete(session.session_id)
