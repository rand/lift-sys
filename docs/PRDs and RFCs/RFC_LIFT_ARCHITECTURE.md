# RFC: lift Technical Architecture

**RFC Number**: RFC-001
**Title**: lift Platform Technical Architecture
**Status**: Draft
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Related Documents**: PRD_LIFT.md, ADR_001_DUAL_PROVIDER_ROUTING.md

---

## Executive Summary

### Vision

lift is an AI-native development platform that bridges natural language intent and verified, production-quality code through a mathematically rigorous Intermediate Representation (IR). Unlike traditional AI coding assistants that generate code directly from prompts, lift introduces a **formal semantic layer** that enables:

- **Bidirectional translation**: Natural language ↔ IR ↔ Code
- **Formal verification**: Type checking, refinement types, SMT solver integration
- **Iterative refinement**: Typed holes with constraint propagation
- **Dual-mode operation**: Forward generation AND reverse understanding
- **LLM orchestration**: Systematic prompt engineering via DSPy + Pydantic AI

### Current Status (2025-10-21)

**Phase 2 Meta-Framework: COMPLETE**
- 6/19 architectural holes resolved (31.6%): H6, H9, H14, H1, H2, H11
- 158/158 tests passing
- Gate 2 PASSED (100%)
- ADR 001 accepted: Dual-provider routing architecture
- Production-ready forward mode: 80% compilation rate, 60% execution rate, 16s average latency

**Ready for Phase 3**: Optimization (H10 OptimizationMetrics, H8 OptimizationAPI)

### Architectural Philosophy

lift's architecture is guided by three core insights:

1. **Formal Semantics Enable AI**: A well-typed IR constrains LLM outputs to syntactically correct, semantically meaningful code
2. **Holes as Design Points**: Typed holes with constraint propagation allow the system to "design itself" through mathematical dependencies
3. **Dual Routes for Dual Needs**: Standard LLM tasks use best-quality models; constrained generation uses inference-system-aware infrastructure

### Key Innovations

1. **IR 0.9 with Dependent + Refinement Types**
   - Refinement types `{x:T | φ}` encode semantic constraints
   - 6 hole kinds (term, type, spec, entity, function, module)
   - SMT solver integration for verification

2. **XGrammar-Constrained Generation**
   - Guarantees syntactic correctness via constrained decoding
   - Routes through Modal SGLang for llguidance/aici support
   - Achieves 80% compilation rate in production

3. **Dual-Provider Routing (ADR 001)**
   - **Route 1**: Best Available (Anthropic Claude 3.5/GPT-4/Gemini) for reasoning
   - **Route 2**: Modal Inference (SGLang + XGrammar) for structured output
   - Quality vs. capability tradeoff optimized per task

4. **DSPy Systematic Orchestration**
   - 6 core signatures: PromptToIR, ExtractIntent, RefineIR, VerifyIR, GenerateCode, ExplainCode
   - MIPROv2 optimization: 60% → 85% success rate target
   - Type-driven prompt composition

5. **Meta-Framework Design by Holes**
   - 19 typed holes define system architecture
   - Constraint propagation ensures coherence
   - 7-phase execution plan with validation gates

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                      │
│  (CLI, Web UI, VS Code Extension, API Clients)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                     API & Session Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ SessionAPI   │  │ ForwardAPI   │  │ ReverseAPI   │          │
│  │ (H4)         │  │ (H5)         │  │ (H7)         │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────────────────────────────────────────┐          │
│  │ Session State Persistence (H2)                    │          │
│  │ - SQLite storage - Session snapshots - Rollback  │          │
│  └──────────────────────────────────────────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   IR Processing Core                             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ IR 0.9 Type System                                        │  │
│  │ - Dependent types - Refinement types {x:T | φ}           │  │
│  │ - 6 hole kinds - Constraint propagation                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ IR Parser    │  │ IR Validator │  │ IR Optimizer │          │
│  │ (H9)         │  │ (H11)        │  │ (H10)        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Constraint Solver Layer                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Tiered Solver Architecture                               │   │
│  │ - Tier 1: Z3 (SMT, dependent types, refinements)        │   │
│  │ - Tier 2: SAT solvers (boolean constraints)             │   │
│  │ - Tier 3: CSP solvers (search problems)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│              LLM Orchestration Layer (DSPy + Pydantic AI)       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Dual-Provider Routing (ADR 001)                          │   │
│  │ ┌─────────────────────┐  ┌─────────────────────┐        │   │
│  │ │ Route 1:            │  │ Route 2:            │        │   │
│  │ │ Best Available      │  │ Modal Inference     │        │   │
│  │ │ (Claude/GPT-4)      │  │ (SGLang+XGrammar)   │        │   │
│  │ │ - Reasoning         │  │ - Structured output │        │   │
│  │ │ - Classification    │  │ - llguidance        │        │   │
│  │ │ - Flexible format   │  │ - aici control      │        │   │
│  │ └─────────────────────┘  └─────────────────────┘        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ DSPy Signatures (6 core):                                │   │
│  │ - PromptToIR      - ExtractIntent    - RefineIR         │   │
│  │ - VerifyIR        - GenerateCode     - ExplainCode      │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Provider Adapter (H1)                                     │   │
│  │ - Route determination  - Fallback logic  - Observability │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Pipeline Execution Layer                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Forward Mode Pipeline (NL → IR → Code)                   │   │
│  │ Step 1: Intent extraction                                │   │
│  │ Step 2: IR generation (XGrammar-constrained)             │   │
│  │ Step 3: IR validation (type + refinement checking)       │   │
│  │ Step 4: SMT verification                                 │   │
│  │ Step 5: Code generation                                  │   │
│  │ Step 6: Execution validation                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Reverse Mode Pipeline (Code → IR → Understanding)        │   │
│  │ Step 1: Multi-file analysis (static + dynamic + security)│   │
│  │ Step 2: IR extraction                                    │   │
│  │ Step 3: Spec synthesis (IntentSpec + FuncSpec)           │   │
│  │ Step 4: Explanation generation                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### System Components

#### 1. IR Processing Core

**Purpose**: Parse, validate, and optimize IR 0.9 programs with dependent and refinement types.

**Key Components**:
- **IR Parser (H9)**: Parses IR 0.9 syntax into AST
- **IR Validator (H11)**: Type checking, refinement type validation, hole closure rules
- **IR Optimizer (H10)**: Metrics collection, optimization suggestions, performance analysis
- **Type System**: Dependent types `Π(x:A).B`, refinement types `{x:T | φ}`, 6 hole kinds

**Status**:
- H9 RESOLVED (Phase 2)
- H11 RESOLVED (Phase 2)
- H10 PENDING (Phase 3)

#### 2. Constraint Solver Layer

**Purpose**: Verify refinement types, resolve typed holes, check semantic constraints.

**Tiered Architecture**:
1. **Tier 1 - Z3 (SMT Solver)**:
   - Use for: Dependent types, refinement types, arithmetic constraints
   - Example: Verify `{x: Int | x > 0 && x < 100}` satisfiability
   - Integration: z3-solver Python library

2. **Tier 2 - SAT Solvers**:
   - Use for: Boolean constraints, propositional logic
   - Example: Configuration validity, feature model checking
   - Tools: PySAT, minisat

3. **Tier 3 - CSP Solvers**:
   - Use for: Search problems, combinatorial constraints
   - Example: Hole closure candidate enumeration
   - Tools: python-constraint, OR-Tools

**Decision Logic**:
```python
def select_solver(constraint: Constraint) -> Solver:
    if has_arithmetic(constraint) or has_dependent_types(constraint):
        return Z3Solver()
    elif is_boolean_only(constraint):
        return SATSolver()
    else:
        return CSPSolver()
```

#### 3. LLM Orchestration Layer

**Purpose**: Systematic LLM interaction via DSPy signatures with dual-provider routing.

**Dual-Provider Routing (ADR 001)**:

See `ADR_001_DUAL_PROVIDER_ROUTING.md` for complete specification.

**Route 1: Best Available (Anthropic/OpenAI/Google)**
- **When**: Standard LLM tasks without inference system requirements
- **Models**: Claude 3.5 Sonnet (reasoning), GPT-4 Turbo (code), Gemini 1.5 Pro (multimodal)
- **Use cases**: Intent extraction, explanation generation, refinement suggestions
- **Priority**: Quality over infrastructure

**Route 2: Modal Inference (SGLang on Modal.com)**
- **When**: Requires XGrammar, llguidance, aici, or speculative decoding
- **Models**: Llama 3.1 70B, Mistral Large (configurable)
- **Use cases**: IR generation, structured output, constrained decoding
- **Priority**: Capability over model size

**Routing Logic**:
```python
class ProviderRoute(Enum):
    BEST_AVAILABLE = "best_available"
    MODAL_INFERENCE = "modal_inference"

def determine_route(**kwargs) -> ProviderRoute:
    # Requires inference system access?
    if any([
        kwargs.get("schema") is not None,           # XGrammar
        kwargs.get("llguidance_grammar") is not None,
        kwargs.get("aici_control") is not None,
        kwargs.get("speculative_decode", False),
    ]):
        return ProviderRoute.MODAL_INFERENCE

    return ProviderRoute.BEST_AVAILABLE
```

**DSPy Signatures**:

Six core signatures define all LLM interactions:

```python
# 1. PromptToIR: NL → IR with XGrammar constraints
class PromptToIR(dspy.Signature):
    """Generate IR 0.9 from natural language, constrained by XGrammar."""
    prompt: str = dspy.InputField()
    context: str = dspy.InputField(desc="Project context, dependencies")
    ir_program: IRProgram = dspy.OutputField(desc="Valid IR 0.9 program")
    # Routes to: Modal Inference (XGrammar required)

# 2. ExtractIntent: NL → IntentSpec
class ExtractIntent(dspy.Signature):
    """Extract structured intent from natural language."""
    prompt: str = dspy.InputField()
    intent: IntentSpec = dspy.OutputField()
    # Routes to: Best Available (no schema constraint needed)

# 3. RefineIR: IR + Feedback → IR
class RefineIR(dspy.Signature):
    """Refine IR based on user feedback or validation errors."""
    current_ir: IRProgram = dspy.InputField()
    feedback: str = dspy.InputField()
    refined_ir: IRProgram = dspy.OutputField()
    # Routes to: Modal Inference (XGrammar for IR output)

# 4. VerifyIR: IR → ValidationReport
class VerifyIR(dspy.Signature):
    """Verify IR program and generate detailed error report."""
    ir_program: IRProgram = dspy.InputField()
    validation_report: ValidationReport = dspy.OutputField()
    # Routes to: Best Available (analysis task, no schema needed)

# 5. GenerateCode: IR → Code
class GenerateCode(dspy.Signature):
    """Generate target language code from verified IR."""
    ir_program: IRProgram = dspy.InputField()
    target_lang: str = dspy.InputField()
    code: str = dspy.OutputField()
    # Routes to: Best Available (code generation, no schema needed)

# 6. ExplainCode: Code → Explanation
class ExplainCode(dspy.Signature):
    """Generate natural language explanation from code/IR."""
    code: str = dspy.InputField()
    ir_program: IRProgram | None = dspy.InputField()
    explanation: str = dspy.OutputField()
    # Routes to: Best Available (reasoning task)
```

**Provider Adapter (H1)**:

Implemented in Phase 2 (277 lines). Key responsibilities:

```python
class ProviderAdapter:
    """Unified interface to dual-provider routing."""

    def __init__(
        self,
        modal_provider: ModalProvider,
        best_available_provider: BestAvailableProvider,
        config: ProviderConfig,
    ):
        self.modal = modal_provider
        self.best_available = best_available_provider
        self.config = config

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        **kwargs
    ) -> dspy.Prediction:
        route = self._determine_route(schema=schema, **kwargs)

        if route == ProviderRoute.MODAL_INFERENCE:
            return await self._call_modal(prompt, schema, **kwargs)
        else:
            return await self._call_best_available(prompt, **kwargs)
```

