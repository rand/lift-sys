"""Storage backends for prompt sessions."""
from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from .models import PromptSession


class SessionStore(Protocol):
    """Protocol defining storage interface for PromptSessions."""

    def create(self, session: PromptSession) -> str:
        """Store a new session and return its ID."""
        ...

    def get(self, session_id: str) -> Optional[PromptSession]:
        """Retrieve a session by ID."""
        ...

    def update(self, session: PromptSession) -> None:
        """Update an existing session."""
        ...

    def list_active(self) -> List[PromptSession]:
        """List all active (non-finalized, non-abandoned) sessions."""
        ...

    def list_all(self) -> List[PromptSession]:
        """List all sessions regardless of status."""
        ...

    def delete(self, session_id: str) -> None:
        """Delete a session by ID."""
        ...


class InMemorySessionStore:
    """In-memory storage implementation for PromptSessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, PromptSession] = {}

    def create(self, session: PromptSession) -> str:
        """Store a new session and return its ID."""
        self._sessions[session.session_id] = session
        return session.session_id

    def get(self, session_id: str) -> Optional[PromptSession]:
        """Retrieve a session by ID."""
        return self._sessions.get(session_id)

    def update(self, session: PromptSession) -> None:
        """Update an existing session."""
        if session.session_id not in self._sessions:
            raise KeyError(f"Session {session.session_id} not found")
        self._sessions[session.session_id] = session

    def list_active(self) -> List[PromptSession]:
        """List all active (non-finalized, non-abandoned) sessions."""
        return [s for s in self._sessions.values() if s.status == "active"]

    def list_all(self) -> List[PromptSession]:
        """List all sessions regardless of status."""
        return list(self._sessions.values())

    def delete(self, session_id: str) -> None:
        """Delete a session by ID."""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def clear(self) -> None:
        """Clear all sessions (useful for testing)."""
        self._sessions.clear()


__all__ = ["SessionStore", "InMemorySessionStore"]
