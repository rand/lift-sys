# RFC: Constraint Solver Architecture for lift

**RFC Number**: RFC-003
**Title**: Tiered Constraint Solving Architecture
**Status**: Draft
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Related Documents**: RFC_LIFT_ARCHITECTURE.md, RFC_IR_CORE.md, IR_SPECIFICATION.md

---

## Executive Summary

### Purpose

This RFC specifies the **tiered constraint solver architecture** for lift's Intermediate Representation (IR). The constraint solver is a critical component that enables:

1. **Refinement type verification**: Checking that values satisfy predicates in types like `{x: Int | x >= 0 && x < 100}`
2. **Typed hole closure**: Finding valid expressions to fill holes based on type and semantic constraints
3. **Semantic correctness**: Verifying pre/postconditions, invariants, and effects
4. **Counterexample generation**: Producing concrete examples when constraints cannot be satisfied

### Design Philosophy

**Tiered by Complexity, Not Capability**: Different constraint problems have different computational characteristics. Rather than routing all problems through a single heavyweight solver (SMT), we use a **three-tier architecture**:

- **Tier 1 - CSP (Constraint Satisfaction Problems)**: Fast enumeration for discrete domains (editor-time hole suggestions)
- **Tier 2 - SAT (Propositional Satisfiability)**: Efficient boolean reasoning with CDCL algorithms
- **Tier 3 - SMT (Satisfiability Modulo Theories)**: Full theory reasoning (arithmetic, arrays, ADTs, strings)

**Incremental and Interactive**: Constraint solving happens **during development**, not just at compile time. We optimize for:
- Sub-second response for editor-time queries (hole suggestions, quick checks)
- Multi-second budgets for verification queries (refinement type checking)
- Incremental solving with push/pop for interactive refinement

**Explainable Results**: Every solver result (SAT/UNSAT) includes:
- **Models**: Concrete satisfying assignments for SAT results → hole fill candidates
- **UNSAT cores**: Minimal unsatisfiable subsets for UNSAT results → actionable error messages
- **Human-friendly explanations**: "This constraint fails because x=5 violates x < 5"

### Current Status

**Phase 2 (Architectural Holes Resolution)**: Planning complete, implementation pending Phase 3.

**Integration Points**:
- IR Core (RFC_IR_CORE.md): Constraint generation from refinement types and FuncSpecs
- LLM Orchestration: Solver results guide prompt generation and best-of-N ranking
- Session Storage: Solver proofs and counterexamples persisted for replay

**Target Metrics**:
- **Editor-time queries**: <500ms for hole suggestions (CSP tier)
- **Verification queries**: <5s for refinement type checks (SMT tier)
- **Success rate**: 90%+ satisfiable constraints resolved correctly
- **Explainability**: 80%+ of failures include actionable UNSAT cores

---

## Table of Contents