**MIPROv2 Optimization**:

DSPy's MIPROv2 optimizer learns from examples to improve success rates:

```python
from dspy.teleprompt import MIPROv2

# Define training set
train_examples = [
    dspy.Example(
        prompt="Create a function to validate email",
        ir_program=IRProgram(...)  # Ground truth
    ).with_inputs("prompt")
]

# Optimize signature
optimizer = MIPROv2(
    metric=ir_compilation_success,
    num_candidates=10,
    init_temperature=1.0,
)

optimized_program = optimizer.compile(
    PromptToIR(),
    trainset=train_examples,
)

# Result: 60% → 85% compilation success rate (target)
```

#### 4. Session State Persistence (H2)

**Purpose**: Enable multi-turn conversations, rollback, and iterative refinement.

**Implementation** (Phase 2, RESOLVED):

```python
@dataclass
class SessionState:
    """Complete session state snapshot."""
    session_id: str
    created_at: datetime
    updated_at: datetime

    # IR state
    current_ir: IRProgram
    ir_history: list[IRProgram]

    # Holes and constraints
    open_holes: list[TypedHole]
    hole_history: list[HoleClosureEvent]
    constraints: list[Constraint]

    # User interaction
    messages: list[Message]
    feedback: list[Feedback]

    # Validation results
    validation_results: list[ValidationResult]
    smt_proofs: list[SMTProof]

class StatePersistence:
    """SQLite-based session storage."""

    def save_snapshot(self, state: SessionState) -> None:
        """Save session snapshot with full state."""
        ...

    def load_session(self, session_id: str) -> SessionState:
        """Load latest session state."""
        ...

    def rollback(self, session_id: str, checkpoint_id: str) -> SessionState:
        """Rollback to previous checkpoint."""
        ...

    def list_sessions(self, user_id: str) -> list[SessionMetadata]:
        """List user's sessions with metadata."""
        ...
```

**Storage Schema**:

```sql
-- sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    current_ir_snapshot TEXT,  -- JSON serialized
    metadata TEXT  -- JSON: project context, settings
);

-- snapshots table (for rollback)
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    state_blob TEXT NOT NULL,  -- Full SessionState JSON
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- holes table (for querying open work)
CREATE TABLE holes (
    hole_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    hole_kind TEXT NOT NULL,  -- term, type, spec, entity, function, module
    status TEXT NOT NULL,  -- open, closed, blocked
    created_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

**WebSocket Real-Time Updates**:

For interactive refinement, session state changes broadcast to connected clients:

```python
@app.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Subscribe to session updates
    async for update in session_updates(session_id):
        await websocket.send_json({
            "type": update.type,  # hole_closed, ir_updated, validation_complete
            "data": update.data,
            "timestamp": update.timestamp.isoformat(),
        })
```

---

## Core Architectural Principles

### 1. Type-Driven Development

**Principle**: Types are not just for correctness—they drive code generation, hole closure, and user guidance.

**Application**:
- **Typed holes** have well-defined types that constrain valid closures
- **Refinement types** encode semantic constraints in the type system
- **Dependent types** allow types to depend on runtime values
- **LLM prompts** include type information to guide generation

**Example**:

```
-- Hole with refinement type
def validate_age(age: ?) -> Bool
where ? :: {x: Int | x >= 0 && x <= 150}

-- Type constraint guides LLM:
-- "Generate expression of type {x: Int | x >= 0 && x <= 150}"
-- Valid closures: user_input, parsed_int, age_from_db
-- Invalid closures: -5, 200, "twenty-five"
```

### 2. Constraint Propagation as Design

**Principle**: System architecture emerges from constraint propagation between typed holes.

**Application**:
- Each hole has **dependencies** (blocks/blocked-by relationships)
- Resolving one hole **propagates constraints** to dependent holes
- **Critical path** through hole graph defines implementation order
- **Validation gates** ensure constraint satisfaction before proceeding

**Example from Meta-Framework**:

```
H6 (NodeSignatureInterface) blocks H1 (ProviderAdapter)
  → H6 defines signature interface
  → H1 must implement interface
  → Resolving H6 first constrains H1 implementation

H1 (ProviderAdapter) blocks H10 (OptimizationMetrics)
  → H10 needs to measure provider performance
  → H1 must expose metrics hooks
  → Constraint: H10 depends on H1's instrumentation
```

Phase 2 resolution order validated this:
1. H6 resolved first (defines interface)
2. H1 resolved second (implements interface)
3. H10 next (uses H1's metrics)

### 3. Bidirectional Semantic Bridge

**Principle**: The IR is not just a compilation target—it's a bidirectional semantic bridge between human intent and machine execution.

**Forward Mode** (NL → IR → Code):
- Preserves user intent in IR IntentSpec
- Enables verification before code generation
- Supports iterative refinement via holes

**Reverse Mode** (Code → IR → Understanding):
- Extracts semantic meaning from code
- Generates specs for documentation
- Enables codebase understanding at scale

**Symmetry Benefits**:
- Same IR representation for both directions
- Same type system and validation rules
- Same hole-based refinement workflow
- Unified LLM orchestration layer

### 4. Formal Verification Before Generation

**Principle**: Never generate code from unverified IR.

**Verification Pipeline**:
1. **Syntactic validation**: IR parses correctly
2. **Type checking**: All terms have valid types
3. **Refinement checking**: All refinement predicates satisfied (via SMT)
4. **Hole checking**: No open holes remain (or all holes are explicitly marked as TODO)
5. **Constraint satisfaction**: All constraint propagation rules satisfied

**Only after all checks pass**: Generate code.

**Benefit**: Guarantees that generated code has formal semantics matching user intent.

### 5. Dual Routes for Quality and Capability

**Principle**: Use the right tool for the job—best models for reasoning, specialized infrastructure for constrained generation.

**ADR 001 Decision**:
- **Best Available Route**: Maximize quality (Claude 3.5, GPT-4) for tasks like intent extraction, explanation, refinement suggestions
- **Modal Inference Route**: Enable advanced features (XGrammar, llguidance, aici) for tasks like IR generation, structured output

**Tradeoffs**:
- Quality vs. capability
- Cost optimization (pay-per-token vs. fixed compute)
- Flexibility (provider-agnostic vs. infrastructure-dependent)
- Future-proofing (migrate tasks as APIs evolve)

**Result**: System can use cutting-edge models for reasoning while leveraging research infrastructure for constrained generation.

### 6. Optimization as a Continuous Process

**Principle**: The system continuously learns and improves from usage data.

**H10 OptimizationMetrics** (Phase 3):
- Collect metrics: Compilation rate, execution rate, latency, cost per request
- Track by route: Best Available vs. Modal Inference
- Identify patterns: Which prompts succeed? Which fail?

**H8 OptimizationAPI** (Phase 3):
- Expose optimization as API: Suggest alternative IR, identify bottlenecks
- Enable self-improvement: Use MIPROv2 to optimize DSPy signatures
- Route optimization: Automatically select best route based on task

**MIPROv2 Integration**:
- Train on success/failure examples
- Optimize prompts for each signature
- Target: 60% → 85% compilation success rate

### 7. Human-AI Collaborative Refinement

**Principle**: AI generates initial solutions; humans guide refinement through natural interaction.

**Workflow**:
1. **AI generates IR** with typed holes for uncertain parts
2. **Human reviews** IR, sees holes with type constraints
3. **AI suggests** valid closures based on type
4. **Human selects** or provides custom closure
5. **System validates** closure satisfies constraints
6. **Repeat** until all holes closed and IR verified

**Key Features**:
- **Typed holes** make uncertainty explicit
- **Constraint propagation** ensures coherence
- **Real-time updates** via WebSocket
- **Rollback support** enables experimentation

---

## Next Sections

This RFC will continue with detailed specifications for:

**Part 2** (Next):
- IR Core Architecture (IR 0.9 specification, type system, hole kinds)
- Type System Details (dependent types, refinement types, hole closure rules)
- Constraint Solver Integration (Z3 usage, SMT encoding, verification pipeline)

**Part 3**:
- LLM Orchestration Details (DSPy implementation, signature composition)
- Dual-Provider Routing Implementation (Modal setup, API integration)
- Forward & Reverse Mode Pipelines (step-by-step execution)

**Part 4**:
- Session Storage Architecture (SQLite schema, WebSocket protocol)
- API Design (REST endpoints, authentication, rate limiting)
- Security Considerations (input validation, SMT solver sandboxing)
- Testing Strategy (unit, integration, property-based testing)
- Performance & Scalability (caching, async execution, GPU optimization)
- Deployment Architecture (Modal functions, Cloudflare Workers, database hosting)

---

## Part 2: IR Core Architecture, Type System, Constraint Solver Integration

### IR 0.9 Specification

lift's Intermediate Representation (IR) is a **mathematically rigorous semantic layer** that bridges natural language intent and production code. Unlike traditional ASTs or bytecode IRs, IR 0.9 is designed for human authoring, AI generation, and formal verification.

#### Design Philosophy

**Three core insights**:

1. **Typed Holes as First-Class Citizens**: Unknowns are not errors—they're explicit design points that drive iterative refinement
2. **Bidirectional Typing + Refinements**: Combine dependent types (types depend on values) with refinement types (types + predicates) for expressive yet decidable checking
3. **Live Execution Around Holes**: Inspired by Hazel's "hole closures," the IR evaluator can run incomplete programs and gather evidence about what belongs in holes

**Influences**:
- **Hazel/Hazelnut Live** (POPL'19): Hole closures, fill-and-resume semantics
- **GHC Typed Holes**: Valid hole fits, refinement fits
- **Lean 4/Coq**: Global meta-context for metavariables/evars
- **Idris/Agda**: Interactive refinement, dependent types
- **Liquid Haskell**: SMT-backed refinement types

#### Layered Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Surface Syntax (Spec-IR in Markdown)                      │
│  - Natural language prose                                  │
│  - Fenced blocks: intent{}, entity{}, spec{}, def{}       │
│  - Human-friendly syntax                                   │
└─────────────────────┬──────────────────────────────────────┘
                      │ Parse & Elaborate
                      ↓
┌────────────────────────────────────────────────────────────┐
│  Syntactic IR (S*)                                         │
│  - SType, STerm, SDecl, SModule                           │
│  - Concrete syntax tree with spans                        │
└─────────────────────┬──────────────────────────────────────┘
                      │ Type Check & Elaborate
                      ↓
┌────────────────────────────────────────────────────────────┐
│  Semantic IR (Core)                                        │
│  - Dependent types: Π(x:A).B                              │
│  - Refinement types: {x:T | φ}                            │
│  - Typed holes: ?h:Kind [Type?] [Links] [Hints]          │
│  - Effects: Eff[T]                                         │
│  - ADTs, products, sums                                    │
└─────────────────────┬──────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┐
      ↓               ↓               ↓
┌──────────┐  ┌──────────────┐  ┌──────────────┐
│ Meta     │  │ Constraint   │  │ Evaluator    │
│ Context  │  │ Store (𝒞)    │  │ (with holes) │
│          │  │              │  │              │
│ - Holes  │  │ - Type eqs   │  │ - Closures   │
│ - Metas  │  │ - Subtyping  │  │ - Traces     │
│ - Links  │  │ - Refine φ   │  │ - Resume     │
└──────────┘  └──────┬───────┘  └──────────────┘
                     │
                     ↓
              ┌──────────────┐
              │ Solver Layer │
              │ - Z3 (SMT)   │
              │ - SAT        │
              │ - CSP        │
              └──────────────┘
```

### Type System

#### Core Grammar

**Types (T)**:
```
T ::= ι                     -- Base types (Int, Str, Bool, etc.)
    | α                     -- Type variables
    | Π(x:T₁).T₂           -- Dependent function types
    | {x:T | φ}            -- Refinement types
    | T₁ × T₂              -- Product types
    | T₁ + T₂              -- Sum types
    | μt.T                 -- Recursive types
    | Eff[T]               -- Effectful computations
    | ?α                   -- Type holes
```

