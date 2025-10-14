"""IR comparison and diff engine.

This module provides comprehensive comparison between two IntermediateRepresentations,
calculating detailed differences and semantic similarity scores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import IntermediateRepresentation


class DiffCategory(str, Enum):
    """Category of IR element being compared."""

    INTENT = "intent"
    SIGNATURE = "signature"
    ASSERTION = "assertion"
    EFFECT = "effect"
    METADATA = "metadata"


class DiffKind(str, Enum):
    """Specific type of difference within a category."""

    # Intent diffs
    INTENT_SUMMARY = "intent_summary"
    INTENT_RATIONALE = "intent_rationale"

    # Signature diffs
    SIGNATURE_NAME = "signature_name"
    PARAMETER_COUNT = "parameter_count"
    PARAMETER_NAME = "parameter_name"
    PARAMETER_TYPE = "parameter_type"
    PARAMETER_DESCRIPTION = "parameter_description"
    RETURN_TYPE = "return_type"

    # Assertion diffs
    ASSERTION_COUNT = "assertion_count"
    ASSERTION_PREDICATE = "assertion_predicate"
    ASSERTION_RATIONALE = "assertion_rationale"

    # Effect diffs
    EFFECT_COUNT = "effect_count"
    EFFECT_DESCRIPTION = "effect_description"

    # Metadata diffs
    METADATA_SOURCE_PATH = "metadata_source_path"
    METADATA_LANGUAGE = "metadata_language"
    METADATA_ORIGIN = "metadata_origin"
    METADATA_EVIDENCE = "metadata_evidence"


class DiffSeverity(str, Enum):
    """Severity level of a difference."""

    ERROR = "error"  # Breaking difference
    WARNING = "warning"  # Significant but non-breaking
    INFO = "info"  # Minor informational difference


@dataclass
class IRDiff:
    """A single difference between two IR elements."""

    category: DiffCategory
    """Category of element (intent, signature, etc.)."""

    kind: DiffKind
    """Specific type of difference."""

    path: str
    """JSON path to the difference (e.g., 'signature.parameters[0].name')."""

    left_value: Any
    """Value from left/original IR."""

    right_value: Any
    """Value from right/compared IR."""

    severity: DiffSeverity = DiffSeverity.ERROR
    """Severity of this difference."""

    message: str | None = None
    """Human-readable description of the difference."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "kind": self.kind.value,
            "path": self.path,
            "left_value": self.left_value,
            "right_value": self.right_value,
            "severity": self.severity.value,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IRDiff:
        """Deserialize from dictionary."""
        return cls(
            category=DiffCategory(data["category"]),
            kind=DiffKind(data["kind"]),
            path=data["path"],
            left_value=data["left_value"],
            right_value=data["right_value"],
            severity=DiffSeverity(data.get("severity", DiffSeverity.ERROR.value)),
            message=data.get("message"),
        )


