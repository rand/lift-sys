"""Tests for IR three-way merge operations."""

import pytest

from lift_sys.ir import (
    AssertClause,
    ConflictResolution,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    IRMerger,
    MergeStrategy,
    Metadata,
    Parameter,
    SigClause,
)


@pytest.fixture
def base_ir():
    """Create base IR for merge testing."""
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
        effects=[EffectClause(description="Pure function")],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
        ],
        metadata=Metadata(
            source_path="math.py",
            language="python",
            origin="manual",
        ),
    )


@pytest.fixture
def ours_ir_no_conflict(base_ir):
    """Our branch - add rationale, no conflicts."""
    return IntermediateRepresentation(
        intent=IntentClause(
            summary="Calculate sum of two numbers",
            rationale="Basic arithmetic operation",
        ),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int", description="First number"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[EffectClause(description="Pure function")],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
            AssertClause(predicate="result >= 0"),
        ],
        metadata=Metadata(
            source_path="math.py",
            language="python",
            origin="manual",
        ),
    )


@pytest.fixture
def theirs_ir_no_conflict(base_ir):
    """Their branch - add return assertion, no conflicts."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate sum of two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int", description="Second number"),
            ],
            returns="int",
        ),
        effects=[EffectClause(description="Pure function")],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
            AssertClause(predicate="result == a + b"),
        ],
        metadata=Metadata(
            source_path="math.py",
            language="python",
            origin="manual",
        ),
    )


@pytest.fixture
def ours_ir_conflict(base_ir):
    """Our branch - conflicting changes to summary."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Add two integers together"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[EffectClause(description="Pure function")],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
        ],
        metadata=Metadata(
            source_path="math.py",
            language="python",
            origin="manual",
        ),
    )


@pytest.fixture
def theirs_ir_conflict(base_ir):
    """Their branch - different conflicting changes to summary."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Compute the sum of two numbers"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[EffectClause(description="Pure function")],
        assertions=[
            AssertClause(predicate="a >= 0"),
            AssertClause(predicate="b >= 0"),
        ],
        metadata=Metadata(
            source_path="math.py",
            language="python",
            origin="manual",
        ),
    )


class TestIRMergerCleanMerge:
    """Tests for clean merges without conflicts."""

    def test_merge_no_changes(self, base_ir):
        """Test merge when no changes on either branch."""
        merger = IRMerger()
        result = merger.merge(base_ir, base_ir, base_ir)

        assert result.is_clean_merge()
        assert result.auto_merged_count == 0
        assert len(result.conflicts) == 0
        assert result.merged_ir.intent.summary == base_ir.intent.summary

    def test_merge_only_ours_changed(self, base_ir, ours_ir_no_conflict):
        """Test merge when only our branch changed."""
        merger = IRMerger()
        result = merger.merge(base_ir, ours_ir_no_conflict, base_ir)

        assert result.is_clean_merge()
        assert result.auto_merged_count > 0
        assert len(result.conflicts) == 0
        assert result.merged_ir.intent.rationale == "Basic arithmetic operation"
        assert len(result.merged_ir.assertions) == 3

    def test_merge_only_theirs_changed(self, base_ir, theirs_ir_no_conflict):
        """Test merge when only their branch changed."""
        merger = IRMerger()
        result = merger.merge(base_ir, base_ir, theirs_ir_no_conflict)

        assert result.is_clean_merge()
        assert result.auto_merged_count > 0
        assert len(result.conflicts) == 0
        assert len(result.merged_ir.assertions) == 3

    def test_merge_non_conflicting_changes(
        self, base_ir, ours_ir_no_conflict, theirs_ir_no_conflict
    ):
        """Test merge when both branches have non-conflicting changes."""
        merger = IRMerger()
        result = merger.merge(base_ir, ours_ir_no_conflict, theirs_ir_no_conflict)

        assert result.is_clean_merge()
        assert result.auto_merged_count > 0
        assert len(result.conflicts) == 0

        # Should have rationale from ours
        assert result.merged_ir.intent.rationale == "Basic arithmetic operation"

        # Should have both parameter descriptions
        params = result.merged_ir.signature.parameters
        assert params[0].description == "First number"
        assert params[1].description == "Second number"

        # Should have all assertions from both (union)
        assertions = {a.predicate for a in result.merged_ir.assertions}
        assert "a >= 0" in assertions
        assert "b >= 0" in assertions
        assert "result >= 0" in assertions
        assert "result == a + b" in assertions


class TestIRMergerConflicts:
    """Tests for conflict detection."""

    def test_detect_intent_summary_conflict(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test detection of conflicting intent summaries."""
        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        assert result.has_conflicts
        assert len(result.unresolved_conflicts()) > 0

        # Find the summary conflict
        summary_conflicts = [c for c in result.conflicts if "summary" in c.path]
        assert len(summary_conflicts) == 1

        conflict = summary_conflicts[0]
        assert conflict.base_value == "Calculate sum of two numbers"
        assert conflict.ours_value == "Add two integers together"
        assert conflict.theirs_value == "Compute the sum of two numbers"
        assert conflict.resolution == ConflictResolution.MANUAL_REQUIRED

    def test_auto_merge_same_change(self, base_ir):
        """Test auto-merge when both branches make the same change."""
        # Both change summary to the same value
        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Sum two numbers"),
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )
        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Sum two numbers"),
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        assert result.merged_ir.intent.summary == "Sum two numbers"


