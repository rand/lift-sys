"""Unit tests for prompt session models."""
from __future__ import annotations

from datetime import datetime

import pytest

from lift_sys.ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
    TypedHole,
)
from lift_sys.spec_sessions.models import (
    HoleResolution,
    IRDraft,
    PromptRevision,
    PromptSession,
)


@pytest.mark.unit
class TestPromptRevision:
    """Tests for PromptRevision model."""

    def test_create_revision(self):
        """Test creating a prompt revision."""
        revision = PromptRevision(
            timestamp="2025-01-11T12:00:00Z",
            content="Calculate factorial of n",
            revision_type="initial",
        )

        assert revision.content == "Calculate factorial of n"
        assert revision.revision_type == "initial"
        assert revision.target_hole is None

    def test_revision_serialization(self):
        """Test revision to_dict and from_dict."""
        revision = PromptRevision(
            timestamp="2025-01-11T12:00:00Z",
            content="Add timeout constraint",
            revision_type="hole_fill",
            target_hole="timeout",
            metadata={"confidence": 0.9},
        )

        data = revision.to_dict()
        assert data["content"] == "Add timeout constraint"
        assert data["target_hole"] == "timeout"

        restored = PromptRevision.from_dict(data)
        assert restored.content == revision.content
        assert restored.target_hole == revision.target_hole
        assert restored.metadata == revision.metadata


