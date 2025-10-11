"""Data models for prompt session management."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..ir.models import IntermediateRepresentation


@dataclass(slots=True)
class PromptRevision:
    """Single user input during refinement."""

    timestamp: str
    content: str  # Natural language text
    revision_type: str  # "initial" | "hole_fill" | "constraint_add" | "manual_edit"
    target_hole: Optional[str] = None  # Hole ID if this revision targets a specific hole
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "content": self.content,
            "revision_type": self.revision_type,
            "target_hole": self.target_hole,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptRevision:
        return cls(
            timestamp=data["timestamp"],
            content=data["content"],
            revision_type=data["revision_type"],
            target_hole=data.get("target_hole"),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class IRDraft:
    """Versioned IR snapshot."""

    version: int
    ir: IntermediateRepresentation
    validation_status: str  # "pending" | "valid" | "contradictory" | "incomplete"
    smt_results: List[Dict[str, Any]] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)  # Unresolved hole identifiers
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "ir": self.ir.to_dict(),
            "validation_status": self.validation_status,
            "smt_results": self.smt_results,
            "ambiguities": self.ambiguities,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IRDraft:
        return cls(
            version=data["version"],
            ir=IntermediateRepresentation.from_dict(data["ir"]),
            validation_status=data["validation_status"],
            smt_results=data.get("smt_results", []),
            ambiguities=data.get("ambiguities", []),
            created_at=data.get("created_at", datetime.utcnow().isoformat() + "Z"),
            metadata=data.get("metadata", {}),
        )

    def get_unresolved_holes(self) -> List[str]:
        """Return list of hole identifiers that still need resolution."""
        all_holes = self.ir.typed_holes()
        return [hole.identifier for hole in all_holes]


@dataclass(slots=True)
class HoleResolution:
    """User's clarification for a typed hole."""

    hole_id: str
    resolution_text: str
    resolution_type: str  # "clarify_intent" | "add_constraint" | "refine_signature" | "specify_effect"
    applied: bool = False
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hole_id": self.hole_id,
            "resolution_text": self.resolution_text,
            "resolution_type": self.resolution_type,
            "applied": self.applied,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HoleResolution:
        return cls(
            hole_id=data["hole_id"],
            resolution_text=data["resolution_text"],
            resolution_type=data["resolution_type"],
            applied=data.get("applied", False),
            timestamp=data.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class PromptSession:
    """Full refinement session state."""

    session_id: str
    created_at: str
    updated_at: str
    status: str  # "active" | "finalized" | "abandoned"

    # Revision history
    revisions: List[PromptRevision] = field(default_factory=list)
    ir_drafts: List[IRDraft] = field(default_factory=list)

    # Current state
    current_draft: Optional[IRDraft] = None
    pending_resolutions: List[HoleResolution] = field(default_factory=list)

    # Metadata
    source: str = "prompt"  # "prompt" | "reverse_mode"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_new(
        cls,
        source: str = "prompt",
        initial_draft: Optional[IRDraft] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PromptSession:
        """Factory method to create a new session with proper defaults."""
        now = datetime.utcnow().isoformat() + "Z"
        session = cls(
            session_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            status="active",
            source=source,
            metadata=metadata or {},
        )

        if initial_draft:
            session.ir_drafts.append(initial_draft)
            session.current_draft = initial_draft

        return session

    def add_revision(self, revision: PromptRevision) -> None:
        """Add a new revision and update timestamps."""
        self.revisions.append(revision)
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def add_draft(self, draft: IRDraft) -> None:
        """Add a new IR draft and set as current."""
        self.ir_drafts.append(draft)
        self.current_draft = draft
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def add_resolution(self, resolution: HoleResolution) -> None:
        """Add a pending hole resolution."""
        self.pending_resolutions.append(resolution)
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def mark_resolution_applied(self, hole_id: str) -> None:
        """Mark a resolution as applied."""
        for resolution in self.pending_resolutions:
            if resolution.hole_id == hole_id and not resolution.applied:
                resolution.applied = True
                break
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def finalize(self) -> None:
        """Mark session as finalized."""
        self.status = "finalized"
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def abandon(self) -> None:
        """Mark session as abandoned."""
        self.status = "abandoned"
        self.updated_at = datetime.utcnow().isoformat() + "Z"

    def get_unresolved_holes(self) -> List[str]:
        """Get list of hole IDs that still need resolution."""
        if not self.current_draft:
            return []
        return self.current_draft.get_unresolved_holes()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "revisions": [r.to_dict() for r in self.revisions],
            "ir_drafts": [d.to_dict() for d in self.ir_drafts],
            "current_draft": self.current_draft.to_dict() if self.current_draft else None,
            "pending_resolutions": [r.to_dict() for r in self.pending_resolutions],
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptSession:
        session = cls(
            session_id=data["session_id"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            status=data["status"],
            revisions=[PromptRevision.from_dict(r) for r in data.get("revisions", [])],
            ir_drafts=[IRDraft.from_dict(d) for d in data.get("ir_drafts", [])],
            current_draft=IRDraft.from_dict(data["current_draft"]) if data.get("current_draft") else None,
            pending_resolutions=[HoleResolution.from_dict(r) for r in data.get("pending_resolutions", [])],
            source=data.get("source", "prompt"),
            metadata=data.get("metadata", {}),
        )
        return session


__all__ = ["PromptSession", "PromptRevision", "IRDraft", "HoleResolution"]
