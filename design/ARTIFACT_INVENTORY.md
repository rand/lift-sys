# Artifact Inventory
## Existing IR Infrastructure and Capabilities

**Document Version:** 1.0
**Created:** 2025-01-11
**Purpose:** Catalog existing IR grammar, TypedHole infrastructure, and serialization utilities

---

## Table of Contents
1. [IR Grammar Specification](#ir-grammar-specification)
2. [TypedHole Infrastructure](#typedhole-infrastructure)
3. [Evidence and Metadata System](#evidence-and-metadata-system)
4. [Serialization and Persistence](#serialization-and-persistence)
5. [Gap Analysis](#gap-analysis)

---

## IR Grammar Specification

### Lark Grammar Definition

**Location:** `lift_sys/ir/parser.py` (lines 21-49)

**Complete Grammar:**

```lark
?start: ir

ir: "ir" NAME "{" intent signature effects? assertions? "}"
intent: "intent" ":" text (hole_list)?
signature: "signature" ":" NAME parameter_block return_type? (hole_list)?
parameter_block: "(" [param ("," param)*] ")"
param: NAME ":" NAME
return_type: "->" NAME

?effects: "effects" ":" effect_item+
effect_item: "-" text (hole_list)?

?assertions: "assert" ":" assertion_item+
assertion_item: "-" text (hole_list)?

?hole_list: "{" hole ("," hole)* "}"
hole: "<?" NAME ":" NAME hole_meta? "?>"
hole_meta: ("=" STRING)? ("@" NAME)?

text: /[^\n\r{}]+/

NAME: /[A-Za-z_][A-Za-z0-9_.]*/
STRING: /\"(\\.|[^\"])*\"/

%import common.WS
%ignore WS
%ignore /\#[^\n]*/
```

### Grammar Features

| Feature | Syntax | Example |
|---------|--------|---------|
| **IR Declaration** | `ir NAME { ... }` | `ir calculate_factorial { ... }` |
| **Intent Clause** | `intent: text` | `intent: Calculate factorial of n` |
| **Signature** | `signature: NAME(params) -> return` | `signature: factorial(n: int) -> int` |
| **Effects** | `effects: - text` | `effects: - Logs computation time` |
| **Assertions** | `assert: - text` | `assert: - n >= 0` |
| **TypedHoles** | `<?id: type "desc" @kind?>` | `<?timeout: int "max seconds" @assertion?>` |
| **Comments** | `# comment` | `# This is a comment` |

### Parser Capabilities

**Class:** `IRParser` (`lift_sys/ir/parser.py`)

**Key Methods:**

```python
def parse(self, source: str) -> IntermediateRepresentation:
    """Parse IR text into object model."""

def parse_file(self, path: str | Path) -> IntermediateRepresentation:
    """Parse IR from file."""

def dumps(self, ir: IntermediateRepresentation) -> str:
    """Render IR object back to textual form."""
```

**Configuration:**

```python
@dataclass
class ParserConfig:
    allow_typed_holes: bool = True  # Can disable hole parsing
```

**Verified Capabilities:**
- ✅ Full round-trip: `text → IR object → text` (test: `test_ir_round_trip_fidelity`)
- ✅ Hole parsing with metadata
- ✅ Comment stripping
- ✅ Multi-line text support
- ✅ Optional sections (effects, assertions)

---

## TypedHole Infrastructure

### HoleKind Taxonomy

**Location:** `lift_sys/ir/models.py` (lines 9-16)

```python
class HoleKind(str, Enum):
    """Enumeration describing the semantic purpose of a typed hole."""

    INTENT = "intent"              # Clarify high-level purpose
    SIGNATURE = "signature"        # Refine function contract
    EFFECT = "effect"              # Detail side effects
    ASSERTION = "assertion"        # Strengthen invariants
    IMPLEMENTATION = "implementation"  # Code-level details
```

**Design Rationale:**

Each HoleKind guides users on what type of refinement is needed:
- **INTENT**: "What should this do?"
- **SIGNATURE**: "What are the inputs/outputs?"
- **EFFECT**: "What external interactions occur?"
- **ASSERTION**: "What must always be true?"
- **IMPLEMENTATION**: "How should this be coded?"

### TypedHole Data Model

**Location:** `lift_sys/ir/models.py` (lines 19-42)

```python
@dataclass(slots=True)
class TypedHole:
    """Explicit representation of an unknown value in the IR."""

    identifier: str                       # Unique ID within IR (e.g., "timeout")
    type_hint: str                        # Expected type (e.g., "int", "string")
    description: str = ""                 # Human-readable explanation
    constraints: Dict[str, str] = field(default_factory=dict)  # Optional constraints
    kind: HoleKind = HoleKind.INTENT      # Semantic category

    def label(self) -> str:
        """Return a human friendly label for visualizations."""
        return f"<?{self.identifier}: {self.type_hint}?>"

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "type_hint": self.type_hint,
            "description": self.description,
            "constraints": self.constraints,
            "kind": self.kind.value,
        }
```

### Hole Distribution in IR Clauses

| Clause | Hole Field | Purpose |
|--------|------------|---------|
| **IntentClause** | `holes: List[TypedHole]` | Ambiguities in high-level purpose |
| **SigClause** | `holes: List[TypedHole]` | Missing parameter types or return type |
| **EffectClause** | `holes: List[TypedHole]` | Unknown side effects or interactions |
| **AssertClause** | `holes: List[TypedHole]` | Under-specified invariants |

**Hole Collection Method:**

```python
def typed_holes(self) -> List[TypedHole]:
    """Return every typed hole contained within the IR."""
    holes: List[TypedHole] = []
    holes.extend(self.intent.holes)
    holes.extend(self.signature.holes)
    for effect in self.effects:
        holes.extend(effect.holes)
    for assertion in self.assertions:
        holes.extend(assertion.holes)
    return holes
```

**Usage Pattern:**

```python
# Example: Creating a hole for missing timeout
timeout_hole = TypedHole(
    identifier="request_timeout",
    type_hint="int",
    description="Maximum seconds to wait for API response",
    kind=HoleKind.ASSERTION
)
```

---

## Evidence and Metadata System

### Metadata Structure

**Location:** `lift_sys/ir/models.py` (lines 102-114)

```python
@dataclass(slots=True)
class Metadata:
    source_path: Optional[str] = None          # File path where IR originated
    language: Optional[str] = None             # Source language ("python", "rust", etc.)
    origin: Optional[str] = None               # "reverse" | "forward" | "manual"
    evidence: List[Dict[str, object]] = field(default_factory=list)  # Provenance records

    def to_dict(self) -> Dict[str, object]:
        return {
            "source_path": self.source_path,
            "language": self.language,
            "origin": self.origin,
            "evidence": self.evidence,
        }
```

### Evidence Schema

Evidence records track **provenance** of IR elements (where assertions/effects came from).

**Typical Evidence Entry:**

```python
{
    "source": "codeql",             # Analyzer that produced this
    "query": "security/default",    # Query or rule ID
    "finding": {
        "id": "CVE-2024-...",
        "severity": "high",
        "location": {"line": 42, "col": 10},
        "description": "SQL injection risk"
    },
    "timestamp": "2025-01-11T12:00:00Z",
    "confidence": 0.95              # Optional: analyzer confidence
}
```

**Evidence Sources:**

| Source | Description | Evidence Fields |
|--------|-------------|-----------------|
| **CodeQL** | Static security analysis | `query`, `finding`, `location`, `severity` |
| **Daikon** | Dynamic invariant detection | `invariant`, `confidence`, `traces_observed` |
| **Stack Graph** | Symbol relationship analysis | `relationship`, `source`, `target`, `relation_type` |
| **Human** | Manual annotation | `author`, `rationale`, `timestamp` |

### Evidence Usage in Reverse Mode

**Location:** `lift_sys/reverse_mode/lifter.py`

```python
def lift(self, target_module: str) -> IntermediateRepresentation:
    # ... analysis steps ...

    evidence = []
    if codeql_results:
        evidence.append({
            "source": "codeql",
            "findings": codeql_results,
            "timestamp": datetime.utcnow().isoformat()
        })
    if daikon_invariants:
        evidence.append({
            "source": "daikon",
            "invariants": daikon_invariants,
            "timestamp": datetime.utcnow().isoformat()
        })

    metadata = Metadata(
        source_path=target_module,
        origin="reverse",
        language="python",
        evidence=evidence,
    )

    return IntermediateRepresentation(
        intent=intent,
        signature=signature,
        effects=effects,
        assertions=assertions,
        metadata=metadata,
    )
```

---

## Serialization and Persistence

### Round-Trip Guarantee

**Verified by Test:** `tests/unit/test_models.py::test_ir_round_trip_fidelity`

**Flow:**

```
IntermediateRepresentation (objects)
    ↓ .to_dict()
Dict[str, object]
    ↓ json.dumps()
JSON String
    ↓ json.loads()
Dict[str, object]
    ↓ IntermediateRepresentation.from_dict()
IntermediateRepresentation (objects)
```

**Guarantees:**
- ✅ All fields preserved (including holes)
- ✅ HoleKind enum values correctly serialized/deserialized
- ✅ Metadata and evidence survive round-trip
- ✅ Nested structures (parameters, assertions, effects) intact

### Serialization Methods

#### to_dict() Implementation

**Location:** `lift_sys/ir/models.py` (lines 142-170)

```python
def to_dict(self) -> Dict[str, object]:
    """Serialise the IR into a dictionary suitable for APIs."""
    return {
        "intent": {
            "summary": self.intent.summary,
            "rationale": self.intent.rationale,
            "holes": [hole.to_dict() for hole in self.intent.holes],
        },
        "signature": {
            "name": self.signature.name,
            "parameters": [param.to_dict() for param in self.signature.parameters],
            "returns": self.signature.returns,
            "holes": [hole.to_dict() for hole in self.signature.holes],
        },
        "effects": [
            {"description": eff.description, "holes": [hole.to_dict() for hole in eff.holes]}
            for eff in self.effects
        ],
        "assertions": [
            {
                "predicate": assertion.predicate,
                "rationale": assertion.rationale,
                "holes": [hole.to_dict() for hole in assertion.holes],
            }
            for assertion in self.assertions
        ],
        "metadata": self.metadata.to_dict(),
    }
```

#### from_dict() Implementation

**Location:** `lift_sys/ir/models.py` (lines 172-234)

**Key Features:**
- Handles missing optional fields with defaults
- Converts HoleKind string values back to enum
- Nested hole parsing via helper function
- Parameter objects reconstructed from dicts

**Example Usage:**

```python
# Serialize to JSON for API transport
ir_dict = ir.to_dict()
json_str = json.dumps(ir_dict)

# Deserialize from API response
response_dict = json.loads(json_str)
ir_copy = IntermediateRepresentation.from_dict(response_dict)

assert ir == ir_copy  # Full fidelity
```

### Parser-Based Serialization

**Alternative:** Human-readable text format

```python
parser = IRParser()

# Object → Text
ir_text = parser.dumps(ir)
# Output:
# ir calculate_factorial {
#   intent: Calculate factorial of n
#   signature: factorial(n: int) -> int
#   assert:
#     - n >= 0
#     - result >= 1
# }

# Text → Object
ir_copy = parser.parse(ir_text)
```

**Comparison:**

| Format | Use Case | Round-Trip | Human-Readable |
|--------|----------|------------|----------------|
| **to_dict/from_dict** | API transport, JSON storage | ✅ Perfect | ❌ No (verbose JSON) |
| **dumps/parse** | Config files, user editing | ✅ Perfect | ✅ Yes (clean syntax) |

---

## Gap Analysis

### Existing Capabilities ✅

| Capability | Status | Notes |
|-----------|--------|-------|
| TypedHole data model | ✅ Complete | Full support with kind taxonomy |
| Hole serialization | ✅ Complete | to_dict/from_dict working |
| Grammar parsing | ✅ Complete | Lark-based with holes |
| Round-trip guarantee | ✅ Verified | Test coverage confirms |
| Evidence tracking | ✅ Complete | Metadata with provenance |
| Multi-source fusion | ✅ Complete | CodeQL + Daikon + StackGraph |
| Hole collection | ✅ Complete | `typed_holes()` method |

### Missing Components ❌

| Component | Priority | Impact |
|-----------|----------|--------|
| **Prompt→IR Translation** | 🔴 HIGH | Cannot create IR from NL yet |
| **Ambiguity Detection** | 🔴 HIGH | No automatic hole generation |
| **Hole Resolution Logic** | 🔴 HIGH | No way to fill holes programmatically |
| **Session State Management** | 🔴 HIGH | No versioning or revision tracking |
| **IR Validation** | 🟡 MEDIUM | Basic structure checks only |
| **Hole Suggestion Engine** | 🟡 MEDIUM | No guided prompts for resolution |
| **Conflict Detection** | 🟡 MEDIUM | No check for contradictory holes |
| **Incremental Verification** | 🟠 LOW | SMT runs on full IR, not diffs |

### Integration Points Needed

| Integration | Required Changes |
|-------------|------------------|
| **API State** | Add `session_manager` and `session_store` fields |
| **Planner** | Add `current_session` field, load from session |
| **WebSocket** | Add session event types (`session_updated`, `hole_resolved`) |
| **Frontend** | New PromptWorkbench view, enhanced IrView with editing |

### Serialization Gaps

**Current:** IR can be serialized, but **session state** cannot.

**Needed:**
- `PromptSession.to_dict() / from_dict()`
- `IRDraft.to_dict() / from_dict()`
- `HoleResolution.to_dict() / from_dict()`

**Storage Requirements:**
- In-memory: Already possible (dict storage)
- Persistent: Need file or database backend (future work)

---

## Test Coverage

### Existing Tests

| Test | Coverage | Status |
|------|----------|--------|
| `test_ir_round_trip_fidelity` | Full serialization | ✅ Passing |
| `test_ir_with_holes_round_trip` | Holes survive round-trip | ✅ Passing |
| `test_metadata_serialization` | Evidence preserved | ✅ Passing |
| `test_parse_ir_with_typed_holes` | Grammar parsing | ✅ Passing |
| `test_typed_hole_kinds` | HoleKind enum | ✅ Passing |
| `test_typed_holes_collection` | `typed_holes()` method | ✅ Passing |

**Total Coverage:** 48 IR-related tests passing

### Gaps in Test Coverage

**Missing Tests:**
- ❌ Hole resolution (applying user input to fill holes)
- ❌ Ambiguity detection (automatic hole generation)
- ❌ Session state serialization
- ❌ Incremental IR updates (versioning)
- ❌ Conflict detection between holes

---

## Recommendations

### Phase 1: Core Extensions

1. **Implement hole resolution logic**
   - Method: `IRDraft.fill_hole(hole_id, resolution_text) → IRDraft`
   - Update IR by replacing hole with resolved value
   - Preserve provenance in metadata

2. **Create ambiguity detector**
   - Analyze IR for under-specified sections
   - Generate TypedHoles automatically
   - Provide actionable descriptions

3. **Add session serialization**
   - Implement `to_dict/from_dict` for all session types
   - Ensure round-trip tests pass

### Phase 2: Integration

4. **Extend AppState**
   - Add session manager field
   - Initialize on `/config` call

5. **Add API endpoints**
   - `/spec-sessions` CRUD operations
   - Use existing telemetry system

6. **Frontend enhancements**
   - Prompt workbench view
   - Hole resolution UI components

### Phase 3: Polish

7. **Validation rules**
   - Check all holes resolved before finalization
   - SMT verification on each draft

8. **Suggestion engine**
   - Context-aware prompts for hole resolution
   - Example resolutions based on hole kind

---

**Document Status:** ✅ Complete (Phase 0.2)
**Next Step:** Phase 0.3 - UI Entry Point Audit
