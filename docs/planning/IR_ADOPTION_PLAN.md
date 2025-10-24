# Lift-Sys IR 0.9 Adoption Plan

**Date**: 2025-10-23 (Updated)
**Status**: Month 4 of 20 (DSPy meta-framework in progress, IR 0.9 Phase 1 upcoming)
**Related Documents**:
- [IR Specification v0.9](../IR_SPECIFICATION.md)
- [DSPy Migration Plan](DSPY_MIGRATION_PLAN.md)
- [DSPy Pydantic AI Architecture Proposal](DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md)
- [Semantic IR Roadmap](../../SEMANTIC_IR_ROADMAP.md)
- [Session State (Meta-Framework)](SESSION_STATE.md)

---

## Current Status (2025-10-23)

### Meta-Framework Progress (Prerequisite for IR 0.9)

**DSPy + Pydantic AI Architecture**:
- ✅ Phase 1, 2, 3, 7 COMPLETE (10/19 holes = 52.6%)
- ✅ Critical path 100% complete (H6 → H1 → H10 → H8 → H17)
- ✅ 277/278 tests passing across all phases
- ✅ ProviderAdapter (H1), StatePersistence (H2), ExecutionHistory (H11) - All ready for IR 0.9 features
- ✅ Dual-provider routing architecture (ADR 001)

**Current IR Foundation** (compatible with IR 0.9 migration):
- Basic typed holes (HoleKind: INTENT | SIGNATURE | EFFECT | ASSERTION)
- Pydantic models (immutable, JSON serializable)
- Supabase storage with migrations
- XGrammar-constrained generation
- Multi-language code generation (TypeScript, Rust, Go, Java complete)

**Ready to Start**: IR 0.9 Phase 1 (types & refinements) can begin alongside remaining meta-framework phases (4, 5, 6).

---

## Executive Summary

This plan details the adoption of the new IR 0.9 specification (from `/docs/IR_SPECIFICATION.md`) into the lift-sys codebase. The new IR is dramatically more ambitious than the current implementation, introducing:

- **Typed holes** (terms, types, specs, entities, functions, modules) - PARTIAL (4 kinds exist)
- **Dependent types** with refinements - PLANNED (Phase 1)
- **IntentSpec ↔ FuncSpec alignment** with drift detection - PLANNED (Phase 5)
- **Solver integration** (CSP/SAT/SMT) for verification - PLANNED (Phase 2)
- **Hole closures** for partial evaluation - PLANNED (Phase 3)
- **Human-friendly surface syntax** (Spec-IR in Markdown) - PLANNED (Phase 4)
- **Provenance tracking** and intent ledger - PARTIAL (H11 ExecutionHistory provides foundation)
- **Safety/deployability manifests** - PLANNED (Phase 6)

**Timeline**: 20 months total (Month 4 of 20 as of 2025-10-23)
**Complexity**: High - This is a fundamental architectural evolution
**Risk**: Medium - Large scope, but **meta-framework provides systematic migration path**
**Dependencies**: Meta-framework Phases 4-6 (in progress), multi-language generators (complete)

---

## 0. Current State Analysis

### What We Have (October 2025 - Updated 2025-10-23)

**Current IR** (`lift_sys/ir/models.py`):
```python
IntermediateRepresentation:
  - intent: IntentClause (summary, rationale, holes)
  - signature: SigClause (name, params, returns, holes)
  - effects: List[EffectClause]
  - assertions: List[AssertClause]
  - metadata: Metadata
  - constraints: Dict[str, Any]
```

**TypedHole** (basic):
```python
TypedHole:
  - identifier: str
  - type_hint: str
  - description: str
  - constraints: Dict[str, Any]
  - kind: HoleKind (INTENT|SIGNATURE|EFFECT|ASSERTION)
```

**Capabilities** (Updated 2025-10-23):
- ✅ Basic IR generation (NL → IR) via ModalProvider
- ✅ **Multi-language code generation** (TypeScript, Rust, Go, Java) with Python/Zig/C++ next
- ✅ Simple typed holes (4 kinds, extensible to 6)
- ✅ XGrammar-constrained generation (schema-validated JSON)
- ✅ Modal deployment with Qwen2.5-Coder-32B-Instruct
- ✅ Supabase storage with migrations (9 migrations complete)
- ✅ **DSPy ProviderAdapter** (H1) - Ready for declarative signatures
- ✅ **StatePersistence** (H2) - Ready for graph state serialization
- ✅ **ExecutionHistory** (H11) - Provenance tracking foundation
- ✅ **OptimizationMetrics** (H10) - IR/code quality scoring
- ✅ **Dual-provider routing** (ADR 001) - Best Available + Modal Inference
- ✅ Fixture-based testing (71x speedup, real LLM validation)
- ✅ **TokDrift robustness framework** (Phase 1 complete)

**Gaps vs IR 0.9** (Prioritized by Phase):
- ❌ **Phase 1**: No dependent types, no refinement types `{x:T | φ}` (3 months)
- ❌ **Phase 2**: No solver integration (CSP/SAT/SMT) (3 months)
- ❌ **Phase 3**: No hole closures / partial evaluation (4 months)
- ❌ **Phase 4**: No surface syntax (Spec-IR) (4 months)
- ❌ **Phase 5**: No IntentSpec ↔ FuncSpec alignment map (4 months)
- ❌ **Phase 6**: No safety manifests / deployability gates (2 months)

---

## 1. Phased Adoption Strategy

### Philosophy: Incremental Enhancement

Rather than a "big bang" rewrite, we adopt IR 0.9 features incrementally **in parallel with meta-framework completion**:

**Timeline** (20 months total, Month 4 of 20 as of 2025-10-23):

