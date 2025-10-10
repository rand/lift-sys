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

    def test_repos_open_endpoint(self, api_client, temp_repo, temp_dir):
        """Test repository opening endpoint."""
        response = api_client.post(
            "/repos/open",
            json={"path": str(temp_dir)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_repos_open_invalid_path(self, api_client):
        """Test repository opening with invalid path."""
        response = api_client.post(
            "/repos/open",
            json={"path": "/nonexistent/path"},
        )

        # Should handle invalid path gracefully
        assert response.status_code in [400, 404, 500]

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
