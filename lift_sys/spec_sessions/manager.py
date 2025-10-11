"""Session manager for orchestrating prompt refinement workflows."""
from __future__ import annotations

from typing import Dict, List, Optional

from ..ir.models import IntermediateRepresentation
from ..planner.planner import Planner
from ..verifier.smt_checker import SMTChecker
from .models import HoleResolution, IRDraft, PromptRevision, PromptSession
from .storage import SessionStore
from .translator import PromptToIRTranslator


class SpecSessionManager:
    """Orchestrates the full lifecycle of prompt sessions."""

    def __init__(
        self,
        store: SessionStore,
        translator: PromptToIRTranslator,
        planner: Planner,
        verifier: Optional[SMTChecker] = None,
    ):
        self.store = store
        self.translator = translator
        self.planner = planner
        self.verifier = verifier or SMTChecker()

    def create_from_prompt(
        self,
        prompt: str,
        metadata: Optional[Dict] = None,
    ) -> PromptSession:
        """
        Create a new session from a natural language prompt.

        Args:
            prompt: Natural language description of desired functionality
            metadata: Optional metadata to attach

        Returns:
            PromptSession with initial IR draft and detected ambiguities
        """
        # Translate prompt to IR
        draft = self.translator.translate(prompt, metadata=metadata)

        # Create revision record
        revision = PromptRevision.from_dict({
            "timestamp": draft.created_at,
            "content": prompt,
            "revision_type": "initial",
        })

        # Create session
        session = PromptSession.create_new(
            source="prompt",
            initial_draft=draft,
            metadata=metadata,
        )
        session.add_revision(revision)

        # Store session
        self.store.create(session)

        # Load into planner
        self.planner.load_ir(draft.ir)
        self.planner.current_session = session

        return session

    def create_from_reverse_mode(
        self,
        ir: IntermediateRepresentation,
        metadata: Optional[Dict] = None,
    ) -> PromptSession:
        """
        Create a session from a reverse-mode lifted IR.

        Args:
            ir: IR from reverse mode lifting
            metadata: Optional metadata

        Returns:
            PromptSession initialized with the lifted IR
        """
        # Detect any ambiguities in the lifted IR
        holes = self.translator._detect_ambiguities(ir, ir.intent.summary)
        ir = self.translator._inject_holes(ir, holes)

        # Create draft
        draft = IRDraft(
            version=1,
            ir=ir,
            validation_status="incomplete" if holes else "pending",
            ambiguities=[h.identifier for h in holes],
            metadata=metadata or {},
        )

        # Create session
        session = PromptSession.create_new(
            source="reverse_mode",
            initial_draft=draft,
            metadata=metadata,
        )

        # Store session
        self.store.create(session)

        # Load into planner
        self.planner.load_ir(draft.ir)
        self.planner.current_session = session

        return session

    def get_session(self, session_id: str) -> Optional[PromptSession]:
        """Retrieve a session by ID."""
        return self.store.get(session_id)

    def list_active_sessions(self) -> List[PromptSession]:
        """List all active sessions."""
        return self.store.list_active()

    def apply_resolution(
        self,
        session_id: str,
        hole_id: str,
        resolution_text: str,
        resolution_type: str,
    ) -> PromptSession:
        """
        Apply a hole resolution to a session.

        Args:
            session_id: Session to update
            hole_id: Hole to resolve
            resolution_text: User-provided resolution
            resolution_type: Type of resolution

        Returns:
            Updated session with new draft

        Raises:
            ValueError: If session not found or hole invalid
        """
        session = self.store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.current_draft:
            raise ValueError("Session has no current draft")

        # Create resolution record
        resolution = HoleResolution(
            hole_id=hole_id,
            resolution_text=resolution_text,
            resolution_type=resolution_type,
        )
        session.add_resolution(resolution)

        # Create revision record
        revision = PromptRevision.from_dict({
            "timestamp": resolution.timestamp,
            "content": resolution_text,
            "revision_type": "hole_fill",
            "target_hole": hole_id,
        })
        session.add_revision(revision)

        # Apply resolution to create new draft
        new_draft = self.translator.fill_hole(
            session.current_draft,
            hole_id,
            resolution_text,
        )

        # Verify with SMT if assertions present
        if new_draft.ir.assertions:
            smt_results = self._verify_assertions(new_draft.ir)
            new_draft.smt_results = smt_results

            # Check for contradictions
            if any(result.get("status") == "unsat" for result in smt_results):
                new_draft.validation_status = "contradictory"
            elif new_draft.ambiguities:
                new_draft.validation_status = "incomplete"
            else:
                new_draft.validation_status = "valid"

        # Add new draft to session
        session.add_draft(new_draft)
        session.mark_resolution_applied(hole_id)

        # Update storage
        self.store.update(session)

        # Update planner
        self.planner.load_ir(new_draft.ir)
        self.planner.current_session = session

        return session

    def finalize(self, session_id: str) -> IntermediateRepresentation:
        """
        Finalize a session and return the completed IR.

        Args:
            session_id: Session to finalize

        Returns:
            Final validated IR

        Raises:
            ValueError: If session has unresolved holes or contradictions
        """
        session = self.store.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        if not session.current_draft:
            raise ValueError("Session has no current draft")

        draft = session.current_draft

        # Check for unresolved holes
        if draft.ambiguities:
            raise ValueError(
                f"Cannot finalize: {len(draft.ambiguities)} unresolved holes remaining"
            )

        # Check for contradictions
        if draft.validation_status == "contradictory":
            raise ValueError("Cannot finalize: IR contains contradictory assertions")

        # Final SMT verification
        if draft.ir.assertions:
            smt_results = self._verify_assertions(draft.ir)
            if any(result.get("status") == "unsat" for result in smt_results):
                raise ValueError("Cannot finalize: SMT verification failed")

        # Mark session as finalized
        session.finalize()
        self.store.update(session)

        return draft.ir

    def get_assists(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get actionable suggestions for resolving holes.

        Args:
            session_id: Session to get assists for

        Returns:
            List of assists with target hole and suggestion message
        """
        session = self.store.get(session_id)
        if not session or not session.current_draft:
            return []

        assists = []
        for hole in session.current_draft.ir.typed_holes():
            # Generate context-aware suggestions
            suggestion = self._generate_suggestion(hole, session.current_draft.ir)
            assists.append({
                "hole_id": hole.identifier,
                "hole_kind": hole.kind.value,
                "suggestion": suggestion,
                "description": hole.description,
            })

        return assists

    def _verify_assertions(self, ir: IntermediateRepresentation) -> List[Dict]:
        """Verify IR assertions using SMT checker."""
        results = []
        for assertion in ir.assertions:
            result = self.verifier.verify(assertion.predicate)
            results.append({
                "predicate": assertion.predicate,
                "status": result.status,
                "model": result.model if hasattr(result, "model") else None,
            })
        return results

    def _generate_suggestion(self, hole, ir: IntermediateRepresentation) -> str:
        """Generate context-aware suggestion for a hole."""
        from ..ir.models import HoleKind

        if hole.kind == HoleKind.INTENT:
            return f"Provide more details about the purpose: {hole.description}"

        elif hole.kind == HoleKind.SIGNATURE:
            if "type" in hole.identifier:
                param_name = hole.identifier.replace("_type", "")
                return f"Specify the type for parameter '{param_name}' (e.g., int, str, List[int])"
            elif hole.identifier == "return_type":
                return "Specify what this function returns (e.g., int, str, None)"
            return f"Clarify signature detail: {hole.description}"

        elif hole.kind == HoleKind.EFFECT:
            return f"Describe the side effect or external interaction: {hole.description}"

        elif hole.kind == HoleKind.ASSERTION:
            # Check for numeric parameters
            numeric_params = [
                p.name for p in ir.signature.parameters
                if p.type_hint in ["int", "float", "number"]
            ]
            if numeric_params:
                examples = ", ".join(f"{p} > 0" for p in numeric_params[:2])
                return f"Add constraints on inputs. Examples: {examples}"
            return f"Add logical constraint: {hole.description}"

        return hole.description or "Resolve this ambiguity"

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        self.store.delete(session_id)


__all__ = ["SpecSessionManager"]