| Phase | Duration | Timeline | Dependencies | Status |
|-------|----------|----------|--------------|--------|
| **Phase 1** | 3 months | Months 4-6 (Nov 2025 - Jan 2026) | Meta-framework H2 (✅ done) | Ready to start |
| **Phase 2** | 3 months | Months 7-9 (Feb - Apr 2026) | Phase 1, formal skills (Z3/SAT) | Planned |
| **Phase 3** | 4 months | Months 10-13 (May - Aug 2026) | Phase 2, meta-framework H4/H5 | Planned |
| **Phase 4** | 4 months | Months 14-17 (Sep - Dec 2026) | Phase 3 | Planned |
| **Phase 5** | 4 months | Months 18-21 (Jan - Apr 2027) | Phase 4 | Planned |
| **Phase 6** | 2 months | Months 22-23 (May - Jun 2027) | Phase 5 | Planned |

**Phases**:
1. **Phase 1 (Months 4-6)**: Core Types & Refinements
2. **Phase 2 (Months 7-9)**: Solver Integration (SMT first)
3. **Phase 3 (Months 10-13)**: Hole Closures & Partial Evaluation
4. **Phase 4 (Months 14-17)**: Surface Syntax & Parsing
5. **Phase 5 (Months 18-21)**: IntentSpec/FuncSpec Alignment & Provenance
6. **Phase 6 (Months 22-23)**: Safety Manifests & Production Hardening

**Total**: ~20 months (18-24 month range with parallel work)

**Current Focus** (Month 4):
- Complete meta-framework Phases 4-6 (H3, H4, H5, H7, H13, H15, H16, H18, H19)
- Expand multi-language generators (Python, Zig, C++ high priority)
- TokDrift Phase 2 (robustness benchmarking)
- **IR 0.9 Phase 1 can start concurrently** (types & refinements are independent)

---

## 2. Phase 1: Core Types & Refinements (Months 1-3)

### Goal
Extend IR data models to support:
- Dependent types (`Π(x:T).U`)
- Refinement types (`{x:T | φ}`)
- Enhanced hole system (type holes, spec holes, entity holes, module holes)
- ADTs and effect types

### Tasks

#### 2.1 Type System Foundation (Week 1-2)
**Deliverable**: `lift_sys/ir/types.py`

```python
# New type system
@dataclass(frozen=True)
class Type:
    """Base type in IR 0.9"""
    pass

@dataclass(frozen=True)
class BaseType(Type):
    """Primitive types: int, str, bool, etc."""
    name: str

@dataclass(frozen=True)
class DependentType(Type):
    """Dependent function type: Π(x:T).U"""
    param_name: str
    param_type: Type
    return_type: Type  # Can reference param_name

@dataclass(frozen=True)
class RefinementType(Type):
    """Refinement type: {x:T | φ}"""
    base_type: Type
    var_name: str
    predicate: Predicate  # SMT-compatible predicate

@dataclass(frozen=True)
class ProductType(Type):
    """Product/tuple type: T × U"""
    components: tuple[Type, ...]

@dataclass(frozen=True)
class SumType(Type):
    """Sum/union type: T + U"""
    variants: tuple[Type, ...]

@dataclass(frozen=True)
class EffectType(Type):
    """Effect type: Eff[T]"""
    inner: Type
    effects: frozenset[str]  # Effect labels

@dataclass(frozen=True)
class TypeHole(Type):
    """Type-level hole: ?α"""
    identifier: str
    constraints: Dict[str, Any]
```

**Acceptance**:
- All types immutable (frozen dataclasses)
- JSON serialization/deserialization
- 100% test coverage
- Type equality and substitution operations

#### 2.2 Predicate System (Week 3-4)
**Deliverable**: `lift_sys/ir/predicates.py`

```python
@dataclass(frozen=True)
class Predicate:
    """Predicate for refinements and specs"""
    pass

@dataclass(frozen=True)
class BoolLiteral(Predicate):
    value: bool

@dataclass(frozen=True)
class VarRef(Predicate):
    name: str

@dataclass(frozen=True)
class BinaryOp(Predicate):
    op: str  # '=', '<', '>', '<=', '>=', '∧', '∨'
    left: Predicate
    right: Predicate

@dataclass(frozen=True)
class Quantified(Predicate):
    quantifier: str  # '∀', '∃'
    var_name: str
    var_type: Type
    body: Predicate

@dataclass(frozen=True)
class PredicateApplication(Predicate):
    """Apply named spec: GoodFor(A, b)"""
    spec_name: str
    args: tuple[Predicate, ...]
```

**Acceptance**:
- Predicate AST with traversal
- Pretty-printing
- Variable substitution
- Free variable collection

#### 2.3 Enhanced Hole System (Week 5-6)
**Deliverable**: Update `lift_sys/ir/models.py`

```python
@dataclass(frozen=True)
class Hole:
    """Unified hole type (IR 0.9 §2.3)"""
    identifier: str
    kind: HoleKind  # term|type|spec|entity|function|module
    type_annotation: Type | None  # Can be TypeHole itself
    links: frozenset[str]  # Dependency edges
    hints: Dict[str, Any]
    provenance: str
    closure_env: Dict[str, Any] | None = None  # For hole closures (Phase 3)

    @property
    def is_unknown_type(self) -> bool:
        """Check if type is also unknown (?h:term where Type=?α)"""
        return isinstance(self.type_annotation, TypeHole)

class HoleKind(Enum):
    TERM = "term"
    TYPE = "type"
    SPEC = "spec"
    ENTITY = "entity"
    FUNCTION = "function"
    MODULE = "module"
```

**Acceptance**:
- Holes can reference type holes
- Hole linking (dependency graph)
- Serialization preserves all metadata

#### 2.4 FuncSpec Enhancement (Week 7-8)
**Deliverable**: `lift_sys/ir/specs.py`

```python
@dataclass
class FuncSpec:
    """Formal contract specification (IR 0.9 §2.5)"""
    requires: list[Predicate]  # Preconditions
    ensures: list[Predicate]   # Postconditions
    invariants: list[Predicate]
    measure: Predicate | None  # Termination measure
    cost: CostSpec | None
    effects: frozenset[str]

@dataclass
class IntentSpec:
    """High-level intentional spec (IR 0.9 §2.5)"""
    summary: str
    roles: list[str]
    goals: list[str]
    constraints: list[str]
    metrics: Dict[str, Any]
    notes: str

@dataclass
class AlignmentMap:
    """Maps IntentSpec atoms to FuncSpec predicates"""
    mappings: Dict[str, str]  # intent_atom_id -> func_predicate_id
    confidence: Dict[str, float]
    last_verified: datetime
    drift_detected: bool
```

