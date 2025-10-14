# IR-Driven Constrained Generation Research

**Version**: 1.1
**Date**: October 14, 2025
**Status**: Phase 1.5 - Foundation Research (Updated with ChatLSP findings)
**Purpose**: Understand how lift-sys's structured IR can drive constrained LLM generation

---

## Executive Summary

lift-sys's Intermediate Representation (IR) is uniquely positioned to drive high-quality constrained code generation. The IR's structured format—with explicit types, typed holes, assertions, and provenance—provides precisely the information needed to constrain LLM generation, verify correctness, and optimize performance through parallel speculative decoding.

**Key Insight**: The IR is not just a specification format—it's a rich constraint graph that can guide every stage of generation:
- **Type constraints** → Token masking during generation
- **Assertions** → SMT verification checkpoints
- **Typed holes** → Structured ambiguity resolution
- **Dependent clauses** → Parallel speculative exploration of valid paths

**Actionable Findings**: Recent research (2024-2025) shows that type-constrained generation reduces compilation errors by 50%, SMT-LLM coupling enables formal verification during generation, and parallel speculative decoding with tree search can explore constraint-satisfying paths efficiently.

---

## Part 1: The IR as a Constraint Graph

### 1.1 IR Structure Review

lift-sys's IR provides several constraint mechanisms:

```python
@dataclass
class TypedHole:
    identifier: str              # Unique hole identifier
    type_hint: str              # Type constraint (e.g., "list[int]", "str | None")
    description: str            # Natural language intent
    constraints: dict[str, str] # Additional constraints (e.g., {"range": "0..100"})
    kind: HoleKind             # INTENT | PARAM_TYPE | RETURN_TYPE | ASSERTION

@dataclass
class AssertClause:
    predicate: str              # Formal assertion (e.g., "result > 0")
    rationale: str | None       # Why this constraint exists
    holes: list[TypedHole]      # Holes within this assertion
    provenance: Provenance      # Origin and confidence

@dataclass
class Parameter:
    name: str
    type_hint: str              # Type constraint for parameter
    description: str            # Semantic meaning

@dataclass
class SigClause:
    name: str
    parameters: list[Parameter] # Typed parameters
    returns: str                # Return type constraint
    rationale: str | None       # Why this signature
```

**Constraint Types in IR**:
1. **Type Constraints**: `type_hint` on parameters, returns, typed holes
2. **Logical Constraints**: `predicate` in assertions (SMT-checkable)
3. **Semantic Constraints**: `description` and `rationale` (natural language)
4. **Structural Constraints**: Function signatures, parameter relationships
5. **Dependency Constraints**: Multiple AssertClauses that reference each other

### 1.2 From IR to Generation Constraints

The IR provides a natural mapping to generation constraints:

| IR Element | Generation Constraint | Enforcement Mechanism |
|------------|----------------------|----------------------|
| `Parameter.type_hint` | Valid tokens for parameter types | Token masking / grammar rules |
| `SigClause.returns` | Valid return type tokens | Type system automaton |
| `AssertClause.predicate` | SMT-checkable logical formula | Z3 verification checkpoint |
| `TypedHole.constraints` | Custom constraint predicates | Runtime validation or SMT |
| `IntentClause.description` | Semantic guidance | Prompt engineering + verification |
| Multiple AssertClauses | Conjunction of constraints | Parallel exploration of satisfying paths |

**Key Observation**: The IR provides both **hard constraints** (types, assertions) and **soft constraints** (descriptions, rationale) that can guide generation at different levels.

---

## Part 2: Type-Constrained Code Generation

### 2.1 Recent Research: Prefix Automata Approach

**Paper**: "Type-Constrained Code Generation with Prefix Automata" (2025)
**Source**: arXiv:2504.09246

**Core Idea**: Build a prefix automaton from the type system rules, then use it to mask invalid tokens during LLM generation.

**Key Findings**:
- Reduces compilation errors by **50%** compared to unconstrained generation
- Adds minimal latency overhead (<5% slowdown)
- Works with any decoder-based LLM (including API-based models with logit bias)

**How It Works**:
1. Extract type system rules (e.g., Python type grammar, function signature constraints)
2. Build prefix automaton that accepts only syntactically valid type expressions
3. At each generation step, mask tokens that would violate type constraints
4. LLM samples from remaining valid tokens

**Application to lift-sys**:

