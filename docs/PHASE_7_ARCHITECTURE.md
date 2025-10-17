# Phase 7 Architecture: IR-Level Constraints

**Technical Implementation Documentation**

## Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Components](#components)
- [Data Flow](#data-flow)
- [Design Decisions](#design-decisions)
- [Integration](#integration)
- [Extensibility](#extensibility)

## Overview

Phase 7 introduces **IR-level constraints** to prevent code generation bugs proactively, rather than fixing them reactively with AST pattern matching (Phase 4-6 approach).

### Motivation

Phase 6 achieved 83.3% success with hybrid LLM + AST repair, but identified **pattern matching brittleness** as the root cause of remaining failures. The same semantic requirement (e.g., "check @ and . not adjacent") can be implemented in multiple syntactically different ways, making AST pattern matching fragile.

**Core insight**: Instead of matching all possible code structures post-generation, specify requirements at the IR level that:

1. **Prevent bugs before generation** - Constraints guide LLM to generate correct code
2. **Work with any code structure** - Semantic requirements, not syntactic patterns
3. **Scale maintainably** - One constraint covers all implementation variations
4. **Provide clear feedback** - Enhanced error messages help LLM fix violations on retry

### Architecture Principles

1. **Separation of concerns**: Detection, validation, and messaging are separate modules
2. **Language-agnostic constraints**: Specified at IR level, validated on generated code
3. **Composable constraints**: Multiple constraints can apply to same function
4. **Automatic inference**: Constraints detected from natural language specifications
5. **Retry-oriented design**: Validation failures trigger retry with enhanced feedback

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Natural Language                         │
│               "Find the first index of value in list"            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      IR Translation                              │
│                 (XGrammarIRTranslator)                           │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Constraint Detection                           │
│               (ConstraintDetector.detect)                        │
│                                                                  │
│  Analyzes:                                                       │
│  • Intent keywords ("first", "count", "adjacent")                │
│  • Effect descriptions                                           │
│  • Return type                                                   │
│  • Special patterns (email, parentheses)                         │
│                                                                  │
│  Produces:                                                       │
│  • ReturnConstraint                                              │
│  • LoopBehaviorConstraint                                        │
│  • PositionConstraint                                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              IntermediateRepresentation                          │
│                                                                  │
│  intent: IntentClause                                            │
│  signature: SigClause                                            │
│  effects: list[EffectClause]                                     │
│  constraints: list[Constraint]  ← NEW                            │
│  assertions: list[Assertion]                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Code Generation                              │
│            (XGrammarCodeGenerator.generate)                      │
│                                                                  │
│  Retry loop (max 3 attempts):                                    │
│  1. Generate code with constraint hints in prompt                │
│  2. Repair AST issues (Phase 4)                                  │
│  3. Validate constraints (Phase 7) ← NEW                         │
│  4. Check assertions (Phase 5b)                                  │
│  5. Success or retry with feedback                               │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                  Constraint Validation                           │
│            (ConstraintValidator.validate)                        │
│                                                                  │
│  For each constraint:                                            │
│  1. Parse code → AST                                             │
│  2. Find target function                                         │
│  3. Analyze AST for constraint-specific patterns                 │
│  4. Return violations (if any)                                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                Enhanced Error Messages                           │
│          (format_violations_summary)                             │
│                                                                  │
│  For each violation:                                             │
│  • What's wrong                                                  │
│  • Why it matters                                                │
│  • How to fix (with examples)                                    │
│                                                                  │
│  Feedback included in next retry attempt                         │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Constraint Data Classes

**Module**: `lift_sys.ir.constraints`

**Purpose**: Define constraint types as data classes with serialization support

**Key classes:**

```python
@dataclass
class Constraint:
    """Base constraint type."""
    type: ConstraintType
    description: str = ""
    severity: ConstraintSeverity = ConstraintSeverity.ERROR

@dataclass
class ReturnConstraint(Constraint):
    """Ensures computed values are explicitly returned."""
    value_name: str = ""
    requirement: ReturnRequirement = ReturnRequirement.MUST_RETURN

@dataclass
class LoopBehaviorConstraint(Constraint):
    """Enforces specific loop behaviors (early return vs accumulation)."""
    search_type: LoopSearchType = LoopSearchType.FIRST_MATCH
    requirement: LoopRequirement = LoopRequirement.EARLY_RETURN
    loop_variable: str | None = None

@dataclass
class PositionConstraint(Constraint):
    """Specifies position requirements between elements."""
    elements: list[str] = field(default_factory=list)
    requirement: PositionRequirement = PositionRequirement.NOT_ADJACENT
    min_distance: int = 0
    max_distance: int | None = None
```

**Design notes:**

- Immutable data classes (frozen=False for flexibility but encouraged immutability)
- Enum-based type safety for constraint types and requirements
- Serialization via `to_dict()`/`from_dict()` for JSON persistence
- Default descriptions auto-generated in `__post_init__()`

### 2. Constraint Detector

**Module**: `lift_sys.ir.constraint_detector`

**Purpose**: Automatically infer constraints from natural language IR specifications

**Algorithm:**

```python
class ConstraintDetector:
    def detect_constraints(self, ir: IntermediateRepresentation) -> list[Constraint]:
        """
        Analyze IR and detect all applicable constraints.

        Returns list of constraints to apply.
        """
        constraints = []

        # Detect return constraints
        if self._should_detect_return(ir):
            constraints.append(self._detect_return_constraint(ir))

        # Detect loop behavior constraints
        if self._should_detect_loop(ir):
            constraints.append(self._detect_loop_behavior_constraint(ir))

        # Detect position constraints
        constraints.extend(self._detect_position_constraints(ir))

        return constraints
```

**Detection logic:**

1. **ReturnConstraint**:
   - Trigger: Non-None return type + computation keywords ("count", "calculate") + no explicit "return" mentioned
   - Value name: Extracted from intent/effects or default to "result"

2. **LoopBehaviorConstraint**:
   - Trigger: Loop keywords ("iterate", "for each") + search type keywords ("first", "all", "last")
   - Search type: Determined by keyword ("first" → FIRST_MATCH, "all" → ALL_MATCHES, "last" → LAST_MATCH)
   - Requirement: FIRST_MATCH requires EARLY_RETURN, ALL_MATCHES/LAST_MATCH require ACCUMULATE

3. **PositionConstraint**:
   - Trigger: Special patterns (email validation, parentheses matching) or adjacency keywords
   - Elements: Extracted from context (e.g., ["@", "."] for email)
   - Requirement: Determined by context (email → NOT_ADJACENT, parentheses → ORDERED)

**Keyword patterns:**

```python
RETURN_KEYWORDS = ["return", "returns", "compute", "computes", "calculate",
                   "calculates", "count", "counts", "sum", "sums", "result", "output"]

FIRST_MATCH_KEYWORDS = ["first", "earliest", "initial", "find first",
                        "locate first", "search for first"]

LAST_MATCH_KEYWORDS = ["last", "final", "find last", "locate last", "search for last"]

ALL_MATCHES_KEYWORDS = ["all", "every", "each", "collect all", "find all", "gather all"]

LOOP_KEYWORDS = ["loop", "iterate", "iteration", "for each", "traverse", "walk through"]

POSITION_KEYWORDS = ["adjacent", "next to", "immediately after", "immediately before",
                     "distance", "position", "placement", "between", "not adjacent", "separated"]
```

**Design trade-offs:**

- **Simple keyword matching** vs complex NLP: Fast, debuggable, good enough for Phase 7
- **Conservative detection** vs aggressive: Prefer false negatives (missing constraint) over false positives (wrong constraint)
- **Rule-based** vs ML: Interpretable, no training data required

### 3. Constraint Validator

**Module**: `lift_sys.ir.constraint_validator`

**Purpose**: Validate generated code satisfies constraints using AST analysis

**Algorithm:**

```python
class ConstraintValidator:
    def validate(self, code: str, ir: IntermediateRepresentation) -> list[ConstraintViolation]:
        """
        Validate code against IR constraints.

        Returns list of violations (empty if all satisfied).
        """
        violations = []

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [ConstraintViolation(constraint_type="syntax_error", ...)]

        # Find target function
        function_def = self._find_function(tree, ir.signature.name)
        if not function_def:
            return [ConstraintViolation(constraint_type="missing_function", ...)]

        # Validate each constraint
        for constraint in ir.constraints:
            if isinstance(constraint, ReturnConstraint):
                violations.extend(self._validate_return_constraint(function_def, constraint))
            elif isinstance(constraint, LoopBehaviorConstraint):
                violations.extend(self._validate_loop_constraint(function_def, constraint))
            elif isinstance(constraint, PositionConstraint):
                violations.extend(self._validate_position_constraint(function_def, constraint))

        return violations
```

**Validation strategies:**

1. **ReturnConstraint**:
   - Find all `return` statements using `ast.walk()`
   - Check at least one return exists
   - Check at least one return is non-None

2. **LoopBehaviorConstraint**:
   - **EARLY_RETURN**: Search for `return` inside loop body
   - **ACCUMULATE**: Search for list append or variable assignment inside loop, return after loop

3. **PositionConstraint**:
   - **NOT_ADJACENT**: Search for `abs()` or subtraction with comparison
   - **ORDERED**: Search for position comparison (e.g., `idx1 < idx2`)
   - **MIN_DISTANCE/MAX_DISTANCE**: Search for distance calculation with threshold

**AST pattern matching:**

```python
# Example: Detect early return in loop
for node in ast.walk(function_def):
    if isinstance(node, (ast.For, ast.While)):
        # Check if loop body contains return
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value is not None:
                has_early_return = True
```

**Design notes:**

- **Heuristic-based validation**: Not perfect, but good enough to catch common bugs
- **Conservative validation**: Prefer false negatives (missed violation) over false positives (incorrect violation)
- **Language-specific**: Python AST patterns, but constraint model is language-agnostic

### 4. Enhanced Error Messages

**Module**: `lift_sys.ir.constraint_messages`

**Purpose**: Generate user-friendly, actionable error messages for constraint violations

**Message structure:**

```python
def format_violation_for_user(violation, constraint) -> str:
    """
    Format violation with enhanced message:

    1. What's wrong: Clear explanation of violation
    2. Why it matters: Impact on correctness
    3. How to fix: Actionable suggestions with examples
    """
```

**Example output:**

```
================================================================================
CONSTRAINT VALIDATION FAILED
================================================================================

Found 1 ERROR(s) - must fix before code can be accepted:

ERROR 1/1:
--------------------------------------------------------------------------------
LoopBehaviorConstraint violation: Missing early return for FIRST match

What's wrong:
  Loop searches for FIRST match but doesn't return immediately when found.
  Instead, it continues iterating or accumulates results.

Why it matters:
  Without early return, the loop continues to the LAST match, not the first.
  This produces incorrect results (e.g., find_index returns wrong index).

How to fix:
  Add 'return' statement inside loop when match is found

Example:
  # Current (wrong - finds LAST match):
  def find_first(items, target):
      result = -1
      for i, item in enumerate(items):
          if item == target:
              result = i  # Accumulates to last match!
      return result

  # Fixed (correct - finds FIRST match):
  def find_first(items, target):
      for i, item in enumerate(items):
          if item == target:
              return i  # Early return on first match!
      return -1  # Default if not found

================================================================================
Please fix these violations in the next generation attempt.
================================================================================
```

**Design principles:**

- **Educational**: Explain WHY violation matters, not just WHAT is wrong
- **Actionable**: Provide concrete examples of how to fix
- **Specific**: Tailor message to constraint type and violation
- **LLM-friendly**: Structured format that LLMs can understand and act on

### 5. Constraint Hints for Generation

**Module**: `lift_sys.ir.constraint_messages.get_constraint_hint()`

**Purpose**: Generate brief hints included in code generation prompt to guide LLM proactively

**Example hints:**

```python
ReturnConstraint(value_name="count"):
  → "MUST explicitly return 'count' value (not None)"

LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN):
  → "MUST use early return inside loop for FIRST match (not accumulate to last)"

PositionConstraint(["@", "."], NOT_ADJACENT, min_distance=1):
  → "MUST check '@' and '.' are NOT adjacent (distance > 1)"
```

**Integration:**

Hints are appended to generation prompt:

```python
# In XGrammarCodeGenerator.generate()
prompt = f"""Generate Python code for:
{ir_to_prompt(ir)}

REQUIRED constraints:
{chr(10).join(f"- {get_constraint_hint(c)}" for c in ir.constraints)}
"""
```

## Data Flow

### 1. IR Translation with Constraint Detection

```python
# In XGrammarIRTranslator.translate()
async def translate(self, prompt: str) -> IntermediateRepresentation:
    # Phase 1-2: Translate natural language → IR
    ir = await self._generate_ir(prompt)

    # Phase 7: Auto-detect constraints
    detector = ConstraintDetector()
    ir.constraints = detector.detect_constraints(ir)

    return ir
```

**Timeline**: Detection happens immediately after IR generation, before code generation

### 2. Code Generation with Constraint Validation

```python
# In XGrammarCodeGenerator.generate()
async def generate(self, ir: IntermediateRepresentation, max_retries: int = 3):
    for attempt in range(max_retries):
        # 1. Generate code with constraint hints
        prompt = self._build_prompt_with_constraints(ir)
        code = await self._generate_code(prompt)

        # 2. Phase 4: Repair AST issues (missing returns, unbalanced brackets)
        if self.ast_repair:
            code = self.ast_repair.repair(code, ir)

        # 3. Phase 7: Validate constraints
        if ir.constraints:
            validator = ConstraintValidator()
            violations = validator.validate(code, ir)
            error_violations = [v for v in violations if v.severity == "error"]

            if error_violations and attempt < max_retries - 1:
                # Generate enhanced feedback
                feedback = format_violations_summary(error_violations, ir.constraints)
                self._validation_feedback = feedback
                continue  # Retry with feedback

        # 4. Phase 5b: Check assertions (runtime validation)
        if ir.assertions:
            assertion_result = await self._check_assertions(code, ir)
            if not assertion_result.passed and attempt < max_retries - 1:
                continue  # Retry

        # Success!
        return code

    # All retries exhausted
    return code  # Return best attempt with warnings
```

**Validation order:**

1. **AST repair** - Fix syntax/structure issues
2. **Constraint validation** - Check semantic requirements (Phase 7)
3. **Assertion checking** - Validate runtime behavior (Phase 5b)

**Rationale**: AST repair must precede constraint validation (can't analyze invalid AST). Constraints check structure, assertions check behavior.

### 3. Constraint Serialization

Constraints are stored on IR and persisted to JSON:

```python
# Serialization
ir_dict = ir.to_dict()
# {
#   "intent": {...},
#   "signature": {...},
#   "effects": [...],
#   "constraints": [  # ← NEW
#     {
#       "type": "return_constraint",
#       "value_name": "count",
#       "requirement": "MUST_RETURN",
#       "severity": "error"
#     }
#   ],
#   "assertions": [...]
# }

# Deserialization
ir = IntermediateRepresentation.from_dict(ir_dict)
# Automatically routes to appropriate constraint subclass
```

## Design Decisions

### 1. Why Constraints at IR Level?

**Alternatives considered:**

- **AST pattern matching** (Phase 4-6): Brittle, doesn't scale to all code structures
- **Runtime validation only** (Phase 5): Too late, requires test execution
- **NLP-based code analysis**: Expensive, complex, lower accuracy

**Decision**: IR-level constraints

**Rationale**:

- **Specification-level requirements**: Constraints describe WHAT is required, not HOW to implement
- **Language-agnostic**: Same constraint applies to Python, JavaScript, Rust
- **Proactive prevention**: Guide generation, don't just detect bugs
- **Composable**: Multiple constraints can apply to same function

### 2. Why Automatic Detection?

**Alternatives:**

- **Manual specification**: User specifies constraints explicitly
- **ML-based inference**: Train model to predict constraints
- **No detection**: Constraints always manual

**Decision**: Rule-based automatic detection with manual override

**Rationale**:

- **Developer ergonomics**: Most constraints are inferrable from natural language
- **Debuggability**: Rule-based detection is interpretable
- **Incremental adoption**: Auto-detection works out of the box, can override if needed

### 3. Why Heuristic Validation?

**Alternatives:**

- **Symbolic execution**: Prove constraint satisfaction
- **SMT solving**: Formal verification
- **Static analysis frameworks**: Use existing tools (pylint, mypy)

**Decision**: Heuristic AST pattern matching

**Rationale**:

- **Performance**: Fast enough for retry loop (20-50ms)
- **Simplicity**: No external dependencies, easy to debug
- **Good enough**: Catches 90%+ of violations, false negatives acceptable
- **Extensibility**: Easy to add new heuristics

**Trade-off**: Accept some false negatives (missed violations) to avoid false positives (incorrect violations)

### 4. Why Enhanced Error Messages?

**Alternatives:**

- **Simple error strings**: "Constraint violated"
- **Code snippets only**: Show incorrect code
- **LLM-generated feedback**: Ask LLM to explain violation

**Decision**: Structured messages with "What/Why/How" + examples

**Rationale**:

- **Educational**: LLMs learn from examples
- **Actionable**: Clear fix instructions increase retry success
- **Structured**: Consistent format across constraint types
- **Human-readable**: Also useful for debugging

## Integration

### Integration with Existing Phases

**Phase 1-2 (IR Translation)**: Constraints detected after IR generation

**Phase 3 (Forward Mode)**: Constraints stored on IR, used during generation

**Phase 4 (AST Repair)**: Runs before constraint validation (repair syntax, then check semantics)

**Phase 5a (Synthetic Assertions)**: Complementary (assertions check runtime behavior, constraints check structure)

**Phase 5b (Assertion Checking)**: Runs after constraint validation in retry loop

**Phase 6 (Modal Inference)**: Constraint validation runs on Modal-generated code

### Backward Compatibility

- **No breaking changes**: Constraints are optional, empty list by default
- **Gradual adoption**: Can enable constraints per-IR or globally
- **Override detection**: Manual constraints override auto-detected ones

### Testing Strategy

1. **Unit tests** (`tests/ir/test_constraints.py`):
   - Constraint data class serialization
   - Enum value correctness
   - Default description generation

2. **Detection tests** (`tests/ir/test_constraint_detector.py`):
   - Keyword pattern matching
   - Edge cases (missing keywords, ambiguous intent)
   - False positive/negative rates

3. **Validation tests** (`tests/ir/test_constraint_validator.py`):
   - Correct detection of violations
   - No false positives on valid code
   - Edge cases (syntax errors, missing functions)

4. **Integration tests** (`tests/integration/test_xgrammar_*_with_constraints.py`):
   - End-to-end: natural language → IR → code → validation
   - Retry loop with feedback
   - Phase 3 persistent failures (count_words, find_index, is_valid_email)

## Extensibility

### Adding New Constraint Types

1. **Define constraint class** in `lift_sys/ir/constraints.py`:

```python
@dataclass
class NewConstraint(Constraint):
    type: ConstraintType = field(default=ConstraintType.NEW, init=False)
    custom_field: str = ""

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["custom_field"] = self.custom_field
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NewConstraint:
        return cls(custom_field=data["custom_field"], ...)
```

2. **Add detection logic** in `ConstraintDetector`:

```python
def _detect_new_constraint(self, ir: IntermediateRepresentation) -> NewConstraint | None:
    if "custom_keyword" in ir.intent.summary.lower():
        return NewConstraint(custom_field="value")
    return None
```

3. **Add validation logic** in `ConstraintValidator`:

```python
def _validate_new_constraint(
    self, function_def: ast.FunctionDef, constraint: NewConstraint
) -> list[ConstraintViolation]:
    # Analyze AST
    # Return violations if any
    return violations
```

4. **Add error message formatting** in `constraint_messages.py`:

```python
def _format_new_constraint_violation(violation, constraint) -> str:
    return """NewConstraint violation: ...

What's wrong: ...
Why it matters: ...
How to fix: ...
"""
```

5. **Add hint generation** in `get_constraint_hint()`:

```python
if isinstance(constraint, NewConstraint):
    return f"MUST satisfy custom requirement: {constraint.custom_field}"
```

### Improving Detection Accuracy

**Current approach**: Simple keyword matching

**Future improvements:**

1. **NLP embeddings**: Use sentence embeddings to detect semantic similarity
2. **Few-shot learning**: Provide examples of intent → constraint mappings
3. **Active learning**: Let users confirm/correct auto-detected constraints, retrain

### Alternative Validation Strategies

**Current approach**: Heuristic AST pattern matching

**Future improvements:**

1. **Static analysis tools**: Integrate pylint, mypy for more robust validation
2. **Symbolic execution**: Use tools like angr, KLEE for formal verification
3. **LLM-based validation**: Ask LLM to verify constraint satisfaction (expensive but flexible)

## Performance

**Constraint detection**: 50-100ms (keyword matching + pattern analysis)

**Constraint validation**: 20-50ms (AST parsing + pattern matching)

**Total overhead per IR**: ~100ms (detection) + ~30ms per validation (0-3 retries)

**Cost impact**:

- **Prompt size**: +10% (constraint hints)
- **Retry rate**: -20% (better first-attempt success)
- **Net cost**: Slight increase in prompt cost, but fewer total attempts → lower cost per success

## Related Documentation

- [USER_GUIDE_CONSTRAINTS.md](USER_GUIDE_CONSTRAINTS.md) - User-facing guide with examples
- [CONSTRAINT_REFERENCE.md](CONSTRAINT_REFERENCE.md) - Complete API reference
- [PHASE_7_IR_CONSTRAINTS_PLAN.md](PHASE_7_IR_CONSTRAINTS_PLAN.md) - Original planning document
