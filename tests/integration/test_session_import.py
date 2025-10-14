"""Integration tests for reverse IR session import.

Tests cover:
- POST /api/spec-sessions/import-from-reverse endpoint
- Session creation with improvement detection
- Integration with ImprovementDetector
- Metadata preservation
- Error handling
"""

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


@pytest.fixture
def reverse_ir_with_evidence():
    """Create a reverse-extracted IR with CodeQL evidence."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Get user from database"),
        signature=SigClause(
            name="get_user",
            parameters=[Parameter(name="username", type_hint="str")],
            returns="dict",
        ),
        effects=[
            EffectClause(description="Executes SQL query"),
        ],
        assertions=[
            AssertClause(predicate="len(username) > 0"),
        ],
        metadata=Metadata(
            source_path="src/db.py",
            language="python",
            origin="reverse",
            evidence=[
                {
                    "id": "codeql-sql-injection-42",
                    "analysis": "codeql",
                    "category": "security",
                    "message": "SQL injection vulnerability detected",
                    "location": "get_user:5",
                    "metadata": {
                        "severity": "critical",
                        "rule_id": "py/sql-injection",
                        "description": "User input directly interpolated into SQL query",
                    },
                },
                {
                    "id": "daikon-inv-1",
                    "analysis": "daikon",
                    "category": "invariant",
                    "predicate": "username != null",
                    "confidence": 0.95,
                },
            ],
        ),
    )


@pytest.fixture
def reverse_ir_minimal():
    """Create a minimal reverse-extracted IR without evidence."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Add two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[],
        assertions=[],
        metadata=Metadata(
            source_path="src/math.py",
            language="python",
            origin="reverse",
        ),
    )


