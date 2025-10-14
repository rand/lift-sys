"""Tests for IR provenance tracking."""

from datetime import UTC, datetime

from lift_sys.ir import (
    AssertClause,
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    Provenance,
    ProvenanceSource,
    SigClause,
)


class TestProvenance:
    """Tests for Provenance data structure."""

    def test_create_provenance_defaults(self):
        """Test creating provenance with defaults."""
        prov = Provenance()

        assert prov.source == ProvenanceSource.UNKNOWN
        assert prov.confidence == 1.0
        assert prov.author is None
        assert prov.evidence_refs == []
        assert prov.metadata == {}
        # Check timestamp is recent
        assert prov.timestamp is not None

    def test_create_provenance_full(self):
        """Test creating provenance with all fields."""
        timestamp = datetime.now(UTC).isoformat() + "Z"
        prov = Provenance(
            source=ProvenanceSource.HUMAN,
            confidence=0.95,
            timestamp=timestamp,
            author="user123",
            evidence_refs=["ev1", "ev2"],
            metadata={"model": "gpt-4"},
        )

        assert prov.source == ProvenanceSource.HUMAN
        assert prov.confidence == 0.95
        assert prov.timestamp == timestamp
        assert prov.author == "user123"
        assert prov.evidence_refs == ["ev1", "ev2"]
        assert prov.metadata == {"model": "gpt-4"}

    def test_provenance_serialization(self):
        """Test provenance serialization and deserialization."""
        prov = Provenance(
            source=ProvenanceSource.AGENT,
            confidence=0.85,
            author="claude",
            evidence_refs=["codeql-1"],
            metadata={"version": "1.0"},
        )

        data = prov.to_dict()
        restored = Provenance.from_dict(data)

        assert restored.source == prov.source
        assert restored.confidence == prov.confidence
        assert restored.author == prov.author
        assert restored.evidence_refs == prov.evidence_refs
        assert restored.metadata == prov.metadata

    def test_from_human_factory(self):
        """Test from_human factory method."""
        prov = Provenance.from_human(author="user123")

        assert prov.source == ProvenanceSource.HUMAN
        assert prov.confidence == 1.0
        assert prov.author == "user123"

    def test_from_agent_factory(self):
        """Test from_agent factory method."""
        prov = Provenance.from_agent(author="claude", confidence=0.92)

        assert prov.source == ProvenanceSource.AGENT
        assert prov.confidence == 0.92
        assert prov.author == "claude"

    def test_from_reverse_factory(self):
        """Test from_reverse factory method."""
        prov = Provenance.from_reverse(evidence_refs=["codeql-1", "daikon-1"])

        assert prov.source == ProvenanceSource.REVERSE
        assert prov.confidence == 0.85
        assert prov.evidence_refs == ["codeql-1", "daikon-1"]

    def test_from_merge_factory(self):
        """Test from_merge factory method."""
        prov = Provenance.from_merge(author="system")

        assert prov.source == ProvenanceSource.MERGE
        assert prov.author == "system"


class TestIntentClauseProvenance:
    """Tests for provenance on IntentClause."""

    def test_intent_without_provenance(self):
        """Test intent clause without provenance."""
        intent = IntentClause(summary="Test function")

        assert intent.provenance is None

    def test_intent_with_provenance(self):
        """Test intent clause with provenance."""
        prov = Provenance.from_human(author="user123")
        intent = IntentClause(
            summary="Test function",
            rationale="For testing",
            provenance=prov,
        )

        assert intent.provenance is not None
        assert intent.provenance.source == ProvenanceSource.HUMAN
        assert intent.provenance.author == "user123"

    def test_intent_serialization_with_provenance(self):
        """Test intent serialization includes provenance."""
        prov = Provenance.from_agent(author="claude")
        intent = IntentClause(summary="Test", provenance=prov)

        data = intent.to_dict()

        assert "provenance" in data
        assert data["provenance"]["source"] == "agent"
        assert data["provenance"]["author"] == "claude"

    def test_intent_serialization_without_provenance(self):
        """Test intent serialization without provenance."""
        intent = IntentClause(summary="Test")

        data = intent.to_dict()

        assert "provenance" not in data