**Acceptance**:
- IntentSpec and FuncSpec coexist
- AlignmentMap tracks relationships
- Drift detection API

#### 2.5 Update Core IR (Week 9-10)
**Deliverable**: Refactor `IntermediateRepresentation`

```python
@dataclass
class IntermediateRepresentation:
    """Enhanced IR with IR 0.9 features"""
    intent_spec: IntentSpec
    func_spec: FuncSpec
    signature: Signature  # Enhanced with Type system
    holes: list[Hole]  # All holes in one place
    alignment: AlignmentMap
    metadata: Metadata

    # Backward compatibility (deprecated)
    @property
    def intent(self) -> IntentClause:
        """Legacy accessor"""
        return self._to_legacy_intent()
```

**Acceptance**:
- Backward compatibility with existing code
- All new features accessible
- Migration path for old IR

#### 2.6 Database Schema Updates (Week 11-12)
**Deliverable**: Supabase migration

```sql
-- migrations/007_ir_v09_types.sql

CREATE TYPE hole_kind AS ENUM (
  'term', 'type', 'spec', 'entity', 'function', 'module'
);

CREATE TABLE holes (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  identifier TEXT NOT NULL,
  kind hole_kind NOT NULL,
  type_annotation JSONB,  -- Serialized Type
  links TEXT[],
  hints JSONB,
  provenance TEXT,
  closure_env JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE func_specs (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  requires JSONB[],  -- Predicates
  ensures JSONB[],
  invariants JSONB[],
  measure JSONB,
  cost JSONB,
  effects TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE intent_specs (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  summary TEXT,
  roles TEXT[],
  goals TEXT[],
  constraints TEXT[],
  metrics JSONB,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alignment_maps (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES sessions(id),
  intent_spec_id UUID REFERENCES intent_specs(id),
  func_spec_id UUID REFERENCES func_specs(id),
  mappings JSONB,
  confidence JSONB,
  last_verified TIMESTAMPTZ,
  drift_detected BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Acceptance**:
- Migration runs cleanly
- Old data preserved
- New IR features storable

### Phase 1 Success Metrics
- ✅ Type system can represent IR 0.9 types
- ✅ Predicates serialize to/from JSON
- ✅ Holes support all 6 kinds + unknown types
- ✅ IntentSpec/FuncSpec coexist with alignment
- ✅ Database stores new IR structures
- ✅ 95%+ backward compatibility

**Phase 1 Estimated Effort**: 3 months (1 senior eng + 1 mid-level eng)

---

## 3. Phase 2: Solver Integration (Months 4-6)

### Goal
Integrate SMT/SAT/CSP solvers for:
- Type checking with refinements
- Constraint validation
- Counterexample generation
- Valid-fit suggestions

### Tasks

#### 3.1 SMT Backend (Week 1-4)
**Deliverable**: `lift_sys/solvers/smt.py`

```python
class SMTEncoder:
    """Encode IR predicates to SMT-LIB 2.6"""

    def encode_type(self, ty: Type) -> str:
        """Convert Type to SMT sort"""
        if isinstance(ty, RefinementType):
            return self._encode_refinement(ty)
        # ...

    def encode_predicate(self, pred: Predicate) -> str:
        """Convert Predicate to SMT-LIB assertion"""
        # ...

    def check_satisfiability(
        self,
        predicates: list[Predicate],
        context: Dict[str, Type]
    ) -> SMTResult:
        """Check if predicates are satisfiable"""
        # ...

class Z3Solver:
    """Z3-based SMT solver integration"""

    def check(self, encoded: str) -> SMTResult:
        """Run Z3 solver"""
        # ...

    def get_model(self) -> Dict[str, Any]:
        """Extract satisfying assignment"""
        # ...

    def get_unsat_core(self) -> list[str]:
        """Get minimal unsatisfiable subset"""
        # ...
```

**Integration Points**:
- Validation pipeline: Check refinements when creating IR
- Code generation: Verify pre/post conditions before codegen
- Hole suggestions: Use solver models as candidate fills

**Acceptance**:
- Encode basic refinements: `{x:Int | x ≥ 0}`
- Detect unsatisfiable constraints
- Generate counterexamples
- <5s solver time for typical queries

#### 3.2 SAT Backend (Week 5-6)
**Deliverable**: `lift_sys/solvers/sat.py`

```python
class SATEncoder:
    """Encode boolean constraints to CNF"""

    def encode_boolean_slice(self, pred: Predicate) -> CNF:
        """Extract boolean structure"""
        # ...

class CDCLSolver:
    """CDCL-based SAT solver (via external tool)"""

    def solve(self, cnf: CNF) -> SATResult:
        """Run SAT solver"""
        # ...
```

**Use Case**: Fast boolean checks before expensive SMT

**Acceptance**:
- Boolean predicates convert to CNF
- <100ms for typical queries

#### 3.3 CSP Backend (Week 7-8)
**Deliverable**: `lift_sys/solvers/csp.py`

```python
class CSPSolver:
    """Constraint Satisfaction Problem solver"""

    def create_domain(self, var: str, values: set) -> Domain:
        """Create finite domain"""
        # ...

    def add_constraint(self, constraint: Constraint) -> None:
        """Add constraint to CSP"""
        # ...

    def solve(self) -> CSPSolution:
        """Find solution via backtracking + propagation"""
        # ...
```

**Use Case**: Editor-time pruning for hole suggestions

**Acceptance**:
- Enumerate small domains (<1000 values)
- Propagate constraints efficiently
- <1s for typical problems

#### 3.4 Validation Pipeline (Week 9-10)
**Deliverable**: Update `lift_sys/validation/`

```python
class IRValidator:
    """Validate IR with solver checks"""

    def __init__(self, smt: SMTEncoder, sat: SATEncoder, csp: CSPSolver):
        self.smt = smt
        self.sat = sat
        self.csp = csp

    def validate(self, ir: IntermediateRepresentation) -> ValidationResult:
        """Multi-stage validation"""
        # 1. Type check
        type_result = self._check_types(ir)
        if not type_result.ok:
            return type_result

        # 2. SAT check (fast)
        sat_result = self._check_sat(ir.func_spec.requires + ir.func_spec.ensures)
        if not sat_result.ok:
            return sat_result

        # 3. SMT check (slower, more powerful)
        smt_result = self._check_smt(ir)
        return smt_result