@pytest.mark.integration
class TestSessionImportEndpoint:
    """Tests for the session import endpoint."""

    def test_import_reverse_ir_with_improvement_detection(
        self, configured_api_client, reverse_ir_with_evidence
    ):
        """Test importing a reverse IR with improvement detection enabled."""
        ir_dict = reverse_ir_with_evidence.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": True,
                "metadata": {"source": "test"},
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check session structure
        assert "session_id" in data
        assert data["status"] == "active"
        assert data["source"] == "reverse_mode"
        assert "created_at" in data
        assert "updated_at" in data
        assert data["revision_count"] == 0  # No revisions yet

        # Check that improvements were detected
        assert "ambiguities" in data
        # Should have at least 1 security hole from the critical CodeQL finding
        assert len(data["ambiguities"]) > 0

        # Check metadata preservation
        assert "metadata" in data
        assert data["metadata"]["improvement_detection_enabled"] is True

        # Check current draft
        assert "current_draft" in data
        assert data["current_draft"] is not None
        draft = data["current_draft"]
        assert draft["version"] == 1
        assert draft["validation_status"] == "incomplete"  # Has improvement holes
        assert "reverse_analysis" in draft["metadata"]
        assert draft["metadata"]["reverse_analysis"]["source_file"] == "src/db.py"
        assert draft["metadata"]["reverse_analysis"]["evidence_count"] == 2
        assert "improvements_detected" in draft["metadata"]
        assert draft["metadata"]["improvements_detected"]["total"] > 0

    def test_import_reverse_ir_without_improvement_detection(
        self, configured_api_client, reverse_ir_with_evidence
    ):
        """Test importing a reverse IR with improvement detection disabled."""
        ir_dict = reverse_ir_with_evidence.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "active"
        assert data["source"] == "reverse_mode"

        # Check that no improvements were detected
        assert "ambiguities" in data
        assert len(data["ambiguities"]) == 0

        # Check current draft
        draft = data["current_draft"]
        assert draft["validation_status"] == "pending"  # No holes
        assert draft["metadata"]["improvements_detected"]["total"] == 0

    def test_import_minimal_reverse_ir(self, configured_api_client, reverse_ir_minimal):
        """Test importing a minimal reverse IR without evidence."""
        ir_dict = reverse_ir_minimal.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "active"
        assert data["source"] == "reverse_mode"

        # With no evidence, improvement detection should find fewer issues
        draft = data["current_draft"]
        assert "improvements_detected" in draft["metadata"]

    def test_import_reverse_ir_with_custom_metadata(
        self, configured_api_client, reverse_ir_minimal
    ):
        """Test importing with custom metadata."""
        ir_dict = reverse_ir_minimal.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": False,
                "metadata": {
                    "project": "test-project",
                    "version": "1.0.0",
                    "custom_field": "custom_value",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check that custom metadata was preserved
        assert data["metadata"]["project"] == "test-project"
        assert data["metadata"]["version"] == "1.0.0"
        assert data["metadata"]["custom_field"] == "custom_value"

    def test_import_reverse_ir_invalid_ir(self, configured_api_client):
        """Test importing with invalid IR data."""
        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": {
                    "invalid": "structure",
                },
                "detect_improvements": True,
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to import reverse IR" in data["detail"]

    def test_import_reverse_ir_missing_ir_field(self, configured_api_client):
        """Test importing without providing IR field."""
        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "detect_improvements": True,
            },
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_import_creates_session_in_manager(
        self, configured_api_client, reverse_ir_minimal, api_state
    ):
        """Test that importing creates a session in the session manager."""
        ir_dict = reverse_ir_minimal.to_dict()

        # Get initial session count
        initial_sessions = api_state.session_manager.list_active_sessions()
        initial_count = len(initial_sessions)

        # Import IR
        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": False,
            },
        )

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Verify session was created
        sessions = api_state.session_manager.list_active_sessions()
        assert len(sessions) == initial_count + 1

        # Verify we can retrieve the session
        session = api_state.session_manager.get_session(session_id)
        assert session is not None
        assert session.source == "reverse_mode"
        assert session.status == "active"

    def test_import_preserves_original_evidence(
        self, configured_api_client, reverse_ir_with_evidence
    ):
        """Test that original evidence is preserved in draft metadata."""
        ir_dict = reverse_ir_with_evidence.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": True,
            },
        )

        assert response.status_code == 200
        draft = response.json()["current_draft"]

        # Check that original evidence was preserved
        assert "original_evidence" in draft["metadata"]
        evidence = draft["metadata"]["original_evidence"]
        assert len(evidence) == 2
        assert evidence[0]["id"] == "codeql-sql-injection-42"
        assert evidence[1]["id"] == "daikon-inv-1"

    def test_import_security_finding_creates_security_hole(
        self, configured_api_client, reverse_ir_with_evidence, api_state
    ):
        """Test that security findings are promoted to improvement holes."""
        ir_dict = reverse_ir_with_evidence.to_dict()

        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
                "detect_improvements": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Get the session to inspect holes
        session_id = data["session_id"]
        session = api_state.session_manager.get_session(session_id)

        # Check that security holes were created
        assert session.current_draft is not None
        ir = session.current_draft.ir
        holes = ir.typed_holes()

        # Should have at least one security-related hole
        security_holes = [
            h
            for h in holes
            if h.constraints and h.constraints.get("severity") in ["critical", "high"]
        ]
        assert len(security_holes) > 0

        # Specifically check for the critical SQL injection finding
        critical_holes = [
            h for h in holes if h.constraints and h.constraints.get("severity") == "critical"
        ]
        assert len(critical_holes) == 1
        assert "SQL injection" in critical_holes[0].description

    def test_import_default_improvement_detection(
        self, configured_api_client, reverse_ir_with_evidence
    ):
        """Test that improvement detection is enabled by default."""
        ir_dict = reverse_ir_with_evidence.to_dict()

        # Don't specify detect_improvements - should default to True
        response = configured_api_client.post(
            "/api/spec-sessions/import-from-reverse",
            json={
                "ir": ir_dict,
            },
        )

        assert response.status_code == 200
        draft = response.json()["current_draft"]

        # Should have detected improvements by default
        assert draft["metadata"]["improvements_detected"]["total"] > 0


