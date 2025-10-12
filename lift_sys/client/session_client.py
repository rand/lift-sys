"""Python client for lift-sys session management API.

Provides both synchronous and asynchronous interfaces for programmatic use.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class IRDraft:
    """IR draft with validation status."""

    version: int
    ir: dict[str, Any]
    validation_status: str
    ambiguities: list[str]
    smt_results: list[dict[str, Any]]
    created_at: str
    metadata: dict[str, Any]


@dataclass
class PromptSession:
    """Prompt refinement session."""

    session_id: str
    status: str
    source: str
    created_at: str
    updated_at: str
    current_draft: IRDraft | None
    ambiguities: list[str]
    revision_count: int
    metadata: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptSession:
        """Create from API response."""
        draft_data = data.get("current_draft")
        draft = (
            IRDraft(
                version=draft_data["version"],
                ir=draft_data["ir"],
                validation_status=draft_data["validation_status"],
                ambiguities=draft_data["ambiguities"],
                smt_results=draft_data["smt_results"],
                created_at=draft_data["created_at"],
                metadata=draft_data["metadata"],
            )
            if draft_data
            else None
        )

        return cls(
            session_id=data["session_id"],
            status=data["status"],
            source=data["source"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            current_draft=draft,
            ambiguities=data["ambiguities"],
            revision_count=data["revision_count"],
            metadata=data["metadata"],
        )


@dataclass
class CreateSessionRequest:
    """Request to create a new session."""

    prompt: str | None = None
    ir: dict[str, Any] | None = None
    source: str = "prompt"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request format."""
        result: dict[str, Any] = {"source": self.source}
        if self.prompt:
            result["prompt"] = self.prompt
        if self.ir:
            result["ir"] = self.ir
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass
class ResolveHoleRequest:
    """Request to resolve a typed hole."""

    resolution_text: str
    resolution_type: str = "clarify_intent"

    def to_dict(self) -> dict[str, Any]:
        """Convert to API request format."""
        return {
            "resolution_text": self.resolution_text,
            "resolution_type": self.resolution_type,
        }


@dataclass
class SessionListResponse:
    """Response containing session list."""

    sessions: list[PromptSession]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionListResponse:
        """Create from API response."""
        return cls(sessions=[PromptSession.from_dict(s) for s in data["sessions"]])


@dataclass
class AssistSuggestion:
    """Suggestion for resolving a hole."""

    hole_id: str
    suggestions: list[str]
    context: str


@dataclass
class AssistsResponse:
    """Response containing assist suggestions."""

    session_id: str
    assists: list[AssistSuggestion]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssistsResponse:
        """Create from API response."""
        return cls(
            session_id=data["session_id"],
            assists=[
                AssistSuggestion(
                    hole_id=a["hole_id"],
                    suggestions=[a["suggestion"]],  # API returns singular 'suggestion'
                    context=a["description"],  # API uses 'description' for context
                )
                for a in data["assists"]
            ],
        )


@dataclass
class IRResponse:
    """Response containing finalized IR."""

    ir: dict[str, Any]
    metadata: dict[str, Any]


