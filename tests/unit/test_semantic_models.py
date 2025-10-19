"""Unit tests for semantic IR data models.

Tests cover:
- All data classes with serialization/deserialization
- Validation logic and edge cases
- Helper methods and properties
- Round-trip JSON serialization with no data loss
- Error handling for invalid inputs

Target: 100% test coverage
"""

import pytest

from lift_sys.ir.semantic_models import (
    Ambiguity,
    AnnotationLayer,
    EnhancedIR,
    Entity,
    EntityType,
    Highlight,
    ImplicitTerm,
    Intent,
    RefinementState,
    RefinementStep,
    Relationship,
    SemanticMetadata,
    SemanticType,
    Span,
    TypedHole,
)

# ============================================================================
# EntityType Tests
# ============================================================================


def test_entity_type_values():
    """Test EntityType enum values."""
    assert EntityType.CONCEPT.value == "concept"
    assert EntityType.DATA_STRUCTURE.value == "data"
    assert EntityType.FUNCTION.value == "function"
    assert EntityType.ATTRIBUTE.value == "attribute"
    assert EntityType.CONSTRAINT.value == "constraint"
    assert EntityType.ACTOR.value == "actor"


def test_entity_type_serialization():
    """Test EntityType serialization."""
    entity_type = EntityType.DATA_STRUCTURE
    serialized = entity_type.to_dict()
    assert serialized == "data"

    deserialized = EntityType.from_dict("data")
    assert deserialized == EntityType.DATA_STRUCTURE


# ============================================================================
# SemanticType Tests
# ============================================================================


def test_semantic_type_creation():
    """Test SemanticType creation with defaults."""
    sem_type = SemanticType("Document")
    assert sem_type.type_name == "Document"
    assert sem_type.confidence == 1.0
    assert sem_type.source is None


def test_semantic_type_with_confidence():
    """Test SemanticType with custom confidence."""
    sem_type = SemanticType("User", confidence=0.85, source="coreference")
    assert sem_type.confidence == 0.85
    assert sem_type.source == "coreference"


def test_semantic_type_invalid_confidence():
    """Test SemanticType rejects invalid confidence."""
    with pytest.raises(ValueError, match="Confidence must be in"):
        SemanticType("Test", confidence=1.5)

    with pytest.raises(ValueError, match="Confidence must be in"):
        SemanticType("Test", confidence=-0.1)


def test_semantic_type_serialization():
    """Test SemanticType round-trip serialization."""
    original = SemanticType("Document", confidence=0.9, source="context")
    data = original.to_dict()

    assert data == {"type_name": "Document", "confidence": 0.9, "source": "context"}

    restored = SemanticType.from_dict(data)
    assert restored.type_name == original.type_name
    assert restored.confidence == original.confidence
    assert restored.source == original.source


# ============================================================================
# Span Tests
# ============================================================================