Given an IR SigClause:
```python
SigClause(
    name="add_numbers",
    parameters=[
        Parameter(name="a", type_hint="int", description="First number"),
        Parameter(name="b", type_hint="int", description="Second number"),
    ],
    returns="int",
    rationale="Simple addition function"
)
```

The type-constrained generator would:
1. Build automaton for Python function signature grammar
2. Enforce `int` type for parameters `a` and `b`
3. Enforce `int` return type
4. Mask tokens that would generate invalid signatures like:
   - `def add_numbers(a: str, b: int)` ❌ (violates `a: int`)
   - `def add_numbers(a, b)` ❌ (missing type hints)
   - `def add_numbers(a: int, b: int) -> str` ❌ (violates return type)

**Benefits for lift-sys**:
- **Guarantee syntactic validity**: Generated code always compiles
- **Type safety**: Parameters and returns match IR specification
- **Fast validation**: No need for post-generation type checking
- **Reduced retries**: Fewer LLM calls due to type errors

### 2.2 IR JSON Schema Enforcement

The IR itself is structured JSON. Constrained generation ensures the IR is always valid:

**Use Case**: Prompt → IR translation

Given a natural language prompt:
> "Write a function that takes a list of numbers and returns the average"

The constrained generator:
1. Loads IR JSON schema (IntentClause, SigClause, AssertClause structure)
2. Builds grammar/automaton for valid IR JSON
3. Generates IR tokens while ensuring:
   - Valid JSON structure
   - Required fields present (`name`, `parameters`, `returns`)
   - Type hints are valid Python types
   - Assertions are well-formed predicates

**Result**: 100% valid IR, no parsing errors, no retries needed.

### 2.3 Implementation Options

**Option 1: llguidance + vLLM**
- Pros: Tight integration, low latency, full control
- Cons: Requires self-hosted LLM infrastructure
- Best for: Production deployment with high volume

**Option 2: Grammar-based sampling with API models**
- Pros: Works with Anthropic/OpenAI APIs
- Cons: Limited to logit bias (less expressive than full token masking)
- Best for: Early prototyping, low-volume use

**Option 3: xgrammar + MLC-LLM**
- Pros: Adaptive caching, multi-language support
- Cons: Another infrastructure dependency
- Best for: Multi-language code generation (Python, TypeScript, Rust)

### 2.4 Recent Research: Static Contextualization with Typed Holes

**Paper**: "Statically Contextualizing Large Language Models with Typed Holes" (September 2024)
**Source**: arXiv:2409.00921v1
**Authors**: Andrew Blinn, Xiang Li, June Hyung Kim, Cyrus Omar (University of Michigan)

**Core Idea**: Enhance LLM code generation by providing static semantic context from language servers, not just syntactic constraints.

**Key Insight**: "AIs need IDEs, too" - LLMs benefit from the same type information and error feedback that human developers get from IDEs.

#### How It Works

**ChatLSP Protocol** (Conservative extension to Language Server Protocol):
1. **`expectedType`**: Returns the expected type at cursor/typed hole
2. **`retrieveRelevantTypes`**: Returns relevant type definitions from codebase
3. **`retrieveRelevantHeaders`**: Returns relevant function signatures
4. **`errorReport`**: Provides static analysis errors for correction

**Iterative Error Correction Workflow**:
```
Generate code from context
    ↓
Query language server for static errors
    ↓
If errors: Send error messages back to LLM
    ↓
LLM attempts to correct the code
    ↓
Repeat (up to 2 times to limit latency)
```

#### Quantitative Results

**GPT-4 on Hazel language**:
- No context: Very poor performance
- Types only: Significant improvement
- Types + Function Headers: **~3x improvement** in correctness
- Types + Headers + Error Correction: **Additional 1.5x improvement**

**Total improvement: ~4.5x correctness** compared to no context

#### Application to lift-sys

**Connection to lift-sys's TypedHoles**:
- **Hazel's typed holes**: Placeholders in incomplete code with known expected types
- **lift-sys's TypedHoles**: Ambiguities in specifications with constraints
- **Synergy**: When generating code from lift-sys IR, query language server for expected types at TypedHole locations

**Integration with IR-Driven Generation**:

Given lift-sys IR with TypedHole:
```python
SigClause(
    name="process_data",
    parameters=[
        Parameter(name="data", type_hint="???", description="User input"),
    ],
    returns="dict[str, Any]",
),
TypedHole(
    identifier="data_type",
    type_hint="str | dict | list",
    description="Unclear input format",
    constraints={"format": "JSON-serializable"},
)
```

