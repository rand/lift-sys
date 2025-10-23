# Product Requirements Document: Typed Holes (Iterative Refinement via Explicit Unknowns)

**Version**: 1.0
**Date**: 2025-10-21
**Status**: Active
**Owner**: Codelift Team

---

## Document Overview

**Purpose**: Define the vision, requirements, and implementation strategy for Typed Holes - a system for making unknowns explicit and enabling iterative refinement through constraint propagation and AI-assisted suggestions.

**Audience**: Product team, engineering team, researchers, PL experts

**Related Documents**:
- [PRD: lift](PRD_LIFT.md) - Top-level product vision
- [PRD: Interactive Refinement](PRD_INTERACTIVE_REFINEMENT.md) - User interaction workflows
- [IR Specification](../lift-sys/docs/IR_SPECIFICATION.md) - Technical details
- [Hole Inventory](../lift-sys/docs/planning/HOLE_INVENTORY.md) - Examples of 19 architectural holes
- [Semantic IR Roadmap](../lift-sys/SEMANTIC_IR_ROADMAP.md) - Phase 3 hole closures timeline

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Philosophy & Approach](#2-philosophy--approach)
3. [Hole Taxonomy](#3-hole-taxonomy)
4. [Functional Requirements](#4-functional-requirements)
5. [User Interactions](#5-user-interactions)
6. [Constraint Propagation](#6-constraint-propagation)
7. [AI Suggestions](#7-ai-suggestions)
8. [Success Metrics](#8-success-metrics)

---

## 1. Executive Summary

### Why Explicit Unknowns Matter

**The Problem with Black-Box AI**: Current AI coding tools make assumptions when specifications are ambiguous. When users write "create a notification system," the AI must guess:
- What channels? (Email, SMS, Push, Slack?)
- What priority levels? (Just high/normal, or a complex hierarchy?)
- How to handle failures? (Retry? Log? Alert?)
- What delivery guarantees? (At-most-once? At-least-once? Exactly-once?)

These guesses are often wrong, leading to:
- **Wasted iterations**: User discovers the wrong assumption after code is generated
- **Subtle bugs**: Implicit assumptions become bugs when edge cases hit
- **Loss of agency**: User doesn't know what decisions the AI made
- **No transparency**: Can't explain to stakeholders what the system does

### The Typed Holes Solution

**Make unknowns explicit.** Instead of guessing, lift identifies ambiguities as **typed holes** - placeholders that carry:
- **Type information**: What kind of thing fills this hole?
- **Constraints**: What must be true of any valid solution?
- **Context**: Why does this hole exist? What depends on it?
- **AI suggestions**: Ranked candidates with confidence scores

**User workflow**:
1. User writes spec: "Create a notification system..."
2. lift generates IR with holes: `?notification_channel`, `?priority_levels`, `?retry_strategy`
3. User hovers over hole → sees type, constraints, suggestions
4. User fills hole (or accepts AI suggestion)
5. Constraints propagate → other holes narrow, some resolve automatically
6. User can leave holes for later → partial evaluation shows how values flow

**Result**: Iterative refinement with full transparency. Users stay in control. AI assists rather than guesses.

### Key Differentiators

| Feature | Traditional AI Tools | lift with Typed Holes |
|---------|---------------------|----------------------|
| **Ambiguity Handling** | Guess and hope | Make explicit as holes |
| **User Agency** | Take it or leave it | Iterative refinement |
| **Transparency** | Black box | Full provenance |
| **Partial Progress** | All or nothing | Evaluate around holes |
| **Constraint Checking** | None | SMT solver verification |
| **Suggestions** | Single answer | Ranked candidates with confidence |

### Integration with lift Ecosystem

Typed holes are a **core pillar** of lift's bidirectional translation system:

**Forward Mode** (NL → Code):
- Spec ambiguities become holes
- User refines iteratively
- Constraints propagate
- Code generated only when holes resolved (or explicitly deferred)

**Reverse Mode** (Code → Understanding):
- Missing documentation becomes holes
- Unknown invariants become spec holes
- Implicit assumptions surfaced
- User fills in intent

**Interactive Refinement**:
- Split-view: Spec with holes ↔ IR ↔ Code
- Real-time constraint propagation
- Partial evaluation shows value flows
- Undo/redo with revision history

### Current Status (2025-10-21)

**Production** (IR 0.8):
- ✅ 4 basic hole kinds implemented (term, type, spec, entity)
- ✅ JSON serialization working
- ✅ Basic UI highlighting

**In Progress** (IR 0.9, Q2-Q3 2025):
- 🔄 Phase 1-2: Enhanced type system (dependent types, refinements) - Month 3 of 20
- ⏳ Phase 3: Hole closures & partial evaluation - Month 7-10 (Q3 2025)
- ⏳ Full 6 hole kinds (add function, module) - IR 0.9

**Meta-Framework Example**: lift is using typed holes to design itself:
- 19 architectural holes documented in HOLE_INVENTORY.md
- Holes like H1 (ProviderAdapter), H6 (NodeSignatureInterface) being resolved systematically
- Constraint propagation tracked: H1 resolution → affects H8 (OptimizationAPI), H10 (Metrics)
- Real dogfooding of the hole-driven development paradigm

---

## 2. Philosophy & Approach

### Theoretical Foundations

**Typed holes in lift synthesize ideas from three major research traditions:**

#### 2.1 GHC Typed Holes (Haskell)

**What we borrow**:
- **Valid hole fits**: Suggest in-scope terms that type-check for the hole
- **Refinement fits**: Generate scaffolding (λ-abstractions) to make types fit
- **Ranking heuristics**: Order by scope proximity, type compatibility

**Reference**: [GHC User Guide - Typed Holes](https://ghc.gitlab.haskell.org/ghc/doc/users_guide/exts/typed_holes.html)

**Example from GHC**:
```haskell
addOne :: Int -> Int
addOne x = x + _hole

-- GHC suggests:
--   Valid hole fits:
--     (1 :: Int)  -- literal
--     x           -- in scope variable
--   Refinement hole fits:
--     negate x    -- function application
```

**lift adaptation**:
- Apply to all 6 hole kinds (not just terms)
- Combine with constraint solving (SMT)
- Add AI-powered suggestions beyond syntax

#### 2.2 Hazel/Hazelnut Live (POPL 2019)

**What we borrow**:
- **Hole closures**: Runtime representation `⟨Γ, ?h⟩` pairing hole with environment
- **Indeterminate progress**: Evaluation continues around holes
- **Fill-and-resume**: Update hole without restarting evaluation

**Reference**: [Live Functional Programming with Typed Holes](https://arxiv.org/abs/1805.00155) (Omar et al., POPL 2019)

**Key insight**: Programs with holes can still execute, producing partial results and traces that help users understand what belongs in the hole.

**Example**:
```python
def process_orders(orders: List[Order]) -> Report:
    validated = [validate(o) for o in orders]  # validate is a hole
    return summarize(validated)

# Partial evaluation:
# - orders = [Order(id=1, amount=100), Order(id=2, amount=50)]
# - validated = [⟨Γ, ?validate⟩, ⟨Γ, ?validate⟩]  # hole closures
# - Trace: ?validate receives Order objects
# - Trace: ?validate must return something summarize accepts
# - Constraint: ?validate : Order -> SomeSummarizableType
```

**lift adaptation**:
- Implement hole closures in IR evaluator
- Collect traces showing value flows
- Use traces to improve AI suggestions

#### 2.3 Dependent Type Systems (Idris, Agda, Lean, Coq)

**What we borrow**:
- **Interactive refinement**: Users work through holes one at a time
- **Context propagation**: Filling one hole narrows others
- **Goal-directed search**: Use types to guide resolution

**Example from Idris**:
```idris
append : Vect n a -> Vect m a -> Vect ?len a
append xs ys = ?impl

-- Idris shows:
--   ?len : Nat
--   Constraint: ?len = n + m  (from return type)
--   ?impl : Vect (n + m) a
--   Context: xs : Vect n a, ys : Vect m a
```

**lift adaptation**:
- Use refinement types `{x:T | φ}` for constraints
- SMT solver checks constraint satisfiability
- Propagate type equalities across holes

### lift's Synthesis: Hazel Semantics + GHC Suggestions + SMT Verification

**Unique combination**:
1. **Holes in types and specs** (beyond GHC's term holes)
2. **Constraint-backed** (SMT solver, not just type checking)
3. **AI-enhanced** (LLM suggestions, not just syntax-based)
4. **Live evaluation** (Hazel-style hole closures)
5. **Multi-language** (not tied to one PL ecosystem)

**Result**: A hole system that works for semi-technical users, not just PL experts.

---

## 3. Hole Taxonomy

### 3.1 Overview of 6 Hole Kinds

| Kind | Symbol | Domain | Example | Use Case |
|------|--------|--------|---------|----------|
| **Term** | `?value` | Expressions | `?default_timeout`, `?max_retries` | Unknown constant, expression, or value |
| **Type** | `?T` | Types | `List<?T>`, `{x:?T \| x>0}` | Unknown type parameter or refinement |
| **Spec** | `?contract` | Predicates | `requires: ?contract`, `ensures: ?inv` | Unknown specification or constraint |
| **Entity** | `?User` | Domain models | `class ?User`, `?CustomerProfile` | Unknown domain entity or schema |
| **Function** | `?helper` | Functions | `result = ?helper(data)` | Unknown helper function needed |
| **Module** | `?lib` | Dependencies | `import ?lib`, `use ?crate` | Unknown library or dependency |

**Current Status**:
- IR 0.8: Term, Type, Spec, Entity (4 kinds) ✅
- IR 0.9: Add Function, Module (6 kinds total) ⏳ Q2 2025

### 3.2 Term Holes: Unknown Values or Expressions

**Description**: Placeholder for a missing value, constant, or expression.

**Type Signature**:
```python
class TermHole:
    id: str                    # ?default_timeout
    type: Type                 # Int, refined to {x:Int | x>0}
    constraints: list[Predicate]  # [x >= 100, x <= 3600]
    links: list[HoleRef]       # Dependencies: [?max_timeout]
    provenance: str            # "Derived from timeout parameter in spec"
    suggestions: list[Suggestion]  # AI-generated candidates
```

**Example 1: Configuration constant**
```python
# User spec: "Process items with a reasonable timeout"
def process_items(items: List[Item]) -> Result:
    timeout = ?default_timeout  # HOLE
    return asyncio.wait_for(process(items), timeout=timeout)

# Hole details:
# - Type: {x:Int | x > 0}
# - Constraints: [reasonable, not too short, not too long]
# - Suggestions:
#   1. (90% confidence) 30 seconds
#   2. (70% confidence) 60 seconds
#   3. (50% confidence) 300 seconds
```

**Example 2: Expression from real project (HOLE_INVENTORY.md H10)**
```python
# H10: OptimizationMetrics
def ir_quality(predicted: IR, expected: IR) -> float:
    return ?quality_formula  # HOLE

# Type: float, refined to {x:float | 0.0 <= x <= 1.0}
# Constraints: [higher is better, 0=worst, 1=perfect]
# Suggestions:
#   1. (85%) weighted_f1(predicted, expected)
#   2. (70%) structural_similarity(predicted, expected)
```

**Acceptance Criteria** (FR3.1):
- [x] Can create term hole with type annotation
- [x] Constraints enforced by SMT solver
- [ ] Suggestions generated and ranked
- [ ] User can accept/reject/modify suggestions
- [ ] Partial evaluation shows value flows through hole

### 3.3 Type Holes: Unknown Type Parameters

**Description**: Placeholder for a missing type, often in generic contexts.

**Example 1: Generic container**
```python
# User spec: "Store user preferences in a collection"
class UserPreferences:
    data: ?PreferenceStore  # HOLE

# Type hole details:
# - Kind: type
# - Constraints: [must support get/set, must be serializable]
# - Suggestions:
#   1. (80%) dict[str, Any]
#   2. (60%) dict[str, str]
#   3. (40%) Custom Pydantic model
```

**Example 2: Refinement parameter**
```python
# User spec: "List of positive numbers"
numbers: List[{x:?T | x > 0}]  # Type hole in refinement

# Type hole details:
# - Kind: type
# - Constraints: [supports > operator, numeric]
# - Suggestions:
#   1. (90%) Int
#   2. (70%) float
#   3. (40%) Decimal
```

**Example 3: From meta-framework (H11: ExecutionHistorySchema)**
```sql
-- Schema design with type hole
CREATE TABLE graph_executions (
    state ?StateType NOT NULL  -- What serialization format?
);

-- Type hole details:
-- - Suggestions: JSONB (flexible), JSON (standard), TEXT (fallback)
-- - Constraints: [must support Pydantic models, queryable]
```

**Acceptance Criteria** (FR3.2):
- [x] Can create type hole in signatures
- [x] Type hole can appear in refinements
- [ ] Type unification narrows hole
- [ ] Constraint propagation updates dependent types

### 3.4 Spec Holes: Unknown Specifications or Contracts

**Description**: Placeholder for missing pre/postcondition, invariant, or contract.

**Example 1: Postcondition**
```python
# User spec: "Transfer money between accounts safely"
def transfer(sender: Account, recipient: Account, amount: Money):
    requires: sender.balance >= amount
    requires: amount > 0
    ensures: ?postcondition  # HOLE - what must be true after?

# Spec hole details:
# - Kind: spec
# - Type: Predicate
# - Suggestions:
#   1. (95%) sender.balance' = sender.balance - amount
#   2. (90%) recipient.balance' = recipient.balance + amount
#   3. (85%) Both accounts exist after transfer
```

**Example 2: Invariant from HOLE_INVENTORY.md (H12: ConfidenceCalibration)**
```python
# H12: Confidence scoring
def score_suggestion(hole: TypedHole, suggestion: str) -> float:
    ensures: ?calibration_invariant  # HOLE

# Spec hole details:
# - Suggestions:
#   1. (80%) result correlates with actual accuracy
#   2. (70%) result ∈ [0.0, 1.0]
#   3. (60%) Brier score < 0.2
```

**Acceptance Criteria** (FR3.3):
- [ ] Spec holes in pre/post conditions
- [ ] SMT solver checks satisfiability
- [ ] Counterexamples when unsatisfiable
- [ ] Suggestions derived from context

### 3.5 Entity Holes: Unknown Domain Entities

**Description**: Placeholder for missing domain model, schema, or data structure.

**Example 1: User profile schema**
```python
# User spec: "Store customer information"
class Customer:
    id: UUID
    name: str
    profile: ?CustomerProfile  # HOLE - what fields?

# Entity hole details:
# - Kind: entity
# - Constraints: [must be serializable, PII-safe]
# - Suggestions:
#   1. (70%) {email: str, phone: str, preferences: dict}
#   2. (60%) {tier: str, since: datetime, metadata: dict}
#   3. (40%) Full CRM schema (15 fields)
```

**Example 2: From IR Specification (Section 6.2)**
```python
# Example from docs
entity "CustomerProfile":
    fields:
        id: {x:Int | x >= 0}
        email: Str
        plan: ?Plan  # ENTITY HOLE

spec "PlanConstraints"(p: ?Plan):
    ensures: valid_plan(p)

# Entity hole details:
# - Links: Used in PlanConstraints spec
# - Constraints: Must satisfy valid_plan predicate
```

**Acceptance Criteria** (FR3.4):
- [ ] Entity holes in class definitions
- [ ] Schema inference from usage
- [ ] Suggestions include field types
- [ ] Can split entity hole into field holes

### 3.6 Function Holes: Unknown Helper Functions

**Description**: Placeholder for a function that's needed but not yet defined.

**Example 1: Validation helper**
```python
# User spec: "Process orders after validation"
def process_orders(orders: List[Order]) -> Report:
    validated = [?validate_order(o) for o in orders]  # FUNCTION HOLE
    return summarize(validated)

# Function hole details:
# - Kind: function
# - Type: Order -> ValidatedOrder | ValidationError
# - Constraints: [must check required fields, must validate amounts]
# - Suggestions:
#   1. (80%) def validate_order(o): check_required_fields(o) and check_amounts(o)
#   2. (60%) Use Pydantic validation
#   3. (40%) Custom validator with logging
```

**Example 2: From HOLE_INVENTORY.md (H5: ErrorRecovery)**
```python
# H5: Error recovery
class ErrorRecovery:
    async def handle_node_error(
        self,
        node: BaseNode,
        error: Exception,
        ctx: RunContext
    ) -> RecoveryAction:
        if ?should_retry(error, ctx.attempt):  # FUNCTION HOLE
            return Retry(backoff=exponential(ctx.attempt))
        return Fail(error)

# Function hole details:
# - Type: (Exception, int) -> bool
# - Constraints: [transient errors retry, fatal errors fail fast]
```

**Acceptance Criteria** (FR3.5):
- [ ] Function holes in call sites
- [ ] Type inference from usage context
- [ ] Suggestions include implementations
- [ ] Can scaffold function definition

### 3.7 Module Holes: Unknown Dependencies

**Description**: Placeholder for a library, package, or module import.

**Example 1: HTTP client**
```python
# User spec: "Fetch data from REST API"
import ?http_client  # MODULE HOLE

def fetch_users() -> List[User]:
    response = ?http_client.get("https://api.example.com/users")
    return parse_users(response.json())

# Module hole details:
# - Kind: module
# - Constraints: [async support preferred, type-safe]
# - Suggestions:
#   1. (85%) httpx (modern, async)
#   2. (70%) requests (popular, sync)
#   3. (50%) aiohttp (async, lower-level)
```

**Example 2: From HOLE_INVENTORY.md (H1: ProviderAdapter)**
```python
# H1: LLM provider
from ?llm_framework import Provider  # MODULE HOLE

class ProviderAdapter:
    def __init__(self, provider: ?llm_framework.Provider):
        ...

# Module hole details:
# - Constraints: [supports async, XGrammar compatible]
# - Suggestions: DSPy, LangChain, custom
```

**Acceptance Criteria** (FR3.6):
- [ ] Module holes at import sites
- [ ] Dependency resolution via package registry
- [ ] Version constraints from compatibility
- [ ] Installation instructions generated

---

## 4. Functional Requirements

### FR3.1: Hole Detection During IR Generation
**Priority**: P0

**Requirement**: System must automatically detect ambiguities and create typed holes during spec → IR translation.

**Detection Triggers**:
- Vague terms: "reasonable timeout", "appropriate", "good quality"
- Missing parameters: "send notifications" (what channels?)
- Underspecified behavior: "handle errors" (retry? fail? log?)
- Unknown types: Generic without concrete instantiation
- Incomplete contracts: Precondition without postcondition

**Acceptance Criteria**:
- [ ] 80%+ of human-identified ambiguities caught
- [ ] False positive rate <10%
- [ ] Detection latency <500ms
- [ ] Each hole has provenance (why created)

**Test Cases**:
- Prompt: "Create a cache" → Detects `?CacheStrategy` hole
- Prompt: "Validate input" → Detects `?ValidationRules` hole
- Prompt: "Process with timeout" → Detects `?TimeoutValue` term hole

---

### FR3.2: Type Annotations on Holes
**Priority**: P0

**Requirement**: Every hole must have a type (possibly itself a type hole).

**Type Inference**:
- From usage context (bottom-up)
- From declared constraints (top-down)
- From examples and traces (Hazel-style)

**Support**:
- Base types: Int, Str, Bool, Float
- Refinement types: `{x:T | φ}`
- Dependent types: `Π(x:T).U` (IR 0.9+)
- Generic types: `List[?T]`, `dict[str, ?V]`
- Unknown types: `?h : ?α` (type hole for type hole)

**Acceptance Criteria**:
- [ ] All holes have type annotations
- [ ] Type unification works across holes
- [ ] Dependent types supported (IR 0.9)
- [ ] Unknown-type holes handled gracefully

---

### FR3.3: Constraint Sets on Holes
**Priority**: P0

**Requirement**: Holes must carry constraints limiting valid fills.

**Constraint Sources**:
- **Type constraints**: From type system
- **Refinement constraints**: From predicates `{x:T | φ}`
- **Spec constraints**: From pre/postconditions
- **Usage constraints**: From how hole is used
- **Domain constraints**: From business rules

**Constraint Types**:
- Equality: `?timeout = 30`
- Inequality: `?max >= ?min`, `?probability ∈ [0.0, 1.0]`
- Membership: `?status ∈ {pending, active, completed}`
- Structural: `?schema has fields [id, name, email]`
- Logical: `?condition → ?consequence`

**SMT Integration**:
- Encode constraints to SMT-LIB
- Check satisfiability before fill
- Generate counterexamples when unsatisfiable

**Acceptance Criteria**:
- [ ] Constraints encoded correctly
- [ ] SMT solver integration working
- [ ] Counterexamples actionable
- [ ] Solver latency <5s for 90% of queries

---

### FR3.4: Dependency Links Between Holes
**Priority**: P0

**Requirement**: Holes must track dependencies to enable constraint propagation.

**Dependency Types**:
- **Blocking**: H1 must resolve before H2
- **Informing**: Resolving H1 narrows H2 (but doesn't block)
- **Conflicting**: H1 and H2 can't both have certain values

**Graph Operations**:
- Topological sort for resolution order
- Critical path identification
- Cycle detection (circular dependencies)
- Impact analysis (what does filling this affect?)

**Example from HOLE_INVENTORY.md**:
```python
# H6 (NodeSignatureInterface) blocks:
# - H1 (ProviderAdapter)
# - H2 (StatePersistence)
# - H4 (ParallelizationImpl)

# Dependency graph:
H6 → H1 → H10 → H17  # Critical path
H6 → H2 → H11 → H7   # Parallel track
```

**Acceptance Criteria**:
- [ ] Dependency graph construction
- [ ] Cycle detection working
- [ ] Critical path computation <100ms
- [ ] Impact analysis shows affected holes

---

### FR3.5: AI Suggestions Ranked by Confidence
**Priority**: P0

**Requirement**: For each hole, generate AI suggestions with confidence scores.

**Suggestion Sources**:
1. **Constraint solver**: Concrete models satisfying constraints
2. **Valid fits** (GHC-style): In-scope terms with compatible types
3. **Pattern matching**: Similar code in codebase or corpus
4. **LLM generation**: Context-aware suggestions
5. **Usage priors**: Common values from training data

**Ranking Factors**:
- Type compatibility score
- Constraint satisfaction score
- Scope proximity (prefer local over global)
- Usage frequency (common patterns ranked higher)
- Semantic similarity to context
- Confidence calibration (see FR3.12)

**Acceptance Criteria**:
- [ ] Top suggestion correct 60%+ of time
- [ ] Top-3 contains correct answer 80%+
- [ ] Suggestions generated <2s
- [ ] Confidence scores calibrated (score 0.8 → 80% accuracy)

---

### FR3.6: Partial Evaluation with Holes (Hazel-Style)
**Priority**: P1

**Requirement**: Allow programs with holes to execute, producing partial results and traces.

**Hole Closures**:
- Runtime representation: `⟨Γ, ?h⟩`
- Capture environment at hole site
- Propagate through evaluation
- Record value flows in traces

**Traces**:
- What values flowed into hole?
- What values flowed out?
- What operations were attempted?
- What type constraints were discovered?

**Use Cases**:
- Preview behavior before full resolution
- Discover constraints from usage
- Generate examples for AI suggestions
- Debug complex holes

**Example**:
```python
def process_users(users: List[User]) -> Report:
    validated = [?validate(u) for u in users]  # Hole
    return summarize(validated)

# Partial evaluation:
# Input: users = [User(id=1, email="a@b.com"), User(id=2, email="invalid")]
# Trace at ?validate:
#   - Received: User(id=1, email="a@b.com")
#   - Expected output type: Something summarize() accepts
#   - Constraint discovered: ?validate must handle invalid emails
```

**Acceptance Criteria**:
- [ ] Hole closures implemented in evaluator
- [ ] Traces collected correctly
- [ ] Fill-and-resume works (no restart needed)
- [ ] Trace size limited (max 1000 values)

---

### FR3.7: Hole Traces Showing Value Flows
**Priority**: P1

**Requirement**: Record and visualize what values pass through holes during evaluation.

**Trace Schema**:
```python
class HoleTrace:
    hole_id: str
    inputs: list[Any]          # Values that flowed in
    outputs: list[Any]         # Values that flowed out (if hole filled)
    operations: list[str]      # Operations attempted
    discovered_constraints: list[Predicate]  # Learned from usage
    timestamp: datetime
```

**Visualization**:
- Timeline view of value flows
- Highlight unexpected values
- Show constraint violations
- Link to suggestion updates

**Acceptance Criteria**:
- [ ] Traces collected during partial evaluation
- [ ] UI displays traces clearly
- [ ] Discovered constraints propagate
- [ ] Trace history browsable

---

### FR3.8: Undo/Redo with Revision History
**Priority**: P1

**Requirement**: Users can undo/redo hole fills and restore previous states.

**Revision Tracking**:
```python
class RefinementStep:
    timestamp: datetime
    hole_id: str
    action: FillHole | SplitHole | MergeHoles | RevertFill
    before: HoleState
    after: HoleState
    propagated_changes: list[HoleUpdate]
```

**Operations**:
- Undo: Revert to previous state, reverse constraint propagation
- Redo: Re-apply reverted change
- Branch: Create alternative refinement path
- Merge: Combine refinement paths (with conflict resolution)

**Acceptance Criteria**:
- [ ] Undo/redo works correctly
- [ ] Constraint propagation reversed on undo
- [ ] Branch/merge supported
- [ ] Full history persisted

---

### FR3.9: Hole Splitting and Merging
**Priority**: P2

**Requirement**: Users can decompose complex holes or combine simple ones.

**Split**:
- Break entity hole into field holes
- Break function hole into signature + implementation
- Break spec hole into pre + post + invariants

**Merge**:
- Combine related term holes (e.g., min/max into range)
- Unify duplicate holes
- Compose function holes into pipeline

**Example**:
```python
# Original hole
?error_handling : ErrorStrategy

# Split into:
?network_errors : NetworkErrorStrategy
?business_errors : BusinessErrorStrategy
?retry_policy : RetryPolicy

# Later merge retry policies:
?retry_policy = merge(?network_retry, ?business_retry)
```

**Acceptance Criteria**:
- [ ] Split creates well-typed holes
- [ ] Merge preserves constraints
- [ ] UI supports split/merge actions
- [ ] Undo works for split/merge

---

### FR3.10: Export/Import Hole Fills for Reuse
**Priority**: P2

**Requirement**: Users can save and reuse hole fills across sessions.

**Export Format**:
```json
{
  "hole_template": "?timeout:term",
  "type": "{x:Int | x>0}",
  "constraints": ["x >= 100", "x <= 3600"],
  "fills": [
    {"value": 300, "context": "API requests", "frequency": 0.6},
    {"value": 30, "context": "database queries", "frequency": 0.3}
  ]
}
```

**Use Cases**:
- Team shares common hole fills
- Personal library of patterns
- Project-specific defaults
- Template marketplace (future)

**Acceptance Criteria**:
- [ ] Export to JSON/YAML
- [ ] Import with validation
- [ ] Context-aware suggestions from library
- [ ] Version control friendly

---

### FR3.11: Constraint Propagation Engine
**Priority**: P0

**Requirement**: Filling one hole must propagate constraints to dependent holes.

**Propagation Rules** (see Section 6 for details):
1. Type refinement: Filling type hole narrows dependent types
2. Value constraints: Filling term hole updates inequalities
3. Spec implications: Filling precondition strengthens postcondition
4. Entity dependencies: Filling field affects schema constraints

**Engine**:
- Dependency graph traversal
- Incremental constraint solving
- Conflict detection and reporting
- Fixpoint computation for cycles

**Acceptance Criteria**:
- [ ] Propagation correctness verified
- [ ] Latency <100ms for typical graphs
- [ ] Conflicts detected and reported
- [ ] User notified of propagated changes

---

### FR3.12: Confidence Calibration for Suggestions
**Priority**: P1

**Requirement**: Confidence scores must be calibrated to match actual accuracy.

**Calibration**:
- Score 0.8 → 80% of suggestions accepted
- Score 0.5 → 50% of suggestions accepted
- Measure via user feedback loop

**Methods**:
- Logistic regression on features
- Isotonic regression for calibration
- Continuous learning from corrections

**Features**:
- Type match score
- Constraint satisfaction score
- Scope proximity
- Usage frequency
- LLM confidence
- Historical acceptance rate

**Acceptance Criteria**:
- [ ] Calibration plot: predicted vs actual
- [ ] Brier score <0.2
- [ ] Improves with feedback
- [ ] User study: confidence helpful

---

### FR3.13: Hole Provenance Tracking
**Priority**: P1

**Requirement**: Every hole must have a provenance explaining why it exists.

**Provenance Fields**:
```python
class HoleProvenance:
    source: HoleSource  # spec_ambiguity | type_inference | constraint_gap
    span: Span          # Location in original spec
    justification: str  # Human-readable explanation
    alternatives: list[str]  # What was considered
    confidence: float   # How certain is hole creation?
```

**Sources**:
- Spec ambiguity: "reasonable timeout" is vague
- Type inference gap: Can't infer type from usage
- Constraint gap: Pre/post don't uniquely determine value
- User explicit: User marked as unknown

**Acceptance Criteria**:
- [ ] All holes have provenance
- [ ] Provenance shown in UI
- [ ] Justification clear to semi-technical users
- [ ] Linked to source span

---

### FR3.14: Hole Context in UI (Hover, Tooltips)
**Priority**: P0

**Requirement**: Rich contextual information when user interacts with hole.

**Hover Tooltip Contents**:
- Hole ID and kind
- Type annotation
- Constraint summary
- Top 3 suggestions with confidence
- Provenance (why does this exist?)
- Dependencies (what blocks/is blocked?)
- Recent traces (value flows)

**Actions from Tooltip**:
- Accept suggestion
- Reject and provide own value
- Split hole
- Defer for later
- View full details (opens panel)

**Acceptance Criteria**:
- [ ] Tooltip loads <50ms
- [ ] All information visible
- [ ] Actions work from tooltip
- [ ] Responsive design (mobile support)

---

### FR3.15: Hole Search and Filtering
**Priority**: P2

**Requirement**: Users can find and filter holes by various criteria.

**Search Dimensions**:
- By kind: Show all type holes
- By status: Resolved, unresolved, deferred
- By dependency: Holes blocking critical path
- By confidence: Holes with low-confidence suggestions
- By context: Holes in specific module/entity

**Sorting**:
- By priority (critical path first)
- By confidence (low confidence first)
- By creation time
- By dependency count

**Acceptance Criteria**:
- [ ] Search works <100ms
- [ ] Filters composable
- [ ] Keyboard navigation
- [ ] Persistent search state

---

## 5. User Interactions

### 5.1 Discovering Holes

**Entry Point**: After spec → IR generation, user sees IR with highlighted holes.

**Visual Design**:
- Holes underlined with yellow wavy line (VSCode-style)
- Icon indicates hole kind (🔲 term, 🔳 type, 📋 spec, 👤 entity, ⚙️ function, 📦 module)
- Glow effect for holes on critical path
- Badge shows number of unresolved holes

**Notification**:
```
IR generated successfully!
⚠️ 5 ambiguities detected as typed holes.
👉 Hover to see suggestions, or refine later.
```

---

### 5.2 Hovering Over Hole

**Trigger**: User hovers mouse over hole

**Tooltip Content**:
```
┌─────────────────────────────────────────┐
│ ?notification_channel (term hole)       │
│ Type: Set[Channel]                      │
│ Constraints: At least one channel       │
│                                         │
│ Suggestions:                            │
│ ✓ {Email, Push} (90% confidence)       │
│   {Email} (70% confidence)             │
│   {SMS, Email, Push} (60% confidence)  │
│                                         │
│ Why: "send notifications" is ambiguous │
│ Blocks: ?retry_strategy, ?rate_limit  │
│                                         │
│ [Accept] [Custom] [Defer] [Details]    │
└─────────────────────────────────────────┘
```

**Actions**:
- **Accept**: Fill hole with top suggestion
- **Custom**: Open input for manual value
- **Defer**: Mark as "to do later"
- **Details**: Open full hole panel (traces, constraints, etc.)

---

### 5.3 Accepting a Suggestion

**User Action**: Click "Accept" on suggestion

**System Response**:
1. Fill hole with selected value
2. Propagate constraints to dependent holes
3. Show notification of changes
4. Highlight affected holes
5. Recompute critical path
6. Update hole count badge

**Notification**:
```
✅ ?notification_channel filled: {Email, Push}

Propagated changes:
  • ?rate_limit updated: max 100/min for Email, 50/min for Push
  • ?retry_strategy narrowed: 3 valid options → 1 (email_retry)

2 holes remaining (was 5)
```

---

### 5.4 Providing Custom Value

**User Action**: Click "Custom" → enters value

**Validation**:
- Type check: Does value match hole type?
- Constraint check: Do constraints hold?
- SMT solver: Is result satisfiable?

**Feedback on Invalid Value**:
```
❌ Invalid value for ?timeout

Value: -5
Error: Violates constraint {x:Int | x>0}

Suggestion: Try a positive integer like 30, 60, or 300
```

**Feedback on Valid Value**:
```
✅ ?timeout filled: 42

Note: This is an unusual value (not in top suggestions).
Constraint check passed ✓
```

---

### 5.5 Splitting a Hole

**User Action**: Right-click hole → "Split into parts"

**Dialog**:
```
Split ?error_handling into:

○ Component holes (strategy, logging, retry)
○ Pre/post holes (precondition, postcondition)
○ Custom split (enter hole names)

[Split] [Cancel]
```

**Result**:
```
?error_handling split into:
  • ?error_strategy (how to handle?)
  • ?error_logging (what to log?)
  • ?retry_policy (when to retry?)

These holes inherit constraints from parent.
Fill them individually or merge later.
```

---

### 5.6 Deferring a Hole

**User Action**: Click "Defer" on hole

**System**: Mark hole as deferred, allow code generation with placeholder

**Code Generation**:
```python
# Deferred hole: ?validation_strategy
def process_item(item: Item) -> Result:
    # TODO: Implement validation strategy (hole ?validation_strategy)
    # Suggestions:
    #   1. Pydantic validation
    #   2. Custom validator
    #   3. Schema-based validation
    pass  # PLACEHOLDER
```

**Partial Evaluation**:
- Evaluation continues around deferred hole
- Traces collected
- User can fill later based on traces

---

### 5.7 Viewing Hole Traces

**User Action**: Click "Details" → "View Traces"

**Trace Visualization**:
```
Traces for ?validate:

Input Values (3 examples):
  1. User(id=1, email="valid@example.com")
  2. User(id=2, email="invalid")
  3. User(id=3, email="test@test.com")

Discovered Constraints:
  • Must handle invalid emails
  • Must return bool or ValidationResult
  • Called 1000+ times (performance matters)

Suggested Type:
  User -> Result[ValidatedUser, ValidationError]
```

---

## 6. Constraint Propagation

### 6.1 Propagation Rules

#### Rule 1: Type Refinement
```
When: Type hole ?T filled with concrete type T_concrete
Then: All holes typed with ?T update to T_concrete

Example:
  ?PreferenceStore filled with dict[str, Any]
  Propagates to:
    • ?get_preference : dict[str, Any] -> Any
    • ?set_preference : (dict[str, Any], str, Any) -> None
```

#### Rule 2: Value Constraints
```
When: Term hole ?x filled with value v
Then: Update inequalities involving ?x

Example:
  ?max_timeout filled with 300
  Propagates to:
    • ?default_timeout : {t:Int | t <= 300}  (was just t>0)
    • ?min_timeout : {t:Int | t < 300}       (was no upper bound)
```

#### Rule 3: Spec Implications
```
When: Precondition hole filled
Then: Strengthen postcondition constraints

Example:
  requires: ?pre filled with "x != null"
  Propagates to:
    ensures: ?post can now assume x is non-null
```

#### Rule 4: Entity Dependencies
```
When: Entity field hole filled
Then: Update schema constraints

Example:
  ?CustomerProfile filled with {email: str, tier: str}
  Propagates to:
    • ?validate_customer must check email and tier
    • ?serialize_customer must handle both fields
```

### 6.2 Propagation Algorithm

**Input**: Filled hole H with value V
**Output**: Updated holes and constraints

```python
def propagate(filled_hole: Hole, value: Any):
    # 1. Find dependent holes
    dependents = dependency_graph.get_dependents(filled_hole.id)

    # 2. For each dependent:
    for dep in dependents:
        # 2a. Update type constraints
        updated_type = unify(dep.type, substitute(filled_hole.id, value))

        # 2b. Update value constraints
        updated_constraints = [
            substitute_and_simplify(c, {filled_hole.id: value})
            for c in dep.constraints
        ]

        # 2c. Check satisfiability
        if not smt_check(updated_constraints):
            report_conflict(dep, filled_hole, value)
            continue

        # 2d. Update suggestions
        dep.suggestions = regenerate_suggestions(dep, updated_constraints)

        # 2e. Notify UI
        emit_update(dep.id, updated_type, updated_constraints)

    # 3. Recompute critical path
    critical_path = dependency_graph.topological_sort()

    # 4. Auto-resolve if constraints uniquely determine value
    for dep in dependents:
        if unique_value := solver_unique_model(dep.constraints):
            auto_fill(dep, unique_value)
            propagate(dep, unique_value)  # Recursive
```

### 6.3 Conflict Detection

**Scenario**: Propagated constraints become unsatisfiable

**Example**:
```python
# Holes
?min_timeout : {x:Int | x>0}
?max_timeout : {y:Int | y>0}
constraint: ?min_timeout < ?max_timeout

# User fills
?min_timeout = 100  # OK

# User tries to fill
?max_timeout = 50   # CONFLICT

# SMT solver: UNSAT
# Counterexample: 100 < 50 is false
```

**UI Response**:
```
❌ Conflict detected

Filling ?max_timeout with 50 violates:
  ?min_timeout (100) < ?max_timeout (50)

Suggestions:
  • Change ?max_timeout to 200 (>=100)
  • Or reduce ?min_timeout to 30
  • Or adjust constraint (different relationship?)
```

### 6.4 Incremental Constraint Solving

**Challenge**: Avoid re-solving entire constraint system after each fill

**Solution**: SMT solver push/pop contexts
```python
# Create solver context
solver = Z3Solver()

# Add baseline constraints
solver.push()
for constraint in baseline_constraints:
    solver.add(encode_smt(constraint))

# Try filling hole
solver.push()
solver.add(encode_smt(f"{hole.id} = {value}"))

if solver.check() == sat:
    # Fill valid, commit
    solver.pop()  # Remove trial
    solver.add(encode_smt(f"{hole.id} = {value}"))  # Add permanently
else:
    # Fill invalid, rollback
    solver.pop()
    show_conflict(solver.unsat_core())
```

**Performance**:
- Incremental solving: <100ms per fill
- Full re-solve: <5s for typical system
- Caching: Reuse solver state when possible

---

## 7. AI Suggestions

### 7.1 Suggestion Generation Pipeline

**Input**: Hole H with type T, constraints C, context Γ

**Pipeline**:
1. **Solver-based**: Generate SMT models satisfying C
2. **Valid fits**: Find in-scope terms matching T (GHC-style)
3. **Pattern matching**: Search codebase for similar holes
4. **LLM generation**: Prompt with context, parse suggestions
5. **Ranking**: Score by type match, constraint satisfaction, usage priors
6. **Calibration**: Adjust confidence based on historical accuracy

**Output**: List[(suggestion, confidence)]

### 7.2 Solver-Based Suggestions

**Method**: Generate concrete models from SMT constraints

**Example**:
```python
# Hole constraints
?timeout : {x:Int | x>0 ∧ x<=3600 ∧ x%10=0}

# SMT solver generates models:
Model 1: x = 10
Model 2: x = 30
Model 3: x = 300

# Rank by usage priors → 30 most common
```

**Limitations**:
- Infinite solution spaces (sample with heuristics)
- Complex constraints (timeout fallback)
- No semantic understanding (just syntactic)

### 7.3 Valid Fits (GHC-Style)

**Method**: Search in-scope identifiers for type-compatible terms

**Example**:
```python
# Hole
result = ?process_data(raw_data)
Type: ?process_data : RawData -> ProcessedData

# In-scope candidates:
1. clean_data : RawData -> CleanData (type mismatch, but close)
2. validate_data : RawData -> ValidationResult (wrong return type)
3. transform : RawData -> ProcessedData (exact match!)

# Refinement fits:
4. lambda x: ProcessedData(transform(x))
```

**Ranking Factors**:
- Exact type match: +10 points
- Scope proximity: local +5, module +2, global +0
- Usage frequency: log(uses) points
- Name similarity: edit_distance bonus

### 7.4 LLM-Generated Suggestions

**Prompt Template**:
```
You are helping resolve a typed hole in a formal IR.

Hole: ?validation_strategy
Type: ValidationStrategy
Constraints:
  - Must validate user input
  - Must handle invalid data gracefully
  - Performance: <10ms per validation

Context:
  - Function: process_user_registration(data: UserData)
  - Available in scope: check_email, check_password, UserSchema
  - Similar code in codebase: Pydantic validation used 80% of time

Generate 3 suggestions for this hole, ranked by appropriateness:
1. [Most appropriate]
2. [Alternative]
3. [Fallback]

Format: {"suggestion": "...", "justification": "..."}
```

**Response Parsing**:
- Extract suggestions from JSON/markdown
- Validate against hole type
- Check constraint satisfaction
- Filter invalid suggestions

**Challenges**:
- Hallucination (LLM suggests non-existent functions)
- Overfitting to prompt wording
- Inconsistent formatting

**Mitigations**:
- Schema validation before showing to user
- Cross-check with codebase (function exists?)
- Few-shot examples in prompt
- DSPy optimization over time

### 7.5 Suggestion Ranking

**Scoring Function**:
```python
def score_suggestion(hole: Hole, sugg: Suggestion, ctx: Context) -> float:
    scores = {
        "type_match": type_compatibility(hole.type, sugg.inferred_type),
        "constraint_sat": constraint_satisfaction(hole.constraints, sugg.value),
        "scope_proximity": scope_score(sugg, ctx.scope),
        "usage_prior": log(usage_count(sugg, ctx.codebase)),
        "llm_confidence": sugg.llm_confidence if sugg.from_llm else 0.5,
        "name_similarity": edit_distance_score(hole.id, sugg.name),
    }

    weights = {
        "type_match": 0.3,
        "constraint_sat": 0.25,
        "scope_proximity": 0.15,
        "usage_prior": 0.15,
        "llm_confidence": 0.1,
        "name_similarity": 0.05,
    }

    return sum(scores[k] * weights[k] for k in scores)
```

**Calibration**:
- Measure acceptance rate per score range
- Adjust weights via logistic regression
- Continuous learning from user feedback

### 7.6 Context-Aware Suggestions

**Context Sources**:
- **Function context**: Other parameters, return type, function name
- **Entity context**: Related fields, class hierarchy
- **Codebase patterns**: How similar holes were filled
- **User history**: User's previous choices
- **Domain knowledge**: Best practices for domain (web, ML, data, etc.)

**Example**:
```python
# Hole in web API endpoint
def create_user(data: UserData) -> Response:
    validated = ?validate(data)  # HOLE
    ...

# Context boosts:
# - Function name "create_user" → suggests CRUD validation
# - Return type Response → suggests raising HTTPException on error
# - Codebase pattern → 90% use Pydantic validation
# → Top suggestion: Pydantic model validation
```

---

## 8. Success Metrics

### 8.1 Hole Detection Accuracy

**Metric**: Percentage of ambiguities correctly identified

**Target**: 80%+ precision, 70%+ recall

**Measurement**:
- Human annotators label ambiguities in 100 test prompts
- Compare system detections to ground truth
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)

**Current Status**: Not measured (IR 0.8 has basic hole detection)

### 8.2 Suggestion Acceptance Rate

**Metric**: Percentage of holes filled with top suggestion (no modification)

**Target**: 60%+

**Measurement**:
- Track user actions: accept top, accept other, reject all
- Acceptance rate = accepts_top / total_holes
- By hole kind: Term (70%), Type (60%), Spec (50%), etc.

**Current Status**: No AI suggestions yet (IR 0.8)

### 8.3 Time to Fill All Holes

**Metric**: Time from IR generation to all holes resolved or deferred

**Target**: <5 minutes for typical request (3-5 holes)

**Measurement**:
- Timestamp IR creation
- Timestamp last hole fill/defer
- Median across sessions

**Current Status**: Not measured (manual hole filling in IR 0.8)

### 8.4 Constraint Propagation Latency

**Metric**: Time from hole fill to propagated updates shown in UI

**Target**: <100ms for 90% of fills

**Measurement**:
- Timestamp hole fill action
- Timestamp UI update complete
- P50, P90, P99 latencies

**Current Status**: No constraint propagation (IR 0.8)

### 8.5 Confidence Calibration (Brier Score)

**Metric**: Brier score measuring calibration quality

**Formula**: `BS = (1/N) * Σ(confidence - actual)^2`

**Target**: <0.2 (well-calibrated)

**Measurement**:
- For each suggestion with confidence C:
  - If accepted: actual = 1
  - If rejected: actual = 0
- Compute Brier score across all suggestions

**Current Status**: No confidence scores (IR 0.8)

### 8.6 User Satisfaction

**Metric**: Post-session survey rating

**Target**: 8/10+ on "holes helped me refine specs"

**Questions**:
1. Holes made ambiguities clear (1-10)
2. Suggestions were helpful (1-10)
3. Constraint propagation was useful (1-10)
4. I felt in control of the process (1-10)

**Current Status**: No user testing yet

### 8.7 Holes per Request

**Metric**: Average number of holes per IR generation

**Target**: 3-5 (sweet spot)
- Too few (<2): Spec might be over-constrained or trivial
- Too many (>10): Spec too vague, user overwhelmed

**Measurement**:
- Count holes after IR generation
- Average across sessions

**Current Status**: Not tracked systematically

### 8.8 Partial Evaluation Usage

**Metric**: Percentage of sessions using partial evaluation

**Target**: 30%+ of sessions with holes

**Measurement**:
- Track "Run with holes" action
- Measure by session

**Current Status**: Not available (IR 0.9 feature)

### 8.9 Hole Provenance Clarity

**Metric**: User comprehension of why holes exist

**Target**: 90%+ understand provenance

**Measurement**:
- Show provenance message
- Ask: "Do you understand why this hole exists?" (Y/N)
- Comprehension rate = Y / (Y+N)

**Current Status**: Basic provenance (IR 0.8), not user-tested

### 8.10 Round-Trip Fidelity (Reverse Mode)

**Metric**: Holes preserved in code → IR → code round trip

**Target**: 90%+ structural fidelity

**Measurement**:
- Start with code with TODOs
- Lift to IR (TODOs become holes)
- Fill holes
- Generate code
- Compare structure

**Current Status**: Reverse mode not implemented yet

---

## Appendix A: Real Examples from HOLE_INVENTORY.md

This appendix demonstrates typed holes in practice using the 19 architectural holes from lift-sys's meta-framework design.

### A.1 H1: ProviderAdapter (Implementation Hole)

**Type**: Implementation
**Kind**: `DSPyProvider`

**Hole Definition**:
```python
class ProviderAdapter:
    def __init__(
        self,
        modal_provider: ModalProvider,
        best_available_provider: ?BestAvailableProvider,  # HOLE
        config: ?ProviderConfig                           # HOLE
    ):
        ...
```

**Constraints**:
- Must preserve XGrammar constraints
- Must support async execution
- Must be compatible with DSPy.LM interface
- Should maintain current performance (<16s p50 latency)

**Dependencies**:
- Blocks: H8 (OptimizationAPI), H10 (OptimizationMetrics)
- Blocked by: H6 (NodeSignatureInterface)

**Suggestions**:
1. (85%) Anthropic Claude Sonnet 4.5 via API
2. (70%) OpenAI GPT-4 via LiteLLM
3. (60%) Google Gemini 1.5 Pro

**Status**: ✅ Resolved 2025-10-21 (Modal provider only, Best Available pending Phase 3)

### A.2 H6: NodeSignatureInterface (Interface Hole)

**Type**: Interface
**Kind**: `Protocol`

**Hole Definition**:
```python
class BaseNode(?Protocol):  # HOLE - what protocol?
    signature: Type[dspy.Signature]

    async def run(self, ctx: ?RunContext) -> ?NodeResult:  # HOLES
        ...
```

**Constraints**:
- Must be type-safe (generic over StateT)
- Must support async execution
- Must compose with Pydantic AI Graph
- Must preserve DSPy semantics

**Dependencies**:
- Blocks: H1, H2, H4, H5 (critical path!)
- Blocked by: None (ready to start)

**Suggestions**:
1. (90%) Generic BaseNode with signature composition
2. (60%) Mixin pattern with SignatureExecutor
3. (40%) Decorator pattern wrapping DSPy modules

**Status**: Ready for implementation (Phase 1, Week 1)

### A.3 H10: OptimizationMetrics (Specification Hole)

**Type**: Specification
**Kind**: `MetricDefinition`

**Hole Definition**:
```python
def ir_quality(predicted: IR, expected: IR) -> float:
    return ?quality_formula  # HOLE

def code_quality(predicted: str, expected: str, tests: list) -> float:
    return ?code_formula  # HOLE
```

**Constraints**:
- Must be measurable (computable from examples)
- Must be differentiable (or at least smooth)
- Must correlate with user satisfaction
- Should be composable (sub-metrics)

**Dependencies**:
- Blocks: H8 (OptimizationAPI), H17 (OptimizationValidation)
- Blocked by: H1 (ProviderAdapter)

**Suggestions**:
1. (85%) Weighted F1 score: `w1*intent_f1 + w2*sig_f1 + w3*code_f1`
2. (70%) Structural similarity: `tree_edit_distance(predicted, expected)`
3. (50%) Learned metric via preference model

**Status**: Blocked by H1 (Phase 3, Week 3 target)

### A.4 H17: OptimizationValidation (Validation Hole)

**Type**: Validation
**Kind**: `StatisticalTest`

**Hole Definition**:
```python
def validate_optimization(
    baseline: Pipeline,
    optimized: Pipeline,
    test_set: list[Example]
) -> ValidationResult:
    # HOLES:
    # - ?statistical_test : Which test? (t-test, bootstrap, Bayesian?)
    # - ?significance_threshold : float (0.05? 0.01?)
    # - ?effect_size : Method (Cohen's d? Hedges' g?)
    ...
```

**Constraints**:
- Must use statistical significance (p < 0.05)
- Must measure effect size (Cohen's d)
- Should use held-out test set
- Should account for variance

**Dependencies**:
- Blocks: Confidence in deployment
- Blocked by: H10 (OptimizationMetrics)

**Suggestions**:
1. (90%) Paired t-test + Cohen's d
2. (70%) Bootstrap confidence intervals
3. (50%) Bayesian A/B test

**Status**: Blocked by H10 (Phase 7, Week 7 target)

### A.5 Constraint Propagation Example

**Scenario**: Filling H1 (ProviderAdapter) propagates to H10 (OptimizationMetrics)

**Before H1 fill**:
```python
# H10 constraints (vague)
?ir_quality : (IR, IR) -> float
Constraints: [computable, correlates with user satisfaction]
```

**After H1 fill** (ProviderAdapter = ModalProvider with XGrammar):
```python
# H10 constraints (refined)
?ir_quality : (IR, IR) -> float
Constraints: [
    computable,
    correlates with user satisfaction,
    # NEW from H1:
    must_measure_xgrammar_constraint_violations,  # H1 uses XGrammar
    must_account_for_modal_latency,               # H1 uses Modal
    should_track_provider_costs                   # H1 has API costs
]

# New suggestions based on propagated constraints:
Suggestions:
1. (90%) weighted_f1 + xgrammar_penalty + latency_factor
2. (75%) structural_sim + constraint_violation_count
```

**Propagation mechanism**:
1. H1 resolved with Modal/XGrammar implementation
2. Dependency graph traversal finds H10 depends on H1
3. H10 constraints updated: "Must measure XGrammar quality"
4. H10 suggestions regenerated with new context
5. UI notifies user: "H10 constraints updated due to H1 resolution"

---

## Appendix B: Implementation Phases (IR 0.9 Roadmap)

### Phase 1: Core Types & Refinements (Months 1-3)
**Status**: 🔄 In Progress (Month 3 of 20)

**Deliverables**:
- ✅ Dependent types `Π(x:T).U`
- ✅ Refinement types `{x:T | φ}`
- ✅ Basic 4 hole kinds (term, type, spec, entity)
- 🔄 Database schema for semantic metadata

**Holes Status**:
- Basic hole detection: ✅
- Hole serialization: ✅
- Type annotations: ✅
- Constraints: 🔄 (SMT encoder pending)

### Phase 2: Solver Integration (Months 4-6)
**Status**: ⏳ Planned

**Deliverables**:
- SMT encoder (Z3)
- SAT/CSP backends
- Counterexample generation
- Validation pipeline

**Holes Impact**:
- Constraint checking via SMT
- Conflict detection
- Valid hole fits from solver models

### Phase 3: Hole Closures & Partial Evaluation (Months 7-10)
**Status**: ⏳ Planned (Q3 2025)

**Deliverables**:
- ✅ Add function holes (6 kinds total)
- ✅ Add module holes
- ✅ Hole closures `⟨Γ, ?h⟩`
- ✅ Partial evaluator
- ✅ Trace collection
- ✅ Fill-and-resume

**Holes Impact**:
- **Major feature**: Run programs with holes
- Collect traces showing value flows
- Discover constraints from usage
- Improve AI suggestions with examples

### Phase 4: Surface Syntax & LSP (Months 11-14)
**Status**: ⏳ Planned

**Deliverables**:
- Spec-IR grammar (Lark-based)
- LSP server (hover, completion)
- VS Code extension
- Ariadne-style diagnostics

**Holes Impact**:
- Hover shows hole details
- Autocomplete for hole fills
- Quick fixes for conflicts
- Inline suggestions

### Phase 5: Alignment & Provenance (Months 15-18)
**Status**: ⏳ Planned

**Deliverables**:
- Alignment maps (IntentSpec ↔ FuncSpec)
- Intent ledger (event log)
- Drift detection
- Provenance chains

**Holes Impact**:
- Hole provenance tracking
- Why does this hole exist?
- What decisions led to this?
- Audit trail for hole fills

### Phase 6: Production Readiness (Months 19-20)
**Status**: ⏳ Planned

**Deliverables**:
- Safety manifests (SBOM, SLSA)
- Telemetry (OpenTelemetry)
- Performance optimization
- Documentation

**Holes Impact**:
- Confidence calibration
- Suggestion quality metrics
- User satisfaction measurement

---

**Document Status**: Active
**Last Updated**: 2025-10-21
**Next Review**: Monthly or with major milestone changes
**Maintained By**: Product & Engineering Leadership
**Version History**: v1.0 (2025-10-21) - Initial comprehensive PRD