```

**Acceptance**:
- Catches unsatisfiable specs
- Reports counterexamples with source spans
- Tiered approach (CSP → SAT → SMT) for performance

#### 3.5 Counterexample Generation (Week 11-12)
**Deliverable**: `lift_sys/solvers/counterexample.py`

```python
class CounterexampleGenerator:
    """Generate counterexamples from solver models"""

    def generate(
        self,
        ir: IntermediateRepresentation,
        failing_predicate: Predicate
    ) -> Counterexample:
        """Generate concrete counterexample"""
        # Use solver model to create test case
        # ...

@dataclass
class Counterexample:
    inputs: Dict[str, Any]
    expected_output: Any
    actual_behavior: str
    violated_predicate: Predicate
    trace: list[str]
```

**Acceptance**:
- Generates runnable test cases
- Links back to IR predicates
- Human-readable explanations

### Phase 2 Success Metrics
- ✅ SMT solver detects unsatisfiable refinements
- ✅ Validation pipeline catches contradictions
- ✅ Counterexamples generated for failing specs
- ✅ <5s SMT time for 90% of queries
- ✅ <100ms SAT time for boolean checks

**Phase 2 Estimated Effort**: 3 months (1 senior eng + 1 solver specialist)

---

## 4. Phase 3: Hole Closures & Partial Evaluation (Months 7-10)

### Goal
Implement Hazel-style hole closures for:
- Executing programs with holes
- Collecting value flows through holes
- Fill-and-resume without restart
- Hole traces for debugging

### Tasks

#### 4.1 Evaluator Design (Week 1-3)
**Deliverable**: `lift_sys/eval/core.py`

```python
@dataclass
class Value:
    """Runtime value"""
    pass

@dataclass
class Closure(Value):
    """Function closure"""
    env: Environment
    param: str
    body: Expr

@dataclass
class HoleClosure(Value):
    """Hole with captured environment (IR 0.9 §2.8)"""
    hole: Hole
    env: Environment

    def resume(self, fill: Value) -> Value:
        """Resume evaluation after filling hole"""
        # ...

class Evaluator:
    """Partial evaluator with hole support"""

    def eval(self, expr: Expr, env: Environment) -> Value:
        """Evaluate with indeterminate progress"""
        match expr:
            case Var(name):
                return env[name]
            case App(f, arg):
                f_val = self.eval(f, env)
                arg_val = self.eval(arg, env)
                if isinstance(f_val, HoleClosure):
                    # Record flow through hole
                    self.trace_hole(f_val.hole, arg_val)
                    return HoleClosure(f_val.hole, env)
                return self.apply(f_val, arg_val)
            case HoleExpr(hole):
                return HoleClosure(hole, env)
            # ...
```

**Acceptance**:
- Can evaluate around holes
- Captures environment at hole sites
- Records value flows

#### 4.2 Trace Collection (Week 4-5)
**Deliverable**: `lift_sys/eval/trace.py`

```python
@dataclass
class HoleTrace:
    """Trace of values flowing through hole"""
    hole_id: str
    values_in: list[Value]
    contexts: list[Environment]
    timestamps: list[datetime]

class TraceCollector:
    """Collect hole traces during evaluation"""

    def record(self, hole: Hole, value: Value, env: Environment):
        """Record value flow"""
        # ...

    def get_trace(self, hole_id: str) -> HoleTrace:
        """Retrieve trace for hole"""
        # ...

    def suggest_fills(self, hole_id: str) -> list[Value]:
        """Suggest fills based on traces"""
        # Use traces + type info + solver
        # ...
```

**Acceptance**:
- Traces persist across evaluations
- Can query traces by hole ID
- Suggestions ranked by likelihood

#### 4.3 Fill-and-Resume (Week 6-8)
**Deliverable**: `lift_sys/eval/resume.py`

```python
class ResumeEngine:
    """Resume evaluation after filling holes"""

    def fill(self, hole_id: str, value: Value) -> None:
        """Fill hole with value"""
        self.fillings[hole_id] = value

    def resume(self, from_state: EvalState) -> Value:
        """Resume from saved state"""
        # Don't restart evaluation from scratch
        # Continue from where we left off
        # ...

@dataclass
class EvalState:
    """Saved evaluation state"""
    stack: list[Frame]
    env: Environment
    filled_holes: Dict[str, Value]
```

**Acceptance**:
- Filling hole doesn't restart evaluation
- State checkpointing works
- Performance: <10ms resume overhead

#### 4.4 Integration with UI (Week 9-10)
**Deliverable**: API endpoints

```python
# lift_sys/api/routes/evaluation.py

@router.post("/sessions/{session_id}/evaluate")
async def evaluate_partial(session_id: str, inputs: Dict[str, Any]):
    """Evaluate IR with inputs, even if holes present"""
    ir = await get_ir(session_id)
    evaluator = Evaluator()
    result = evaluator.eval(ir_to_expr(ir), inputs)
    traces = evaluator.get_traces()
    return {
        "result": serialize_value(result),
        "traces": [serialize_trace(t) for t in traces],
        "holes_encountered": [h.hole.identifier for h in result.hole_closures]
    }

@router.post("/sessions/{session_id}/fill-and-resume")
async def fill_and_resume(session_id: str, hole_id: str, fill: Any):
    """Fill hole and resume evaluation"""
    state = await get_eval_state(session_id)
    engine = ResumeEngine()
    engine.fill(hole_id, deserialize_value(fill))
    result = engine.resume(state)
    return {"result": serialize_value(result)}