def test_span_creation():
    """Test Span creation."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    assert span.start == 10
    assert span.length == 5
    assert span.token_start == 2
    assert span.token_length == 1


def test_span_properties():
    """Test Span computed properties."""
    span = Span(start=10, length=5, token_start=2, token_length=3)
    assert span.end == 15
    assert span.token_end == 5


def test_span_overlaps():
    """Test Span overlap detection."""
    span1 = Span(start=10, length=5, token_start=2, token_length=1)  # 10-15
    span2 = Span(start=12, length=5, token_start=3, token_length=1)  # 12-17
    span3 = Span(start=20, length=5, token_start=5, token_length=1)  # 20-25

    assert span1.overlaps(span2)
    assert span2.overlaps(span1)
    assert not span1.overlaps(span3)
    assert not span3.overlaps(span1)


def test_span_contains():
    """Test Span contains position."""
    span = Span(start=10, length=5, token_start=2, token_length=1)  # 10-15

    assert span.contains(10)
    assert span.contains(12)
    assert span.contains(14)
    assert not span.contains(15)  # end is exclusive
    assert not span.contains(9)


def test_span_validation():
    """Test Span validation."""
    with pytest.raises(ValueError, match="Span start must be"):
        Span(start=-1, length=5, token_start=0, token_length=1)

    with pytest.raises(ValueError, match="Span length must be"):
        Span(start=0, length=-1, token_start=0, token_length=1)

    with pytest.raises(ValueError, match="Token start must be"):
        Span(start=0, length=5, token_start=-1, token_length=1)

    with pytest.raises(ValueError, match="Token length must be"):
        Span(start=0, length=5, token_start=0, token_length=-1)


def test_span_serialization():
    """Test Span round-trip serialization."""
    original = Span(start=10, length=5, token_start=2, token_length=1)
    data = original.to_dict()

    assert data == {"start": 10, "length": 5, "token_start": 2, "token_length": 1}

    restored = Span.from_dict(data)
    assert restored.start == original.start
    assert restored.length == original.length
    assert restored.token_start == original.token_start
    assert restored.token_length == original.token_length


# ============================================================================
# Entity Tests
# ============================================================================


def test_entity_creation():
    """Test Entity creation with minimal fields."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    assert entity.id == "e1"
    assert entity.name == "report"
    assert entity.entity_type == EntityType.DATA_STRUCTURE
    assert entity.semantic_type is None
    assert entity.resolved is False
    assert len(entity.attributes) == 0
    assert len(entity.references) == 0


def test_entity_with_all_fields():
    """Test Entity with all fields populated."""
    span = Span(start=10, length=6, token_start=2, token_length=1)
    sem_type = SemanticType("Report", confidence=0.9)
    attr = Entity(id="a1", name="shareable", entity_type=EntityType.ATTRIBUTE)

    entity = Entity(
        id="e1",
        name="report",
        entity_type=EntityType.DATA_STRUCTURE,
        semantic_type=sem_type,
        syntactic_type="noun",
        span=span,
        resolved=True,
        linked_to="src/models/report.py:Report",
        attributes=[attr],
        references=["e2", "e3"],
    )

    assert entity.semantic_type.type_name == "Report"
    assert entity.span.start == 10
    assert entity.resolved is True
    assert entity.linked_to == "src/models/report.py:Report"
    assert len(entity.attributes) == 1
    assert len(entity.references) == 2


def test_entity_serialization():
    """Test Entity round-trip serialization."""
    span = Span(start=10, length=6, token_start=2, token_length=1)
    sem_type = SemanticType("Report", confidence=0.9)
    attr = Entity(id="a1", name="shareable", entity_type=EntityType.ATTRIBUTE)

    original = Entity(
        id="e1",
        name="report",
        entity_type=EntityType.DATA_STRUCTURE,
        semantic_type=sem_type,
        span=span,
        resolved=True,
        attributes=[attr],
        references=["e2"],
    )

    data = original.to_dict()
    restored = Entity.from_dict(data)

    assert restored.id == original.id
    assert restored.name == original.name
    assert restored.entity_type == original.entity_type
    assert restored.semantic_type.type_name == original.semantic_type.type_name
    assert restored.span.start == original.span.start
    assert restored.resolved == original.resolved
    assert len(restored.attributes) == 1
    assert restored.attributes[0].id == "a1"
    assert len(restored.references) == 1


# ============================================================================
# Relationship Tests
# ============================================================================


def test_relationship_creation():
    """Test Relationship creation."""
    rel = Relationship(id="r1", type="creates", source="e2", target="e1")
    assert rel.id == "r1"
    assert rel.type == "creates"
    assert rel.source == "e2"
    assert rel.target == "e1"
    assert rel.confidence == 1.0
    assert rel.derived_from is None