**ChatLSP-Enhanced Generation Workflow**:
1. **Generate initial code** from IR (with TypedHole)
2. **Query language server** for expected type at hole location
3. **Retrieve relevant type definitions** from codebase context
4. **Retrieve relevant function headers** that work with these types
5. **Generate complete code** with richer semantic context
6. **Check for static errors** via language server
7. **If errors**: Send errors back to LLM, regenerate (up to 2 iterations)

**Example Generation Flow**:
```python
# Step 1: Initial generation with TypedHole
def process_data(data: ???) -> dict[str, Any]:
    # TypedHole: Need to determine data type
    pass

# Step 2: Query ChatLSP for context
expected_type = chatLSP.expectedType(cursor_position)  # Returns: str | dict | list
relevant_types = chatLSP.retrieveRelevantTypes()       # Returns: JSONType definitions
relevant_headers = chatLSP.retrieveRelevantHeaders()   # Returns: json.loads, json.dumps

# Step 3: Generate with context
def process_data(data: str | dict | list) -> dict[str, Any]:
    if isinstance(data, str):
        return json.loads(data)  # From relevant headers
    elif isinstance(data, dict):
        return data
    else:
        raise TypeError(f"Unsupported type: {type(data)}")

# Step 4: Check for errors
errors = chatLSP.errorReport()  # Returns: "json not imported"

# Step 5: Correct
import json

def process_data(data: str | dict | list) -> dict[str, Any]:
    if isinstance(data, str):
        return json.loads(data)
    elif isinstance(data, dict):
        return data
    else:
        raise TypeError(f"Unsupported type: {type(data)}")
```

#### Benefits for lift-sys

1. **Semantic Type Information**: Beyond syntax, get actual type expectations from codebase
2. **Contextual Function Headers**: Suggest relevant functions based on types (3x improvement)
3. **Iterative Error Correction**: Catch semantic errors early (1.5x improvement)
4. **Reduced Hallucination**: Grounded in actual codebase types, not just training data
5. **Better TypedHole Resolution**: Use language server to narrow ambiguity space

#### Complementary to Constrained Generation

**ChatLSP vs. Constrained Generation**:
- **Constrained generation** (llguidance/AICI/xgrammar): Prevents syntactic errors
- **ChatLSP**: Catches semantic errors and provides context

**Combined Approach**:
```
IR with TypedHole
    ↓
[Constrained Generation] Enforce syntax + types
    ↓
Syntactically valid code with type hints
    ↓
[ChatLSP] Provide semantic context + error correction
    ↓
Semantically valid code that fits codebase
```

**Synergy**:
- Constrained generation ensures syntax is valid (no parsing errors)
- ChatLSP ensures semantics are correct (no type errors, contextually appropriate)
- Together: **Syntax-valid + Type-correct + Contextually-appropriate code**

#### Implementation Options

**Option 1: Python Language Server (Pyright/Pylance)**
- Pros: Mature, widely used, excellent type inference
- Cons: Need to implement ChatLSP extensions
- Best for: Python code generation from IR

**Option 2: Custom Language Server for lift-sys IR**
- Pros: Full control, can integrate IR constraints directly
- Cons: Significant engineering effort
- Best for: Long-term, if language-agnostic IR generation is goal

**Option 3: Hybrid Approach**
- Pros: Use existing language servers for semantic context, constrained generation for syntax
- Cons: Integration complexity
- Best for: Near-term implementation with maximum benefit

#### Integration Path

**Short-term (2-4 weeks)**:
1. Integrate Pyright as language server for Python code generation
2. Query for type errors after generating code from IR
3. Use error messages to refine generation (1-2 iterations)

**Medium-term (4-8 weeks)**:
1. Implement ChatLSP extensions for Pyright
2. Query `expectedType` at TypedHole locations
3. Retrieve relevant type definitions and function headers
4. Use context to improve initial generation quality

**Long-term (3-6 months)**:
1. Build custom language server that understands lift-sys IR
2. Provide IR-aware type inference and error checking
3. Enable bidirectional feedback: language server ↔ IR ↔ code

---

## Part 3: SMT-Constrained Generation

### 3.1 Recent Research: LLM + SMT Solver Tight Coupling

**Papers**:
- "Loop Invariant Generation with LLM and SMT Solver" (2024)
- "Hardware Verification Assertions with LLM-SMT Co-Generation" (2024)

**Core Idea**: Interleave LLM generation with SMT solver verification, using counterexamples to guide generation.

