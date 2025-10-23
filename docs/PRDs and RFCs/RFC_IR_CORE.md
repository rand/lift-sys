# RFC: IR 0.9 Core Technical Specification

**RFC Number**: RFC-002
**Title**: Intermediate Representation 0.9 Core Architecture
**Status**: Draft
**Created**: 2025-10-21
**Last Updated**: 2025-10-21
**Authors**: Codelift Team
**Related Documents**: RFC_LIFT_ARCHITECTURE.md, IR_SPECIFICATION.md, PRD_TYPED_HOLES.md

---

## Executive Summary

This RFC provides a comprehensive technical deep-dive into **IR 0.9**, lift's Intermediate Representation system. While RFC_LIFT_ARCHITECTURE provides the architectural overview, this document focuses exclusively on the formal semantics, implementation details, and practical usage of the IR core.

**What is IR 0.9?**

IR 0.9 is a mathematically rigorous semantic layer that bridges natural language intent and production code. Unlike traditional IRs (LLVM IR, JVM bytecode), IR 0.9 is designed for:
- **Human authoring**: Readable syntax with prose integration
- **AI generation**: Constrainable output via XGrammar/llguidance
- **Formal verification**: SMT solver integration for refinement types
- **Iterative refinement**: Typed holes with partial evaluation
- **Bidirectional translation**: Natural language ↔ IR ↔ Code

**Key Innovations**:

1. **Six Hole Kinds**: term, type, spec, entity, function, module - with dependent type holes
2. **Hole Closures**: Hazel-inspired partial evaluation around unknowns
3. **Refinement Types**: SMT-backed predicates `{x:T | φ}` for semantic constraints
4. **Dependent Types**: Types depending on values `Π(x:A).B` for precise specifications
5. **IntentSpec ↔ FuncSpec Alignment**: Human goals mapped to machine-checkable contracts

**Scope**: This RFC covers IR syntax, semantics, type system, parser implementation, type checker, validator, and serialization. Constraint solving details are in RFC_CONSTRAINT_SOLVER.md.

---

## Part 1: Introduction & IR Philosophy

### 1.1 The Problem: Traditional IRs Are Too Low-Level

Traditional intermediate representations serve compilation and optimization:
- **LLVM IR**: Register-based SSA form, optimized for machine generation
- **JVM bytecode**: Stack-based, designed for portability and verification
- **GHC Core**: Simplified functional IR, good for optimization passes

**None support**:
- Natural language alignment (where does the user's intent live?)
- Explicit unknowns (how do we represent "not yet decided"?)
- Semantic constraints (how do we encode "this value must be positive"?)
- Live execution around holes (how do we preview partial programs?)

### 1.2 The Solution: IR as Semantic Bridge

IR 0.9 positions the intermediate representation as a **semantic bridge** between human intent and machine execution:

```
Natural Language                                    Production Code
     ↓                                                     ↑
IntentSpec {goals, constraints}            Code {Python, TypeScript, ...}
     ↓                                                     ↑
     └─────────→  IR 0.9 (Semantic Core)  ←───────────────┘
                  - Types + Refinements
                  - Typed Holes
                  - Constraint Store
                  - Solver Queries
```

**Bidirectional Flow**:
- **Forward**: NL → Intent → FuncSpec → IR → Code (with holes for ambiguities)
- **Reverse**: Code → IR → FuncSpec → IntentSpec (understanding existing code)

### 1.3 Design Philosophy

**Three Core Insights**:

1. **Typed Holes as First-Class Citizens**
   - Unknowns are not errors—they're explicit design points
   - Each hole has a type (possibly another hole!)
   - Holes drive constraint propagation and AI suggestion

2. **Bidirectional Typing + Refinements**
   - Dependent types (types depend on values): `Vec n T` has length `n`
   - Refinement types (types + predicates): `{x:Int | x ≥ 0}` is non-negative
   - Decidable checking via SMT solvers (Z3)

3. **Live Execution Around Holes**
   - Inspired by Hazel's "hole closures" [POPL'19]
   - Programs run even with holes, recording evidence
   - Fill-and-resume: no full restart after filling holes

### 1.4 Influences and Prior Art