def test_relationship_with_confidence():
    """Test Relationship with custom confidence."""
    rel = Relationship(
        id="r1",
        type="depends_on",
        source="e1",
        target="e2",
        confidence=0.75,
        derived_from="clause_analysis",
    )
    assert rel.confidence == 0.75
    assert rel.derived_from == "clause_analysis"


def test_relationship_invalid_confidence():
    """Test Relationship rejects invalid confidence."""
    with pytest.raises(ValueError, match="Confidence must be in"):
        Relationship(id="r1", type="test", source="e1", target="e2", confidence=2.0)


def test_relationship_serialization():
    """Test Relationship round-trip serialization."""
    original = Relationship(
        id="r1", type="modifies", source="e1", target="e2", confidence=0.85, derived_from="analysis"
    )

    data = original.to_dict()
    restored = Relationship.from_dict(data)

    assert restored.id == original.id
    assert restored.type == original.type
    assert restored.source == original.source
    assert restored.target == original.target
    assert restored.confidence == original.confidence
    assert restored.derived_from == original.derived_from


# ============================================================================
# TypedHole Tests
# ============================================================================


def test_typed_hole_creation():
    """Test TypedHole creation."""
    location = Span(start=10, length=5, token_start=2, token_length=1)
    hole = TypedHole(
        id="hole_1", kind="type_specification", location=location, context="Create a report"
    )
    assert hole.id == "hole_1"
    assert hole.kind == "type_specification"
    assert hole.context == "Create a report"
    assert hole.required is True
    assert hole.resolved is False
    assert len(hole.suggestions) == 0


def test_typed_hole_with_suggestions():
    """Test TypedHole with suggestions."""
    location = Span(start=10, length=5, token_start=2, token_length=1)
    hole = TypedHole(
        id="hole_1",
        kind="type_specification",
        location=location,
        context="Create a report",
        suggestions=["PDF", "JSON", "HTML"],
        required=False,
    )
    assert len(hole.suggestions) == 3
    assert hole.required is False


def test_typed_hole_serialization():
    """Test TypedHole round-trip serialization."""
    location = Span(start=10, length=5, token_start=2, token_length=1)
    original = TypedHole(
        id="hole_1",
        kind="type_specification",
        location=location,
        context="Create a report",
        suggestions=["PDF", "JSON"],
        resolved=True,
        resolution="PDF",
    )

    data = original.to_dict()
    restored = TypedHole.from_dict(data)

    assert restored.id == original.id
    assert restored.kind == original.kind
    assert restored.context == original.context
    assert restored.suggestions == original.suggestions
    assert restored.resolved == original.resolved
    assert restored.resolution == original.resolution


# ============================================================================
# Ambiguity Tests
# ============================================================================


def test_ambiguity_creation():
    """Test Ambiguity creation."""
    location = Span(start=15, length=9, token_start=3, token_length=1)
    ambiguity = Ambiguity(
        id="amb_1",
        type="vague_term",
        location=location,
        text="shareable",
        issue="Unclear what 'shareable' means",
        severity="medium",
    )
    assert ambiguity.id == "amb_1"
    assert ambiguity.type == "vague_term"
    assert ambiguity.text == "shareable"
    assert ambiguity.severity == "medium"
    assert ambiguity.resolved is False


def test_ambiguity_invalid_severity():
    """Test Ambiguity rejects invalid severity."""
    location = Span(start=0, length=5, token_start=0, token_length=1)
    with pytest.raises(ValueError, match="Severity must be"):
        Ambiguity(
            id="amb_1",
            type="test",
            location=location,
            text="test",
            issue="test",
            severity="critical",  # invalid
        )


def test_ambiguity_serialization():
    """Test Ambiguity round-trip serialization."""
    location = Span(start=15, length=9, token_start=3, token_length=1)
    original = Ambiguity(
        id="amb_1",
        type="vague_term",
        location=location,
        text="shareable",
        issue="Unclear meaning",
        severity="high",
        suggestions=["public", "private"],
        resolved=True,
        resolution="public",
    )

    data = original.to_dict()
    restored = Ambiguity.from_dict(data)

    assert restored.id == original.id
    assert restored.type == original.type
    assert restored.text == original.text
    assert restored.severity == original.severity
    assert restored.suggestions == original.suggestions
    assert restored.resolved == original.resolved
    assert restored.resolution == original.resolution


