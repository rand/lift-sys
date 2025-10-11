"""Unit tests for CLI session commands.

Tests cover:
- CLI command execution with mocked SessionClient
- Error handling
- Output formatting
- Command structure
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from lift_sys.cli.session_commands import app
from lift_sys.client import (
    AssistsResponse,
    AssistSuggestion,
    IRDraft,
    IRResponse,
    PromptSession,
    SessionListResponse,
)


@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_session():
    """Create mock session."""
    return PromptSession(
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


@pytest.mark.unit
class TestCLICommands:
    """Unit tests for CLI commands."""

    def test_create_session_from_prompt(self, cli_runner, mock_session):
        """Test creating session from prompt."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_session.return_value = mock_session
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "create",
                    "--prompt",
                    "Test function",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "test-session-123" in result.stdout
            assert "active" in result.stdout

    def test_create_session_missing_prompt_and_ir(self, cli_runner):
        """Test creating session without prompt or IR fails."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(app, ["create", "--json"])

            assert result.exit_code == 1
            assert "prompt" in result.stdout.lower() or "ir" in result.stdout.lower()

    def test_list_sessions_empty(self, cli_runner):
        """Test listing sessions when none exist."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_sessions.return_value = SessionListResponse(sessions=[])
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(app, ["list", "--json"])

            assert result.exit_code == 0
            assert "[]" in result.stdout

    def test_list_sessions_with_data(self, cli_runner, mock_session):
        """Test listing sessions with data."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_sessions.return_value = SessionListResponse(sessions=[mock_session])
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(app, ["list", "--json"])

            assert result.exit_code == 0
            assert "test-session-123" in result.stdout

    def test_get_session(self, cli_runner, mock_session):
        """Test getting a specific session."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_session.return_value = mock_session
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "get",
                    "test-session-123",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "test-session-123" in result.stdout

    def test_get_session_not_found(self, cli_runner):
        """Test getting non-existent session."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_session.side_effect = Exception("Session not found")
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "get",
                    "nonexistent",
                    "--json",
                ],
            )

            assert result.exit_code == 1

    def test_resolve_hole(self, cli_runner, mock_session):
        """Test resolving a hole."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            updated_session = PromptSession(
                session_id="test-session-123",
                status="active",
                source="prompt",
                created_at="2025-01-01T00:00:00Z",
                updated_at="2025-01-01T00:00:00Z",
                current_draft=None,
                ambiguities=[],  # Hole resolved
                revision_count=2,
                metadata={},
            )
            mock_client.resolve_hole.return_value = updated_session
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "resolve",
                    "test-session-123",
                    "hole_1",
                    "resolution",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "test-session-123" in result.stdout

    def test_get_assists(self, cli_runner):
        """Test getting assists."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_assists.return_value = AssistsResponse(
                session_id="test-session-123",
                assists=[
                    AssistSuggestion(
                        hole_id="hole_1",
                        suggestions=["int", "str"],
                        context="return type",
                    )
                ],
            )
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "assists",
                    "test-session-123",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "hole_1" in result.stdout

    def test_finalize_session(self, cli_runner):
        """Test finalizing a session."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.finalize_session.return_value = IRResponse(
                ir={"intent": {"summary": "finalized"}}, metadata={}
            )
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "finalize",
                    "test-session-123",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "intent" in result.stdout

    def test_delete_session(self, cli_runner):
        """Test deleting a session."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.delete_session.return_value = None
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "delete",
                    "test-session-123",
                    "--yes",
                ],
            )

            assert result.exit_code == 0
            assert "deleted" in result.stdout.lower()

    def test_rich_output_mode(self, cli_runner, mock_session):
        """Test rich output mode (without --json)."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_session.return_value = mock_session
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "create",
                    "--prompt",
                    "Test function",
                ],
            )

            assert result.exit_code == 0
            # Rich output should not be JSON
            assert not result.stdout.strip().startswith("{")

    def test_custom_api_url(self, cli_runner, mock_session):
        """Test specifying custom API URL."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.list_sessions.return_value = SessionListResponse(sessions=[])
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "list",
                    "--api-url",
                    "http://custom:9000",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            # Verify get_client was called with custom URL
            mock_get_client.assert_called_once_with("http://custom:9000")

    def test_resolution_types(self, cli_runner, mock_session):
        """Test different resolution types."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.resolve_hole.return_value = mock_session
            mock_get_client.return_value = mock_client

            for resolution_type in ["clarify_intent", "refine_signature", "add_constraint"]:
                result = cli_runner.invoke(
                    app,
                    [
                        "resolve",
                        "test-session-123",
                        "hole_1",
                        "value",
                        "--type",
                        resolution_type,
                        "--json",
                    ],
                )

                assert result.exit_code == 0

    def test_get_session_with_ir_flag(self, cli_runner, mock_session):
        """Test getting session with --show-ir flag."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.get_session.return_value = mock_session
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "get",
                    "test-session-123",
                    "--show-ir",
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert "ir" in result.stdout

    def test_error_handling(self, cli_runner):
        """Test error handling for API failures."""
        with patch("lift_sys.cli.session_commands.get_client") as mock_get_client:
            mock_client = Mock()
            mock_client.create_session.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(
                app,
                [
                    "create",
                    "--prompt",
                    "Test",
                    "--json",
                ],
            )

            assert result.exit_code == 1
            assert "error" in result.stdout.lower() or "error" in str(result.exception).lower()
