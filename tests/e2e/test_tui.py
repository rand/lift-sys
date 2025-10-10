"""Textual Pilot based end-to-end tests."""
from __future__ import annotations

from typing import Any, Dict

import pytest

pytest.importorskip("textual.testing")

from textual.testing import Pilot  # noqa: E402  - imported after availability check

from lift_sys.main import LiftSysApp


pytestmark = [pytest.mark.e2e, pytest.mark.textual]


class _DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError(f"Unexpected HTTP status {self.status_code}")


@pytest.mark.asyncio
async def test_tui_ir_to_code_generation(monkeypatch, sample_ir) -> None:
    """Drive the TUI through reverse mode and plan refresh."""

    plan_payload = {
        "steps": [
            {"identifier": "parse_ir", "description": "Parse IR and normalise metadata"},
            {"identifier": "verify_assertions", "description": "Verify logical assertions with SMT"},
        ],
        "goals": ["verified_ir", "code_generation"],
    }

    class DummyAsyncClient:
        async def __aenter__(self) -> "DummyAsyncClient":  # type: ignore[override]
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
            return None

        async def post(self, url: str, json: Dict[str, Any]) -> _DummyResponse:
            if url.endswith("/config"):
                return _DummyResponse({"status": "configured"})
            if url.endswith("/repos/open"):
                return _DummyResponse({"status": "ready"})
            if url.endswith("/reverse"):
                return _DummyResponse({"ir": sample_ir.to_dict()})
            raise AssertionError(f"Unexpected POST {url}")

        async def get(self, url: str) -> _DummyResponse:
            if url.endswith("/plan"):
                return _DummyResponse(plan_payload)
            raise AssertionError(f"Unexpected GET {url}")

    monkeypatch.setattr("lift_sys.main.httpx.AsyncClient", lambda: DummyAsyncClient())

    app = LiftSysApp()
    async with Pilot.create(app) as pilot:
        await pilot.start()
        app.endpoint_input.value = "http://localhost:8001"
        app.temperature_input.value = "0.0"
        await app.configure_backend()

        app.repo_input.value = "/tmp/repo"
        await app.open_repo()

        await app.run_reverse("module.py")
        await app.action_refresh_plan()
        await pilot.wait_for_idle()

    assert app.status_panel.message == "Planner refreshed"
    assert "module" in str(app.ir_panel.renderable)
    assert "verify_assertions" in str(app.plan_panel.renderable)
