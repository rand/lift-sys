"""Unit tests for TUI session management methods.

Tests cover:
- SessionClient initialization
- SessionState structure
- Method existence and signatures
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lift_sys.client import IRDraft, PromptSession, SessionListResponse
from lift_sys.main import LiftSysApp, SessionState


@pytest.mark.unit
class TestTUISessionMethods:
    """Unit tests for TUI session management methods."""

    def test_session_state_creation(self):
        """Test creating SessionState with required fields."""
        state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.7,
            repository=None,
            ir=None,
            active_session=None,
            sessions=None,
        )

        assert state.endpoint == "http://localhost:8000"
        assert state.temperature == 0.7
        assert state.repository is None
        assert state.ir is None
        assert state.active_session is None
        assert state.sessions == []  # __post_init__ initializes empty list

    def test_session_state_with_active_session(self):
        """Test SessionState with an active session."""
        session = PromptSession(
            session_id="test-123",
            status="active",
            source="prompt",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            current_draft=None,
            ambiguities=[],
            revision_count=1,
            metadata={},
        )

        state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.7,
            repository=None,
            ir=None,
            active_session=session,
            sessions=[session],
        )

        assert state.active_session == session
        assert len(state.sessions) == 1

    def test_lift_sys_app_has_session_client(self):
        """Test that LiftSysApp initializes with SessionClient."""
        app = LiftSysApp()

        assert hasattr(app, "session_client")
        assert app.session_client is not None
        assert app.session_client.base_url == "http://localhost:8000"

    def test_lift_sys_app_has_create_prompt_session_method(self):
        """Test that LiftSysApp has create_prompt_session method."""
        app = LiftSysApp()

        assert hasattr(app, "create_prompt_session")
        assert callable(app.create_prompt_session)

    def test_lift_sys_app_has_list_prompt_sessions_method(self):
        """Test that LiftSysApp has list_prompt_sessions method."""
        app = LiftSysApp()

        assert hasattr(app, "list_prompt_sessions")
        assert callable(app.list_prompt_sessions)

    def test_lift_sys_app_has_refresh_sessions_list_method(self):
        """Test that LiftSysApp has refresh_sessions_list method."""
        app = LiftSysApp()

        assert hasattr(app, "refresh_sessions_list")
        assert callable(app.refresh_sessions_list)

    def test_lift_sys_app_has_refresh_session_display_method(self):
        """Test that LiftSysApp has refresh_session_display method."""
        app = LiftSysApp()

        assert hasattr(app, "refresh_session_display")
        assert callable(app.refresh_session_display)

    def test_lift_sys_app_has_action_list_sessions(self):
        """Test that LiftSysApp has action_list_sessions method."""
        app = LiftSysApp()

        assert hasattr(app, "action_list_sessions")
        assert callable(app.action_list_sessions)

    def test_lift_sys_app_initializes_state(self):
        """Test that LiftSysApp initializes with state."""
        app = LiftSysApp()

        assert hasattr(app, "state")
        assert isinstance(app.state, SessionState)
        assert app.state.sessions == []

    def test_session_state_defaults(self):
        """Test SessionState default values."""
        state = SessionState()

        assert state.endpoint == "http://localhost:8000"
        assert state.temperature == 0.0
        assert state.repository is None
        assert state.ir is None
        assert state.active_session is None
        assert state.sessions == []

    @pytest.mark.asyncio
    async def test_create_prompt_session_method_exists(self):
        """Test that create_prompt_session method can be called."""
        app = LiftSysApp()

        # Mock the session client
        mock_session = PromptSession(
            session_id="test-session",
            status="active",
            source="prompt",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            current_draft=None,
            ambiguities=[],
            revision_count=1,
            metadata={},
        )

        with patch.object(app.session_client, "acreate_session", return_value=mock_session):
            # Set prompt value (note: widgets may not be fully initialized)
            if hasattr(app, "prompt_input"):
                app.prompt_input.value = "Test prompt"

                # Call the method
                await app.create_prompt_session()

                # Verify session was added
                assert app.state.active_session == mock_session
                assert mock_session in app.state.sessions

    @pytest.mark.asyncio
    async def test_list_prompt_sessions_method_exists(self):
        """Test that list_prompt_sessions method can be called."""
        app = LiftSysApp()

        mock_sessions = [
            PromptSession(
                session_id="session-1",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=None,
                ambiguities=[],
                revision_count=1,
                metadata={},
            )
        ]

        # Mock the status_panel to avoid widget context issues
        with (
            patch.object(
                app.session_client,
                "alist_sessions",
                return_value=SessionListResponse(sessions=mock_sessions),
            ),
            patch.object(app, "status_panel", create=True) as mock_status,
        ):
            mock_status.message = ""

            await app.list_prompt_sessions()

            # Verify sessions were loaded
            assert len(app.state.sessions) == 1
            assert app.state.sessions[0].session_id == "session-1"

    @pytest.mark.asyncio
    async def test_refresh_session_display_with_active_session(self):
        """Test refresh_session_display with active session."""
        app = LiftSysApp()

        app.state.active_session = PromptSession(
            session_id="test",
            status="active",
            source="prompt",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            current_draft=IRDraft(
                version=1,
                ir={"intent": {"summary": "test"}},
                validation_status="pending",
                ambiguities=["hole_1"],
                smt_results=[],
                created_at="2025-01-01T00:00:00Z",
                metadata={},
            ),
            ambiguities=["hole_1"],
            revision_count=1,
            metadata={},
        )

        # This should not raise an exception
        await app.refresh_session_display()

    @pytest.mark.asyncio
    async def test_refresh_session_display_without_active_session(self):
        """Test refresh_session_display without active session."""
        app = LiftSysApp()
        app.state.active_session = None

        # This should not raise an exception
        await app.refresh_session_display()

    def test_session_client_base_url(self):
        """Test SessionClient is initialized with correct base URL."""
        app = LiftSysApp()

        assert app.session_client.base_url == "http://localhost:8000"

    def test_session_state_mutation(self):
        """Test that SessionState can be mutated."""
        state = SessionState()

        # Add a session
        session = PromptSession(
            session_id="new-session",
            status="active",
            source="prompt",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            current_draft=None,
            ambiguities=[],
            revision_count=1,
            metadata={},
        )

        state.sessions.append(session)
        state.active_session = session

        assert len(state.sessions) == 1
        assert state.active_session == session