**How It Works**:
1. LLM generates candidate assertion/code
2. SMT solver checks satisfiability
3. If unsatisfiable, solver provides counterexample
4. LLM regenerates using counterexample as feedback
5. Iterate until solver confirms satisfiability

**Application to lift-sys**:

Given IR with assertions:
```python
AssertClause(predicate="a > 0 and b > 0", rationale="Only positive integers"),
AssertClause(predicate="result == a + b", rationale="Correct addition"),
AssertClause(predicate="result > 0", rationale="Result is positive"),
```

**Traditional Approach** (current lift-sys):
1. Generate code separately
2. Inject assertions as runtime checks
3. Hope code satisfies assertions

**SMT-Constrained Approach**:
1. Convert assertions to Z3 constraints:
   ```python
   a, b, result = z3.Ints('a b result')
   solver.add(a > 0, b > 0, result == a + b, result > 0)
   ```
2. Generate code with SMT verification checkpoints:
   ```python
   # Generation step 1: function signature
   def add_numbers(a: int, b: int) -> int:
   # SMT check: Can we satisfy assertions with this signature?

   # Generation step 2: precondition checks
   if a <= 0 or b <= 0:
       raise ValueError("Inputs must be positive")
   # SMT check: Does this enforce a > 0 and b > 0?

   # Generation step 3: computation
   result = a + b
   # SMT check: Does result == a + b and result > 0 hold?

   return result
   ```
3. At each step, verify partial code satisfies constraints
4. If SMT solver finds counterexample, regenerate that step

**Benefits for lift-sys**:
- **Formal correctness**: Generated code provably satisfies IR assertions
- **Early error detection**: Catch logical errors during generation, not at runtime
- **Reduced test burden**: Formal verification supplements testing
- **Confidence scores**: SMT solver confidence can update IR provenance

### 3.2 Dependent Clause Handling

IR often contains multiple dependent assertions:

```python
assertions=[
    AssertClause(predicate="len(items) > 0", rationale="Non-empty list"),
    AssertClause(predicate="all(x > 0 for x in items)", rationale="All positive"),
    AssertClause(predicate="result == sum(items) / len(items)", rationale="Average formula"),
    AssertClause(predicate="min(items) <= result <= max(items)", rationale="Result in range"),
]
```

These constraints are **dependent**:
- `min(items) <= result` depends on `result == sum(items) / len(items)`
- `len(items) > 0` is a precondition for `sum(items) / len(items)`

**SMT Approach**:
1. Build constraint graph showing dependencies
2. Order generation to satisfy preconditions first
3. Generate code incrementally, verifying at each step
4. Use SMT solver to find valid execution paths

**Example Generation Order**:
```python
# Step 1: Check precondition
if len(items) == 0:
    raise ValueError("List cannot be empty")
# SMT verifies: len(items) > 0 in all branches

# Step 2: Compute average
total = sum(items)
result = total / len(items)
# SMT verifies: result == sum(items) / len(items)

# Step 3: Validate result in range
assert min(items) <= result <= max(items), "Average out of range"
# SMT verifies: This assertion always holds given previous constraints
```

---

## Part 4: Parallel Speculative Decoding with Constraints

### 4.1 Recent Research: SpecExec and Tree-Based Search

**Papers**:
- "SpecExec: Massively Parallel Speculative Decoding" (2024)
- "Group Tree Optimization for Speculative Decoding" (2024)
- "Tree-Search-Based Reasoning with Speculative Execution" (2024)

**Core Idea**: Generate multiple candidate continuations in parallel, verify them against constraints, and select the best valid path.

**Traditional Speculative Decoding**:
1. Draft model generates K tokens speculatively
2. Target model verifies in parallel
3. Accept longest matching prefix

**Constraint-Aware Speculative Decoding**:
1. Draft model generates K candidate paths
2. For each path, check constraint satisfaction (type + SMT)
3. Target model evaluates only constraint-satisfying paths
4. Accept best valid path (highest likelihood + constraint satisfaction)

**SpecExec Key Innovation**: Cache tree of verified paths
- Reuse verified subtrees across generation steps
- Amortize constraint checking cost
- Achieve 2-3x speedup with constraints

### 4.2 Application to lift-sys: Multi-Clause Generation

Given IR with multiple ways to satisfy constraints:

```python
IntentClause(description="Sort a list of numbers efficiently"),
AssertClause(predicate="is_sorted(result)", rationale="Output must be sorted"),
AssertClause(predicate="set(result) == set(items)", rationale="No elements lost"),
AssertClause(predicate="time_complexity <= O(n log n)", rationale="Efficient algorithm"),
```

