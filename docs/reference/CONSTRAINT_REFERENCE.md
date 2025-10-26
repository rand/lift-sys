# Constraint Reference

**Technical API Reference for IR-Level Constraints (Phase 7)**

This document provides complete technical documentation for the constraint system API. For user-focused documentation with examples, see [USER_GUIDE_CONSTRAINTS.md](USER_GUIDE_CONSTRAINTS.md).

## Table of Contents

- [Overview](#overview)
- [Core Types](#core-types)
- [Constraint Types](#constraint-types)
- [Detection Rules](#detection-rules)
- [Validation Logic](#validation-logic)
- [Serialization](#serialization)

## Overview

The constraint system provides three layers of functionality:

1. **Constraint Types** (`lift_sys.ir.constraints`) - Data classes representing requirements
2. **Constraint Detection** (`lift_sys.ir.constraint_detector`) - Automatic inference from natural language
3. **Constraint Validation** (`lift_sys.ir.constraint_validator`) - AST analysis to verify satisfaction

**Design principles:**

- Constraints specify requirements at IR level (language-agnostic)
- Work with any code structure implementing the same semantics
- Prevent bugs before generation (not fix after)
- Provide actionable feedback for LLM retry

## Core Types

### ConstraintType

```python
class ConstraintType(str, Enum):
    RETURN = "return_constraint"
    LOOP_BEHAVIOR = "loop_constraint"
    POSITION = "position_constraint"
```

**Usage**: Identifies which type of constraint to apply

### ConstraintSeverity

```python
class ConstraintSeverity(str, Enum):
    ERROR = "error"        # Blocks code generation, triggers retry
    WARNING = "warning"    # Logged but allows generation
```

**Default**: `ERROR`

**Usage**: Controls whether constraint violations block generation or just emit warnings

## Constraint Types

### Base: Constraint

All constraints inherit from this base class.

```python
@dataclass
class Constraint:
    type: ConstraintType
    description: str = ""
    severity: ConstraintSeverity = ConstraintSeverity.ERROR
```

**Fields:**

- `type` (ConstraintType, required): Type of constraint
- `description` (str, optional): Human-readable description of requirement
- `severity` (ConstraintSeverity, optional): Violation severity (default: ERROR)

**Methods:**

```python
def to_dict(self) -> dict[str, Any]:
    """Serialize constraint to dictionary."""

@classmethod
def from_dict(cls, data: dict[str, Any]) -> Constraint:
    """Deserialize constraint from dictionary."""
```

### ReturnConstraint

Ensures computed values are explicitly returned (not None or missing).

```python
@dataclass
class ReturnConstraint(Constraint):
    type: ConstraintType = ConstraintType.RETURN
    value_name: str = ""
    requirement: ReturnRequirement = ReturnRequirement.MUST_RETURN
```

**Fields:**

- `value_name` (str, required): Name of value that must be returned (e.g., "count", "result")
- `requirement` (ReturnRequirement, optional): Whether return is required (default: MUST_RETURN)

**ReturnRequirement values:**

```python
class ReturnRequirement(str, Enum):
    MUST_RETURN = "MUST_RETURN"          # Value must be explicitly returned
    OPTIONAL_RETURN = "OPTIONAL_RETURN"  # Value may optionally be returned
```

**Example:**

```python
ReturnConstraint(
    value_name="count",
    requirement=ReturnRequirement.MUST_RETURN,
    description="Function must return the computed count value"
)
```

**Prevents bugs like:**

```python
# ❌ Missing return
def count_words(text: str) -> int:
    count = len(text.split())
    # Forgot to return!

# ❌ Returns None
def count_words(text: str) -> int:
    count = len(text.split())
    return None
```

**Detection rules** (see [Detection Rules](#detection-rules)):

- Function has non-None return type
- Intent/effects mention: "count", "compute", "calculate", "find", "search"
- No explicit "return" mentioned in effects

**Validation logic** (see [Validation Logic](#validation-logic)):

- Checks function has at least one return statement
- Ensures not all returns are `return None`

### LoopBehaviorConstraint

Enforces specific loop behaviors (early return vs accumulation).

```python
@dataclass
class LoopBehaviorConstraint(Constraint):
    type: ConstraintType = ConstraintType.LOOP_BEHAVIOR
    search_type: LoopSearchType = LoopSearchType.FIRST_MATCH
    requirement: LoopRequirement = LoopRequirement.EARLY_RETURN
    loop_variable: str | None = None
```

**Fields:**

- `search_type` (LoopSearchType, required): Type of search operation
- `requirement` (LoopRequirement, required): Required loop behavior
- `loop_variable` (str, optional): Name of loop variable for clarity

**LoopSearchType values:**

```python
class LoopSearchType(str, Enum):
    FIRST_MATCH = "FIRST_MATCH"  # Find and return first matching element
    LAST_MATCH = "LAST_MATCH"    # Find and return last matching element
    ALL_MATCHES = "ALL_MATCHES"  # Find and return all matching elements
```

**LoopRequirement values:**

```python
class LoopRequirement(str, Enum):
    EARLY_RETURN = "EARLY_RETURN"  # Must return immediately on finding match
    ACCUMULATE = "ACCUMULATE"      # Must accumulate results, return after loop
    TRANSFORM = "TRANSFORM"        # Must transform elements, return collection
```

**Common combinations:**

- `FIRST_MATCH` + `EARLY_RETURN` - Find first occurrence
- `LAST_MATCH` + `ACCUMULATE` - Find last occurrence
- `ALL_MATCHES` + `ACCUMULATE` - Find all occurrences

**Example:**

```python
LoopBehaviorConstraint(
    search_type=LoopSearchType.FIRST_MATCH,
    requirement=LoopRequirement.EARLY_RETURN,
    loop_variable="item",
    description="Loop must return immediately on FIRST match (not continue)"
)
```

**Prevents bugs like:**

```python
# ❌ FIRST_MATCH without early return (finds LAST match instead)
def find_index(lst, value):
    result = -1
    for i, item in enumerate(lst):
        if item == value:
            result = i  # Accumulates to last match!
    return result

# ❌ ALL_MATCHES with early return (finds only FIRST match)
def find_all_indices(lst, value):
    for i, item in enumerate(lst):
        if item == value:
            return [i]  # Early return - wrong for ALL_MATCHES!
    return []
```

**Detection rules:**

- Intent/effects mention: "first", "last", "all", "each", "every"
- Intent/effects mention: "loop", "iterate", "for each", "traverse"

**Validation logic:**

- **EARLY_RETURN**: Checks for return statement inside loop body
- **ACCUMULATE**: Checks for list/accumulator variable updated in loop, return after loop

### PositionConstraint

Specifies position requirements between elements (e.g., "@" and "." in email validation).

```python
@dataclass
class PositionConstraint(Constraint):
    type: ConstraintType = ConstraintType.POSITION
    elements: list[str] = field(default_factory=list)
    requirement: PositionRequirement = PositionRequirement.NOT_ADJACENT
    min_distance: int = 0
    max_distance: int | None = None
```

**Fields:**

- `elements` (list[str], required): Elements whose positions are constrained (e.g., ["@", "."])
- `requirement` (PositionRequirement, required): Required relationship between elements
- `min_distance` (int, optional): Minimum character distance (default: 0)
- `max_distance` (int | None, optional): Maximum character distance (default: None = unlimited)

**PositionRequirement values:**

```python
class PositionRequirement(str, Enum):
    NOT_ADJACENT = "NOT_ADJACENT"    # Elements must NOT be immediately adjacent
    ORDERED = "ORDERED"              # Elements must appear in specified order
    MIN_DISTANCE = "MIN_DISTANCE"    # Elements must be >= N characters apart
    MAX_DISTANCE = "MAX_DISTANCE"    # Elements must be <= N characters apart
```

**Example:**

```python
PositionConstraint(
    elements=["@", "."],
    requirement=PositionRequirement.NOT_ADJACENT,
    min_distance=1,
    description="Dot must NOT be immediately adjacent to @"
)
```

**Prevents bugs like:**

```python
# ❌ No position check (accepts invalid emails like "test@.com")
def is_valid_email(email: str) -> bool:
    return '@' in email and '.' in email  # No distance check!

# ✅ With position check
def is_valid_email(email: str) -> bool:
    at_idx = email.find('@')
    dot_idx = email.find('.')
    if at_idx == -1 or dot_idx == -1:
        return False
    return abs(at_idx - dot_idx) > 1  # Checks distance
```

**Detection rules:**

- Email validation: Intent mentions "@", ".", "email"
- Parentheses matching: Intent mentions "(", ")", "bracket", "balanced"
- Adjacency: Intent mentions "adjacent", "next to", "immediately after"

**Validation logic:**

- **NOT_ADJACENT**: Checks for position comparison using `abs()` or distance check
- **ORDERED**: Checks for position comparison (e.g., `idx1 < idx2`)
- **MIN_DISTANCE/MAX_DISTANCE**: Checks for distance calculation with appropriate threshold

## Detection Rules

The `ConstraintDetector` automatically infers constraints from IR specifications using keyword matching.

**Module**: `lift_sys.ir.constraint_detector`

### ReturnConstraint Detection

**Trigger conditions:**

1. Function has non-None return type (`signature.returns` not None)
2. Intent/effects mention computation keywords: "count", "compute", "calculate", "find", "search", "sum", "result"
3. Effects do NOT explicitly mention "return"

**Keyword patterns:**

```python
RETURN_KEYWORDS = [
    "return", "returns",
    "compute", "computes",
    "calculate", "calculates",
    "count", "counts",
    "sum", "sums",
    "result", "output"
]
```

**Value name inference:**

- Extracts from intent/effects (e.g., "count words" → value_name="count")
- Defaults to "result" if not inferrable

**Example:**

```python
# Intent: "Count the number of words in a string"
# Effects: ["Compute count of words"]
# Returns: int
#
# → ReturnConstraint(value_name="count")
```

### LoopBehaviorConstraint Detection

**Trigger conditions:**

1. Intent/effects mention loop keywords: "loop", "iterate", "for each", "traverse"
2. Intent/effects mention search type keywords: "first", "last", "all"

**Keyword patterns:**

```python
FIRST_MATCH_KEYWORDS = ["first", "earliest", "initial", "find first"]
LAST_MATCH_KEYWORDS = ["last", "final", "find last"]
ALL_MATCHES_KEYWORDS = ["all", "every", "each", "collect all", "find all"]
LOOP_KEYWORDS = ["loop", "iterate", "iteration", "for each", "traverse"]
```

**Search type determination:**

- "first" → `FIRST_MATCH` + `EARLY_RETURN`
- "last" → `LAST_MATCH` + `ACCUMULATE`
- "all" → `ALL_MATCHES` + `ACCUMULATE`

**Example:**

```python
# Intent: "Find the first index of value in list"
# Effects: ["Iterate through list", "Return first match"]
#
# → LoopBehaviorConstraint(
#     search_type=FIRST_MATCH,
#     requirement=EARLY_RETURN
# )
```

### PositionConstraint Detection

**Trigger conditions:**

1. Email validation: Intent mentions "@", ".", "email"
2. Parentheses matching: Intent mentions "(", ")", "bracket", "balanced"
3. Adjacency: Intent mentions "adjacent", "next to", "distance"

**Keyword patterns:**

```python
POSITION_KEYWORDS = [
    "adjacent", "next to",
    "immediately after", "immediately before",
    "distance", "position", "placement",
    "between", "not adjacent", "separated"
]
```

**Special cases:**

- **Email validation**: Automatically adds NOT_ADJACENT constraint for ["@", "."]
- **Parentheses**: Automatically adds ORDERED constraint for ["(", ")"]

**Example:**

```python
# Intent: "Validate email address format"
# Effects: ["Check for @ and . symbols"]
#
# → PositionConstraint(
#     elements=["@", "."],
#     requirement=NOT_ADJACENT,
#     min_distance=1
# )
```

## Validation Logic

The `ConstraintValidator` performs AST analysis to verify code satisfies constraints.

**Module**: `lift_sys.ir.constraint_validator`

### General Approach

1. Parse code into AST using `ast.parse()`
2. Find function by name from IR signature
3. Apply constraint-specific validation logic
4. Return list of violations (empty if all satisfied)

### ReturnConstraint Validation

**Steps:**

1. Find all `return` statements in function body
2. Check if at least one return exists
3. Check if any returns are non-None values

**Violation cases:**

- **No return statement**: `"No return statement found in function"`
- **All returns are None**: `"All return statements return None, but should return '{value_name}'"`

**AST pattern matching:**

```python
for node in ast.walk(function_def):
    if isinstance(node, ast.Return):
        if node.value is None or is_none_constant(node.value):
            # Returns None
        else:
            # Returns non-None value
```

### LoopBehaviorConstraint Validation

**Steps:**

1. Find all loop statements (`for`, `while`)
2. Check for return statements inside loop body
3. Check for accumulator patterns (list append, variable assignment)

**Violation cases:**

- **EARLY_RETURN missing**: `"Loop requires early return for FIRST_MATCH, but has no return inside loop"`
- **ACCUMULATE with early return**: `"Loop requires ACCUMULATE for ALL_MATCHES, but has early return"`

**AST pattern matching:**

```python
# Check for early return pattern
for node in ast.walk(loop_node):
    if isinstance(node, ast.Return):
        has_early_return = True

# Check for accumulator pattern
for node in ast.walk(loop_node):
    if isinstance(node, ast.Call) and getattr(node.func, 'attr', None) == 'append':
        has_accumulator = True
```

### PositionConstraint Validation

**Steps:**

1. Search for position-related operations (`.find()`, `.index()`)
2. Search for distance calculations (`abs()`, subtraction)
3. Verify comparison operators check position relationships

**Violation cases:**

- **NOT_ADJACENT missing check**: `"Code does not verify elements are not adjacent"`
- **ORDERED missing check**: `"Code does not verify elements appear in order"`

**AST pattern matching:**

```python
# Check for position comparison
for node in ast.walk(function_def):
    if isinstance(node, ast.Compare):
        if has_abs_call(node) or has_subtraction(node):
            has_position_check = True
```

### Validation Result

```python
@dataclass
class ConstraintViolation:
    constraint_type: str           # e.g., "return_constraint"
    description: str               # Human-readable violation message
    severity: str = "error"        # "error" or "warning"
    line_number: int | None = None # Optional line number
```

## Serialization

All constraints support serialization to/from dictionaries for JSON storage.

### to_dict()

```python
constraint = ReturnConstraint(value_name="count")
data = constraint.to_dict()
# {
#   "type": "return_constraint",
#   "value_name": "count",
#   "requirement": "MUST_RETURN",
#   "description": "Function must return 'count' value explicitly",
#   "severity": "error"
# }
```

### from_dict()

```python
data = {
    "type": "return_constraint",
    "value_name": "result",
    "requirement": "MUST_RETURN"
}
constraint = Constraint.from_dict(data)
# Returns ReturnConstraint(value_name="result", ...)
```

### parse_constraint()

Convenience function for parsing constraint dictionaries:

```python
from lift_sys.ir.constraints import parse_constraint

data = {"type": "loop_constraint", "search_type": "FIRST_MATCH", ...}
constraint = parse_constraint(data)
# Returns LoopBehaviorConstraint(search_type=FIRST_MATCH, ...)
```

## Integration

### IR Integration

Constraints are stored on the `IntermediateRepresentation` object:

```python
from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.ir.constraints import ReturnConstraint

ir = IntermediateRepresentation(
    intent=...,
    signature=...,
    constraints=[
        ReturnConstraint(value_name="count"),
        # ... more constraints
    ]
)
```

### Detection Integration

```python
from lift_sys.ir.constraint_detector import ConstraintDetector

detector = ConstraintDetector()
constraints = detector.detect_constraints(ir)
ir.constraints = constraints
```

### Validation Integration

```python
from lift_sys.ir.constraint_validator import (
    ConstraintValidator,
    validate_code_against_constraints,
)

# Option 1: Direct validator
validator = ConstraintValidator()
violations = validator.validate(code, ir)

# Option 2: Convenience function
is_valid, violations = validate_code_against_constraints(code, ir)
```

### Code Generation Integration

Constraints are used in the code generation retry loop:

```python
# In XGrammarCodeGenerator.generate()
for attempt in range(max_retries):
    code = generate_code(ir)

    # Validate constraints
    if ir.constraints:
        violations = validator.validate(code, ir)
        if violations:
            # Format enhanced error message
            feedback = format_violations_summary(violations)
            # Retry with feedback
            continue

    return code
```

## Testing

### Unit Tests

- `tests/ir/test_constraints.py` - Constraint data class tests
- `tests/ir/test_constraint_detector.py` - Detection logic tests
- `tests/ir/test_constraint_validator.py` - Validation logic tests

### Integration Tests

- `tests/integration/test_xgrammar_translator_with_constraints.py` - End-to-end translation with constraint detection
- `tests/integration/test_xgrammar_code_generator_with_constraints.py` - End-to-end generation with constraint validation

## Performance

**Detection overhead**: ~50-100ms per IR (keyword matching)

**Validation overhead**: ~20-50ms per validation (AST parsing + analysis)

**Retry attempts**: 0-3 (only if violations occur)

**Cost impact**: +10% longer prompts, but higher success rate reduces total cost per success

## Related Documentation

- [USER_GUIDE_CONSTRAINTS.md](USER_GUIDE_CONSTRAINTS.md) - User-focused documentation with examples
- [PHASE_7_ARCHITECTURE.md](PHASE_7_ARCHITECTURE.md) - Technical implementation details (upcoming)
- Phase 7 completion summary (upcoming)