**Terms (e)**:
```
e ::= x                    -- Variables
    | λx:T.e               -- Lambda abstraction
    | e₁ e₂                -- Application
    | ctor e               -- Constructor application
    | match e with ...     -- Pattern matching
    | let x = e₁ in e₂     -- Let binding
    | eff e                -- Effect invocation
    | ?h                   -- Term holes
```

**Specifications (φ)**:
```
φ ::= P(e₁,...,eₙ)        -- Predicates
    | φ₁ ∧ φ₂              -- Conjunction
    | ∀x:T. φ              -- Universal quantification
    | ∃x:T. φ              -- Existential quantification
    | e₁ = e₂              -- Equality
    | safe(e)              -- Safety predicates
    | cost ≤ κ             -- Cost bounds
    | e₁ < e₂, e₁ ≤ e₂     -- Arithmetic comparisons
```

**Declarations (d)**:
```
d ::= type t = T           -- Type definitions
    | def f : T = e        -- Function definitions
    | entity E { ... }     -- Entity declarations
    | spec S = φ           -- Specification declarations
    | intent I { ... }     -- Intent specifications
```

#### Dependent Types

**Purpose**: Types that depend on runtime values, enabling precise specifications.

**Examples**:

```specir
-- Vector with length in type
type Vec (n: Nat) (T: Type) = ...

def concat : Π(n:Nat). Π(m:Nat). Vec n T -> Vec m T -> Vec (n+m) T

-- Matrix dimensions
type Matrix (rows: Nat) (cols: Nat) = ...

def multiply :
  Π(r1:Nat). Π(c1:Nat). Π(c2:Nat).
  Matrix r1 c1 -> Matrix c1 c2 -> Matrix r1 c2
```

**Benefits**:
- **Compile-time guarantees**: Type checker proves `concat` produces correct length
- **API constraints**: Impossible to call `multiply` with incompatible matrices
- **Documentation**: Types encode invariants explicitly

**Implementation**:
- Bidirectional type checking (check mode `⊢ e ⇐ T` and synthesize mode `⊢ e ⇒ T`)
- Higher-order unification for type inference
- Normalization by evaluation for type equality

#### Refinement Types

**Purpose**: Add logical predicates to types for semantic constraints.

**Syntax**: `{x:T | φ}` where `x` has type `T` and satisfies predicate `φ`.

**Examples**:

```specir
-- Natural numbers (non-negative integers)
type Nat = {x: Int | x ≥ 0}

-- Bounded age
type Age = {x: Int | x ≥ 0 ∧ x ≤ 150}

-- Non-empty list
type NonEmptyList T = {xs: List T | length(xs) > 0}

-- Validated email
type Email = {s: Str | is_valid_email(s)}

-- Sorted list
type SortedList T = {xs: List T | ∀i,j. i < j → xs[i] ≤ xs[j]}

-- Function returning positive
def factorial : Nat -> {x: Nat | x > 0}
```

**Verification**:
```
1. Syntactic check: Parse φ as valid predicate
2. Type check: Ensure φ : Bool under Γ, x:T
3. SMT check: Query Z3 for satisfiability
4. Subtyping: {x:T | φ₁} <: {x:T | φ₂} if φ₁ ⊢ φ₂
```

**Example Verification**:

```specir
def validate_age(input: Int) : Age =
  if input >= 0 && input <= 150
    then input  -- Type checks: input satisfies Age refinement
    else panic("Invalid age")
```

Type checker generates SMT query:
```smt2
(declare-const input Int)
(assert (>= input 0))
(assert (<= input 150))
(check-sat)  ; Returns: sat (valid Age)
```

#### Typed Holes

**Philosophy**: Make unknowns explicit and type-checkable.

**Six Hole Kinds**:

```
Kind ::= term      -- Unknown expression (most common)
       | type      -- Unknown type
       | spec      -- Unknown specification predicate
       | entity    -- Unknown entity/data structure
       | function  -- Unknown function implementation
       | module    -- Unknown module/component
```

**Hole Representation**:

```python
@dataclass
class Hole:
    id: str                      # Unique identifier (e.g., "?impl", "?h1")
    kind: HoleKind               # term | type | spec | entity | function | module
    type: Type | Hole | None     # Type constraint (can be another hole!)
    links: list[HoleRef]         # Dependency edges to other holes
    hints: dict[str, Any]        # User hints, provenance, context
    provenance: str              # Where did this hole come from?

@dataclass
class HoleRef:
    hole_id: str
    relationship: str            # blocks, blocked_by, uses, implements, etc.
```

**Example: Unknown Type**:

```specir
entity "CustomerProfile":
  fields:
    id:    {x: Int | x ≥ 0}
    email: Str
    plan:  ?Plan:type            -- Type hole: what is Plan?

spec "PlanConstraints"(p: ?Plan):
  ensures: valid_plan(p)

hole ?Plan:type
```

Type checker:
1. Accepts `?Plan:type` as valid type
2. Propagates constraint: `?Plan` must support `valid_plan` predicate
3. Suggests candidates: `enum {Free, Pro, Enterprise}`, `Str`, custom ADT

**Example: Linked Holes**:

```specir
def summarize(doc: Str, audience: Str, n: Nat) :
  {bullets: List Str | length(bullets) = n ∧ ∀b. GoodFor(audience, b)} =
  ?impl:term [links={?goodFor, ?extract, ?rank}]

hole ?goodFor:function : (Str, Str) -> Bool
hole ?extract:function : Str -> List Str
hole ?rank:function : List Str -> List Str
```

Constraints:
- `?impl` USES `?goodFor`, `?extract`, `?rank`
- `?goodFor` must satisfy `GoodFor` spec
- Resolving `?goodFor` first helps constrain `?impl`

**Hole Closures (Hazel-Inspired)**:

Holes have **closures** `⟨Γ, ?h⟩` that capture their environment. This enables:

1. **Partial Evaluation**: Run program even with holes, record what values flow through
2. **Fill-and-Resume**: After filling hole, resume from last checkpoint (no full restart)
3. **Evidence Collection**: See example values, types, constraints at runtime

```specir
def process(input: Int) : Int =
  let x = input * 2 in
  let y = ?transform:term x in  -- Hole: how to transform?
  y + 10

-- Evaluator runs with input=5:
-- x = 10
-- Hole closure: ⟨{input=5, x=10}, ?transform⟩
-- Record: ?transform receives Int (value 10)
-- Continue: y = ⟨?transform 10⟩, result = ⟨?transform 10⟩ + 10
```

**Valid Fits** (GHC-Inspired):

When user hovers on hole, system suggests **valid fits**:

```
Valid fits for ?transform : Int -> Int
Ranked by type + scope + constraints:

1. (λn. n * 2)        -- In scope, right type
2. (λn. abs n)        -- Stdlib function
3. (λn. n + 1)        -- Simple arithmetic
4. user_function      -- From context
```

Ranking factors:
1. **Type compatibility**: Exact match vs. needs adaptation
2. **Scope proximity**: Local > module > stdlib > imports
3. **Constraint satisfaction**: How much of postcondition is satisfied?
4. **Usage priors**: Frequency in codebase, past selections

### IntentSpec ↔ FuncSpec Alignment

**Two Views, One Function**:

- **IntentSpec**: Human-level "what and why" (goals, roles, constraints, metrics, NL)
- **FuncSpec**: Machine-checkable "how to verify" (requires, ensures, invariants, effects, cost)

**Example**:

```specir
intent "Summarize document for audience":
  inputs:  doc: Str, audience: Str, n: Nat
  outputs: bullets: List Str
  goals:
    - Produce exactly n bullet points
    - Each bullet appropriate for audience
    - Readable at 8th grade level or below
  constraints:
    - Latency < 5s
    - Cost < $0.01 per request
  metrics:
    - readability_score ≥ 0.8
    - audience_fit_score ≥ 0.7

spec "SummarizeFuncSpec":
  requires:
    - length(doc) > 0
    - n > 0 ∧ n ≤ 10
  ensures:
    - length(bullets) = n
    - ∀b ∈ bullets. GoodFor(audience, b)
    - ∀b ∈ bullets. flesch_kincaid(b) ≤ 8.0
  effects:
    - llm_call
    - network_io
  cost: ≤ $0.01
  latency: ≤ 5000ms

def summarize(doc: Str, audience: Str, n: Nat) :
  {bullets: List Str | SummarizeFuncSpec} =
  ?impl:term
```

**Alignment Map**:

```python
@dataclass
class Alignment:
    intent_atom: IntentAtom        # Goal, constraint, metric
    func_predicate: FuncPredicate  # Requires, ensures clause
    confidence: float              # 0.0 - 1.0
    provenance: str                # How was this aligned?

alignments = [
    Alignment(
        intent_atom="Produce exactly n bullet points",
        func_predicate="length(bullets) = n",
        confidence=1.0,
        provenance="exact_match"
    ),
    Alignment(
        intent_atom="Each bullet appropriate for audience",
        func_predicate="∀b ∈ bullets. GoodFor(audience, b)",
        confidence=0.9,
        provenance="llm_extraction"
    ),
    # ...
]
```

**Drift Detection**:

System tracks when Intent and Func diverge:
- Intent goal added but no corresponding ensures clause → WARNING
- Ensures clause added but no intent goal → SUGGEST adding goal
- Metric changed but cost bound unchanged → REVIEW alignment

### Constraint Solver Integration

#### Tiered Solver Architecture

**Philosophy**: Use the right solver for each constraint class.

**Tier 1: Z3 (SMT Solver)**

**When to use**:
- Dependent types verification
- Refinement types checking
- Arithmetic constraints (linear, non-linear)
- Algebraic datatypes (ADTs)
- Array theory
- String constraints (limited)

**Examples**:

```specir
-- Refinement type
type ValidPort = {x: Int | x > 1024 ∧ x < 65536}

-- Z3 encoding:
(declare-const port Int)
(assert (> port 1024))
(assert (< port 65536))
(check-sat)  ; sat → valid refinement

-- Dependent type
def safe_divide(n: Int, d: {x: Int | x ≠ 0}) : Int = n / d

-- Z3 verifies division by zero impossible
```

**Integration**:

```python
from z3 import Int, Solver, sat

class Z3Backend:
    def check_refinement(self, type_: RefinementType) -> CheckResult:
        """Check if refinement type is satisfiable."""
        solver = Solver()

        # Encode type constraint
        var = Int(type_.var_name)
        predicate = self.encode_predicate(type_.predicate, var)
        solver.add(predicate)

        # Check satisfiability
        if solver.check() == sat:
            model = solver.model()
            return CheckResult(
                satisfiable=True,
                witness=model[var],
                explanation=f"Valid: {var} = {model[var]}"
            )
        else:
            return CheckResult(
                satisfiable=False,
                explanation=solver.unsat_core()
            )

    def check_subtyping(
        self,
        subtype: RefinementType,
        supertype: RefinementType
    ) -> bool:
        """Check if φ₁ ⊢ φ₂ (subtype ≤ supertype)."""
        solver = Solver()
        var = Int("x")

        # Assume subtype predicate
        solver.add(self.encode_predicate(subtype.predicate, var))

        # Try to refute supertype predicate
        solver.add(Not(self.encode_predicate(supertype.predicate, var)))

        # If unsat, then φ₁ ⊢ φ₂ (implication holds)
        return solver.check() == unsat
```

**Tier 2: SAT Solvers**

**When to use**:
- Boolean constraints only
- Configuration validity
- Feature model checking
- Propositional logic slices

**Example**:

```specir
-- Feature model
entity "AppConfig":
  fields:
    database: Bool
    cache: Bool
    distributed: Bool
  constraints:
    - distributed → database    -- Distributed requires database
    - distributed → cache        -- Distributed requires cache
    - ¬(cache ∧ ¬database)       -- Cache requires database
```

SAT encoding (CNF):
```
¬distributed ∨ database
¬distributed ∨ cache
¬cache ∨ database
```

**Tier 3: CSP Solvers**

