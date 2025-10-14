"""IR three-way merge operations.

This module provides three-way merge functionality for IntermediateRepresentations,
enabling collaborative workflows with automatic conflict detection and resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .differ import DiffCategory, DiffKind, IRComparer
from .models import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    Provenance,
    SigClause,
)


class MergeStrategy(str, Enum):
    """Strategy for resolving merge conflicts."""

    AUTO = "auto"  # Auto-merge where safe, mark conflicts otherwise
    OURS = "ours"  # Always prefer our changes
    THEIRS = "theirs"  # Always prefer their changes
    BASE = "base"  # Keep base value
    MANUAL = "manual"  # All conflicts require manual resolution


class ConflictResolution(str, Enum):
    """How a conflict was resolved."""

    AUTO_MERGED = "auto_merged"  # Successfully auto-merged
    TOOK_OURS = "took_ours"  # Used our version
    TOOK_THEIRS = "took_theirs"  # Used their version
    KEPT_BASE = "kept_base"  # Kept base version
    MANUAL_REQUIRED = "manual_required"  # Needs manual resolution


@dataclass
class MergeConflict:
    """Represents a merge conflict between two versions."""

    category: DiffCategory
    """Category of the conflict (intent, signature, etc.)."""

    kind: DiffKind
    """Specific type of conflict."""

    path: str
    """Path to the conflicting element."""

    base_value: Any
    """Value from base/common ancestor."""

    ours_value: Any
    """Value from our branch."""

    theirs_value: Any
    """Value from their branch."""

    resolution: ConflictResolution | None = None
    """How this conflict was resolved (if resolved)."""

    resolved_value: Any = None
    """The value chosen to resolve the conflict."""

    message: str | None = None
    """Human-readable description of the conflict."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "kind": self.kind.value,
            "path": self.path,
            "base_value": self.base_value,
            "ours_value": self.ours_value,
            "theirs_value": self.theirs_value,
            "resolution": self.resolution.value if self.resolution else None,
            "resolved_value": self.resolved_value,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeConflict:
        """Deserialize from dictionary."""
        return cls(
            category=DiffCategory(data["category"]),
            kind=DiffKind(data["kind"]),
            path=data["path"],
            base_value=data["base_value"],
            ours_value=data["ours_value"],
            theirs_value=data["theirs_value"],
            resolution=ConflictResolution(data["resolution"]) if data.get("resolution") else None,
            resolved_value=data.get("resolved_value"),
            message=data.get("message"),
        )


@dataclass
class MergeResult:
    """Result of a three-way merge operation."""

    merged_ir: IntermediateRepresentation
    """The merged IR (may contain conflict markers if not fully resolved)."""

    conflicts: list[MergeConflict] = field(default_factory=list)
    """All conflicts encountered during merge."""

    auto_merged_count: int = 0
    """Number of changes that were auto-merged successfully."""

    has_conflicts: bool = False
    """Whether there are unresolved conflicts."""

    strategy: MergeStrategy = MergeStrategy.AUTO
    """The merge strategy that was used."""

    def unresolved_conflicts(self) -> list[MergeConflict]:
        """Get list of conflicts that still need resolution."""
        return [c for c in self.conflicts if c.resolution == ConflictResolution.MANUAL_REQUIRED]

    def is_clean_merge(self) -> bool:
        """Check if merge completed without any conflicts."""
        return not self.has_conflicts and len(self.unresolved_conflicts()) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "merged_ir": self.merged_ir.to_dict(),
            "conflicts": [c.to_dict() for c in self.conflicts],
            "auto_merged_count": self.auto_merged_count,
            "has_conflicts": self.has_conflicts,
            "strategy": self.strategy.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeResult:
        """Deserialize from dictionary."""
        return cls(
            merged_ir=IntermediateRepresentation.from_dict(data["merged_ir"]),
            conflicts=[MergeConflict.from_dict(c) for c in data.get("conflicts", [])],
            auto_merged_count=data.get("auto_merged_count", 0),
            has_conflicts=data.get("has_conflicts", False),
            strategy=MergeStrategy(data.get("strategy", MergeStrategy.AUTO.value)),
        )


