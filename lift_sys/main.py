"""Textual TUI entrypoint for lift-sys."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from rich.text import Text
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    Static,
    TabbedContent,
    TabPane,
)

from lift_sys.client import PromptSession, SessionClient

API_URL = "http://localhost:8000"


@dataclass
class SessionState:
    endpoint: str = API_URL
    temperature: float = 0.0
    repository: str | None = None
    ir: dict[str, Any] | None = None
    active_session: PromptSession | None = None
    sessions: list[PromptSession] = None

    def __post_init__(self):
        if self.sessions is None:
            self.sessions = []


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
        ("ctrl+l", "list_sessions", "List Sessions"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.state = SessionState()
        self.status_panel = StatusPanel()
        self.plan_panel = Static("Plan not loaded")
        self.ir_panel = Static("IR not loaded")
        self.session_client = SessionClient(API_URL)
        self.sessions_list = Static("No sessions")
        self.session_detail = Static("Select a session")

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Configuration"):
                yield Label("Model Endpoint")
                self.endpoint_input = Input(
                    value=self.state.endpoint, placeholder="http://localhost:8001"
                )
                yield self.endpoint_input
                yield Label("Temperature")
                self.temperature_input = Input(value=str(self.state.temperature))
                yield self.temperature_input
                yield Label("Repository Identifier")
                self.repo_input = Input(placeholder="owner/repository")
                yield self.repo_input
                yield Static("Press Enter in any field to submit.")
            with TabPane("Prompt Refinement"):
                yield Label("Natural Language Prompt")
                self.prompt_input = Input(placeholder="e.g., A function that adds two numbers")
                yield self.prompt_input
                yield Static("Press Enter to create session | Ctrl+L to list sessions")
                yield Label("Sessions")
                yield self.sessions_list
                yield Label("Session Details")
                yield self.session_detail
            with TabPane("IR"):
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
        elif event.input is self.prompt_input:
            await self.create_prompt_session()

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
            response = await client.post(f"{API_URL}/repos/open", json={"identifier": identifier})
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
        rendered = "\n".join(
            f"- {step['identifier']}: {step['description']}" for step in plan["steps"]
        )
        self.plan_panel.update(rendered)
        self.status_panel.message = "Planner refreshed"

    async def action_list_sessions(self) -> None:
        """Action to list prompt refinement sessions."""
        await self.list_prompt_sessions()

    async def watch_ir(self, ir: dict[str, Any]) -> None:  # pragma: no cover - reactive hook
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

    async def create_prompt_session(self) -> None:
        """Create a new prompt refinement session."""
        prompt = self.prompt_input.value
        if not prompt.strip():
            self.status_panel.message = "Please enter a prompt"
            return

        try:
            session = await self.session_client.acreate_session(prompt=prompt.strip())
            self.state.active_session = session
            self.state.sessions.append(session)
            self.prompt_input.value = ""
            await self.refresh_session_display()
            self.status_panel.message = f"Created session {session.session_id[:8]}"
        except Exception as e:
            self.status_panel.message = f"Error: {str(e)}"

    async def list_prompt_sessions(self) -> None:
        """List all prompt refinement sessions."""
        try:
            response = await self.session_client.alist_sessions()
            self.state.sessions = response.sessions
            await self.refresh_sessions_list()
            self.status_panel.message = f"Found {len(response.sessions)} sessions"
        except Exception as e:
            self.status_panel.message = f"Error: {str(e)}"

    async def refresh_sessions_list(self) -> None:
        """Update the sessions list display."""
        if not self.state.sessions:
            self.sessions_list.update("No sessions")
            return

        lines = []
        for session in self.state.sessions:
            status_mark = "●" if session.status == "active" else "○"
            holes_count = len(session.ambiguities)
            lines.append(
                f"{status_mark} {session.session_id[:12]}... "
                f"({session.status}, {holes_count} holes)"
            )
        self.sessions_list.update("\n".join(lines))

    async def refresh_session_display(self) -> None:
        """Update the active session detail display."""
        session = self.state.active_session
        if not session:
            self.session_detail.update("No active session")
            return

        lines = [
            f"Session: {session.session_id}",
            f"Status: {session.status}",
            f"Source: {session.source}",
            f"Draft version: {session.current_draft.version if session.current_draft else 0}",
            f"Validation: {session.current_draft.validation_status if session.current_draft else 'N/A'}",
            f"Ambiguities: {len(session.ambiguities)}",
            "",
        ]

        if session.ambiguities:
            lines.append("Unresolved holes:")
            for hole_id in session.ambiguities:
                lines.append(f"  - {hole_id}")
            lines.append("")
            lines.append("Use API or web UI to resolve holes")
        else:
            lines.append("✓ No ambiguities - ready to finalize")

        if session.current_draft and session.current_draft.ir:
            lines.append("")
            lines.append("IR Preview:")
            lines.append(str(session.current_draft.ir))

        self.session_detail.update("\n".join(lines))


if __name__ == "__main__":
    app = LiftSysApp()
    app.run()