**When to use**:
- Discrete domain constraints
- Combinatorial search
- Hole closure candidate enumeration
- Editor-time pruning (fast, incomplete)

**Example**:

```specir
-- Schedule optimization
entity "Task":
  fields:
    start: {x: Int | x ≥ 0 ∧ x < 24}    -- Hour of day
    duration: {x: Int | x > 0 ∧ x ≤ 4}  -- Hours

constraints:
  - ∀t1, t2. overlaps(t1, t2) → t1.priority ≠ t2.priority
```

CSP model:
- Variables: `start[1..n]`, `duration[1..n]`
- Domains: `start_i ∈ [0..23]`, `duration_i ∈ [1..4]`
- Constraints: No overlap for same priority

#### Solver Selection Logic

```python
class SolverRouter:
    def select_solver(self, constraint: Constraint) -> Solver:
        """Route constraint to appropriate solver tier."""

        # Check for arithmetic, refinements, dependent types → Z3
        if self.has_arithmetic(constraint):
            return self.z3_solver
        if self.has_refinement_types(constraint):
            return self.z3_solver
        if self.has_dependent_types(constraint):
            return self.z3_solver
        if self.has_adt_constraints(constraint):
            return self.z3_solver

        # Pure boolean → SAT
        if self.is_boolean_only(constraint):
            return self.sat_solver

        # Discrete domains, combinatorial → CSP
        if self.has_discrete_domains(constraint):
            return self.csp_solver

        # Default to Z3 (most general)
        return self.z3_solver

    def has_arithmetic(self, c: Constraint) -> bool:
        """Check if constraint uses <, ≤, +, *, etc."""
        return any(
            op in c.operators
            for op in ['<', '<=', '>', '>=', '+', '-', '*', '/', '%']
        )

    def has_refinement_types(self, c: Constraint) -> bool:
        """Check if constraint involves {x:T | φ}."""
        return isinstance(c, RefinementConstraint)

    def is_boolean_only(self, c: Constraint) -> bool:
        """Check if all variables are boolean."""
        return all(
            var.type == BoolType()
            for var in c.variables
        )
```

#### Constraint Store (𝒞)

**Purpose**: Global store for all typing, subtyping, and refinement constraints.

```python
@dataclass
class ConstraintStore:
    """Global constraint accumulator."""

    # Typing constraints
    typing_eqs: list[TypingEquality]        # T₁ ≡ T₂
    subtyping: list[SubtypingConstraint]    # T₁ <: T₂

    # Refinement predicates
    refinements: list[RefinementPredicate]  # φ must hold

    # Meta assignments
    meta_assignments: dict[str, Type]       # ?α := T
    hole_assignments: dict[str, Term]       # ?h := e

    # Blocked constraints
    blocked: dict[str, BlockedConstraint]   # Can't solve yet

    # Obligations (must be satisfied before codegen)
    obligations: list[Obligation]

    def add_typing_eq(self, t1: Type, t2: Type, ctx: Context):
        """Add T₁ ≡ T₂ constraint."""
        self.typing_eqs.append(TypingEquality(t1, t2, ctx))
        self.propagate()

    def add_refinement(self, pred: Predicate, origin: Origin):
        """Add refinement predicate φ."""
        self.refinements.append(RefinementPredicate(pred, origin))

        # Route to solver
        solver = self.solver_router.select_solver(pred)
        result = solver.check(pred)

        if not result.satisfiable:
            self.obligations.append(Obligation(
                kind="refinement_unsat",
                predicate=pred,
                origin=origin,
                explanation=result.explanation
            ))

    def propagate(self):
        """Propagate constraint solutions (unification, substitution)."""
        changed = True
        while changed:
            changed = False
            for eq in self.typing_eqs:
                if self.try_unify(eq.t1, eq.t2):
                    changed = True
            for blocked_id in list(self.blocked.keys()):
                if self.try_unblock(blocked_id):
                    changed = True
```

**Constraint Propagation Example**:

```specir
def example() : ?α =          -- Unknown return type
  let x = 42 in               -- x : Int
  let y = ?h in               -- y : ?β (unknown)
  x + y                       -- Result: Int

-- Constraint generation:
-- 1. x : Int                      (literal)
-- 2. y : ?β                        (hole)
-- 3. (+) : Int -> Int -> Int      (operator)
-- 4. x + y : Int                   (application)
-- 5. ?β ≡ Int                      (from step 3, 4)
-- 6. ?α ≡ Int                      (return type)

-- Propagation:
-- Solve: ?β := Int
-- Solve: ?α := Int
-- Update: ?h now has type Int
```

#### SMT Encoding

**Refinement Type Encoding**:

```specir
type ValidAge = {x: Int | x ≥ 0 ∧ x ≤ 150}
```

SMT-LIB encoding:
```smt2
(declare-datatype ValidAge ((mk-ValidAge (value Int))))
(define-fun valid-age? ((a ValidAge)) Bool
  (and (>= (value a) 0) (<= (value a) 150)))
```

**Postcondition Verification**:

```specir
def increment_age(age: ValidAge) : ValidAge
  requires: true
  ensures: result.value = age.value + 1 ∧ valid-age?(result) =
  mk-ValidAge(age.value + 1)
```

SMT query:
```smt2
(declare-const age ValidAge)
(assert (valid-age? age))                      ; Precondition
(define-const result ValidAge
  (mk-ValidAge (+ (value age) 1)))            ; Function body
(assert (not (valid-age? result)))             ; Negate postcondition

(check-sat)
; Expected: unsat (postcondition always holds)
; If sat: counterexample found!
```

---

## Part 3: LLM Orchestration, Dual-Provider Routing, Pipeline Architecture

### LLM Orchestration with DSPy + Pydantic AI

#### DSPy Framework Integration

**Philosophy**: Treat prompts as typed interfaces, not strings.

**Core Concepts**:
1. **Signatures**: Typed specifications for LLM calls (`InputField`, `OutputField`, docstrings)
2. **Modules**: Composable LLM programs (ChainOfThought, ReAct, etc.)
3. **Optimizers**: Automatic prompt tuning (MIPROv2, BootstrapFewShot)
4. **Evaluation**: Metrics-driven development

**Why DSPy for lift**:
- **Type-driven prompts**: IR types → DSPy signatures naturally
- **Systematic optimization**: MIPROv2 learns from examples (60% → 85% success)
- **Composability**: Build complex pipelines from simple modules
- **Observability**: Built-in tracing, metrics, evaluation

#### Six Core Signatures

**1. PromptToIR - Natural Language → IR**

**Purpose**: Generate valid IR 0.9 from natural language prompts.

**Implementation**:

```python
import dspy
from pydantic import BaseModel

class IRProgram(BaseModel):
    """Pydantic model for IR 0.9 programs."""
    decls: list[Decl]
    holes: list[Hole]
    intent_specs: list[IntentSpec]
    func_specs: list[FuncSpec]

class PromptToIR(dspy.Signature):
    """Generate syntactically correct IR 0.9 from natural language.

    Uses XGrammar-constrained generation via Modal Inference route.
    """

    # Inputs
    prompt: str = dspy.InputField(
        desc="Natural language description of desired functionality"
    )
    context: str = dspy.InputField(
        desc="Project context: existing entities, functions, types, specs"
    )
    target_lang: str = dspy.InputField(
        desc="Target language for eventual code generation",
        default="python"
    )

    # Output (XGrammar schema-constrained)
    ir_program: IRProgram = dspy.OutputField(
        desc="Valid IR 0.9 program with intent + func specs"
    )

    # Metadata
    confidence: float = dspy.OutputField(
        desc="Confidence score 0.0-1.0 for generated IR"
    )
    reasoning: str = dspy.OutputField(
        desc="Step-by-step reasoning for IR generation"
    )

class PromptToIRModule(dspy.Module):
    """Module wrapper with XGrammar routing."""

    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(PromptToIR)

    def forward(self, prompt: str, context: str, target_lang: str = "python"):
        # Route to Modal Inference (XGrammar required for IRProgram schema)
        with dspy.settings.context(
            lm=self.modal_lm,  # Modal SGLang with XGrammar
            schema=IRProgram,   # Constrain output structure
        ):
            result = self.generate(
                prompt=prompt,
                context=context,
                target_lang=target_lang
            )

        return result
```

**Routing**: **Modal Inference** (requires XGrammar for structured IR output)

**Optimization Target**: 80%+ compilation rate, 70%+ type-check pass rate

---

**2. ExtractIntent - Prompt → IntentSpec**

**Purpose**: Extract structured intent from natural language.

```python
class IntentSpec(BaseModel):
    """Structured intent specification."""
    inputs: dict[str, str]      # name → type
    outputs: dict[str, str]     # name → type
    goals: list[str]             # Natural language goals
    constraints: list[str]       # Latency, cost, quality constraints
    metrics: dict[str, float]    # Success metrics with thresholds

class ExtractIntent(dspy.Signature):
    """Extract structured intent from natural language prompt."""

    prompt: str = dspy.InputField()
    intent_spec: IntentSpec = dspy.OutputField()

class ExtractIntentModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.extract = dspy.Predict(ExtractIntent)

    def forward(self, prompt: str):
        # Route to Best Available (reasoning task, no schema constraint)
        with dspy.settings.context(lm=self.best_available_lm):
            return self.extract(prompt=prompt)
```

**Routing**: **Best Available** (reasoning task, uses Claude 3.5/GPT-4)

---

**3. RefineIR - IR + Feedback → Refined IR**

**Purpose**: Iteratively refine IR based on validation errors or user feedback.

```python
class RefineIR(dspy.Signature):
    """Refine IR based on validation errors or user feedback."""

    current_ir: IRProgram = dspy.InputField()
    feedback: str = dspy.InputField(
        desc="Validation errors, user comments, or suggested changes"
    )
    validation_errors: list[str] = dspy.InputField(
        desc="Specific type errors, refinement failures, or constraint violations"
    )

    refined_ir: IRProgram = dspy.OutputField()
    changes_summary: str = dspy.OutputField(
        desc="Human-readable summary of changes made"
    )

class RefineIRModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.refine = dspy.ChainOfThought(RefineIR)

    def forward(self, current_ir, feedback, validation_errors):
        # Route to Modal Inference (XGrammar for IRProgram output)
        with dspy.settings.context(
            lm=self.modal_lm,
            schema=IRProgram
        ):
            return self.refine(
                current_ir=current_ir,
                feedback=feedback,
                validation_errors=validation_errors
            )
```

**Routing**: **Modal Inference** (XGrammar for structured IR)

**Key Feature**: Incorporates validation errors directly, enabling type-driven refinement.

---

**4. VerifyIR - IR → ValidationReport**

**Purpose**: Analyze IR and generate detailed validation report.

```python
class ValidationReport(BaseModel):
    """Comprehensive validation report."""
    is_valid: bool
    type_errors: list[TypeError]
    refinement_errors: list[RefinementError]
    constraint_violations: list[ConstraintViolation]
    open_holes: list[Hole]
    warnings: list[str]
    suggestions: list[str]

class VerifyIR(dspy.Signature):
    """Generate detailed validation report for IR program."""

    ir_program: IRProgram = dspy.InputField()
    validation_report: ValidationReport = dspy.OutputField()
    explanation: str = dspy.OutputField(
        desc="Human-readable explanation of validation results"
    )

class VerifyIRModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.verify = dspy.Predict(VerifyIR)

    def forward(self, ir_program):
        # Route to Best Available (analysis task)
        with dspy.settings.context(lm=self.best_available_lm):
            return self.verify(ir_program=ir_program)
```

**Routing**: **Best Available** (reasoning/analysis, uses Claude 3.5)

---

**5. GenerateCode - IR → Target Code**

**Purpose**: Generate production code from verified IR.