@pytest.mark.integration
class TestSessionManagerEnhancedImport:
    """Tests for SpecSessionManager.create_from_reverse_mode_enhanced()."""

    def test_inject_improvement_holes_by_kind(
        self, configured_api_client, reverse_ir_minimal, api_state
    ):
        """Test that holes are injected into correct IR sections by kind."""

        # Create improvement holes of different kinds
        holes = [
            TypedHole(
                identifier="intent_clarification",
                type_hint="IntentRefinement",
                description="Clarify the intent",
                kind=HoleKind.INTENT,
            ),
            TypedHole(
                identifier="missing_param_type",
                type_hint="TypeAnnotation",
                description="Add type annotation",
                kind=HoleKind.SIGNATURE,
            ),
            TypedHole(
                identifier="missing_assertion",
                type_hint="Constraint",
                description="Add constraint",
                kind=HoleKind.ASSERTION,
            ),
            TypedHole(
                identifier="missing_effect",
                type_hint="SideEffect",
                description="Document effect",
                kind=HoleKind.EFFECT,
            ),
        ]

        # Create session with these holes
        session = api_state.session_manager.create_from_reverse_mode_enhanced(
            ir=reverse_ir_minimal,
            improvement_holes=holes,
            metadata={"test": "inject_holes"},
        )

        # Verify holes were injected
        assert session.current_draft is not None
        ir = session.current_draft.ir

        # Check intent holes
        assert len(ir.intent.holes) == 1
        assert ir.intent.holes[0].identifier == "intent_clarification"

        # Check signature holes
        assert len(ir.signature.holes) == 1
        assert ir.signature.holes[0].identifier == "missing_param_type"

        # Check assertion holes (should be in the holes field of assertion clauses)
        # The test IR has no assertions, so a new assertion clause should be created
        assert len(ir.assertions) >= 1
        # Check all assertion clauses for holes
        all_assertion_holes = []
        for assertion in ir.assertions:
            all_assertion_holes.extend(assertion.holes)
        assert len(all_assertion_holes) == 1
        assert all_assertion_holes[0].identifier == "missing_assertion"

        # Check effect holes (should be in the holes field of effect clauses)
        # The test IR has no effects, so a new effect clause should be created
        assert len(ir.effects) >= 1
        # Check all effect clauses for holes
        all_effect_holes = []
        for effect in ir.effects:
            all_effect_holes.extend(effect.holes)
        assert len(all_effect_holes) == 1
        assert all_effect_holes[0].identifier == "missing_effect"

    def test_count_by_priority(self, configured_api_client, api_state):
        """Test that holes are counted by priority."""
        from lift_sys.ir.models import IntentClause, SigClause

        holes = [
            TypedHole(
                identifier="h1",
                type_hint="T1",
                description="High priority",
                kind=HoleKind.INTENT,
                constraints={"priority": "critical"},
            ),
            TypedHole(
                identifier="h2",
                type_hint="T2",
                description="High priority",
                kind=HoleKind.INTENT,
                constraints={"priority": "high"},
            ),
            TypedHole(
                identifier="h3",
                type_hint="T3",
                description="Medium priority",
                kind=HoleKind.INTENT,
                constraints={"priority": "medium"},
            ),
        ]

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        session = api_state.session_manager.create_from_reverse_mode_enhanced(
            ir=ir,
            improvement_holes=holes,
        )

        # Check metadata
        draft_metadata = session.current_draft.metadata
        by_priority = draft_metadata["improvements_detected"]["by_priority"]
        assert by_priority["critical"] == 1
        assert by_priority["high"] == 1
        assert by_priority["medium"] == 1

    def test_count_by_kind(self, configured_api_client, api_state):
        """Test that holes are counted by kind."""
        from lift_sys.ir.models import IntentClause, SigClause

        holes = [
            TypedHole(
                identifier="h1",
                type_hint="T1",
                description="Intent hole",
                kind=HoleKind.INTENT,
            ),
            TypedHole(
                identifier="h2",
                type_hint="T2",
                description="Signature hole",
                kind=HoleKind.SIGNATURE,
            ),
            TypedHole(
                identifier="h3",
                type_hint="T3",
                description="Assertion hole",
                kind=HoleKind.ASSERTION,
            ),
        ]

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        session = api_state.session_manager.create_from_reverse_mode_enhanced(
            ir=ir,
            improvement_holes=holes,
        )

        # Check metadata
        draft_metadata = session.current_draft.metadata
        by_kind = draft_metadata["improvements_detected"]["by_kind"]
        assert by_kind["intent"] == 1
        assert by_kind["signature"] == 1
        assert by_kind["assertion"] == 1