**Parallel Speculative Approach**:

1. **Draft model generates multiple candidate algorithms**:
   - Path A: QuickSort implementation
   - Path B: MergeSort implementation
   - Path C: Python's built-in `sorted()`
   - Path D: Heap-based sort

2. **Verify each path against constraints in parallel**:
   - Path A: ✅ Satisfies all constraints (QuickSort is O(n log n) average)
   - Path B: ✅ Satisfies all constraints (MergeSort is O(n log n) worst-case)
   - Path C: ✅ Satisfies all constraints (Timsort is O(n log n) worst-case)
   - Path D: ✅ Satisfies all constraints (Heapsort is O(n log n) worst-case)

3. **Target model ranks valid paths**:
   - Path C (built-in sorted): Highest simplicity score
   - Path B (MergeSort): Highest pedagogical value
   - Path A (QuickSort): Highest performance on random data

4. **Select based on context** (e.g., user preference, IR metadata):
   - If IR has `metadata.preference = "production"` → Path C (built-in)
   - If IR has `metadata.preference = "educational"` → Path B (MergeSort)

**Benefits**:
- **Explore design space**: Generate multiple valid implementations
- **User choice**: Present alternatives, let user pick
- **Confidence**: Higher confidence when multiple paths satisfy constraints
- **Speed**: Parallel verification faster than sequential generate-verify

### 4.3 Tree Search with Typed Holes

Typed holes in IR represent **ambiguities** that need resolution. Parallel speculative decoding can explore resolution space:

**Example IR with Typed Holes**:
```python
IntentClause(description="Process user data"),
SigClause(
    name="process_data",
    parameters=[
        Parameter(name="data", type_hint="???", description="User input data"),
    ],
    returns="???",
),
TypedHole(
    identifier="data_type",
    type_hint="str | dict | list",
    description="Unclear what format data comes in",
    constraints={"format": "JSON-serializable"},
),
TypedHole(
    identifier="return_type",
    type_hint="bool | dict | None",
    description="Unclear what processing returns",
),
```

**Parallel Speculative Resolution**:

1. **Generate candidate resolutions** (tree branches):
   - Branch A: `data: str` (JSON string), `returns: dict` (parsed data)
   - Branch B: `data: dict` (already parsed), `returns: bool` (validation result)
   - Branch C: `data: list[dict]` (multiple items), `returns: list[dict]` (processed items)

2. **Generate code for each branch in parallel**:
   - Branch A:
     ```python
     def process_data(data: str) -> dict:
         return json.loads(data)
     ```
   - Branch B:
     ```python
     def process_data(data: dict) -> bool:
         return validate_schema(data)
     ```
   - Branch C:
     ```python
     def process_data(data: list[dict]) -> list[dict]:
         return [sanitize(item) for item in data]
     ```

3. **User reviews alternatives**:
   - See all three interpretations
   - Pick the one that matches intent
   - System updates IR with chosen resolution

4. **Cache verified branches**:
   - Future refinements can reuse verified implementations
   - If user changes mind, switch to different cached branch

**Benefits**:
- **Disambiguation**: Explicitly explore ambiguity space
- **User clarity**: Show concrete examples of each interpretation
- **Efficiency**: Generate all options in one parallel pass
- **Provenance**: Track which branch was chosen and why

---

## Part 5: Synthesis - Complete Workflow

### 5.1 Forward Mode: Prompt → IR → Code (Constraint-Driven)

**Step 1: Prompt → IR (Type-Constrained)**
```
User prompt: "Function that calculates average of positive numbers"
         ↓
[Type-constrained JSON generation with IR schema]
         ↓
IR with explicit types and constraints:
  IntentClause("Calculate average of positive numbers")
  SigClause(name="average_positive", params=[("numbers", "list[int]")], returns="float")
  AssertClause("all(x > 0 for x in numbers)")
  AssertClause("result == sum(numbers) / len(numbers)")
```

**Constraints enforced during generation**:
- IR JSON schema compliance (100% valid JSON)
- Type hints are valid Python types
- Assertions are valid Python predicates
- Required IR fields present