```python
class GenerateCode(dspy.Signature):
    """Generate target language code from verified IR."""

    ir_program: IRProgram = dspy.InputField()
    target_lang: str = dspy.InputField(default="python")
    code_style: str = dspy.InputField(
        desc="PEP8, Google, Airbnb, etc.",
        default="pep8"
    )

    code: str = dspy.OutputField(desc="Generated code")
    imports: list[str] = dspy.OutputField(desc="Required imports")
    tests: str = dspy.OutputField(desc="Generated unit tests")

class GenerateCodeModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateCode)

    def forward(self, ir_program, target_lang="python", code_style="pep8"):
        # Route to Best Available (code generation, GPT-4 excels here)
        with dspy.settings.context(lm=self.best_available_lm):
            return self.generate(
                ir_program=ir_program,
                target_lang=target_lang,
                code_style=code_style
            )
```

**Routing**: **Best Available** (code generation, prefers GPT-4)

---

**6. ExplainCode - Code/IR → Natural Language**

**Purpose**: Generate explanations for code understanding (Reverse Mode).

```python
class ExplainCode(dspy.Signature):
    """Generate natural language explanation from code and/or IR."""

    code: str = dspy.InputField()
    ir_program: IRProgram | None = dspy.InputField(default=None)
    audience: str = dspy.InputField(
        desc="Target audience: beginner, intermediate, expert",
        default="intermediate"
    )

    explanation: str = dspy.OutputField(
        desc="Natural language explanation of code behavior"
    )
    key_concepts: list[str] = dspy.OutputField(
        desc="Key concepts and patterns used"
    )

class ExplainCodeModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.explain = dspy.ChainOfThought(ExplainCode)

    def forward(self, code, ir_program=None, audience="intermediate"):
        # Route to Best Available (reasoning task, Claude 3.5 excels)
        with dspy.settings.context(lm=self.best_available_lm):
            return self.explain(
                code=code,
                ir_program=ir_program,
                audience=audience
            )
```

**Routing**: **Best Available** (explanation/reasoning, uses Claude 3.5)

---

#### Signature Composition

Complex workflows compose multiple signatures:

```python
class ForwardModePipeline(dspy.Module):
    """Complete Forward Mode: NL → IR → Code."""

    def __init__(self):
        super().__init__()
        self.extract_intent = ExtractIntentModule()
        self.generate_ir = PromptToIRModule()
        self.verify_ir = VerifyIRModule()
        self.refine_ir = RefineIRModule()
        self.generate_code = GenerateCodeModule()

    def forward(self, prompt: str, context: str, max_refinements: int = 3):
        # Step 1: Extract intent
        intent = self.extract_intent(prompt=prompt)

        # Step 2: Generate initial IR
        ir_result = self.generate_ir(
            prompt=prompt,
            context=context + f"\nIntent: {intent.intent_spec}"
        )

        # Step 3-4: Verify and refine loop
        for i in range(max_refinements):
            validation = self.verify_ir(ir_program=ir_result.ir_program)

            if validation.validation_report.is_valid:
                break

            # Refine based on validation errors
            ir_result = self.refine_ir(
                current_ir=ir_result.ir_program,
                feedback=validation.explanation,
                validation_errors=validation.validation_report.type_errors
            )

        # Step 5: Generate code from verified IR
        code_result = self.generate_code(ir_program=ir_result.ir_program)

        return {
            "intent": intent.intent_spec,
            "ir_program": ir_result.ir_program,
            "validation": validation,
            "code": code_result.code,
            "imports": code_result.imports,
            "tests": code_result.tests,
        }
```

#### MIPROv2 Optimization

**Goal**: Improve success rate from 60% baseline to 85% target.

**Approach**:

```python
from dspy.teleprompt import MIPROv2

# 1. Create training set from production data
train_examples = [
    dspy.Example(
        prompt="Create a function to validate email addresses",
        context="Python project, use regex",
        ir_program=IRProgram(...),  # Ground truth
    ).with_inputs("prompt", "context"),

    dspy.Example(
        prompt="Implement binary search on sorted list",
        context="Python, return index or -1",
        ir_program=IRProgram(...),
    ).with_inputs("prompt", "context"),

    # ... 100-500 examples
]

# 2. Define success metric
def ir_compilation_success(example, prediction, trace=None):
    """Metric: Does generated IR compile and type-check?"""
    try:
        # Parse IR
        parsed = parse_ir(prediction.ir_program)

        # Type check
        type_check_result = type_checker.check(parsed)

        # Refinement check
        smt_result = smt_solver.verify_refinements(parsed)

        return (
            type_check_result.success
            and smt_result.success
        )
    except Exception:
        return False

# 3. Optimize with MIPROv2
optimizer = MIPROv2(
    metric=ir_compilation_success,
    num_candidates=10,        # Try 10 prompt variations
    init_temperature=1.0,     # Exploration vs. exploitation
    verbose=True,
)

optimized_prompt_to_ir = optimizer.compile(
    PromptToIRModule(),
    trainset=train_examples,
    num_trials=30,            # Optimization rounds
)

# 4. Results
# Before: 60% compilation success
# After:  85% compilation success (target)
```

**What MIPROv2 Learns**:
- Better instruction phrasing for IR generation
- Effective few-shot examples from training set
- Optimal reasoning chain structure
- Type hint strategies that reduce errors

### Dual-Provider Routing Implementation

#### Provider Architecture

```python
from enum import Enum
from abc import ABC, abstractmethod

class ProviderRoute(Enum):
    BEST_AVAILABLE = "best_available"
    MODAL_INFERENCE = "modal_inference"

class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        **kwargs
    ) -> dspy.Prediction:
        """Execute LLM call."""
        ...

    @abstractmethod
    def supports_schema_constraint(self) -> bool:
        """Does provider support XGrammar/structured output?"""
        ...

class BestAvailableProvider(BaseLLMProvider):
    """Routes to best quality model available."""

    def __init__(self, config: BestAvailableConfig):
        self.anthropic_client = anthropic.Anthropic(api_key=config.anthropic_key)
        self.openai_client = openai.OpenAI(api_key=config.openai_key)
        self.priority = config.priority  # ["claude-3.5", "gpt-4", "gemini-1.5"]

    async def __call__(self, prompt: str, schema: BaseModel | None = None, **kwargs):
        for model_name in self.priority:
            try:
                if "claude" in model_name:
                    return await self._call_anthropic(prompt, **kwargs)
                elif "gpt" in model_name:
                    return await self._call_openai(prompt, **kwargs)
                elif "gemini" in model_name:
                    return await self._call_google(prompt, **kwargs)
            except Exception as e:
                logging.warning(f"{model_name} failed: {e}, trying next")
                continue

        raise Exception("All Best Available providers failed")

    def supports_schema_constraint(self) -> bool:
        return False  # Standard APIs don't support XGrammar

    async def _call_anthropic(self, prompt: str, **kwargs):
        """Call Claude 3.5 Sonnet."""
        response = await self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        return dspy.Prediction(text=response.content[0].text)

class ModalInferenceProvider(BaseLLMProvider):
    """Routes to Modal SGLang with XGrammar support."""

    def __init__(self, config: ModalConfig):
        self.modal_url = config.modal_url  # e.g., https://xyz.modal.run
        self.model = config.model          # e.g., "meta-llama/Llama-3.1-70B"
        self.gpu = config.gpu              # e.g., "L40S"

    async def __call__(self, prompt: str, schema: BaseModel | None = None, **kwargs):
        """Call Modal SGLang with optional XGrammar constraint."""

        payload = {
            "prompt": prompt,
            "model": self.model,
            **kwargs
        }

        if schema:
            # Enable XGrammar structured output
            payload["xgrammar_schema"] = schema.model_json_schema()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.modal_url}/generate",
                json=payload,
                timeout=60.0
            )

        result = response.json()

        if schema:
            # Parse structured output
            parsed = schema.model_validate_json(result["text"])
            return dspy.Prediction(structured_output=parsed)
        else:
            return dspy.Prediction(text=result["text"])

    def supports_schema_constraint(self) -> bool:
        return True  # Modal SGLang supports XGrammar
```

#### ProviderAdapter (H1 Implementation)

**Status**: RESOLVED (Phase 2, 277 lines)

```python
class ProviderAdapter:
    """Unified interface with automatic routing (ADR 001)."""

    def __init__(
        self,
        modal_provider: ModalInferenceProvider,
        best_available_provider: BestAvailableProvider,
        config: ProviderConfig,
    ):
        self.modal = modal_provider
        self.best_available = best_available_provider
        self.config = config

        # Metrics collection (for H10)
        self.metrics = MetricsCollector()

    async def __call__(
        self,
        prompt: str,
        schema: BaseModel | None = None,
        llguidance_grammar: str | None = None,
        aici_control: str | None = None,
        speculative_decode: bool = False,
        **kwargs
    ) -> dspy.Prediction:
        """Execute LLM call with automatic routing."""

        # Determine route based on requirements
        route = self._determine_route(
            schema=schema,
            llguidance_grammar=llguidance_grammar,
            aici_control=aici_control,
            speculative_decode=speculative_decode,
        )

        # Record routing decision
        self.metrics.record_route(route, prompt)

        # Execute on selected route
        start_time = time.time()

        if route == ProviderRoute.MODAL_INFERENCE:
            result = await self._call_modal(
                prompt, schema, llguidance_grammar, **kwargs
            )
        else:
            result = await self._call_best_available(prompt, **kwargs)

        latency = time.time() - start_time

        # Record metrics
        self.metrics.record_call(
            route=route,
            latency=latency,
            tokens=result.usage.total_tokens if hasattr(result, 'usage') else None,
            success=True,
        )

        return result

    def _determine_route(self, **kwargs) -> ProviderRoute:
        """Implement ADR 001 routing logic."""

        # Check for inference system requirements
        requires_inference_system = any([
            kwargs.get("schema") is not None,           # XGrammar
            kwargs.get("llguidance_grammar") is not None,
            kwargs.get("aici_control") is not None,
            kwargs.get("speculative_decode", False),
            kwargs.get("custom_sampling", False),
        ])

        if requires_inference_system:
            return ProviderRoute.MODAL_INFERENCE

        # Check task-specific overrides from config
        task_type = kwargs.get("task_type")
        if task_type and task_type in self.config.task_overrides:
            return self.config.task_overrides[task_type]

        # Default: Best Available
        return ProviderRoute.BEST_AVAILABLE

    async def _call_modal(self, prompt, schema, llguidance_grammar, **kwargs):
        """Call Modal Inference route."""
        return await self.modal(
            prompt=prompt,
            schema=schema,
            llguidance_grammar=llguidance_grammar,
            **kwargs
        )

    async def _call_best_available(self, prompt, **kwargs):
        """Call Best Available route."""
        return await self.best_available(prompt=prompt, **kwargs)
```

#### Modal Deployment

**Modal App Structure**:

```python
import modal

app = modal.App("lift-inference")

# GPU configuration (ADR 001 recommendation: L40S for cost/performance)
gpu_config = modal.gpu.L40S(count=1)

# Image with SGLang + XGrammar
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "sglang[all]",
        "xgrammar",
        "torch",
        "transformers",
    )
)

@app.function(
    image=image,
    gpu=gpu_config,
    timeout=600,
    container_idle_timeout=300,
)
@modal.web_endpoint(method="POST")
async def generate(request: dict):
    """SGLang generation endpoint with XGrammar support."""
    import sglang as sgl
    from xgrammar import XGrammar

    prompt = request["prompt"]
    schema = request.get("xgrammar_schema")

    # Initialize SGLang runtime
    runtime = sgl.Runtime(
        model_path="meta-llama/Llama-3.1-70B-Instruct",
        tokenizer_path="meta-llama/Llama-3.1-70B-Instruct",
    )

    if schema:
        # XGrammar-constrained generation
        grammar = XGrammar.from_json_schema(schema)

        @sgl.function
        def constrained_gen(s, prompt):
            s += prompt
            s += sgl.gen("response", max_tokens=2048, grammar=grammar)

        result = constrained_gen.run(prompt=prompt, runtime=runtime)
        return {"text": result["response"]}
    else:
        # Standard generation
        @sgl.function
        def standard_gen(s, prompt):
            s += prompt
            s += sgl.gen("response", max_tokens=2048)

        result = standard_gen.run(prompt=prompt, runtime=runtime)
        return {"text": result["response"]}
```

