"""Supabase storage backend for prompt sessions."""

from __future__ import annotations

import os
from typing import Any

from supabase import Client, create_client

from .models import HoleResolution, IRDraft, PromptRevision, PromptSession


class SupabaseSessionStore:
    """Supabase-backed storage implementation for PromptSessions.

    This implementation maps PromptSession data models to the Supabase database schema:
    - PromptSession → sessions table
    - PromptRevision → session_revisions table (via revisions list)
    - IRDraft → session_drafts table (via ir_drafts list)
    - HoleResolution → hole_resolutions table (via pending_resolutions list)

    The schema uses Row-Level Security (RLS) for multi-user isolation, with
    auth.uid() enforcement on all operations. For service-level operations,
    use the service_role key which bypasses RLS.
    """

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Initialize Supabase client.

        Args:
            url: Supabase project URL (defaults to SUPABASE_URL env var)
            key: Supabase API key (defaults to SUPABASE_SERVICE_KEY env var)
            user_id: User ID for RLS enforcement (required for user operations)
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be provided "
                "or set as environment variables"
            )

        self.client: Client = create_client(self.url, self.key)
        self.user_id = user_id

    def create(self, session: PromptSession) -> str:
        """Store a new session and return its ID.

        Stores the session in the sessions table, then stores all revisions,
        drafts, and resolutions in their respective tables.

        Args:
            session: PromptSession to store

        Returns:
            Session ID (UUID string)

        Raises:
            ValueError: If user_id not set
            Exception: If database operation fails
        """
        if not self.user_id:
            raise ValueError("user_id must be set to create sessions")

        # Store main session record
        session_data = {
            "id": session.session_id,
            "user_id": self.user_id,
            "status": session.status,
            "source": session.source,
            "original_input": self._get_original_input(session),
            "current_ir": self._serialize_current_draft(session),
            "revision_count": len(session.revisions),
            "draft_count": len(session.ir_drafts),
            "hole_count": len(session.pending_resolutions),
            "metadata": session.metadata,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

        self.client.table("sessions").insert(session_data).execute()

        # Store revisions
        for idx, revision in enumerate(session.revisions):
            self._store_revision(session.session_id, idx + 1, revision)

        # Store IR drafts
        for idx, draft in enumerate(session.ir_drafts):
            self._store_draft(session.session_id, idx + 1, draft)

        # Store pending resolutions
        for resolution in session.pending_resolutions:
            self._store_resolution(session.session_id, resolution)

        return session.session_id

    def get(self, session_id: str) -> PromptSession | None:
        """Retrieve a session by ID.

        Fetches the session from the sessions table, then fetches all associated
        revisions, drafts, and resolutions.

        Args:
            session_id: UUID of session to retrieve

        Returns:
            PromptSession if found, None otherwise
        """
        # Fetch main session record
        response = self.client.table("sessions").select("*").eq("id", session_id).execute()

        if not response.data:
            return None

        session_row = response.data[0]

        # Fetch revisions
        revisions_response = (
            self.client.table("session_revisions")
            .select("*")
            .eq("session_id", session_id)
            .order("revision_number")
            .execute()
        )

        revisions = [self._parse_revision(rev_row) for rev_row in revisions_response.data]

        # Fetch drafts
        drafts_response = (
            self.client.table("session_drafts")
            .select("*")
            .eq("session_id", session_id)
            .order("draft_number")
            .execute()
        )

        ir_drafts = [self._parse_draft(draft_row) for draft_row in drafts_response.data]

        # Fetch resolutions
        resolutions_response = (
            self.client.table("hole_resolutions")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at")
            .execute()
        )

        pending_resolutions = [
            self._parse_resolution(res_row) for res_row in resolutions_response.data
        ]

        # Reconstruct PromptSession
        session = PromptSession(
            session_id=session_row["id"],
            created_at=session_row["created_at"],
            updated_at=session_row["updated_at"],
            status=session_row["status"],
            revisions=revisions,
            ir_drafts=ir_drafts,
            current_draft=ir_drafts[-1] if ir_drafts else None,
            pending_resolutions=pending_resolutions,
            source=session_row["source"],
            metadata=session_row.get("metadata", {}),
        )

        return session

    def update(self, session: PromptSession) -> None:
        """Update an existing session.

        Updates the main session record and syncs all revisions, drafts, and
        resolutions. This is a full sync operation - existing records are kept
        but new ones are added.

        Args:
            session: PromptSession with updated data

        Raises:
            KeyError: If session not found in database
        """
        # Check if session exists
        existing = self.client.table("sessions").select("id").eq("id", session.session_id).execute()

        if not existing.data:
            raise KeyError(f"Session {session.session_id} not found")

        # Update main session record
        session_updates = {
            "status": session.status,
            "current_ir": self._serialize_current_draft(session),
            "revision_count": len(session.revisions),
            "draft_count": len(session.ir_drafts),
            "hole_count": len(session.pending_resolutions),
            "metadata": session.metadata,
            "updated_at": session.updated_at,
        }

        if session.status == "finalized":
            session_updates["finalized_at"] = session.updated_at

        self.client.table("sessions").update(session_updates).eq("id", session.session_id).execute()

        # Sync revisions (append new ones)
        existing_revisions = (
            self.client.table("session_revisions")
            .select("revision_number")
            .eq("session_id", session.session_id)
            .execute()
        )

        existing_count = len(existing_revisions.data)
        new_revisions = session.revisions[existing_count:]

        for idx, revision in enumerate(new_revisions, start=existing_count + 1):
            self._store_revision(session.session_id, idx, revision)

        # Sync drafts (append new ones)
        existing_drafts = (
            self.client.table("session_drafts")
            .select("draft_number")
            .eq("session_id", session.session_id)
            .execute()
        )

        existing_draft_count = len(existing_drafts.data)
        new_drafts = session.ir_drafts[existing_draft_count:]

        for idx, draft in enumerate(new_drafts, start=existing_draft_count + 1):
            self._store_draft(session.session_id, idx, draft)

        # Sync resolutions (append new ones)
        existing_resolutions = (
            self.client.table("hole_resolutions")
            .select("hole_id")
            .eq("session_id", session.session_id)
            .execute()
        )

        existing_hole_ids = {res["hole_id"] for res in existing_resolutions.data}

        for resolution in session.pending_resolutions:
            if resolution.hole_id not in existing_hole_ids:
                self._store_resolution(session.session_id, resolution)

    def list_active(self) -> list[PromptSession]:
        """List all active (non-finalized, non-abandoned) sessions.

        Returns:
            List of active PromptSessions (status='active')
        """
        if not self.user_id:
            raise ValueError("user_id must be set to list sessions")

        response = (
            self.client.table("sessions")
            .select("id")
            .eq("user_id", self.user_id)
            .eq("status", "active")
            .order("updated_at", desc=True)
            .execute()
        )

        return [self.get(row["id"]) for row in response.data if self.get(row["id"])]

    def list_all(self) -> list[PromptSession]:
        """List all sessions regardless of status.

        Returns:
            List of all PromptSessions for the current user
        """
        if not self.user_id:
            raise ValueError("user_id must be set to list sessions")

        response = (
            self.client.table("sessions")
            .select("id")
            .eq("user_id", self.user_id)
            .order("updated_at", desc=True)
            .execute()
        )

        return [self.get(row["id"]) for row in response.data if self.get(row["id"])]

    def delete(self, session_id: str) -> None:
        """Delete a session by ID.

        Deletes the session and all associated revisions, drafts, and resolutions
        via CASCADE foreign key constraints.

        Args:
            session_id: UUID of session to delete
        """
        self.client.table("sessions").delete().eq("id", session_id).execute()

    # Helper methods for serialization/deserialization

    def _get_original_input(self, session: PromptSession) -> str:
        """Extract original input from first revision or metadata."""
        if session.revisions:
            return session.revisions[0].content
        return session.metadata.get("original_input", "")

    def _serialize_current_draft(self, session: PromptSession) -> dict[str, Any] | None:
        """Serialize current draft IR to JSONB."""
        if not session.current_draft:
            return None
        return session.current_draft.to_dict()

    def _store_revision(
        self, session_id: str, revision_number: int, revision: PromptRevision
    ) -> None:
        """Store a single revision in session_revisions table."""
        revision_data = {
            "session_id": session_id,
            "revision_number": revision_number,
            "source": revision.revision_type,
            "content": revision.content,
            "target_hole": revision.target_hole,
            "metadata": revision.metadata,
            "created_at": revision.timestamp,
        }

        self.client.table("session_revisions").insert(revision_data).execute()

    def _store_draft(self, session_id: str, draft_number: int, draft: IRDraft) -> None:
        """Store a single IR draft in session_drafts table."""
        draft_data = {
            "session_id": session_id,
            "draft_number": draft_number,
            "ir_content": draft.to_dict(),
            "validation_status": draft.validation_status,
            "unresolved_holes": draft.ambiguities,
            "smt_results": draft.smt_results,
            "metadata": draft.metadata,
            "created_at": draft.created_at,
        }

        self.client.table("session_drafts").insert(draft_data).execute()

    def _store_resolution(self, session_id: str, resolution: HoleResolution) -> None:
        """Store a single hole resolution in hole_resolutions table."""
        resolution_data = {
            "session_id": session_id,
            "hole_id": resolution.hole_id,
            "hole_type": self._map_resolution_type(resolution.resolution_type),
            "resolution_method": "user_selection",  # From interactive prompt
            "resolved_value": {
                "text": resolution.resolution_text,
                "type": resolution.resolution_type,
                "applied": resolution.applied,
            },
            "metadata": resolution.metadata,
            "created_at": resolution.timestamp,
        }

        self.client.table("hole_resolutions").insert(resolution_data).execute()

    def _map_resolution_type(self, resolution_type: str) -> str:
        """Map PromptSession resolution type to database hole_type enum."""
        mapping = {
            "clarify_intent": "validation",
            "add_constraint": "constraint",
            "refine_signature": "type",
            "specify_effect": "parameter",
        }
        return mapping.get(resolution_type, "other")

    def _parse_revision(self, row: dict[str, Any]) -> PromptRevision:
        """Parse database row into PromptRevision."""
        return PromptRevision(
            timestamp=row["created_at"],
            content=row["content"],
            revision_type=row["source"],
            target_hole=row.get("target_hole"),
            metadata=row.get("metadata", {}),
        )

    def _parse_draft(self, row: dict[str, Any]) -> IRDraft:
        """Parse database row into IRDraft."""
        return IRDraft.from_dict(row["ir_content"])

    def _parse_resolution(self, row: dict[str, Any]) -> HoleResolution:
        """Parse database row into HoleResolution."""
        resolved_value = row["resolved_value"]
        return HoleResolution(
            hole_id=row["hole_id"],
            resolution_text=resolved_value.get("text", ""),
            resolution_type=resolved_value.get("type", "clarify_intent"),
            applied=resolved_value.get("applied", False),
            timestamp=row["created_at"],
            metadata=row.get("metadata", {}),
        )


__all__ = ["SupabaseSessionStore"]