# ============================================================================
# ImplicitTerm Tests
# ============================================================================


def test_implicit_term_creation():
    """Test ImplicitTerm creation."""
    term = ImplicitTerm(
        id="imp_1", type="precondition", inferred_from="make it shareable", term="report must exist"
    )
    assert term.id == "imp_1"
    assert term.type == "precondition"
    assert term.confidence == 0.5  # default
    assert term.accepted is False


def test_implicit_term_with_location():
    """Test ImplicitTerm with location."""
    location = Span(start=20, length=5, token_start=4, token_length=1)
    term = ImplicitTerm(
        id="imp_1",
        type="missing_parameter",
        inferred_from="send notification",
        term="recipient email address",
        confidence=0.85,
        location=location,
        accepted=True,
    )
    assert term.confidence == 0.85
    assert term.location.start == 20
    assert term.accepted is True


def test_implicit_term_invalid_confidence():
    """Test ImplicitTerm rejects invalid confidence."""
    with pytest.raises(ValueError, match="Confidence must be in"):
        ImplicitTerm(id="imp_1", type="test", inferred_from="test", term="test", confidence=1.5)


def test_implicit_term_serialization():
    """Test ImplicitTerm round-trip serialization."""
    location = Span(start=20, length=5, token_start=4, token_length=1)
    original = ImplicitTerm(
        id="imp_1",
        type="precondition",
        inferred_from="process data",
        term="data must be validated",
        confidence=0.9,
        location=location,
        accepted=True,
    )

    data = original.to_dict()
    restored = ImplicitTerm.from_dict(data)

    assert restored.id == original.id
    assert restored.type == original.type
    assert restored.inferred_from == original.inferred_from
    assert restored.term == original.term
    assert restored.confidence == original.confidence
    assert restored.location.start == original.location.start
    assert restored.accepted == original.accepted


# ============================================================================
# Intent Tests
# ============================================================================


def test_intent_creation():
    """Test Intent creation."""
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")
    assert intent.signature == "Create<Report>"
    assert intent.operation == "CREATE"
    assert intent.target == "report"
    assert len(intent.constraints) == 0
    assert len(intent.sub_intents) == 0
    assert intent.confidence == 1.0


def test_intent_with_hierarchy():
    """Test Intent with sub-intents."""
    sub1 = Intent(signature="Create<Report>", operation="CREATE", target="report")
    sub2 = Intent(signature="MakeShareable<Report>", operation="UPDATE", target="report")

    parent = Intent(
        signature="CreateAndShare<Report>",
        operation="CREATE_UPDATE",
        target="report",
        constraints=["user.authenticated == True"],
        sub_intents=[sub1, sub2],
        confidence=0.95,
    )

    assert len(parent.sub_intents) == 2
    assert len(parent.constraints) == 1
    assert parent.confidence == 0.95


def test_intent_serialization():
    """Test Intent round-trip serialization with hierarchy."""
    sub1 = Intent(signature="Create<Report>", operation="CREATE", target="report")
    sub2 = Intent(signature="Update<Report>", operation="UPDATE", target="report")

    original = Intent(
        signature="CreateAndUpdate<Report>",
        operation="COMPOSITE",
        target="report",
        constraints=["user.is_admin"],
        sub_intents=[sub1, sub2],
        confidence=0.9,
    )

    data = original.to_dict()
    restored = Intent.from_dict(data)

    assert restored.signature == original.signature
    assert restored.operation == original.operation
    assert restored.target == original.target
    assert restored.constraints == original.constraints
    assert len(restored.sub_intents) == 2
    assert restored.sub_intents[0].signature == "Create<Report>"
    assert restored.confidence == original.confidence