**Step 2: IR → Code (Type + SMT + ChatLSP Constrained)**
```
IR with types and assertions
         ↓
[Type-constrained code generation]
  - Enforce "list[int]" for parameter
  - Enforce "float" for return type
  - Generate function signature
         ↓
[ChatLSP semantic context]
  - Query language server for relevant type definitions
  - Retrieve function headers (e.g., sum, len, type guards)
  - Get expected return type context
         ↓
[SMT-constrained body generation with context]
  - Check: Does precondition check satisfy "all(x > 0)"?
  - Check: Does computation satisfy "result == sum / len"?
  - Generate with verification checkpoints + semantic context
         ↓
[ChatLSP error correction]
  - Check generated code for static type errors
  - If errors: Send to LLM for correction (up to 2 iterations)
         ↓
[Parallel speculative decoding]
  - Generate multiple implementations in parallel
  - Verify each against type + SMT constraints
  - Check each for semantic correctness via ChatLSP
  - Select best valid implementation
         ↓
Verified, runnable, semantically correct code
```

**Result**: Code that is:
- **Syntactically valid** (type-constrained generation guarantees this)
- **Logically correct** (SMT verification guarantees this)
- **Semantically appropriate** (ChatLSP ensures type correctness and contextual fit)
- **Optimized** (parallel decoding explores design space)
- **Traceable** (provenance tracks generation decisions)

### 5.2 Reverse Mode: Code → IR (Constraint Extraction)

**Current Challenge**: Extract IR from existing code without explicit types/assertions.

**Constraint-Driven Approach**:

**Step 1: Static Analysis → Type Constraints**
```python
# Input code (untyped)
def average_positive(numbers):
    return sum(numbers) / len(numbers)

# Type inference (nuanced-py / stack-graphs)
# Infer: numbers: list[int | float]
# Infer: returns: float

# Generate IR SigClause
SigClause(
    name="average_positive",
    parameters=[Parameter("numbers", "list[int | float]", "Numbers to average")],
    returns="float",
)
```

**Step 2: Dynamic Analysis → Assertion Constraints**
```python
# Input: Test traces from Daikon
# Trace 1: numbers=[1, 2, 3] → result=2.0
# Trace 2: numbers=[5, 10, 15] → result=10.0
# Trace 3: numbers=[100] → result=100.0

# Inferred invariants:
# - len(numbers) > 0 (no empty lists in traces)
# - all(x > 0 for x in numbers) (all positive in traces)
# - result == sum(numbers) / len(numbers) (verified across traces)

# Generate IR AssertClauses
AssertClause(predicate="len(numbers) > 0", rationale="Empty list would cause division by zero"),
AssertClause(predicate="all(x > 0 for x in numbers)", rationale="Observed in all test cases"),
AssertClause(predicate="result == sum(numbers) / len(numbers)", rationale="Mathematical definition"),
```

**Step 3: Typed Hole Insertion for Ambiguities**
```python
# Ambiguous: Should negative numbers be rejected or filtered?
TypedHole(
    identifier="negative_handling",
    type_hint="reject | filter | allow",
    description="How should negative numbers be handled?",
    constraints={
        "reject": "Raise ValueError if any negative",
        "filter": "Remove negatives before averaging",
        "allow": "Include negatives in calculation",
    },
    kind=HoleKind.INTENT,
)
```

**Result**: Extracted IR with:
- **Type constraints** from static analysis
- **Logical constraints** from dynamic analysis
- **Ambiguities** marked explicitly as typed holes

### 5.3 Core Loop: Extract → Refine → Regenerate

**Complete Workflow**:

```
Legacy Code (untyped, untested)
         ↓
[Reverse Mode: Code → IR]
  - Static analysis → types
  - Dynamic analysis → assertions
  - Insert typed holes for ambiguities
         ↓
IR v1 (extracted, with holes and constraints)
         ↓
[User + Agent Refinement]
  - Resolve typed holes (parallel speculative suggestions)
  - Add missing assertions
  - Clarify intent
         ↓
IR v2 (complete, verified)
         ↓
[Forward Mode: IR → Code]
  - Type-constrained generation
  - SMT-verified generation
  - Parallel speculative optimization
         ↓
Regenerated Code (typed, tested, verified)
         ↓
[Round-Trip Validation]
  - Extract IR from regenerated code
  - Compare to IR v2
  - Verify equivalence
         ↓
✅ Code matches intent, or ❌ Loop again
```

**Key Insight**: Constraints flow bidirectionally:
- **Forward**: IR constraints guide code generation
- **Reverse**: Code behavior infers IR constraints
- **Refinement**: User resolves constraint conflicts

---

## Part 6: Actionable Recommendations

### 6.1 Short-Term: Proof-of-Concept (2-3 weeks)

**Goal**: Validate that IR-driven constrained generation works.