@dataclass
class CategoryComparison:
    """Comparison result for a specific IR category."""

    category: DiffCategory
    """The category being compared."""

    diffs: list[IRDiff] = field(default_factory=list)
    """Differences found in this category."""

    matches: int = 0
    """Number of matched fields."""

    total_fields: int = 0
    """Total fields compared."""

    similarity: float = 1.0
    """Similarity score for this category (0.0 to 1.0)."""

    def has_diffs(self) -> bool:
        """Check if any differences exist."""
        return len(self.diffs) > 0

    def has_errors(self) -> bool:
        """Check if any error-level diffs exist."""
        return any(d.severity == DiffSeverity.ERROR for d in self.diffs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category.value,
            "diffs": [d.to_dict() for d in self.diffs],
            "matches": self.matches,
            "total_fields": self.total_fields,
            "similarity": self.similarity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CategoryComparison:
        """Deserialize from dictionary."""
        return cls(
            category=DiffCategory(data["category"]),
            diffs=[IRDiff.from_dict(d) for d in data.get("diffs", [])],
            matches=data.get("matches", 0),
            total_fields=data.get("total_fields", 0),
            similarity=data.get("similarity", 1.0),
        )


@dataclass
class ComparisonResult:
    """Complete result of comparing two IRs."""

    left_ir: IntermediateRepresentation
    """The left/original IR."""

    right_ir: IntermediateRepresentation
    """The right/compared IR."""

    intent_comparison: CategoryComparison
    """Comparison of intent elements."""

    signature_comparison: CategoryComparison
    """Comparison of signature elements."""

    assertion_comparison: CategoryComparison
    """Comparison of assertion elements."""

    effect_comparison: CategoryComparison
    """Comparison of effect elements."""

    metadata_comparison: CategoryComparison
    """Comparison of metadata elements."""

    overall_similarity: float = 1.0
    """Overall semantic similarity score (0.0 to 1.0)."""

    def all_diffs(self) -> list[IRDiff]:
        """Get all differences across all categories."""
        return (
            self.intent_comparison.diffs
            + self.signature_comparison.diffs
            + self.assertion_comparison.diffs
            + self.effect_comparison.diffs
            + self.metadata_comparison.diffs
        )

    def has_breaking_changes(self) -> bool:
        """Check if any error-level differences exist."""
        return any(
            comp.has_errors()
            for comp in [
                self.intent_comparison,
                self.signature_comparison,
                self.assertion_comparison,
                self.effect_comparison,
                self.metadata_comparison,
            ]
        )

    def is_identical(self) -> bool:
        """Check if IRs are identical (no differences at all)."""
        return len(self.all_diffs()) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "left_ir": self.left_ir.to_dict(),
            "right_ir": self.right_ir.to_dict(),
            "intent_comparison": self.intent_comparison.to_dict(),
            "signature_comparison": self.signature_comparison.to_dict(),
            "assertion_comparison": self.assertion_comparison.to_dict(),
            "effect_comparison": self.effect_comparison.to_dict(),
            "metadata_comparison": self.metadata_comparison.to_dict(),
            "overall_similarity": self.overall_similarity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComparisonResult:
        """Deserialize from dictionary."""
        from .models import IntermediateRepresentation

        return cls(
            left_ir=IntermediateRepresentation.from_dict(data["left_ir"]),
            right_ir=IntermediateRepresentation.from_dict(data["right_ir"]),
            intent_comparison=CategoryComparison.from_dict(data["intent_comparison"]),
            signature_comparison=CategoryComparison.from_dict(data["signature_comparison"]),
            assertion_comparison=CategoryComparison.from_dict(data["assertion_comparison"]),
            effect_comparison=CategoryComparison.from_dict(data["effect_comparison"]),
            metadata_comparison=CategoryComparison.from_dict(data["metadata_comparison"]),
            overall_similarity=data.get("overall_similarity", 1.0),
        )


class IRComparer:
    """Compares two IntermediateRepresentations and calculates differences."""

    def __init__(
        self,
        ignore_metadata: bool = False,
        ignore_descriptions: bool = False,
        case_sensitive: bool = True,
    ):
        """Initialize the comparer with options.

        Args:
            ignore_metadata: If True, skip metadata comparison.
            ignore_descriptions: If True, skip description/rationale comparisons.
            case_sensitive: If True, use case-sensitive string comparisons.
        """
        self.ignore_metadata = ignore_metadata
        self.ignore_descriptions = ignore_descriptions
        self.case_sensitive = case_sensitive

    def compare(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> ComparisonResult:
        """Compare two IRs and return detailed comparison result.

        Args:
            left: The left/original IR.
            right: The right/compared IR.

        Returns:
            ComparisonResult with detailed differences and similarity scores.
        """
        intent_comp = self._compare_intent(left, right)
        signature_comp = self._compare_signature(left, right)
        assertion_comp = self._compare_assertions(left, right)
        effect_comp = self._compare_effects(left, right)
        metadata_comp = (
            self._compare_metadata(left, right)
            if not self.ignore_metadata
            else CategoryComparison(category=DiffCategory.METADATA, similarity=1.0)
        )

        # Calculate overall similarity as weighted average
        weights = {
            "signature": 0.35,
            "intent": 0.20,
            "assertion": 0.20,
            "effect": 0.15,
            "metadata": 0.10,
        }

        overall_similarity = (
            signature_comp.similarity * weights["signature"]
            + intent_comp.similarity * weights["intent"]
            + assertion_comp.similarity * weights["assertion"]
            + effect_comp.similarity * weights["effect"]
            + metadata_comp.similarity * weights["metadata"]
        )

        return ComparisonResult(
            left_ir=left,
            right_ir=right,
            intent_comparison=intent_comp,
            signature_comparison=signature_comp,
            assertion_comparison=assertion_comp,
            effect_comparison=effect_comp,
            metadata_comparison=metadata_comp,
            overall_similarity=overall_similarity,
        )

    def _compare_intent(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> CategoryComparison:
        """Compare intent clauses."""
        diffs = []
        matches = 0
        total_fields = 0

        # Compare summary
        total_fields += 1
        if self._strings_equal(left.intent.summary, right.intent.summary):
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.INTENT,
                    kind=DiffKind.INTENT_SUMMARY,
                    path="intent.summary",
                    left_value=left.intent.summary,
                    right_value=right.intent.summary,
                    severity=DiffSeverity.WARNING,
                    message="Intent summaries differ",
                )
            )

        # Compare rationale (if not ignoring descriptions)
        if not self.ignore_descriptions:
            total_fields += 1
            if self._strings_equal(left.intent.rationale, right.intent.rationale):
                matches += 1
            else:
                diffs.append(
                    IRDiff(
                        category=DiffCategory.INTENT,
                        kind=DiffKind.INTENT_RATIONALE,
                        path="intent.rationale",
                        left_value=left.intent.rationale,
                        right_value=right.intent.rationale,
                        severity=DiffSeverity.INFO,
                        message="Intent rationales differ",
                    )
                )

        similarity = matches / total_fields if total_fields > 0 else 1.0

        return CategoryComparison(
            category=DiffCategory.INTENT,
            diffs=diffs,
            matches=matches,
            total_fields=total_fields,
            similarity=similarity,
        )

    def _compare_signature(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> CategoryComparison:
        """Compare signature clauses."""
        diffs = []
        matches = 0
        total_fields = 0

        # Compare function name
        total_fields += 1
        if left.signature.name == right.signature.name:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.SIGNATURE,
                    kind=DiffKind.SIGNATURE_NAME,
                    path="signature.name",
                    left_value=left.signature.name,
                    right_value=right.signature.name,
                    severity=DiffSeverity.ERROR,
                    message=f"Function name changed: '{left.signature.name}' -> '{right.signature.name}'",
                )
            )

        # Compare parameter count
        total_fields += 1
        left_param_count = len(left.signature.parameters)
        right_param_count = len(right.signature.parameters)
        if left_param_count == right_param_count:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.SIGNATURE,
                    kind=DiffKind.PARAMETER_COUNT,
                    path="signature.parameters",
                    left_value=left_param_count,
                    right_value=right_param_count,
                    severity=DiffSeverity.ERROR,
                    message=f"Parameter count changed: {left_param_count} -> {right_param_count}",
                )
            )

        # Compare individual parameters
        for i in range(min(left_param_count, right_param_count)):
            left_param = left.signature.parameters[i]
            right_param = right.signature.parameters[i]

            # Parameter name
            total_fields += 1
            if left_param.name == right_param.name:
                matches += 1
            else:
                diffs.append(
                    IRDiff(
                        category=DiffCategory.SIGNATURE,
                        kind=DiffKind.PARAMETER_NAME,
                        path=f"signature.parameters[{i}].name",
                        left_value=left_param.name,
                        right_value=right_param.name,
                        severity=DiffSeverity.ERROR,
                        message=f"Parameter {i} name: '{left_param.name}' -> '{right_param.name}'",
                    )
                )

            # Parameter type
            total_fields += 1
            if self._types_equal(left_param.type_hint, right_param.type_hint):
                matches += 1
            else:
                diffs.append(
                    IRDiff(
                        category=DiffCategory.SIGNATURE,
                        kind=DiffKind.PARAMETER_TYPE,
                        path=f"signature.parameters[{i}].type_hint",
                        left_value=left_param.type_hint,
                        right_value=right_param.type_hint,
                        severity=DiffSeverity.WARNING,
                        message=f"Parameter {left_param.name} type: {left_param.type_hint} -> {right_param.type_hint}",
                    )
                )

            # Parameter description (if not ignoring descriptions)
            if not self.ignore_descriptions:
                total_fields += 1
                if self._strings_equal(left_param.description, right_param.description):
                    matches += 1
                else:
                    diffs.append(
                        IRDiff(
                            category=DiffCategory.SIGNATURE,
                            kind=DiffKind.PARAMETER_DESCRIPTION,
                            path=f"signature.parameters[{i}].description",
                            left_value=left_param.description,
                            right_value=right_param.description,
                            severity=DiffSeverity.INFO,
                            message=f"Parameter {left_param.name} description differs",
                        )
                    )

        # Compare return type
        total_fields += 1
        if self._types_equal(left.signature.returns, right.signature.returns):
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.SIGNATURE,
                    kind=DiffKind.RETURN_TYPE,
                    path="signature.returns",
                    left_value=left.signature.returns,
                    right_value=right.signature.returns,
                    severity=DiffSeverity.WARNING,
                    message=f"Return type: {left.signature.returns} -> {right.signature.returns}",
                )
            )

        similarity = matches / total_fields if total_fields > 0 else 1.0

        return CategoryComparison(
            category=DiffCategory.SIGNATURE,
            diffs=diffs,
            matches=matches,
            total_fields=total_fields,
            similarity=similarity,
        )

    def _compare_assertions(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> CategoryComparison:
        """Compare assertion clauses."""
        diffs = []
        matches = 0
        total_fields = 0

        # Compare assertion count
        total_fields += 1
        left_count = len(left.assertions)
        right_count = len(right.assertions)
        if left_count == right_count:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.ASSERTION,
                    kind=DiffKind.ASSERTION_COUNT,
                    path="assertions",
                    left_value=left_count,
                    right_value=right_count,
                    severity=DiffSeverity.WARNING,
                    message=f"Assertion count: {left_count} -> {right_count}",
                )
            )

        # Compare individual assertions
        for i in range(min(left_count, right_count)):
            left_assert = left.assertions[i]
            right_assert = right.assertions[i]

            # Predicate
            total_fields += 1
            if self._strings_equal(left_assert.predicate.strip(), right_assert.predicate.strip()):
                matches += 1
            else:
                diffs.append(
                    IRDiff(
                        category=DiffCategory.ASSERTION,
                        kind=DiffKind.ASSERTION_PREDICATE,
                        path=f"assertions[{i}].predicate",
                        left_value=left_assert.predicate,
                        right_value=right_assert.predicate,
                        severity=DiffSeverity.WARNING,
                        message=f"Assertion {i} predicate differs",
                    )
                )

            # Rationale (if not ignoring descriptions)
            if not self.ignore_descriptions:
                total_fields += 1
                if self._strings_equal(left_assert.rationale, right_assert.rationale):
                    matches += 1
                else:
                    diffs.append(
                        IRDiff(
                            category=DiffCategory.ASSERTION,
                            kind=DiffKind.ASSERTION_RATIONALE,
                            path=f"assertions[{i}].rationale",
                            left_value=left_assert.rationale,
                            right_value=right_assert.rationale,
                            severity=DiffSeverity.INFO,
                            message=f"Assertion {i} rationale differs",
                        )
                    )

        similarity = matches / total_fields if total_fields > 0 else 1.0

        return CategoryComparison(
            category=DiffCategory.ASSERTION,
            diffs=diffs,
            matches=matches,
            total_fields=total_fields,
            similarity=similarity,
        )

    def _compare_effects(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> CategoryComparison:
        """Compare effect clauses."""
        diffs = []
        matches = 0
        total_fields = 0

        # Compare effect count
        total_fields += 1
        left_count = len(left.effects)
        right_count = len(right.effects)
        if left_count == right_count:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.EFFECT,
                    kind=DiffKind.EFFECT_COUNT,
                    path="effects",
                    left_value=left_count,
                    right_value=right_count,
                    severity=DiffSeverity.WARNING,
                    message=f"Effect count: {left_count} -> {right_count}",
                )
            )

        # Compare individual effects
        for i in range(min(left_count, right_count)):
            left_effect = left.effects[i]
            right_effect = right.effects[i]

            # Effect description
            total_fields += 1
            if self._strings_equal(left_effect.description, right_effect.description):
                matches += 1
            else:
                diffs.append(
                    IRDiff(
                        category=DiffCategory.EFFECT,
                        kind=DiffKind.EFFECT_DESCRIPTION,
                        path=f"effects[{i}].description",
                        left_value=left_effect.description,
                        right_value=right_effect.description,
                        severity=DiffSeverity.WARNING,
                        message=f"Effect {i} description differs",
                    )
                )

        similarity = matches / total_fields if total_fields > 0 else 1.0

        return CategoryComparison(
            category=DiffCategory.EFFECT,
            diffs=diffs,
            matches=matches,
            total_fields=total_fields,
            similarity=similarity,
        )

    def _compare_metadata(
        self, left: IntermediateRepresentation, right: IntermediateRepresentation
    ) -> CategoryComparison:
        """Compare metadata."""
        diffs = []
        matches = 0
        total_fields = 0

        # Source path
        total_fields += 1
        if left.metadata.source_path == right.metadata.source_path:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.METADATA,
                    kind=DiffKind.METADATA_SOURCE_PATH,
                    path="metadata.source_path",
                    left_value=left.metadata.source_path,
                    right_value=right.metadata.source_path,
                    severity=DiffSeverity.INFO,
                    message="Source path differs",
                )
            )

        # Language
        total_fields += 1
        if left.metadata.language == right.metadata.language:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.METADATA,
                    kind=DiffKind.METADATA_LANGUAGE,
                    path="metadata.language",
                    left_value=left.metadata.language,
                    right_value=right.metadata.language,
                    severity=DiffSeverity.INFO,
                    message="Language differs",
                )
            )

        # Origin
        total_fields += 1
        if left.metadata.origin == right.metadata.origin:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.METADATA,
                    kind=DiffKind.METADATA_ORIGIN,
                    path="metadata.origin",
                    left_value=left.metadata.origin,
                    right_value=right.metadata.origin,
                    severity=DiffSeverity.INFO,
                    message="Origin differs",
                )
            )

        # Evidence count
        total_fields += 1
        left_evidence_count = len(left.metadata.evidence)
        right_evidence_count = len(right.metadata.evidence)
        if left_evidence_count == right_evidence_count:
            matches += 1
        else:
            diffs.append(
                IRDiff(
                    category=DiffCategory.METADATA,
                    kind=DiffKind.METADATA_EVIDENCE,
                    path="metadata.evidence",
                    left_value=left_evidence_count,
                    right_value=right_evidence_count,
                    severity=DiffSeverity.INFO,
                    message=f"Evidence count: {left_evidence_count} -> {right_evidence_count}",
                )
            )

        similarity = matches / total_fields if total_fields > 0 else 1.0

        return CategoryComparison(
            category=DiffCategory.METADATA,
            diffs=diffs,
            matches=matches,
            total_fields=total_fields,
            similarity=similarity,
        )

    def _strings_equal(self, left: str | None, right: str | None) -> bool:
        """Compare two strings with case sensitivity option."""
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False

        if self.case_sensitive:
            return left == right
        return left.lower() == right.lower()

    def _types_equal(self, left: str | None, right: str | None) -> bool:
        """Compare two type hints, normalizing whitespace."""
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False

        # Normalize whitespace in type hints
        left_normalized = " ".join(left.split())
        right_normalized = " ".join(right.split())

        return left_normalized == right_normalized


__all__ = [
    "DiffCategory",
    "DiffKind",
    "DiffSeverity",
    "IRDiff",
    "CategoryComparison",
    "ComparisonResult",
    "IRComparer",
]