# ============================================================================
# SemanticMetadata Tests
# ============================================================================


def test_semantic_metadata_creation():
    """Test SemanticMetadata creation."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    rel = Relationship(id="r1", type="creates", source="e2", target="e1")
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")

    metadata = SemanticMetadata(
        entities={"e1": entity}, relationships=[rel], intent_hierarchy=intent
    )

    assert len(metadata.entities) == 1
    assert len(metadata.relationships) == 1
    assert metadata.intent_hierarchy.signature == "Create<Report>"
    assert len(metadata.typed_holes) == 0
    assert len(metadata.ambiguities) == 0


def test_semantic_metadata_with_all_fields():
    """Test SemanticMetadata with all fields."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    rel = Relationship(id="r1", type="creates", source="e2", target="e1")
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")

    location = Span(start=10, length=5, token_start=2, token_length=1)
    hole = TypedHole(id="hole_1", kind="type_spec", location=location, context="test")
    ambiguity = Ambiguity(
        id="amb_1",
        type="vague_term",
        location=location,
        text="shareable",
        issue="unclear",
        severity="medium",
    )
    implicit = ImplicitTerm(
        id="imp_1", type="precondition", inferred_from="test", term="must exist"
    )

    metadata = SemanticMetadata(
        entities={"e1": entity},
        relationships=[rel],
        intent_hierarchy=intent,
        typed_holes=[hole],
        ambiguities=[ambiguity],
        implicit_terms=[implicit],
        context_used=["src/models/report.py"],
    )

    assert len(metadata.typed_holes) == 1
    assert len(metadata.ambiguities) == 1
    assert len(metadata.implicit_terms) == 1
    assert len(metadata.context_used) == 1


def test_semantic_metadata_serialization():
    """Test SemanticMetadata round-trip serialization."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    rel = Relationship(id="r1", type="creates", source="e2", target="e1")
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")

    original = SemanticMetadata(
        entities={"e1": entity},
        relationships=[rel],
        intent_hierarchy=intent,
        context_used=["src/models/report.py"],
    )

    data = original.to_dict()
    restored = SemanticMetadata.from_dict(data)

    assert len(restored.entities) == 1
    assert "e1" in restored.entities
    assert restored.entities["e1"].name == "report"
    assert len(restored.relationships) == 1
    assert restored.intent_hierarchy.signature == "Create<Report>"
    assert restored.context_used == ["src/models/report.py"]


# ============================================================================
# Highlight Tests
# ============================================================================


def test_highlight_creation():
    """Test Highlight creation."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    highlight = Highlight(span=span, color="entity-data", type="entity")
    assert highlight.span.start == 10
    assert highlight.color == "entity-data"
    assert highlight.type == "entity"
    assert highlight.tooltip is None
    assert highlight.linked_to is None


def test_highlight_with_tooltip():
    """Test Highlight with tooltip and link."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    highlight = Highlight(
        span=span,
        color="entity-data",
        type="entity",
        tooltip="Report (Document) - resolved",
        linked_to="ir.signature.returns",
    )
    assert highlight.tooltip == "Report (Document) - resolved"
    assert highlight.linked_to == "ir.signature.returns"


def test_highlight_serialization():
    """Test Highlight round-trip serialization."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    original = Highlight(
        span=span,
        color="entity-actor",
        type="entity",
        tooltip="User entity",
        linked_to="ir.entities.e2",
    )

    data = original.to_dict()
    restored = Highlight.from_dict(data)

    assert restored.span.start == original.span.start
    assert restored.color == original.color
    assert restored.type == original.type
    assert restored.tooltip == original.tooltip
    assert restored.linked_to == original.linked_to


# ============================================================================
# AnnotationLayer Tests
# ============================================================================