**Academic Foundations**:
- **Hazel/Hazelnut Live** (POPL'19): Hole closures, indeterminate progress, fill-and-resume semantics
- **GHC Typed Holes**: Valid hole fits, refinement fits, type-directed suggestions
- **Lean 4/Coq**: Global meta-context for metavariables/evars with constraint propagation
- **Idris/Agda**: Interactive refinement, dependent types, hole-driven development
- **Liquid Haskell**: SMT-backed refinement types with decidable checking

**Key Papers**:
1. Cyrus Omar et al. "Live Functional Programming with Typed Holes." POPL 2019. [arXiv:1805.00155](https://arxiv.org/abs/1805.00155)
2. Matthías Páll Gissurarson. "Suggesting Valid Hole Fits for Typed-Holes." Haskell 2018.
3. Niki Vazou et al. "Refinement Types for Haskell." ICFP 2014.
4. Noam Zeilberger. "Principles of Type Refinement." PhD Thesis, CMU 2009.

### 1.5 What IR 0.9 Is NOT

**Not a general-purpose programming language**: IR is a semantic layer for specification and verification, not direct human programming (though it's human-readable).

**Not a proof assistant**: We don't require full proofs. SMT solver checks are sufficient for many properties. Proof assistants (Lean, Coq) can be integrated as solvers.

**Not tied to one target language**: IR compiles to Python, TypeScript, Go, Rust, Java, etc. The same IR can generate multiple target languages.

**Not a database schema**: While IR includes entity declarations, it's not an ORM. Entities map to types + validation logic in target languages.

---

## Part 2: IR 0.9 Grammar (Formal BNF/EBNF)

### 2.1 Lexical Structure

**Keywords**:
```
intent  entity  spec  def  type  hole
requires  ensures  invariants  effects  cost
let  in  match  with  if  then  else
forall  exists  safe  import  export
```

**Operators**:
```
Logical:  ∧ ∨ ¬ → ↔ (or: and or not implies iff)
Arithmetic: + - * / % < <= > >= = ≠
Type:  : :: -> => | × + Π { } [ ]
Hole:  ?
```

**Identifiers**:
```
identifier ::= [a-zA-Z_][a-zA-Z0-9_]*
hole_id    ::= '?' identifier
type_var   ::= [a-z] | 'α' | 'β' | 'γ' ...
```

### 2.2 Types (T)

```ebnf
Type ::= BaseType
       | TypeVar
       | DependentFunctionType
       | RefinementType
       | ProductType
       | SumType
       | RecursiveType
       | EffectType
       | TypeHole

BaseType ::= 'Int' | 'Str' | 'Bool' | 'Nat' | 'Float' | 'Bytes'
           | 'List' Type | 'Option' Type | 'Result' Type Type

TypeVar ::= identifier

DependentFunctionType ::= 'Π' '(' identifier ':' Type ')' '.' Type
                        | Type '->' Type  (* sugar for non-dependent *)

RefinementType ::= '{' identifier ':' Type '|' Predicate '}'

ProductType ::= Type '×' Type
              | '(' Type ',' Type (',' Type)* ')'  (* sugar *)

SumType ::= Type '+' Type
          | Type '|' Type  (* sugar *)

RecursiveType ::= 'μ' identifier '.' Type

EffectType ::= 'Eff' '[' Type ']' ('with' EffectLabel (',' EffectLabel)*)?

TypeHole ::= '?' identifier ':' 'type'

EffectLabel ::= 'IO' | 'State' | 'Error' | 'Network' | 'LLM' | identifier
```

**Examples**:
```specir
-- Base types
x: Int
s: Str
valid: Bool

-- Dependent function (vector concatenation)
concat : Π(n:Nat). Π(m:Nat). Vec n T -> Vec m T -> Vec (n+m) T

-- Refinement type (positive integers)
Positive = {x: Int | x > 0}

-- Product type
Point = Int × Int

-- Sum type (Result)
Result T E = Ok T | Err E

-- Recursive type (List)
List T = μL. Nil | Cons (T × L)

-- Effect type
readFile : Str -> Eff[Bytes] with IO, Error

-- Type hole
CustomerId = ?CustomerIdType:type
```

### 2.3 Terms (e)

```ebnf
Term ::= Variable
       | Lambda
       | Application
       | ConstructorApp
       | Match
       | Let
       | If
       | EffectInvoke
       | Literal
       | TermHole

Variable ::= identifier

Lambda ::= 'λ' identifier ':' Type '.' Term
         | '(' identifier ':' Type ')' '=>' Term  (* sugar *)

Application ::= Term Term
              | Term '(' Term (',' Term)* ')'  (* sugar *)

ConstructorApp ::= identifier Term
                 | identifier '(' Term (',' Term)* ')'  (* sugar *)

Match ::= 'match' Term 'with' Pattern '->' Term ('|' Pattern '->' Term)*

Let ::= 'let' identifier '=' Term 'in' Term

If ::= 'if' Term 'then' Term 'else' Term

EffectInvoke ::= 'eff' Term

Literal ::= Integer | String | Boolean | FloatLit

TermHole ::= '?' identifier (':' 'term')? ('[' 'links' '=' '{' HoleRef (',' HoleRef)* '}' ']')?

HoleRef ::= '?' identifier
```

**Examples**:
```specir
-- Lambda
increment = λx:Int. x + 1

-- Application
result = increment 5

-- Constructor
Some(42)
Ok("success")

-- Match
match result with
| Ok(x) -> x
| Err(e) -> panic(e)

-- Let binding
let doubled = x * 2 in
doubled + 10

-- If expression
if age >= 18 then "adult" else "minor"

-- Term hole with links
?impl:term [links={?helper1, ?helper2}]
```

### 2.4 Predicates (φ)

```ebnf
Predicate ::= PredicateApp
            | Conjunction
            | Disjunction
            | Negation
            | Implication
            | Quantification
            | Comparison
            | SafetyPred
            | CostPred

PredicateApp ::= identifier '(' Term (',' Term)* ')'

Conjunction ::= Predicate '∧' Predicate
              | Predicate 'and' Predicate

Disjunction ::= Predicate '∨' Predicate
              | Predicate 'or' Predicate

Negation ::= '¬' Predicate
           | 'not' Predicate

Implication ::= Predicate '→' Predicate
              | Predicate 'implies' Predicate

Quantification ::= '∀' identifier ':' Type '.' Predicate
                 | '∃' identifier ':' Type '.' Predicate
                 | 'forall' identifier ':' Type '.' Predicate
                 | 'exists' identifier ':' Type '.' Predicate

Comparison ::= Term '=' Term
             | Term '≠' Term
             | Term '<' Term
             | Term '<=' Term
             | Term '>' Term
             | Term '>=' Term

SafetyPred ::= 'safe' '(' Term ')'

CostPred ::= 'cost' '<=' Term
           | 'latency' '<=' Term
```

**Examples**:
```specir
-- Predicate application
is_valid(email)

-- Conjunction
x > 0 ∧ x < 100

-- Quantification
∀i:Nat. i < length(xs) → xs[i] ≥ 0

-- Implication
valid(x) → safe(process(x))

-- Cost predicate
cost <= 0.01
latency <= 5000
```

### 2.5 Declarations (d)

```ebnf
Declaration ::= TypeDecl
              | DefDecl
              | EntityDecl
              | SpecDecl
              | IntentDecl
              | HoleDecl

TypeDecl ::= 'type' identifier ('(' identifier ':' Type (',' identifier ':' Type)* ')')? '=' Type

DefDecl ::= 'def' identifier ':' Type '=' Term
          | 'def' identifier '(' Parameter (',' Parameter)* ')' ':' Type '=' Term

Parameter ::= identifier ':' Type

EntityDecl ::= 'entity' StringLit ':' '{' FieldDecl (',' FieldDecl)* '}'

FieldDecl ::= identifier ':' Type

SpecDecl ::= 'spec' StringLit ('(' Parameter (',' Parameter)* ')')? ':'
             ('requires:' Predicate)?
             ('ensures:' Predicate)?
             ('invariants:' Predicate)?
             ('effects:' EffectLabel (',' EffectLabel)*)?
             ('cost:' CostPred)?

IntentDecl ::= 'intent' StringLit ':'
               'inputs:' FieldDecl (',' FieldDecl)*
               'outputs:' FieldDecl (',' FieldDecl)*
               'goals:' StringLit (',' StringLit)*
               ('constraints:' StringLit (',' StringLit)*)?
               ('metrics:' MetricDecl (',' MetricDecl)*)?

MetricDecl ::= identifier '>=' Term | identifier '<=' Term

HoleDecl ::= 'hole' '?' identifier ':' HoleKind (':' Type)?
             ('[' 'links' '=' '{' HoleRef (',' HoleRef)* '}' ']')?
             ('[' 'hints' '=' '{' KeyValue (',' KeyValue)* '}' ']')?

HoleKind ::= 'term' | 'type' | 'spec' | 'entity' | 'function' | 'module'

KeyValue ::= StringLit ':' Term
```

**Examples**:
```specir
-- Type declaration
type Vec (n: Nat) (T: Type) = ...

-- Function definition
def factorial : Nat -> Nat =
  λn. if n = 0 then 1 else n * factorial(n - 1)

-- Entity declaration
entity "User": {
  id: {x: Int | x >= 0},
  email: {s: Str | is_valid_email(s)},
  age: {x: Int | x >= 0 ∧ x <= 150}
}

-- Spec declaration
spec "Sorted"(xs: List Int):
  ensures: ∀i,j:Nat. i < j ∧ j < length(xs) → xs[i] <= xs[j]

-- Intent declaration
intent "Summarize document":
  inputs: doc: Str, n: Nat
  outputs: bullets: List Str
  goals:
    - "Produce exactly n bullet points"
    - "Each bullet appropriate for audience"
  metrics:
    readability >= 0.8

-- Hole declaration
hole ?impl:term : List Str [links={?extract, ?rank}]
```

### 2.6 Programs and Modules

```ebnf
Program ::= Declaration*

Module ::= 'module' identifier (':' '{' Import* Export* Declaration* '}')?

Import ::= 'import' identifier ('as' identifier)?

Export ::= 'export' identifier
```

---

## Part 3: Type System Details

### 3.1 Bidirectional Type Checking

IR 0.9 uses **bidirectional type checking**: terms are either **checked** against a known type or **synthesized** to produce a type.

**Judgments**:
```
Γ ⊢ e ⇐ T    -- Check: term e has type T in context Γ
Γ ⊢ e ⇒ T    -- Synthesize: term e produces type T in context Γ
```

**Rules (Selected)**:

**[Var-Synth]**:
```
x:T ∈ Γ
─────────────
Γ ⊢ x ⇒ T
```

**[Lam-Check]**:
```
Γ, x:A ⊢ e ⇐ B
──────────────────────
Γ ⊢ (λx:A. e) ⇐ A → B
```

**[App-Synth]**:
```
Γ ⊢ e₁ ⇒ A → B    Γ ⊢ e₂ ⇐ A
──────────────────────────────
Γ ⊢ e₁ e₂ ⇒ B
```

**[Refine-Check]**:
```
Γ ⊢ e ⇐ T    Γ, x:T ⊢ φ : Bool    SMT_check(Γ, φ[x:=e]) = sat
─────────────────────────────────────────────────────────────
Γ ⊢ e ⇐ {x:T | φ}
```

**[Hole-Synth]**:
```
?h fresh    ?α = fresh_type_var()    record_meta(?h, ?α)
────────────────────────────────────────────────────────
Γ ⊢ ?h:term ⇒ ?α
```

**[TypeHole-Synth]**:
```
?α fresh    record_type_meta(?α)
─────────────────────────────────
Γ ⊢ ?α:type ⇒ ★
```

### 3.2 Dependent Types: Π-Types

**Syntax**: `Π(x:A).B` where `x` may appear in `B`.

**Non-dependent sugar**: `A → B` is shorthand for `Π(x:A).B` when `x` not free in `B`.

**Examples**:
```specir
-- Dependent: x appears in result type
replicate : Π(n:Nat). T -> Vec n T

-- Non-dependent: x doesn't appear in result
add : Int -> Int -> Int  -- sugar for Π(_:Int). Π(_:Int). Int
```

**Typing Rule** (simplified):
```
Γ ⊢ A : Type    Γ, x:A ⊢ B : Type
──────────────────────────────────
Γ ⊢ Π(x:A).B : Type
```

**Application with Substitution**:
```
Γ ⊢ e₁ ⇒ Π(x:A).B    Γ ⊢ e₂ ⇐ A
──────────────────────────────────
Γ ⊢ e₁ e₂ ⇒ B[x := e₂]
```

Example:
```specir
-- Definition
concat : Π(n:Nat). Π(m:Nat). Vec n T -> Vec m T -> Vec (n+m) T

-- Application
xs : Vec 3 Int
ys : Vec 5 Int
result = concat 3 5 xs ys  -- Type: Vec (3+5) Int = Vec 8 Int
```

### 3.3 Refinement Types: {x:T | φ}

**Syntax**: `{x:T | φ}` where `x:T` and `φ` is a predicate.

**Semantics**: The subset of values `v:T` such that `φ[x:=v]` holds.

**Subtyping Rule**:
```
Γ ⊢ φ₁ implies φ₂    (via SMT)
────────────────────────────────
Γ ⊢ {x:T | φ₁} <: {x:T | φ₂}
```

**Examples**:
```specir
-- Natural numbers
Nat = {x: Int | x >= 0}

-- Bounded values
Age = {x: Int | x >= 0 ∧ x <= 150}

-- Non-empty lists
NonEmpty T = {xs: List T | length(xs) > 0}

-- Sorted lists
Sorted T = {xs: List T | ∀i,j. i < j → xs[i] <= xs[j]}
```

**Checking Refinements**:

When checking `e ⇐ {x:T | φ}`:
1. Check `e ⇐ T` (base type)
2. Generate SMT query: `Γ ⊢ φ[x:=e]`
3. If `sat`: accept
4. If `unsat`: reject with counterexample
5. If `unknown`: warn and accept (or require annotation)

**Example: Checking Factorial**:
```specir
def factorial : Nat -> {x: Nat | x > 0} =
  λn. if n = 0 then 1 else n * factorial(n - 1)

-- Type checker must prove:
-- ∀n:Nat. (n = 0 → 1 > 0) ∧ (n ≠ 0 → n * factorial(n-1) > 0)
```

SMT query (simplified):
```smt2
(declare-const n Int)
(assert (>= n 0))  ; n is Nat
(assert (or
  (and (= n 0) (> 1 0))  ; base case
  (and (not (= n 0)) (> (* n (factorial-result (- n 1))) 0))  ; recursive
))
(check-sat)
```

### 3.4 Hole Type Rules

**Six Hole Kinds**:

1. **Term Holes** (`?h:term`): Unknown expression
2. **Type Holes** (`?α:type`): Unknown type
3. **Spec Holes** (`?s:spec`): Unknown predicate
4. **Entity Holes** (`?E:entity`): Unknown data structure
5. **Function Holes** (`?f:function`): Unknown function implementation
6. **Module Holes** (`?M:module`): Unknown component

**Term Hole Typing**:
```
?h fresh    ?α = fresh_type_var()    record_meta(?h : ?α, Γ)
──────────────────────────────────────────────────────────────
Γ ⊢ ?h:term ⇒ ?α
```

**Type Hole Typing**:
```
?α fresh    record_type_meta(?α, kind=Type)
────────────────────────────────────────────
Γ ⊢ ?α:type ⇒ ★
```

**Unknown Type Hole** (hole with hole type):
```specir
-- The hole's type is itself unknown
?impl:term : ?T:type

-- Type checker:
-- 1. Creates meta ?T (type hole)
-- 2. Creates meta ?impl with type ?T
-- 3. Constraints: ?impl must fill with term of type ?T
```

**Hole Linking**:

Holes can declare dependencies via `links`:
```specir
def summarize(doc: Str, n: Nat) : List Str =
  ?impl:term [links={?extract, ?rank}]

hole ?extract:function : Str -> List Str
hole ?rank:function : List Str -> List Str

-- Constraint propagation:
-- ?impl USES ?extract and ?rank
-- Filling ?extract or ?rank constrains ?impl
```

### 3.5 Meta-Context and Constraint Store

**Global State**:
```python
MetaContext = {
    holes: dict[HoleID, HoleMeta],
    type_metas: dict[TypeVar, TypeMeta],
    constraints: list[Constraint],
}

@dataclass
class HoleMeta:
    hole_id: str
    kind: HoleKind
    type: Type | TypeVar  # Can be a type meta!
    context: Context  # Γ where hole appears
    links: list[HoleID]
    hints: dict[str, Any]

@dataclass
class Constraint:
    kind: ConstraintKind  # TypeEq, Subtype, Refinement
    left: Term | Type
    right: Term | Type
    origin: str  # Where did this constraint come from?
```

**Constraint Propagation**:

When resolving hole `?h`:
1. Collect all constraints mentioning `?h`
2. Unify `?h`'s type with constraint types
3. Propagate to linked holes (update their constraints)
4. Check for occurs-check violations
5. Validate refinements via SMT

**Example**:
```specir
def process(x: Int) : {y: Int | y > 0} =
  ?impl:term

-- Constraints generated:
-- 1. ?impl : Int -> {y: Int | y > 0}  (from signature)
-- 2. ?impl must be in scope or constructed  (from context)
-- 3. Result must satisfy y > 0  (from refinement)

-- Valid fits:
-- λn. abs(n) + 1  -- Always positive
-- λn. n * n + 1   -- Always positive
-- λn. n + 1       -- INVALID (not always positive when n < 0)
```

### 3.6 Occurs Check

**Problem**: Prevent infinite types via self-reference.

**Rule**: Type variable `α` cannot appear in type `T` if we're solving `α := T`.

**Example (Invalid)**:
```specir
?α := List ?α  -- INVALID: α appears in its own definition
```

**Detection**:
```python
def occurs_check(var: TypeVar, typ: Type) -> bool:
    """Returns True if var occurs in typ (violation)."""
    if typ == var:
        return True
    if isinstance(typ, (ListType, OptionType)):
        return occurs_check(var, typ.inner)
    if isinstance(typ, FunctionType):
        return occurs_check(var, typ.arg) or occurs_check(var, typ.ret)
    return False
```

**Blocked Metas**:

When occurs check fails, meta is **blocked** with justification:
```python
BlockedMeta(
    meta_id="?α",
    reason="occurs_check",
    cycle_path=["?α", "List ?α", "?α"],
    suggestion="Introduce recursive type: μα. List α",
)
```

---

## Part 4: Typed Holes (Six Kinds, Closures, Meta-Context)

### 4.1 Hole Taxonomy

**Term Holes** (`?h:term`):
```specir
-- Unknown expression
def factorial(n: Nat) : Nat =
  if n = 0 then 1 else ?recursive_case:term

-- Constraints: ?recursive_case : Nat, uses n
-- Suggestions: n * factorial(n-1)
```

**Type Holes** (`?α:type`):
```specir
-- Unknown type
entity "Customer":
  id: Int
  status: ?StatusType:type  -- What type for status?

-- Constraints: ?StatusType must be serializable
-- Suggestions: enum {Active, Inactive}, Str, custom ADT
```

**Spec Holes** (`?s:spec`):
```specir
-- Unknown predicate
spec "ValidInput"(x: Int):
  requires: ?input_constraint:spec

-- Constraints: ?input_constraint : Bool
-- Suggestions: x >= 0, x > 0 ∧ x < 100
```

**Entity Holes** (`?E:entity`):
```specir
-- Unknown data structure
def store_user(data: ?UserEntity:entity) : Result Unit Error =
  ?impl:term

-- Constraints: ?UserEntity must have id field
-- Suggestions: existing User type, new entity with fields
```

**Function Holes** (`?f:function`):
```specir
-- Unknown function
def pipeline(input: Str) : Result Str Error =
  let validated = ?validate:function input in
  let transformed = ?transform:function validated in
  Ok(transformed)

-- Constraints:
--   ?validate : Str -> Str
--   ?transform : Str -> Str
```

**Module Holes** (`?M:module`):
```specir
-- Unknown component
import ?AuthModule:module

def authenticate(token: Str) : Result User Error =
  ?AuthModule.verify(token)

-- Constraints: ?AuthModule must export verify : Str -> Result User Error
-- Suggestions: existing auth modules, OAuth library, JWT library
```

### 4.2 Hole Closures (Hazel-Inspired)

**Concept**: Holes carry their **environment** so programs can run around them.

**Closure Definition**:
```
⟨Γ, ?h⟩  where Γ is the environment (local bindings) and ?h is the hole
```

**Example**:
```specir
def process(input: Int) : Int =
  let x = input * 2 in
  let y = ?transform:term x in  -- Hole closure: ⟨{input=5, x=10}, ?transform⟩
  y + 10

-- Evaluation with input=5:
-- 1. x = 10
-- 2. Create closure: ⟨{input=5, x=10}, ?transform⟩
-- 3. Record: ?transform receives Int (example value: 10)
-- 4. Continue: y = ⟨?transform 10⟩ (indeterminate)
-- 5. Result: ⟨?transform 10⟩ + 10 (indeterminate, but shows structure)
```

**Indeterminate Progress**:

Programs produce **partial values** with hole markers:
```python
@dataclass
class IndeterminateValue:
    structure: str  # "(_ + 10)" where _ is hole result
    holes: list[HoleRef]  # [?transform]
    traces: list[ValueTrace]  # [{hole: ?transform, input_example: 10}]
```

**Fill-and-Resume**:

After filling `?transform = λn. n * n`:
1. Retrieve closure: `⟨{input=5, x=10}, ?transform⟩`
2. Substitute: `?transform x` becomes `(λn. n * n) 10`
3. Evaluate: `10 * 10 = 100`
4. Resume: `y = 100`, then `y + 10 = 110`
5. **No full restart required**

### 4.3 Meta-Context Implementation

**Structure**:
```python
@dataclass
class MetaContext:
    """Global context for all holes and metas."""
    holes: dict[str, HoleMeta]
    type_vars: dict[str, TypeVarMeta]
    constraints: list[Constraint]
    traces: list[HoleTrace]  # Evaluation evidence

    def add_hole(self, hole: HoleMeta) -> None:
        """Register new hole with fresh ID."""
        self.holes[hole.hole_id] = hole

    def unify_type(self, var: str, typ: Type) -> Result[None, TypeError]:
        """Assign type to type variable with occurs check."""
        if occurs_check(var, typ):
            return Err(f"Occurs check: {var} in {typ}")
        self.type_vars[var].assignment = typ
        self.propagate_constraints(var)
        return Ok(None)

    def propagate_constraints(self, changed_meta: str) -> None:
        """Update constraints after meta assignment."""
        for constraint in self.constraints:
            if changed_meta in constraint.free_metas():
                constraint.simplify(self)

    def collect_hole_traces(self, hole_id: str) -> list[ValueTrace]:
        """Get all recorded values for a hole during evaluation."""
        return [t for t in self.traces if t.hole_id == hole_id]
```

**Hole Registration**:
```python
def register_hole(ctx: MetaContext, hole_id: str, kind: HoleKind,
                  typ: Type | None = None) -> HoleMeta:
    """Create and register new hole."""
    if typ is None:
        typ = fresh_type_var()  # Generate ?α

    meta = HoleMeta(
        hole_id=hole_id,
        kind=kind,
        type=typ,
        context={},  # Will be populated during type checking
        links=[],
        hints={},
    )
    ctx.add_hole(meta)
    return meta
```

### 4.4 Constraint Propagation Example

**Code**:
```specir
def summarize(doc: Str, n: Nat) : {bullets: List Str | length(bullets) = n} =
  let extracted = ?extract:function doc in
  let ranked = ?rank:function extracted in
  take n ranked

hole ?extract:function : Str -> List Str
hole ?rank:function : List Str -> List Str
```

**Constraints Generated**:
```python
# From signature
C1: ?extract : Str -> List Str
C2: ?rank : List Str -> List Str
C3: result must satisfy length(bullets) = n

# From usage in body
C4: ?extract receives doc : Str
C5: ?rank receives extracted : List Str
C6: take n ranked must produce List Str with length = n

# Propagated constraints
C7: ?rank must preserve or produce lists with length >= n
C8: ?extract must produce List Str (no length constraint yet)
```

**Filling ?extract**:

User fills: `?extract = split_sentences`

Type checker:
1. Check: `split_sentences : Str -> List Str` ✓
2. Substitute in C4: `split_sentences doc` ✓
3. Update C6: Now `take n (rank (split_sentences doc))` must have length n
4. Constraint on `?rank`: Must produce list with length >= n

**This constrains the next fill!**

---

## Part 5: Parser Implementation

### 5.1 Parsing Strategy

**Architecture**: Recursive descent parser with operator precedence and error recovery.

**Stages**:
1. **Lexer**: Source → Tokens (with spans for error reporting)
2. **Parser**: Tokens → Syntactic IR (S*)
3. **Elaborator**: Syntactic IR → Semantic IR (Core)
4. **Type Checker**: Semantic IR → Typed IR + Constraints

**Libraries**:
- **Python**: `lark-parser` for grammar-based parsing, or hand-written recursive descent
- **Rust**: `nom` or `pest` for parser combinators, `chumsky` for error recovery

### 5.2 Error Recovery

**Goal**: Parse as much as possible, report multiple errors, suggest fixes.

**Strategies**:

1. **Synchronization Tokens**: `; } end` mark safe resume points
2. **Panic Mode**: Skip tokens until synchronization point
3. **Error Productions**: Special grammar rules for common mistakes
4. **Quickfixes**: Suggest corrections based on context

**Example**:
```specir
def factorial(n: Nat) : Nat =
  if n = 0 then 1 else n * factorial(n - 1  -- Missing closing paren

-- Parser error recovery:
-- Error at line 2, col 49: Expected ')' before 'end of line'
-- Quickfix: Add ')' after 'n - 1'
```

### 5.3 Span Tracking

**Purpose**: Every AST node carries its source location for error reporting.

```python
@dataclass
class Span:
    start: Position  # (line, column)
    end: Position
    file: str

@dataclass
class Term:
    kind: TermKind  # Lambda, App, Var, Hole, etc.
    span: Span
    # ... other fields
```

**Error Reporting with Spans**:
```python
def report_type_error(term: Term, expected: Type, actual: Type):
    print(f"Type error at {term.span.file}:{term.span.start.line}:{term.span.start.column}")
    print(f"  Expected: {expected}")
    print(f"  Actual:   {actual}")
    # Use Ariadne/Miette for fancy diagnostics with source highlighting
```

### 5.4 Parser Implementation Sketch (Python)

```python
from lark import Lark, Transformer, v_args

# Grammar (EBNF)
grammar = r"""
    ?start: program

    program: declaration*

    declaration: type_decl | def_decl | entity_decl | spec_decl | hole_decl

    type_decl: "type" IDENT "=" type

    def_decl: "def" IDENT ":" type "=" term

    entity_decl: "entity" STRING ":" "{" field_decl ("," field_decl)* "}"

    field_decl: IDENT ":" type

    spec_decl: "spec" STRING ("(" parameter ("," parameter)* ")")? ":"
               ("requires:" predicate)?
               ("ensures:" predicate)?

    hole_decl: "hole" HOLE_ID ":" hole_kind (":" type)?

    hole_kind: "term" | "type" | "spec" | "entity" | "function" | "module"

    type: base_type
        | dependent_type
        | refinement_type
        | product_type
        | type_hole

    base_type: "Int" | "Str" | "Bool" | "Nat"
             | "List" type

    dependent_type: "Π" "(" IDENT ":" type ")" "." type

    refinement_type: "{" IDENT ":" type "|" predicate "}"

    product_type: type "×" type

    type_hole: HOLE_ID ":" "type"

    term: variable
        | lambda
        | application
        | let_expr
        | if_expr
        | term_hole

    variable: IDENT

    lambda: "λ" IDENT ":" type "." term

    application: term term

    let_expr: "let" IDENT "=" term "in" term

    if_expr: "if" term "then" term "else" term

    term_hole: HOLE_ID (":" "term")?

    predicate: comparison
             | conjunction
             | quantification

    comparison: term ">" term
              | term ">=" term
              | term "=" term

    conjunction: predicate "∧" predicate

    quantification: "∀" IDENT ":" type "." predicate

    parameter: IDENT ":" type

    IDENT: /[a-zA-Z_][a-zA-Z0-9_]*/
    HOLE_ID: /\?[a-zA-Z_][a-zA-Z0-9_]*/
    STRING: /"[^"]*"/

    %import common.WS
    %ignore WS
"""

parser = Lark(grammar, start='start', parser='lalr')

# Transformer to build AST
class IRTransformer(Transformer):
    @v_args(inline=True)
    def type_decl(self, name, typ):
        return TypeDecl(name=name, type=typ)

    @v_args(inline=True)
    def def_decl(self, name, typ, body):
        return DefDecl(name=name, type=typ, body=body)

    # ... more transformation rules
```

**Usage**:
```python
source = """
def factorial : Nat -> Nat =
  λn. if n = 0 then 1 else n * factorial(n - 1)
"""

tree = parser.parse(source)
ast = IRTransformer().transform(tree)
```

### 5.5 Elaboration (Syntactic → Semantic IR)

**Desugaring**:
```python
def elaborate_term(sterm: STerm) -> Term:
    """Convert syntactic term to semantic term."""
    match sterm:
        case SLambda(param, body):
            # Desugar: (x) => body  to  λx:?T. body
            param_type = infer_or_fresh_meta(param.type_annot)
            elab_body = elaborate_term(body)
            return Lambda(param=param.name, param_type=param_type, body=elab_body)

        case SApp(func, args):
            # Desugar: f(x, y)  to  (f x) y
            elab_func = elaborate_term(func)
            result = elab_func
            for arg in args:
                result = App(func=result, arg=elaborate_term(arg))
            return result

        case SHole(hole_id, kind):
            # Register hole in meta-context
            meta = register_hole(meta_ctx, hole_id, kind)
            return Hole(hole_id=hole_id, kind=kind, type=meta.type)

        # ... more cases
```

---

## Part 6: Type Checker Implementation

### 6.1 Bidirectional Algorithm

**Entry Point**:
```python
def type_check(ctx: Context, term: Term, typ: Type) -> Result[None, TypeError]:
    """Check that term has type typ in context ctx."""
    # Dispatch to check or synth based on term structure

def type_synth(ctx: Context, term: Term) -> Result[Type, TypeError]:
    """Synthesize type for term in context ctx."""
    # Dispatch based on term kind
```

**Implementation**:
```python
def type_check(ctx: Context, term: Term, expected: Type) -> Result[None, TypeError]:
    match term:
        case Lambda(param, param_type, body):
            # Check λx:A. e against A → B
            if not isinstance(expected, FunctionType):
                return Err(f"Expected function type, got {expected}")
            ctx_extended = ctx.extend(param, param_type)
            return type_check(ctx_extended, body, expected.ret)

        case Hole(hole_id, kind, _):
            # Check hole: unify hole's type with expected
            hole_meta = meta_ctx.holes[hole_id]
            unify_result = unify(hole_meta.type, expected)
            if unify_result.is_err():
                return Err(f"Cannot unify hole {hole_id} type {hole_meta.type} with {expected}")
            meta_ctx.constraints.append(Constraint(hole_id=hole_id, type=expected))
            return Ok(None)

        case _:
            # Fallback: synthesize type and check compatibility
            synth_result = type_synth(ctx, term)?
            if not subtype(synth_result, expected):
                return Err(f"Type mismatch: {synth_result} not subtype of {expected}")
            return Ok(None)

def type_synth(ctx: Context, term: Term) -> Result[Type, TypeError]:
    match term:
        case Var(name):
            typ = ctx.lookup(name)
            if typ is None:
                return Err(f"Variable {name} not in scope")
            return Ok(typ)

        case App(func, arg):
            func_type = type_synth(ctx, func)?
            if not isinstance(func_type, FunctionType):
                return Err(f"Cannot apply non-function type {func_type}")
            type_check(ctx, arg, func_type.arg)?
            # Substitute: result type is B[x := arg]
            return Ok(substitute(func_type.ret, func_type.param, arg))

        case Hole(hole_id, kind, type_annot):
            # Synthesize fresh type variable if not annotated
            if type_annot is None:
                fresh_var = fresh_type_var()
                meta_ctx.holes[hole_id].type = fresh_var
                return Ok(fresh_var)
            return Ok(type_annot)

        # ... more cases
```

### 6.2 Unification

**Purpose**: Solve type equations `T₁ = T₂` by finding substitutions for type variables.

**Algorithm** (simplified):
```python
def unify(t1: Type, t2: Type) -> Result[Subst, TypeError]:
    """Unify two types, returning substitution or error."""
    match (t1, t2):
        case (TypeVar(a), TypeVar(b)) if a == b:
            return Ok(empty_subst())

        case (TypeVar(a), t):
            if occurs_check(a, t):
                return Err(f"Occurs check: {a} in {t}")
            return Ok(subst(a, t))

        case (t, TypeVar(a)):
            if occurs_check(a, t):
                return Err(f"Occurs check: {a} in {t}")
            return Ok(subst(a, t))

        case (FunctionType(a1, r1), FunctionType(a2, r2)):
            s1 = unify(a1, a2)?
            s2 = unify(apply_subst(s1, r1), apply_subst(s1, r2))?
            return Ok(compose(s1, s2))

        case (BaseType(name1), BaseType(name2)) if name1 == name2:
            return Ok(empty_subst())

        case _:
            return Err(f"Cannot unify {t1} with {t2}")
```

### 6.3 Refinement Type Checking (SMT Integration)

**When checking `e : {x:T | φ}`**:
1. Check base type: `e : T`
2. Generate SMT query for `φ[x := e]`
3. Call Z3 solver
4. If SAT: accept
5. If UNSAT: reject with counterexample
6. If UNKNOWN: warn (timeout, undecidable theory)

**Implementation**:
```python
def check_refinement(ctx: Context, term: Term, refine: RefinementType) -> Result[None, TypeError]:
    # Step 1: Check base type
    type_check(ctx, term, refine.base)?

    # Step 2: Generate SMT query
    predicate = substitute_predicate(refine.predicate, refine.var, term)
    smt_query = encode_to_smt(ctx, predicate)

    # Step 3: Call solver
    result = z3_check(smt_query)

    match result:
        case SolverResult.SAT:
            return Ok(None)
        case SolverResult.UNSAT:
            return Err(f"Refinement violation: {predicate} is unsatisfiable")
        case SolverResult.UNKNOWN:
            warn(f"SMT solver returned UNKNOWN for {predicate}")
            return Ok(None)  # Or Err depending on strictness
```

**SMT Encoding Example**:
```python
def encode_to_smt(ctx: Context, predicate: Predicate) -> str:
    """Encode IR predicate to SMT-LIB 2.6."""
    match predicate:
        case Comparison(left, op, right):
            left_smt = encode_term_to_smt(left)
            right_smt = encode_term_to_smt(right)
            op_smt = {"<": "<", "<=": "<=", ">": ">", ">=": ">=", "=": "="}[op]
            return f"({op_smt} {left_smt} {right_smt})"

        case Conjunction(p1, p2):
            return f"(and {encode_to_smt(ctx, p1)} {encode_to_smt(ctx, p2)})"

        case Quantification("forall", var, var_type, body):
            return f"(forall (({var} {encode_type_to_smt(var_type)})) {encode_to_smt(ctx, body)})"

        # ... more cases
```

Example query for `{x: Int | x >= 0 ∧ x <= 150}`:
```smt2
(declare-const x Int)
(assert (and (>= x 0) (<= x 150)))
(check-sat)
```

---

## Part 7: IR Validator (Validation Rules, Error Messages, Quickfixes)

### 7.1 Validation Phases

**Phase 1: Syntactic Validation**
- All terms parse correctly
- No undefined identifiers
- Hole IDs are unique

**Phase 2: Type Validation**
- All terms type-check
- No unresolved type variables (unless holes)
- Dependent type indices normalize

**Phase 3: Refinement Validation**
- All refinement predicates are SAT
- No contradictory constraints

**Phase 4: Hole Validation**
- All holes have valid types
- Linked holes form DAG (no cycles)
- Hole closures are well-formed

**Phase 5: Semantic Validation**
- IntentSpec aligns with FuncSpec
- All effects are declared
- Cost/latency bounds are specified

### 7.2 Validation Rules

**Rule V1: No Orphan Holes**
```
For each hole ?h, either:
  1. ?h appears in a term, OR
  2. ?h is explicitly declared with 'hole ?h:kind'
```

**Rule V2: Hole Type Consistency**
```
If hole ?h appears with type T₁ in context C₁
and type T₂ in context C₂,
then T₁ and T₂ must unify.
```

**Rule V3: Refinement Satisfiability**
```
For each refinement {x:T | φ},
φ must be satisfiable (SMT check returns SAT or UNKNOWN, not UNSAT).
```

**Rule V4: Effect Declarations**
```
For each function f with body e,
if e uses effect ε, then f must declare ε in its type.
```

**Rule V5: Cost Bounds**
```
For each spec with cost ≤ κ,
all implementations must track and enforce κ.
```

### 7.3 Error Messages

**Example 1: Type Mismatch**
```
Error: Type mismatch in function application
  --> example.ir:5:12
   |
 5 |   let result = add "hello" 5
   |                    ^^^^^^^ Expected Int, found Str
   |
   = note: function 'add' has type Int -> Int -> Int
   = help: Did you mean to use 'concat' instead?
```

**Example 2: Refinement Violation**
```
Error: Refinement type violation
  --> example.ir:10:3
   |
10 |   let age = -5
   |             ^^ Does not satisfy {x: Int | x >= 0 ∧ x <= 150}
   |
   = note: Predicate 'x >= 0' is violated
   = help: Ensure input is non-negative
```

**Example 3: Hole Cycle**
```
Error: Cycle detected in hole dependencies
  --> example.ir:15:3
   |
15 |   hole ?a:term [links={?b}]
   |        ^^ Hole ?a
16 |   hole ?b:term [links={?a}]
   |        ^^ Hole ?b
   |
   = note: Cycle: ?a -> ?b -> ?a
   = help: Remove one of the links to break the cycle
```

### 7.4 Quickfixes

**Quickfix 1: Add Missing Type Annotation**
```
Warning: Type inference failed for hole ?impl
  --> example.ir:20:3
   |
20 |   ?impl:term
   |   ^^^^^^^^^^ Cannot infer type
   |
   = help: Add type annotation: ?impl:term : Int -> Int
```

**Quickfix 2: Suggest Valid Fits**
```
Hole: ?transform:term : Int -> Int
  --> example.ir:25:10
   |
25 |   let y = ?transform x
   |           ^^^^^^^^^^ Hole needs to be filled
   |
   = suggestion 1: (λn. n * 2)      -- In scope, matches signature
   = suggestion 2: (λn. abs n)      -- stdlib function
   = suggestion 3: (λn. n + 1)      -- Simple arithmetic
```

**Quickfix 3: Fix Refinement**
```
Error: Cannot prove postcondition
  --> example.ir:30:1
   |
30 | def factorial : Nat -> {x: Nat | x > 0}
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Postcondition may not hold
   |
   = note: Cannot prove 'factorial(0) > 0' from implementation
   = help: Change postcondition to: {x: Nat | x >= 1}
         OR ensure factorial(0) returns value > 0
```

### 7.5 Validator Implementation Sketch

```python
class IRValidator:
    def __init__(self, meta_ctx: MetaContext):
        self.meta_ctx = meta_ctx
        self.errors: list[ValidationError] = []

    def validate(self, program: Program) -> ValidationReport:
        """Run all validation phases."""
        self.validate_syntax(program)
        self.validate_types(program)
        self.validate_refinements(program)
        self.validate_holes(program)
        self.validate_semantics(program)

        return ValidationReport(
            errors=self.errors,
            warnings=self.warnings,
            quickfixes=self.quickfixes,
        )

    def validate_holes(self, program: Program):
        """Check hole-specific rules."""
        # V1: No orphan holes
        declared_holes = {h.hole_id for h in program.hole_decls}
        used_holes = collect_used_holes(program)
        orphans = declared_holes - used_holes
        for orphan in orphans:
            self.errors.append(ValidationError(
                message=f"Hole {orphan} declared but never used",
                span=find_hole_decl_span(program, orphan),
                quickfix=f"Remove unused hole declaration",
            ))

        # V2: Hole type consistency
        for hole_id in used_holes:
            types = collect_hole_types(program, hole_id)
            if len(types) > 1:
                unify_result = unify_all(types)
                if unify_result.is_err():
                    self.errors.append(ValidationError(
                        message=f"Hole {hole_id} used with inconsistent types: {types}",
                        span=find_hole_usage_spans(program, hole_id),
                    ))

        # V4: Check for cycles in hole links
        hole_graph = build_hole_dependency_graph(program)
        cycles = detect_cycles(hole_graph)
        for cycle in cycles:
            self.errors.append(ValidationError(
                message=f"Cycle in hole dependencies: {' -> '.join(cycle)}",
                span=find_cycle_spans(program, cycle),
                quickfix=f"Remove link to break cycle",
            ))
```

---

## Part 8: JSON Schema & Serialization

### 8.1 JSON Schema (Excerpt)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IR 0.9 Program",
  "type": "object",
  "required": ["version", "declarations"],
  "properties": {
    "version": {"type": "string", "const": "0.9"},
    "declarations": {
      "type": "array",
      "items": {"$ref": "#/definitions/Declaration"}
    }
  },
  "definitions": {
    "Declaration": {
      "oneOf": [
        {"$ref": "#/definitions/TypeDecl"},
        {"$ref": "#/definitions/DefDecl"},
        {"$ref": "#/definitions/EntityDecl"},
        {"$ref": "#/definitions/SpecDecl"},
        {"$ref": "#/definitions/IntentDecl"},
        {"$ref": "#/definitions/HoleDecl"}
      ]
    },
    "TypeDecl": {
      "type": "object",
      "required": ["kind", "name", "type"],
      "properties": {
        "kind": {"const": "TypeDecl"},
        "name": {"type": "string"},
        "type": {"$ref": "#/definitions/Type"}
      }
    },
    "DefDecl": {
      "type": "object",
      "required": ["kind", "name", "type", "body"],
      "properties": {
        "kind": {"const": "DefDecl"},
        "name": {"type": "string"},
        "type": {"$ref": "#/definitions/Type"},
        "body": {"$ref": "#/definitions/Term"}
      }
    },
    "HoleDecl": {
      "type": "object",
      "required": ["kind", "holeId", "holeKind"],
      "properties": {
        "kind": {"const": "HoleDecl"},
        "holeId": {"type": "string", "pattern": "^\\?[a-zA-Z_][a-zA-Z0-9_]*$"},
        "holeKind": {"enum": ["term", "type", "spec", "entity", "function", "module"]},
        "type": {"$ref": "#/definitions/Type"},
        "links": {
          "type": "array",
          "items": {"type": "string", "pattern": "^\\?[a-zA-Z_][a-zA-Z0-9_]*$"}
        },
        "hints": {"type": "object"}
      }
    },
    "Type": {
      "oneOf": [
        {"$ref": "#/definitions/BaseType"},
        {"$ref": "#/definitions/DependentFunctionType"},
        {"$ref": "#/definitions/RefinementType"},
        {"$ref": "#/definitions/ProductType"},
        {"$ref": "#/definitions/TypeHole"}
      ]
    },
    "BaseType": {
      "type": "object",
      "required": ["kind", "name"],
      "properties": {
        "kind": {"const": "BaseType"},
        "name": {"enum": ["Int", "Str", "Bool", "Nat", "Float", "Bytes"]}
      }
    },
    "DependentFunctionType": {
      "type": "object",
      "required": ["kind", "param", "paramType", "returnType"],
      "properties": {
        "kind": {"const": "DependentFunctionType"},
        "param": {"type": "string"},
        "paramType": {"$ref": "#/definitions/Type"},
        "returnType": {"$ref": "#/definitions/Type"}
      }
    },
    "RefinementType": {
      "type": "object",
      "required": ["kind", "var", "baseType", "predicate"],
      "properties": {
        "kind": {"const": "RefinementType"},
        "var": {"type": "string"},
        "baseType": {"$ref": "#/definitions/Type"},
        "predicate": {"$ref": "#/definitions/Predicate"}
      }
    },
    "TypeHole": {
      "type": "object",
      "required": ["kind", "holeId"],
      "properties": {
        "kind": {"const": "TypeHole"},
        "holeId": {"type": "string", "pattern": "^\\?[a-zA-Z_][a-zA-Z0-9_]*$"}
      }
    },
    "Term": {
      "oneOf": [
        {"$ref": "#/definitions/Var"},
        {"$ref": "#/definitions/Lambda"},
        {"$ref": "#/definitions/App"},
        {"$ref": "#/definitions/Let"},
        {"$ref": "#/definitions/If"},
        {"$ref": "#/definitions/Hole"}
      ]
    },
    "Hole": {
      "type": "object",
      "required": ["kind", "holeId", "holeKind"],
      "properties": {
        "kind": {"const": "Hole"},
        "holeId": {"type": "string"},
        "holeKind": {"enum": ["term", "type", "spec", "entity", "function", "module"]},
        "type": {"$ref": "#/definitions/Type"},
        "links": {"type": "array", "items": {"type": "string"}},
        "span": {"$ref": "#/definitions/Span"}
      }
    },
    "Span": {
      "type": "object",
      "required": ["start", "end"],
      "properties": {
        "start": {"$ref": "#/definitions/Position"},
        "end": {"$ref": "#/definitions/Position"},
        "file": {"type": "string"}
      }
    },
    "Position": {
      "type": "object",
      "required": ["line", "column"],
      "properties": {
        "line": {"type": "integer", "minimum": 1},
        "column": {"type": "integer", "minimum": 1}
      }
    }
  }
}
```

### 8.2 Serialization Example

**IR Program**:
```specir
def factorial : Nat -> Nat =
  λn. if n = 0 then 1 else n * factorial(n - 1)

hole ?impl:term : List Str
```

**JSON Serialization**:
```json
{
  "version": "0.9",
  "declarations": [
    {
      "kind": "DefDecl",
      "name": "factorial",
      "type": {
        "kind": "DependentFunctionType",
        "param": "_",
        "paramType": {"kind": "BaseType", "name": "Nat"},
        "returnType": {"kind": "BaseType", "name": "Nat"}
      },
      "body": {
        "kind": "Lambda",
        "param": "n",
        "paramType": {"kind": "BaseType", "name": "Nat"},
        "body": {
          "kind": "If",
          "condition": {
            "kind": "App",
            "func": {
              "kind": "App",
              "func": {"kind": "Var", "name": "="},
              "arg": {"kind": "Var", "name": "n"}
            },
            "arg": {"kind": "IntLit", "value": 0}
          },
          "thenBranch": {"kind": "IntLit", "value": 1},
          "elseBranch": {
            "kind": "App",
            "func": {
              "kind": "App",
              "func": {"kind": "Var", "name": "*"},
              "arg": {"kind": "Var", "name": "n"}
            },
            "arg": {
              "kind": "App",
              "func": {"kind": "Var", "name": "factorial"},
              "arg": {
                "kind": "App",
                "func": {
                  "kind": "App",
                  "func": {"kind": "Var", "name": "-"},
                  "arg": {"kind": "Var", "name": "n"}
                },
                "arg": {"kind": "IntLit", "value": 1}
              }
            }
          }
        }
      }
    },
    {
      "kind": "HoleDecl",
      "holeId": "?impl",
      "holeKind": "term",
      "type": {
        "kind": "App",
        "func": {"kind": "BaseType", "name": "List"},
        "arg": {"kind": "BaseType", "name": "Str"}
      },
      "links": [],
      "hints": {}
    }
  ]
}
```

---

## Part 9: Examples (Worked Examples from IR_SPECIFICATION.md)

### 9.1 Example 1: Summarizer with Dependent Holes

**Spec-IR**:
```specir
intent "Summarize document":
  inputs:  doc: Str, audience: Str, n: Nat
  outputs: bullets: List Str
  goals:
    - "Produce exactly n bullet points"
    - "Each bullet appropriate for audience"
  constraints:
    - "Latency < 5s"
    - "Cost < $0.01"

spec "GoodFor"(audience: Str, bullet: Str):
  ensures: sentiment(bullet, audience) >= 0.6

def summarize(doc: Str, audience: Str, n: Nat) :
  {bullets: List Str | length(bullets) = n ∧ ∀b ∈ bullets. GoodFor(audience, b)} =
  ?impl:term [links={?goodFor, ?extract, ?rank}]

hole ?goodFor:function : (Str, Str) -> Bool
hole ?extract:function : Str -> List Str
hole ?rank:function : List Str -> List Str
```

**Constraint Propagation**:

1. **From signature**: `?impl : {bullets: List Str | length(bullets) = n ∧ ∀b. GoodFor(audience, b)}`
2. **From links**: `?impl` uses `?goodFor`, `?extract`, `?rank`
3. **Constraint on ?goodFor**: Must implement `GoodFor` spec → signature `(Str, Str) -> Bool`
4. **Constraint on ?extract**: Must extract candidates from `doc: Str` → signature `Str -> List Str`
5. **Constraint on ?rank**: Must rank/filter to produce exactly `n` items → signature `List Str -> List Str`

**Filling Process**:

Step 1: User fills `?extract`:
```specir
?extract = split_sentences  -- Str -> List Str
```

Type checker validates, updates constraints.

Step 2: User fills `?rank`:
```specir
?rank = λxs. take n (sort_by_relevance xs audience)
```

Constraint: Must produce list with `length = n`.

Step 3: AI suggests `?goodFor`:
```specir
?goodFor = λaudience, bullet. sentiment_score(bullet, audience) >= 0.6
```

Step 4: Fill `?impl` (AI-generated or manual):
```specir
?impl = λdoc, audience, n.
  let candidates = ?extract doc in
  let ranked = ?rank candidates in
  ranked
```

**Verification**: Type checker + SMT solver verify:
- `length(ranked) = n` ✓ (from `take n ...`)
- `∀b ∈ ranked. GoodFor(audience, b)` ✓ (from `sort_by_relevance` + `?goodFor`)

### 9.2 Example 2: Entity Schema Unknown

**Spec-IR**:
```specir
entity "CustomerProfile":
  fields:
    id:    {x: Int | x >= 0}
    email: {s: Str | is_valid_email(s)}
    plan:  ?Plan:type  -- Type hole: what is Plan?

spec "PlanConstraints"(p: ?Plan):
  ensures: valid_plan(p)

hole ?Plan:type

def upgrade_plan(customer: CustomerProfile, new_plan: ?Plan) : Result CustomerProfile Error =
  if PlanConstraints(new_plan)
    then Ok({...customer, plan: new_plan})
    else Err("Invalid plan")
```

**Valid Fits for ?Plan**:

Suggestions ranked by type + constraints:
1. `enum {Free, Pro, Enterprise}` — Most specific, common pattern
2. `{s: Str | s ∈ {"free", "pro", "enterprise"}}` — Refinement type with validation
3. `Str` — Least specific, relies on `valid_plan` predicate

User selects option 1:
```specir
type Plan = Free | Pro | Enterprise

spec "PlanConstraints"(p: Plan):
  ensures: p ∈ {Free, Pro, Enterprise}  -- Always true for ADT
```

### 9.3 Example 3: Service Pipeline

**Spec-IR**:
```specir
entity "Invoice": {
  customer: CustomerProfile,
  items: List Item,
  total: {x: Float | x >= 0.0}
}

def renderInvoice(cust: CustomerProfile, items: List Item) :
  {pdf: Bytes | size(pdf) <= 2*MB} =
  ?render:term

requires: ∀item ∈ items. valid_item(item)
ensures:  auditTrail(pdf, cust)
effects:  IO, Network
cost:     <= 0.001
latency:  <= 2000

hole ?render:term : CustomerProfile -> List Item -> Bytes
  [hints={
    "target_format": "PDF/A-1b",
    "template": "invoice_template_v2.html"
  }]
```

**Constraints on ?render**:
- Input: `CustomerProfile`, `List Item`
- Output: `Bytes` with `size <= 2*MB`
- Must satisfy: `auditTrail(pdf, cust)`
- Performance: `latency <= 2000ms`

**AI Suggestion**:
```specir
?render = λcust, items.
  let html = render_template("invoice_template_v2.html", {cust, items}) in
  let pdf_bytes = html_to_pdf(html, format="PDF/A-1b") in
  let signed = sign_pdf(pdf_bytes, cust.id) in
  signed
```

Validation:
- Size check: `assert size(signed) <= 2*MB` (runtime or static estimate)
- Audit trail: `sign_pdf` ensures `auditTrail` property
- Latency: Profiling shows ~1500ms (within budget)

---

## Part 10: Testing Strategy

### 10.1 Parser Tests

**Unit Tests**:
```python
def test_parse_type_decl():
    source = "type Nat = {x: Int | x >= 0}"
    ast = parse(source)
    assert isinstance(ast.declarations[0], TypeDecl)
    assert ast.declarations[0].name == "Nat"
    assert isinstance(ast.declarations[0].type, RefinementType)

def test_parse_hole_decl():
    source = "hole ?impl:term : List Str"
    ast = parse(source)
    hole = ast.declarations[0]
    assert hole.hole_id == "?impl"
    assert hole.hole_kind == HoleKind.TERM
    assert hole.type == ListType(BaseType("Str"))

def test_parse_dependent_function():
    source = "Π(n:Nat). Vec n T"
    typ = parse_type(source)
    assert isinstance(typ, DependentFunctionType)
    assert typ.param == "n"
    assert typ.param_type == BaseType("Nat")
```

**Property-Based Tests** (using Hypothesis):
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100, alphabet=string.ascii_lowercase))
def test_parse_identifier_roundtrip(identifier):
    """Any valid identifier should parse and pretty-print identically."""
    source = f"def {identifier} : Int = 42"
    ast = parse(source)
    pretty = pretty_print(ast)
    assert identifier in pretty

@given(st.integers(min_value=0, max_value=1000))
def test_parse_nat_refinement(n):
    """Nat refinement should accept non-negative integers."""
    source = f"type Nat = {{x: Int | x >= 0}}"
    ast = parse(source)
    # Validate that n satisfies refinement
    assert check_refinement(n, ast.declarations[0].type).is_ok()
```

### 10.2 Type Checker Tests

**Unit Tests**:
```python
def test_typecheck_lambda():
    term = Lambda("x", BaseType("Int"), Var("x"))
    typ = FunctionType(BaseType("Int"), BaseType("Int"))
    ctx = empty_context()
    assert type_check(ctx, term, typ).is_ok()

def test_typecheck_hole_unification():
    hole = Hole("?h", HoleKind.TERM, None)
    typ = BaseType("Int")
    ctx = empty_context()
    result = type_check(ctx, hole, typ)
    assert result.is_ok()
    assert meta_ctx.holes["?h"].type == BaseType("Int")

def test_typecheck_refinement_violation():
    # age = -5, should fail {x: Int | x >= 0}
    term = IntLit(-5)
    typ = RefinementType("x", BaseType("Int"), Comparison(Var("x"), ">=", IntLit(0)))
    ctx = empty_context()
    result = type_check(ctx, term, typ)
    assert result.is_err()
    assert "Refinement violation" in result.error()
```

**Integration Tests**:
```python
def test_typecheck_factorial():
    source = """
    def factorial : Nat -> Nat =
      λn. if n = 0 then 1 else n * factorial(n - 1)
    """
    ast = parse(source)
    result = type_check_program(ast)
    assert result.is_ok()

def test_typecheck_summarizer_with_holes():
    source = """
    def summarize(doc: Str, n: Nat) : {bullets: List Str | length(bullets) = n} =
      ?impl:term [links={?extract, ?rank}]

    hole ?extract:function : Str -> List Str
    hole ?rank:function : List Str -> List Str
    """
    ast = parse(source)
    result = type_check_program(ast)
    assert result.is_ok()
    assert "?impl" in meta_ctx.holes
    assert "?extract" in meta_ctx.holes
    assert "?rank" in meta_ctx.holes
```

### 10.3 Validation Tests

**Unit Tests**:
```python
def test_validate_no_orphan_holes():
    program = parse("hole ?unused:term : Int")
    validator = IRValidator(meta_ctx)
    report = validator.validate(program)
    assert len(report.errors) == 1
    assert "never used" in report.errors[0].message

def test_validate_hole_cycle():
    source = """
    hole ?a:term [links={?b}]
    hole ?b:term [links={?a}]
    """
    program = parse(source)
    validator = IRValidator(meta_ctx)
    report = validator.validate(program)
    assert any("Cycle" in err.message for err in report.errors)

def test_validate_refinement_satisfiability():
    source = "type Invalid = {x: Int | x > 0 ∧ x < 0}"
    program = parse(source)
    validator = IRValidator(meta_ctx)
    report = validator.validate(program)
    assert any("unsatisfiable" in err.message.lower() for err in report.errors)
```

### 10.4 End-to-End Tests

**Scenario: Parse → Type Check → Validate → Fill Holes → Generate Code**:
```python
def test_e2e_summarizer():
    # Step 1: Parse IR with holes
    source = """
    def summarize(doc: Str, n: Nat) : List Str =
      ?impl:term [links={?extract, ?rank}]

    hole ?extract:function : Str -> List Str
    hole ?rank:function : List Str -> List Str
    """
    ast = parse(source)

    # Step 2: Type check
    type_result = type_check_program(ast)
    assert type_result.is_ok()

    # Step 3: Validate
    validator = IRValidator(meta_ctx)
    validation_report = validator.validate(ast)
    assert len(validation_report.errors) == 0

    # Step 4: Fill holes (manual for test)
    fill_hole("?extract", Lambda("doc", BaseType("Str"), App(Var("split_sentences"), Var("doc"))))
    fill_hole("?rank", Lambda("xs", ListType(BaseType("Str")), App(Var("take"), IntLit(5), Var("xs"))))
    fill_hole("?impl", Lambda("doc", BaseType("Str"), Lambda("n", BaseType("Nat"),
        Let("extracted", App(Var("?extract"), Var("doc")),
            Let("ranked", App(Var("?rank"), Var("extracted")),
                Var("ranked"))))))

    # Step 5: Re-validate after fills
    validation_report2 = validator.validate(ast)
    assert len(validation_report2.errors) == 0

    # Step 6: Generate Python code
    python_code = generate_python(ast)
    assert "def summarize(doc: str, n: int) -> list[str]:" in python_code
    assert "split_sentences(doc)" in python_code
```

### 10.5 Performance Tests

**Benchmark: Type Checking Speed**:
```python
import time

def benchmark_typecheck_large_program():
    # Generate program with 1000 function definitions
    source = "\n".join([
        f"def func{i} : Int -> Int = λx. x + {i}"
        for i in range(1000)
    ])
    ast = parse(source)

    start = time.time()
    type_check_program(ast)
    elapsed = time.time() - start

    assert elapsed < 1.0  # Should complete in < 1 second
    print(f"Type checked 1000 functions in {elapsed:.3f}s")
```

**Benchmark: SMT Solver Latency**:
```python
def benchmark_refinement_checking():
    # Check 100 refinement types
    refinements = [
        RefinementType("x", BaseType("Int"), Comparison(Var("x"), ">=", IntLit(i)))
        for i in range(100)
    ]

    start = time.time()
    for refine in refinements:
        check_refinement(IntLit(50), refine)
    elapsed = time.time() - start

    assert elapsed < 0.5  # Should complete in < 500ms
    print(f"Checked 100 refinements in {elapsed:.3f}s")
```

---

## Conclusion

This RFC has provided a comprehensive technical deep-dive into **IR 0.9 Core**:

1. **Philosophy**: Typed holes as first-class, bidirectional typing + refinements, live execution around holes
2. **Grammar**: Formal BNF/EBNF for types, terms, predicates, declarations
3. **Type System**: Dependent types (Π), refinement types ({x:T | φ}), six hole kinds, meta-context
4. **Typed Holes**: Term, type, spec, entity, function, module holes with closures and constraint propagation
5. **Parser**: Recursive descent with error recovery, span tracking, elaboration
6. **Type Checker**: Bidirectional algorithm, unification, occurs check, SMT integration
7. **Validator**: Five validation phases, error messages with spans, quickfixes
8. **Serialization**: JSON schema for IR 0.9 programs
9. **Examples**: Worked examples from IR_SPECIFICATION.md
10. **Testing**: Parser, type checker, validator, E2E, performance tests

**Next Steps**:
- **RFC_CONSTRAINT_SOLVER.md**: Deep dive into Z3 integration, SMT encoding, solver selection
- **RFC_LLM_ORCHESTRATION.md**: DSPy signatures, Pydantic AI graphs, provider routing
- **RFC_SESSION_STORAGE.md**: Persistence, versioning, rollback, RLS policies

**Implementation Status**:
- Parser (H9): ✅ RESOLVED (Phase 2)
- Validator (H11): ✅ RESOLVED (Phase 2)
- Type checker: Partial (basic bidirectional, refinements pending full SMT integration)
- Hole closures: Pending (Phase 3)

---

**Document Status**: Draft RFC
**Authors**: Codelift Team
**Last Updated**: 2025-10-21
**Next Review**: After Phase 3 implementation (Optimization)
