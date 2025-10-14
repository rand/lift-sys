"""IR versioning and history management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .differ import ComparisonResult, IRComparer
from .models import IntermediateRepresentation


@dataclass(slots=True)
class VersionMetadata:
    """Metadata for a single IR version."""

    version: int
    parent_version: int | None
    created_at: str
    author: str | None = None
    change_summary: str | None = None
    diff_from_parent: ComparisonResult | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "version": self.version,
            "parent_version": self.parent_version,
            "created_at": self.created_at,
            "author": self.author,
            "change_summary": self.change_summary,
            "diff_from_parent": self.diff_from_parent.to_dict() if self.diff_from_parent else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionMetadata:
        """Deserialize from dictionary."""
        from .differ import ComparisonResult

        diff_data = data.get("diff_from_parent")
        diff = ComparisonResult.from_dict(diff_data) if diff_data else None

        return cls(
            version=data["version"],
            parent_version=data.get("parent_version"),
            created_at=data["created_at"],
            author=data.get("author"),
            change_summary=data.get("change_summary"),
            diff_from_parent=diff,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class IRVersion:
    """A single version of an IR with its metadata."""

    ir: IntermediateRepresentation
    version_metadata: VersionMetadata

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "ir": self.ir.to_dict(),
            "version_metadata": self.version_metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IRVersion:
        """Deserialize from dictionary."""
        return cls(
            ir=IntermediateRepresentation.from_dict(data["ir"]),
            version_metadata=VersionMetadata.from_dict(data["version_metadata"]),
        )


class VersionedIR:
    """
    Wrapper for IntermediateRepresentation with version history.

    Manages a linear version history of an IR, with each version
    tracking its parent, changes, and metadata.
    """

    def __init__(
        self,
        current_ir: IntermediateRepresentation | None = None,
        initial_author: str | None = None,
        initial_metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a new versioned IR.

        Args:
            current_ir: Initial IR (creates version 1)
            initial_author: Author of the initial version
            initial_metadata: Additional metadata for the initial version
        """
        self._versions: list[IRVersion] = []
        self._comparer = IRComparer()

        if current_ir:
            self.create_version(
                ir=current_ir,
                change_summary="Initial version",
                author=initial_author,
                metadata=initial_metadata or {},
            )

    @property
    def current_version(self) -> int:
        """Get the current version number."""
        return len(self._versions)

    @property
    def current_ir(self) -> IntermediateRepresentation | None:
        """Get the current IR."""
        if not self._versions:
            return None
        return self._versions[-1].ir

    @property
    def versions(self) -> list[IRVersion]:
        """Get all versions (read-only access)."""
        return self._versions.copy()

    def create_version(
        self,
        ir: IntermediateRepresentation,
        change_summary: str | None = None,
        author: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Create a new version of the IR.

        Args:
            ir: The new IR
            change_summary: Human-readable summary of changes
            author: Author of this version
            tags: Tags for this version (e.g., ["milestone", "reviewed"])
            metadata: Additional metadata

        Returns:
            The new version number
        """
        new_version = len(self._versions) + 1
        parent_version = new_version - 1 if self._versions else None

        # Compute diff from parent
        diff_from_parent = None
        if parent_version is not None:
            parent_ir = self._versions[parent_version - 1].ir
            diff_from_parent = self._comparer.compare(parent_ir, ir)

        version_metadata = VersionMetadata(
            version=new_version,
            parent_version=parent_version,
            created_at=datetime.now(UTC).isoformat() + "Z",
            author=author,
            change_summary=change_summary,
            diff_from_parent=diff_from_parent,
            tags=tags or [],
            metadata=metadata or {},
        )

        ir_version = IRVersion(ir=ir, version_metadata=version_metadata)
        self._versions.append(ir_version)

        return new_version

    def get_version(self, version: int) -> IRVersion | None:
        """
        Get a specific version.

        Args:
            version: Version number (1-indexed)

        Returns:
            The IR version or None if not found
        """
        if version < 1 or version > len(self._versions):
            return None
        return self._versions[version - 1]

    def get_version_range(self, start: int, end: int) -> list[IRVersion]:
        """
        Get a range of versions.

        Args:
            start: Start version (1-indexed, inclusive)
            end: End version (1-indexed, inclusive)

        Returns:
            List of IR versions in the range
        """
        if start < 1 or end > len(self._versions) or start > end:
            return []
        return self._versions[start - 1 : end]

    def get_versions_by_author(self, author: str) -> list[IRVersion]:
        """
        Get all versions by a specific author.

        Args:
            author: Author name to search for

        Returns:
            List of versions by that author
        """
        return [v for v in self._versions if v.version_metadata.author == author]

    def get_versions_by_tag(self, tag: str) -> list[IRVersion]:
        """
        Get all versions with a specific tag.

        Args:
            tag: Tag to search for

        Returns:
            List of versions with that tag
        """
        return [v for v in self._versions if tag in v.version_metadata.tags]

    def compare_versions(self, version1: int, version2: int) -> ComparisonResult | None:
        """
        Compare two versions of the IR.

        Args:
            version1: First version number
            version2: Second version number

        Returns:
            Comparison result or None if versions not found
        """
        v1 = self.get_version(version1)
        v2 = self.get_version(version2)

        if not v1 or not v2:
            return None

        return self._comparer.compare(v1.ir, v2.ir)

    def get_history_summary(self) -> list[dict[str, Any]]:
        """
        Get a summary of the version history.

        Returns:
            List of version summaries with key metadata
        """
        return [
            {
                "version": v.version_metadata.version,
                "created_at": v.version_metadata.created_at,
                "author": v.version_metadata.author,
                "change_summary": v.version_metadata.change_summary,
                "tags": v.version_metadata.tags,
                "has_changes": v.version_metadata.diff_from_parent is not None,
            }
            for v in self._versions
        ]

    def rollback_to_version(self, version: int) -> int | None:
        """
        Rollback to a previous version by creating a new version with that IR.

        Args:
            version: Version number to rollback to

        Returns:
            The new version number or None if rollback failed
        """
        target = self.get_version(version)
        if not target:
            return None

        return self.create_version(
            ir=target.ir,
            change_summary=f"Rollback to version {version}",
            tags=["rollback"],
            metadata={"rollback_from": self.current_version, "rollback_to": version},
        )

    def add_tag_to_version(self, version: int, tag: str) -> bool:
        """
        Add a tag to a specific version.

        Args:
            version: Version number
            tag: Tag to add

        Returns:
            True if successful, False if version not found
        """
        v = self.get_version(version)
        if not v:
            return False

        if tag not in v.version_metadata.tags:
            v.version_metadata.tags.append(tag)
        return True

    def remove_tag_from_version(self, version: int, tag: str) -> bool:
        """
        Remove a tag from a specific version.

        Args:
            version: Version number
            tag: Tag to remove

        Returns:
            True if successful, False if version not found or tag not present
        """
        v = self.get_version(version)
        if not v:
            return False

        if tag in v.version_metadata.tags:
            v.version_metadata.tags.remove(tag)
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the entire version history to a dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "current_version": self.current_version,
            "versions": [v.to_dict() for v in self._versions],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VersionedIR:
        """
        Deserialize from a dictionary.

        Args:
            data: Dictionary representation

        Returns:
            VersionedIR instance
        """
        versioned_ir = cls()
        versioned_ir._versions = [IRVersion.from_dict(v) for v in data.get("versions", [])]
        return versioned_ir

    def get_change_log(self, start_version: int = 1, end_version: int | None = None) -> str:
        """
        Generate a human-readable changelog.

        Args:
            start_version: Starting version (inclusive)
            end_version: Ending version (inclusive), defaults to current

        Returns:
            Formatted changelog string
        """
        if end_version is None:
            end_version = self.current_version

        versions = self.get_version_range(start_version, end_version)
        if not versions:
            return "No versions in range"

        lines = ["# IR Version History\n"]
        for v in versions:
            meta = v.version_metadata
            lines.append(f"## Version {meta.version}")
            lines.append(f"**Date**: {meta.created_at}")
            if meta.author:
                lines.append(f"**Author**: {meta.author}")
            if meta.tags:
                lines.append(f"**Tags**: {', '.join(meta.tags)}")
            if meta.change_summary:
                lines.append(f"**Changes**: {meta.change_summary}")

            # Add diff summary if available
            if meta.diff_from_parent:
                diff = meta.diff_from_parent
                total_diffs = (
                    len(diff.intent_comparison.diffs)
                    + len(diff.signature_comparison.diffs)
                    + len(diff.assertion_comparison.diffs)
                    + len(diff.effect_comparison.diffs)
                    + len(diff.metadata_comparison.diffs)
                )
                if total_diffs > 0:
                    lines.append(f"**Similarity**: {diff.overall_similarity:.1%}")
                    lines.append(f"**Changes**: {total_diffs} differences from parent")

            lines.append("")  # Blank line between versions

        return "\n".join(lines)


__all__ = [
    "VersionMetadata",
    "IRVersion",
    "VersionedIR",
]