```

**Acceptance**:
- UI can trigger partial evaluation
- Hole traces visible in UI
- Fill-and-resume works end-to-end

### Phase 3 Success Metrics
- ✅ Can evaluate IR with holes
- ✅ Hole traces collected correctly
- ✅ Fill-and-resume <10ms overhead
- ✅ UI shows live previews from partial evaluation
- ✅ Suggestions based on traces 70%+ helpful

**Phase 3 Estimated Effort**: 4 months (1 senior eng + 1 PL specialist)

---

## 5. Phase 4: Surface Syntax & Parsing (Months 11-14)

### Goal
Implement human-friendly Spec-IR surface syntax:
- Markdown with fenced blocks
- Readable syntax (Haskell/Idris-like)
- Bidirectional conversion (Surface ↔ Core IR)
- Diagnostics with Ariadne/Miette

### Tasks

#### 5.1 Grammar Design (Week 1-2)
**Deliverable**: `lift_sys/ir/surface_grammar.lark`

```lark
// Spec-IR surface syntax grammar
?start: program

program: decl+

?decl: intent_decl
     | entity_decl
     | spec_decl
     | def_decl
     | hole_decl

intent_decl: "intent" STRING ":" intent_body
intent_body: "inputs:" field_list
           | "outputs:" field_list
           | "goals:" goal_list

entity_decl: "entity" STRING ":" entity_body
entity_body: "fields:" field_list

spec_decl: "spec" STRING params ":" spec_body
spec_body: "requires:" predicate
         | "ensures:" predicate

def_decl: "def" NAME params ":" refinement "=" expr

hole_decl: "hole" HOLE_ID ":" hole_kind opt_type

refinement: "{" NAME ":" type "|" predicate "}"

// ... (full grammar)
```

**Acceptance**:
- Parses all examples from IR spec
- Handles holes gracefully
- Error recovery for partial input

#### 5.2 Parser Implementation (Week 3-5)
**Deliverable**: `lift_sys/ir/surface_parser.py`

```python
class SurfaceParser:
    """Parse Spec-IR surface syntax to Core IR"""

    def __init__(self):
        self.grammar = lark.Lark.open("surface_grammar.lark")

    def parse(self, source: str) -> IntermediateRepresentation:
        """Parse surface syntax to IR"""
        tree = self.grammar.parse(source)
        return self.elaborate(tree)

    def elaborate(self, tree: lark.Tree) -> IntermediateRepresentation:
        """Elaborate surface IR to core IR"""
        # Type inference
        # Constraint generation
        # Hole registration
        # ...
```

**Acceptance**:
- Parses example from IR spec §6.1 (summarizer)
- Handles nested holes
- Reports parse errors with spans

#### 5.3 Pretty Printer (Week 6-7)
**Deliverable**: `lift_sys/ir/surface_printer.py`

```python
class SurfacePrinter:
    """Pretty-print Core IR to Spec-IR surface syntax"""

    def print_ir(self, ir: IntermediateRepresentation) -> str:
        """Convert IR to readable surface syntax"""
        # ...

    def print_type(self, ty: Type) -> str:
        """Pretty-print type"""
        match ty:
            case RefinementType(base, var, pred):
                return f"{{{var}:{self.print_type(base)} | {self.print_pred(pred)}}}"
            # ...
```

**Acceptance**:
- Round-trip: parse(print(ir)) ≈ ir
- Human-readable output
- Syntax highlighting compatible

#### 5.4 Diagnostic System (Week 8-10)
**Deliverable**: `lift_sys/ir/diagnostics.py`

```python
class Diagnostic:
    """Ariadne/Miette-style diagnostic"""
    level: str  # error, warning, info
    message: str
    labels: list[Label]
    notes: list[str]
    help: str | None

class Label:
    """Source span with label"""
    span: Span
    message: str
    style: str  # primary, secondary

class DiagnosticRenderer:
    """Render diagnostics with fancy formatting"""

    def render(self, diag: Diagnostic, source: str) -> str:
        """Render diagnostic with source context"""
        # Ariadne-style colored output
        # ───────┬────────────────────────
        #        │ error: unsatisfiable refinement
        #     12 │   {x:Int | x > 0 ∧ x < 0}
        #        │            ─────┬──────
        #        │                 └─ contradiction here
        # ...
```

**Acceptance**:
- Beautiful error messages
- Suggests fixes where possible
- Links to documentation

#### 5.5 IDE Integration (Week 11-14)
**Deliverable**: LSP server basics

```python
# lift_sys/lsp/server.py

class SpecIRLanguageServer:
    """Language Server Protocol server for Spec-IR"""

    def on_open(self, doc: TextDocument):
        """Parse and validate document"""
        # ...

    def on_change(self, doc: TextDocument):
        """Incremental re-parse"""
        # ...

    def on_hover(self, position: Position) -> Hover:
        """Show hole information on hover"""
        # ...

    def on_completion(self, position: Position) -> list[CompletionItem]:
        """Suggest hole fills"""
        # ...
```

**Acceptance**:
- VS Code extension works
- Hover shows type info
- Completions for hole fills

### Phase 4 Success Metrics
- ✅ Can parse all IR 0.9 examples
- ✅ Pretty-printer produces readable syntax
- ✅ Round-trip fidelity >95%
- ✅ Diagnostics helpful (user study >7/10)
- ✅ LSP server provides hover/completion

**Phase 4 Estimated Effort**: 4 months (1 senior eng + 1 PL specialist + 1 frontend for LSP)

---

## 6. Phase 5: IntentSpec/FuncSpec Alignment & Provenance (Months 15-18)

### Goal
Implement alignment tracking and provenance:
- Alignment map with confidence scores
- Drift detection
- Intent ledger (event log)
- Provenance chains

### Tasks

#### 6.1 Alignment Engine (Week 1-4)
**Deliverable**: `lift_sys/alignment/engine.py`

```python
class AlignmentEngine:
    """Align IntentSpec atoms with FuncSpec predicates"""

    def align(
        self,
        intent: IntentSpec,
        func: FuncSpec
    ) -> AlignmentMap:
        """Create initial alignment"""
        # Use NLP + embedding similarity
        # Map goals → ensures predicates
        # Map constraints → requires predicates
        # ...

    def detect_drift(
        self,
        old_alignment: AlignmentMap,
        new_intent: IntentSpec,
        new_func: FuncSpec
    ) -> DriftReport:
        """Detect when alignment breaks"""
        # Check if mappings still valid
        # Report added/removed/changed atoms
        # ...