### Forward Mode Pipeline

**Goal**: Natural Language → Verified IR → Production Code

#### Six-Step Pipeline

```python
class ForwardMode:
    """Complete Forward Mode pipeline with validation."""

    def __init__(self, provider_adapter: ProviderAdapter):
        self.adapter = provider_adapter

        # DSPy modules
        self.extract_intent = ExtractIntentModule()
        self.generate_ir = PromptToIRModule()
        self.refine_ir = RefineIRModule()

        # Validation components
        self.type_checker = TypeChecker()
        self.refinement_checker = RefinementChecker(z3_solver=Z3Solver())
        self.smt_verifier = SMTVerifier()

    async def execute(
        self,
        prompt: str,
        context: str,
        target_lang: str = "python",
        max_refinements: int = 3,
    ) -> ForwardModeResult:
        """Execute 6-step Forward Mode pipeline."""

        # Step 1: Extract Intent
        intent_result = await self.extract_intent(prompt=prompt)
        intent_spec = intent_result.intent_spec

        # Step 2: Generate IR (XGrammar-constrained)
        ir_result = await self.generate_ir(
            prompt=prompt,
            context=context + f"\nIntent: {intent_spec}",
            target_lang=target_lang,
        )
        ir_program = ir_result.ir_program

        # Step 3: Validate IR (Type + Refinement Checking)
        validation_result = await self._validate_ir(ir_program)

        # Step 4: Refinement Loop (if validation fails)
        refinement_count = 0
        while not validation_result.is_valid and refinement_count < max_refinements:
            refinement_count += 1

            ir_result = await self.refine_ir(
                current_ir=ir_program,
                feedback=validation_result.error_summary,
                validation_errors=validation_result.errors,
            )
            ir_program = ir_result.refined_ir

            validation_result = await self._validate_ir(ir_program)

        if not validation_result.is_valid:
            raise ValidationError(
                f"IR validation failed after {max_refinements} refinements",
                errors=validation_result.errors
            )

        # Step 5: SMT Verification
        smt_result = await self.smt_verifier.verify(ir_program)

        if not smt_result.verified:
            # Attempt one more refinement with SMT counterexample
            ir_result = await self.refine_ir(
                current_ir=ir_program,
                feedback=f"SMT verification failed: {smt_result.counterexample}",
                validation_errors=[smt_result.counterexample],
            )
            ir_program = ir_result.refined_ir

            # Re-verify
            smt_result = await self.smt_verifier.verify(ir_program)

        # Step 6: Code Generation
        code_result = await self.adapter(
            prompt=f"Generate {target_lang} code from this IR:\n{ir_program}",
            task_type="code_generation",  # Routes to Best Available (GPT-4)
        )

        return ForwardModeResult(
            intent_spec=intent_spec,
            ir_program=ir_program,
            validation=validation_result,
            smt_verification=smt_result,
            code=code_result.text,
            refinement_iterations=refinement_count,
        )

    async def _validate_ir(self, ir_program: IRProgram) -> ValidationResult:
        """Run type checking and refinement checking."""

        # Type check
        type_errors = self.type_checker.check(ir_program)

        # Refinement check (Z3)
        refinement_errors = await self.refinement_checker.check(ir_program)

        # Hole check
        open_holes = [h for h in ir_program.holes if not h.filled]

        return ValidationResult(
            is_valid=len(type_errors) == 0 and len(refinement_errors) == 0,
            type_errors=type_errors,
            refinement_errors=refinement_errors,
            open_holes=open_holes,
            error_summary=self._summarize_errors(type_errors, refinement_errors),
        )
```

**Current Performance** (Phase 2 production):
- **Compilation rate**: 80% (IR compiles successfully)
- **Execution rate**: 60% (generated code executes correctly)
- **Average latency**: 16 seconds (end-to-end)
- **Cost**: $0.0029 per request

**Phase 3 Target** (with H10 optimization):
- **Compilation rate**: 90%+
- **Execution rate**: 80%+
- **Average latency**: <10 seconds
- **Cost**: <$0.002 per request

### Reverse Mode Pipeline

**Goal**: Code → IR → Specs + Understanding

#### Four-Step Pipeline

```python
class ReverseMode:
    """Complete Reverse Mode pipeline."""

    def __init__(self, provider_adapter: ProviderAdapter):
        self.adapter = provider_adapter

        # Analysis components
        self.static_analyzer = StaticAnalyzer()
        self.dynamic_analyzer = DynamicAnalyzer()
        self.security_analyzer = SecurityAnalyzer()

    async def execute(
        self,
        code: str,
        language: str = "python",
        run_dynamic_analysis: bool = False,
    ) -> ReverseModeResult:
        """Execute 4-step Reverse Mode pipeline."""

        # Step 1: Multi-File Analysis
        analysis_result = await self._analyze_code(
            code, language, run_dynamic_analysis
        )

        # Step 2: IR Extraction
        ir_result = await self.adapter(
            prompt=f"""Extract IR 0.9 representation from this {language} code:

{code}

Include:
- Entity definitions
- Function signatures with refinement types
- Inferred specifications (pre/post conditions)

Static analysis results:
{analysis_result.static}
""",
            schema=IRProgram,  # Routes to Modal Inference (XGrammar)
        )

        ir_program = ir_result.structured_output

        # Step 3: Spec Synthesis (IntentSpec + FuncSpec)
        spec_result = await self.adapter(
            prompt=f"""Generate IntentSpec and FuncSpec from:

Code:
{code}

Extracted IR:
{ir_program}

Provide:
- IntentSpec: goals, constraints, metrics (human-readable)
- FuncSpec: requires, ensures, invariants (formal)
""",
            schema=SpecSynthesisResult,  # Routes to Modal Inference
        )

        # Step 4: Explanation Generation
        explanation_result = await self.adapter(
            prompt=f"""Explain this code for intermediate developers:

{code}

Focus on:
- High-level purpose and design
- Key algorithms and data structures
- Security and performance considerations
""",
            task_type="explanation",  # Routes to Best Available (Claude 3.5)
        )

        return ReverseModeResult(
            ir_program=ir_program,
            intent_spec=spec_result.structured_output.intent_spec,
            func_spec=spec_result.structured_output.func_spec,
            explanation=explanation_result.text,
            analysis=analysis_result,
        )

    async def _analyze_code(
        self, code: str, language: str, run_dynamic: bool
    ) -> AnalysisResult:
        """Run static, dynamic, and security analysis."""

        # Static analysis (always run)
        static_result = self.static_analyzer.analyze(code, language)

        # Dynamic analysis (optional, requires execution)
        dynamic_result = None
        if run_dynamic:
            dynamic_result = await self.dynamic_analyzer.analyze(code, language)

        # Security analysis
        security_result = self.security_analyzer.analyze(code, language)

        return AnalysisResult(
            static=static_result,
            dynamic=dynamic_result,
            security=security_result,
        )
```

**Current Capabilities** (Phase 2):
- **Multi-file analysis**: 1000+ file codebases
- **Intent fidelity**: 85%+ (reconstructed intent matches original)
- **Signature accuracy**: 90%+ (function signatures correct)
- **Security detection**: Common vulnerabilities (SQL injection, XSS, etc.)

**Target Performance** (Phase 4-5):
- **Codebase scale**: 10,000+ files
- **Intent fidelity**: 95%+
- **Full dependency analysis**: Call graphs, data flow
- **Advanced security**: Data flow taint analysis, access control verification

---

## Part 4: Session Storage, API Design, Security, Testing, Deployment

### Session Storage Architecture (H2 Implementation)

**Status**: RESOLVED (Phase 2)

#### Purpose

Enable multi-turn conversations, state rollback, and iterative refinement through persistent session management.

#### Core Design

```python
@dataclass
class SessionState:
    """Complete session state snapshot."""

    # Identity
    session_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    # IR State
    current_ir: IRProgram | None
    ir_history: list[tuple[datetime, IRProgram]]  # Timestamped history

    # Holes and Constraints
    open_holes: list[Hole]
    closed_holes: list[tuple[Hole, Term]]  # Hole + closure
    hole_events: list[HoleEvent]           # Create, update, close events
    constraint_store: ConstraintStore

    # User Interaction
    messages: list[Message]                # User + assistant messages
    feedback: list[Feedback]               # User feedback on generations
    validation_history: list[ValidationResult]

    # Verification Results
    smt_proofs: list[SMTProof]
    type_check_results: list[TypeCheckResult]

    # Metadata
    target_language: str
    project_context: str
    custom_metadata: dict[str, Any]
```

#### SQLite Storage Schema

```sql
-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Current state (denormalized for fast access)
    current_ir TEXT,  -- JSON-serialized IRProgram
    target_language TEXT,
    project_context TEXT,

    -- Metadata
    metadata TEXT,  -- JSON: custom fields

    INDEX idx_user_sessions (user_id, updated_at DESC),
    INDEX idx_updated (updated_at DESC)
);

-- Snapshots table (for rollback and history)
CREATE TABLE snapshots (
    snapshot_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Full state snapshot
    state_blob TEXT NOT NULL,  -- JSON-serialized SessionState

    -- Quick access fields
    ir_version INTEGER,
    hole_count INTEGER,
    validation_status TEXT,  -- valid, invalid, pending

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_snapshots (session_id, created_at DESC)
);

-- Holes table (queryable hole state)
CREATE TABLE holes (
    hole_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    snapshot_id TEXT,  -- Snapshot where hole was created

    -- Hole properties
    kind TEXT NOT NULL,  -- term, type, spec, entity, function, module
    type_constraint TEXT,  -- JSON
    status TEXT NOT NULL,  -- open, closed, blocked

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,

    -- Closure
    closure_term TEXT,  -- What filled this hole (if closed)

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_holes (session_id, status),
    INDEX idx_open_holes (status, created_at) WHERE status = 'open'
);

-- Messages table (conversation history)
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    role TEXT NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON: routing info, latency, tokens, etc.

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    INDEX idx_session_messages (session_id, created_at)
);

-- Validation results table
CREATE TABLE validation_results (
    validation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    is_valid BOOLEAN NOT NULL,
    type_errors TEXT,  -- JSON array
    refinement_errors TEXT,  -- JSON array
    smt_result TEXT,  -- JSON

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id) ON DELETE CASCADE,
    INDEX idx_session_validations (session_id, created_at DESC)
);
```

#### StatePersistence Implementation