class TestSignatureProvenance:
    """Tests for provenance on signature elements."""

    def test_parameter_with_provenance(self):
        """Test parameter with provenance."""
        prov = Provenance.from_reverse(evidence_refs=["ast-1"])
        param = Parameter(
            name="x",
            type_hint="int",
            description="Input value",
            provenance=prov,
        )

        assert param.provenance is not None
        assert param.provenance.source == ProvenanceSource.REVERSE
        assert param.provenance.evidence_refs == ["ast-1"]

    def test_signature_with_provenance(self):
        """Test signature clause with provenance."""
        prov = Provenance.from_human(author="user123")
        sig = SigClause(
            name="test_func",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="str",
            provenance=prov,
        )

        assert sig.provenance is not None
        assert sig.provenance.author == "user123"

    def test_parameter_serialization(self):
        """Test parameter serialization with provenance."""
        prov = Provenance.from_agent(author="claude", confidence=0.9)
        param = Parameter(name="x", type_hint="int", provenance=prov)

        data = param.to_dict()

        assert "provenance" in data
        assert data["provenance"]["source"] == "agent"
        assert data["provenance"]["confidence"] == 0.9


class TestAssertionEffectProvenance:
    """Tests for provenance on assertions and effects."""

    def test_assertion_with_provenance(self):
        """Test assertion with provenance."""
        prov = Provenance.from_reverse(evidence_refs=["daikon-1"])
        assertion = AssertClause(
            predicate="x > 0",
            rationale="From Daikon analysis",
            provenance=prov,
        )

        assert assertion.provenance is not None
        assert assertion.provenance.source == ProvenanceSource.REVERSE
        assert assertion.provenance.evidence_refs == ["daikon-1"]

    def test_effect_with_provenance(self):
        """Test effect with provenance."""
        prov = Provenance.from_agent(author="claude")
        effect = EffectClause(
            description="Writes to file",
            provenance=prov,
        )

        assert effect.provenance is not None
        assert effect.provenance.source == ProvenanceSource.AGENT

    def test_assertion_serialization(self):
        """Test assertion serialization with provenance."""
        prov = Provenance(source=ProvenanceSource.VERIFICATION, confidence=1.0)
        assertion = AssertClause(predicate="x > 0", provenance=prov)

        data = assertion.to_dict()

        assert "provenance" in data
        assert data["provenance"]["source"] == "verification"

    def test_effect_serialization(self):
        """Test effect serialization with provenance."""
        prov = Provenance.from_human(author="user456")
        effect = EffectClause(description="Side effect", provenance=prov)

        data = effect.to_dict()

        assert "provenance" in data
        assert data["provenance"]["author"] == "user456"


class TestIRProvenance:
    """Tests for provenance on complete IR."""

    def test_ir_with_mixed_provenance(self):
        """Test IR with different provenance for different elements."""
        human_prov = Provenance.from_human(author="user123")
        agent_prov = Provenance.from_agent(author="claude", confidence=0.9)
        reverse_prov = Provenance.from_reverse(evidence_refs=["codeql-1"])

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test", provenance=human_prov),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=reverse_prov),
                ],
                returns="str",
                provenance=agent_prov,
            ),
            assertions=[
                AssertClause(predicate="x > 0", provenance=reverse_prov),
            ],
        )

        # Check intent provenance
        assert ir.intent.provenance.source == ProvenanceSource.HUMAN
        assert ir.intent.provenance.author == "user123"

        # Check signature provenance
        assert ir.signature.provenance.source == ProvenanceSource.AGENT
        assert ir.signature.provenance.confidence == 0.9

        # Check parameter provenance
        assert ir.signature.parameters[0].provenance.source == ProvenanceSource.REVERSE

        # Check assertion provenance
        assert ir.assertions[0].provenance.source == ProvenanceSource.REVERSE

    def test_ir_serialization_with_provenance(self):
        """Test complete IR serialization with provenance."""
        prov = Provenance.from_agent(author="claude")

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test", provenance=prov),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=prov),
                ],
                returns="str",
                provenance=prov,
            ),
            effects=[
                EffectClause(description="Side effect", provenance=prov),
            ],
            assertions=[
                AssertClause(predicate="x > 0", provenance=prov),
            ],
        )

        data = ir.to_dict()

        # Check intent provenance
        assert "provenance" in data["intent"]
        assert data["intent"]["provenance"]["source"] == "agent"

        # Check signature provenance
        assert "provenance" in data["signature"]

        # Check parameter provenance
        assert "provenance" in data["signature"]["parameters"][0]

        # Check effect provenance
        assert "provenance" in data["effects"][0]

        # Check assertion provenance
        assert "provenance" in data["assertions"][0]

    def test_ir_deserialization_with_provenance(self):
        """Test IR deserialization preserves provenance."""
        prov = Provenance.from_human(author="user123")

        original_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test", provenance=prov),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=prov),
                ],
                returns="str",
                provenance=prov,
            ),
        )

        data = original_ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(data)

        # Check intent provenance
        assert restored_ir.intent.provenance is not None
        assert restored_ir.intent.provenance.source == ProvenanceSource.HUMAN
        assert restored_ir.intent.provenance.author == "user123"

        # Check signature provenance
        assert restored_ir.signature.provenance is not None
        assert restored_ir.signature.provenance.source == ProvenanceSource.HUMAN

        # Check parameter provenance
        assert restored_ir.signature.parameters[0].provenance is not None
        assert restored_ir.signature.parameters[0].provenance.author == "user123"

    def test_ir_without_provenance_backward_compatible(self):
        """Test IR without provenance is backward compatible."""
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="str",
            ),
        )

        # Serialize and deserialize
        data = ir.to_dict()
        restored_ir = IntermediateRepresentation.from_dict(data)

        # All provenance should be None
        assert restored_ir.intent.provenance is None
        assert restored_ir.signature.provenance is None
        assert restored_ir.signature.parameters[0].provenance is None