@dataclass
class DriftReport:
    drifted: bool
    added_atoms: list[str]
    removed_atoms: list[str]
    changed_mappings: list[tuple[str, str, str]]  # (atom, old_pred, new_pred)
    confidence_dropped: list[tuple[str, float, float]]  # (mapping, old_conf, new_conf)
```

**Acceptance**:
- Aligns example from IR spec
- Detects drift when spec changes
- Confidence scores reasonable

#### 6.2 Intent Ledger (Week 5-8)
**Deliverable**: `lift_sys/provenance/ledger.py`

```python
@dataclass
class LedgerEvent:
    """Event in intent ledger (IR 0.9 §16)"""
    id: str
    timestamp: datetime
    actor: str
    kind: str  # IntentAdded, SpecAligned, HoleFilled, etc.
    targets: list[str]  # IR node IDs
    diff: Dict[str, Any]
    effects: Dict[str, list[str]]  # functions, tests, policies touched
    justification: str

class IntentLedger:
    """Append-only event log for intent tracking"""

    def record(self, event: LedgerEvent) -> None:
        """Record event"""
        # Append to log
        # Update provenance graph
        # ...

    def query_history(self, target: str) -> list[LedgerEvent]:
        """Get history for IR node"""
        # ...

    def explain_change(self, event_id: str) -> str:
        """Generate human-readable explanation"""
        # Narrative: "User tightened constraint X because Y"
        # ...
```

**Acceptance**:
- Events immutable and ordered
- Can query by IR node
- Explanations readable

#### 6.3 Provenance Tracking (Week 9-12)
**Deliverable**: `lift_sys/provenance/tracker.py`

```python
@dataclass
class ProvenanceChain:
    """Chain of derivations for IR node"""
    node_id: str
    origin: str  # prompt, code, inference, solver, user
    derivation_steps: list[DerivationStep]
    confidence: float

@dataclass
class DerivationStep:
    """Single derivation step"""
    from_nodes: list[str]
    rule: str  # "inferred_from_return", "aligned_with_goal", etc.
    metadata: Dict[str, Any]

class ProvenanceTracker:
    """Track provenance for all IR elements"""

    def record_derivation(
        self,
        target: str,
        sources: list[str],
        rule: str
    ) -> None:
        """Record how target was derived"""
        # ...

    def get_chain(self, node_id: str) -> ProvenanceChain:
        """Get full provenance chain"""
        # ...

    def visualize(self, node_id: str) -> Graph:
        """Generate provenance graph"""
        # For UI visualization
        # ...
```

**Acceptance**:
- All IR elements have provenance
- Chains traceable to root
- Visualization clear

#### 6.4 Integration (Week 13-16)
**Deliverable**: Update all IR generation code

```python
# Example: Forward mode
class EnhancedIRTranslator:
    def __init__(self, tracker: ProvenanceTracker, ledger: IntentLedger):
        self.tracker = tracker
        self.ledger = ledger

    async def translate(self, prompt: str) -> IntermediateRepresentation:
        ir = await self._generate_ir(prompt)

        # Record provenance
        self.tracker.record_derivation(
            target=ir.id,
            sources=[],
            rule="translated_from_prompt"
        )

        # Record in ledger
        self.ledger.record(LedgerEvent(
            kind="IntentAdded",
            targets=[ir.intent_spec.id],
            justification=f"User provided prompt: {prompt[:100]}"
        ))

        return ir
```

**Acceptance**:
- Forward mode records provenance
- Reverse mode records provenance
- Refinements tracked in ledger

### Phase 5 Success Metrics
- ✅ Alignment detects drift 90%+ accuracy
- ✅ Ledger tracks all changes
- ✅ Provenance chains complete
- ✅ UI shows intent history
- ✅ "Why did this change?" queries work

**Phase 5 Estimated Effort**: 4 months (1 senior eng + 1 mid-level eng)

---

## 7. Phase 6: Safety Manifests & Production (Months 19-20)

### Goal
Production-ready system with:
- Safety/deployability manifests
- Policy gates
- Telemetry integration
- Documentation
- Beta testing

### Tasks

#### 7.1 Safety Manifest (Week 1-2)
**Deliverable**: `lift_sys/safety/manifest.py`

```python
@dataclass
class SafetyManifest:
    """Safety and deployability manifest (IR 0.9 §14)"""
    target: str
    slo: SLO
    resources: Resources
    network: NetworkPolicy
    security: SecurityPolicy
    telemetry: TelemetryConfig

@dataclass
class SecurityPolicy:
    sbom_format: str  # CycloneDX, SPDX
    slsa_level: int
    deny_hardcoded_secrets: bool
    allowed_secret_providers: list[str]
    policies: list[str]  # OPA Rego policies
```

**Acceptance**:
- Manifest validates
- Can generate SBOM/SLSA attestations

#### 7.2 Policy Gates (Week 3-4)
**Deliverable**: `lift_sys/safety/gates.py`

```python
class PolicyGate:
    """CI/CD gate for safety checks"""

    async def check(self, manifest: SafetyManifest, ir: IntermediateRepresentation) -> GateResult:
        """Run policy checks"""
        results = []

        # SBOM generation
        results.append(await self._generate_sbom(manifest))

        # SLSA attestation
        results.append(await self._generate_slsa(manifest))

        # OPA policy checks
        for policy in manifest.security.policies:
            results.append(await self._check_opa(policy, ir))

        return GateResult(
            passed=all(r.passed for r in results),
            results=results
        )
```

**Acceptance**:
- Gates integrated in CI
- Violations block deployment

#### 7.3 Telemetry Integration (Week 5-6)
**Deliverable**: OpenTelemetry spans

```python
# lift_sys/telemetry/instrumentation.py