**Experiment 1: Type-Constrained IR Generation**
- **Task**: Generate valid IR JSON from 20 test prompts
- **Approach**: Use llguidance with IR JSON schema
- **Success Metric**: 100% valid JSON, no parsing errors
- **Estimated Effort**: 3-4 days

**Experiment 2: SMT-Verified Code Generation**
- **Task**: Generate code for 10 IR specs with assertions
- **Approach**: Generate code, verify with Z3 at each step
- **Success Metric**: 90%+ assertions satisfied without retries
- **Estimated Effort**: 4-5 days

**Experiment 3: Parallel Speculative Disambiguation**
- **Task**: Generate 3 alternatives for 5 IRs with typed holes
- **Approach**: Parallel speculative decoding, verify all branches
- **Success Metric**: All branches satisfy constraints, user can pick
- **Estimated Effort**: 5-6 days

**Experiment 4: ChatLSP Semantic Correction**
- **Task**: Generate code for 10 IR specs, use language server for error correction
- **Approach**: Generate code, query Pyright for errors, refine (up to 2 iterations)
- **Success Metric**: Measure improvement in type correctness after error correction
- **Baseline**: No error correction vs. 1 iteration vs. 2 iterations
- **Expected**: ~3x improvement with context, ~1.5x with error correction
- **Estimated Effort**: 3-4 days

**Deliverable**: POC report with benchmarks, examples, recommendation

### 6.2 Medium-Term: Integration (4-6 weeks)

**Phase 1: Type-Constrained Generation**
- Replace regex-based prompt→IR with llguidance + IR schema
- Integrate with `lift_sys/spec_sessions/translator.py`
- Add IR validation checkpoint after generation

**Phase 2: SMT-Verified Code Generation**
- Extend `lift_sys/codegen/generator.py` with Z3 checkpoints
- Verify assertions during generation, not just at runtime
- Add constraint satisfaction confidence to IR provenance

**Phase 3: ChatLSP Integration**
- Integrate Pyright as language server for Python code generation
- Query for type errors after generation, refine iteratively
- Retrieve relevant type definitions and function headers for context
- Add error correction loop (up to 2 iterations)
- Integrate with `lift_sys/codegen/generator.py`

**Phase 4: Parallel Speculative Decoding**
- Integrate speculative decoding for typed hole resolution
- Generate multiple alternatives in `lift_sys/forward_mode/controller_runtime.py`
- Verify each alternative with ChatLSP for semantic correctness
- Add UI for user to review and select alternatives

**Success Metrics**:
- IR generation: 100% valid JSON, 95%+ captures intent
- Code generation: 100% compiles, 90%+ passes tests, 80%+ satisfies assertions, 95%+ passes type checks
- Typed hole resolution: 3+ alternatives generated, 70%+ user acceptance
- Error correction: 3x improvement in type correctness with context, 1.5x with error correction

### 6.3 Long-Term: Optimization (3-6 months)

**Performance Optimization**:
- Cache type automata for common IR patterns
- Cache SMT solver proofs for reusable constraints
- Cache verified speculative decoding trees
- Target: <2s for IR generation, <5s for code generation

**Quality Optimization**:
- Train draft model on lift-sys IR corpus
- Fine-tune on verified code-IR pairs
- Improve assertion inference from test traces
- Build custom ChatLSP extensions for better context retrieval
- Target: 95%+ assertion satisfaction without retries, 98%+ type correctness

**Multi-Language Support**:
- Extend type constraints to TypeScript, Rust, Go
- Integrate language servers for each target language (tsserver, rust-analyzer, gopls)
- Build language-specific assertion languages
- Cross-language code generation (Python IR → Rust code)
- Target: 3+ languages supported with ChatLSP integration

**Custom IR-Aware Language Server**:
- Build language server that understands lift-sys IR directly
- Provide IR-aware type inference and error checking
- Enable bidirectional feedback: language server ↔ IR ↔ code
- Query IR constraints during code completion
- Suggest refinements to IR based on code patterns
- Target: Seamless integration between IR and code generation

---

## Part 7: Research Questions for Phase 2

Now that we understand IR-driven constrained generation, Phase 2 (Constrained Generation Technologies) should answer:

### For llguidance:
1. Can it enforce lift-sys's IR JSON schema with 100% reliability?
2. Can it enforce Python type grammar for generated code?
3. What's the latency overhead for typical IR generation (50-200 tokens)?
4. Does it support streaming generation with constraints?
5. Can we use it with Anthropic/OpenAI APIs or only self-hosted vLLM?
6. How does it handle deeply nested IR structures (e.g., 10+ AssertClauses)?
7. Can we integrate with Z3 for SMT verification during generation?

