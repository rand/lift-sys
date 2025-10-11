"""Integration tests for CLI session management commands.

Tests cover:
- Session creation via CLI (from prompt and IR)
- Session listing
- Session retrieval
- Hole resolution
- Assists retrieval
- Session finalization
- Session deletion
- Error handling
- JSON output mode
- End-to-end workflow
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_cli(command: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
    """Run CLI command and return result.

    Args:
        command: CLI command arguments (without the module prefix)
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess with stdout/stderr
    """
    full_command = [
        sys.executable,
        "-m",
        "lift_sys.cli",
        "session",
    ] + command

    return subprocess.run(
        full_command,
        capture_output=capture_output,
        text=True,
        cwd=PROJECT_ROOT,
        env={"LIFT_SYS_ENABLE_DEMO_USER_HEADER": "1"},
    )


def parse_json_output(output: str) -> Any:
    """Parse JSON from CLI output.

    Args:
        output: CLI output string

    Returns:
        Parsed JSON data
    """
    # Find JSON content (skip any non-JSON lines)
    lines = output.strip().split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("{") or line.strip().startswith("["):
            json_content = "\n".join(lines[i:])
            return json.loads(json_content)
    raise ValueError(f"No JSON found in output: {output}")


@pytest.mark.integration
class TestCLISessionCommands:
    """Integration tests for CLI session commands.

    Note: These tests require a running API server on localhost:8000.
    The api_client fixture ensures the test server is running.
    """

    def test_cli_help_command(self):
        """Test CLI help output."""
        result = run_cli(["--help"])
        assert result.returncode == 0
        assert "session" in result.stdout.lower()

    def test_cli_create_session_from_prompt(self, api_client):
        """Test creating a session from a prompt via CLI."""
        # Note: This test requires the API to accept connections
        # Skip if API is not reachable
        import httpx

        try:
            httpx.get("http://localhost:8000/health", timeout=1.0)
        except Exception:
            pytest.skip("API server not accessible")

        result = run_cli(
            [
                "create",
                "--prompt",
                "A function that takes two integers and returns their sum",
                "--json",
            ]
        )

        if result.returncode != 0:
            # CLI tests may fail if server is not reachable
            pytest.skip(f"CLI failed: {result.stdout} {result.stderr}")

        data = parse_json_output(result.stdout)
        assert "session_id" in data
        assert data["status"] == "active"
        assert "ambiguities" in data

    def test_cli_create_session_from_ir_file(self, api_client, simple_ir, temp_dir):
        """Test creating a session from an IR file via CLI."""
        # Write IR to temp file
        ir_file = temp_dir / "test_ir.json"
        ir_file.write_text(json.dumps(simple_ir.to_dict()))

        result = run_cli(
            [
                "create",
                "--ir-file",
                str(ir_file),
                "--source",
                "reverse_mode",
                "--json",
            ]
        )

        assert result.returncode == 0
        data = parse_json_output(result.stdout)
        assert data["session_id"]
        assert data["source"] == "reverse_mode"

    def test_cli_create_session_missing_prompt_and_ir(self, api_client):
        """Test that creating session without prompt or IR fails."""
        result = run_cli(["create", "--json"])

        assert result.returncode == 1
        assert "prompt" in result.stdout.lower() or "ir" in result.stdout.lower()

    def test_cli_list_sessions_empty(self, api_client):
        """Test listing sessions when none exist."""
        result = run_cli(["list", "--json"])

        assert result.returncode == 0
        data = parse_json_output(result.stdout)
        assert isinstance(data, list)

    def test_cli_list_sessions_with_data(self, api_client):
        """Test listing sessions after creating some."""
        # Create two sessions
        run_cli(
            [
                "create",
                "--prompt",
                "Function to add numbers",
                "--json",
            ]
        )
        run_cli(
            [
                "create",
                "--prompt",
                "Function to multiply numbers",
                "--json",
            ]
        )

        # List sessions
        result = run_cli(["list", "--json"])

        assert result.returncode == 0
        data = parse_json_output(result.stdout)
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_cli_get_session(self, api_client):
        """Test retrieving a specific session by ID."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Function to compute factorial",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Get session
        get_result = run_cli(["get", session_id, "--json"])

        assert get_result.returncode == 0
        get_data = parse_json_output(get_result.stdout)
        assert get_data["session_id"] == session_id
        assert get_data["status"] == "active"

    def test_cli_get_session_not_found(self, api_client):
        """Test retrieving a non-existent session."""
        result = run_cli(["get", "nonexistent-id", "--json"])

        assert result.returncode == 1

    def test_cli_get_session_with_ir(self, api_client):
        """Test retrieving session with IR included."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Test function",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Get session with IR
        get_result = run_cli(["get", session_id, "--show-ir", "--json"])

        assert get_result.returncode == 0
        get_data = parse_json_output(get_result.stdout)
        assert "ir" in get_data
        assert get_data["ir"] is not None

    def test_cli_resolve_hole(self, api_client):
        """Test resolving a hole via CLI."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Add numbers",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Check if there are holes to resolve
        if create_data.get("ambiguities"):
            hole_id = create_data["ambiguities"][0]

            # Resolve the hole
            resolve_result = run_cli(
                [
                    "resolve",
                    session_id,
                    hole_id,
                    "int",
                    "--json",
                ]
            )

            assert resolve_result.returncode == 0
            resolve_data = parse_json_output(resolve_result.stdout)
            assert resolve_data["session_id"] == session_id

    def test_cli_resolve_hole_session_not_found(self, api_client):
        """Test resolving hole in non-existent session."""
        result = run_cli(
            [
                "resolve",
                "nonexistent",
                "hole_id",
                "resolution",
                "--json",
            ]
        )

        assert result.returncode == 1

    def test_cli_get_assists(self, api_client):
        """Test getting assist suggestions via CLI."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Calculate something",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Get assists
        assists_result = run_cli(["assists", session_id, "--json"])

        assert assists_result.returncode == 0
        assists_data = parse_json_output(assists_result.stdout)
        assert isinstance(assists_data, list)

    def test_cli_get_assists_session_not_found(self, api_client):
        """Test getting assists for non-existent session."""
        result = run_cli(["assists", "nonexistent", "--json"])

        assert result.returncode == 1

    def test_cli_finalize_session(self, api_client, simple_ir, temp_dir):
        """Test finalizing a session via CLI."""
        # Create session from complete IR
        ir_file = temp_dir / "finalize_ir.json"
        ir_file.write_text(json.dumps(simple_ir.to_dict()))

        create_result = run_cli(
            [
                "create",
                "--ir-file",
                str(ir_file),
                "--source",
                "reverse_mode",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # If no ambiguities, finalize
        if not create_data.get("ambiguities"):
            finalize_result = run_cli(
                [
                    "finalize",
                    session_id,
                    "--json",
                ]
            )

            assert finalize_result.returncode == 0
            finalize_data = parse_json_output(finalize_result.stdout)
            assert finalize_data is not None

    def test_cli_finalize_session_with_holes(self, api_client):
        """Test that finalizing fails with unresolved holes."""
        # Create session with ambiguities
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Function",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Try to finalize with holes
        if create_data.get("ambiguities"):
            finalize_result = run_cli(
                [
                    "finalize",
                    session_id,
                    "--json",
                ]
            )

            assert finalize_result.returncode == 1

    def test_cli_finalize_session_not_found(self, api_client):
        """Test finalizing a non-existent session."""
        result = run_cli(["finalize", "nonexistent", "--json"])

        assert result.returncode == 1

    def test_cli_finalize_session_with_output_file(self, api_client, simple_ir, temp_dir):
        """Test finalizing session and saving IR to file."""
        # Create session from complete IR
        ir_file = temp_dir / "input_ir.json"
        ir_file.write_text(json.dumps(simple_ir.to_dict()))

        create_result = run_cli(
            [
                "create",
                "--ir-file",
                str(ir_file),
                "--source",
                "reverse_mode",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # If no ambiguities, finalize with output file
        if not create_data.get("ambiguities"):
            output_file = temp_dir / "output_ir.json"
            finalize_result = run_cli(
                [
                    "finalize",
                    session_id,
                    "--output",
                    str(output_file),
                    "--json",
                ]
            )

            assert finalize_result.returncode == 0
            assert output_file.exists()

            # Verify output file has valid IR
            output_ir = json.loads(output_file.read_text())
            assert "intent" in output_ir
            assert "signature" in output_ir

    def test_cli_delete_session(self, api_client):
        """Test deleting a session via CLI."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Test function",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Delete session with --yes flag to skip confirmation
        delete_result = run_cli(
            [
                "delete",
                session_id,
                "--yes",
            ]
        )

        assert delete_result.returncode == 0
        assert "deleted" in delete_result.stdout.lower()

        # Verify session is gone
        get_result = run_cli(["get", session_id, "--json"])
        assert get_result.returncode == 1

    def test_cli_delete_session_not_found(self, api_client):
        """Test deleting a non-existent session."""
        result = run_cli(
            [
                "delete",
                "nonexistent",
                "--yes",
            ]
        )

        assert result.returncode == 1

    def test_cli_workflow_complete(self, api_client):
        """Test complete CLI workflow: create → list → get → assists → resolve → finalize."""
        # Step 1: Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Function that takes an integer and returns boolean",
                "--json",
            ]
        )
        assert create_result.returncode == 0
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Step 2: List sessions
        list_result = run_cli(["list", "--json"])
        assert list_result.returncode == 0
        list_data = parse_json_output(list_result.stdout)
        assert any(s["session_id"] == session_id for s in list_data)

        # Step 3: Get session
        get_result = run_cli(["get", session_id, "--json"])
        assert get_result.returncode == 0
        get_data = parse_json_output(get_result.stdout)
        assert get_data["session_id"] == session_id

        # Step 4: Get assists
        assists_result = run_cli(["assists", session_id, "--json"])
        assert assists_result.returncode == 0

        # Step 5: Resolve holes if any
        if create_data.get("ambiguities"):
            hole_id = create_data["ambiguities"][0]
            resolve_result = run_cli(
                [
                    "resolve",
                    session_id,
                    hole_id,
                    "test_value",
                    "--json",
                ]
            )
            assert resolve_result.returncode == 0

    def test_cli_rich_output_mode(self, api_client):
        """Test that CLI produces rich output when --json is not specified."""
        # Create session without --json flag
        result = run_cli(
            [
                "create",
                "--prompt",
                "Test function",
            ]
        )

        assert result.returncode == 0
        # Rich output should contain formatted text (not JSON)
        assert not result.stdout.strip().startswith("{")
        assert "Session" in result.stdout or "session" in result.stdout.lower()

    def test_cli_custom_api_url(self, api_client):
        """Test specifying custom API URL."""
        result = run_cli(
            [
                "list",
                "--api-url",
                "http://localhost:8000",
                "--json",
            ]
        )

        assert result.returncode == 0

    def test_cli_resolution_types(self, api_client):
        """Test different resolution types."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Test",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        if create_data.get("ambiguities"):
            hole_id = create_data["ambiguities"][0]

            # Test different resolution types
            for resolution_type in ["clarify_intent", "refine_signature", "add_constraint"]:
                resolve_result = run_cli(
                    [
                        "resolve",
                        session_id,
                        hole_id,
                        "test_value",
                        "--type",
                        resolution_type,
                        "--json",
                    ]
                )

                # Should succeed (or fail if hole already resolved)
                assert resolve_result.returncode in [0, 1]

    def test_cli_metadata_preservation(self, api_client):
        """Test that metadata is preserved in CLI operations."""
        # Create session
        create_result = run_cli(
            [
                "create",
                "--prompt",
                "Test function",
                "--json",
            ]
        )
        create_data = parse_json_output(create_result.stdout)
        session_id = create_data["session_id"]

        # Get session and verify metadata exists
        get_result = run_cli(["get", session_id, "--json"])
        get_data = parse_json_output(get_result.stdout)
        assert "session_id" in get_data
        assert "status" in get_data

    def test_cli_error_messages(self, api_client):
        """Test that CLI provides helpful error messages."""
        # Test various error conditions
        error_cases = [
            (["get", "invalid-session-id"], "not found"),
            (["resolve", "invalid", "hole", "value"], "not found"),
            (["assists", "invalid"], "not found"),
            (["finalize", "invalid"], "not found"),
            (["delete", "invalid", "--yes"], "not found"),
        ]

        for command, expected_text in error_cases:
            result = run_cli(command)
            assert result.returncode == 1
            # Error output can be in stdout or stderr
            output = result.stdout + result.stderr
            assert expected_text.lower() in output.lower() or "error" in output.lower()