class TestProvenanceWorkflows:
    """Tests for common provenance workflows."""

    def test_reverse_mode_workflow(self):
        """Test typical reverse mode provenance."""
        # Reverse mode extracts IR with evidence
        prov = Provenance.from_reverse(
            evidence_refs=["codeql-sql-injection-1", "daikon-inv-1"],
            author="reverse_lifter",
            metadata={"lifter_version": "1.0"},
        )

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Get user from database", provenance=prov),
            signature=SigClause(
                name="get_user",
                parameters=[
                    Parameter(name="username", type_hint="str", provenance=prov),
                ],
                returns="dict",
                provenance=prov,
            ),
            assertions=[
                AssertClause(predicate="len(username) > 0", provenance=prov),
            ],
        )

        # All elements should have reverse provenance
        assert ir.intent.provenance.source == ProvenanceSource.REVERSE
        assert ir.signature.provenance.source == ProvenanceSource.REVERSE
        assert ir.assertions[0].provenance.source == ProvenanceSource.REVERSE

        # Should reference evidence
        assert "codeql-sql-injection-1" in ir.intent.provenance.evidence_refs

    def test_human_refinement_workflow(self):
        """Test human refining an agent-generated IR."""
        # Agent creates initial IR
        agent_prov = Provenance.from_agent(author="claude", confidence=0.85)

        # Human refines the intent
        human_prov = Provenance.from_human(author="user123")

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Calculate sum of two numbers",
                rationale="Basic arithmetic for positive integers",
                provenance=human_prov,  # Refined by human
            ),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int", provenance=agent_prov),
                    Parameter(name="b", type_hint="int", provenance=agent_prov),
                ],
                returns="int",
                provenance=agent_prov,  # Generated by agent
            ),
        )

        # Intent should have human provenance
        assert ir.intent.provenance.source == ProvenanceSource.HUMAN
        assert ir.intent.provenance.author == "user123"

        # Signature should have agent provenance
        assert ir.signature.provenance.source == ProvenanceSource.AGENT
        assert ir.signature.provenance.confidence == 0.85

    def test_merge_provenance(self):
        """Test provenance for merged elements."""
        merge_prov = Provenance.from_merge(
            author="merge_system",
            metadata={
                "merge_strategy": "ours",
                "base_version": 1,
                "ours_version": 2,
                "theirs_version": 3,
            },
        )

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Merged summary",
                provenance=merge_prov,
            ),
            signature=SigClause(
                name="merged_func",
                parameters=[],
                returns="str",
                provenance=merge_prov,
            ),
        )

        assert ir.intent.provenance.source == ProvenanceSource.MERGE
        assert ir.intent.provenance.metadata["merge_strategy"] == "ours"

    def test_confidence_tracking(self):
        """Test tracking confidence scores."""
        # High confidence human input
        high_conf = Provenance.from_human(author="expert")
        assert high_conf.confidence == 1.0

        # Medium confidence agent
        medium_conf = Provenance.from_agent(author="claude", confidence=0.85)
        assert medium_conf.confidence == 0.85

        # Lower confidence from reverse mode
        low_conf = Provenance.from_reverse()
        assert low_conf.confidence == 0.85

        # Can track which elements need review
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="High confidence", provenance=high_conf),
            signature=SigClause(
                name="test",
                parameters=[
                    Parameter(name="x", type_hint="int", provenance=medium_conf),
                ],
                returns="str",
                provenance=low_conf,
            ),
        )

        # Identify low confidence elements
        low_confidence_elements = []
        if ir.intent.provenance and ir.intent.provenance.confidence < 0.9:
            low_confidence_elements.append("intent")
        if ir.signature.provenance and ir.signature.provenance.confidence < 0.9:
            low_confidence_elements.append("signature")

        assert "signature" in low_confidence_elements
        assert "intent" not in low_confidence_elements
