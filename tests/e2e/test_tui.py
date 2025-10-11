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
                assert "identifier" in json
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

        app.repo_input.value = "octocat/example"
        await app.open_repo()

        await app.run_reverse("module.py")
        await app.action_refresh_plan()
        await pilot.wait_for_idle()

    assert app.status_panel.message == "Planner refreshed"
    assert "module" in str(app.ir_panel.renderable)
    assert "verify_assertions" in str(app.plan_panel.renderable)


# =============================================================================
# Additional TUI Test Placeholders
# These tests demonstrate the structure for comprehensive TUI testing
# =============================================================================


@pytest.mark.e2e
@pytest.mark.slow
class TestTUIWorkflows:
    """End-to-end tests for TUI application workflows."""

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_launches_successfully(self):
        """Test that TUI application launches without errors."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_navigation_to_ir_editor(self):
        """Test navigating to IR editor screen."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_load_ir_file(self, fixtures_dir):
        """Test loading an IR file in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_forward_mode_workflow(self, fixtures_dir):
        """Test complete forward mode code generation workflow in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_hole_interaction(self, fixtures_dir):
        """Test interacting with TypedHoles in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_save_ir(self, temp_dir, fixtures_dir):
        """Test saving modified IR in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_verification_display(self, fixtures_dir):
        """Test that verification results are displayed in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_plan_view(self, fixtures_dir):
        """Test viewing execution plan in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_help_screen(self):
        """Test accessing help screen in TUI."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_quit(self):
        """Test quitting TUI application."""
        pass


@pytest.mark.e2e
@pytest.mark.slow
class TestTUIEdgeCases:
    """Edge case tests for TUI."""

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_handles_invalid_ir(self, fixtures_dir):
        """Test TUI handling of invalid IR file."""
        pass

    @pytest.mark.skip(reason="Requires full Textual app implementation")
    async def test_tui_handles_missing_file(self, temp_dir):
        """Test TUI handling of missing file."""
        pass