```python
class StatePersistence:
    """SQLite-based session state manager."""

    def __init__(self, db_path: str = "lift_sessions.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema."""
        with open("schema.sql") as f:
            self.conn.executescript(f.read())

    async def create_session(
        self,
        user_id: str,
        target_language: str = "python",
        project_context: str = "",
    ) -> SessionState:
        """Create new session."""

        session_id = f"ses_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        state = SessionState(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            current_ir=None,
            ir_history=[],
            open_holes=[],
            closed_holes=[],
            hole_events=[],
            constraint_store=ConstraintStore(),
            messages=[],
            feedback=[],
            validation_history=[],
            smt_proofs=[],
            type_check_results=[],
            target_language=target_language,
            project_context=project_context,
            custom_metadata={},
        )

        # Persist to database
        self.conn.execute(
            """
            INSERT INTO sessions (session_id, user_id, target_language, project_context)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, user_id, target_language, project_context)
        )
        self.conn.commit()

        return state

    async def save_snapshot(self, state: SessionState) -> str:
        """Save session snapshot (for rollback)."""

        snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
        state_json = json.dumps(asdict(state), default=str)

        self.conn.execute(
            """
            INSERT INTO snapshots (
                snapshot_id, session_id, state_blob,
                ir_version, hole_count, validation_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                state.session_id,
                state_json,
                len(state.ir_history),
                len(state.open_holes),
                "valid" if state.validation_history and state.validation_history[-1].is_valid else "pending"
            )
        )

        # Update session updated_at
        self.conn.execute(
            """
            UPDATE sessions
            SET updated_at = ?, current_ir = ?
            WHERE session_id = ?
            """,
            (datetime.utcnow(), json.dumps(asdict(state.current_ir)) if state.current_ir else None, state.session_id)
        )

        self.conn.commit()

        return snapshot_id

    async def load_session(self, session_id: str) -> SessionState:
        """Load latest session state."""

        # Get latest snapshot
        cursor = self.conn.execute(
            """
            SELECT state_blob FROM snapshots
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,)
        )

        row = cursor.fetchone()
        if not row:
            raise SessionNotFoundError(session_id)

        state_dict = json.loads(row[0])
        return SessionState(**state_dict)

    async def rollback(self, session_id: str, snapshot_id: str) -> SessionState:
        """Rollback to specific snapshot."""

        cursor = self.conn.execute(
            """
            SELECT state_blob FROM snapshots
            WHERE snapshot_id = ? AND session_id = ?
            """,
            (snapshot_id, session_id)
        )

        row = cursor.fetchone()
        if not row:
            raise SnapshotNotFoundError(snapshot_id)

        state_dict = json.loads(row[0])
        return SessionState(**state_dict)

    async def list_sessions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[SessionMetadata]:
        """List user's sessions."""

        cursor = self.conn.execute(
            """
            SELECT
                session_id,
                created_at,
                updated_at,
                target_language,
                (SELECT COUNT(*) FROM snapshots WHERE snapshots.session_id = sessions.session_id) as snapshot_count
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )

        return [
            SessionMetadata(
                session_id=row[0],
                created_at=datetime.fromisoformat(row[1]),
                updated_at=datetime.fromisoformat(row[2]),
                target_language=row[3],
                snapshot_count=row[4],
            )
            for row in cursor.fetchall()
        ]
```

#### WebSocket Real-Time Updates

```python
from fastapi import WebSocket, WebSocketDisconnect

class SessionManager:
    """Manages WebSocket connections for real-time session updates."""

    def __init__(self):
        # session_id → set of WebSocket connections
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Register new WebSocket connection."""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            # Clean up empty sets
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, event: SessionEvent):
        """Broadcast event to all connections for session."""
        if session_id not in self.active_connections:
            return

        # Serialize event
        message = json.dumps({
            "type": event.type,
            "data": event.data,
            "timestamp": event.timestamp.isoformat(),
        })

        # Send to all connected clients
        dead_connections = set()
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                dead_connections.add(websocket)

        # Clean up dead connections
        for websocket in dead_connections:
            self.disconnect(websocket, session_id)

# FastAPI endpoint
session_manager = SessionManager()

@app.websocket("/ws/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for session real-time updates."""
    await session_manager.connect(websocket, session_id)

    try:
        while True:
            # Keep connection alive (client can send ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        session_manager.disconnect(websocket, session_id)
```

**Event Types**:
- `hole_created`: New hole introduced
- `hole_updated`: Hole type or constraints changed
- `hole_closed`: Hole filled with term
- `ir_updated`: IR program changed
- `validation_complete`: Validation finished
- `smt_verification_complete`: SMT verification finished

---

### API Design

#### REST API Endpoints

**Base URL**: `https://api.lift.dev/v1`

**Authentication**: Bearer token (JWT)

**Core Endpoints**:

```python
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="lift API", version="1.0.0")
security = HTTPBearer()

# ============================================================================
# Session Management
# ============================================================================

@app.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> SessionResponse:
    """Create new lift session.

    Request:
        {
            "target_language": "python",
            "project_context": "FastAPI web service with PostgreSQL"
        }

    Response:
        {
            "session_id": "ses_abc123",
            "created_at": "2025-10-21T10:00:00Z",
            "ws_url": "wss://api.lift.dev/ws/ses_abc123"
        }
    """
    user_id = await verify_token(creds.credentials)

    state = await state_persistence.create_session(
        user_id=user_id,
        target_language=request.target_language,
        project_context=request.project_context,
    )

    return SessionResponse(
        session_id=state.session_id,
        created_at=state.created_at,
        ws_url=f"wss://api.lift.dev/ws/{state.session_id}"
    )

@app.get("/sessions")
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> ListSessionsResponse:
    """List user's sessions."""
    user_id = await verify_token(creds.credentials)

    sessions = await state_persistence.list_sessions(
        user_id=user_id,
        limit=limit,
        offset=offset
    )

    return ListSessionsResponse(sessions=sessions)

@app.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> SessionState:
    """Get session state."""
    user_id = await verify_token(creds.credentials)

    state = await state_persistence.load_session(session_id)

    if state.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return state

@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> DeleteResponse:
    """Delete session."""
    user_id = await verify_token(creds.credentials)
    # Implementation details...

# ============================================================================
# Forward Mode
# ============================================================================

@app.post("/sessions/{session_id}/forward")
async def execute_forward_mode(
    session_id: str,
    request: ForwardModeRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> ForwardModeResponse:
    """Execute Forward Mode: NL → IR → Code.

    Request:
        {
            "prompt": "Create a REST API endpoint to validate emails",
            "max_refinements": 3
        }

    Response:
        {
            "intent_spec": {...},
            "ir_program": {...},
            "code": "...",
            "validation": {...},
            "refinement_iterations": 2,
            "latency_ms": 15234
        }
    """
    user_id = await verify_token(creds.credentials)

    state = await state_persistence.load_session(session_id)
    if state.user_id != user_id:
        raise HTTPException(status_code=403)

    # Execute Forward Mode pipeline
    result = await forward_mode.execute(
        prompt=request.prompt,
        context=state.project_context,
        target_lang=state.target_language,
        max_refinements=request.max_refinements or 3,
    )

    # Update session state
    state.current_ir = result.ir_program
    state.ir_history.append((datetime.utcnow(), result.ir_program))
    state.validation_history.append(result.validation)

    await state_persistence.save_snapshot(state)

    # Broadcast update via WebSocket
    await session_manager.broadcast(
        session_id,
        SessionEvent(type="forward_complete", data=result)
    )

    return ForwardModeResponse(**asdict(result))

# ============================================================================
# Reverse Mode
# ============================================================================

@app.post("/sessions/{session_id}/reverse")
async def execute_reverse_mode(
    session_id: str,
    request: ReverseModeRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> ReverseModeResponse:
    """Execute Reverse Mode: Code → IR → Specs.

    Request:
        {
            "code": "def validate_email(email: str) -> bool: ...",
            "language": "python"
        }

    Response:
        {
            "ir_program": {...},
            "intent_spec": {...},
            "func_spec": {...},
            "explanation": "...",
            "analysis": {...}
        }
    """
    # Similar structure to forward mode...

# ============================================================================
# IR Operations
# ============================================================================

@app.post("/sessions/{session_id}/ir/validate")
async def validate_ir(
    session_id: str,
    request: ValidateIRRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> ValidationResult:
    """Validate IR program."""
    # Type check + refinement check + SMT verification

@app.post("/sessions/{session_id}/ir/refine")
async def refine_ir(
    session_id: str,
    request: RefineIRRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> RefineIRResponse:
    """Refine IR based on feedback."""

# ============================================================================
# Holes
# ============================================================================

@app.get("/sessions/{session_id}/holes")
async def list_holes(
    session_id: str,
    status: str | None = None,  # open, closed, blocked
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> ListHolesResponse:
    """List holes in session."""

@app.post("/sessions/{session_id}/holes/{hole_id}/close")
async def close_hole(
    session_id: str,
    hole_id: str,
    request: CloseHoleRequest,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> CloseHoleResponse:
    """Close hole with provided term."""

@app.get("/sessions/{session_id}/holes/{hole_id}/suggestions")
async def get_hole_suggestions(
    session_id: str,
    hole_id: str,
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> HoleSuggestionsResponse:
    """Get valid fits for hole."""
```

#### Rate Limiting

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

# Initialize Redis-backed rate limiter
await FastAPILimiter.init(redis_client)

# Apply rate limits
@app.post("/sessions/{session_id}/forward")
@limiter.limit("10/minute")  # 10 Forward Mode calls per minute
async def execute_forward_mode(...):
    ...

@app.post("/sessions/{session_id}/reverse")
@limiter.limit("20/minute")  # 20 Reverse Mode calls per minute
async def execute_reverse_mode(...):
    ...
```

**Rate Limit Tiers**:
- **Free**: 10 forward/min, 20 reverse/min, 100 validations/min
- **Pro**: 50 forward/min, 100 reverse/min, 500 validations/min
- **Enterprise**: Custom limits

---

### Security Considerations

#### Input Validation

**Principle**: Validate all inputs at API boundary before processing.

```python
from pydantic import BaseModel, validator, Field

class ForwardModeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)
    max_refinements: int = Field(default=3, ge=0, le=10)

    @validator("prompt")
    def validate_prompt(cls, v):
        # Check for injection attempts
        if contains_injection_pattern(v):
            raise ValueError("Prompt contains suspicious patterns")
        return v

class CloseHoleRequest(BaseModel):
    closure_term: str = Field(..., max_length=5000)

    @validator("closure_term")
    def validate_term(cls, v):
        # Validate syntax
        try:
            parse_term(v)
        except SyntaxError as e:
            raise ValueError(f"Invalid term syntax: {e}")
        return v
```

#### SMT Solver Sandboxing

**Risk**: Z3 solver can be resource-intensive or hang on malicious inputs.

**Mitigation**:

```python
import resource
import signal
from contextlib import contextmanager

@contextmanager
def solver_timeout(seconds: int = 10):
    """Enforce timeout for solver calls."""

    def timeout_handler(signum, frame):
        raise TimeoutError("Solver exceeded time limit")

    # Set resource limits
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))  # 512MB

    # Set signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

class SafeZ3Solver:
    """Z3 solver with resource limits."""

    def check_refinement(self, refinement_type: RefinementType) -> CheckResult:
        try:
            with solver_timeout(seconds=10):
                solver = Solver()
                # ... Z3 operations
                result = solver.check()
                return CheckResult(satisfiable=(result == sat))
        except TimeoutError:
            return CheckResult(
                satisfiable=None,
                error="Solver timeout (complexity too high)"
            )
```

#### Secrets Management

```python
from google.cloud import secretmanager

class SecretsManager:
    """Centralized secrets management."""

    def __init__(self, project_id: str):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id

    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret from Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
        response = self.client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

# Usage
secrets = SecretsManager(project_id="lift-prod")
anthropic_key = secrets.get_secret("anthropic-api-key")
openai_key = secrets.get_secret("openai-api-key")
```

---

### Testing Strategy

#### Unit Tests

```python
import pytest
from lift.type_checker import TypeChecker
from lift.ir import IRProgram, RefinementType

class TestTypeChecker:
    """Unit tests for type checker."""

    def test_refinement_type_validation(self):
        """Test refinement type {x: Int | x > 0} is valid."""
        checker = TypeChecker()

        refinement = RefinementType(
            var="x",
            base_type=IntType(),
            predicate=GreaterThan(Var("x"), Literal(0))
        )

        result = checker.check_refinement(refinement)
        assert result.valid

    def test_dependent_function_type(self):
        """Test dependent function type Π(n:Nat).Vec n Int."""
        checker = TypeChecker()

        func_type = DependentFunctionType(
            param="n",
            param_type=NatType(),
            return_type=VecType(Var("n"), IntType())
        )

        result = checker.check_type(func_type)
        assert result.valid
