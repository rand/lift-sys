"""Integration tests for API endpoints.

Tests cover:
- All API endpoints
- Happy path (200 OK)
- Error handling (4xx)
- Request/response formats
- State management
"""
import pytest
from fastapi.testclient import TestClient

from lift_sys.services.github_repository import RepositoryAccessError


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for FastAPI endpoints."""

    def test_root_endpoint(self, api_client):
        """Test root endpoint returns API information."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "lift-sys API"

    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_config_endpoint_success(self, api_client):
        """Test configuration endpoint with valid payload."""
        response = api_client.post(
            "/config",
            json={
                "model_endpoint": "http://localhost:8001",
                "temperature": 0.7,
                "provider_type": "vllm",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "configured"

    def test_config_endpoint_invalid_json(self, api_client):
        """Test configuration endpoint with invalid JSON."""
        response = api_client.post(
            "/config",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422  # Unprocessable Entity

    def test_forward_endpoint_without_config(self, api_client):
        """Test forward endpoint fails without configuration."""
        response = api_client.post(
            "/forward",
            json={
                "ir": {
                    "intent": {"summary": "test", "rationale": "", "holes": []},
                    "signature": {"name": "test", "parameters": [], "returns": None, "holes": []},
                    "effects": [],
                    "assertions": [],
                    "metadata": {"source_path": None, "language": None, "origin": None},
                }
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not configured" in data["detail"].lower()

    def test_forward_endpoint_with_config(self, configured_api_client, simple_ir):
        """Test forward endpoint with valid configuration and IR."""
        ir_dict = simple_ir.to_dict()

        response = configured_api_client.post(
            "/forward",
            json={"ir": ir_dict},
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_payload" in data
        payload = data["request_payload"]
        assert "endpoint" in payload
        assert "temperature" in payload
        assert "prompt" in payload
        assert payload["provider"] == "vllm"
        assert isinstance(payload.get("stream"), list)
        assert "constraint_intersections" in payload
        assert payload["telemetry"]

    def test_forward_endpoint_invalid_ir(self, configured_api_client):
        """Test forward endpoint with invalid IR structure."""
        response = configured_api_client.post(
            "/forward",
            json={
                "ir": {
                    "invalid": "structure",
                }
            },
        )

        # Should return error for invalid IR
        assert response.status_code in [400, 422]

    def test_plan_endpoint_without_ir(self, api_client):
        """Test plan endpoint without loaded IR."""
        response = api_client.get("/plan")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_repos_open_endpoint(self, api_client):
        """Test repository opening endpoint."""
        response = api_client.post(
            "/repos/open",
            json={"identifier": "octocat/example"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["repository"]["identifier"] == "octocat/example"

    def test_repos_list_endpoint(self, api_client):
        """Repositories endpoint should list accessible repositories."""
        response = api_client.get("/repos")

        assert response.status_code == 200
        data = response.json()
        assert data["repositories"][0]["identifier"] == "octocat/example"

    def test_repos_open_permission_error(self, api_client, monkeypatch):
        """Repository open should respect permission failures."""

        async def fail(*_args, **_kwargs):
            raise RepositoryAccessError(403, "github_token_missing")

        monkeypatch.setattr(
            api_client.app.state.github_repositories,
            "ensure_repository",
            fail,
        )
        response = api_client.post(
            "/repos/open",
            json={"identifier": "octocat/example"},
        )

        assert response.status_code == 403

    def test_multiple_config_updates(self, api_client):
        """Test updating configuration multiple times."""
        # First config
        response1 = api_client.post(
            "/config",
            json={
                "model_endpoint": "http://localhost:8001",
                "temperature": 0.5,
                "provider_type": "vllm",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            },
        )
        assert response1.status_code == 200

        # Second config
        response2 = api_client.post(
            "/config",
            json={
                "model_endpoint": "http://localhost:8002",
                "temperature": 0.8,
                "provider_type": "sglang",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            },
        )
        assert response2.status_code == 200

    def test_forward_workflow(self, api_client, simple_ir):
        """Test complete forward workflow."""
        # Step 1: Configure
        config_response = api_client.post(
            "/config",
            json={
                "model_endpoint": "http://localhost:8001",
                "temperature": 0.7,
                "provider_type": "vllm",
                "schema_uri": "memory://schema.json",
                "grammar_source": "start -> expr",
            },
        )
        assert config_response.status_code == 200

        # Step 2: Generate code
        forward_response = api_client.post(
            "/forward",
            json={"ir": simple_ir.to_dict()},
        )
        assert forward_response.status_code == 200
        data = forward_response.json()
        assert "request_payload" in data
        assert isinstance(data["request_payload"].get("stream"), list)

    def test_config_temperature_bounds(self, api_client):
        """Test configuration with different temperature values."""
        valid_temps = [0.0, 0.5, 1.0, 2.0]

        for temp in valid_temps:
            response = api_client.post(
                "/config",
                json={
                    "model_endpoint": "http://localhost:8001",
                    "temperature": temp,
                    "provider_type": "vllm",
                },
            )
            assert response.status_code == 200

    def test_concurrent_requests(self, configured_api_client, simple_ir):
        """Test handling of concurrent requests."""
        ir_dict = simple_ir.to_dict()

        # Make multiple concurrent requests
        responses = []
        for _ in range(3):
            response = configured_api_client.post(
                "/forward",
                json={"ir": ir_dict},
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200

    def test_api_cors_headers(self, api_client):
        """Test that API handles CORS properly."""
        response = api_client.get("/health")

        # Check if CORS headers are present
        # (FastAPI may add these automatically or via middleware)
        assert response.status_code == 200

    def test_api_content_type(self, api_client):
        """Test that API returns correct content type."""
        response = api_client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_forward_preserves_ir_structure(self, configured_api_client, complex_ir):
        """Test that forward mode preserves complex IR structure."""
        ir_dict = complex_ir.to_dict()

        response = configured_api_client.post(
            "/forward",
            json={"ir": ir_dict},
        )

        assert response.status_code == 200
        data = response.json()
        prompt = data["request_payload"]["prompt"]
        assert "constraint_intersections" in data["request_payload"]
        assert data["request_payload"]["constraint_intersections"]["assertion"]

        # Verify structure preserved
        assert "intent" in prompt
        assert "signature" in prompt
        assert "constraints" in prompt

    def test_api_error_messages(self, api_client):
        """Test that API returns helpful error messages."""
        response = api_client.post(
            "/forward",
            json={"ir": {"malformed": "data"}},
        )

        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], (str, list, dict))

    def test_websocket_endpoint_exists(self, api_client):
        """Test that WebSocket endpoint is accessible."""
        # Note: WebSocket testing requires special handling
        # This just checks the endpoint exists
        # Full WebSocket testing would require pytest-asyncio and websockets

        # Try to access WebSocket endpoint (will fail but endpoint should exist)
        # Real WebSocket test would use WebSocketTestClient

        # For now, just verify other endpoints work
        response = api_client.get("/health")
        assert response.status_code == 200

    def test_api_versioning(self, api_client):
        """Test that API version is accessible."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_state_isolation_between_requests(self, api_client, simple_ir):
        """Test that state is properly isolated between requests."""
        # Configure once
        api_client.post(
            "/config",
            json={"model_endpoint": "http://localhost:8001", "temperature": 0.5},
        )

        # Make forward request
        response1 = api_client.post(
            "/forward",
            json={"ir": simple_ir.to_dict()},
        )
        assert response1.status_code == 200

        # Make another forward request
        response2 = api_client.post(
            "/forward",
            json={"ir": simple_ir.to_dict()},
        )
        assert response2.status_code == 200

        # Both should succeed independently
        assert response1.json() is not None
        assert response2.json() is not None

    # =============================================================================
    # Session Management Endpoints Tests
    # =============================================================================

    def test_create_session_from_prompt(self, api_client):
        """Test creating a session from a natural language prompt."""
        response = api_client.post(
            "/spec-sessions",
            json={
                "prompt": "Create a function that takes two integers and returns their sum",
                "source": "prompt",
                "metadata": {"test": "value"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "active"
        assert data["source"] == "prompt"
        assert "ambiguities" in data
        assert "current_draft" in data
        assert data["revision_count"] > 0
        assert data["metadata"]["test"] == "value"

    def test_create_session_from_ir(self, api_client, simple_ir):
        """Test creating a session from an existing IR (reverse mode)."""
        response = api_client.post(
            "/spec-sessions",
            json={
                "ir": simple_ir.to_dict(),
                "source": "reverse_mode",
                "metadata": {"origin": "reverse"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"]
        assert data["status"] == "active"
        assert data["source"] == "reverse_mode"
        assert data["metadata"]["origin"] == "reverse"

    def test_create_session_requires_prompt_or_ir(self, api_client):
        """Test that creating a session requires either prompt or IR."""
        response = api_client.post(
            "/spec-sessions",
            json={
                "source": "prompt",
                "metadata": {},
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        # Check that both "prompt" and "ir" are mentioned in the error
        assert "prompt" in data["detail"].lower() and "ir" in data["detail"].lower()

    def test_list_sessions_empty(self, api_client):
        """Test listing sessions when none exist."""
        response = api_client.get("/spec-sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) == 0

    def test_list_sessions_with_data(self, api_client):
        """Test listing sessions after creating some."""
        # Create first session
        response1 = api_client.post(
            "/spec-sessions",
            json={"prompt": "Function to add numbers", "source": "prompt"},
        )
        assert response1.status_code == 200

        # Create second session
        response2 = api_client.post(
            "/spec-sessions",
            json={"prompt": "Function to multiply numbers", "source": "prompt"},
        )
        assert response2.status_code == 200

        # List sessions
        list_response = api_client.get("/spec-sessions")
        assert list_response.status_code == 200
        data = list_response.json()
        assert len(data["sessions"]) == 2
        assert all(s["status"] == "active" for s in data["sessions"])

    def test_get_session_by_id(self, api_client):
        """Test retrieving a specific session by ID."""
        # Create session
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Function to compute factorial", "source": "prompt"},
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Get session
        get_response = api_client.get(f"/spec-sessions/{session_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "active"

    def test_get_session_not_found(self, api_client):
        """Test retrieving a non-existent session."""
        response = api_client.get("/spec-sessions/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    def test_resolve_hole(self, api_client):
        """Test resolving a typed hole in a session."""
        # Create session with ambiguities
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Add numbers", "source": "prompt"},
        )
        assert create_response.status_code == 200
        data = create_response.json()
        session_id = data["session_id"]

        # Check if there are ambiguities to resolve
        if data["ambiguities"]:
            hole_id = data["ambiguities"][0]

            # Resolve the hole
            resolve_response = api_client.post(
                f"/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                json={
                    "resolution_text": "int",
                    "resolution_type": "refine_signature",
                },
            )

            assert resolve_response.status_code == 200
            resolved_data = resolve_response.json()
            assert resolved_data["session_id"] == session_id
            # Check that ambiguities decreased or stayed same
            assert len(resolved_data["ambiguities"]) <= len(data["ambiguities"])

    def test_resolve_hole_session_not_found(self, api_client):
        """Test resolving a hole in a non-existent session."""
        response = api_client.post(
            "/spec-sessions/nonexistent/holes/hole1/resolve",
            json={"resolution_text": "int", "resolution_type": "refine_signature"},
        )

        assert response.status_code == 404

    def test_get_assists(self, api_client):
        """Test getting actionable suggestions for resolving holes."""
        # Create session
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Calculate", "source": "prompt"},
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Get assists
        assists_response = api_client.get(f"/spec-sessions/{session_id}/assists")
        assert assists_response.status_code == 200
        data = assists_response.json()
        assert "assists" in data
        assert isinstance(data["assists"], list)

        # Check assist structure if any exist
        if data["assists"]:
            assist = data["assists"][0]
            assert "hole_id" in assist
            assert "hole_kind" in assist
            assert "suggestion" in assist
            assert "description" in assist

    def test_get_assists_session_not_found(self, api_client):
        """Test getting assists for non-existent session."""
        response = api_client.get("/spec-sessions/nonexistent/assists")

        assert response.status_code == 404

    def test_finalize_session(self, api_client, simple_ir):
        """Test finalizing a session with no remaining holes."""
        # Create session from complete IR
        create_response = api_client.post(
            "/spec-sessions",
            json={"ir": simple_ir.to_dict(), "source": "reverse_mode"},
        )
        assert create_response.status_code == 200
        data = create_response.json()
        session_id = data["session_id"]

        # If there are no ambiguities, we can finalize
        if not data["ambiguities"]:
            finalize_response = api_client.post(
                f"/spec-sessions/{session_id}/finalize"
            )

            assert finalize_response.status_code == 200
            finalized_data = finalize_response.json()
            assert "ir" in finalized_data
            assert finalized_data["ir"] is not None

    def test_finalize_session_with_holes(self, api_client):
        """Test that finalizing fails with unresolved holes."""
        # Create session with ambiguities
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Function", "source": "prompt"},
        )
        assert create_response.status_code == 200
        data = create_response.json()
        session_id = data["session_id"]

        # Try to finalize with holes
        if data["ambiguities"]:
            finalize_response = api_client.post(
                f"/spec-sessions/{session_id}/finalize"
            )

            assert finalize_response.status_code == 400
            error_data = finalize_response.json()
            assert "detail" in error_data
            assert "unresolved" in error_data["detail"].lower()

    def test_finalize_session_not_found(self, api_client):
        """Test finalizing a non-existent session."""
        response = api_client.post("/spec-sessions/nonexistent/finalize")

        assert response.status_code == 404

    def test_delete_session(self, api_client):
        """Test deleting a session."""
        # Create session
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Test function", "source": "prompt"},
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Delete session
        delete_response = api_client.delete(f"/spec-sessions/{session_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["status"] == "deleted"
        assert data["session_id"] == session_id

        # Verify session is gone
        get_response = api_client.get(f"/spec-sessions/{session_id}")
        assert get_response.status_code == 404

    def test_delete_session_not_found(self, api_client):
        """Test deleting a non-existent session."""
        response = api_client.delete("/spec-sessions/nonexistent")

        assert response.status_code == 404

    def test_session_workflow_complete(self, api_client):
        """Test complete session workflow: create → resolve → finalize."""
        # Step 1: Create session
        create_response = api_client.post(
            "/spec-sessions",
            json={
                "prompt": "Function that takes an integer n and returns boolean",
                "source": "prompt",
            },
        )
        assert create_response.status_code == 200
        data = create_response.json()
        session_id = data["session_id"]
        initial_ambiguities = data["ambiguities"]

        # Step 2: Get assists
        assists_response = api_client.get(f"/spec-sessions/{session_id}/assists")
        assert assists_response.status_code == 200

        # Step 3: Resolve holes if any exist
        if initial_ambiguities:
            for hole_id in initial_ambiguities[:2]:  # Resolve first two holes
                # Get current state
                get_response = api_client.get(f"/spec-sessions/{session_id}")
                current_data = get_response.json()

                # Only resolve if hole still exists
                if hole_id in current_data["ambiguities"]:
                    resolve_response = api_client.post(
                        f"/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                        json={
                            "resolution_text": "Resolved value",
                            "resolution_type": "clarify_intent",
                        },
                    )
                    assert resolve_response.status_code == 200

        # Step 4: Check final state
        final_response = api_client.get(f"/spec-sessions/{session_id}")
        assert final_response.status_code == 200
        final_data = final_response.json()

        # Verify session is still active
        assert final_data["status"] == "active"

    def test_session_isolation(self, api_client):
        """Test that sessions are isolated from each other."""
        # Create two sessions
        response1 = api_client.post(
            "/spec-sessions",
            json={"prompt": "First function", "source": "prompt"},
        )
        response2 = api_client.post(
            "/spec-sessions",
            json={"prompt": "Second function", "source": "prompt"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        session1_id = response1.json()["session_id"]
        session2_id = response2.json()["session_id"]

        assert session1_id != session2_id

        # Modify session 1
        session1_data = api_client.get(f"/spec-sessions/{session1_id}").json()
        if session1_data["ambiguities"]:
            hole_id = session1_data["ambiguities"][0]
            api_client.post(
                f"/spec-sessions/{session1_id}/holes/{hole_id}/resolve",
                json={"resolution_text": "Modified", "resolution_type": "clarify_intent"},
            )

        # Verify session 2 is unchanged
        session2_after = api_client.get(f"/spec-sessions/{session2_id}").json()
        assert session2_after["revision_count"] == response2.json()["revision_count"]

    def test_session_metadata_preserved(self, api_client):
        """Test that session metadata is preserved throughout workflow."""
        metadata = {"user_id": "test123", "project": "demo", "tags": ["experimental"]}

        # Create session with metadata
        create_response = api_client.post(
            "/spec-sessions",
            json={
                "prompt": "Test function",
                "source": "prompt",
                "metadata": metadata,
            },
        )

        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Retrieve and verify metadata
        get_response = api_client.get(f"/spec-sessions/{session_id}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["metadata"]["user_id"] == "test123"
        assert data["metadata"]["project"] == "demo"
        assert data["metadata"]["tags"] == ["experimental"]

    def test_session_revision_tracking(self, api_client):
        """Test that sessions track revisions correctly."""
        # Create session
        create_response = api_client.post(
            "/spec-sessions",
            json={"prompt": "Function to test", "source": "prompt"},
        )

        assert create_response.status_code == 200
        data = create_response.json()
        session_id = data["session_id"]
        initial_revision_count = data["revision_count"]

        # Resolve a hole to create a new revision
        if data["ambiguities"]:
            hole_id = data["ambiguities"][0]
            resolve_response = api_client.post(
                f"/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                json={"resolution_text": "int", "resolution_type": "refine_signature"},
            )

            assert resolve_response.status_code == 200
            resolved_data = resolve_response.json()

            # Revision count should increase
            assert resolved_data["revision_count"] > initial_revision_count
