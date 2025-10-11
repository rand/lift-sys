# Prompt-to-IR Architecture Design
## System Architecture for Iterative Specification Refinement

**Document Version:** 1.0
**Created:** 2025-01-11
**Purpose:** Define architecture for natural language to IR translation with human-in-the-loop refinement

---

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [New Components Design](#new-components-design)
4. [Integration Points](#integration-points)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Implementation Strategy](#implementation-strategy)

---

## Executive Summary

This document defines the architecture for extending lift-sys with **iterative prompt-to-IR refinement** capabilities. Users will be able to:

1. Submit natural language prompts describing desired functionality
2. Receive machine-translated IR drafts with ambiguities marked as TypedHoles
3. Iteratively refine holes with human clarifications
4. Verify consistency via SMT checking
5. Generate code from finalized IR

The architecture integrates seamlessly with existing reverse-mode, forward-mode, and planner subsystems.

---

## Current Architecture Analysis

### Existing API Routes

| Route | Method | Purpose | State Changes |
|-------|--------|---------|---------------|
| `/` | GET | Root/info endpoint | None |
| `/health` | GET | Health check | None |
| `/config` | POST | Configure synthesizer/lifter | Sets `STATE.config`, creates `synthesizer` & `lifter` |
| `/repos/open` | POST | Load git repository | Loads repo into `STATE.lifter.repo` |
| `/reverse` | POST | Lift IR from code | Creates IR, loads into `STATE.planner`, publishes progress |
| `/forward` | POST | Generate code from IR | Uses synthesizer to create payload |
| `/plan` | GET | Get current plan state | None (read-only) |
| `/ws/progress` | WebSocket | Stream real-time events | Subscribe to progress queue |

### Centralized State (AppState)

```python
class AppState:
    # Core services
    parser: IRParser                    # Parse IR text ↔ objects
    planner: Planner                    # Plan orchestration with CDCL
    config: Optional[SynthesizerConfig] # Model endpoint config
    synthesizer: Optional[CodeSynthesizer]  # Forward mode
    lifter: Optional[SpecificationLifter]   # Reverse mode

    # Telemetry system
    progress_log: deque[dict]           # Ring buffer (maxlen=256)
    _progress_subscribers: set[Queue]   # WebSocket subscribers
```

**Key Methods:**
- `publish_progress(event)` - Emit event to all subscribers
- `subscribe_progress()` / `unsubscribe_progress()` - Queue-based pub/sub
- `set_config(request)` - Initialize services
- `reset()` - Clear all state

### Telemetry System

**Dual-Channel Event Streaming:**

1. **General Progress Events** (`STATE.publish_progress()`)
   - Reverse mode stages (codeql_scan, daikon_invariants, planner_alignment)
   - Forward mode stages (constraints, stream)
   - Custom progress checkpoints

2. **Planner Events** (`STATE.planner.consume_events()`)
   - Decision tracking
   - Learned clauses
   - Conflict resolution
   - Backjumping notifications

**WebSocket Emitter Pattern:**
```python
async def websocket_emitter() -> AsyncIterator[str]:
    yield json.dumps({"type": "planner_ready", "data": {}})
    queue = STATE.subscribe_progress()
    while True:
        # Emit planner events
        for event in STATE.planner.consume_events():
            yield json.dumps(event)
        # Emit progress events
        event = await queue.get()  # with timeout & heartbeat
        yield json.dumps(event)
```

### Planner Lifecycle

```
┌─────────────────────────────────────────────────────┐
│ Planner State Machine                               │
│                                                     │
│  load_ir(ir)                                        │
│      ↓                                              │
│  derive_plan(ir) → Plan with Steps                  │
│      ↓                                              │
│  step(step_id, success, reason)                     │
│      ↓                                              │
│  [SUCCESS] → Update state.completed                 │
│  [FAILURE] → Record conflict, learn clause,         │
│              update implication graph,              │
│              suggest resolution                     │
│      ↓                                              │
│  _filter_next_steps(candidates)                     │
│      ↓                                              │
│  PlannerStepResult(next_steps, clauses, backjump)   │
└─────────────────────────────────────────────────────┘
```

**Key Components:**
- `PlannerState`: Tracks completed steps, conflicts, decision levels, checkpoints
- `ClauseStore`: Stores learned clauses, checks for conflicts
- `ImplicationGraph`: Tracks decision literals and dependencies
- `Plan`: Immutable workflow with steps, goals, decision literals

### Frontend Architecture

**Simple Single-Page App:**
- No routing framework (React Router, etc.)
- State managed via `useState` hooks
- 5 main views: Configuration, Repository, IR Review, Planner, IDE

**View Responsibilities:**

| View | Purpose | API Interactions |
|------|---------|------------------|
| ConfigurationView | Set model endpoint, provider | `POST /config` |
| RepositoryView | Load repo, trigger reverse mode | `POST /repos/open`, `POST /reverse` |
| IrView | Display & edit IR text | None (local state) |
| PlannerView | Show plan graph, holes, assists | `GET /plan`, `WS /ws/progress` |
| IdeView | Integrated development | Multiple endpoints |

**State Management:** Local component state, no global store (Zustand/Redux)

### Reverse Mode Pipeline

```
Repository
    ↓
SpecificationLifter.load_repository(path)
    ↓
SpecificationLifter.lift(module)
    ↓
├─ CodeQLAnalyzer (mocked) → Security assertions
├─ DaikonAnalyzer (mocked) → Runtime invariants
└─ StackGraphAnalyzer → Symbol relationships
    ↓
SpecificationFusion
    ↓
IntermediateRepresentation (with TypedHoles)
    ↓
Planner.load_ir(ir)
```

### Forward Mode Pipeline

```
IntermediateRepresentation
    ↓
CodeSynthesizer.generate(ir)
    ↓
ControllerRuntime
    ↓
├─ Compile constraints from assertions
├─ Compile schema from signature
├─ Compile grammar from effects
└─ Execute WASM lifecycle hooks
    ↓
Request Payload (provider-agnostic)
    ↓
{prompt, constraints, stream, provider, ...}
```

### Existing TypedHole Support

**Data Model (`lift_sys/ir/models.py`):**

```python
class HoleKind(Enum):
    INTENT = "intent"
    SIGNATURE = "signature"
    EFFECT = "effect"
    ASSERTION = "assertion"
    IMPLEMENTATION = "implementation"

@dataclass
class TypedHole:
    identifier: str
    type_hint: str
    description: str = ""
    constraints: Dict[str, str] = field(default_factory=dict)
    kind: HoleKind = HoleKind.INTENT
```

**IR Clauses with Holes:**
- `IntentClause.holes: List[TypedHole]`
- `SigClause.holes: List[TypedHole]`
- `EffectClause.holes: List[TypedHole]`
- `AssertClause.holes: List[TypedHole]`

**Parser Support (`lift_sys/ir/parser.py`):**
- Grammar: `hole: "<?" NAME ":" NAME hole_meta? "?>"`
- Metadata: `hole_meta: ("=" STRING)? ("@" NAME)?`
- Round-trip serialization with `dumps()` and `parse()`

---

## New Components Design

### 1. Prompt Session Management

**Package:** `lift_sys/spec_sessions/`

**Core Models:**

```python
@dataclass
class PromptRevision:
    """Single user input during refinement."""
    timestamp: str
    content: str  # Natural language text
    revision_type: str  # "initial" | "hole_fill" | "constraint_add"
    target_hole: Optional[str] = None

@dataclass
class IRDraft:
    """Versioned IR snapshot."""
    version: int
    ir: IntermediateRepresentation
    validation_status: str  # "pending" | "valid" | "contradictory"
    smt_results: List[Dict[str, Any]]  # SMT verification results
    ambiguities: List[str]  # Unresolved hole identifiers

@dataclass
class HoleResolution:
    """User's clarification for a typed hole."""
    hole_id: str
    resolution_text: str
    resolution_type: str  # "clarify_intent" | "add_constraint" | "refine_signature"
    applied: bool = False

@dataclass
class PromptSession:
    """Full refinement session state."""
    session_id: str
    created_at: str
    updated_at: str
    status: str  # "active" | "finalized" | "abandoned"

    # Revision history
    revisions: List[PromptRevision]
    ir_drafts: List[IRDraft]

    # Current state
    current_draft: Optional[IRDraft]
    pending_resolutions: List[HoleResolution]

    # Metadata
    source: str  # "prompt" | "reverse_mode"
    metadata: Dict[str, Any]
```

**Storage Interface:**

```python
class SessionStore(Protocol):
    """Pluggable storage backend."""
    def create(self, session: PromptSession) -> str: ...
    def get(self, session_id: str) -> Optional[PromptSession]: ...
    def update(self, session: PromptSession) -> None: ...
    def list_active(self) -> List[PromptSession]: ...
    def delete(self, session_id: str) -> None: ...

class InMemorySessionStore:
    """Default in-memory implementation."""
    _sessions: Dict[str, PromptSession]
```

### 2. Prompt Translation Pipeline

**Module:** `lift_sys/spec_sessions/translator.py`

```python
class PromptToIRTranslator:
    """Converts natural language to IR drafts."""

    def __init__(self, synthesizer: CodeSynthesizer, parser: IRParser):
        self.synthesizer = synthesizer
        self.parser = parser

    async def translate(
        self,
        prompt: str,
        context: Optional[IntermediateRepresentation] = None
    ) -> IRDraft:
        """
        1. Send prompt to controller runtime with IR generation schema
        2. Parse LLM output into IR structure
        3. Identify ambiguities (missing constraints, vague intent)
        4. Create TypedHoles for ambiguities
        5. Return IRDraft with validation status
        """
        pass

    def detect_ambiguities(self, ir: IntermediateRepresentation) -> List[TypedHole]:
        """Heuristic ambiguity detection."""
        pass

    def fill_hole(
        self,
        draft: IRDraft,
        hole_id: str,
        resolution: str
    ) -> IRDraft:
        """Apply user resolution to create new draft version."""
        pass
```

### 3. Ambiguity Detection

**Module:** `lift_sys/spec_sessions/ambiguity.py`

```python
class AmbiguityDetector:
    """Identifies issues in IR drafts."""

    def __init__(self, verifier: SMTChecker):
        self.verifier = verifier

    def analyze(self, ir: IntermediateRepresentation) -> AmbiguityReport:
        """
        Returns:
            AmbiguityReport with:
            - missing_constraints: Assertions that are under-specified
            - contradictions: SMT unsat results
            - vague_intents: Intent clauses with low specificity
            - incomplete_signatures: Parameters missing type hints
        """
        pass

@dataclass
class AmbiguityReport:
    missing_constraints: List[str]
    contradictions: List[Dict[str, Any]]
    vague_intents: List[str]
    incomplete_signatures: List[str]

    def to_typed_holes(self) -> List[TypedHole]:
        """Convert ambiguities to TypedHoles with actionable descriptions."""
        pass
```

### 4. Session Manager

**Module:** `lift_sys/spec_sessions/manager.py`

```python
class SpecSessionManager:
    """Orchestrates prompt session lifecycle."""

    def __init__(
        self,
        store: SessionStore,
        translator: PromptToIRTranslator,
        detector: AmbiguityDetector,
        planner: Planner,
    ):
        self.store = store
        self.translator = translator
        self.detector = detector
        self.planner = planner

    async def create_from_prompt(self, prompt: str) -> PromptSession:
        """Initialize session from natural language."""
        pass

    async def create_from_reverse_mode(self, ir: IntermediateRepresentation) -> PromptSession:
        """Initialize session from lifted IR."""
        pass

    async def apply_resolution(
        self,
        session_id: str,
        resolution: HoleResolution
    ) -> PromptSession:
        """Apply user hole resolution and create new draft."""
        pass

    async def finalize(self, session_id: str) -> IntermediateRepresentation:
        """Validate and return final IR for forward mode."""
        pass

    async def get_assists(self, session_id: str) -> List[Dict[str, str]]:
        """Get actionable suggestions for current draft."""
        pass
```

---

## Integration Points

### API Server Extension

**New Routes:**

```python
# Session management
POST   /spec-sessions                 # Create from prompt or reverse mode
GET    /spec-sessions                 # List active sessions
GET    /spec-sessions/{id}            # Get session details
PUT    /spec-sessions/{id}            # Update session (apply resolution)
DELETE /spec-sessions/{id}            # Delete session
POST   /spec-sessions/{id}/finalize   # Finalize and return IR

# Hole resolution
POST   /spec-sessions/{id}/holes/{hole_id}/resolve  # Resolve typed hole
GET    /spec-sessions/{id}/assists                  # Get resolution suggestions

# WebSocket (extend existing /ws/progress)
# New event types: "session_updated", "draft_created", "hole_resolved", "ambiguity_detected"
```

**State Extension:**

```python
class AppState:
    # Existing fields...

    # New fields
    session_manager: Optional[SpecSessionManager] = None
    session_store: SessionStore = InMemorySessionStore()
```

### Planner Integration

**Enhanced Planner with Session Context:**

```python
class Planner:
    # Add session reference
    current_session: Optional[PromptSession] = None

    def load_session(self, session: PromptSession) -> Plan:
        """Load plan from session's current draft."""
        self.current_session = session
        if session.current_draft:
            return self.load_ir(session.current_draft.ir)
        raise ValueError("No draft available")
```

### Frontend Integration

**New View: Prompt Workbench**

```tsx
// frontend/src/views/PromptWorkbenchView.tsx
export function PromptWorkbenchView() {
  // State
  const [sessions, setSessions] = useState<PromptSession[]>([]);
  const [activeSession, setActiveSession] = useState<PromptSession | null>(null);
  const [promptInput, setPromptInput] = useState("");

  // Layout
  return (
    <div className="prompt-workbench">
      <PromptInput onSubmit={handleCreateSession} />
      <SessionList sessions={sessions} onSelect={setActiveSession} />
      {activeSession && (
        <>
          <IRDraftView draft={activeSession.current_draft} />
          <HoleList holes={extractHoles(activeSession)} onResolve={handleResolve} />
          <ActionPanel assists={assists} />
        </>
      )}
    </div>
  );
}
```

**Enhanced IrView with Editing:**

```tsx
// Add inline editing capabilities
<IrEditor
  value={irText}
  onChange={handleIrEdit}
  holes={typedHoles}
  onHoleClick={showHoleResolutionDialog}
/>
```

---

## Data Flow Diagrams

### Flow 1: Prompt-Based Session Creation

```
User Input (NL Prompt)
    ↓
POST /spec-sessions { "prompt": "..." }
    ↓
SpecSessionManager.create_from_prompt()
    ↓
PromptToIRTranslator.translate()
    ↓
├─ Send prompt to CodeSynthesizer with IR schema
├─ Parse LLM response into IR
├─ AmbiguityDetector.analyze(ir)
└─ Create TypedHoles for ambiguities
    ↓
Store IRDraft with holes
    ↓
Emit WebSocket: {"type": "draft_created", ...}
    ↓
Return PromptSession
```

### Flow 2: Hole Resolution

```
User Clarification
    ↓
POST /spec-sessions/{id}/holes/{hole_id}/resolve { "text": "..." }
    ↓
SpecSessionManager.apply_resolution()
    ↓
PromptToIRTranslator.fill_hole(draft, hole_id, resolution)
    ↓
├─ Update IR with resolved constraint
├─ SMTChecker.verify(updated_ir)
├─ AmbiguityDetector.analyze(updated_ir)
└─ Create new IRDraft (version++)
    ↓
Update PromptSession.current_draft
    ↓
Planner.load_ir(updated_ir)  # Refresh plan
    ↓
Emit WebSocket: {"type": "hole_resolved", ...}
    ↓
Return updated PromptSession
```

### Flow 3: Reverse Mode to Session

```
Existing Code
    ↓
POST /reverse { "module": "..." }
    ↓
SpecificationLifter.lift() → IR with holes
    ↓
POST /spec-sessions { "source": "reverse_mode", "ir": {...} }
    ↓
SpecSessionManager.create_from_reverse_mode(ir)
    ↓
├─ Create PromptSession with IR as initial draft
├─ AmbiguityDetector.analyze(ir)
└─ No translation needed (already have IR)
    ↓
Return PromptSession for refinement
```

### Flow 4: Finalization to Forward Mode

```
Refined IR (all holes resolved)
    ↓
POST /spec-sessions/{id}/finalize
    ↓
SpecSessionManager.finalize()
    ↓
├─ Validate all holes resolved
├─ SMTChecker.verify(final_ir) → must be SAT
└─ Mark session status = "finalized"
    ↓
POST /forward { "ir": final_ir.to_dict() }
    ↓
CodeSynthesizer.generate(ir)
    ↓
Generated Code
```

---

## Implementation Strategy

### Phase 0: Foundation (CURRENT)
- ✅ Document existing architecture
- ✅ Identify integration points
- ✅ Define data models

### Phase 1: Backend Services
1. Create `lift_sys/spec_sessions/` package
2. Implement data models (session, draft, resolution)
3. Implement InMemorySessionStore
4. Implement PromptToIRTranslator
5. Implement AmbiguityDetector
6. Implement SpecSessionManager
7. Add FastAPI routes
8. Write unit & integration tests

### Phase 2: Frontend Experience
1. Create PromptWorkbenchView component
2. Add session list and management UI
3. Enhance IrView with editing
4. Create HoleList component with resolution dialogs
5. Add WebSocket subscription for session events
6. Write Playwright E2E tests

### Phase 3: CLI/TUI Parity
1. Add CLI commands (`lift-sys spec refine`)
2. Extend Textual TUI with Prompt Refinement tab
3. Create Python client SDK
4. Update API documentation

### Phase 4: Documentation
1. User guides (web, CLI, API)
2. Developer documentation
3. Architectural diagrams
4. Example workflows

---

## Glossary

**Term** | **Definition**
---------|---------------
**Prompt Session** | A stateful refinement workflow from initial NL input to finalized IR
**IR Draft** | A versioned snapshot of the IR with validation status
**Typed Hole** | Explicit placeholder for ambiguous/unknown information
**Hole Resolution** | User-provided clarification that fills a typed hole
**Ambiguity Detection** | Automated analysis identifying under-specified or contradictory parts of IR
**Session Manager** | Orchestrator managing the full lifecycle of prompt sessions
**Translator** | Component converting NL prompts to IR structures
**Spec Session** | Short for "specification session" (same as prompt session)

---

## Success Criteria

- ✅ Users can create sessions from NL prompts
- ✅ Ambiguities automatically detected and surfaced as typed holes
- ✅ Users can iteratively resolve holes with clear affordances
- ✅ SMT verification runs on each draft update
- ✅ Finalized IR integrates seamlessly with forward mode
- ✅ CLI/API provide same capabilities as web UI
- ✅ Comprehensive tests cover full lifecycle
- ✅ Documentation enables independent use

---

**Document Status:** ✅ Complete (Phase 0.1)
**Next Step:** Phase 0.2 - Artifact Inventory