```

#### Integration Tests

```python
@pytest.mark.asyncio
class TestForwardModePipeline:
    """Integration tests for Forward Mode."""

    async def test_simple_function_generation(self):
        """Test: NL prompt → validated IR → Python code."""

        pipeline = ForwardMode(provider_adapter=mock_adapter)

        result = await pipeline.execute(
            prompt="Create a function to validate email addresses",
            context="Python project",
            target_lang="python",
        )

        # Assertions
        assert result.intent_spec is not None
        assert result.ir_program is not None
        assert result.validation.is_valid
        assert "def" in result.code
        assert "@" in result.code  # Email validation likely uses @

    async def test_refinement_loop(self):
        """Test: Invalid IR → refinement → valid IR."""

        pipeline = ForwardMode(provider_adapter=mock_adapter)

        # Inject validation failure on first try
        mock_adapter.set_failure_count(1)

        result = await pipeline.execute(
            prompt="Function returning positive integer",
            context="",
            max_refinements=3,
        )

        assert result.refinement_iterations > 0
        assert result.validation.is_valid
```

#### Property-Based Tests

```python
from hypothesis import given, strategies as st

class TestConstraintSolver:
    """Property-based tests for constraint solver."""

    @given(st.integers(min_value=0, max_value=150))
    def test_age_refinement_accepts_valid(self, age: int):
        """Property: All ages 0-150 satisfy Age refinement."""

        solver = Z3Solver()
        age_type = RefinementType(
            var="x",
            base_type=IntType(),
            predicate=And(GreaterThanOrEqual(Var("x"), Literal(0)),
                          LessThanOrEqual(Var("x"), Literal(150)))
        )

        result = solver.check_satisfiable(age_type, {"x": age})
        assert result.satisfiable

    @given(st.one_of(st.integers(max_value=-1), st.integers(min_value=151)))
    def test_age_refinement_rejects_invalid(self, age: int):
        """Property: Ages outside 0-150 violate Age refinement."""

        solver = Z3Solver()
        # Same refinement as above

        result = solver.check_satisfiable(age_type, {"x": age})
        assert not result.satisfiable
```

#### End-to-End Tests

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestEndToEnd:
    """End-to-end tests with real LLM calls."""

    async def test_full_forward_mode_with_real_llms(self):
        """E2E: Real prompt → Real LLM → Verified code."""

        # Use real providers (not mocks)
        adapter = ProviderAdapter(
            modal_provider=ModalInferenceProvider(config=test_modal_config),
            best_available_provider=BestAvailableProvider(config=test_best_available_config),
            config=test_provider_config,
        )

        pipeline = ForwardMode(provider_adapter=adapter)

        result = await pipeline.execute(
            prompt="Create a function to calculate Fibonacci numbers recursively",
            context="Python 3.11 project",
            target_lang="python",
        )

        # Verify IR
        assert result.ir_program is not None
        assert result.validation.is_valid

        # Verify code executes correctly
        exec_globals = {}
        exec(result.code, exec_globals)
        fib = exec_globals["fibonacci"]  # Assume function named "fibonacci"

        assert fib(0) == 0
        assert fib(1) == 1
        assert fib(10) == 55
```

---

### Performance & Scalability

#### Caching Strategy

```python
from functools import lru_cache
import redis

# In-memory cache for hot paths
@lru_cache(maxsize=1000)
def parse_ir(ir_text: str) -> IRProgram:
    """Cache parsed IR programs."""
    return IRParser().parse(ir_text)

# Redis cache for LLM responses
class LLMCache:
    """Redis-backed LLM response cache."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour

    def get(self, prompt: str, schema: str | None) -> str | None:
        """Get cached response."""
        key = self._make_key(prompt, schema)
        return self.redis.get(key)

    def set(self, prompt: str, schema: str | None, response: str):
        """Cache response."""
        key = self._make_key(prompt, schema)
        self.redis.setex(key, self.ttl, response)

    def _make_key(self, prompt: str, schema: str | None) -> str:
        """Generate cache key."""
        import hashlib
        content = f"{prompt}::{schema or ''}"
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"
```

#### Async Execution

```python
import asyncio

class ParallelForwardMode:
    """Forward Mode with parallel validation steps."""

    async def execute(self, prompt: str, context: str) -> ForwardModeResult:
        # Generate IR
        ir_result = await self.generate_ir(prompt, context)

        # Run validation steps in parallel
        type_check_task = asyncio.create_task(
            self.type_checker.check(ir_result.ir_program)
        )
        refinement_check_task = asyncio.create_task(
            self.refinement_checker.check(ir_result.ir_program)
        )
        smt_verification_task = asyncio.create_task(
            self.smt_verifier.verify(ir_result.ir_program)
        )

        # Wait for all validations
        type_errors, refinement_errors, smt_result = await asyncio.gather(
            type_check_task,
            refinement_check_task,
            smt_verification_task,
        )

        # Continue with code generation...
```

#### GPU Optimization (Modal)

```python
# Modal deployment with GPU optimization
@app.function(
    gpu=modal.gpu.L40S(count=1),
    image=modal.Image.debian_slim().pip_install("sglang[all]", "xgrammar"),
    timeout=300,
    concurrency_limit=10,  # Max 10 concurrent requests
    container_idle_timeout=120,  # Keep warm for 2 min
)
@modal.web_endpoint(method="POST")
async def generate_ir(request: dict):
    """Optimized IR generation with batching."""

    # Batch multiple requests for efficiency
    if len(request_batch) > 1:
        results = await batch_generate(request_batch)
        return results
    else:
        return await single_generate(request)
```

---

### Deployment Architecture

#### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare Workers                        │
│                  (API Gateway + Edge Caching)                │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (Render/Fly.io)             │
│  - REST API endpoints                                        │
│  - WebSocket server                                          │
│  - Session management                                        │
│  - Forward/Reverse Mode orchestration                        │
└──────┬───────────────────────┬──────────────────────────────┘
       │                       │
       ↓                       ↓
┌──────────────┐      ┌───────────────────┐
│ Modal.com    │      │ Best Available    │
│ (SGLang +    │      │ (Anthropic/OpenAI)│
│  XGrammar)   │      │                   │
└──────────────┘      └───────────────────┘
       │
       ↓
┌──────────────────────────────────────────┐
│          Data Layer                       │
│  ┌────────────┐  ┌────────────────────┐ │
│  │ PostgreSQL │  │ Redis              │ │
│  │ (sessions, │  │ (cache, rate limit)│ │
│  │  snapshots)│  │                    │ │
│  └────────────┘  └────────────────────┘ │
└──────────────────────────────────────────┘
```

#### Deployment Steps

1. **Modal Deployment**:
```bash
modal deploy lift_inference.py
modal app list  # Get endpoint URL
```

2. **FastAPI Backend** (Render):
```bash
# render.yaml
services:
  - type: web
    name: lift-api
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: lift-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: lift-redis
          property: connectionString
```

3. **Cloudflare Workers** (Edge):
```typescript
// worker.ts
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Edge caching for static responses
    const cache = caches.default;
    const cacheKey = new Request(request.url, request);
    let response = await cache.match(cacheKey);

    if (!response) {
      // Forward to FastAPI backend
      response = await fetch(env.BACKEND_URL + request.url, {
        method: request.method,
        headers: request.headers,
        body: request.body,
      });

      // Cache successful responses
      if (response.ok) {
        response = new Response(response.body, response);
        response.headers.set("Cache-Control", "s-maxage=300");
        await cache.put(cacheKey, response.clone());
      }
    }

    return response;
  }
};
```

---

### Monitoring & Observability

#### OpenTelemetry Integration

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to observability backend (e.g., Honeycomb, Datadog)
otlp_exporter = OTLPSpanExporter(endpoint="https://api.honeycomb.io")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument Forward Mode
class ForwardMode:
    async def execute(self, prompt: str, context: str) -> ForwardModeResult:
        with tracer.start_as_current_span("forward_mode.execute") as span:
            span.set_attribute("prompt_length", len(prompt))
            span.set_attribute("target_lang", self.target_lang)

            # Step 1: Extract Intent
            with tracer.start_as_current_span("extract_intent"):
                intent_result = await self.extract_intent(prompt=prompt)
                span.set_attribute("intent.goals_count", len(intent_result.intent_spec.goals))

            # Step 2: Generate IR
            with tracer.start_as_current_span("generate_ir"):
                ir_result = await self.generate_ir(prompt, context)
                span.set_attribute("ir.hole_count", len(ir_result.ir_program.holes))

            # ... continue with tracing
```

#### Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
forward_mode_requests = Counter(
    "forward_mode_requests_total",
    "Total Forward Mode requests",
    ["status"]
)

forward_mode_latency = Histogram(
    "forward_mode_latency_seconds",
    "Forward Mode latency",
    buckets=[1, 5, 10, 30, 60]
)

compilation_rate = Gauge(
    "ir_compilation_rate",
    "IR compilation success rate"
)

# Instrument
async def execute_forward_mode(...):
    start = time.time()

    try:
        result = await forward_mode.execute(...)

        forward_mode_requests.labels(status="success").inc()
        compilation_rate.set(result.validation.compilation_rate)

        return result
    except Exception as e:
        forward_mode_requests.labels(status="error").inc()
        raise
    finally:
        forward_mode_latency.observe(time.time() - start)
```

---

## Conclusion

### Summary

lift's technical architecture delivers on its vision of **mathematically rigorous, AI-native software development** through:

1. **IR 0.9 Core**: Dependent + refinement types with typed holes enable formal verification and iterative refinement
2. **Dual-Provider Routing**: Best-quality models for reasoning (Claude 3.5, GPT-4), specialized infrastructure for constrained generation (Modal SGLang + XGrammar)
3. **DSPy Orchestration**: Systematic prompt engineering with MIPROv2 optimization (60% → 85% target success rate)
4. **Constraint Solving**: Tiered architecture (Z3/SAT/CSP) for verification and validation
5. **Bidirectional Translation**: Forward Mode (NL → IR → Code) and Reverse Mode (Code → IR → Understanding)
6. **Session Persistence**: SQLite-backed state management with WebSocket real-time updates
7. **Production-Ready**: Comprehensive API, security, testing, and deployment infrastructure

### Current Status (2025-10-21)

**Phase 2 Meta-Framework: COMPLETE**
- 6/19 holes resolved (31.6%): H6, H9, H14, H1, H2, H11
- 158/158 tests passing
- Gate 2 PASSED (100%)
- ADR 001 accepted: Dual-provider routing architecture
- Production metrics: 80% compilation, 60% execution, 16s latency, $0.0029/request

**Ready for Phase 3**: H10 OptimizationMetrics, H8 OptimizationAPI

### Next Steps

**Phase 3** (Q1 2025):
- H10: OptimizationMetrics (route tracking, cost analysis, pattern identification)
- H8: OptimizationAPI (optimization suggestions, MIPROv2 integration)
- Target: 90% compilation, 80% execution, <10s latency

**Phase 4-7** (Q2-Q4 2025):
- Multi-file projects, code understanding, interactive IDE, codebase adoption
- Full IR 0.9 adoption across all workflows
- Enterprise features: SSO, audit logs, custom deployment

### Key Innovations

1. **Meta-Framework Design by Holes**: System architecture emerges from constraint propagation between 19 typed holes
2. **XGrammar-Constrained Generation**: Syntactic correctness guarantees for LLM outputs
3. **Hole Closures**: Hazel-inspired partial evaluation enables live previews and iterative refinement
4. **IntentSpec ↔ FuncSpec Alignment**: Bridges human goals and machine-checkable contracts
5. **Systematic LLM Orchestration**: DSPy signatures with automatic optimization replace brittle prompt engineering

### References

**Core Technologies**:
- IR Design: Hazel (POPL'19), GHC Typed Holes, Lean 4, Liquid Haskell
- LLM Orchestration: DSPy, Pydantic AI, MIPROv2
- Constraint Solving: Z3, SMT-LIB 2.6, PySAT
- Infrastructure: Modal.com, SGLang, XGrammar

**Related Documents**:
- PRD_LIFT.md: Product vision and requirements
- ADR_001_DUAL_PROVIDER_ROUTING.md: Routing strategy decision
- HOLE_INVENTORY.md: Complete hole catalog
- INTEGRATED_STRATEGY.md: 20-month IR + 14-month DSPy plans

---

**Document Status**: Complete
**Version**: 1.0
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Review Status**: Draft (awaiting architecture review)