1. [Introduction & Constraint Solving Philosophy](#1-introduction--constraint-solving-philosophy)
2. [Tiered Architecture](#2-tiered-architecture)
3. [Z3 Integration (SMT)](#3-z3-integration-smt)
4. [SAT Solver Integration](#4-sat-solver-integration)
5. [CSP Solver Integration](#5-csp-solver-integration)
6. [Solver Selection Logic](#6-solver-selection-logic)
7. [Constraint Store Implementation](#7-constraint-store-implementation)
8. [Performance Optimization](#8-performance-optimization)
9. [Error Reporting](#9-error-reporting)
10. [Testing Strategy](#10-testing-strategy)

---

## 1. Introduction & Constraint Solving Philosophy

### 1.1 What Are Constraints in lift?

In lift's IR, **constraints** are logical predicates that specify requirements on program behavior. They arise from multiple sources:

**Source 1: Refinement Types**
```
{x: Int | x >= 0 && x < 100}
```
Predicate: `x >= 0 ∧ x < 100`

**Source 2: FuncSpec Pre/Postconditions**
```
def validate_age(age: Int) -> Bool
requires: age >= 0 && age <= 150
ensures: result == (age >= 18)
```
Predicates:
- Precondition: `age >= 0 ∧ age <= 150`
- Postcondition: `result = (age >= 18)`

**Source 3: Typed Holes with Constraints**
```
def compute_discount(price: ?p, customer: Customer) -> Float
where ?p :: {x: Float | x > 0.0}
```
Constraint on hole `?p`: Type must be `Float` AND satisfy `x > 0.0`

**Source 4: Invariants and Effects**
```
entity ShoppingCart:
  fields:
    items: List[Item]
    total: {x: Float | x == sum(items.map(_.price))}
  invariants:
    - total >= 0.0
    - items.length <= 100
```
Invariants: `total >= 0.0`, `items.length <= 100`, `total = sum(...)`

### 1.2 Why Constraint Solving?

**Problem**: Natural language is ambiguous. LLMs generate code that may violate semantic requirements even when syntactically correct.

**Example**: "Create a function to find the first even number in a list."

```python
# ❌ LLM Output (WRONG - finds LAST even number)
def find_first_even(numbers: List[int]) -> int | None:
    result = None
    for num in numbers:
        if num % 2 == 0:
            result = num  # Accumulates to LAST match
    return result

# ✅ Constraint-Verified Output (CORRECT)
def find_first_even(numbers: List[int]) -> int | None:
    for num in numbers:
        if num % 2 == 0:
            return num  # Early return on FIRST match
    return None
```

**How Constraints Prevent This Bug**:

1. **Constraint Detection** (from natural language "first"):
   ```python
   LoopBehaviorConstraint(
       search_type=LoopSearchType.FIRST_MATCH,
       requirement=LoopRequirement.EARLY_RETURN,
       description="Must return immediately on FIRST match"
   )
   ```

2. **Constraint Validation** (AST analysis):
   - First version: ❌ No return statement inside loop body
   - Second version: ✅ Return statement inside loop body

3. **Result**: LLM retries until constraint satisfied.

### 1.3 Design Goals

**G1. Decidability Over Completeness**: Prefer decidable fragments (linear arithmetic, quantifier-free formulas) to ensure termination. Fall back to heuristics for undecidable problems.

**G2. Incrementality**: Support push/pop operations to avoid re-solving entire constraint systems on small changes.

**G3. Explainability**: Every result must be interpretable by humans (developers) and machines (LLM retry prompts).

**G4. Performance**: Sub-second for editor interactions, multi-second budgets for batch verification.

**G5. Composability**: Solvers compose through the Constraint Store—share learned facts across tiers.

### 1.4 Non-Goals (Out of Scope)

**NG1. Full Theorem Proving**: We don't require proofs of deep mathematical properties. SMT checks suffice for most refinement types.

**NG2. Automated Proof Search**: No tactics or proof term synthesis (unlike Coq/Lean). Manual annotations required for complex properties.

**NG3. Distributed Solving**: Single-machine solvers. No parallel/distributed constraint solving infrastructure.

**NG4. Custom Solver Implementation**: Use existing, battle-tested solvers (Z3, MiniSat, python-constraint). Don't build from scratch.

---

## 2. Tiered Architecture

### 2.1 Overview

The constraint solver uses a **three-tier architecture** where problems are routed to the simplest solver capable of handling them:

```
┌─────────────────────────────────────────────────────────────┐
│                    Constraint Problem                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │ Solver Selection     │
              │ (complexity analysis)│
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ↓               ↓               ↓
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Tier 1     │  │  Tier 2     │  │  Tier 3     │
│  CSP        │  │  SAT        │  │  SMT (Z3)   │
│  (Fast)     │  │  (Medium)   │  │  (Powerful) │
└─────────────┘  └─────────────┘  └─────────────┘
      │                │                │
      └────────────────┴────────────────┘
                       │
                       ↓
              ┌──────────────────┐
              │  Result + Model  │
              │  or UNSAT Core   │
              └──────────────────┘
```

### 2.2 Tier 1: CSP (Constraint Satisfaction Problems)

**When to Use**:
- Discrete, finite domains (enumerations, small integer ranges)
- Hole closure candidate generation (≤100 candidates)
- Editor-time suggestions (<500ms latency requirement)
- No arithmetic theories required

**Solver**: `python-constraint` library

**Strengths**:
- Extremely fast for small domains
- Produces **all** solutions (useful for ranking candidates)
- Simple API, easy to debug

**Limitations**:
- Doesn't scale to large domains (>10^4 values)
- No theory reasoning (no real numbers, strings, arrays)
- Backtracking search—exponential worst-case

**Example Use Case**: Hole closure for enum types

```python
# IR: def get_status(user: User) -> ?status
# where ?status :: UserStatus (enum with 5 values)

from constraint import Problem

problem = Problem()
problem.addVariable("status", ["active", "inactive", "pending", "suspended", "deleted"])

# Constraint: user is admin → status must be "active" or "suspended"
if user.is_admin:
    problem.addConstraint(lambda s: s in ["active", "suspended"], ("status",))

solutions = problem.getSolutions()
# Result: [{"status": "active"}, {"status": "suspended"}]
# → Suggest these 2 values to user
```

**Performance**: O(d^n) where d = domain size, n = number of variables. Fast for d*n < 1000.

### 2.3 Tier 2: SAT (Boolean Satisfiability)

**When to Use**:
- Pure boolean constraints (no arithmetic)
- Configuration validation (feature models, dependency constraints)
- Reachability analysis (control flow graphs)
- Conjunction of boolean variables only

**Solver**: `pysat` library (MiniSat backend)

**Strengths**:
- Highly optimized CDCL (Conflict-Driven Clause Learning) algorithms
- Scales to millions of clauses
- Fast UNSAT core extraction

**Limitations**:
- Boolean variables only—no integers, reals, strings
- Requires encoding to CNF (Conjunctive Normal Form)
- No natural representation for arithmetic (`x + y < 10` requires bit-blasting)

**Example Use Case**: Feature dependency validation

```python
# IR: Feature flags with mutual exclusion constraints
# - "dark_mode" XOR "light_mode" (exactly one must be true)
# - "premium_features" → "user_authenticated" (implication)

from pysat.solvers import Minisat22

# Variables: dark_mode=1, light_mode=2, premium=3, authenticated=4
solver = Minisat22()

# XOR encoding: (dark_mode ∨ light_mode) ∧ ¬(dark_mode ∧ light_mode)
solver.add_clause([1, 2])       # At least one
solver.add_clause([-1, -2])     # At most one

# Implication: premium → authenticated
solver.add_clause([-3, 4])      # ¬premium ∨ authenticated

if solver.solve():
    model = solver.get_model()  # [1, -2, -3, 4] = dark_mode=T, light_mode=F, premium=F, auth=T
else:
    core = solver.get_core()    # Minimal UNSAT subset
```

**Performance**: Modern SAT solvers handle 10^6 clauses in seconds. CDCL makes typical cases sub-linear.

### 2.4 Tier 3: SMT (Satisfiability Modulo Theories)

**When to Use**:
- Arithmetic constraints (linear/nonlinear, integers/reals)
- Dependent types (type depends on runtime value)
- Refinement types (`{x: T | φ}` where `φ` uses arithmetic)
- Array reasoning, algebraic datatypes, string constraints

**Solver**: Z3 (Microsoft Research, de facto standard)

**Strengths**:
- Rich theory support (Int, Real, BitVec, Array, ADT, String, etc.)
- Quantifier reasoning (limited)
- Incremental solving with push/pop
- Model and UNSAT core extraction

**Limitations**:
- Slower than SAT for boolean-only problems
- Quantifiers may not terminate (incomplete for ∃∀ formulas)
- String theory still maturing (performance varies)

**Example Use Case**: Refinement type verification

```python
from z3 import Int, Solver, sat

# IR: {x: Int | x >= 0 && x < 100}
x = Int('x')
solver = Solver()
solver.add(x >= 0)
solver.add(x < 100)

# Check satisfiability
if solver.check() == sat:
    model = solver.model()
    print(f"Example: x = {model[x]}")  # x = 0 (or any value in [0, 99])
else:
    core = solver.unsat_core()
```

**Performance**: Linear arithmetic queries typically <100ms. Nonlinear arithmetic and quantifiers may take seconds or timeout.

### 2.5 Tier Interaction

**Tier Escalation**: Start with simplest solver, escalate if needed.

```python
def solve_constraint(constraint: Constraint) -> SolverResult:
    # Try CSP first (if applicable)
    if is_discrete_domain(constraint) and domain_size(constraint) < 1000:
        result = csp_solve(constraint)
        if result.status == SolverStatus.SOLVED:
            return result

    # Try SAT next (if boolean-only)
    if is_boolean_only(constraint):
        result = sat_solve(constraint)
        if result.status == SolverStatus.SOLVED:
            return result

    # Escalate to SMT (most powerful)
    return smt_solve(constraint)
```

**Shared Learning**: Facts proven at one tier can be reused at higher tiers.

Example: CSP proves `status ∈ {active, suspended}` → SMT inherits this as constraint `status = active ∨ status = suspended`.

---

## 3. Z3 Integration (SMT)

### 3.1 SMT-LIB Encoding

Z3 accepts constraints in **SMT-LIB format** (standardized S-expression syntax). We encode IR predicates to SMT-LIB programmatically.

**Example 1: Refinement Type**

IR:
```
{age: Int | age >= 0 && age <= 150}
```

SMT-LIB:
```smt2
(declare-const age Int)
(assert (>= age 0))
(assert (<= age 150))
(check-sat)
(get-model)
```

Python (z3-solver library):
```python
from z3 import Int, Solver, And

age = Int('age')
solver = Solver()
solver.add(And(age >= 0, age <= 150))

if solver.check() == sat:
    print(solver.model())  # [age = 0] (example model)
```

**Example 2: Dependent Type**

IR:
```
def create_array(n: {x: Int | x > 0}) -> Array[Int, n]
```

Constraint: `n > 0` (array size must be positive)

SMT-LIB:
```smt2
(declare-const n Int)
(assert (> n 0))
(check-sat)
```

Python:
```python
n = Int('n')
solver = Solver()
solver.add(n > 0)
assert solver.check() == sat  # Always satisfiable
```

**Example 3: Postcondition Verification**

IR:
```
def abs_value(x: Int) -> {result: Int | result >= 0}
ensures: result >= 0
```

Verification query (prove postcondition):
```smt2
(declare-const x Int)
(declare-const result Int)

; Definition: result = abs(x)
(assert (ite (>= x 0) (= result x) (= result (- x))))

; Check: Does result >= 0 always hold?
(assert (not (>= result 0)))  ; Negate postcondition
(check-sat)  ; Should be UNSAT (postcondition always true)
```

Python:
```python
x = Int('x')
result = Int('result')
solver = Solver()

# Definition of abs
solver.add(If(x >= 0, result == x, result == -x))

# Negate postcondition (try to find counterexample)
solver.add(Not(result >= 0))

if solver.check() == unsat:
    print("Postcondition verified ✓")
else:
    print(f"Counterexample: {solver.model()}")
```

### 3.2 Theory Selection

Z3 supports multiple **theories** (sets of predicates and axioms). Choose the minimal theory for performance.

| Theory | Use Case | Example Predicate | Performance |
|--------|----------|-------------------|-------------|
| **LIA** (Linear Integer Arithmetic) | Integer arithmetic without multiplication | `2*x + 3*y < 10` | Fast (polynomial) |
| **NIA** (Nonlinear Integer Arithmetic) | Integer multiplication, exponentiation | `x*y = 12` | Slow (may timeout) |
| **LRA** (Linear Real Arithmetic) | Real number arithmetic, no multiplication | `0.5*x + 0.3*y <= 1.0` | Fast (simplex) |
| **NRA** (Nonlinear Real Arithmetic) | Real multiplication, division | `x^2 + y^2 < 1.0` | Very slow (CAD algorithm) |
| **BitVec** | Fixed-width bit vectors | `bvadd(x, y) = 0b1010` | Fast (bit-blasting) |
| **Array** | Array reads/writes | `select(store(a, i, v), i) = v` | Medium (axioms) |
| **ADT** | Algebraic datatypes (lists, trees) | `is-cons(x) ⇒ head(x) = 5` | Medium |
| **String** | String operations | `str.contains(s, "http")` | Slow (still maturing) |

**Decision Tree**:

```python
def select_theory(constraint: Constraint) -> Z3Theory:
    if uses_strings(constraint):
        return Z3Theory.STRING
    elif uses_arrays(constraint):
        return Z3Theory.ARRAY
    elif uses_multiplication(constraint):
        if uses_reals(constraint):
            return Z3Theory.NRA  # Warning: slow
        else:
            return Z3Theory.NIA  # Warning: may timeout
    elif uses_reals(constraint):
        return Z3Theory.LRA  # Fast
    else:
        return Z3Theory.LIA  # Fastest
```

### 3.3 Incremental Solving

**Problem**: Re-solving from scratch on every constraint change is wasteful.

**Solution**: Use Z3's **push/pop** to incrementally add/remove constraints.

**Example**: Interactive refinement session

```python
from z3 import Solver, Int

solver = Solver()
x = Int('x')

# Initial constraint: x > 0
solver.add(x > 0)
print(solver.check())  # sat

# User refines: "x must also be even"
solver.push()  # Save current state
solver.add(x % 2 == 0)
print(solver.check())  # sat (x=2, 4, 6, ...)

# User refines: "x must be < 10"
solver.push()
solver.add(x < 10)
print(solver.check())  # sat (x=2, 4, 6, 8)

# User backtracks: remove "x < 10"
solver.pop()
print(solver.check())  # sat (x=2, 4, 6, 8, 10, 12, ...)
```

**Performance**: Push/pop is O(1) for stack operations. Avoids re-solving shared constraints.

### 3.4 Quantifier Handling

**Challenge**: Quantifiers (∀, ∃) make SMT undecidable in general.

**Strategies**:

1. **Avoid Quantifiers**: Encode using quantifier-free formulas when possible.

   Example: Instead of `∀i. 0 <= i < len(arr) ⇒ arr[i] >= 0`
   Use: Explicit constraints for each index (if length is small/known)

2. **Bounded Quantification**: Instantiate quantifiers up to a fixed bound.

   Example: `∀i ∈ [0, 10). arr[i] >= 0` becomes:
   ```python
   And([arr[i] >= 0 for i in range(10)])
   ```

3. **E-Matching**: Z3's default strategy. Heuristically instantiate quantifiers based on patterns.

   SMT-LIB:
   ```smt2
   (assert (forall ((i Int))
       (! (=> (and (>= i 0) (< i 10)) (>= (select arr i) 0))
          :pattern ((select arr i)))))
   ```

4. **Timeout and Fallback**: If quantified query doesn't terminate in 5s, fall back to heuristics or admit "unknown".

**Recommendation**: Prefer quantifier-free fragments (LIA, LRA, Array theory without quantifiers). Use quantifiers sparingly with patterns.

### 3.5 Model Extraction

When Z3 returns **sat**, extract a **model** (concrete variable assignment).

```python
from z3 import Int, Solver, sat

solver = Solver()
x = Int('x')
y = Int('y')
solver.add(x + y == 10)
solver.add(x > 0)
solver.add(y > 0)

if solver.check() == sat:
    model = solver.model()
    print(f"x = {model[x]}, y = {model[y]}")  # x = 1, y = 9 (example)

    # Use model as hole fill candidate
    hole_fill = {"x": model[x].as_long(), "y": model[y].as_long()}
```

**Use Cases**:
- **Hole closure**: Model provides concrete value for typed hole
- **Test case generation**: Model is a valid input satisfying preconditions
- **Debugging**: Model shows why constraint is satisfiable

### 3.6 UNSAT Core Extraction

When Z3 returns **unsat**, extract **UNSAT core** (minimal subset of constraints causing contradiction).

```python
from z3 import Int, Solver, Bool

solver = Solver()
x = Int('x')

# Named assertions (for core tracking)
c1 = Bool('c1')
c2 = Bool('c2')
c3 = Bool('c3')

solver.assert_and_track(x > 10, c1)
solver.assert_and_track(x < 5, c2)
solver.assert_and_track(x >= 0, c3)

if solver.check() == unsat:
    core = solver.unsat_core()
    print(f"Conflicting constraints: {core}")  # [c1, c2] (x > 10 and x < 5 are inconsistent)
```

**Use Cases**:
- **Error reporting**: Show user which constraints conflict
- **LLM retry prompts**: "The constraint 'x > 10' conflicts with 'x < 5'. Please revise."
- **Debugging**: Identify root cause of UNSAT

---

## 4. SAT Solver Integration

### 4.1 Boolean Constraints and CNF Encoding

SAT solvers require constraints in **CNF (Conjunctive Normal Form)**: conjunction of disjunctions.

**CNF**: `(a ∨ b) ∧ (¬a ∨ c) ∧ (b ∨ ¬c)`

**Encoding Process**:

1. **Assign boolean variables** to propositions
2. **Translate formula** to CNF using:
   - Tseitin transformation (for complex formulas)
   - Direct encoding (for simple formulas)

**Example**: XOR constraint `a ⊕ b` (exactly one true)

Direct encoding:
```
a ⊕ b = (a ∨ b) ∧ ¬(a ∧ b)
      = (a ∨ b) ∧ (¬a ∨ ¬b)
```

CNF clauses:
- `(a ∨ b)` — at least one true
- `(¬a ∨ ¬b)` — at most one true

Python:
```python
from pysat.solvers import Minisat22

solver = Minisat22()
solver.add_clause([1, 2])      # a ∨ b
solver.add_clause([-1, -2])    # ¬a ∨ ¬b

if solver.solve():
    model = solver.get_model()  # [1, -2] = a=true, b=false (one solution)
```

### 4.2 Tseitin Transformation

**Problem**: Complex formulas (nested AND/OR/NOT) explode in size when converted to CNF naively.

**Solution**: **Tseitin transformation** introduces auxiliary variables to keep CNF linear in size.

**Example**: `(a ∧ b) ∨ (c ∧ d)`

Naive CNF: 4 clauses, exponential growth for deeper nesting

Tseitin:
1. Introduce `t1 = a ∧ b`, `t2 = c ∧ d`
2. Encode: `t1 ∨ t2` (final result), `t1 ⇔ (a ∧ b)`, `t2 ⇔ (c ∧ d)`

CNF (6 clauses, linear):
```
(t1 ∨ t2)               # Final disjunction
(¬t1 ∨ a)  (¬t1 ∨ b)   # t1 ⇒ a ∧ b
(¬a ∨ ¬b ∨ t1)         # a ∧ b ⇒ t1
(¬t2 ∨ c)  (¬t2 ∨ d)   # t2 ⇒ c ∧ d
(¬c ∨ ¬d ∨ t2)         # c ∧ d ⇒ t2
```

**Implementation**:
```python
from pysat.formula import CNF
from pysat.solvers import Solver

# Build CNF using Tseitin (automatic in pysat)
cnf = CNF()
# Variables: a=1, b=2, c=3, d=4, t1=5, t2=6

cnf.append([5, 6])          # t1 ∨ t2
cnf.append([-5, 1])         # ¬t1 ∨ a
cnf.append([-5, 2])         # ¬t1 ∨ b
cnf.append([-1, -2, 5])     # ¬a ∨ ¬b ∨ t1
cnf.append([-6, 3])         # Similar for t2
cnf.append([-6, 4])
cnf.append([-3, -4, 6])

solver = Solver(bootstrap_with=cnf)
print(solver.solve())  # True
```

### 4.3 CDCL Algorithm

Modern SAT solvers use **CDCL (Conflict-Driven Clause Learning)**.

**Key Ideas**:
1. **DPLL search** with backtracking (try assignments, backtrack on conflicts)
2. **Clause learning**: When conflict occurs, learn a new clause preventing that conflict
3. **Non-chronological backtracking**: Jump back to decision level where learned clause becomes unit
4. **Watched literals**: Efficient propagation without scanning all clauses

**Why It Matters**: CDCL makes SAT solving practical for millions of variables. Empirically near-linear for typical cases (though worst-case exponential).

**Implementation**: Use `pysat` (Python bindings to MiniSat, Glucose, etc.)—CDCL is built-in.

```python
from pysat.solvers import Glucose3

solver = Glucose3()
# Add clauses...
solver.solve()  # Uses CDCL internally
```

### 4.4 Use Cases in lift

**UC1: Feature Model Validation**

Check if feature flag configuration is valid.

```python
# Features: A, B, C
# Constraints: A ⇒ B (if A enabled, B must be enabled)
#              B ⇒ ¬C (if B enabled, C must be disabled)

solver = Minisat22()
solver.add_clause([-1, 2])   # A ⇒ B
solver.add_clause([-2, -3])  # B ⇒ ¬C

# Check if A=true, C=true is valid
solver.add_clause([1])   # A=true
solver.add_clause([3])   # C=true

if solver.solve():
    print("Valid configuration")
else:
    print("Invalid: A ⇒ B ⇒ ¬C, but C=true")
```

**UC2: Control Flow Reachability**

Check if a code path is reachable given branch conditions.

```python
# if (a): branch1
# elif (b): branch2
# else: branch3

# Is branch3 reachable? (¬a ∧ ¬b must be satisfiable)
solver = Minisat22()
solver.add_clause([-1])  # a=false
solver.add_clause([-2])  # b=false
print(solver.solve())  # True → branch3 reachable
```

---

## 5. CSP Solver Integration

### 5.1 Discrete Domains and Variables

CSP solvers work with **variables** and **finite domains**.

**Example**: Assign colors to graph nodes (no adjacent nodes same color)

```python
from constraint import Problem

problem = Problem()

# Variables: nodes A, B, C
# Domain: {red, blue, green}
problem.addVariable("A", ["red", "blue", "green"])
problem.addVariable("B", ["red", "blue", "green"])
problem.addVariable("C", ["red", "blue", "green"])

# Constraints: A != B, B != C, A != C (edges in graph)
problem.addConstraint(lambda a, b: a != b, ("A", "B"))
problem.addConstraint(lambda b, c: b != c, ("B", "C"))
problem.addConstraint(lambda a, c: a != c, ("A", "C"))

solutions = problem.getSolutions()
print(solutions)  # [{'A': 'red', 'B': 'blue', 'C': 'green'}, ...]
```

### 5.2 Hole Closure Candidate Enumeration

**Use Case**: Find all valid closures for a typed hole.

**Example**:
```
def get_discount(customer: Customer, purchase_amount: Float) -> ?discount_type
where ?discount_type :: DiscountType (enum with 5 values)
```

Constraints:
- `customer.is_premium ⇒ discount_type ∈ {Gold, Platinum}`
- `purchase_amount > 1000 ⇒ discount_type != None`

CSP encoding:
```python
from constraint import Problem, FunctionConstraint

problem = Problem()
problem.addVariable("discount_type", ["None", "Silver", "Gold", "Platinum", "Special"])

# Constraint 1: Premium customers get Gold or Platinum
if customer.is_premium:
    problem.addConstraint(lambda d: d in ["Gold", "Platinum"], ("discount_type",))

# Constraint 2: Large purchases get non-None discount
if purchase_amount > 1000:
    problem.addConstraint(lambda d: d != "None", ("discount_type",))

solutions = problem.getSolutions()
# Result: [{"discount_type": "Gold"}, {"discount_type": "Platinum"}]
# → Suggest these 2 options to user
```

### 5.3 Editor-Time Pruning

**Goal**: Provide hole suggestions in <500ms while user types.

**Strategy**:
1. Maintain **pre-computed domain** for each hole (all in-scope values)
2. On each keystroke/edit, **incrementally prune** domain based on new constraints
3. Return top-k ranked suggestions

**Example**:

```python
class HoleSuggester:
    def __init__(self, hole: TypedHole):
        self.hole = hole
        self.domain = self._compute_initial_domain()
        self.constraints = []

    def _compute_initial_domain(self) -> list[str]:
        # All in-scope values with compatible type
        return [v for v in scope if typeof(v) == self.hole.type]

    def add_constraint(self, constraint: Constraint):
        self.constraints.append(constraint)
        self.domain = [v for v in self.domain if satisfies(v, constraint)]

    def suggest(self, k: int = 5) -> list[Suggestion]:
        # Rank by: type compatibility, usage frequency, proximity
        ranked = rank_candidates(self.domain, self.hole)
        return ranked[:k]
```

**Performance**: O(n) pruning per constraint, where n = domain size. For n < 1000, <10ms.

### 5.4 Constraint Propagation

**Idea**: Use constraint propagation to shrink domains before search.

**Arc Consistency (AC-3)**: For each constraint, remove values that cannot participate in any solution.

**Example**:
```
Variables: x ∈ {1, 2, 3}, y ∈ {2, 3, 4}
Constraint: x < y

AC-3 propagation:
- x=3 impossible (no y > 3 in domain) → x ∈ {1, 2}
- y=2 impossible (no x < 2 in domain) → y ∈ {3, 4}

Reduced domains: x ∈ {1, 2}, y ∈ {3, 4}
```

**Implementation**: `python-constraint` includes AC-3 by default.

```python
from constraint import Problem

problem = Problem()
problem.addVariable("x", [1, 2, 3])
problem.addVariable("y", [2, 3, 4])
problem.addConstraint(lambda x, y: x < y, ("x", "y"))

# AC-3 runs automatically during getSolutions()
solutions = problem.getSolutions()
# Returns: [{'x': 1, 'y': 2}, {'x': 1, 'y': 3}, {'x': 1, 'y': 4},
#           {'x': 2, 'y': 3}, {'x': 2, 'y': 4}]
```

---

## 6. Solver Selection Logic

### 6.1 Decision Tree

```python
from enum import Enum
from dataclasses import dataclass

class SolverTier(Enum):
    CSP = "csp"
    SAT = "sat"
    SMT = "smt"

@dataclass
class SolverSelection:
    tier: SolverTier
    rationale: str
    expected_latency_ms: int

def select_solver(constraint: Constraint, context: SolverContext) -> SolverSelection:
    """
    Select appropriate solver tier based on constraint characteristics.

    Decision criteria:
    1. Domain type and size
    2. Theory requirements
    3. Latency requirements (editor-time vs batch)
    4. Complexity analysis
    """

    # Tier 1: CSP (fastest, most restricted)
    if (
        constraint.is_discrete_domain() and
        constraint.domain_size() < 1000 and
        not constraint.uses_arithmetic() and
        context.latency_requirement == LatencyRequirement.INTERACTIVE  # <500ms
    ):
        return SolverSelection(
            tier=SolverTier.CSP,
            rationale="Discrete domain with <1000 values, no arithmetic",
            expected_latency_ms=50
        )

    # Tier 2: SAT (fast, boolean-only)
    if (
        constraint.is_boolean_only() and
        not constraint.uses_arithmetic() and
        constraint.cnf_size() < 100000  # clauses
    ):
        return SolverSelection(
            tier=SolverTier.SAT,
            rationale="Pure boolean constraint, no arithmetic needed",
            expected_latency_ms=200
        )

    # Tier 3: SMT (most powerful, slowest)
    return SolverSelection(
        tier=SolverTier.SMT,
        rationale=f"Requires theory: {constraint.required_theories()}",
        expected_latency_ms=2000
    )
```

### 6.2 Complexity Analysis

**Heuristics for Constraint Complexity**:

```python
def analyze_complexity(constraint: Constraint) -> ComplexityEstimate:
    score = 0

    # Factor 1: Number of variables
    score += len(constraint.variables) * 10

    # Factor 2: Domain sizes (exponential in worst case)
    max_domain = max(len(domain) for domain in constraint.domains.values())
    score += math.log2(max_domain + 1) * 50

    # Factor 3: Theory complexity
    if constraint.uses_nonlinear_arithmetic():
        score += 1000  # Very expensive
    elif constraint.uses_linear_arithmetic():
        score += 100
    elif constraint.uses_quantifiers():
        score += 500  # Expensive, may not terminate

    # Factor 4: Constraint arity (number of variables per constraint)
    avg_arity = sum(c.arity for c in constraint.clauses) / len(constraint.clauses)
    score += avg_arity * 20

    return ComplexityEstimate(
        score=score,
        expected_runtime_class="polynomial" if score < 500 else "exponential"
    )
```

### 6.3 Latency Requirements

Different use cases have different latency budgets:

| Use Case | Latency Budget | Solver Tier | Strategy |
|----------|---------------|-------------|----------|
| **Editor-time hole suggestion** | <500ms | CSP | Pre-computed domains, incremental pruning |
| **Quick type check** | <2s | SAT or SMT (LIA) | Cached results, simple queries |
| **Refinement type verification** | <5s | SMT (LIA/LRA) | Full verification, incremental |
| **Batch verification (CI)** | <60s | SMT (all theories) | Parallel queries, no timeout |

**Timeout Handling**:
```python
import timeout_decorator

@timeout_decorator.timeout(5)  # 5 second timeout
def verify_constraint(constraint: Constraint) -> VerificationResult:
    solver = select_solver(constraint)
    return solver.check()

try:
    result = verify_constraint(constraint)
except timeout_decorator.TimeoutError:
    return VerificationResult(
        status=VerificationStatus.UNKNOWN,
        message="Solver timeout after 5s. Constraint too complex or requires manual proof."
    )
```

### 6.4 Fallback Strategy

**Problem**: Solver may fail (timeout, out of memory, unsupported theory).

**Fallback Chain**:
1. **Try selected solver** (e.g., SMT with NRA for `x^2 + y^2 < 1`)
2. **Simplify constraint** (e.g., bound variables: `x ∈ [-10, 10]`)
3. **Use heuristic** (e.g., random sampling, counterexample-guided search)
4. **Admit "unknown"** and request manual annotation

**Example**:
```python
def solve_with_fallback(constraint: Constraint) -> SolverResult:
    # Attempt 1: Full solver
    try:
        return smt_solve(constraint, timeout=5)
    except SolverTimeout:
        pass

    # Attempt 2: Bounded approximation
    try:
        bounded = bound_variables(constraint, range=(-1000, 1000))
        return smt_solve(bounded, timeout=10)
    except SolverTimeout:
        pass

    # Attempt 3: Heuristic (counterexample search)
    for _ in range(1000):
        assignment = random_assignment(constraint)
        if satisfies(assignment, constraint):
            return SolverResult(status=SolverStatus.SAT, model=assignment)

    # Give up
    return SolverResult(
        status=SolverStatus.UNKNOWN,
        message="Unable to solve. Please simplify constraint or provide manual proof."
    )
```

---

## 7. Constraint Store Implementation

### 7.1 Data Structure (𝒞)

The **Constraint Store** (𝒞) is a global data structure maintaining all active constraints, their dependencies, and solver state.

```python
from dataclasses import dataclass, field
from typing import Dict, List, Set

@dataclass
class ConstraintStore:
    """
    Global constraint store (𝒞) for IR session.

    Responsibilities:
    - Track all active constraints
    - Maintain dependency graph (which holes depend on which constraints)
    - Cache solver results
    - Propagate learned facts across tiers
    """

    # Core state
    constraints: Dict[ConstraintID, Constraint] = field(default_factory=dict)
    dependencies: Dict[HoleID, Set[ConstraintID]] = field(default_factory=dict)

    # Solver state
    solver_cache: Dict[ConstraintID, SolverResult] = field(default_factory=dict)
    learned_facts: List[Constraint] = field(default_factory=list)
    blocked_constraints: Dict[ConstraintID, BlockReason] = field(default_factory=dict)

    # Propagation state
    propagation_queue: List[ConstraintID] = field(default_factory=list)

    def add_constraint(self, constraint: Constraint, depends_on: Set[HoleID]) -> ConstraintID:
        """Add new constraint and track dependencies."""
        cid = generate_constraint_id()
        self.constraints[cid] = constraint

        for hole in depends_on:
            if hole not in self.dependencies:
                self.dependencies[hole] = set()
            self.dependencies[hole].add(cid)

        self.propagation_queue.append(cid)
        return cid

    def close_hole(self, hole: HoleID, fill: Expression):
        """
        Close a hole with a fill expression.
        Triggers constraint propagation for all dependent constraints.
        """
        # Substitute fill into dependent constraints
        for cid in self.dependencies.get(hole, set()):
            constraint = self.constraints[cid]
            updated = constraint.substitute(hole, fill)
            self.constraints[cid] = updated

            # Invalidate cache
            if cid in self.solver_cache:
                del self.solver_cache[cid]

            # Re-queue for checking
            self.propagation_queue.append(cid)

        # Remove hole from dependencies
        del self.dependencies[hole]

    def propagate(self):
        """
        Run constraint propagation algorithm.
        Processes queue until fixpoint reached.
        """
        while self.propagation_queue:
            cid = self.propagation_queue.pop(0)
            constraint = self.constraints[cid]

            # Skip if already solved
            if cid in self.solver_cache:
                continue

            # Solve constraint
            result = self._solve_constraint(constraint)
            self.solver_cache[cid] = result

            # Learn new facts
            if result.status == SolverStatus.SAT and result.learned_facts:
                self.learned_facts.extend(result.learned_facts)
                # Add learned facts as new constraints
                for fact in result.learned_facts:
                    self.add_constraint(fact, depends_on=set())

    def _solve_constraint(self, constraint: Constraint) -> SolverResult:
        """Dispatch to appropriate solver tier."""
        selection = select_solver(constraint, context=self.context)

        if selection.tier == SolverTier.CSP:
            return csp_solve(constraint)
        elif selection.tier == SolverTier.SAT:
            return sat_solve(constraint)
        else:
            return smt_solve(constraint)
```

### 7.2 Propagation Algorithm

**Goal**: Derive new constraints from existing ones (similar to type inference).

**Algorithm** (simplified Worklist algorithm):

```python
def propagate_constraints(store: ConstraintStore):
    """
    Constraint propagation with worklist algorithm.

    Invariants:
    - Queue contains constraints that may have changed
    - Cache contains results for unchanged constraints
    - Learned facts monotonically increase
    """

    while store.propagation_queue:
        cid = store.propagation_queue.pop(0)
        constraint = store.constraints[cid]

        # Check if constraint can be simplified using learned facts
        simplified = apply_learned_facts(constraint, store.learned_facts)

        if simplified != constraint:
            store.constraints[cid] = simplified
            constraint = simplified

        # Solve if not in cache
        if cid not in store.solver_cache:
            result = solve_with_timeout(constraint, timeout=5)
            store.solver_cache[cid] = result

            # If UNSAT, mark as blocked
            if result.status == SolverStatus.UNSAT:
                store.blocked_constraints[cid] = BlockReason(
                    unsat_core=result.unsat_core,
                    explanation=result.explanation
                )

            # If SAT, learn facts from model
            elif result.status == SolverStatus.SAT:
                facts = extract_facts_from_model(result.model, constraint)
                store.learned_facts.extend(facts)

                # Re-queue dependent constraints (may simplify)
                for hole in constraint.free_holes():
                    if hole in store.dependencies:
                        store.propagation_queue.extend(store.dependencies[hole])
```

**Example**: Type inference propagation

```
Initial constraints:
  C1: typeof(?x) = Int ∨ typeof(?x) = String
  C2: typeof(?y) = typeof(?x)
  C3: ?y + 5  (requires typeof(?y) = Int)

Propagation:
1. Solve C3 → typeof(?y) = Int
2. Learn fact: typeof(?y) = Int
3. Substitute into C2 → typeof(?x) = Int
4. Substitute into C1 → typeof(?x) = Int (C1 now trivially satisfied)
5. Fixpoint reached
```

### 7.3 Blocked Constraints

**Problem**: Some constraints may be unsatisfiable due to conflicting requirements.

**Example**:
```
C1: x > 10
C2: x < 5
```

**Solution**: Mark as **blocked** with UNSAT core for user feedback.

```python
@dataclass
class BlockReason:
    unsat_core: List[ConstraintID]
    explanation: str
    suggested_fix: str | None = None

def handle_blocked_constraint(cid: ConstraintID, store: ConstraintStore):
    """
    Handle unsatisfiable constraint.

    Strategies:
    1. Report to user with UNSAT core
    2. Suggest relaxing one constraint
    3. If hole-dependent, mark hole as "needs manual attention"
    """

    reason = store.blocked_constraints[cid]
    constraint = store.constraints[cid]

    # Generate human-friendly explanation
    explanation = f"Constraint '{constraint.description}' is unsatisfiable.\n"
    explanation += f"Conflicting requirements:\n"

    for core_cid in reason.unsat_core:
        core_constraint = store.constraints[core_cid]
        explanation += f"  - {core_constraint.description}\n"

    # Suggest fix: relax one constraint
    if len(reason.unsat_core) == 2:
        c1 = store.constraints[reason.unsat_core[0]]
        c2 = store.constraints[reason.unsat_core[1]]
        explanation += f"\nSuggestion: Relax either '{c1.description}' or '{c2.description}'"

    return ErrorReport(
        severity=ErrorSeverity.ERROR,
        message=explanation,
        suggested_fix=reason.suggested_fix
    )
```

---

## 8. Performance Optimization

### 8.1 Caching Strategy

**Problem**: Repeated solver queries for same constraints are wasteful.

**Solution**: Multi-level cache hierarchy.

```python
from functools import lru_cache
import hashlib

class SolverCache:
    """
    Three-level cache:
    1. In-memory LRU (fast, limited size)
    2. Session-level SQLite (persistent across API calls)
    3. Global Redis (shared across users for common queries)
    """

    def __init__(self):
        self.memory_cache = {}  # LRU with max 1000 entries
        self.session_db = SessionDB()
        self.global_cache = RedisCache()

    def get(self, constraint: Constraint) -> SolverResult | None:
        key = self._hash_constraint(constraint)

        # Level 1: Memory
        if key in self.memory_cache:
            return self.memory_cache[key]

        # Level 2: Session DB
        result = self.session_db.get_solver_result(key)
        if result:
            self.memory_cache[key] = result  # Promote to L1
            return result

        # Level 3: Global cache (for common queries like "x >= 0")
        result = self.global_cache.get(key)
        if result:
            self.memory_cache[key] = result
            self.session_db.store_solver_result(key, result)
            return result

        return None

    def store(self, constraint: Constraint, result: SolverResult):
        key = self._hash_constraint(constraint)
        self.memory_cache[key] = result
        self.session_db.store_solver_result(key, result)

        # Only cache to global if query is "common" (appears in multiple sessions)
        if self._is_common(constraint):
            self.global_cache.set(key, result)

    def _hash_constraint(self, constraint: Constraint) -> str:
        """Canonical hash for constraint (modulo variable renaming)."""
        normalized = normalize_constraint(constraint)  # Alpha-rename variables
        return hashlib.sha256(str(normalized).encode()).hexdigest()
```

**Cache Hit Rates** (target):
- Memory cache: 60% (recently used queries)
- Session cache: 30% (queries from earlier in session)
- Global cache: 5% (common patterns like `x >= 0`, `length(list) >= 0`)
- Cold queries: 5%

### 8.2 Incremental Solving

**Z3 Push/Pop**: Already covered in §3.3.

**SAT Incremental Mode**: Some SAT solvers (e.g., Glucose) support incremental mode.

```python
from pysat.solvers import Glucose3

solver = Glucose3()

# Initial clauses
solver.add_clause([1, 2])
solver.add_clause([-1, 3])

# Solve
print(solver.solve())  # True

# Add more clauses (incremental)
solver.add_clause([-2, -3])

# Re-solve (reuses learned clauses)
print(solver.solve())  # Faster than starting fresh
```

**Benefits**:
- Reuses learned clauses from previous solve
- Avoids re-parsing/re-encoding
- 2-10x speedup for iterative refinement

### 8.3 Timeout Management

**Strategy**: Different timeouts for different latency tiers.

```python
from dataclasses import dataclass
from enum import Enum

class LatencyTier(Enum):
    INTERACTIVE = "interactive"      # <500ms
    RESPONSIVE = "responsive"        # <2s
    BATCH = "batch"                  # <60s

@dataclass
class TimeoutConfig:
    tier: LatencyTier
    timeout_ms: int
    fallback: str  # What to do on timeout

TIMEOUT_CONFIGS = {
    LatencyTier.INTERACTIVE: TimeoutConfig(
        tier=LatencyTier.INTERACTIVE,
        timeout_ms=500,
        fallback="return cached or heuristic result"
    ),
    LatencyTier.RESPONSIVE: TimeoutConfig(
        tier=LatencyTier.RESPONSIVE,
        timeout_ms=2000,
        fallback="simplify constraint and retry"
    ),
    LatencyTier.BATCH: TimeoutConfig(
        tier=LatencyTier.BATCH,
        timeout_ms=60000,
        fallback="mark as unknown, request manual proof"
    ),
}

def solve_with_tiered_timeout(constraint: Constraint, tier: LatencyTier) -> SolverResult:
    config = TIMEOUT_CONFIGS[tier]

    try:
        return solve_with_timeout(constraint, timeout_ms=config.timeout_ms)
    except TimeoutError:
        if config.fallback == "return cached or heuristic result":
            return get_cached_or_heuristic(constraint)
        elif config.fallback == "simplify constraint and retry":
            simplified = simplify_constraint(constraint)
            return solve_with_timeout(simplified, timeout_ms=config.timeout_ms * 2)
        else:
            return SolverResult(status=SolverStatus.UNKNOWN)
```

### 8.4 Resource Limits

**Memory**: Z3 can consume gigabytes for complex queries. Set limits.

```python
from z3 import set_param

# Limit Z3 memory to 2GB
set_param('memory_max_size', 2048)  # MB

# Limit SMT solver iterations
set_param('smt.max_conflicts', 100000)
```

**Parallelization**: Solve independent constraints in parallel.

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

async def solve_parallel(constraints: List[Constraint]) -> List[SolverResult]:
    """Solve independent constraints in parallel."""

    # Partition constraints by dependency groups
    independent_groups = partition_by_dependencies(constraints)

    # Solve each group in parallel
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(solve_constraint_group, group)
            for group in independent_groups
        ]
        results = await asyncio.gather(*futures)

    return flatten(results)
```

**Benchmark** (4-core machine):
- Sequential solving: 12s for 100 constraints
- Parallel solving: 4s for 100 constraints (3x speedup)

---

## 9. Error Reporting

### 9.1 Counterexample Generation

**When**: Constraint is unsatisfiable (UNSAT).

**Goal**: Provide concrete example showing why constraint fails.

**Example**:

Constraint: `∀x. x > 0 ⇒ sqrt(x) > 0`

Z3 verification (negated postcondition):
```python
from z3 import Real, Solver, Sqrt, Not, ForAll

x = Real('x')
solver = Solver()

# Negate postcondition: ∃x. x > 0 ∧ sqrt(x) <= 0
solver.add(x > 0)
solver.add(Sqrt(x) <= 0)

if solver.check() == sat:
    model = solver.model()
    print(f"Counterexample: x = {model[x]}")  # Should be UNSAT (no counterexample)
else:
    print("Postcondition verified ✓")
```

**User-Facing Error**:
```
❌ Constraint Violation

The postcondition 'sqrt(x) > 0' does not hold for all inputs.

Counterexample:
  x = 0.0
  Expected: sqrt(0.0) > 0
  Actual: sqrt(0.0) = 0

Suggestion: Change postcondition to 'sqrt(x) >= 0' or strengthen precondition to 'x > 0.0001'
```

### 9.2 UNSAT Core Extraction

**When**: Multiple constraints conflict.

**Goal**: Identify minimal set of conflicting constraints.

**Example**:

```python
from z3 import Int, Solver, Bool

solver = Solver()
x = Int('x')

# Named constraints for tracking
c1 = Bool('c1')
c2 = Bool('c2')
c3 = Bool('c3')

solver.assert_and_track(x > 10, c1)
solver.assert_and_track(x < 5, c2)
solver.assert_and_track(x >= 0, c3)

if solver.check() == unsat:
    core = solver.unsat_core()
    print(f"Minimal conflict: {[str(c) for c in core]}")  # ['c1', 'c2']
```

**User-Facing Error**:
```
❌ Conflicting Constraints

The following constraints cannot be satisfied simultaneously:
  1. x > 10  (from refinement type: {x: Int | x > 10})
  2. x < 5   (from FuncSpec precondition: requires x < 5)

These constraints are contradictory. Please revise one of them.

Suggestion: Did you mean 'x >= 5' instead of 'x < 5'?
```

### 9.3 User-Friendly Explanations

**Challenge**: SMT-LIB output is cryptic. Make it human-readable.

**Strategy**: Template-based explanation generation.

```python
def explain_unsat_core(core: List[Constraint]) -> str:
    """Generate human-friendly explanation for UNSAT core."""

    if len(core) == 2:
        c1, c2 = core
        return f"""
The constraints '{c1.description}' and '{c2.description}' are contradictory.

Details:
  - {c1.description} requires: {c1.predicate}
  - {c2.description} requires: {c2.predicate}

These cannot both be true. Please revise one of them.
"""

    elif len(core) > 2:
        return f"""
The following {len(core)} constraints cannot all be satisfied:

{numbered_list([c.description for c in core])}

This is an over-constrained problem. Try relaxing one or more constraints.
"""

    else:
        return f"Constraint '{core[0].description}' is unsatisfiable (always false)."
```

**Example Output**:
```
The constraints 'age must be positive' and 'age must be less than zero' are contradictory.

Details:
  - age must be positive requires: age > 0
  - age must be less than zero requires: age < 0

These cannot both be true. Please revise one of them.
```

### 9.4 Suggested Fixes

**Goal**: Don't just report errors—suggest fixes.

**Strategies**:

1. **Relax bound**: `x > 10` conflicts with `x < 5` → Suggest `x >= 5`
2. **Add precondition**: Postcondition fails → Suggest strengthening precondition
3. **Remove constraint**: If constraint is optional, suggest removing it

**Example**:

```python
def suggest_fix(unsat_core: List[Constraint]) -> str | None:
    """Heuristically suggest a fix for UNSAT core."""

    if len(unsat_core) == 2:
        c1, c2 = unsat_core

        # Case: x > a conflicts with x < b where a >= b
        if is_lower_bound(c1) and is_upper_bound(c2):
            a = extract_bound(c1)
            b = extract_bound(c2)
            if a >= b:
                return f"Change '{c1.description}' to 'x >= {b}' or '{c2.description}' to 'x < {a}'"

        # Case: x == a conflicts with x == b where a != b
        if is_equality(c1) and is_equality(c2):
            return f"Remove one of the equality constraints—x cannot equal two different values"

    return None  # No automated suggestion
```

---

## 10. Testing Strategy

### 10.1 Solver Correctness

**Goal**: Verify that solver results are correct (no false SAT/UNSAT).

**Strategy**: Property-based testing with Hypothesis.

```python
from hypothesis import given, strategies as st
from z3 import Int, Solver, sat, unsat

@given(st.integers(min_value=-100, max_value=100))
def test_smt_correctness_satisfiable(value: int):
    """Test: If solver says SAT, model must satisfy constraint."""

    x = Int('x')
    solver = Solver()
    solver.add(x == value)

    # Solver must return SAT
    assert solver.check() == sat

    # Model must satisfy constraint
    model = solver.model()
    assert model[x].as_long() == value

@given(st.integers(), st.integers())
def test_smt_correctness_unsatisfiable(a: int, b: int):
    """Test: If solver says UNSAT, no model exists."""

    if a >= b:
        return  # Skip if constraints are satisfiable

    x = Int('x')
    solver = Solver()
    solver.add(x > a)
    solver.add(x < b)

    # If a >= b, must be UNSAT
    if a >= b:
        assert solver.check() == unsat
```

**Coverage**: Run 10,000 random test cases per property.

### 10.2 Performance Benchmarks

**Goal**: Ensure solver queries meet latency targets.

**Benchmark Suite**:

```python
import pytest
import time

@pytest.mark.benchmark
def test_csp_latency():
    """CSP queries must complete in <500ms."""

    start = time.time()

    problem = create_hole_closure_problem(domain_size=100)
    solutions = problem.getSolutions()

    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 500, f"CSP too slow: {elapsed_ms}ms"

@pytest.mark.benchmark
def test_smt_refinement_latency():
    """Refinement type checks must complete in <5s."""

    start = time.time()

    solver = create_refinement_solver(complexity="high")
    result = solver.check()

    elapsed_ms = (time.time() - start) * 1000
    assert elapsed_ms < 5000, f"SMT too slow: {elapsed_ms}ms"
```

**Regression Detection**: Track p50, p95, p99 latencies over time. Alert if p95 increases >20%.

### 10.3 Property-Based Testing

**Goal**: Find edge cases and corner cases automatically.

**Example**: Constraint propagation preserves satisfiability.

```python
from hypothesis import given, strategies as st

@given(
    st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=5)
)
def test_constraint_propagation_preserves_satisfiability(constraints: List[int]):
    """
    Property: If original constraint set is SAT, propagated set must also be SAT.
    """

    store = ConstraintStore()

    # Add constraints
    for value in constraints:
        store.add_constraint(make_constraint(f"x == {value}"))

    # Check original satisfiability
    original_sat = all_satisfiable(store.constraints.values())

    # Run propagation
    store.propagate()

    # Check propagated satisfiability
    propagated_sat = all_satisfiable(store.constraints.values())

    # Invariant: Propagation doesn't introduce unsatisfiability
    if original_sat:
        assert propagated_sat, "Propagation broke satisfiability"
```

### 10.4 Integration Tests

**Goal**: Test end-to-end solver integration in realistic scenarios.

**Scenario 1**: Typed hole closure

```python
def test_hole_closure_with_refinement_type():
    """
    Test: Find valid closures for hole with refinement type.

    IR:
      def discount(price: Float) -> ?pct
      where ?pct :: {x: Float | x >= 0.0 && x <= 1.0}
    """

    hole = TypedHole(
        id="pct",
        type=RefinementType(
            base=FloatType(),
            predicate=And(Var("x") >= 0.0, Var("x") <= 1.0)
        )
    )

    # Scope: available variables
    scope = {
        "price": FloatType(),
        "customer_tier": EnumType(["bronze", "silver", "gold"]),
    }

    # Find closures
    closures = find_hole_closures(hole, scope)

    # Verify all closures satisfy refinement type
    for closure in closures:
        assert satisfies_refinement(closure, hole.type)

    # Expected closures: 0.0, 0.1, 0.2, ... (constants in range)
    #                    or expressions like: if customer_tier == "gold" then 0.2 else 0.1
```

**Scenario 2**: Postcondition verification

```python
def test_postcondition_verification():
    """
    Test: Verify postcondition holds for function implementation.

    IR:
      def abs_value(x: Int) -> {result: Int | result >= 0}
      ensures: result >= 0

      Implementation:
        if x >= 0 then x else -x
    """

    func_spec = FuncSpec(
        name="abs_value",
        inputs=[("x", IntType())],
        output=RefinementType(base=IntType(), predicate=Var("result") >= 0),
        postcondition=Var("result") >= 0
    )

    implementation = IfExpr(
        condition=Var("x") >= 0,
        then_branch=Var("x"),
        else_branch=UnaryOp("-", Var("x"))
    )

    # Verify
    result = verify_postcondition(func_spec, implementation)

    assert result.status == VerificationStatus.VERIFIED
    assert result.message == "Postcondition verified ✓"
```

---

## Conclusion

### Summary

This RFC specifies a **tiered constraint solver architecture** for lift's IR that:

1. **Routes problems efficiently**: CSP for discrete domains, SAT for booleans, SMT for theories
2. **Optimizes for interactivity**: Sub-second queries for editor-time suggestions
3. **Provides explainable results**: Models for SAT, UNSAT cores for failures, human-friendly explanations
4. **Scales incrementally**: Push/pop for iterative refinement, caching for repeated queries
5. **Integrates seamlessly**: Constraint Store (𝒞) manages propagation, dependencies, learned facts

### Key Design Decisions

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| **Tiered architecture** (CSP/SAT/SMT) | Different problems have different complexity | Additional routing logic |
| **Z3 for SMT** | Industry standard, rich theory support | Vendor lock-in (mitigated by SMT-LIB) |
| **Incremental solving** | Interactive refinement requires fast updates | More complex solver state |
| **UNSAT cores** | Essential for actionable error messages | Extra solver overhead |
| **Timeout budgets** | Prevent runaway queries | May miss valid solutions |

### Success Criteria

This solver architecture is successful if:

- ✅ **Editor-time queries**: 95% complete in <500ms (CSP tier)
- ✅ **Verification queries**: 90% complete in <5s (SMT tier)
- ✅ **Correctness**: 100% SAT results verified by model, 100% UNSAT results include core
- ✅ **Explainability**: 80% of failures include suggested fix
- ✅ **Cache hit rate**: >50% overall (reduces redundant solving)

### Future Work

**Phase 3+ (Post-MVP)**:

1. **Parallel solving**: Distribute independent constraints across cores/machines
2. **Custom theories**: Domain-specific theories (e.g., SQL query constraints, API contracts)
3. **Proof term generation**: For deep verification, generate Lean/Coq proof terms
4. **Counterexample-guided abstraction refinement (CEGAR)**: Iteratively refine abstractions
5. **Quantifier instantiation heuristics**: Improve Z3's handling of ∀∃ formulas

### References

**SMT Solving**:
- [SMT-LIB Standard 2.6](https://smt-lib.org/language.shtml) - Official SMT-LIB language specification
- [Z3 Guide](https://microsoft.github.io/z3guide/) - Comprehensive Z3 tutorial and API reference
- Moura & Bjørner. "Z3: An Efficient SMT Solver" (TACAS 2008)

**SAT Solving**:
- Marques-Silva et al. "CDCL SAT Solving" (Handbook of Satisfiability, 2nd ed., 2021)
- [PySAT Documentation](https://pysathq.github.io/) - Python SAT solving library

**CSP Solving**:
- Dechter. "Constraint Processing" (2003) - Comprehensive CSP textbook
- [python-constraint Documentation](https://labix.org/python-constraint)

**Refinement Types**:
- Jhala & Vazou. "Refinement Types: A Tutorial" (2021)
- Liquid Haskell: Refinement types for Haskell

**Related Work in lift**:
- RFC_IR_CORE.md - IR type system and refinement type semantics
- RFC_LIFT_ARCHITECTURE.md - Overall system architecture
- IR_SPECIFICATION.md - Complete IR 0.9 formal specification

---

**Document Status**: Draft
**Owner**: Codelift Team
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Next Review**: Phase 3 Kickoff (when H10 OptimizationMetrics begins)