def test_annotation_layer_creation():
    """Test AnnotationLayer creation."""
    layer = AnnotationLayer()
    assert len(layer.prompt_highlights) == 0
    assert len(layer.ir_highlights) == 0
    assert len(layer.prompt_to_ir_links) == 0
    assert len(layer.ir_to_prompt_links) == 0


def test_annotation_layer_add_bidirectional_link():
    """Test AnnotationLayer bidirectional link addition."""
    layer = AnnotationLayer()
    layer.add_bidirectional_link("token_3", "ir.signature.returns")

    assert layer.prompt_to_ir_links["token_3"] == "ir.signature.returns"
    assert layer.ir_to_prompt_links["ir.signature.returns"] == "token_3"


def test_annotation_layer_with_highlights():
    """Test AnnotationLayer with highlights."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    highlight = Highlight(span=span, color="entity-data", type="entity")

    layer = AnnotationLayer(
        prompt_highlights=[highlight],
        ir_highlights=[],
        prompt_to_ir_links={"token_2": "ir.entities.e1"},
        ir_to_prompt_links={"ir.entities.e1": "token_2"},
    )

    assert len(layer.prompt_highlights) == 1
    assert len(layer.prompt_to_ir_links) == 1


def test_annotation_layer_serialization():
    """Test AnnotationLayer round-trip serialization."""
    span = Span(start=10, length=5, token_start=2, token_length=1)
    highlight = Highlight(span=span, color="entity-data", type="entity")

    original = AnnotationLayer(
        prompt_highlights=[highlight],
        prompt_to_ir_links={"token_2": "ir.entities.e1"},
        ir_to_prompt_links={"ir.entities.e1": "token_2"},
    )

    data = original.to_dict()
    restored = AnnotationLayer.from_dict(data)

    assert len(restored.prompt_highlights) == 1
    assert restored.prompt_to_ir_links == original.prompt_to_ir_links
    assert restored.ir_to_prompt_links == original.ir_to_prompt_links


# ============================================================================
# RefinementStep Tests
# ============================================================================


def test_refinement_step_creation():
    """Test RefinementStep creation."""
    step = RefinementStep(
        step_number=1,
        hole_or_ambiguity_id="hole_1",
        user_choice="PDF",
        timestamp="2025-10-18T10:30:00Z",
        ir_version_before=0,
        ir_version_after=1,
    )
    assert step.step_number == 1
    assert step.hole_or_ambiguity_id == "hole_1"
    assert step.user_choice == "PDF"
    assert step.ir_version_before == 0
    assert step.ir_version_after == 1


def test_refinement_step_serialization():
    """Test RefinementStep round-trip serialization."""
    original = RefinementStep(
        step_number=1,
        hole_or_ambiguity_id="hole_1",
        user_choice="PDF",
        timestamp="2025-10-18T10:30:00Z",
        ir_version_before=0,
        ir_version_after=1,
    )

    data = original.to_dict()
    restored = RefinementStep.from_dict(data)

    assert restored.step_number == original.step_number
    assert restored.hole_or_ambiguity_id == original.hole_or_ambiguity_id
    assert restored.user_choice == original.user_choice
    assert restored.timestamp == original.timestamp


# ============================================================================
# RefinementState Tests
# ============================================================================


def test_refinement_state_creation():
    """Test RefinementState creation."""
    state = RefinementState()
    assert len(state.history) == 0
    assert len(state.unresolved_holes) == 0
    assert len(state.unresolved_ambiguities) == 0
    assert state.current_version == 0
    assert state.is_complete is False


def test_refinement_state_record_resolution():
    """Test RefinementState resolution recording."""
    state = RefinementState(unresolved_holes=["hole_1", "hole_2"], unresolved_ambiguities=["amb_1"])

    state.record_resolution("hole_1", "PDF", "2025-10-18T10:30:00Z")

    assert len(state.history) == 1
    assert state.current_version == 1
    assert "hole_1" not in state.unresolved_holes
    assert "hole_2" in state.unresolved_holes
    assert state.is_complete is False  # still has hole_2 and amb_1


def test_refinement_state_complete():
    """Test RefinementState completion."""
    state = RefinementState(unresolved_holes=["hole_1"], unresolved_ambiguities=[])

    state.record_resolution("hole_1", "PDF")

    assert len(state.unresolved_holes) == 0
    assert state.is_complete is True


def test_refinement_state_serialization():
    """Test RefinementState round-trip serialization."""
    step = RefinementStep(
        step_number=1,
        hole_or_ambiguity_id="hole_1",
        user_choice="PDF",
        timestamp="2025-10-18T10:30:00Z",
        ir_version_before=0,
        ir_version_after=1,
    )

    original = RefinementState(
        history=[step],
        unresolved_holes=["hole_2"],
        unresolved_ambiguities=["amb_1"],
        current_version=1,
        is_complete=False,
    )

    data = original.to_dict()
    restored = RefinementState.from_dict(data)

    assert len(restored.history) == 1
    assert restored.history[0].hole_or_ambiguity_id == "hole_1"
    assert restored.unresolved_holes == ["hole_2"]
    assert restored.unresolved_ambiguities == ["amb_1"]
    assert restored.current_version == 1
    assert restored.is_complete is False


# ============================================================================
# EnhancedIR Tests
# ============================================================================


def test_enhanced_ir_creation():
    """Test EnhancedIR creation."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")
    semantic = SemanticMetadata(entities={"e1": entity}, relationships=[], intent_hierarchy=intent)
    annotations = AnnotationLayer()
    refinement = RefinementState()

    enhanced_ir = EnhancedIR(
        semantic=semantic,
        annotations=annotations,
        refinement=refinement,
        source_prompt="Create a report",
    )

    assert enhanced_ir.source_prompt == "Create a report"
    assert enhanced_ir.source_code is None
    assert enhanced_ir.created_at is not None
    assert enhanced_ir.updated_at is not None