@pytest.mark.unit
class TestIRDraft:
    """Tests for IRDraft model."""

    def test_create_draft(self):
        """Test creating an IR draft."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test_func",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
        )

        draft = IRDraft(version=1, ir=ir, validation_status="pending")

        assert draft.version == 1
        assert draft.validation_status == "pending"
        assert draft.ir.signature.name == "test_func"

    def test_draft_with_ambiguities(self):
        """Test draft with ambiguities marked."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Process data",
                holes=[
                    TypedHole(
                        identifier="data_format",
                        type_hint="string",
                        description="Expected data format",
                        kind=HoleKind.INTENT,
                    )
                ],
            ),
            signature=SigClause(name="process", parameters=[], returns="void"),
        )

        draft = IRDraft(version=1, ir=ir, validation_status="incomplete", ambiguities=["data_format"])

        assert "data_format" in draft.ambiguities
        assert len(draft.get_unresolved_holes()) == 1

    def test_draft_serialization(self):
        """Test IRDraft to_dict and from_dict."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="void"),
            metadata=Metadata(origin="prompt"),
        )

        draft = IRDraft(
            version=2,
            ir=ir,
            validation_status="valid",
            smt_results=[{"assertion": "x > 0", "status": "sat"}],
            ambiguities=[],
        )

        data = draft.to_dict()
        assert data["version"] == 2
        assert data["validation_status"] == "valid"
        assert len(data["smt_results"]) == 1

        restored = IRDraft.from_dict(data)
        assert restored.version == draft.version
        assert restored.validation_status == draft.validation_status
        assert restored.ir.signature.name == draft.ir.signature.name


@pytest.mark.unit
class TestHoleResolution:
    """Tests for HoleResolution model."""

    def test_create_resolution(self):
        """Test creating a hole resolution."""
        resolution = HoleResolution(
            hole_id="timeout",
            resolution_text="30 seconds",
            resolution_type="add_constraint",
        )

        assert resolution.hole_id == "timeout"
        assert resolution.resolution_text == "30 seconds"
        assert not resolution.applied

    def test_resolution_serialization(self):
        """Test HoleResolution to_dict and from_dict."""
        resolution = HoleResolution(
            hole_id="data_format",
            resolution_text="JSON",
            resolution_type="clarify_intent",
            applied=True,
            timestamp="2025-01-11T12:30:00Z",
        )

        data = resolution.to_dict()
        assert data["hole_id"] == "data_format"
        assert data["applied"] is True

        restored = HoleResolution.from_dict(data)
        assert restored.hole_id == resolution.hole_id
        assert restored.applied == resolution.applied


@pytest.mark.unit
class TestPromptSession:
    """Tests for PromptSession model."""

    def test_create_new_session(self):
        """Test creating a new prompt session."""
        session = PromptSession.create_new(source="prompt")

        assert session.status == "active"
        assert session.source == "prompt"
        assert len(session.revisions) == 0
        assert session.current_draft is None

    def test_create_session_with_initial_draft(self):
        """Test creating session with initial IR draft."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Initial spec"),
            signature=SigClause(name="func", parameters=[], returns="void"),
        )
        draft = IRDraft(version=1, ir=ir, validation_status="pending")

        session = PromptSession.create_new(source="reverse_mode", initial_draft=draft)

        assert session.source == "reverse_mode"
        assert session.current_draft is not None
        assert session.current_draft.version == 1
        assert len(session.ir_drafts) == 1

    def test_add_revision(self):
        """Test adding a revision to a session."""
        session = PromptSession.create_new()
        initial_update_time = session.updated_at

        revision = PromptRevision(
            timestamp="2025-01-11T12:00:00Z",
            content="Calculate factorial",
            revision_type="initial",
        )
        session.add_revision(revision)

        assert len(session.revisions) == 1
        assert session.revisions[0].content == "Calculate factorial"
        assert session.updated_at != initial_update_time

    def test_add_draft(self):
        """Test adding a new draft to a session."""
        session = PromptSession.create_new()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Version 1"),
            signature=SigClause(name="func", parameters=[], returns="void"),
        )
        draft1 = IRDraft(version=1, ir=ir1, validation_status="pending")
        session.add_draft(draft1)

        assert session.current_draft == draft1
        assert len(session.ir_drafts) == 1

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Version 2"),
            signature=SigClause(name="func", parameters=[], returns="void"),
        )
        draft2 = IRDraft(version=2, ir=ir2, validation_status="valid")
        session.add_draft(draft2)

        assert session.current_draft == draft2
        assert len(session.ir_drafts) == 2

    def test_add_and_apply_resolution(self):
        """Test adding and applying hole resolutions."""
        session = PromptSession.create_new()

        resolution = HoleResolution(
            hole_id="timeout",
            resolution_text="30 seconds",
            resolution_type="add_constraint",
        )
        session.add_resolution(resolution)

        assert len(session.pending_resolutions) == 1
        assert not session.pending_resolutions[0].applied

        session.mark_resolution_applied("timeout")

        assert session.pending_resolutions[0].applied

    def test_finalize_session(self):
        """Test finalizing a session."""
        session = PromptSession.create_new()
        assert session.status == "active"

        session.finalize()

        assert session.status == "finalized"

    def test_abandon_session(self):
        """Test abandoning a session."""
        session = PromptSession.create_new()
        session.abandon()

        assert session.status == "abandoned"

    def test_get_unresolved_holes(self):
        """Test getting unresolved holes from current draft."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Process data",
                holes=[
                    TypedHole(
                        identifier="format",
                        type_hint="string",
                        kind=HoleKind.INTENT,
                    )
                ],
            ),
            signature=SigClause(
                name="process",
                parameters=[],
                returns="void",
                holes=[
                    TypedHole(
                        identifier="input_type",
                        type_hint="type",
                        kind=HoleKind.SIGNATURE,
                    )
                ],
            ),
        )
        draft = IRDraft(version=1, ir=ir, validation_status="incomplete")

        session = PromptSession.create_new(initial_draft=draft)
        holes = session.get_unresolved_holes()

        assert len(holes) == 2
        assert "format" in holes
        assert "input_type" in holes

    def test_session_serialization(self):
        """Test PromptSession to_dict and from_dict."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="void"),
        )
        draft = IRDraft(version=1, ir=ir, validation_status="valid")

        session = PromptSession.create_new(initial_draft=draft, metadata={"author": "user1"})
        session.add_revision(
            PromptRevision(
                timestamp="2025-01-11T12:00:00Z",
                content="Initial prompt",
                revision_type="initial",
            )
        )

        data = session.to_dict()
        assert data["status"] == "active"
        assert len(data["revisions"]) == 1
        assert data["metadata"]["author"] == "user1"

        restored = PromptSession.from_dict(data)
        assert restored.session_id == session.session_id
        assert restored.status == session.status
        assert len(restored.revisions) == 1
        assert restored.current_draft is not None
