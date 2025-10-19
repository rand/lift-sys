"""Semantic IR Data Models for Enhanced Intermediate Representation.

This module implements the complete semantic layer for the lift-sys IR system,
enabling bidirectional translation (NL ↔ IR ↔ Code) with rich semantic metadata,
interactive refinement, and visual annotations.

Architecture:
- Semantic Metadata Layer: Entity resolution, relationships, typed holes
- Annotation Layer: Visual highlights, tooltips, bidirectional links
- Refinement State: Track resolution history, holes, ambiguities

See: docs/SEMANTIC_IR_SPECIFICATION.md for complete specification.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# ============================================================================
# Semantic Metadata Layer
# ============================================================================


class EntityType(Enum):
    """Semantic entity types for classification.

    Categories:
    - CONCEPT: Abstract concept or idea
    - DATA_STRUCTURE: Concrete data type (class, struct, record)
    - FUNCTION: Callable operation
    - ATTRIBUTE: Property or characteristic
    - CONSTRAINT: Restriction or requirement
    - ACTOR: Agent performing action (user, system, service)
    """

    CONCEPT = "concept"
    DATA_STRUCTURE = "data"
    FUNCTION = "function"
    ATTRIBUTE = "attribute"
    CONSTRAINT = "constraint"
    ACTOR = "actor"

    def to_dict(self) -> str:
        """Serialize to string value."""
        return self.value

    @classmethod
    def from_dict(cls, value: str) -> "EntityType":
        """Deserialize from string value."""
        return cls(value)


@dataclass
class SemanticType:
    """Semantic type with confidence score.

    Represents inferred or specified semantic types (e.g., "Document", "User",
    "DateTime") with confidence tracking and provenance.

    Attributes:
        type_name: Semantic type name (e.g., "Document", "User")
        confidence: Confidence score 0.0-1.0 (1.0 = certain)
        source: Where this type was inferred from (e.g., "coreference", "context")
    """

    type_name: str
    confidence: float = 1.0
    source: str | None = None

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {"type_name": self.type_name, "confidence": self.confidence, "source": self.source}

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticType":
        """Deserialize from dictionary."""
        return cls(
            type_name=data["type_name"],
            confidence=data.get("confidence", 1.0),
            source=data.get("source"),
        )


@dataclass
class Span:
    """A span in the prompt or code text.

    Tracks both character-level and token-level positions for accurate
    highlighting and navigation.

    Attributes:
        start: Character offset from beginning of text
        length: Length in characters
        token_start: Token index (0-based)
        token_length: Length in tokens
    """

    start: int
    length: int
    token_start: int
    token_length: int

    def __post_init__(self):
        """Validate span values."""
        if self.start < 0:
            raise ValueError(f"Span start must be >= 0, got {self.start}")
        if self.length < 0:
            raise ValueError(f"Span length must be >= 0, got {self.length}")
        if self.token_start < 0:
            raise ValueError(f"Token start must be >= 0, got {self.token_start}")
        if self.token_length < 0:
            raise ValueError(f"Token length must be >= 0, got {self.token_length}")

    @property
    def end(self) -> int:
        """End character position (exclusive)."""
        return self.start + self.length

    @property
    def token_end(self) -> int:
        """End token position (exclusive)."""
        return self.token_start + self.token_length

    def overlaps(self, other: "Span") -> bool:
        """Check if this span overlaps with another span."""
        return not (self.end <= other.start or other.end <= self.start)

    def contains(self, pos: int) -> bool:
        """Check if a character position is within this span."""
        return self.start <= pos < self.end

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "start": self.start,
            "length": self.length,
            "token_start": self.token_start,
            "token_length": self.token_length,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Span":
        """Deserialize from dictionary."""
        return cls(
            start=data["start"],
            length=data["length"],
            token_start=data["token_start"],
            token_length=data["token_length"],
        )


@dataclass
class Entity:
    """An entity extracted from the prompt or code.

    Entities represent nouns, noun phrases, and other significant elements
    with semantic type information, resolution state, and relationships.

    Attributes:
        id: Unique identifier (e.g., "e1", "e2")
        name: Entity name as it appears in text (e.g., "report", "user")
        entity_type: Category (CONCEPT, DATA_STRUCTURE, etc.)
        semantic_type: Inferred semantic type with confidence
        syntactic_type: Part-of-speech tag (e.g., "noun", "noun_phrase")
        span: Location in source text
        resolved: Whether entity is fully specified
        linked_to: Link to code entity (e.g., "src/models.py:User")
        attributes: Applied attributes (e.g., "shareable" applied to "report")
        references: Other mentions/coreferences (list of entity IDs)
    """

    id: str
    name: str
    entity_type: EntityType
    semantic_type: SemanticType | None = None
    syntactic_type: str = "noun"
    span: Span | None = None
    resolved: bool = False
    linked_to: str | None = None
    attributes: list["Entity"] = field(default_factory=list)
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.to_dict(),
            "semantic_type": self.semantic_type.to_dict() if self.semantic_type else None,
            "syntactic_type": self.syntactic_type,
            "span": self.span.to_dict() if self.span else None,
            "resolved": self.resolved,
            "linked_to": self.linked_to,
            "attributes": [attr.to_dict() for attr in self.attributes],
            "references": self.references,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType.from_dict(data["entity_type"]),
            semantic_type=SemanticType.from_dict(data["semantic_type"])
            if data.get("semantic_type")
            else None,
            syntactic_type=data.get("syntactic_type", "noun"),
            span=Span.from_dict(data["span"]) if data.get("span") else None,
            resolved=data.get("resolved", False),
            linked_to=data.get("linked_to"),
            attributes=[cls.from_dict(attr) for attr in data.get("attributes", [])],
            references=data.get("references", []),
        )


@dataclass
class Relationship:
    """A relationship between entities.

    Represents semantic relationships like "depends_on", "modifies", "uses",
    "creates", etc. with confidence tracking and provenance.

    Attributes:
        id: Unique identifier (e.g., "r1", "r2")
        type: Relationship type (e.g., "depends_on", "modifies", "creates")
        source: Source entity ID
        target: Target entity ID
        confidence: Confidence score 0.0-1.0
        derived_from: Which analysis step produced this relationship
    """

    id: str
    type: str
    source: str
    target: str
    confidence: float = 1.0
    derived_from: str | None = None

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "confidence": self.confidence,
            "derived_from": self.derived_from,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            source=data["source"],
            target=data["target"],
            confidence=data.get("confidence", 1.0),
            derived_from=data.get("derived_from"),
        )


@dataclass
class TypedHole:
    """An unresolved element in the IR (typed hole).

    Represents unknowns that need user clarification, following the
    typed holes approach for explicit ambiguity handling.

    Attributes:
        id: Unique identifier (e.g., "hole_report_format")
        kind: Hole type (e.g., "type_specification", "missing_parameter")
        location: Span in source text
        context: Surrounding text for context
        suggestions: Possible resolutions
        required: Whether this must be resolved before code generation
        resolved: Whether user has resolved this hole
        resolution: User's chosen resolution
    """

    id: str
    kind: str
    location: Span
    context: str
    suggestions: list[str] = field(default_factory=list)
    required: bool = True
    resolved: bool = False
    resolution: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "kind": self.kind,
            "location": self.location.to_dict(),
            "context": self.context,
            "suggestions": self.suggestions,
            "required": self.required,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TypedHole":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            location=Span.from_dict(data["location"]),
            context=data["context"],
            suggestions=data.get("suggestions", []),
            required=data.get("required", True),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
        )


@dataclass
class Ambiguity:
    """An ambiguous or unclear element.

    Represents vague terms, contradictions, or unclear references that
    need disambiguation.

    Attributes:
        id: Unique identifier (e.g., "amb_1")
        type: Ambiguity type (e.g., "vague_term", "contradiction")
        location: Span in source text
        text: The ambiguous text
        issue: Description of the issue
        severity: "low", "medium", or "high"
        suggestions: Disambiguation options
        resolved: Whether user has resolved this
        resolution: User's chosen resolution
    """

    id: str
    type: str
    location: Span
    text: str
    issue: str
    severity: str
    suggestions: list[str] = field(default_factory=list)
    resolved: bool = False
    resolution: str | None = None

    def __post_init__(self):
        """Validate severity."""
        if self.severity not in ["low", "medium", "high"]:
            raise ValueError(f"Severity must be 'low', 'medium', or 'high', got {self.severity}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "location": self.location.to_dict(),
            "text": self.text,
            "issue": self.issue,
            "severity": self.severity,
            "suggestions": self.suggestions,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Ambiguity":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            location=Span.from_dict(data["location"]),
            text=data["text"],
            issue=data["issue"],
            severity=data["severity"],
            suggestions=data.get("suggestions", []),
            resolved=data.get("resolved", False),
            resolution=data.get("resolution"),
        )


@dataclass
class ImplicitTerm:
    """An implicit or missing term/logic.

    Represents inferred preconditions, missing parameters, or assumed
    context that may need explicit handling.

    Attributes:
        id: Unique identifier (e.g., "imp_1")
        type: Type (e.g., "precondition", "missing_parameter")
        inferred_from: What clause/entity led to this inference
        term: The implicit term description
        confidence: Confidence in this inference (0.0-1.0)
        location: Where to insert (if applicable)
        accepted: Whether user accepted this inference
    """

    id: str
    type: str
    inferred_from: str
    term: str
    confidence: float = 0.5
    location: Span | None = None
    accepted: bool = False

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "inferred_from": self.inferred_from,
            "term": self.term,
            "confidence": self.confidence,
            "location": self.location.to_dict() if self.location else None,
            "accepted": self.accepted,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImplicitTerm":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=data["type"],
            inferred_from=data["inferred_from"],
            term=data["term"],
            confidence=data.get("confidence", 0.5),
            location=Span.from_dict(data["location"]) if data.get("location") else None,
            accepted=data.get("accepted", False),
        )


@dataclass
class Intent:
    """Intent signature for the prompt or sub-element.

    Represents the hierarchical intent structure with canonical signatures,
    operations, and constraints.

    Attributes:
        signature: Canonical signature (e.g., "Create<Report>")
        operation: CRUD operation or transformation type
        target: What entity is being acted upon
        constraints: Conditions or restrictions
        sub_intents: Nested intents (hierarchical structure)
        confidence: Confidence score 0.0-1.0
    """

    signature: str
    operation: str
    target: str
    constraints: list[str] = field(default_factory=list)
    sub_intents: list["Intent"] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0.0, 1.0], got {self.confidence}")

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "signature": self.signature,
            "operation": self.operation,
            "target": self.target,
            "constraints": self.constraints,
            "sub_intents": [intent.to_dict() for intent in self.sub_intents],
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Intent":
        """Deserialize from dictionary."""
        return cls(
            signature=data["signature"],
            operation=data["operation"],
            target=data["target"],
            constraints=data.get("constraints", []),
            sub_intents=[cls.from_dict(intent) for intent in data.get("sub_intents", [])],
            confidence=data.get("confidence", 1.0),
        )


@dataclass
class SemanticMetadata:
    """Semantic analysis results container.

    Aggregates all semantic analysis outputs: entities, relationships,
    intent hierarchy, holes, ambiguities, and implicit terms.

    Attributes:
        entities: All entities by ID
        relationships: Entity relationships
        intent_hierarchy: Intent tree
        typed_holes: Unresolved elements
        ambiguities: Ambiguous elements
        implicit_terms: Inferred missing terms
        context_used: Context sources used in analysis
    """

    entities: dict[str, Entity]
    relationships: list[Relationship]
    intent_hierarchy: Intent
    typed_holes: list[TypedHole] = field(default_factory=list)
    ambiguities: list[Ambiguity] = field(default_factory=list)
    implicit_terms: list[ImplicitTerm] = field(default_factory=list)
    context_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "entities": {id: entity.to_dict() for id, entity in self.entities.items()},
            "relationships": [rel.to_dict() for rel in self.relationships],
            "intent_hierarchy": self.intent_hierarchy.to_dict(),
            "typed_holes": [hole.to_dict() for hole in self.typed_holes],
            "ambiguities": [amb.to_dict() for amb in self.ambiguities],
            "implicit_terms": [term.to_dict() for term in self.implicit_terms],
            "context_used": self.context_used,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SemanticMetadata":
        """Deserialize from dictionary."""
        return cls(
            entities={id: Entity.from_dict(entity) for id, entity in data["entities"].items()},
            relationships=[Relationship.from_dict(rel) for rel in data["relationships"]],
            intent_hierarchy=Intent.from_dict(data["intent_hierarchy"]),
            typed_holes=[TypedHole.from_dict(hole) for hole in data.get("typed_holes", [])],
            ambiguities=[Ambiguity.from_dict(amb) for amb in data.get("ambiguities", [])],
            implicit_terms=[
                ImplicitTerm.from_dict(term) for term in data.get("implicit_terms", [])
            ],
            context_used=data.get("context_used", []),
        )


# ============================================================================
# Annotation Layer (for UI rendering)
# ============================================================================


@dataclass
class Highlight:
    """A syntax highlight or annotation for UI rendering.

    Attributes:
        span: Where to highlight
        color: Color or style class (e.g., "entity-data", "hole", "ambiguity")
        type: Highlight type (e.g., "entity", "type", "hole", "ambiguity")
        tooltip: Hover text
        linked_to: Link to IR element ID
    """

    span: Span
    color: str
    type: str
    tooltip: str | None = None
    linked_to: str | None = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "span": self.span.to_dict(),
            "color": self.color,
            "type": self.type,
            "tooltip": self.tooltip,
            "linked_to": self.linked_to,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Highlight":
        """Deserialize from dictionary."""
        return cls(
            span=Span.from_dict(data["span"]),
            color=data["color"],
            type=data["type"],
            tooltip=data.get("tooltip"),
            linked_to=data.get("linked_to"),
        )


@dataclass
class AnnotationLayer:
    """Visual annotations for UI rendering.

    Provides bidirectional links between prompt tokens and IR elements,
    plus highlighting metadata for IDE-style visualization.

    Attributes:
        prompt_highlights: Highlights for prompt text
        ir_highlights: Highlights for IR display
        prompt_to_ir_links: Mapping from prompt tokens to IR elements
        ir_to_prompt_links: Mapping from IR elements to prompt tokens
    """

    prompt_highlights: list[Highlight] = field(default_factory=list)
    ir_highlights: list[Highlight] = field(default_factory=list)
    prompt_to_ir_links: dict[str, str] = field(default_factory=dict)
    ir_to_prompt_links: dict[str, str] = field(default_factory=dict)

    def add_bidirectional_link(self, prompt_token: str, ir_element: str):
        """Add a bidirectional link between prompt and IR.

        Args:
            prompt_token: Token identifier (e.g., "token_3")
            ir_element: IR element path (e.g., "ir.signature.returns")
        """
        self.prompt_to_ir_links[prompt_token] = ir_element
        self.ir_to_prompt_links[ir_element] = prompt_token

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "prompt_highlights": [h.to_dict() for h in self.prompt_highlights],
            "ir_highlights": [h.to_dict() for h in self.ir_highlights],
            "prompt_to_ir_links": self.prompt_to_ir_links,
            "ir_to_prompt_links": self.ir_to_prompt_links,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AnnotationLayer":
        """Deserialize from dictionary."""
        return cls(
            prompt_highlights=[Highlight.from_dict(h) for h in data.get("prompt_highlights", [])],
            ir_highlights=[Highlight.from_dict(h) for h in data.get("ir_highlights", [])],
            prompt_to_ir_links=data.get("prompt_to_ir_links", {}),
            ir_to_prompt_links=data.get("ir_to_prompt_links", {}),
        )


# ============================================================================
# Refinement State
# ============================================================================


@dataclass
class RefinementStep:
    """A single refinement step in the session.

    Tracks user resolutions of holes and ambiguities with versioning.

    Attributes:
        step_number: Sequential step number
        hole_or_ambiguity_id: What was resolved
        user_choice: User's resolution choice
        timestamp: ISO 8601 timestamp
        ir_version_before: IR version before this step
        ir_version_after: IR version after this step
    """

    step_number: int
    hole_or_ambiguity_id: str
    user_choice: str
    timestamp: str
    ir_version_before: int
    ir_version_after: int

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RefinementStep":
        """Deserialize from dictionary."""
        return cls(**data)


@dataclass
class RefinementState:
    """Tracks the refinement process state.

    Maintains refinement history, unresolved items, version tracking,
    and completion status.

    Attributes:
        history: List of refinement steps
        unresolved_holes: IDs of unresolved typed holes
        unresolved_ambiguities: IDs of unresolved ambiguities
        current_version: Current IR version number
        is_complete: Whether IR is ready for code generation
    """

    history: list[RefinementStep] = field(default_factory=list)
    unresolved_holes: list[str] = field(default_factory=list)
    unresolved_ambiguities: list[str] = field(default_factory=list)
    current_version: int = 0
    is_complete: bool = False

    def record_resolution(
        self, hole_or_ambiguity_id: str, user_choice: str, timestamp: str | None = None
    ):
        """Record a resolution step and increment version.

        Args:
            hole_or_ambiguity_id: ID of resolved item
            user_choice: User's chosen resolution
            timestamp: ISO timestamp (auto-generated if None)
        """
        if timestamp is None:
            timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        step = RefinementStep(
            step_number=len(self.history) + 1,
            hole_or_ambiguity_id=hole_or_ambiguity_id,
            user_choice=user_choice,
            timestamp=timestamp,
            ir_version_before=self.current_version,
            ir_version_after=self.current_version + 1,
        )

        self.history.append(step)
        self.current_version += 1

        # Remove from unresolved lists
        if hole_or_ambiguity_id in self.unresolved_holes:
            self.unresolved_holes.remove(hole_or_ambiguity_id)
        if hole_or_ambiguity_id in self.unresolved_ambiguities:
            self.unresolved_ambiguities.remove(hole_or_ambiguity_id)

        # Update completion status
        self.is_complete = len(self.unresolved_holes) == 0 and len(self.unresolved_ambiguities) == 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "history": [step.to_dict() for step in self.history],
            "unresolved_holes": self.unresolved_holes,
            "unresolved_ambiguities": self.unresolved_ambiguities,
            "current_version": self.current_version,
            "is_complete": self.is_complete,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RefinementState":
        """Deserialize from dictionary."""
        return cls(
            history=[RefinementStep.from_dict(step) for step in data.get("history", [])],
            unresolved_holes=data.get("unresolved_holes", []),
            unresolved_ambiguities=data.get("unresolved_ambiguities", []),
            current_version=data.get("current_version", 0),
            is_complete=data.get("is_complete", False),
        )


# ============================================================================
# Enhanced IR (combines all layers)
# ============================================================================


@dataclass
class EnhancedIR:
    """The complete IR with semantic metadata and annotations.

    Combines core IR structure with semantic analysis results,
    visual annotations, and refinement state for the full
    bidirectional translation system.

    Note: This is a simplified version that doesn't include the full
    core IR (IntentClause, SigClause, etc.) to avoid circular dependencies.
    In production, this would wrap the existing IntermediateRepresentation.

    Attributes:
        semantic: Semantic analysis results
        annotations: Visual annotations for UI
        refinement: Refinement state tracking
        source_prompt: Original prompt text
        source_code: Source code (if from reverse mode)
        created_at: ISO timestamp of creation
        updated_at: ISO timestamp of last update
        metadata: Additional metadata (language, origin, etc.)
    """

    semantic: SemanticMetadata
    annotations: AnnotationLayer
    refinement: RefinementState
    source_prompt: str
    source_code: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set timestamps if not provided."""
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = now

    def update_timestamp(self):
        """Update the updated_at timestamp to current time."""
        self.updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> dict:
        """Serialize to dictionary (JSON-compatible).

        Returns:
            Dictionary representation with no data loss
        """
        return {
            "semantic": self.semantic.to_dict(),
            "annotations": self.annotations.to_dict(),
            "refinement": self.refinement.to_dict(),
            "source_prompt": self.source_prompt,
            "source_code": self.source_code,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnhancedIR":
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            EnhancedIR instance with all data restored
        """
        return cls(
            semantic=SemanticMetadata.from_dict(data["semantic"]),
            annotations=AnnotationLayer.from_dict(data["annotations"]),
            refinement=RefinementState.from_dict(data["refinement"]),
            source_prompt=data["source_prompt"],
            source_code=data.get("source_code"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, indent: int | None = 2) -> str:
        """Serialize to JSON string.

        Args:
            indent: JSON indentation (None for compact)

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "EnhancedIR":
        """Deserialize from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            EnhancedIR instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    @property
    def has_unresolved_items(self) -> bool:
        """Check if there are unresolved holes or ambiguities."""
        return not self.refinement.is_complete

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage (0.0-1.0).

        Based on ratio of resolved to total holes and ambiguities.
        """
        total = len(self.semantic.typed_holes) + len(self.semantic.ambiguities)
        if total == 0:
            return 1.0

        unresolved = len(self.refinement.unresolved_holes) + len(
            self.refinement.unresolved_ambiguities
        )
        return 1.0 - (unresolved / total)