def test_enhanced_ir_timestamps():
    """Test EnhancedIR automatic timestamp generation."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")
    semantic = SemanticMetadata(entities={"e1": entity}, relationships=[], intent_hierarchy=intent)

    enhanced_ir = EnhancedIR(
        semantic=semantic,
        annotations=AnnotationLayer(),
        refinement=RefinementState(),
        source_prompt="test",
    )

    # Timestamps should be auto-generated
    assert enhanced_ir.created_at is not None
    assert enhanced_ir.updated_at is not None

    # Update timestamp should change
    original_updated = enhanced_ir.updated_at
    import time

    time.sleep(0.01)  # Small delay to ensure timestamp changes
    enhanced_ir.update_timestamp()
    assert enhanced_ir.updated_at != original_updated


def test_enhanced_ir_properties():
    """Test EnhancedIR computed properties."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")

    location = Span(start=10, length=5, token_start=2, token_length=1)
    hole = TypedHole(id="hole_1", kind="type_spec", location=location, context="test")
    ambiguity = Ambiguity(
        id="amb_1",
        type="vague_term",
        location=location,
        text="test",
        issue="test",
        severity="medium",
    )

    semantic = SemanticMetadata(
        entities={"e1": entity},
        relationships=[],
        intent_hierarchy=intent,
        typed_holes=[hole],
        ambiguities=[ambiguity],
    )

    refinement = RefinementState(unresolved_holes=["hole_1"], unresolved_ambiguities=["amb_1"])

    enhanced_ir = EnhancedIR(
        semantic=semantic,
        annotations=AnnotationLayer(),
        refinement=refinement,
        source_prompt="test",
    )

    assert enhanced_ir.has_unresolved_items is True
    assert enhanced_ir.completion_percentage == 0.0

    # Resolve one item
    refinement.record_resolution("hole_1", "PDF")
    assert enhanced_ir.completion_percentage == 0.5

    # Resolve remaining item
    refinement.record_resolution("amb_1", "public")
    assert enhanced_ir.completion_percentage == 1.0
    assert enhanced_ir.has_unresolved_items is False