class SessionClient:
    """Client for interacting with lift-sys session management API.

    Supports both sync and async operations. Use async methods for
    concurrent operations or integration with async frameworks.

    Example (sync):
        >>> client = SessionClient("http://localhost:8000")
        >>> session = client.create_session(prompt="A function that adds two numbers")
        >>> print(session.session_id)

    Example (async):
        >>> client = SessionClient("http://localhost:8000")
        >>> session = await client.acreate_session(prompt="A function that adds")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        """Initialize session client.

        Args:
            base_url: Base URL of the lift-sys API
            headers: Optional headers to include in all requests
            timeout: Request timeout in seconds

        Note:
            Automatically detects demo mode from LIFT_SYS_ENABLE_DEMO_USER_HEADER
            environment variable and adds x-demo-user header if enabled.
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}

        # Auto-detect demo mode from environment variable
        if os.getenv("LIFT_SYS_ENABLE_DEMO_USER_HEADER") == "1":
            # Only add if not explicitly provided in headers
            if "x-demo-user" not in self.headers:
                demo_user = os.getenv("LIFT_SYS_DEMO_USER", "sdk-user")
                self.headers["x-demo-user"] = demo_user

        self.timeout = timeout

    # Synchronous methods

    def create_session(
        self,
        prompt: str | None = None,
        ir: dict[str, Any] | None = None,
        source: str = "prompt",
        metadata: dict[str, Any] | None = None,
    ) -> PromptSession:
        """Create a new prompt refinement session.

        Args:
            prompt: Natural language prompt to translate to IR
            ir: Existing IR to create session from
            source: Session source ("prompt" or "reverse_mode")
            metadata: Additional metadata to attach

        Returns:
            Created session

        Raises:
            httpx.HTTPError: If request fails
        """
        request = CreateSessionRequest(prompt=prompt, ir=ir, source=source, metadata=metadata)
        response = httpx.post(
            f"{self.base_url}/spec-sessions",
            json=request.to_dict(),
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PromptSession.from_dict(response.json())

    def list_sessions(self) -> SessionListResponse:
        """List all active sessions.

        Returns:
            List of sessions

        Raises:
            httpx.HTTPError: If request fails
        """
        response = httpx.get(
            f"{self.base_url}/spec-sessions",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return SessionListResponse.from_dict(response.json())

    def get_session(self, session_id: str) -> PromptSession:
        """Get details of a specific session.

        Args:
            session_id: Session identifier

        Returns:
            Session details

        Raises:
            httpx.HTTPError: If request fails or session not found
        """
        response = httpx.get(
            f"{self.base_url}/spec-sessions/{session_id}",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PromptSession.from_dict(response.json())

    def resolve_hole(
        self,
        session_id: str,
        hole_id: str,
        resolution_text: str,
        resolution_type: str = "clarify_intent",
    ) -> PromptSession:
        """Resolve a typed hole in a session.

        Args:
            session_id: Session identifier
            hole_id: Hole identifier to resolve
            resolution_text: Resolution text
            resolution_type: Type of resolution

        Returns:
            Updated session

        Raises:
            httpx.HTTPError: If request fails
        """
        request = ResolveHoleRequest(
            resolution_text=resolution_text, resolution_type=resolution_type
        )
        response = httpx.post(
            f"{self.base_url}/spec-sessions/{session_id}/holes/{hole_id}/resolve",
            json=request.to_dict(),
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return PromptSession.from_dict(response.json())

    def finalize_session(self, session_id: str) -> IRResponse:
        """Finalize a session and return the completed IR.

        Args:
            session_id: Session identifier

        Returns:
            Finalized IR and metadata

        Raises:
            httpx.HTTPError: If request fails or session has unresolved holes
        """
        response = httpx.post(
            f"{self.base_url}/spec-sessions/{session_id}/finalize",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return IRResponse(ir=data["ir"], metadata=data["metadata"])

    def get_assists(self, session_id: str) -> AssistsResponse:
        """Get actionable suggestions for resolving holes.

        Args:
            session_id: Session identifier

        Returns:
            Assist suggestions

        Raises:
            httpx.HTTPError: If request fails
        """
        response = httpx.get(
            f"{self.base_url}/spec-sessions/{session_id}/assists",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return AssistsResponse.from_dict(response.json())

    def delete_session(self, session_id: str) -> None:
        """Delete a session.

        Args:
            session_id: Session identifier

        Raises:
            httpx.HTTPError: If request fails
        """
        response = httpx.delete(
            f"{self.base_url}/spec-sessions/{session_id}",
            headers=self.headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

    # Asynchronous methods

    async def acreate_session(
        self,
        prompt: str | None = None,
        ir: dict[str, Any] | None = None,
        source: str = "prompt",
        metadata: dict[str, Any] | None = None,
    ) -> PromptSession:
        """Create a new prompt refinement session (async).

        Args:
            prompt: Natural language prompt to translate to IR
            ir: Existing IR to create session from
            source: Session source ("prompt" or "reverse_mode")
            metadata: Additional metadata to attach

        Returns:
            Created session

        Raises:
            httpx.HTTPError: If request fails
        """
        request = CreateSessionRequest(prompt=prompt, ir=ir, source=source, metadata=metadata)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/spec-sessions",
                json=request.to_dict(),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return PromptSession.from_dict(response.json())

    async def alist_sessions(self) -> SessionListResponse:
        """List all active sessions (async).

        Returns:
            List of sessions

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/spec-sessions",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return SessionListResponse.from_dict(response.json())

    async def aget_session(self, session_id: str) -> PromptSession:
        """Get details of a specific session (async).

        Args:
            session_id: Session identifier

        Returns:
            Session details

        Raises:
            httpx.HTTPError: If request fails or session not found
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/spec-sessions/{session_id}",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return PromptSession.from_dict(response.json())

    async def aresolve_hole(
        self,
        session_id: str,
        hole_id: str,
        resolution_text: str,
        resolution_type: str = "clarify_intent",
    ) -> PromptSession:
        """Resolve a typed hole in a session (async).

        Args:
            session_id: Session identifier
            hole_id: Hole identifier to resolve
            resolution_text: Resolution text
            resolution_type: Type of resolution

        Returns:
            Updated session

        Raises:
            httpx.HTTPError: If request fails
        """
        request = ResolveHoleRequest(
            resolution_text=resolution_text, resolution_type=resolution_type
        )
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/spec-sessions/{session_id}/holes/{hole_id}/resolve",
                json=request.to_dict(),
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return PromptSession.from_dict(response.json())

    async def afinalize_session(self, session_id: str) -> IRResponse:
        """Finalize a session and return the completed IR (async).

        Args:
            session_id: Session identifier

        Returns:
            Finalized IR and metadata

        Raises:
            httpx.HTTPError: If request fails or session has unresolved holes
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/spec-sessions/{session_id}/finalize",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return IRResponse(ir=data["ir"], metadata=data["metadata"])

    async def aget_assists(self, session_id: str) -> AssistsResponse:
        """Get actionable suggestions for resolving holes (async).

        Args:
            session_id: Session identifier

        Returns:
            Assist suggestions

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/spec-sessions/{session_id}/assists",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return AssistsResponse.from_dict(response.json())

    async def adelete_session(self, session_id: str) -> None:
        """Delete a session (async).

        Args:
            session_id: Session identifier

        Raises:
            httpx.HTTPError: If request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/spec-sessions/{session_id}",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
