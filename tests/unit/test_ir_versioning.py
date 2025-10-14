"""Tests for IR versioning system."""

import pytest

from lift_sys.ir import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    IRVersion,
    Parameter,
    SigClause,
    VersionedIR,
    VersionMetadata,
)


@pytest.fixture
def simple_ir():
    """Create a simple IR for testing."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate sum of two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
    )


@pytest.fixture
def modified_ir():
    """Create a modified version of the IR."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate sum of two integers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int", description="First number"),
                Parameter(name="b", type_hint="int", description="Second number"),
            ],
            returns="int",
        ),
        assertions=[AssertClause(predicate="a >= 0 and b >= 0")],
    )


class TestVersionMetadata:
    """Tests for VersionMetadata."""

    def test_create_version_metadata(self):
        """Test creating version metadata."""
        metadata = VersionMetadata(
            version=1,
            parent_version=None,
            created_at="2025-01-01T00:00:00Z",
            author="test_user",
            change_summary="Initial version",
        )

        assert metadata.version == 1
        assert metadata.parent_version is None
        assert metadata.author == "test_user"
        assert metadata.change_summary == "Initial version"

    def test_version_metadata_serialization(self):
        """Test serializing and deserializing version metadata."""
        metadata = VersionMetadata(
            version=2,
            parent_version=1,
            created_at="2025-01-01T00:00:00Z",
            author="test_user",
            change_summary="Added assertions",
            tags=["milestone"],
            metadata={"review_status": "approved"},
        )

        data = metadata.to_dict()
        restored = VersionMetadata.from_dict(data)

        assert restored.version == metadata.version
        assert restored.parent_version == metadata.parent_version
        assert restored.author == metadata.author
        assert restored.change_summary == metadata.change_summary
        assert restored.tags == metadata.tags
        assert restored.metadata == metadata.metadata


class TestIRVersion:
    """Tests for IRVersion."""

    def test_create_ir_version(self, simple_ir):
        """Test creating an IR version."""
        metadata = VersionMetadata(
            version=1,
            parent_version=None,
            created_at="2025-01-01T00:00:00Z",
        )
        ir_version = IRVersion(ir=simple_ir, version_metadata=metadata)

        assert ir_version.ir == simple_ir
        assert ir_version.version_metadata == metadata

    def test_ir_version_serialization(self, simple_ir):
        """Test serializing and deserializing IR version."""
        metadata = VersionMetadata(
            version=1,
            parent_version=None,
            created_at="2025-01-01T00:00:00Z",
        )
        ir_version = IRVersion(ir=simple_ir, version_metadata=metadata)

        data = ir_version.to_dict()
        restored = IRVersion.from_dict(data)

        assert restored.ir.intent.summary == simple_ir.intent.summary
        assert restored.version_metadata.version == metadata.version