class TestMergeStrategies:
    """Tests for different merge strategies."""

    def test_strategy_ours(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test OURS strategy - always prefer our changes."""
        merger = IRMerger(strategy=MergeStrategy.OURS)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        assert not result.has_conflicts  # Resolved by strategy
        assert result.merged_ir.intent.summary == "Add two integers together"

        # Check that conflicts were resolved as TOOK_OURS
        for conflict in result.conflicts:
            assert conflict.resolution == ConflictResolution.TOOK_OURS

    def test_strategy_theirs(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test THEIRS strategy - always prefer their changes."""
        merger = IRMerger(strategy=MergeStrategy.THEIRS)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        assert not result.has_conflicts
        assert result.merged_ir.intent.summary == "Compute the sum of two numbers"

        for conflict in result.conflicts:
            assert conflict.resolution == ConflictResolution.TOOK_THEIRS

    def test_strategy_base(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test BASE strategy - keep base value."""
        merger = IRMerger(strategy=MergeStrategy.BASE)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        assert not result.has_conflicts
        assert result.merged_ir.intent.summary == "Calculate sum of two numbers"

        for conflict in result.conflicts:
            assert conflict.resolution == ConflictResolution.KEPT_BASE

    def test_strategy_manual(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test MANUAL strategy - mark all conflicts."""
        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        assert result.has_conflicts
        assert len(result.unresolved_conflicts()) > 0

    def test_override_strategy(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test overriding default strategy in merge call."""
        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        # Override with OURS for this specific merge
        result = merger.merge(
            base_ir, ours_ir_conflict, theirs_ir_conflict, strategy=MergeStrategy.OURS
        )

        assert not result.has_conflicts
        assert result.merged_ir.intent.summary == "Add two integers together"


class TestParameterMerging:
    """Tests for parameter list merging."""

    def test_merge_parameter_descriptions(
        self, base_ir, ours_ir_no_conflict, theirs_ir_no_conflict
    ):
        """Test merging parameter descriptions from both branches."""
        merger = IRMerger()
        result = merger.merge(base_ir, ours_ir_no_conflict, theirs_ir_no_conflict)

        assert result.is_clean_merge()
        params = result.merged_ir.signature.parameters
        assert params[0].description == "First number"
        assert params[1].description == "Second number"

    def test_parameter_count_conflict(self, base_ir):
        """Test conflict when parameter counts differ."""
        # Ours adds a parameter
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                    Parameter(name="c", type_hint="int"),
                ],
                returns="int",
            ),
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        # Theirs keeps original
        theirs = base_ir

        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours, theirs)

        assert result.has_conflicts
        param_conflicts = [c for c in result.conflicts if "parameter" in c.path.lower()]
        assert len(param_conflicts) > 0

    def test_parameter_type_conflict(self, base_ir):
        """Test conflict when parameter types differ."""
        # Ours changes type to float
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="float"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="float",
            ),
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        # Theirs changes to different type
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="number"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="number",
            ),
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours, theirs)

        assert result.has_conflicts
        type_conflicts = [c for c in result.conflicts if "type" in c.path.lower()]
        assert len(type_conflicts) > 0


class TestListMerging:
    """Tests for merging lists (assertions, effects)."""

    def test_merge_assertions_union(self, base_ir):
        """Test union merge of assertions."""
        # Ours adds one assertion
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
                AssertClause(predicate="b >= 0"),
                AssertClause(predicate="result >= 0"),
            ],
            metadata=base_ir.metadata,
        )

        # Theirs adds a different assertion
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
                AssertClause(predicate="b >= 0"),
                AssertClause(predicate="result == a + b"),
            ],
            metadata=base_ir.metadata,
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        assertions = {a.predicate for a in result.merged_ir.assertions}
        assert "a >= 0" in assertions
        assert "b >= 0" in assertions
        assert "result >= 0" in assertions
        assert "result == a + b" in assertions
        assert len(assertions) == 4

    def test_merge_assertions_both_remove(self, base_ir):
        """Test removing same assertion in both branches."""
        # Both remove "b >= 0"
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
            ],
            metadata=base_ir.metadata,
        )

        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
            ],
            metadata=base_ir.metadata,
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        assertions = {a.predicate for a in result.merged_ir.assertions}
        assert "a >= 0" in assertions
        assert "b >= 0" not in assertions

    def test_merge_assertions_add_remove_conflict(self, base_ir):
        """Test conflict when one adds and other removes."""
        # Ours removes "b >= 0"
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
            ],
            metadata=base_ir.metadata,
        )

        # Theirs modifies to "b > 0" (effectively remove + add)
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=[
                AssertClause(predicate="a >= 0"),
                AssertClause(predicate="b >= 0"),
                AssertClause(predicate="b > 0"),
            ],
            metadata=base_ir.metadata,
        )

        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours, theirs)

        # No conflict since we're doing union merge
        # "b >= 0" is in theirs but not ours - theirs wins
        assert not result.has_conflicts

    def test_merge_effects_union(self, base_ir):
        """Test union merge of effects."""
        # Ours adds an effect
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=[
                EffectClause(description="Pure function"),
                EffectClause(description="Returns positive value"),
            ],
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        # Theirs adds a different effect
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=[
                EffectClause(description="Pure function"),
                EffectClause(description="No side effects"),
            ],
            assertions=base_ir.assertions,
            metadata=base_ir.metadata,
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        effects = {e.description for e in result.merged_ir.effects}
        assert len(effects) == 3


class TestMetadataMerging:
    """Tests for metadata merging."""

    def test_merge_metadata_fields(self, base_ir):
        """Test merging metadata fields."""
        # Ours changes language
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=Metadata(
                source_path="math.py",
                language="python3",
                origin="manual",
            ),
        )

        # Theirs changes origin
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=Metadata(
                source_path="math.py",
                language="python",
                origin="generated",
            ),
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        assert result.merged_ir.metadata.language == "python3"
        assert result.merged_ir.metadata.origin == "generated"

    def test_merge_evidence_union(self, base_ir):
        """Test union merge of evidence lists."""
        # Ours adds evidence
        ours = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=Metadata(
                source_path="math.py",
                language="python",
                origin="manual",
                evidence=[
                    {"id": "codeql-1", "finding": "no issues"},
                ],
            ),
        )

        # Theirs adds different evidence
        theirs = IntermediateRepresentation(
            intent=base_ir.intent,
            signature=base_ir.signature,
            effects=base_ir.effects,
            assertions=base_ir.assertions,
            metadata=Metadata(
                source_path="math.py",
                language="python",
                origin="manual",
                evidence=[
                    {"id": "daikon-1", "invariant": "a + b > 0"},
                ],
            ),
        )

        merger = IRMerger()
        result = merger.merge(base_ir, ours, theirs)

        assert result.is_clean_merge()
        evidence_ids = {e["id"] for e in result.merged_ir.metadata.evidence}
        assert "codeql-1" in evidence_ids
        assert "daikon-1" in evidence_ids


class TestMergeResultSerialization:
    """Tests for MergeResult serialization."""

    def test_merge_result_to_dict(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test serializing merge result to dict."""
        merger = IRMerger(strategy=MergeStrategy.MANUAL)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        data = result.to_dict()

        assert "merged_ir" in data
        assert "conflicts" in data
        assert "auto_merged_count" in data
        assert "has_conflicts" in data
        assert "strategy" in data
        assert data["strategy"] == "manual"

    def test_merge_result_from_dict(self, base_ir, ours_ir_conflict, theirs_ir_conflict):
        """Test deserializing merge result from dict."""
        from lift_sys.ir import MergeResult

        merger = IRMerger(strategy=MergeStrategy.OURS)
        result = merger.merge(base_ir, ours_ir_conflict, theirs_ir_conflict)

        data = result.to_dict()
        restored = MergeResult.from_dict(data)

        assert restored.has_conflicts == result.has_conflicts
        assert restored.auto_merged_count == result.auto_merged_count
        assert restored.strategy == result.strategy
        assert len(restored.conflicts) == len(result.conflicts)


class TestProvenancePreservation:
    """Tests for provenance preservation through merge operations."""

    def test_merge_preserves_intent_provenance(self):
        """Test that provenance is preserved when merging intent."""
        from lift_sys.ir import Provenance, ProvenanceSource

        human_prov = Provenance.from_human(author="user123")
        agent_prov = Provenance.from_agent(author="claude", confidence=0.9)

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Base summary", provenance=human_prov),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        # Ours changes rationale but keeps summary
        ours = IntermediateRepresentation(
            intent=IntentClause(
                summary="Base summary",
                rationale="Added rationale",
                provenance=agent_prov,
            ),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        # Theirs doesn't change intent
        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Base summary", provenance=human_prov),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        merger = IRMerger()
        result = merger.merge(base, ours, theirs)

        # Should use ours provenance since ours changed
        assert result.merged_ir.intent.provenance is not None
        assert result.merged_ir.intent.provenance.source == ProvenanceSource.AGENT
        assert result.merged_ir.intent.provenance.author == "claude"

    def test_merge_preserves_signature_provenance(self):
        """Test that provenance is preserved when merging signature."""
        from lift_sys.ir import Provenance

        reverse_prov = Provenance.from_reverse(evidence_refs=["codeql-1"])

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
        )

        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[],
                returns="str",
                provenance=reverse_prov,
            ),
        )

        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="int"),
        )

        merger = IRMerger()
        result = merger.merge(base, ours, theirs)

        # Should preserve ours provenance
        assert result.merged_ir.signature.provenance is not None
        assert result.merged_ir.signature.provenance.evidence_refs == ["codeql-1"]

    def test_merge_preserves_parameter_provenance(self):
        """Test that provenance is preserved when merging parameters."""
        from lift_sys.ir import Provenance, ProvenanceSource

        human_prov = Provenance.from_human(author="user456")
        agent_prov = Provenance.from_agent(author="claude")

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=human_prov),
                ],
                returns="str",
            ),
        )

        # Ours changes parameter description
        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(
                        name="x",
                        type_hint="int",
                        description="Input value",
                        provenance=agent_prov,
                    ),
                ],
                returns="str",
            ),
        )

        # Theirs doesn't change parameter
        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=human_prov),
                ],
                returns="str",
            ),
        )

        merger = IRMerger()
        result = merger.merge(base, ours, theirs)

        # Should use ours provenance since ours changed
        param_prov = result.merged_ir.signature.parameters[0].provenance
        assert param_prov is not None
        assert param_prov.source == ProvenanceSource.AGENT
        assert param_prov.author == "claude"

    def test_merge_combines_provenance_on_conflict(self):
        """Test that provenance is combined when both branches change."""
        from lift_sys.ir import Provenance, ProvenanceSource

        human_prov = Provenance.from_human(author="user1")
        agent_prov1 = Provenance.from_agent(author="claude", confidence=0.9)
        agent_prov2 = Provenance.from_agent(author="gpt4", confidence=0.85)

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Base", provenance=human_prov),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Base", rationale="Ours", provenance=agent_prov1),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Base", rationale="Theirs", provenance=agent_prov2),
            signature=SigClause(name="test", parameters=[], returns="str"),
        )

        merger = IRMerger(strategy=MergeStrategy.AUTO)
        result = merger.merge(base, ours, theirs)

        # With AUTO strategy and conflicting provenance, should create merged provenance
        merged_prov = result.merged_ir.intent.provenance
        assert merged_prov is not None
        assert merged_prov.source == ProvenanceSource.MERGE
        assert merged_prov.author == "merge_system"
        # Should take lower confidence (more conservative)
        assert merged_prov.confidence == 0.85

    def test_merge_preserves_assertion_provenance(self):
        """Test that provenance is preserved when merging assertions."""
        from lift_sys.ir import Provenance

        reverse_prov = Provenance.from_reverse(evidence_refs=["daikon-1"])

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            assertions=[],
        )

        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            assertions=[
                AssertClause(predicate="x > 0", provenance=reverse_prov),
            ],
        )

        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            assertions=[],
        )

        merger = IRMerger()
        result = merger.merge(base, ours, theirs)

        # Should preserve assertion with provenance from ours
        assert len(result.merged_ir.assertions) == 1
        assert result.merged_ir.assertions[0].provenance is not None
        assert result.merged_ir.assertions[0].provenance.evidence_refs == ["daikon-1"]

    def test_merge_preserves_effect_provenance(self):
        """Test that provenance is preserved when merging effects."""
        from lift_sys.ir import Provenance

        agent_prov = Provenance.from_agent(author="claude")

        base = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            effects=[],
        )

        ours = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            effects=[],
        )

        theirs = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns="str"),
            effects=[
                EffectClause(description="Writes to file", provenance=agent_prov),
            ],
        )

        merger = IRMerger()
        result = merger.merge(base, ours, theirs)

        # Should preserve effect with provenance from theirs
        assert len(result.merged_ir.effects) == 1
        assert result.merged_ir.effects[0].provenance is not None
        assert result.merged_ir.effects[0].provenance.author == "claude"