class IRMerger:
    """Performs three-way merge of IntermediateRepresentations."""

    def __init__(self, strategy: MergeStrategy = MergeStrategy.AUTO):
        """
        Initialize the merger with a merge strategy.

        Args:
            strategy: Strategy for resolving conflicts.
        """
        self.strategy = strategy
        self.comparer = IRComparer()

    def merge(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        strategy: MergeStrategy | None = None,
    ) -> MergeResult:
        """
        Perform three-way merge of IRs.

        Args:
            base: Common ancestor version.
            ours: Our branch's version.
            theirs: Their branch's version.
            strategy: Override the default merge strategy for this operation.

        Returns:
            MergeResult with merged IR and any conflicts.
        """
        merge_strategy = strategy or self.strategy

        # Compare base with both branches
        base_to_ours = self.comparer.compare(base, ours)
        base_to_theirs = self.comparer.compare(base, theirs)

        conflicts = []
        auto_merged = 0

        # Merge each category
        merged_intent, intent_conflicts, intent_auto = self._merge_intent(
            base, ours, theirs, base_to_ours, base_to_theirs, merge_strategy
        )
        conflicts.extend(intent_conflicts)
        auto_merged += intent_auto

        merged_signature, sig_conflicts, sig_auto = self._merge_signature(
            base, ours, theirs, base_to_ours, base_to_theirs, merge_strategy
        )
        conflicts.extend(sig_conflicts)
        auto_merged += sig_auto

        merged_assertions, assert_conflicts, assert_auto = self._merge_assertions(
            base, ours, theirs, merge_strategy
        )
        conflicts.extend(assert_conflicts)
        auto_merged += assert_auto

        merged_effects, effect_conflicts, effect_auto = self._merge_effects(
            base, ours, theirs, merge_strategy
        )
        conflicts.extend(effect_conflicts)
        auto_merged += effect_auto

        merged_metadata, meta_conflicts, meta_auto = self._merge_metadata(
            base, ours, theirs, base_to_ours, base_to_theirs, merge_strategy
        )
        conflicts.extend(meta_conflicts)
        auto_merged += meta_auto

        # Build merged IR
        merged_ir = IntermediateRepresentation(
            intent=merged_intent,
            signature=merged_signature,
            effects=merged_effects,
            assertions=merged_assertions,
            metadata=merged_metadata,
        )

        # Determine if there are unresolved conflicts
        has_conflicts = any(c.resolution == ConflictResolution.MANUAL_REQUIRED for c in conflicts)

        return MergeResult(
            merged_ir=merged_ir,
            conflicts=conflicts,
            auto_merged_count=auto_merged,
            has_conflicts=has_conflicts,
            strategy=merge_strategy,
        )

    def _merge_intent(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        base_to_ours,
        base_to_theirs,
        strategy: MergeStrategy,
    ) -> tuple[IntentClause, list[MergeConflict], int]:
        """Merge intent clauses."""
        conflicts = []
        auto_merged = 0

        # Merge summary
        summary, summary_conflict, summary_auto = self._merge_field(
            "intent.summary",
            DiffCategory.INTENT,
            DiffKind.INTENT_SUMMARY,
            base.intent.summary,
            ours.intent.summary,
            theirs.intent.summary,
            strategy,
        )
        if summary_conflict:
            conflicts.append(summary_conflict)
        auto_merged += summary_auto

        # Merge rationale
        rationale, rationale_conflict, rationale_auto = self._merge_field(
            "intent.rationale",
            DiffCategory.INTENT,
            DiffKind.INTENT_RATIONALE,
            base.intent.rationale,
            ours.intent.rationale,
            theirs.intent.rationale,
            strategy,
        )
        if rationale_conflict:
            conflicts.append(rationale_conflict)
        auto_merged += rationale_auto

        # Merge holes (union of both)
        merged_holes = list(ours.intent.holes)
        for hole in theirs.intent.holes:
            if hole.identifier not in [h.identifier for h in merged_holes]:
                merged_holes.append(hole)

        # Merge provenance
        merged_provenance = self._merge_provenance(
            base.intent.provenance,
            ours.intent.provenance,
            theirs.intent.provenance,
            strategy,
        )

        return (
            IntentClause(
                summary=summary,
                rationale=rationale,
                holes=merged_holes,
                provenance=merged_provenance,
            ),
            conflicts,
            auto_merged,
        )

    def _merge_signature(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        base_to_ours,
        base_to_theirs,
        strategy: MergeStrategy,
    ) -> tuple[SigClause, list[MergeConflict], int]:
        """Merge signature clauses."""
        conflicts = []
        auto_merged = 0

        # Merge function name
        name, name_conflict, name_auto = self._merge_field(
            "signature.name",
            DiffCategory.SIGNATURE,
            DiffKind.SIGNATURE_NAME,
            base.signature.name,
            ours.signature.name,
            theirs.signature.name,
            strategy,
        )
        if name_conflict:
            conflicts.append(name_conflict)
        auto_merged += name_auto

        # Merge return type
        returns, returns_conflict, returns_auto = self._merge_field(
            "signature.returns",
            DiffCategory.SIGNATURE,
            DiffKind.RETURN_TYPE,
            base.signature.returns,
            ours.signature.returns,
            theirs.signature.returns,
            strategy,
        )
        if returns_conflict:
            conflicts.append(returns_conflict)
        auto_merged += returns_auto

        # Merge parameters (more complex - need positional matching)
        merged_params, param_conflicts, param_auto = self._merge_parameters(
            base.signature.parameters,
            ours.signature.parameters,
            theirs.signature.parameters,
            strategy,
        )
        conflicts.extend(param_conflicts)
        auto_merged += param_auto

        # Merge holes
        merged_holes = list(ours.signature.holes)
        for hole in theirs.signature.holes:
            if hole.identifier not in [h.identifier for h in merged_holes]:
                merged_holes.append(hole)

        # Merge provenance
        merged_provenance = self._merge_provenance(
            base.signature.provenance,
            ours.signature.provenance,
            theirs.signature.provenance,
            strategy,
        )

        return (
            SigClause(
                name=name,
                parameters=merged_params,
                returns=returns,
                holes=merged_holes,
                provenance=merged_provenance,
            ),
            conflicts,
            auto_merged,
        )

    def _merge_parameters(
        self,
        base_params: list[Parameter],
        ours_params: list[Parameter],
        theirs_params: list[Parameter],
        strategy: MergeStrategy,
    ) -> tuple[list[Parameter], list[MergeConflict], int]:
        """Merge parameter lists."""
        conflicts = []
        auto_merged = 0

        # If lengths differ, this is a conflict
        if len(ours_params) != len(theirs_params):
            conflict = MergeConflict(
                category=DiffCategory.SIGNATURE,
                kind=DiffKind.PARAMETER_COUNT,
                path="signature.parameters",
                base_value=len(base_params),
                ours_value=len(ours_params),
                theirs_value=len(theirs_params),
                message="Parameter count differs between branches",
            )

            if strategy == MergeStrategy.OURS:
                conflict.resolution = ConflictResolution.TOOK_OURS
                conflict.resolved_value = ours_params
                conflicts.append(conflict)
                return list(ours_params), conflicts, 0
            elif strategy == MergeStrategy.THEIRS:
                conflict.resolution = ConflictResolution.TOOK_THEIRS
                conflict.resolved_value = theirs_params
                conflicts.append(conflict)
                return list(theirs_params), conflicts, 0
            elif strategy == MergeStrategy.BASE:
                conflict.resolution = ConflictResolution.KEPT_BASE
                conflict.resolved_value = base_params
                conflicts.append(conflict)
                return list(base_params), conflicts, 0
            else:
                # AUTO or MANUAL - mark as requiring resolution
                conflict.resolution = ConflictResolution.MANUAL_REQUIRED
                conflicts.append(conflict)
                # Return ours as placeholder
                return list(ours_params), conflicts, 0

        # Same length - merge each parameter
        merged_params = []
        for i, (base_p, ours_p, theirs_p) in enumerate(
            zip(base_params, ours_params, theirs_params, strict=False)
        ):
            # Merge parameter name
            name, name_conflict, name_auto = self._merge_field(
                f"signature.parameters[{i}].name",
                DiffCategory.SIGNATURE,
                DiffKind.PARAMETER_NAME,
                base_p.name,
                ours_p.name,
                theirs_p.name,
                strategy,
            )
            if name_conflict:
                conflicts.append(name_conflict)
            auto_merged += name_auto

            # Merge parameter type
            type_hint, type_conflict, type_auto = self._merge_field(
                f"signature.parameters[{i}].type_hint",
                DiffCategory.SIGNATURE,
                DiffKind.PARAMETER_TYPE,
                base_p.type_hint,
                ours_p.type_hint,
                theirs_p.type_hint,
                strategy,
            )
            if type_conflict:
                conflicts.append(type_conflict)
            auto_merged += type_auto

            # Merge parameter description
            description, desc_conflict, desc_auto = self._merge_field(
                f"signature.parameters[{i}].description",
                DiffCategory.SIGNATURE,
                DiffKind.PARAMETER_DESCRIPTION,
                base_p.description,
                ours_p.description,
                theirs_p.description,
                strategy,
            )
            if desc_conflict:
                conflicts.append(desc_conflict)
            auto_merged += desc_auto

            # Merge parameter provenance
            param_provenance = self._merge_provenance(
                base_p.provenance,
                ours_p.provenance,
                theirs_p.provenance,
                strategy,
            )

            merged_params.append(
                Parameter(
                    name=name,
                    type_hint=type_hint,
                    description=description,
                    provenance=param_provenance,
                )
            )

        return merged_params, conflicts, auto_merged

    def _merge_assertions(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        strategy: MergeStrategy,
    ) -> tuple[list[AssertClause], list[MergeConflict], int]:
        """Merge assertion lists."""
        # For lists like assertions, we use set-based merging
        # Union of both sets, preserving order where possible
        base_predicates = {a.predicate for a in base.assertions}
        ours_predicates = {a.predicate for a in ours.assertions}
        theirs_predicates = {a.predicate for a in theirs.assertions}

        # Added in ours
        ours_added = ours_predicates - base_predicates
        # Added in theirs
        theirs_added = theirs_predicates - base_predicates
        # Removed in ours
        ours_removed = base_predicates - ours_predicates
        # Removed in theirs
        theirs_removed = base_predicates - theirs_predicates

        # Start with base
        merged = list(base.assertions)

        # Remove items deleted in both branches
        both_removed = ours_removed & theirs_removed
        merged = [a for a in merged if a.predicate not in both_removed]

        # Handle conflicts where one added and other removed
        conflicts = []
        conflict_predicates = (ours_removed & theirs_added) | (theirs_removed & ours_added)
        for pred in conflict_predicates:
            conflict = MergeConflict(
                category=DiffCategory.ASSERTION,
                kind=DiffKind.ASSERTION_PREDICATE,
                path=f"assertions[predicate={pred}]",
                base_value=pred in base_predicates,
                ours_value=pred in ours_predicates,
                theirs_value=pred in theirs_predicates,
                message=f"Assertion '{pred}' modified differently in each branch",
            )

            if strategy == MergeStrategy.OURS:
                conflict.resolution = ConflictResolution.TOOK_OURS
                if pred in ours_predicates:
                    # Keep/add from ours
                    assertion = next(a for a in ours.assertions if a.predicate == pred)
                    if assertion not in merged:
                        merged.append(assertion)
                else:
                    # Remove
                    merged = [a for a in merged if a.predicate != pred]
            elif strategy == MergeStrategy.THEIRS:
                conflict.resolution = ConflictResolution.TOOK_THEIRS
                if pred in theirs_predicates:
                    assertion = next(a for a in theirs.assertions if a.predicate == pred)
                    if assertion not in merged:
                        merged.append(assertion)
                else:
                    merged = [a for a in merged if a.predicate != pred]
            else:
                conflict.resolution = ConflictResolution.MANUAL_REQUIRED

            conflicts.append(conflict)

        # Add items that were only added (not in conflict)
        safe_ours_added = ours_added - theirs_removed
        safe_theirs_added = theirs_added - ours_removed

        for assertion in ours.assertions:
            if assertion.predicate in safe_ours_added:
                merged.append(assertion)

        for assertion in theirs.assertions:
            if assertion.predicate in safe_theirs_added and assertion not in merged:
                merged.append(assertion)

        auto_merged = len(safe_ours_added) + len(safe_theirs_added)
        return merged, conflicts, auto_merged

    def _merge_effects(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        strategy: MergeStrategy,
    ) -> tuple[list[EffectClause], list[MergeConflict], int]:
        """Merge effect lists (similar to assertions)."""
        # Use set-based merging on descriptions
        base_descs = {e.description for e in base.effects}
        ours_descs = {e.description for e in ours.effects}
        theirs_descs = {e.description for e in theirs.effects}

        ours_added = ours_descs - base_descs
        theirs_added = theirs_descs - base_descs
        ours_removed = base_descs - ours_descs
        theirs_removed = base_descs - theirs_descs

        merged = list(base.effects)
        both_removed = ours_removed & theirs_removed
        merged = [e for e in merged if e.description not in both_removed]

        conflicts = []
        conflict_descs = (ours_removed & theirs_added) | (theirs_removed & ours_added)
        for desc in conflict_descs:
            conflict = MergeConflict(
                category=DiffCategory.EFFECT,
                kind=DiffKind.EFFECT_DESCRIPTION,
                path=f"effects[description={desc[:30]}...]",
                base_value=desc in base_descs,
                ours_value=desc in ours_descs,
                theirs_value=desc in theirs_descs,
                message="Effect modified differently in each branch",
            )

            if strategy == MergeStrategy.OURS:
                conflict.resolution = ConflictResolution.TOOK_OURS
                if desc in ours_descs:
                    effect = next(e for e in ours.effects if e.description == desc)
                    if effect not in merged:
                        merged.append(effect)
                else:
                    merged = [e for e in merged if e.description != desc]
            elif strategy == MergeStrategy.THEIRS:
                conflict.resolution = ConflictResolution.TOOK_THEIRS
                if desc in theirs_descs:
                    effect = next(e for e in theirs.effects if e.description == desc)
                    if effect not in merged:
                        merged.append(effect)
                else:
                    merged = [e for e in merged if e.description != desc]
            else:
                conflict.resolution = ConflictResolution.MANUAL_REQUIRED

            conflicts.append(conflict)

        # Add safe additions
        safe_ours_added = ours_added - theirs_removed
        safe_theirs_added = theirs_added - ours_removed

        for effect in ours.effects:
            if effect.description in safe_ours_added:
                merged.append(effect)

        for effect in theirs.effects:
            if effect.description in safe_theirs_added and effect not in merged:
                merged.append(effect)

        auto_merged = len(safe_ours_added) + len(safe_theirs_added)
        return merged, conflicts, auto_merged

    def _merge_metadata(
        self,
        base: IntermediateRepresentation,
        ours: IntermediateRepresentation,
        theirs: IntermediateRepresentation,
        base_to_ours,
        base_to_theirs,
        strategy: MergeStrategy,
    ) -> tuple[Metadata, list[MergeConflict], int]:
        """Merge metadata."""
        conflicts = []
        auto_merged = 0

        # Merge simple fields
        source_path, sp_conflict, sp_auto = self._merge_field(
            "metadata.source_path",
            DiffCategory.METADATA,
            DiffKind.METADATA_SOURCE_PATH,
            base.metadata.source_path if base.metadata else None,
            ours.metadata.source_path if ours.metadata else None,
            theirs.metadata.source_path if theirs.metadata else None,
            strategy,
        )
        if sp_conflict:
            conflicts.append(sp_conflict)
        auto_merged += sp_auto

        language, lang_conflict, lang_auto = self._merge_field(
            "metadata.language",
            DiffCategory.METADATA,
            DiffKind.METADATA_LANGUAGE,
            base.metadata.language if base.metadata else None,
            ours.metadata.language if ours.metadata else None,
            theirs.metadata.language if theirs.metadata else None,
            strategy,
        )
        if lang_conflict:
            conflicts.append(lang_conflict)
        auto_merged += lang_auto

        origin, origin_conflict, origin_auto = self._merge_field(
            "metadata.origin",
            DiffCategory.METADATA,
            DiffKind.METADATA_ORIGIN,
            base.metadata.origin if base.metadata else None,
            ours.metadata.origin if ours.metadata else None,
            theirs.metadata.origin if theirs.metadata else None,
            strategy,
        )
        if origin_conflict:
            conflicts.append(origin_conflict)
        auto_merged += origin_auto

        # For evidence lists, use union
        base_evidence = base.metadata.evidence if base.metadata else []
        ours_evidence = ours.metadata.evidence if ours.metadata else []
        theirs_evidence = theirs.metadata.evidence if theirs.metadata else []

        # Union of evidence, deduped by id
        merged_evidence = list(ours_evidence)
        ours_ids = {e.get("id") for e in ours_evidence if e.get("id")}
        for evidence in theirs_evidence:
            if evidence.get("id") and evidence.get("id") not in ours_ids:
                merged_evidence.append(evidence)

        return (
            Metadata(
                source_path=source_path,
                language=language,
                origin=origin,
                evidence=merged_evidence,
            ),
            conflicts,
            auto_merged,
        )

    def _merge_field(
        self,
        path: str,
        category: DiffCategory,
        kind: DiffKind,
        base_value: Any,
        ours_value: Any,
        theirs_value: Any,
        strategy: MergeStrategy,
    ) -> tuple[Any, MergeConflict | None, int]:
        """
        Merge a single field value.

        Returns:
            Tuple of (merged_value, conflict_if_any, auto_merged_count)
        """
        # If all three are equal, no conflict
        if base_value == ours_value == theirs_value:
            return base_value, None, 0

        # If ours unchanged, use theirs
        if base_value == ours_value:
            return theirs_value, None, 1

        # If theirs unchanged, use ours
        if base_value == theirs_value:
            return ours_value, None, 1

        # If both changed to the same value, use that
        if ours_value == theirs_value:
            return ours_value, None, 1

        # Both changed to different values - CONFLICT
        conflict = MergeConflict(
            category=category,
            kind=kind,
            path=path,
            base_value=base_value,
            ours_value=ours_value,
            theirs_value=theirs_value,
            message=f"Field '{path}' modified differently in each branch",
        )

        # Apply strategy
        if strategy == MergeStrategy.OURS:
            conflict.resolution = ConflictResolution.TOOK_OURS
            conflict.resolved_value = ours_value
            return ours_value, conflict, 0

        elif strategy == MergeStrategy.THEIRS:
            conflict.resolution = ConflictResolution.TOOK_THEIRS
            conflict.resolved_value = theirs_value
            return theirs_value, conflict, 0

        elif strategy == MergeStrategy.BASE:
            conflict.resolution = ConflictResolution.KEPT_BASE
            conflict.resolved_value = base_value
            return base_value, conflict, 0

        else:  # AUTO or MANUAL
            # Mark as needing manual resolution
            conflict.resolution = ConflictResolution.MANUAL_REQUIRED
            # Return ours as placeholder
            return ours_value, conflict, 0

    def _merge_provenance(
        self,
        base_prov: Provenance | None,
        ours_prov: Provenance | None,
        theirs_prov: Provenance | None,
        strategy: MergeStrategy,
    ) -> Provenance | None:
        """
        Merge provenance information from three versions.

        Args:
            base_prov: Base provenance.
            ours_prov: Our provenance.
            theirs_prov: Their provenance.
            strategy: Merge strategy.

        Returns:
            Merged provenance, or None if all are None.
        """
        # If all are None, return None
        if base_prov is None and ours_prov is None and theirs_prov is None:
            return None

        # If all three are equal, return the common value
        if base_prov == ours_prov == theirs_prov:
            return ours_prov

        # If ours unchanged, use theirs
        if base_prov == ours_prov:
            return theirs_prov

        # If theirs unchanged, use ours
        if base_prov == theirs_prov:
            return ours_prov

        # If both changed to the same value, use that
        if ours_prov == theirs_prov:
            return ours_prov

        # Both changed to different values - create merged provenance
        # Use the merge strategy to determine which to prefer
        if strategy == MergeStrategy.OURS:
            return ours_prov
        elif strategy == MergeStrategy.THEIRS:
            return theirs_prov
        elif strategy == MergeStrategy.BASE:
            return base_prov
        else:  # AUTO or MANUAL - create merged provenance
            # Combine information from both
            combined_evidence = []
            combined_metadata = {}

            if ours_prov:
                combined_evidence.extend(ours_prov.evidence_refs)
                combined_metadata.update(ours_prov.metadata)

            if theirs_prov:
                # Add unique evidence refs
                for ref in theirs_prov.evidence_refs:
                    if ref not in combined_evidence:
                        combined_evidence.append(ref)
                # Merge metadata (theirs takes precedence for conflicts)
                combined_metadata.update(theirs_prov.metadata)

            # Take lower confidence (more conservative)
            confidence = 1.0
            if ours_prov:
                confidence = min(confidence, ours_prov.confidence)
            if theirs_prov:
                confidence = min(confidence, theirs_prov.confidence)

            # Create merged provenance
            return Provenance.from_merge(
                author="merge_system",
                confidence=confidence,
                evidence_refs=combined_evidence,
                metadata=combined_metadata,
            )


__all__ = [
    "IRMerger",
    "MergeStrategy",
    "MergeResult",
    "MergeConflict",
    "ConflictResolution",
]
