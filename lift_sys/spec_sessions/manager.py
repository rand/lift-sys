"""Session manager for orchestrating prompt refinement workflows."""

from __future__ import annotations

from ..ir.models import (
    AssertClause,
    EffectClause,
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    SigClause,
    TypedHole,
)
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
        verifier: SMTChecker | None = None,
    ):
        self.store = store
        self.translator = translator
        self.planner = planner
        self.verifier = verifier or SMTChecker()

    def create_from_prompt(
        self,
        prompt: str,
        metadata: dict | None = None,
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
        revision = PromptRevision.from_dict(
            {
                "timestamp": draft.created_at,
                "content": prompt,
                "revision_type": "initial",
            }
        )

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
        metadata: dict | None = None,
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

    def create_from_reverse_mode_enhanced(
        self,
        ir: IntermediateRepresentation,
        improvement_holes: list[TypedHole],
        metadata: dict | None = None,
    ) -> PromptSession:
        """
        Create session from reverse IR with improvement detection.

        This enhanced version accepts pre-detected improvement opportunities
        from the ImprovementDetector and injects them as typed holes into
        the appropriate IR sections.

        Args:
            ir: Reverse-extracted IR with evidence
            improvement_holes: Pre-detected improvement opportunities
            metadata: Additional metadata

        Returns:
            PromptSession ready for refinement with improvement holes
        """
        # Inject improvement holes into IR
        ir_with_holes = self._inject_improvement_holes(ir, improvement_holes)

        # Build comprehensive metadata
        draft_metadata = {
            "reverse_analysis": {
                "source_file": ir.metadata.source_path if ir.metadata else "unknown",
                "language": ir.metadata.language if ir.metadata else "unknown",
                "evidence_count": len(ir.metadata.evidence) if ir.metadata else 0,
            },
            "improvements_detected": {
                "total": len(improvement_holes),
                "by_priority": self._count_by_priority(improvement_holes),
                "by_kind": self._count_by_kind(improvement_holes),
            },
        }
        if metadata:
            draft_metadata.update(metadata)

        # Preserve original evidence
        if ir.metadata and ir.metadata.evidence:
            draft_metadata["original_evidence"] = ir.metadata.evidence

        # Create draft
        draft = IRDraft(
            version=1,
            ir=ir_with_holes,
            validation_status="incomplete" if improvement_holes else "pending",
            ambiguities=[h.identifier for h in improvement_holes],
            metadata=draft_metadata,
        )

        # Create session
        session = PromptSession.create_new(
            source="reverse_mode",
            initial_draft=draft,
            metadata=metadata or {},
        )

        # Store and load into planner
        self.store.create(session)
        self.planner.load_ir(draft.ir)
        self.planner.current_session = session

        return session

    def _inject_improvement_holes(
        self,
        ir: IntermediateRepresentation,
        holes: list[TypedHole],
    ) -> IntermediateRepresentation:
        """
        Inject typed holes into appropriate IR sections.

        Groups holes by kind and injects them into the corresponding
        IR clause (intent, signature, effects, assertions).
        """
        # Group holes by kind
        intent_holes = [h for h in holes if h.kind == HoleKind.INTENT]
        signature_holes = [h for h in holes if h.kind == HoleKind.SIGNATURE]
        assertion_holes = [h for h in holes if h.kind == HoleKind.ASSERTION]
        effect_holes = [h for h in holes if h.kind == HoleKind.EFFECT]

        # Create new clauses with holes injected
        new_intent = IntentClause(
            summary=ir.intent.summary,
            rationale=ir.intent.rationale,
            holes=ir.intent.holes + intent_holes,
        )

        new_signature = SigClause(
            name=ir.signature.name,
            parameters=ir.signature.parameters,
            returns=ir.signature.returns,
            holes=ir.signature.holes + signature_holes,
        )

        # For effects and assertions, we need to append holes to existing clauses
        # or create new clauses if none exist
        new_effects = list(ir.effects)  # Copy list
        new_assertions = list(ir.assertions)  # Copy list

        # If there are effect holes, add them to the first effect clause
        # or create a new effect clause with the holes
        if effect_holes:
            if new_effects:
                # Add holes to first effect
                first_effect = new_effects[0]
                new_effects[0] = EffectClause(
                    description=first_effect.description,
                    holes=first_effect.holes + effect_holes,
                )
            else:
                # Create new effect clause with holes
                new_effects.append(
                    EffectClause(
                        description="[Improvement areas detected]",
                        holes=effect_holes,
                    )
                )

        # If there are assertion holes, add them to the first assertion clause
        # or create a new assertion clause with the holes
        if assertion_holes:
            if new_assertions:
                # Add holes to first assertion
                first_assertion = new_assertions[0]
                new_assertions[0] = AssertClause(
                    predicate=first_assertion.predicate,
                    rationale=first_assertion.rationale,
                    holes=first_assertion.holes + assertion_holes,
                )
            else:
                # Create new assertion clause with holes
                new_assertions.append(
                    AssertClause(
                        predicate="[Improvement areas detected]",
                        holes=assertion_holes,
                    )
                )

        # Reconstruct IR with injected holes
        return IntermediateRepresentation(
            intent=new_intent,
            signature=new_signature,
            effects=new_effects,
            assertions=new_assertions,
            metadata=ir.metadata,
        )

    def _count_by_priority(self, holes: list[TypedHole]) -> dict[str, int]:
        """Count holes by priority level."""
        priority_map = {}
        for hole in holes:
            priority = (
                hole.constraints.get("priority", "unknown") if hole.constraints else "unknown"
            )
            priority_map[priority] = priority_map.get(priority, 0) + 1
        return priority_map

    def _count_by_kind(self, holes: list[TypedHole]) -> dict[str, int]:
        """Count holes by kind."""
        kind_map = {}
        for hole in holes:
            kind = hole.kind.value if hole.kind else "unknown"
            kind_map[kind] = kind_map.get(kind, 0) + 1
        return kind_map

    def get_session(self, session_id: str) -> PromptSession | None:
        """Retrieve a session by ID."""
        return self.store.get(session_id)

    def list_active_sessions(self) -> list[PromptSession]:
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
        revision = PromptRevision.from_dict(
            {
                "timestamp": resolution.timestamp,
                "content": resolution_text,
                "revision_type": "hole_fill",
                "target_hole": hole_id,
            }
        )
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

    def get_assists(self, session_id: str) -> list[dict[str, str]]:
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
            assists.append(
                {
                    "hole_id": hole.identifier,
                    "hole_kind": hole.kind.value,
                    "suggestion": suggestion,
                    "description": hole.description,
                }
            )

        return assists

    def _verify_assertions(self, ir: IntermediateRepresentation) -> list[dict]:
        """Verify IR assertions using SMT checker."""
        results = []
        for assertion in ir.assertions:
            result = self.verifier.verify(assertion.predicate)
            results.append(
                {
                    "predicate": assertion.predicate,
                    "status": result.status,
                    "model": result.model if hasattr(result, "model") else None,
                }
            )
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
                p.name for p in ir.signature.parameters if p.type_hint in ["int", "float", "number"]
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