class IRInstrumentation:
    """Instrument IR operations with OTel"""

    def trace_generation(self, ir_id: str):
        """Create span for IR generation"""
        with tracer.start_as_current_span(f"ir.generate.{ir_id}") as span:
            span.set_attribute("ir.version", "0.9")
            span.set_attribute("ir.holes", len(ir.holes))
            # ...
```

**Acceptance**:
- All operations traced
- Metrics exported
- Dashboards show IR metrics

#### 7.4 Documentation (Week 7-8)
**Deliverable**: Comprehensive docs

- User guide: Authoring Spec-IR
- Developer guide: Extending IR
- API reference
- Tutorial videos
- Migration guide (old IR → new IR)

#### 7.5 Beta Testing (Week 9-12)
- 20 beta testers
- Feedback collection
- Bug fixes
- Performance tuning

### Phase 6 Success Metrics
- ✅ All safety gates pass
- ✅ Telemetry dashboard live
- ✅ Documentation complete
- ✅ Beta user satisfaction >8/10
- ✅ No critical bugs

**Phase 6 Estimated Effort**: 2 months (full team)

---

## 8. Backward Compatibility Strategy

### Approach
**Gradual deprecation with adapters**

#### 8.1 Compatibility Layer
```python
# lift_sys/ir/compat.py

class LegacyIRAdapter:
    """Adapter for old IR format"""

    def from_legacy(self, old_ir: OldIntermediateRepresentation) -> IntermediateRepresentation:
        """Convert old IR to new IR"""
        # Map old IntentClause to IntentSpec
        intent_spec = IntentSpec(
            summary=old_ir.intent.summary,
            roles=[],
            goals=[],
            constraints=[],
            metrics={},
            notes=old_ir.intent.rationale or ""
        )

        # Map to FuncSpec (extract from assertions)
        func_spec = FuncSpec(
            requires=[],
            ensures=[self._parse_assertion(a) for a in old_ir.assertions],
            invariants=[],
            measure=None,
            cost=None,
            effects=frozenset(e.description for e in old_ir.effects)
        )

        # Create alignment (empty initially)
        alignment = AlignmentMap(
            mappings={},
            confidence={},
            last_verified=datetime.now(),
            drift_detected=False
        )

        return IntermediateRepresentation(
            intent_spec=intent_spec,
            func_spec=func_spec,
            alignment=alignment,
            # ...
        )

    def to_legacy(self, ir: IntermediateRepresentation) -> OldIntermediateRepresentation:
        """Convert new IR to old format (lossy)"""
        # For backward compatibility with old code
        # ...
```

#### 8.2 API Versioning
```python
# lift_sys/api/routes/generate.py

@router.post("/v1/generate")  # Old API
async def generate_v1(request: OldGenerateRequest):
    """Legacy endpoint using old IR"""
    adapter = LegacyIRAdapter()
    # ...

@router.post("/v2/generate")  # New API
async def generate_v2(request: NewGenerateRequest):
    """New endpoint using IR 0.9"""
    # ...
```

#### 8.3 Migration Tools
```python
# scripts/migrate_ir.py

class IRMigrationTool:
    """Migrate stored IRs from old to new format"""

    async def migrate_session(self, session_id: str):
        """Migrate single session"""
        old_ir = await old_storage.get_ir(session_id)
        new_ir = adapter.from_legacy(old_ir)
        await new_storage.save_ir(session_id, new_ir)

    async def migrate_all(self):
        """Migrate all sessions"""
        sessions = await old_storage.list_sessions()
        for session_id in sessions:
            await self.migrate_session(session_id)
