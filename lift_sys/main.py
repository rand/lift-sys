"""Textual TUI entrypoint for lift-sys."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
from rich.text import Text
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Label, Static, TabbedContent, TabPane

API_URL = "http://localhost:8000"


@dataclass
class SessionState:
    endpoint: str = API_URL
    temperature: float = 0.0
    repository: Optional[str] = None
    ir: Optional[Dict[str, Any]] = None


class StatusPanel(Static):
    message = reactive("Ready")

    def watch_message(self, value: str) -> None:
        self.update(Text(value))


class LiftSysApp(App):
    CSS_PATH = None
    TITLE = "lift-sys"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+r", "refresh_plan", "Refresh Plan"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state = SessionState()
        self.status_panel = StatusPanel()
        self.plan_panel = Static("Plan not loaded")
        self.ir_panel = Static("IR not loaded")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Configuration"):
                yield Label("Model Endpoint")
                self.endpoint_input = Input(value=self.state.endpoint, placeholder="http://localhost:8001")
                yield self.endpoint_input
                yield Label("Temperature")
                self.temperature_input = Input(value=str(self.state.temperature))
                yield self.temperature_input
                yield Label("Repository Identifier")
                self.repo_input = Input(placeholder="owner/repository")
                yield self.repo_input
                yield Static("Press Enter in any field to submit.")
            with TabPane("IR" ):
                yield self.ir_panel
            with TabPane("Planner"):
                yield self.plan_panel
        yield self.status_panel
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is self.endpoint_input or event.input is self.temperature_input:
            await self.configure_backend()
        elif event.input is self.repo_input:
            await self.open_repo()

    async def configure_backend(self) -> None:
        endpoint = self.endpoint_input.value
        temperature = float(self.temperature_input.value or 0.0)
        payload = {"model_endpoint": endpoint, "temperature": temperature}
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{API_URL}/config", json=payload)
            response.raise_for_status()
        self.state.endpoint = endpoint
        self.state.temperature = temperature
        self.status_panel.message = "Configuration saved"

    async def open_repo(self) -> None:
        identifier = self.repo_input.value
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/repos/open", json={"identifier": identifier}
            )
            response.raise_for_status()
        self.state.repository = identifier
        self.status_panel.message = f"Repository {identifier} opened"

    async def action_refresh_plan(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/plan")
            if response.status_code == 404:
                self.plan_panel.update("Plan not initialised")
                return
            response.raise_for_status()
            plan = response.json()
        rendered = "\n".join(f"- {step['identifier']}: {step['description']}" for step in plan["steps"])
        self.plan_panel.update(rendered)
        self.status_panel.message = "Planner refreshed"

    async def watch_ir(self, ir: Dict[str, Any]) -> None:  # pragma: no cover - reactive hook
        self.ir_panel.update(str(ir))

    async def run_reverse(self, module: str) -> None:
        if not self.state.repository:
            self.status_panel.message = "Open a repository first"
            return
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_URL}/reverse",
                json={"module": module, "queries": ["security/default"], "entrypoint": "main"},
            )
            response.raise_for_status()
            payload = response.json()
        self.state.ir = payload["ir"]
        self.ir_panel.update(str(self.state.ir))
        self.status_panel.message = "IR lifted"


if __name__ == "__main__":
    app = LiftSysApp()
    app.run()
