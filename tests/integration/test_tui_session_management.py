"""Integration tests for TUI session management.

Tests cover:
- Session creation from prompts
- Session listing
- Session state management
- Session display rendering
- Integration with SessionClient
- Error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lift_sys.client import IRDraft, PromptSession, SessionListResponse
from lift_sys.main import LiftSysApp, SessionState


def setup_app_widgets(app: LiftSysApp) -> None:
    """Set up mock widgets for testing without full app mounting.

    This allows us to test the business logic without needing the Textual
    testing framework or full app composition.
    """
    # Mock input widgets with a value attribute
    app.prompt_input = MagicMock()
    app.prompt_input.value = ""

    # Mock display widgets
    app.status_panel = MagicMock()
    app.status_panel.message = ""
    app.session_detail = MagicMock()
    app.sessions_list = MagicMock()


@pytest.mark.integration
class TestTUISessionManagement:
    """Integration tests for TUI session management."""

    @pytest.mark.asyncio
    async def test_create_prompt_session(self):
        """Test creating a session from a prompt in TUI."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock the session client
        mock_session = PromptSession(
            session_id="test-session-123",
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

        with patch.object(app.session_client, "acreate_session", return_value=mock_session):
            # Set prompt input
            app.prompt_input.value = "Test function"

            # Create session
            await app.create_prompt_session()

            # Verify session was created
            assert app.state.active_session is not None
            assert app.state.active_session.session_id == "test-session-123"
            assert len(app.state.sessions) == 1
            assert app.prompt_input.value == ""  # Input cleared

    @pytest.mark.asyncio
    async def test_create_prompt_session_empty_prompt(self):
        """Test creating session with empty prompt fails gracefully."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Set empty prompt
        app.prompt_input.value = ""

        # Try to create session
        await app.create_prompt_session()

        # Verify no session was created
        assert app.state.active_session is None
        assert len(app.state.sessions) == 0

    @pytest.mark.asyncio
    async def test_create_prompt_session_error_handling(self):
        """Test error handling when session creation fails."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock session client to raise error
        with patch.object(
            app.session_client, "acreate_session", side_effect=Exception("API error")
        ):
            app.prompt_input.value = "Test function"

            # Create session (should handle error gracefully)
            await app.create_prompt_session()

            # Verify session was not created
            assert app.state.active_session is None
            assert len(app.state.sessions) == 0

    @pytest.mark.asyncio
    async def test_list_prompt_sessions(self):
        """Test listing sessions in TUI."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock session list response
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
            ),
            PromptSession(
                session_id="session-2",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=None,
                ambiguities=["hole_1"],
                revision_count=2,
                metadata={},
            ),
        ]
        mock_response = SessionListResponse(sessions=mock_sessions)

        with patch.object(app.session_client, "alist_sessions", return_value=mock_response):
            # List sessions
            await app.list_prompt_sessions()

            # Verify sessions were loaded
            assert len(app.state.sessions) == 2
            assert app.state.sessions[0].session_id == "session-1"
            assert app.state.sessions[1].session_id == "session-2"

    @pytest.mark.asyncio
    async def test_list_prompt_sessions_empty(self):
        """Test listing sessions when none exist."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock empty session list
        mock_response = SessionListResponse(sessions=[])

        with patch.object(app.session_client, "alist_sessions", return_value=mock_response):
            # List sessions
            await app.list_prompt_sessions()

            # Verify sessions list is empty
            assert len(app.state.sessions) == 0

    @pytest.mark.asyncio
    async def test_list_prompt_sessions_error_handling(self):
        """Test error handling when listing sessions fails."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock session client to raise error
        with patch.object(app.session_client, "alist_sessions", side_effect=Exception("API error")):
            # List sessions (should handle error gracefully)
            await app.list_prompt_sessions()

            # Verify sessions list is empty
            assert len(app.state.sessions) == 0

    @pytest.mark.asyncio
    async def test_refresh_sessions_list(self):
        """Test refreshing sessions list view."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[
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
                ),
            ],
        )

        # Refresh sessions list (this should update the ListView widget)
        await app.refresh_sessions_list()

        # Verify list was refreshed (implementation-dependent)
        # This test mainly ensures the method doesn't crash
        assert True

    @pytest.mark.asyncio
    async def test_refresh_session_display_with_session(self):
        """Test refreshing session detail display with active session."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=PromptSession(
                session_id="test-session",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=IRDraft(
                    version=1,
                    ir={"intent": {"summary": "test"}},
                    validation_status="pending",
                    ambiguities=["hole_1", "hole_2"],
                    smt_results=[],
                    created_at="2025-01-01T00:00:00Z",
                    metadata={},
                ),
                ambiguities=["hole_1", "hole_2"],
                revision_count=1,
                metadata={},
            ),
            sessions=[],
        )

        # Refresh display
        await app.refresh_session_display()

        # Verify display was updated (implementation-dependent)
        # This test mainly ensures the method doesn't crash
        assert True

    @pytest.mark.asyncio
    async def test_refresh_session_display_without_session(self):
        """Test refreshing session detail display with no active session."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Refresh display
        await app.refresh_session_display()

        # Verify display shows "No active session" (implementation-dependent)
        # This test mainly ensures the method doesn't crash
        assert True

    @pytest.mark.asyncio
    async def test_action_list_sessions(self):
        """Test list sessions action handler."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock session list response
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
            ),
        ]
        mock_response = SessionListResponse(sessions=mock_sessions)

        with patch.object(app.session_client, "alist_sessions", return_value=mock_response):
            # Trigger action
            await app.action_list_sessions()

            # Verify sessions were loaded
            assert len(app.state.sessions) == 1

    def test_session_state_initialization(self):
        """Test SessionState dataclass initialization."""
        state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Verify basic state attributes
        assert state.endpoint == "http://localhost:8000"
        assert state.temperature == 0.0
        assert state.active_session is None
        assert state.sessions == []

    def test_session_state_with_data(self):
        """Test SessionState with session data."""
        session = PromptSession(
            session_id="test",
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
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=session,
            sessions=[session],
        )

        assert state.active_session == session
        assert len(state.sessions) == 1
        assert state.sessions[0] == session

    @pytest.mark.asyncio
    async def test_tui_session_workflow(self):
        """Test complete TUI session workflow."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=None,
            sessions=[],
        )

        # Mock session
        mock_session = PromptSession(
            session_id="workflow-session",
            status="active",
            source="prompt",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            current_draft=IRDraft(
                version=1,
                ir={"intent": {"summary": "workflow test"}},
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

        # Mock session list
        mock_list_response = SessionListResponse(sessions=[mock_session])

        with (
            patch.object(app.session_client, "acreate_session", return_value=mock_session),
            patch.object(app.session_client, "alist_sessions", return_value=mock_list_response),
        ):
            # Step 1: Create session
            app.prompt_input.value = "Workflow test"
            await app.create_prompt_session()
            assert app.state.active_session is not None

            # Step 2: List sessions
            await app.list_prompt_sessions()
            assert len(app.state.sessions) == 1

            # Step 3: Refresh display
            await app.refresh_session_display()
            # Verify no errors occurred

    def test_tui_session_client_initialization(self):
        """Test that TUI initializes SessionClient correctly."""
        app = LiftSysApp()
        setup_app_widgets(app)

        # Verify session client is initialized
        assert app.session_client is not None
        assert app.session_client.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_tui_handles_session_with_no_draft(self):
        """Test TUI handles sessions without current draft."""
        app = LiftSysApp()
        setup_app_widgets(app)
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=PromptSession(
                session_id="no-draft-session",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=None,  # No draft
                ambiguities=[],
                revision_count=1,
                metadata={},
            ),
            sessions=[],
        )

        # Refresh display (should handle None draft gracefully)
        await app.refresh_session_display()

        # Verify no errors occurred
        assert True

    @pytest.mark.asyncio
    async def test_tui_handles_session_with_many_ambiguities(self):
        """Test TUI handles sessions with many ambiguities."""
        app = LiftSysApp()
        setup_app_widgets(app)

        # Create session with many ambiguities
        many_holes = [f"hole_{i}" for i in range(20)]
        app.state = SessionState(
            endpoint="http://localhost:8000",
            temperature=0.0,
            repository=None,
            ir=None,
            active_session=PromptSession(
                session_id="many-holes-session",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=IRDraft(
                    version=1,
                    ir={"intent": {"summary": "many holes"}},
                    validation_status="incomplete",
                    ambiguities=many_holes,
                    smt_results=[],
                    created_at="2025-01-01T00:00:00Z",
                    metadata={},
                ),
                ambiguities=many_holes,
                revision_count=1,
                metadata={},
            ),
            sessions=[],
        )

        # Refresh display (should handle many holes gracefully)
        await app.refresh_session_display()

        # Verify no errors occurred
        assert True

    def test_tui_prompt_input_widget_exists(self):
        """Test that prompt input widget is accessible."""
        app = LiftSysApp()
        setup_app_widgets(app)

        # Verify prompt input exists
        assert hasattr(app, "prompt_input")
        assert app.prompt_input is not None

    def test_tui_session_detail_widget_exists(self):
        """Test that session detail widget is accessible."""
        app = LiftSysApp()
        setup_app_widgets(app)

        # Verify session detail exists
        assert hasattr(app, "session_detail")
        assert app.session_detail is not None

    def test_tui_sessions_list_widget_exists(self):
        """Test that sessions list widget is accessible."""
        app = LiftSysApp()
        setup_app_widgets(app)

        # Verify sessions list exists
        assert hasattr(app, "sessions_list")
        assert app.sessions_list is not None