def test_enhanced_ir_json_serialization():
    """Test EnhancedIR JSON round-trip serialization."""
    entity = Entity(id="e1", name="report", entity_type=EntityType.DATA_STRUCTURE)
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report")
    semantic = SemanticMetadata(entities={"e1": entity}, relationships=[], intent_hierarchy=intent)

    original = EnhancedIR(
        semantic=semantic,
        annotations=AnnotationLayer(),
        refinement=RefinementState(),
        source_prompt="Create a report",
        metadata={"language": "python", "origin": "forward"},
    )

    # Test JSON serialization
    json_str = original.to_json()
    assert isinstance(json_str, str)
    assert "Create a report" in json_str

    # Test JSON deserialization
    restored = EnhancedIR.from_json(json_str)
    assert restored.source_prompt == original.source_prompt
    assert "e1" in restored.semantic.entities
    assert restored.metadata["language"] == "python"


def test_enhanced_ir_full_round_trip():
    """Test EnhancedIR complete round-trip with all features."""
    # Create complex EnhancedIR with all features populated
    span = Span(start=10, length=6, token_start=2, token_length=1)
    entity = Entity(
        id="e1",
        name="report",
        entity_type=EntityType.DATA_STRUCTURE,
        semantic_type=SemanticType("Report", confidence=0.9),
        span=span,
        resolved=True,
    )

    rel = Relationship(id="r1", type="creates", source="e2", target="e1", confidence=0.95)
    intent = Intent(signature="Create<Report>", operation="CREATE", target="report", confidence=0.9)

    hole_location = Span(start=20, length=5, token_start=4, token_length=1)
    hole = TypedHole(
        id="hole_1",
        kind="type_specification",
        location=hole_location,
        context="report format",
        suggestions=["PDF", "JSON"],
        resolved=True,
        resolution="PDF",
    )

    semantic = SemanticMetadata(
        entities={"e1": entity},
        relationships=[rel],
        intent_hierarchy=intent,
        typed_holes=[hole],
        context_used=["src/models/report.py"],
    )

    highlight = Highlight(span=span, color="entity-data", type="entity", tooltip="Report entity")
    annotations = AnnotationLayer(prompt_highlights=[highlight])

    step = RefinementStep(
        step_number=1,
        hole_or_ambiguity_id="hole_1",
        user_choice="PDF",
        timestamp="2025-10-18T10:30:00Z",
        ir_version_before=0,
        ir_version_after=1,
    )
    refinement = RefinementState(history=[step], current_version=1, is_complete=True)

    original = EnhancedIR(
        semantic=semantic,
        annotations=annotations,
        refinement=refinement,
        source_prompt="Create a report",
        created_at="2025-10-18T10:00:00Z",
        updated_at="2025-10-18T10:30:00Z",
        metadata={"language": "python", "confidence": 0.9},
    )

    # Full round-trip via JSON
    json_str = original.to_json()
    restored = EnhancedIR.from_json(json_str)

    # Verify all data preserved
    assert restored.source_prompt == original.source_prompt
    assert "e1" in restored.semantic.entities
    assert restored.semantic.entities["e1"].name == "report"
    assert restored.semantic.entities["e1"].semantic_type.confidence == 0.9
    assert len(restored.semantic.relationships) == 1
    assert len(restored.semantic.typed_holes) == 1
    assert restored.semantic.typed_holes[0].resolution == "PDF"
    assert len(restored.annotations.prompt_highlights) == 1
    assert len(restored.refinement.history) == 1
    assert restored.refinement.is_complete is True
    assert restored.metadata["language"] == "python"