```

### Deprecation Timeline
- **Months 1-6**: Both formats supported
- **Months 7-12**: Old format deprecated, warnings emitted
- **Month 13+**: Old format removed (adapter remains for import)

---

## 9. Risk Mitigation

### High Risks

#### 9.1 Solver Performance
**Risk**: SMT queries too slow for interactive use

**Mitigation**:
- Tiered approach (CSP → SAT → SMT)
- Caching solver results
- Incremental solving
- Fallback to heuristics if timeout
- Budget: 5s max per query

#### 9.2 Type System Complexity
**Risk**: Dependent types too complex for users

**Mitigation**:
- Inference where possible
- Simple types work without refinements
- Progressive disclosure (start simple)
- Excellent error messages
- Examples and templates

#### 9.3 Hole Closure Overhead
**Risk**: Partial evaluation too slow

**Mitigation**:
- Lazy evaluation
- Memoization
- Limit trace size
- Budget: <10ms overhead

#### 9.4 Breaking Changes
**Risk**: New IR breaks existing code

**Mitigation**:
- Compatibility layer
- Gradual migration
- Extensive testing
- Clear migration guide

### Medium Risks

#### 9.5 Surface Syntax Adoption
**Risk**: Users prefer old format

**Mitigation**:
- Make optional (both work)
- Show benefits clearly
- Smooth editor experience
- Good tutorials

#### 9.6 Alignment Accuracy
**Risk**: Intent/Func alignment low quality

**Mitigation**:
- Start with simple heuristics
- User can correct manually
- Learn from corrections
- Confidence thresholds

---

## 10. Success Metrics

### Technical Metrics

**Phase 1 (Types & Refinements)**:
- ✅ Type system can represent all IR 0.9 examples
- ✅ Backward compatibility ≥95%
- ✅ Performance: <100ms type checking

**Phase 2 (Solvers)**:
- ✅ SMT detects 90%+ unsatisfiable specs
- ✅ Solver time <5s for 90% queries
- ✅ Counterexamples useful (user study >7/10)

**Phase 3 (Hole Closures)**:
- ✅ Partial evaluation works for all examples
- ✅ Fill-and-resume <10ms overhead
- ✅ Hole traces 70%+ helpful

**Phase 4 (Surface Syntax)**:
- ✅ Parses all IR 0.9 examples
- ✅ Round-trip fidelity >95%
- ✅ Diagnostics helpful >7/10

**Phase 5 (Alignment & Provenance)**:
- ✅ Alignment detects drift 90%+ accuracy
- ✅ Provenance chains complete
- ✅ "Why?" queries answer 80%+ of questions

**Phase 6 (Production)**:
- ✅ All safety gates pass
- ✅ Beta user satisfaction >8/10
- ✅ Zero critical bugs

### Business Metrics

**Adoption**:
- 50+ active users by Month 12
- 200+ active users by Month 18
- 1000+ specs created by Month 20

**Quality**:
- Spec-to-code success rate >90%
- Code-to-spec fidelity >85%
- User retention >70%

---

## 11. Resource Requirements

### Team Composition

**Core Team** (Full time):
- 1 Tech Lead (all phases)
- 2 Senior Engineers (Phases 1-6)
- 1 PL Specialist (Phases 3-4)
- 1 Solver Specialist (Phase 2)
- 1 Frontend Engineer (Phase 4, Phase 6)

**Part Time**:
- 1 DevOps (Phase 6)
- 1 Technical Writer (Phase 6)
- 1 Designer (Phase 4, Phase 6)

**Total**: ~4-6 FTE over 20 months

### Infrastructure

- Modal.com credits: ~$2K/month
- Supabase Pro: ~$500/month
- Z3/solver compute: ~$500/month
- CI/CD (GitHub Actions): ~$200/month

**Total**: ~$3.2K/month = ~$64K over 20 months

---

## 12. Go/No-Go Decision Points

### After Phase 1 (Month 3)
**Decision**: Continue to solver integration?

**Criteria**:
- ✅ Type system working
- ✅ Backward compatibility verified
- ✅ Team confident in approach

**Risk**: If type system too complex, simplify before continuing

### After Phase 2 (Month 6)
**Decision**: Continue to hole closures?

**Criteria**:
- ✅ Solvers integrated
- ✅ Performance acceptable
- ✅ Counterexamples useful

**Risk**: If solver performance poor, revisit approach

### After Phase 3 (Month 10)
**Decision**: Continue to surface syntax?

**Criteria**:
- ✅ Partial evaluation working
- ✅ Users find hole traces helpful
- ✅ Performance acceptable

**Risk**: If hole closures too slow, optimize or simplify

### After Phase 4 (Month 14)
**Decision**: Continue to production?

**Criteria**:
- ✅ Surface syntax adopted
- ✅ LSP working
- ✅ Users prefer new IR

**Risk**: If users don't adopt surface syntax, keep both

### After Phase 5 (Month 18)
**Decision**: Launch beta?

**Criteria**:
- ✅ Alignment working
- ✅ Provenance complete
- ✅ System stable

**Risk**: If quality not there, extend Phase 5

---

## 13. Integration with DSPy Migration

**Parallel Tracks**:
- IR Adoption: Bottom-up (data models, solvers, evaluation)
- DSPy Migration: Top-down (AI components, optimization)

**Synergy Points**:
- **Phase 1-2**: DSPy can consume new IR types for signatures
- **Phase 3**: DSPy can use hole traces for training data
- **Phase 4**: Surface syntax parseable by DSPy prompts
- **Phase 5**: Provenance tracks DSPy optimization steps

**Coordination**:
- Both plans share IR schema
- DSPy migration can start after Phase 1 (Month 4)
- Full integration by Phase 5 (Month 18)

See [DSPy Migration Plan](DSPY_MIGRATION_PLAN.md) for details.

---

## 14. Timeline Summary

```
Month  Phase                        Deliverables
─────────────────────────────────────────────────────────────────
1-3    Phase 1: Types & Refinements  Enhanced IR data models
                                     Type system, Predicates
                                     Enhanced holes
                                     FuncSpec, IntentSpec
                                     Database migrations

4-6    Phase 2: Solver Integration   SMT encoder (Z3)
                                     SAT encoder
                                     CSP solver
                                     Validation pipeline
                                     Counterexample generation

7-10   Phase 3: Hole Closures        Partial evaluator
                                     Trace collection
                                     Fill-and-resume
                                     UI integration

11-14  Phase 4: Surface Syntax       Grammar + parser
                                     Pretty printer
                                     Diagnostics (Ariadne-style)
                                     LSP server basics
                                     VS Code extension

15-18  Phase 5: Alignment            Alignment engine
                                     Intent ledger
                                     Provenance tracking
                                     Integration across codebase

19-20  Phase 6: Production           Safety manifests
                                     Policy gates
                                     Telemetry (OpenTelemetry)
                                     Documentation
                                     Beta testing
```

**Total Duration**: 20 months
**Parallel Work**: Phases can overlap (e.g., Surface Syntax while Hole Closures finish)
**Aggressive Timeline**: 18 months with larger team

---

## 15. Next Steps

### Immediate (This Week)
1. ✅ Review this plan with team
2. ⬜ Get buy-in on timeline and scope
3. ⬜ Allocate engineers to Phase 1
4. ⬜ Set up Phase 1 tracking in Beads

### Week 2
1. ⬜ Start Phase 1.1: Type System Foundation
2. ⬜ Create detailed task breakdown for Phase 1
3. ⬜ Set up monitoring for success metrics

### Month 1
1. ⬜ Complete Type System (Phase 1.1)
2. ⬜ Complete Predicate System (Phase 1.2)
3. ⬜ Start Enhanced Hole System (Phase 1.3)

---

## 16. Conclusion

The IR 0.9 specification represents a major advancement in semantic program representation. This adoption plan:

✅ **Pragmatic**: Phased approach with clear go/no-go points
✅ **Ambitious**: Delivers full IR 0.9 vision in 20 months
✅ **Detailed**: Task-level breakdown for Phase 1-3
✅ **Risk-aware**: Mitigation strategies for key risks
✅ **Integrated**: Coordinates with DSPy migration plan

**The new IR will enable**:
- More accurate code generation (via solver verification)
- Interactive refinement (via hole closures and partial evaluation)
- Better user experience (via surface syntax and diagnostics)
- Provenance tracking (for trust and debugging)
- Production safety (via manifests and policy gates)

**This is the foundation for the codelift.space vision.**

---

**Status**: Ready for review and approval
**Next Action**: Schedule team review meeting
**Owner**: Tech Lead + Engineering Manager
