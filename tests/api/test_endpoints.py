"""Integration tests for the FastAPI surface."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.reverse_mode.lifter import RepositoryHandle

pytestmark = pytest.mark.integration


def configure_backend(
    client,
    endpoint: str = "http://model",
    temperature: float = 0.3,
    provider: str = "vllm",
):
    response = client.post(
        "/config",
        json={
            "model_endpoint": endpoint,
            "temperature": temperature,
            "provider_type": provider,
            "schema_uri": "memory://schema.json",
            "grammar_source": "start -> expr",
        },
    )
    assert response.status_code == 200
    return response


def test_configure_endpoint_initialises_state(api_client, api_state) -> None:
    configure_backend(api_client)

    assert api_state.config is not None
    assert api_state.synthesizer is not None
    assert api_state.lifter is not None


def test_reverse_endpoint_happy_path(
    api_client, api_state, sample_ir: IntermediateRepresentation
) -> None:
    configure_backend(api_client)
    assert api_state.lifter is not None
    api_state.lifter.repo = MagicMock()
    api_state.lifter.repo.working_tree_dir = "/tmp/repo"

    with patch.object(api_state.lifter, "lift", return_value=sample_ir):
        response = api_client.post(
            "/reverse",
            json={"module": "module.py", "queries": ["security/default"], "entrypoint": "main"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ir"]["signature"]["name"] == sample_ir.signature.name
    assert api_state.planner.current_plan is not None


def test_reverse_endpoint_rejects_when_unconfigured(api_client) -> None:
    response = api_client.post(
        "/reverse",
        json={"module": "module.py", "queries": ["security/default"], "entrypoint": "main"},
    )
    assert response.status_code == 400


def test_forward_endpoint_generates_payload(
    api_client, api_state, sample_ir: IntermediateRepresentation
) -> None:
    configure_backend(api_client)
    assert api_state.synthesizer is not None

    payload = api_client.post(
        "/forward",
        json={"ir": sample_ir.to_dict()},
    )

    assert payload.status_code == 200
    body = payload.json()
    assert body["request_payload"]["prompt"]["intent"] == sample_ir.intent.summary
    assert body["request_payload"]["provider"] == "vllm"
    assert "stream" in body["request_payload"]
    assert isinstance(body["request_payload"]["stream"], list)


def test_forward_endpoint_requires_configuration(api_client) -> None:
    response = api_client.post(
        "/forward",
        json={"ir": {}},
    )
    assert response.status_code == 400


def test_open_repository_uses_lifter(api_client, api_state) -> None:
    configure_backend(api_client)
    assert api_state.lifter is not None

    with patch.object(api_state.lifter, "load_repository", return_value=MagicMock()) as loader:
        response = api_client.post("/repos/open", json={"identifier": "octocat/example"})

    assert response.status_code == 200
    loader.assert_called_once()
    args, _ = loader.call_args
    assert isinstance(args[0], RepositoryHandle)
    assert args[0].identifier == "octocat/example"


def test_list_repositories(api_client) -> None:
    response = api_client.get("/repos")

    assert response.status_code == 200
    payload = response.json()
    assert "repositories" in payload
    assert payload["repositories"][0]["identifier"] == "octocat/example"


def test_plan_endpoint_requires_plan(api_client) -> None:
    response = api_client.get("/plan")
    assert response.status_code == 404


def test_plan_endpoint_returns_loaded_plan(
    api_client, api_state, sample_ir: IntermediateRepresentation
) -> None:
    configure_backend(api_client)
    assert api_state.lifter is not None
    api_state.lifter.repo = MagicMock()
    api_state.lifter.repo.working_tree_dir = "/tmp/repo"

    with patch.object(api_state.lifter, "lift", return_value=sample_ir):
        api_client.post(
            "/reverse",
            json={"module": "module.py", "queries": ["security/default"], "entrypoint": "main"},
        )

    response = api_client.get("/plan")
    assert response.status_code == 200
    plan = response.json()
    assert plan["goals"] == ["verified_ir", "code_generation"]
    assert "decision_literals" in plan
    verifier_literal = plan["decision_literals"].get("controller:verifier")
    assert verifier_literal
    assert "steps" in verifier_literal
    assert plan["recent_events"] == []


def test_progress_socket_streams_planner_events(
    api_client, api_state, sample_ir: IntermediateRepresentation
) -> None:
    configure_backend(api_client)
    planner = api_state.planner
    planner.load_ir(sample_ir)

    planner.step("parse_ir", success=True)
    planner.step("verify_assertions", success=False, reason="blocked_by:controller:synthesiser")

    with api_client.websocket_connect("/ws/progress") as websocket:
        ready = websocket.receive_json()
        assert ready["type"] == "planner_ready"
        observed = {websocket.receive_json()["type"] for _ in range(4)}
        assert "decision" in observed
        assert "learned_clause" in observed
        assert "next_decisions" in observed