### For AICI:
1. Can AICI controllers enforce complex IR constraints (types + assertions)?
2. How does AICI's backtracking compare to llguidance's token masking?
3. Can we write AICI controllers that call Z3 mid-generation?
4. What's the performance profile for IR generation vs. llguidance?
5. Does AICI support parallel speculative decoding?
6. Can we use AICI with cached constraint trees?

### For xgrammar:
1. Can xgrammar's adaptive grammar handle Python type system?
2. What's the speedup from caching repeated IR patterns?
3. Does it integrate with SMT solvers?
4. Can we define grammars for multiple target languages (Python, TypeScript, Rust)?
5. How does xgrammar compare to llguidance in terms of expressiveness?

### For ChatLSP / Language Server Integration:
1. Can we integrate Pyright as a language server for Python code generation?
2. How do we implement the ChatLSP protocol extensions (expectedType, retrieveRelevantTypes, etc.)?
3. What's the latency overhead for querying language server during generation?
4. Can we combine ChatLSP with constrained generation (e.g., llguidance + Pyright)?
5. How effective is iterative error correction (1 vs. 2 iterations)?
6. Can language server queries be cached for repeated IR patterns?
7. Does ChatLSP work with TypedHole resolution (query expected type at hole)?
8. Can we extend to other languages (TypeScript, Rust) with their language servers?

### Cross-Cutting Questions:
1. Which approach has the lowest latency for interactive IR refinement?
2. Which approach best supports SMT integration?
3. Which approach works best for parallel speculative decoding?
4. Which approach has the best developer experience for defining constraints?
5. Which approach is most production-ready?
6. How do constrained generation and ChatLSP complement each other?
7. What's the optimal pipeline: Constrained → ChatLSP or ChatLSP → Constrained?
8. Can we combine all three: Type constraints + SMT + ChatLSP + Parallel decoding?

---

## Part 8: Updated Research Plan Structure

The research plan should be reorganized to reflect IR-driven generation as the foundation:

**Phase 1: Foundation** (COMPLETE)
- ✅ Understand lift-sys goals and architecture
- ✅ Map current implementation gaps
- ✅ Research IR-driven constrained generation (this document)

**Phase 1.5: IR-Driven Generation Research** (COMPLETE - this document)
- ✅ Understand how IR structure maps to constraints
- ✅ Research type-constrained generation
- ✅ Research SMT-constrained generation
- ✅ Research parallel speculative decoding with constraints
- ✅ Synthesize actionable recommendations

**Phase 2: Constrained Generation Technologies** (UPDATED)
- Now focuses on: Which technology best implements IR-driven generation?
- Evaluate llguidance, AICI, xgrammar through IR lens
- Run experiments with IR JSON schema enforcement
- Test SMT integration capabilities
- Benchmark latency and quality

**Phase 3: Program Synthesis** (UPDATED)
- Loom: Can it leverage IR constraints for synthesis?
- Calligrapher: How does its IR compare? Can we merge approaches?
- Focus: Reusable techniques for IR-to-code synthesis

**Phase 4: Static Analysis** (UPDATED)
- stack-graphs, nuanced-py: How accurately can they extract IR constraints?
- Focus: Code → IR constraint extraction quality

**Phase 5: Inference Optimization** (UPDATED)
- ATLAS, parallel decoding: Can they handle constraint-aware generation?
- Focus: Speed up constrained generation without quality loss

**Phase 6: Synthesis** (UPDATED)
- Integration roadmap informed by IR-driven generation
- Concrete implementation plan with constraint-driven architecture
- Updated success metrics for constrained generation

---

## Conclusion

lift-sys's IR is uniquely positioned to drive high-quality constrained code generation. The structured format—with explicit types, typed holes, assertions, and provenance—provides exactly the information needed to:

1. **Enforce correctness** through type-constrained and SMT-verified generation
2. **Explore alternatives** through parallel speculative decoding
3. **Trace decisions** through provenance and constraint satisfaction records
4. **Optimize performance** through caching of verified constraint paths

The next phase of research should focus on finding the best technology to implement IR-driven constrained generation, with the understanding that the IR itself is the key enabler of quality, performance, and adherence to intent.

**Key Takeaway**: Don't just evaluate technologies in isolation—evaluate them through the lens of how well they can leverage lift-sys's structured IR to drive generation.