class TestVersionedIR:
    """Tests for VersionedIR."""

    def test_create_empty_versioned_ir(self):
        """Test creating an empty versioned IR."""
        versioned_ir = VersionedIR()

        assert versioned_ir.current_version == 0
        assert versioned_ir.current_ir is None
        assert len(versioned_ir.versions) == 0

    def test_create_versioned_ir_with_initial_ir(self, simple_ir):
        """Test creating a versioned IR with initial IR."""
        versioned_ir = VersionedIR(
            current_ir=simple_ir,
            initial_author="test_user",
        )

        assert versioned_ir.current_version == 1
        assert versioned_ir.current_ir == simple_ir
        assert len(versioned_ir.versions) == 1

    def test_create_new_version(self, simple_ir, modified_ir):
        """Test creating a new version."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        new_version = versioned_ir.create_version(
            ir=modified_ir,
            change_summary="Added parameter descriptions and assertions",
            author="test_user",
        )

        assert new_version == 2
        assert versioned_ir.current_version == 2
        assert versioned_ir.current_ir == modified_ir

    def test_get_version(self, simple_ir, modified_ir):
        """Test getting a specific version."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(ir=modified_ir, change_summary="Modified")

        v1 = versioned_ir.get_version(1)
        v2 = versioned_ir.get_version(2)

        assert v1 is not None
        assert v1.ir == simple_ir
        assert v2 is not None
        assert v2.ir == modified_ir

    def test_get_nonexistent_version(self, simple_ir):
        """Test getting a version that doesn't exist."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        assert versioned_ir.get_version(0) is None
        assert versioned_ir.get_version(5) is None

    def test_get_version_range(self, simple_ir):
        """Test getting a range of versions."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        # Create 4 more versions
        for i in range(2, 6):
            ir = IntermediateRepresentation(
                intent=IntentClause(summary=f"Version {i}"),
                signature=simple_ir.signature,
            )
            versioned_ir.create_version(ir, change_summary=f"Version {i}")

        versions = versioned_ir.get_version_range(2, 4)

        assert len(versions) == 3
        assert versions[0].version_metadata.version == 2
        assert versions[2].version_metadata.version == 4

    def test_get_versions_by_author(self, simple_ir, modified_ir):
        """Test getting versions by author."""
        versioned_ir = VersionedIR(current_ir=simple_ir, initial_author="alice")
        versioned_ir.create_version(ir=modified_ir, author="bob")
        versioned_ir.create_version(ir=simple_ir, author="alice")

        alice_versions = versioned_ir.get_versions_by_author("alice")
        bob_versions = versioned_ir.get_versions_by_author("bob")

        assert len(alice_versions) == 2
        assert len(bob_versions) == 1
        assert alice_versions[0].version_metadata.version == 1
        assert alice_versions[1].version_metadata.version == 3
        assert bob_versions[0].version_metadata.version == 2

    def test_get_versions_by_tag(self, simple_ir):
        """Test getting versions by tag."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(ir=simple_ir, tags=["milestone"])
        versioned_ir.create_version(ir=simple_ir, tags=["draft"])
        versioned_ir.create_version(ir=simple_ir, tags=["milestone", "reviewed"])

        milestone_versions = versioned_ir.get_versions_by_tag("milestone")
        reviewed_versions = versioned_ir.get_versions_by_tag("reviewed")

        assert len(milestone_versions) == 2
        assert len(reviewed_versions) == 1

    def test_compare_versions(self, simple_ir, modified_ir):
        """Test comparing two versions."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(ir=modified_ir)

        comparison = versioned_ir.compare_versions(1, 2)

        assert comparison is not None
        assert comparison.overall_similarity < 1.0
        assert len(comparison.all_diffs()) > 0

    def test_get_history_summary(self, simple_ir, modified_ir):
        """Test getting history summary."""
        versioned_ir = VersionedIR(current_ir=simple_ir, initial_author="alice")
        versioned_ir.create_version(
            ir=modified_ir,
            author="bob",
            change_summary="Added assertions",
        )

        summary = versioned_ir.get_history_summary()

        assert len(summary) == 2
        assert summary[0]["version"] == 1
        assert summary[0]["author"] == "alice"
        assert summary[1]["version"] == 2
        assert summary[1]["author"] == "bob"
        assert summary[1]["change_summary"] == "Added assertions"

    def test_rollback_to_version(self, simple_ir, modified_ir):
        """Test rolling back to a previous version."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(ir=modified_ir)

        # Rollback to version 1
        new_version = versioned_ir.rollback_to_version(1)

        assert new_version == 3
        assert versioned_ir.current_version == 3
        assert versioned_ir.current_ir.intent.summary == simple_ir.intent.summary
        assert "rollback" in versioned_ir.get_version(3).version_metadata.tags

    def test_rollback_to_nonexistent_version(self, simple_ir):
        """Test rolling back to a version that doesn't exist."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        result = versioned_ir.rollback_to_version(5)

        assert result is None
        assert versioned_ir.current_version == 1

    def test_add_tag_to_version(self, simple_ir):
        """Test adding a tag to a version."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        success = versioned_ir.add_tag_to_version(1, "production")

        assert success is True
        v1 = versioned_ir.get_version(1)
        assert "production" in v1.version_metadata.tags

    def test_add_duplicate_tag(self, simple_ir):
        """Test adding a tag that already exists."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.add_tag_to_version(1, "production")

        # Try to add same tag again
        versioned_ir.add_tag_to_version(1, "production")

        v1 = versioned_ir.get_version(1)
        assert v1.version_metadata.tags.count("production") == 1

    def test_remove_tag_from_version(self, simple_ir):
        """Test removing a tag from a version."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.add_tag_to_version(1, "draft")

        success = versioned_ir.remove_tag_from_version(1, "draft")

        assert success is True
        v1 = versioned_ir.get_version(1)
        assert "draft" not in v1.version_metadata.tags

    def test_remove_nonexistent_tag(self, simple_ir):
        """Test removing a tag that doesn't exist."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        success = versioned_ir.remove_tag_from_version(1, "nonexistent")

        assert success is False

    def test_version_diff_from_parent(self, simple_ir, modified_ir):
        """Test that version includes diff from parent."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(ir=modified_ir)

        v2 = versioned_ir.get_version(2)

        assert v2.version_metadata.diff_from_parent is not None
        assert v2.version_metadata.parent_version == 1
        assert len(v2.version_metadata.diff_from_parent.all_diffs()) > 0

    def test_first_version_has_no_parent_diff(self, simple_ir):
        """Test that first version has no parent diff."""
        versioned_ir = VersionedIR(current_ir=simple_ir)

        v1 = versioned_ir.get_version(1)

        assert v1.version_metadata.parent_version is None
        assert v1.version_metadata.diff_from_parent is None

    def test_serialization_roundtrip(self, simple_ir, modified_ir):
        """Test full serialization and deserialization."""
        versioned_ir = VersionedIR(current_ir=simple_ir, initial_author="alice")
        versioned_ir.create_version(
            ir=modified_ir,
            author="bob",
            change_summary="Added assertions",
            tags=["milestone"],
        )

        # Serialize
        data = versioned_ir.to_dict()

        # Deserialize
        restored = VersionedIR.from_dict(data)

        assert restored.current_version == versioned_ir.current_version
        assert len(restored.versions) == len(versioned_ir.versions)
        assert restored.current_ir.intent.summary == versioned_ir.current_ir.intent.summary
        assert (
            restored.get_version(2).version_metadata.author
            == versioned_ir.get_version(2).version_metadata.author
        )

    def test_get_change_log(self, simple_ir, modified_ir):
        """Test generating a changelog."""
        versioned_ir = VersionedIR(current_ir=simple_ir, initial_author="alice")
        versioned_ir.create_version(
            ir=modified_ir,
            author="bob",
            change_summary="Added assertions",
            tags=["reviewed"],
        )

        changelog = versioned_ir.get_change_log()

        assert "# IR Version History" in changelog
        assert "Version 1" in changelog
        assert "Version 2" in changelog
        assert "alice" in changelog
        assert "bob" in changelog
        assert "Added assertions" in changelog
        assert "reviewed" in changelog

    def test_get_change_log_range(self, simple_ir):
        """Test generating a changelog for a specific range."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        for i in range(2, 5):
            ir = IntermediateRepresentation(
                intent=IntentClause(summary=f"Version {i}"),
                signature=simple_ir.signature,
            )
            versioned_ir.create_version(ir, change_summary=f"Change {i}")

        changelog = versioned_ir.get_change_log(start_version=2, end_version=3)

        assert "Version 1" not in changelog
        assert "Version 2" in changelog
        assert "Version 3" in changelog
        assert "Version 4" not in changelog

    def test_version_metadata_with_custom_fields(self, simple_ir):
        """Test version metadata with custom fields."""
        versioned_ir = VersionedIR(current_ir=simple_ir)
        versioned_ir.create_version(
            ir=simple_ir,
            metadata={
                "review_status": "approved",
                "reviewer": "charlie",
                "test_coverage": 0.95,
            },
        )

        v2 = versioned_ir.get_version(2)
        assert v2.version_metadata.metadata["review_status"] == "approved"
        assert v2.version_metadata.metadata["reviewer"] == "charlie"
        assert v2.version_metadata.metadata["test_coverage"] == 0.95
