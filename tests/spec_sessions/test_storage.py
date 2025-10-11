"""Unit tests for session storage backends."""

from __future__ import annotations

import pytest

from lift_sys.ir.models import IntentClause, IntermediateRepresentation, SigClause
from lift_sys.spec_sessions.models import IRDraft, PromptSession
from lift_sys.spec_sessions.storage import InMemorySessionStore


@pytest.mark.unit
class TestInMemorySessionStore:
    """Tests for InMemorySessionStore."""

    def test_create_session(self):
        """Test creating and storing a session."""
        store = InMemorySessionStore()
        session = PromptSession.create_new()

        session_id = store.create(session)

        assert session_id == session.session_id
        retrieved = store.get(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id

    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session returns None."""
        store = InMemorySessionStore()

        result = store.get("nonexistent-id")

        assert result is None

    def test_update_session(self):
        """Test updating an existing session."""
        store = InMemorySessionStore()
        session = PromptSession.create_new()
        store.create(session)

        # Modify session
        session.status = "finalized"
        store.update(session)

        # Retrieve and verify
        retrieved = store.get(session.session_id)
        assert retrieved is not None
        assert retrieved.status == "finalized"

    def test_update_nonexistent_session_raises(self):
        """Test updating non-existent session raises error."""
        store = InMemorySessionStore()
        session = PromptSession.create_new()

        with pytest.raises(KeyError):
            store.update(session)

    def test_list_active_sessions(self):
        """Test listing only active sessions."""
        store = InMemorySessionStore()

        # Create multiple sessions with different statuses
        active1 = PromptSession.create_new()
        active2 = PromptSession.create_new()
        finalized = PromptSession.create_new()
        finalized.finalize()
        abandoned = PromptSession.create_new()
        abandoned.abandon()

        store.create(active1)
        store.create(active2)
        store.create(finalized)
        store.create(abandoned)

        # List active sessions
        active = store.list_active()

        assert len(active) == 2
        active_ids = {s.session_id for s in active}
        assert active1.session_id in active_ids
        assert active2.session_id in active_ids

    def test_list_all_sessions(self):
        """Test listing all sessions regardless of status."""
        store = InMemorySessionStore()

        session1 = PromptSession.create_new()
        session2 = PromptSession.create_new()
        session2.finalize()

        store.create(session1)
        store.create(session2)

        all_sessions = store.list_all()

        assert len(all_sessions) == 2

    def test_delete_session(self):
        """Test deleting a session."""
        store = InMemorySessionStore()
        session = PromptSession.create_new()
        session_id = store.create(session)

        # Verify exists
        assert store.get(session_id) is not None

        # Delete
        store.delete(session_id)

        # Verify deleted
        assert store.get(session_id) is None

    def test_delete_nonexistent_session(self):
        """Test deleting non-existent session (should not raise)."""
        store = InMemorySessionStore()

        # Should not raise
        store.delete("nonexistent-id")

    def test_clear_all_sessions(self):
        """Test clearing all sessions."""
        store = InMemorySessionStore()

        session1 = PromptSession.create_new()
        session2 = PromptSession.create_new()
        store.create(session1)
        store.create(session2)

        assert len(store.list_all()) == 2

        store.clear()

        assert len(store.list_all()) == 0

    def test_store_and_retrieve_complex_session(self):
        """Test storing and retrieving a session with full history."""
        store = InMemorySessionStore()

        # Create complex session
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Complex function"),
            signature=SigClause(name="complex", parameters=[], returns="void"),
        )
        draft = IRDraft(version=1, ir=ir, validation_status="valid")
        session = PromptSession.create_new(initial_draft=draft)

        # Add history
        from lift_sys.spec_sessions.models import HoleResolution, PromptRevision

        session.add_revision(
            PromptRevision(
                timestamp="2025-01-11T12:00:00Z",
                content="Initial prompt",
                revision_type="initial",
            )
        )
        session.add_resolution(
            HoleResolution(
                hole_id="param1",
                resolution_text="integer type",
                resolution_type="refine_signature",
            )
        )

        # Store
        session_id = store.create(session)

        # Retrieve and verify
        retrieved = store.get(session_id)
        assert retrieved is not None
        assert len(retrieved.revisions) == 1
        assert len(retrieved.pending_resolutions) == 1
        assert retrieved.current_draft is not None
        assert retrieved.current_draft.version == 1
