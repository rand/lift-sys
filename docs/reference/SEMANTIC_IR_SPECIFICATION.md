# Semantic IR Specification: Interactive Refinement & Annotation

**Status**: Design Proposal
**Created**: 2025-10-15
**Supersedes**: Current session-based IR refinement
**Related**: `API_SESSION_MANAGEMENT.md`, `IR_TO_CODE_ARCHITECTURE.md`, `FORWARD_REVERSE_INTEGRATION_PLAN.md`

---

## Executive Summary

This specification describes an enhanced IR system that treats prompts and code as **semantically annotated, interactively refinable artifacts**. The system performs deep analysis of natural language prompts and lifted code to build a rich, annotated IR that serves as:

1. **A semantic model** with entity resolution, type inference, and relationship tracking
2. **A visual artifact** with IDE-style highlighting, hover states, and annotations
3. **An interactive refinement target** for iterative clarification with users
4. **A bidirectional bridge** between natural language, IR, and code

**Key Innovation**: The IR becomes a **living document** with metadata that tracks semantic types, unresolved holes, relationships, and provenance—not just a static data structure.

---

## Table of Contents

1. [Goals and Non-Goals](#goals-and-non-goals)
2. [System Architecture](#system-architecture)
3. [Prompt Processing Pipeline](#prompt-processing-pipeline)
4. [Enhanced IR Data Model](#enhanced-ir-data-model)
5. [Visual Affordances](#visual-affordances)
6. [Interactive Refinement Protocol](#interactive-refinement-protocol)
7. [Reverse Mode Integration](#reverse-mode-integration)
8. [Implementation Phases](#implementation-phases)
9. [Technical Requirements](#technical-requirements)
10. [Open Questions](#open-questions)

---

## Goals and Non-Goals

### Goals

✅ **Semantic Understanding**
- Resolve entities, references (definite/indefinite articles, pronouns)
- Identify relationships between clauses and terms
- Detect ambiguities, contradictions, missing information

✅ **Rich Annotation**
- Semantic types and syntactic types for all elements
- Typed holes for unresolved elements
- Intent signatures for prompts and sub-elements
- Relationship graphs between entities

✅ **Visual Intelligence**
- IDE-style syntax highlighting on prompts and IR
- Hover states showing type information, relationships, provenance
- Visual indicators for ambiguities, holes, resolved elements

✅ **Interactive Refinement**
- Iterative disambiguation with user
- Context-aware suggestions
- Real-time IR updates as prompt evolves

✅ **Bidirectional Consistency**
- Same IR structure for forward mode (prompt→IR→code)
- Same IR structure for reverse mode (code→IR)
- Visual affordances work in both directions

✅ **Human-Readable & Formal**
- IR is readable as a spec
- IR is structured enough for code generation
- IR is editable without breaking formalism

### Non-Goals

❌ Full natural language understanding (AGI-level)
❌ Multi-language prompts (English only initially)
❌ Real-time collaborative editing (single-user focus)
❌ Version control integration (separate concern)
❌ Automated code repair/debugging

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface Layer                         │
│  - Syntax highlighting    - Hover annotations   - Inline refinement │
└────────────────────┬───────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────────┐
│                    Semantic Analysis Pipeline                        │
│  1. Entity Resolution   4. Ambiguity Detection   7. Intent Inference │
│  2. Clause Analysis     5. Implicit Term Finding 8. Type Inference   │
│  3. Relationship Graph  6. Semantic Type Holes   9. IR Construction  │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────────┐
│                      Enhanced IR Data Model                          │
│  - Core IR (intent, signature, effects, assertions)                 │
│  - Semantic Metadata (types, relationships, provenance)             │
│  - Annotation Layer (highlights, tooltips, links)                   │
│  - Refinement State (holes, ambiguities, resolution history)        │
└────────────────────┬────────────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────────────┐
│                    Refinement Engine                                 │
│  - Hole resolution   - Suggestion generation   - Consistency check  │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **NLP Preprocessor** | Tokenize, parse, tag parts of speech | Raw prompt | Structured parse tree |
| **Entity Resolver** | Resolve references, pronouns, articles | Parse tree | Entity graph |
| **Clause Analyzer** | Identify clauses, logic, relationships | Parse tree | Clause dependency graph |
| **Ambiguity Detector** | Find contradictions, missing info | Entity + clause graphs | Ambiguity list |
| **Type Inferencer** | Infer semantic types for entities | Entity graph + context | Type annotations |
| **Intent Classifier** | Identify intent signatures | Analyzed prompt | Intent hierarchy |
| **IR Builder** | Construct IR from analysis | All analyses | Enhanced IR |
| **Annotation Generator** | Create visual annotations | Enhanced IR | UI metadata |
| **Refinement Suggester** | Generate refinement suggestions | IR + ambiguities | Suggestion list |

---

## Prompt Processing Pipeline

### Step-by-Step Flow

#### Step 1: Context Review

**Input**: User prompt + available context (prior session, codebase, docs)

**Process**:
1. Load session history (if any)
2. Index available code context (if repository connected)
3. Extract relevant documentation snippets
4. Build context vector for semantic analysis

**Output**: Context bundle with relevance scores

**Example**:
```python
Context {
    session_history: [
        Prompt("Create a user authentication system"),
        IR(user_auth_system_v1)
    ],
    codebase: {
        "src/models/user.py": RelevanceScore(0.9),
        "src/auth/jwt.py": RelevanceScore(0.7),
    },
    docs: ["Authentication guide", "Security best practices"]
}
```

---

#### Step 2: Entity Resolution

**Input**: Prompt text + context

**Process**:
1. **Tokenize and POS tag** prompt
2. **Extract entities**: Nouns, noun phrases
3. **Resolve references**:
   - Definite articles ("the report") → anaphora resolution
   - Indefinite articles ("a report") → new entity introduction
   - Pronouns ("it", "them") → coreference resolution
4. **Link entities across prompt**
5. **Merge with context entities** (e.g., existing types in codebase)

**Output**: Entity graph with resolved references

**Example**:
```
Prompt: "Create a report and make it shareable"

Entity Graph:
  [report] (entity_id: e1)
    ├─ mentioned_at: [token 3]
    ├─ referenced_by: ["it" at token 6] (coreference)
    ├─ semantic_type: Document (inferred)
    └─ attributes: [shareable] (applied at token 6)

  [shareable] (entity_id: a1)
    ├─ type: Attribute
    ├─ applies_to: e1 (report)
    └─ semantic_type: Permission (inferred)
```

---

#### Step 3: Clause Analysis & Logic

**Input**: Parse tree + entity graph

**Process**:
1. **Identify clauses**: Main, subordinate, relative
2. **Extract verbs and actions**: "create", "make", "validate"
3. **Build dependency graph**: Which clauses depend on others
4. **Identify conditions**: "if X then Y", "when X", "unless Y"
5. **Extract temporal relationships**: "before", "after", "during"

**Output**: Clause dependency graph with logical relationships

**Example**:
```
Prompt: "Create a report and make it shareable if the user is authenticated"

Clause Graph:
  [C1: "Create a report"] (main clause)
    ├─ action: create
    ├─ object: e1 (report)
    └─ dependencies: []

  [C2: "make it shareable"] (coordinate clause)
    ├─ action: make
    ├─ object: e1 (report)
    ├─ attribute: shareable
    └─ dependencies: [C1]  # "and" coordinator

  [C3: "if the user is authenticated"] (conditional clause)
    ├─ type: condition
    ├─ applies_to: C2
    ├─ condition: user.authenticated == true
    └─ dependencies: [C2]
```

---

#### Step 4: Ambiguity Detection

**Input**: Entity graph + clause graph

**Process**:
1. **Detect contradictions**: "create file X" then "X must exist"
2. **Find ambiguous references**: Pronoun with multiple antecedents
3. **Identify vague terms**: "process the data" (what process?)
4. **Check missing constraints**: No type specified for parameter
5. **Flag inconsistent uses**: "report" used as noun and verb

**Output**: Ambiguity list with severity and suggestions

**Example**:
```python
Ambiguities = [
    Ambiguity(
        id="amb_1",
        type="vague_term",
        location=Span(token=8, length=2),  # "shareable"
        text="shareable",
        issue="Unclear what 'shareable' means",
        severity="medium",
        suggestions=[
            "Make it publicly accessible (URL)",
            "Add it to a shared folder",
            "Send it via email",
            "Export as PDF for sharing"
        ]
    ),
    Ambiguity(
        id="amb_2",
        type="missing_constraint",
        location=Span(token=3, length=1),  # "report"
        text="report",
        issue="No type specified for report (format, structure)",
        severity="high",
        suggestions=[
            "PDF document",
            "JSON data structure",
            "HTML web page",
            "Excel spreadsheet"
        ]
    )
]
```

---

#### Step 5: Implicit Term Finding

**Input**: Clause graph + domain knowledge

**Process**:
1. **Identify missing subjects**: "Process data" → who processes?
2. **Find implicit preconditions**: "Delete file" → file must exist
3. **Infer missing steps**: "Upload and process" → where's the upload endpoint?
4. **Detect assumed context**: "Send notification" → to whom?

**Output**: List of implicit terms/logic with confidence scores

**Example**:
```python
ImplicitTerms = [
    ImplicitTerm(
        id="imp_1",
        type="precondition",
        inferred_from="make it shareable",
        term="report must be created first",
        confidence=0.95,
        location=Span(token=6, length=2)
    ),
    ImplicitTerm(
        id="imp_2",
        type="missing_parameter",
        inferred_from="user is authenticated",
        term="user object/session",
        confidence=0.85,
        location=Span(token=10, length=1)
    )
]
```

---

#### Step 6: Semantic Type Holes

**Input**: Entity graph + type inference results

**Process**:
1. **Assign semantic types** to resolved entities (e.g., `report: Document`)
2. **Create typed holes** for unresolved elements:
   - Unknown types: `param_x: ???`
   - Ambiguous types: `file: File | Stream | Buffer`
   - Missing entities: `user: HOLE<User>`

**Output**: Annotated entity graph with typed holes

**Example**:
```python
EntityGraph = {
    "report": Entity(
        id="e1",
        name="report",
        semantic_type=SemanticType("Document", confidence=0.7),
        syntactic_type=SyntacticType("noun"),
        resolved=False,  # Needs refinement
        holes=[
            TypedHole(
                id="hole_report_format",
                kind="type_specification",
                suggestions=["PDF", "JSON", "HTML"]
            )
        ]
    ),
    "user": Entity(
        id="e2",
        name="user",
        semantic_type=SemanticType("User", confidence=0.9),
        syntactic_type=SyntacticType("noun"),
        resolved=True,  # Found in context (existing codebase)
        linked_to="src/models/user.py:User"
    )
}
```

---

#### Step 7: Intent Signature Inference

**Input**: Clause graph + semantic types

**Process**:
1. **Classify overall intent**: CRUD operation, transformation, validation, etc.
2. **Extract sub-intents**: Each clause may have its own intent
3. **Build intent hierarchy**: Main intent → sub-intents
4. **Map to canonical forms**: "create report" → CreateOperation(Document)

**Output**: Intent hierarchy with signatures

**Example**:
```python
IntentHierarchy = Intent(
    signature="CreateAndShare<Document>",
    main_intent="create_and_configure",
    sub_intents=[
        Intent(
            signature="Create<Report>",
            operation="CREATE",
            target="report",
            constraints=["user.authenticated == true"]
        ),
        Intent(
            signature="Configure<Report, Attribute=shareable>",
            operation="UPDATE",
            target="report",
            attribute="shareable",
            constraints=["user.authenticated == true"]
        )
    ],
    confidence=0.85
)
```

---

#### Step 8: Type Inference (Inputs/Outputs)

**Input**: Intent hierarchy + entity graph

**Process**:
1. **Infer input types**: What data is needed?
2. **Infer output types**: What data is produced?
3. **Infer intermediate types**: Data transformations
4. **Apply type constraints**: From domain knowledge

**Output**: Type annotations for all data flows

**Example**:
```python
TypeInference = {
    "inputs": [
        TypedEntity(
            name="user",
            type="User",
            source="context.codebase",
            required=True
        ),
        TypedEntity(
            name="report_data",
            type="ReportData | HOLE",
            source="unknown",
            required=True
        )
    ],
    "outputs": [
        TypedEntity(
            name="report",
            type="ShareableReport",
            derived_from=["report_data", "user"],
            constraints=["report.shareable == true"]
        )
    ],
    "intermediate": [
        TypedEntity(
            name="report_id",
            type="str | UUID",
            derived_from=["report"],
            used_in=["shareable_link"]
        )
    ]
}
```

---

#### Step 9: IR Construction

**Input**: All analyses from steps 1-8

**Process**:
1. **Build core IR structure** (intent, signature, effects, assertions)
2. **Attach semantic metadata** (entities, types, relationships)
3. **Embed annotation layer** (highlights, tooltips, provenance)
4. **Mark refinement state** (holes, ambiguities, confidence scores)

**Output**: Enhanced IR with full metadata

**See**: [Enhanced IR Data Model](#enhanced-ir-data-model) section below

---

#### Step 10: Visual Annotation Generation

**Input**: Enhanced IR

**Process**:
1. **Generate syntax highlighting** for prompt and IR
2. **Create hover states** with type info, relationships
3. **Add inline annotations** for ambiguities and holes
4. **Link prompt tokens** to IR elements (bidirectional)

**Output**: UI metadata for rendering

**See**: [Visual Affordances](#visual-affordances) section below

---

#### Steps 11-14: Interactive Refinement

**Process**: Iterative loop with user

1. **Present annotated prompt and IR** with highlighted issues
2. **User selects ambiguity/hole** to refine
3. **System generates suggestions** from context and analysis
4. **User chooses or provides custom resolution**
5. **IR updates in real-time**, propagating changes
6. **Repeat** until IR is complete or user is satisfied

**See**: [Interactive Refinement Protocol](#interactive-refinement-protocol) section below

---

## Enhanced IR Data Model

### Core IR (Existing)

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class IntentClause:
    summary: str
    rationale: Optional[str] = None

@dataclass
class Parameter:
    name: str
    type_hint: str
    description: Optional[str] = None

@dataclass
class SigClause:
    name: str
    parameters: List[Parameter]
    returns: Optional[str] = None

@dataclass
class EffectClause:
    description: str

@dataclass
class AssertClause:
    predicate: str
    rationale: Optional[str] = None

@dataclass
class IntermediateRepresentation:
    intent: IntentClause
    signature: SigClause
    effects: List[EffectClause]
    assertions: List[AssertClause]
    metadata: dict
```

### Enhanced IR (Proposed)

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum

# ============================================================================
# Semantic Metadata Layer
# ============================================================================

class EntityType(Enum):
    """Semantic entity types"""
    CONCEPT = "concept"           # Abstract concept
    DATA_STRUCTURE = "data"       # Concrete data type
    FUNCTION = "function"         # Callable
    ATTRIBUTE = "attribute"       # Property or characteristic
    CONSTRAINT = "constraint"     # Restriction or requirement
    ACTOR = "actor"              # Agent performing action

class SemanticType:
    """Semantic type with confidence score"""
    def __init__(self, type_name: str, confidence: float = 1.0):
        self.type_name = type_name        # e.g., "Document", "User", "DateTime"
        self.confidence = confidence      # 0.0 to 1.0
        self.source = None               # Where this type was inferred from

@dataclass
class Entity:
    """An entity extracted from the prompt"""
    id: str                              # Unique identifier (e.g., "e1")
    name: str                            # Entity name (e.g., "report")
    entity_type: EntityType              # Category
    semantic_type: Optional[SemanticType] = None  # Inferred type
    syntactic_type: str = "noun"         # POS tag
    span: Optional['Span'] = None        # Location in prompt
    resolved: bool = False               # Whether fully specified
    linked_to: Optional[str] = None      # Link to code entity (e.g., "src/models.py:User")
    attributes: List['Entity'] = field(default_factory=list)  # Applied attributes
    references: List[str] = field(default_factory=list)       # Other mentions (coreferences)

@dataclass
class Span:
    """A span in the prompt text"""
    start: int                           # Character offset
    length: int                          # Length in characters
    token_start: int                     # Token index
    token_length: int                    # Length in tokens

@dataclass
class Relationship:
    """A relationship between entities"""
    id: str                              # Unique identifier
    type: str                            # "depends_on", "modifies", "uses", etc.
    source: str                          # Source entity ID
    target: str                          # Target entity ID
    confidence: float = 1.0              # Confidence score
    derived_from: Optional[str] = None   # Which analysis step produced this

@dataclass
class TypedHole:
    """An unresolved element in the IR"""
    id: str                              # Unique identifier (e.g., "hole_report_format")
    kind: str                            # "type_specification", "missing_parameter", etc.
    location: Span                       # Where in the prompt
    context: str                         # Surrounding text for context
    suggestions: List[str] = field(default_factory=list)  # Possible resolutions
    required: bool = True                # Whether this must be resolved
    resolved: bool = False               # Whether user has resolved it
    resolution: Optional[str] = None     # User's resolution

@dataclass
class Ambiguity:
    """An ambiguous or unclear element"""
    id: str                              # Unique identifier
    type: str                            # "vague_term", "contradiction", etc.
    location: Span                       # Where in the prompt
    text: str                            # The ambiguous text
    issue: str                           # Description of the issue
    severity: str                        # "low", "medium", "high"
    suggestions: List[str] = field(default_factory=list)  # Disambiguation options
    resolved: bool = False
    resolution: Optional[str] = None

@dataclass
class ImplicitTerm:
    """An implicit or missing term/logic"""
    id: str                              # Unique identifier
    type: str                            # "precondition", "missing_parameter", etc.
    inferred_from: str                   # What clause/entity led to this inference
    term: str                            # The implicit term
    confidence: float = 0.5              # Confidence in this inference
    location: Optional[Span] = None      # Where to insert (if applicable)
    accepted: bool = False               # Whether user accepted this inference

@dataclass
class Intent:
    """Intent signature for the prompt or sub-element"""
    signature: str                       # Canonical signature (e.g., "Create<Report>")
    operation: str                       # CRUD operation or transformation
    target: str                          # What entity is being acted upon
    constraints: List[str] = field(default_factory=list)  # Conditions
    sub_intents: List['Intent'] = field(default_factory=list)  # Nested intents
    confidence: float = 1.0              # Confidence score

@dataclass
class SemanticMetadata:
    """Semantic analysis results"""
    entities: Dict[str, Entity]          # All entities by ID
    relationships: List[Relationship]     # Entity relationships
    intent_hierarchy: Intent             # Intent tree
    typed_holes: List[TypedHole]         # Unresolved elements
    ambiguities: List[Ambiguity]         # Ambiguous elements
    implicit_terms: List[ImplicitTerm]   # Inferred missing terms
    context_used: List[str] = field(default_factory=list)  # Context sources used

# ============================================================================
# Annotation Layer (for UI rendering)
# ============================================================================

@dataclass
class Highlight:
    """A syntax highlight or annotation"""
    span: Span                           # Where to highlight
    color: str                           # Color or style class
    type: str                            # "entity", "type", "hole", "ambiguity", etc.
    tooltip: Optional[str] = None        # Hover text
    linked_to: Optional[str] = None      # Link to IR element

@dataclass
class AnnotationLayer:
    """Visual annotations for UI"""
    prompt_highlights: List[Highlight] = field(default_factory=list)
    ir_highlights: List[Highlight] = field(default_factory=list)
    prompt_to_ir_links: Dict[str, str] = field(default_factory=dict)  # Token → IR element
    ir_to_prompt_links: Dict[str, str] = field(default_factory=dict)  # IR element → Token

# ============================================================================
# Refinement State
# ============================================================================

@dataclass
class RefinementStep:
    """A single refinement step in the session"""
    step_number: int
    hole_or_ambiguity_id: str            # What was resolved
    user_choice: str                     # User's resolution
    timestamp: str                       # ISO timestamp
    ir_version_before: int               # IR version before this step
    ir_version_after: int                # IR version after this step

@dataclass
class RefinementState:
    """Tracks the refinement process"""
    history: List[RefinementStep] = field(default_factory=list)
    unresolved_holes: List[str] = field(default_factory=list)        # Hole IDs
    unresolved_ambiguities: List[str] = field(default_factory=list)  # Ambiguity IDs
    current_version: int = 0             # IR version number
    is_complete: bool = False            # Whether IR is ready for code gen

# ============================================================================
# Enhanced IR (combines all layers)
# ============================================================================

@dataclass
class EnhancedIR:
    """The complete IR with semantic metadata and annotations"""

    # Core IR (existing structure)
    intent: IntentClause
    signature: SigClause
    effects: List[EffectClause]
    assertions: List[AssertClause]
    metadata: dict

    # New: Semantic layer
    semantic: SemanticMetadata

    # New: Visual layer
    annotations: AnnotationLayer

    # New: Refinement state
    refinement: RefinementState

    # Provenance
    source_prompt: str                   # Original prompt
    source_code: Optional[str] = None    # If from reverse mode
    created_at: str                      # ISO timestamp
    updated_at: str                      # ISO timestamp

    def to_dict(self) -> dict:
        """Serialize to JSON"""
        # Implementation...

    @classmethod
    def from_dict(cls, data: dict) -> 'EnhancedIR':
        """Deserialize from JSON"""
        # Implementation...
```

### Example: Full Enhanced IR

```python
example_ir = EnhancedIR(
    # Core IR
    intent=IntentClause(
        summary="Create a shareable report for authenticated users",
        rationale="Users need to generate and share reports with specific permissions"
    ),
    signature=SigClause(
        name="create_shareable_report",
        parameters=[
            Parameter(name="user", type_hint="User", description="Authenticated user"),
            Parameter(name="report_data", type_hint="ReportData", description="Data for the report")
        ],
        returns="ShareableReport"
    ),
    effects=[
        EffectClause(description="Creates a new report in the database"),
        EffectClause(description="Generates a shareable link")
    ],
    assertions=[
        AssertClause(
            predicate="user.is_authenticated == True",
            rationale="Only authenticated users can create reports"
        )
    ],
    metadata={
        "language": "python",
        "origin": "forward",
        "confidence": 0.85
    },

    # Semantic layer
    semantic=SemanticMetadata(
        entities={
            "e1": Entity(
                id="e1",
                name="report",
                entity_type=EntityType.DATA_STRUCTURE,
                semantic_type=SemanticType("Report", confidence=0.9),
                span=Span(start=12, length=6, token_start=3, token_length=1),
                resolved=True,
                attributes=[Entity(id="a1", name="shareable", entity_type=EntityType.ATTRIBUTE)]
            ),
            "e2": Entity(
                id="e2",
                name="user",
                entity_type=EntityType.ACTOR,
                semantic_type=SemanticType("User", confidence=1.0),
                span=Span(start=48, length=4, token_start=10, token_length=1),
                resolved=True,
                linked_to="src/models/user.py:User"
            )
        },
        relationships=[
            Relationship(
                id="r1",
                type="creates",
                source="e2",  # user
                target="e1",  # report
                confidence=0.95
            ),
            Relationship(
                id="r2",
                type="has_attribute",
                source="e1",  # report
                target="a1",  # shareable
                confidence=1.0
            )
        ],
        intent_hierarchy=Intent(
            signature="CreateAndConfigure<Report>",
            operation="CREATE_UPDATE",
            target="report",
            constraints=["user.is_authenticated == True"],
            sub_intents=[
                Intent(signature="Create<Report>", operation="CREATE", target="report"),
                Intent(signature="MakeShareable<Report>", operation="UPDATE", target="report")
            ]
        ),
        typed_holes=[],  # All resolved in this example
        ambiguities=[],  # All resolved
        implicit_terms=[
            ImplicitTerm(
                id="imp_1",
                type="precondition",
                inferred_from="make it shareable",
                term="report must be created before being made shareable",
                confidence=0.95,
                accepted=True
            )
        ],
        context_used=["src/models/user.py", "src/models/report.py"]
    ),

    # Annotation layer
    annotations=AnnotationLayer(
        prompt_highlights=[
            Highlight(
                span=Span(start=12, length=6, token_start=3, token_length=1),
                color="entity-data",
                type="entity",
                tooltip="Report (Document) - resolved",
                linked_to="ir.signature.returns"
            ),
            Highlight(
                span=Span(start=48, length=4, token_start=10, token_length=1),
                color="entity-actor",
                type="entity",
                tooltip="User - linked to src/models/user.py:User",
                linked_to="ir.signature.parameters[0]"
            )
        ],
        prompt_to_ir_links={
            "token_3": "ir.signature.returns",
            "token_10": "ir.signature.parameters[0]"
        }
    ),

    # Refinement state
    refinement=RefinementState(
        history=[
            RefinementStep(
                step_number=1,
                hole_or_ambiguity_id="hole_report_format",
                user_choice="ShareableReport (custom type with link)",
                timestamp="2025-10-15T10:30:00Z",
                ir_version_before=0,
                ir_version_after=1
            )
        ],
        unresolved_holes=[],
        unresolved_ambiguities=[],
        current_version=1,
        is_complete=True
    ),

    # Provenance
    source_prompt="Create a report and make it shareable if the user is authenticated",
    created_at="2025-10-15T10:25:00Z",
    updated_at="2025-10-15T10:30:00Z"
)
```

---

## Visual Affordances

### UI Components

The system provides **IDE-style visual intelligence** for both the prompt and the IR.

#### 1. Syntax Highlighting

**Prompt highlighting** (applied to user's natural language):

```
Create a [report] and make [it] [shareable] if the [user] is [authenticated]
         ^^^^^^^^        ^^^^  ^^^^^^^^^^       ^^^^^^    ^^^^^^^^^^^^^^^
         entity          ref   attribute        entity    constraint
         (data)          (e1)  (applied to e1)  (actor)   (condition)
```

**IR highlighting** (applied to JSON/YAML representation):

```yaml
intent:
  summary: Create a shareable report for authenticated users
           ^^^^^^   ^^^^^^^^^                ^^^^^^^^^^^^^^
           CREATE   attribute                constraint

signature:
  name: create_shareable_report
  parameters:
    - name: user
      type: User  ← linked to src/models/user.py:User (hover to navigate)
            ^^^^
            resolved from context
```

#### 2. Hover States

**On prompt tokens**:
```
Hovering over "report":
┌─────────────────────────────────────┐
│ Entity: report (e1)                 │
│ Type: Report (Document)             │
│ Confidence: 90%                     │
│                                     │
│ Used in:                            │
│   • Return type: ShareableReport    │
│   • Creates in database             │
│                                     │
│ Attributes:                         │
│   • shareable (applied at token 6)  │
│                                     │
│ → Click to view in IR               │
└─────────────────────────────────────┘
```

**On IR elements**:
```
Hovering over "User" type:
┌─────────────────────────────────────┐
│ Type: User                          │
│ Source: Codebase                    │
│ File: src/models/user.py            │
│                                     │
│ Definition:                         │
│   class User:                       │
│       id: UUID                      │
│       username: str                 │
│       is_authenticated: bool        │
│                                     │
│ → Cmd+Click to open file            │
└─────────────────────────────────────┘
```

#### 3. Inline Annotations

**For ambiguities**:
```
Create a report and make it shareable
                        ~~~~~~~~~~~~~
                        ⚠️ Unclear: What does "shareable" mean?

                        Suggestions:
                        • Public URL
                        • Email sharing
                        • Export as PDF

                        [Resolve →]
```

**For holes**:
```
signature:
  returns: ???
           ^^^
           ⚠️ Missing: Return type not specified

           Suggestions (from context):
           • Report (most likely based on prompt)
           • ShareableReport (custom type)
           • dict[str, Any] (generic)

           [Choose type →]
```

**For implicit terms**:
```
assertions:
  - predicate: user.is_authenticated == True
    💡 Inferred precondition (confidence: 95%)
       "Report must be created before being made shareable"

       [Accept] [Reject] [Edit]
```

#### 4. Relationship Visualization

**Entity relationship graph** (shown in sidebar or modal):

```
        creates
   user ──────→ report
                  │
                  │ has_attribute
                  ↓
              shareable
                  │
                  │ requires
                  ↓
              authenticated
```

**Click on any node** to highlight in prompt and IR.

#### 5. Provenance Tracking

**Show where each IR element came from**:

```yaml
signature:
  name: create_shareable_report
        ^^^^^^^^^^^^^^^^^^^^^^
        Derived from:
          • "Create" → verb at token 0
          • "report" → noun at token 3
          • "shareable" → attribute at token 6
```

### Color Scheme

| Element Type | Color | Example |
|--------------|-------|---------|
| **Entity (Data)** | Blue | `report`, `file`, `record` |
| **Entity (Actor)** | Purple | `user`, `admin`, `system` |
| **Attribute** | Green | `shareable`, `public`, `readonly` |
| **Constraint** | Orange | `authenticated`, `if`, `unless` |
| **Hole** | Red | `???`, unresolved element |
| **Ambiguity** | Yellow | Highlighted with ⚠️ |
| **Implicit Term** | Light blue | With 💡 icon |
| **Resolved** | Gray | Checkmark ✓ |

---

## Interactive Refinement Protocol

### Refinement Loop

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Present annotated prompt + IR with issues highlighted     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ 2. User clicks on hole/ambiguity                             │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ 3. System shows refinement panel with:                       │
│    • Context (surrounding prompt)                            │
│    • Suggestions (from analysis + context)                   │
│    • Custom input field                                      │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ 4. User selects suggestion or provides custom resolution     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ 5. System updates IR:                                        │
│    • Fills in hole                                           │
│    • Marks ambiguity as resolved                             │
│    • Propagates changes (updates related elements)           │
│    • Re-runs consistency checks                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│ 6. UI updates:                                               │
│    • Highlights fade/change color (red → green)              │
│    • New annotations appear (if propagation revealed issues) │
│    • IR view refreshes                                       │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ More issues? → Loop back to step 1
                     │ Complete? → Exit to code generation
                     ↓
                  [Done]
```

### Refinement UI Example

**Before refinement**:
```
┌────────────────────────────────────────────────────────┐
│ Prompt:                                                │
│ Create a report and make it shareable                  │
│                                                        │
│ IR:                                                    │
│   signature:                                           │
│     name: create_report                                │
│     parameters:                                        │
│       - name: ???  ← ⚠️ Missing parameter              │
│     returns: ???   ← ⚠️ Missing return type            │
│                                                        │
│ 2 issues found  [Start refinement →]                  │
└────────────────────────────────────────────────────────┘
```

**During refinement** (user clicked on "Missing return type"):
```
┌────────────────────────────────────────────────────────┐
│ Resolve: Return type                                   │
│                                                        │
│ Context:                                               │
│ "Create a report and make it shareable"               │
│          ^^^^^^                                        │
│                                                        │
│ Suggestions from context:                             │
│  ○ Report                                              │
│     Standard report type (src/models/report.py)       │
│                                                        │
│  ● ShareableReport  ← Selected                        │
│     Report with sharing metadata                      │
│                                                        │
│  ○ dict[str, Any]                                      │
│     Generic dictionary                                 │
│                                                        │
│  ○ Custom type...                                      │
│     [Enter type name: ________________]                │
│                                                        │
│ [Cancel]  [Apply]                                      │
└────────────────────────────────────────────────────────┘
```

**After refinement**:
```
┌────────────────────────────────────────────────────────┐
│ IR:                                                    │
│   signature:                                           │
│     name: create_report                                │
│     parameters:                                        │
│       - name: user     ← ✓ Resolved                    │
│         type: User                                     │
│     returns: ShareableReport  ← ✓ Resolved             │
│                                                        │
│ All issues resolved!  [Generate code →]               │
└────────────────────────────────────────────────────────┘
```

---

## Reverse Mode Integration

### IR from Code: Same Structure, Different Pipeline

When lifting code to IR (reverse mode), the system produces the **same Enhanced IR structure**, but follows a different analysis pipeline:

```
┌─────────────────────────────────────────────────────────┐
│                    Code Input                            │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│        Static Analysis (AST, type hints, docs)          │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│     Dynamic Analysis (optional: traces, CodeQL)         │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│            Build Enhanced IR                            │
│  - Extract entities from code                           │
│  - Infer intent from function names, docstrings         │
│  - Map types from type hints                            │
│  - Extract effects from code (I/O, mutations)           │
│  - Generate assertions from conditions                  │
│  - Add provenance (links to code)                       │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│          Annotate for UI (same as forward mode)         │
└─────────────────────────────────────────────────────────┘
```

### Reverse Mode IR Example

Given this code:

```python
def create_shareable_report(user: User, report_data: dict) -> Report:
    """Create a report and make it shareable for authenticated users."""
    if not user.is_authenticated:
        raise PermissionError("User must be authenticated")

    report = Report.create(report_data)
    report.shareable = True
    report.save()
    return report
```

The system generates:

```python
EnhancedIR(
    # Core IR (same structure as forward mode)
    intent=IntentClause(
        summary="Create a shareable report for authenticated users",
        rationale="Extracted from docstring"
    ),
    signature=SigClause(
        name="create_shareable_report",
        parameters=[
            Parameter(name="user", type_hint="User", description="Authenticated user"),
            Parameter(name="report_data", type_hint="dict", description="Report data")
        ],
        returns="Report"
    ),
    effects=[
        EffectClause(description="Creates a new Report object"),
        EffectClause(description="Saves report to database")
    ],
    assertions=[
        AssertClause(
            predicate="user.is_authenticated == True",
            rationale="Extracted from condition at line 3"
        )
    ],

    # Semantic layer
    semantic=SemanticMetadata(
        entities={
            "e1": Entity(
                id="e1",
                name="report",
                entity_type=EntityType.DATA_STRUCTURE,
                semantic_type=SemanticType("Report", confidence=1.0),
                resolved=True,
                linked_to="line 6: report = Report.create(...)"
            ),
            "e2": Entity(
                id="e2",
                name="user",
                entity_type=EntityType.ACTOR,
                semantic_type=SemanticType("User", confidence=1.0),
                resolved=True,
                linked_to="parameter at line 1"
            )
        },
        # ... similar to forward mode
    ),

    # Annotations link IR elements back to code
    annotations=AnnotationLayer(
        ir_to_code_links={
            "ir.signature.name": "line 1:5-26",
            "ir.assertions[0]": "line 3:8-35",
            "ir.effects[0]": "line 6:12-38"
        }
    ),

    # Provenance
    source_code="def create_shareable_report(...)...",
    source_prompt=None  # No prompt (reverse mode)
)
```

### Visual Affordances: Code ↔ IR

**Split view** with bidirectional highlighting:

```
┌──────────────────────────────┬──────────────────────────────┐
│ Code                         │ IR                           │
├──────────────────────────────┼──────────────────────────────┤
│ def create_shareable_report( │ signature:                   │
│     ^^^^^^^^^^^^^^^^^^^^^^^^ │   name: create_shareable_... │
│     (hover: shows intent)    │   ^^^^ (hover: shows code)   │
│                              │                              │
│     user: User,              │   parameters:                │
│     ^^^^  ^^^^ (linked)      │     - name: user             │
│                              │       ^^^^^ (linked)         │
│                              │       type: User             │
│                              │       ^^^^ (linked)          │
│                              │                              │
│     if not user.is_authenti…│   assertions:                │
│        ^^^^^^^^^^^^^^^^^^^   │     - predicate: user.is...  │
│        (linked to assertion) │       ^^^^^^^^^^^ (linked)   │
└──────────────────────────────┴──────────────────────────────┘
```

**Click on code** → highlights corresponding IR element
**Click on IR** → highlights corresponding code

---

## Implementation Phases

### Phase 1: Foundation (Months 1-2)

**Goal**: Basic semantic analysis and typed holes

**Deliverables**:
1. Enhanced IR data model (Python classes)
2. Entity resolver (basic coreference)
3. Typed hole system
4. Basic UI annotations (highlights only)

**Milestones**:
- M1.1: Data model implemented and tested
- M1.2: Entity resolution for simple prompts (90% accuracy)
- M1.3: Typed holes generated and stored
- M1.4: Prompt highlighting works in UI

**Success Criteria**:
- Can process "Create X and do Y to it" prompts
- Resolves "it" to "X" correctly
- Creates typed holes for missing types
- UI shows basic highlights

---

### Phase 2: Deep Analysis (Months 3-4)

**Goal**: Clause analysis, ambiguity detection, intent inference

**Deliverables**:
1. Clause dependency graph builder
2. Ambiguity detector
3. Implicit term finder
4. Intent classifier

**Milestones**:
- M2.1: Clause analysis working
- M2.2: Ambiguity detection (precision 80%, recall 70%)
- M2.3: Intent signatures generated
- M2.4: Implicit terms identified

**Success Criteria**:
- Handles complex multi-clause prompts
- Detects most ambiguities
- Infers intent correctly for common patterns
- Finds 60%+ of implicit terms

---

### Phase 3: Interactive Refinement (Months 5-6)

**Goal**: Full refinement loop with UI

**Deliverables**:
1. Refinement UI components
2. Suggestion generator
3. IR update propagation
4. Consistency checker

**Milestones**:
- M3.1: Refinement panel functional
- M3.2: Suggestions generated from context
- M3.3: Real-time IR updates
- M3.4: End-to-end refinement workflow

**Success Criteria**:
- Users can resolve all holes interactively
- IR updates propagate correctly
- Consistency checks catch contradictions
- Refinement completes in <5 interactions for typical prompts

---

### Phase 4: Visual Intelligence (Months 7-8)

**Goal**: Full IDE-style experience

**Deliverables**:
1. Advanced hover states
2. Relationship visualization
3. Provenance tracking
4. Bidirectional linking (prompt ↔ IR)

**Milestones**:
- M4.1: Rich hover tooltips
- M4.2: Relationship graph viewer
- M4.3: Click-to-navigate works both ways
- M4.4: Provenance displayed throughout

**Success Criteria**:
- Hover shows complete context
- Relationship graph is interactive
- Users can navigate seamlessly between views
- Provenance is clear at all levels

---

### Phase 5: Reverse Mode Integration (Months 9-10)

**Goal**: Same visual experience for code → IR

**Deliverables**:
1. Code analysis pipeline
2. Code ↔ IR linking
3. Split-view UI
4. Reverse mode refinement

**Milestones**:
- M5.1: Static analysis produces Enhanced IR
- M5.2: Code highlighting linked to IR
- M5.3: Split view functional
- M5.4: Can refine lifted IR

**Success Criteria**:
- Code lifts to same IR structure as forward mode
- Visual affordances work in both directions
- Split view is intuitive
- Refinement works on lifted IR

---

### Phase 6: Polish & Optimization (Months 11-12)

**Goal**: Production-ready system

**Deliverables**:
1. Performance optimization
2. Comprehensive testing
3. User documentation
4. Deployment

**Milestones**:
- M6.1: Analysis completes in <2s for typical prompts
- M6.2: 95%+ test coverage
- M6.3: Documentation complete
- M6.4: Deployed to production

**Success Criteria**:
- Handles 100+ prompt sessions/minute
- <1% error rate
- Users rate experience 8/10+
- Zero critical bugs

---

## Technical Requirements

### NLP & ML Dependencies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Tokenization** | spaCy or NLTK | Basic NLP pipeline |
| **Entity Recognition** | spaCy NER + custom rules | Entity extraction |
| **Coreference Resolution** | NeuralCoref or AllenNLP | Resolve "it", "them", etc. |
| **Dependency Parsing** | spaCy | Clause structure |
| **Type Inference** | Custom heuristics + LLM | Semantic type assignment |
| **Intent Classification** | Fine-tuned transformer (BERT/RoBERTa) | Intent signatures |
| **Suggestion Generation** | LLM (Claude/GPT) + retrieval | Contextual suggestions |

### Backend Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI (existing)
- **NLP**: spaCy 3.7+
- **ML**: Transformers (Hugging Face)
- **Storage**: PostgreSQL (for IR history) + Redis (for sessions)
- **Search**: Elasticsearch (for context retrieval)

### Frontend Stack

- **Framework**: React 18+ (existing)
- **UI Components**: shadcn/ui (existing)
- **Syntax Highlighting**: Monaco Editor or CodeMirror
- **Visualization**: D3.js (for relationship graphs)
- **State Management**: Zustand or Redux Toolkit

### Performance Targets

| Metric | Target |
|--------|--------|
| **Analysis time** | <2s for typical prompt (50-100 tokens) |
| **UI response** | <100ms for interactions |
| **Refinement latency** | <500ms for IR update |
| **Throughput** | 100+ prompts/minute |
| **Accuracy** | 90%+ entity resolution, 80%+ ambiguity detection |

---

## Open Questions

### Q1: NLP Model Selection

**Question**: Use pre-trained models or fine-tune custom models?

**Options**:
- **A**: Use off-the-shelf spaCy models
  - Pros: Fast to implement, no training needed
  - Cons: May not handle domain-specific language well

- **B**: Fine-tune BERT/RoBERTa on programming prompts
  - Pros: Better accuracy for code-related prompts
  - Cons: Requires labeled dataset, training time

- **C**: Use LLM (Claude/GPT) for all analysis
  - Pros: High accuracy, handles nuance
  - Cons: Slow, expensive, requires API

**Recommendation**: Start with (A), iterate to (B) for critical components, use (C) for suggestion generation only.

---

### Q2: Real-Time vs Batch Analysis

**Question**: Analyze as user types or on-demand?

**Options**:
- **A**: Real-time (analyze every keystroke)
  - Pros: Immediate feedback
  - Cons: High compute, may feel sluggish

- **B**: Debounced (analyze after 500ms pause)
  - Pros: Balance of responsiveness and performance
  - Cons: Small delay

- **C**: On-demand (user clicks "Analyze")
  - Pros: No background compute
  - Cons: Extra step for user

**Recommendation**: (B) for initial analysis, (A) for incremental updates after first analysis.

---

### Q3: Context Retrieval Strategy

**Question**: How to retrieve relevant context (code, docs) efficiently?

**Options**:
- **A**: Full-text search (Elasticsearch)
  - Pros: Fast, well-understood
  - Cons: May miss semantic relevance

- **B**: Semantic search (embeddings + vector DB)
  - Pros: Finds semantically similar content
  - Cons: Slower, requires embedding model

- **C**: Hybrid (lexical + semantic)
  - Pros: Best of both worlds
  - Cons: More complex

**Recommendation**: Start with (A), add (B) if precision is insufficient.

---

### Q4: Ambiguity Resolution Modes

**Question**: Should system auto-resolve low-severity ambiguities?

**Options**:
- **A**: Always ask user
  - Pros: User in control
  - Cons: Many interruptions

- **B**: Auto-resolve if confidence > 90%
  - Pros: Fewer interruptions
  - Cons: May make wrong choices

- **C**: Configurable (user sets threshold)
  - Pros: Flexible
  - Cons: More settings to manage

**Recommendation**: (B) with undo capability. Mark auto-resolved items visually so user can review.

---

### Q5: IR Versioning & History

**Question**: How to handle IR evolution during refinement?

**Options**:
- **A**: Store full IR at each version
  - Pros: Easy to revert
  - Cons: Storage overhead

- **B**: Store diffs between versions
  - Pros: Efficient storage
  - Cons: Complex to reconstruct

- **C**: Store critical checkpoints only
  - Pros: Balance of storage and history
  - Cons: Can't revert to arbitrary version

**Recommendation**: (C) - store initial IR, after each major refinement, and final IR.

---

## Next Steps

### Immediate Actions

1. **Review & Validate Specification**
   - Stakeholder review
   - User feedback on proposed UI
   - Technical feasibility assessment

2. **Create Proof-of-Concept**
   - Implement Phase 1 foundation (2 months)
   - Test with 10-20 sample prompts
   - Validate data model works

3. **Design User Studies**
   - Define evaluation criteria
   - Recruit test users
   - Prepare test scenarios

4. **Build Prototype UI**
   - Mock up visual affordances
   - Test interaction patterns
   - Iterate based on feedback

### Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Entity resolution accuracy** | 90%+ | Manual annotation on test set |
| **Ambiguity detection recall** | 70%+ | User study (did we catch ambiguities?) |
| **Ambiguity detection precision** | 80%+ | User study (were flagged items actually ambiguous?) |
| **User satisfaction** | 8/10 | Post-task survey |
| **Time to complete IR** | <5 min | Measured in user studies |
| **IR → Code quality** | 90%+ valid syntax | Automated testing |

---

## References

- Current IR Models: `lift_sys/ir/models.py`
- Session Management: `docs/API_SESSION_MANAGEMENT.md`
- Forward-Reverse Integration: `docs/FORWARD_REVERSE_INTEGRATION_PLAN.md`
- Code Generation: `docs/IR_TO_CODE_ARCHITECTURE.md`
- NLP Research:
  - Coreference Resolution: Lee et al. (2017) "End-to-end Neural Coreference Resolution"
  - Intent Classification: Zhang et al. (2020) "Intent Detection and Slot Filling"
  - Semantic Parsing: Berant et al. (2013) "Semantic Parsing on Freebase"

---

**Document Version**: 1.0
**Last Updated**: 2025-10-15
**Status**: Awaiting review and approval
