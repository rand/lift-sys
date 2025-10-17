# User Guide: IR-Level Constraints

**Phase 7 Feature - Automatic Constraint Detection and Validation**

## Overview

IR-level constraints are explicit requirements that guide LLM code generation and validate the output. Instead of fixing bugs after generation (like AST repair), constraints prevent bugs by specifying requirements upfront and validating generated code against them.

### Key Benefits

1. **Prevents bugs before generation** - Constraints guide the LLM to generate correct code
2. **Works with any code structure** - Not tied to specific AST patterns
3. **Automatic detection** - Constraints are inferred from natural language specifications
4. **Clear error messages** - When violations occur, detailed feedback helps fix them

## How It Works

### 1. Automatic Detection (Phase 7 Week 1)

When you translate a natural language prompt to IR, constraints are automatically detected:

```python
from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator

translator = XGrammarIRTranslator(provider)
ir = await translator.translate("Find the first index of value in list")

# IR now has constraints automatically detected:
# - LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN)
# - ReturnConstraint(value_name="index")
```

### 2. Generation Guidance

Constraints are included in the code generation prompt to guide the LLM:

```
Generate Python code with these REQUIRED constraints:
- MUST use early return inside loop for FIRST match (not accumulate to last)
- MUST explicitly return 'index' value (not None)
```

### 3. Post-Generation Validation (Phase 7 Week 2)

After code is generated, it's validated against constraints:

```python
from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator

generator = XGrammarCodeGenerator(provider)
result = await generator.generate(ir, max_retries=3)

# If constraints are violated, generator retries with detailed feedback
# If all attempts fail, returns best attempt with warnings
```

## Constraint Types

### ReturnConstraint

**Purpose**: Ensures computed values are explicitly returned (not None or missing).

**When detected**:
- Function has non-None return type
- Effect description mentions "count", "compute", "calculate", "find", "search"
- Effect does NOT explicitly mention "return"

**Example**:

```python
# Natural language:
"Count the number of words in a string"

# Detected constraint:
ReturnConstraint(
    value_name="count",
    requirement=MUST_RETURN,
    description="Function must return 'count' value explicitly"
)

# Valid implementation:
def count_words(text: str) -> int:
    count = len(text.split())
    return count  # ✓ Explicitly returns computed value

# Invalid (violates constraint):
def count_words(text: str) -> int:
    count = len(text.split())
    # Missing return!  ✗ Constraint violation
```

**Common violations**:
- No return statement
- Returns None instead of computed value
- Forgets to return after computation

### LoopBehaviorConstraint

**Purpose**: Enforces correct loop patterns (early return vs accumulation).

**When detected**:
- Effect mentions loop keywords: "iterate", "for each", "loop", "traverse"
- Search type keywords: "first", "last", "all"

**Search Types**:

#### FIRST_MATCH (requires EARLY_RETURN)

```python
# Natural language:
"Find the first index of value in list"

# Detected constraint:
LoopBehaviorConstraint(
    search_type=FIRST_MATCH,
    requirement=EARLY_RETURN,
    description="Loop must return immediately on FIRST match"
)

# Valid implementation:
def find_index(lst, value):
    for i, item in enumerate(lst):
        if item == value:
            return i  # ✓ Early return on first match
    return -1

# Invalid (violates constraint):
def find_index(lst, value):
    result = -1
    for i, item in enumerate(lst):
        if item == value:
            result = i  # ✗ Accumulates to LAST match, not first!
    return result
```

#### ALL_MATCHES (requires ACCUMULATE)

```python
# Natural language:
"Find all indices where value appears"

# Detected constraint:
LoopBehaviorConstraint(
    search_type=ALL_MATCHES,
    requirement=ACCUMULATE,
    description="Loop must return ALL matches"
)

# Valid implementation:
def find_all_indices(lst, value):
    indices = []  # Accumulator
    for i, item in enumerate(lst):
        if item == value:
            indices.append(i)  # ✓ Accumulates all matches
    return indices

# Invalid (violates constraint):
def find_all_indices(lst, value):
    for i, item in enumerate(lst):
        if item == value:
            return [i]  # ✗ Early return - only returns first!
    return []
```

#### LAST_MATCH (requires ACCUMULATE)

```python
# Natural language:
"Find the last occurrence of character"

# Detected constraint:
LoopBehaviorConstraint(
    search_type=LAST_MATCH,
    requirement=ACCUMULATE,
    description="Loop must return LAST match"
)

# Valid implementation:
def find_last(text, char):
    last_idx = -1
    for i, c in enumerate(text):
        if c == char:
            last_idx = i  # ✓ Updates to last match
    return last_idx
```

### PositionConstraint

**Purpose**: Specifies position requirements between elements.

**When detected**:
- Email validation: mentions "@", ".", "email"
- Parentheses matching: mentions "(", ")", "bracket", "balanced"
- Adjacency keywords: "adjacent", "next to", "immediately after"

**Requirements**:

#### NOT_ADJACENT

```python
# Natural language:
"Validate email address format"

# Detected constraint:
PositionConstraint(
    elements=["@", "."],
    requirement=NOT_ADJACENT,
    min_distance=1,
    description="Dot must NOT be immediately adjacent to @"
)

# Valid implementation:
def is_valid_email(email: str) -> bool:
    at_idx = email.find('@')
    dot_idx = email.find('.')
    if at_idx == -1 or dot_idx == -1:
        return False
    return abs(at_idx - dot_idx) > 1  # ✓ Checks distance

# Invalid (violates constraint):
def is_valid_email(email: str) -> bool:
    return '@' in email and '.' in email  # ✗ No position check!
    # This accepts invalid emails like "test@.com"
```

#### ORDERED

```python
# Natural language:
"Check if parentheses are balanced"

# Detected constraint:
PositionConstraint(
    elements=["(", ")"],
    requirement=ORDERED,
    description="Opening parenthesis must come before closing"
)

# Valid implementation:
def is_balanced(text: str) -> bool:
    open_idx = text.find('(')
    close_idx = text.find(')')
    return open_idx != -1 and close_idx != -1 and open_idx < close_idx
```

## Error Messages

When constraints are violated, you receive detailed error messages with:

1. **What's wrong** - Clear explanation of the violation
2. **Why it matters** - Impact on correctness
3. **How to fix** - Actionable suggestions with examples

### Example Error Message

```
================================================================================
CONSTRAINT VALIDATION FAILED
================================================================================

Found 1 ERROR(s) - must fix before code can be accepted:

ERROR 1/1:
--------------------------------------------------------------------------------
ReturnConstraint violation: Missing return statement

What's wrong:
  Function does not have a return statement, but it computes 'count'

Why it matters:
  Without an explicit return, the function will return None instead of the
  computed value. This causes tests to fail and violates the function's contract.

How to fix:
  Add 'return count' after computing the value

Example:
  # Current (wrong):
  def compute_result(data):
      count = process(data)
      # Missing return!

  # Fixed (correct):
  def compute_result(data):
      count = process(data)
      return count

================================================================================
Please fix these violations in the next generation attempt.
================================================================================
```

## Advanced Usage

### Manual Constraint Specification

While constraints are automatically detected, you can manually add or override them:

```python
from lift_sys.ir.constraints import (
    ReturnConstraint,
    LoopBehaviorConstraint,
    LoopSearchType,
    LoopRequirement,
)

# Manually create IR with custom constraints
ir = IntermediateRepresentation(
    intent=IntentClause(summary="Custom function"),
    signature=SigClause(
        name="my_function",
        parameters=[Parameter(name="data", type_hint="list")],
        returns="int"
    ),
    constraints=[
        ReturnConstraint(value_name="result", requirement="MUST_RETURN"),
        LoopBehaviorConstraint(
            search_type=LoopSearchType.FIRST_MATCH,
            requirement=LoopRequirement.EARLY_RETURN,
            loop_variable="item"
        )
    ]
)
```

### Disabling Constraint Detection

If you want to disable automatic constraint detection:

```python
# During IR translation - constraints still auto-detected
ir = await translator.translate("Find first value")

# Manually clear constraints
ir.constraints = []

# Or filter specific constraint types
ir.constraints = [
    c for c in ir.constraints
    if not isinstance(c, ReturnConstraint)
]
```

### Constraint Severity Levels

Constraints have severity levels:

- **ERROR** (default): Blocks code generation, triggers retry
- **WARNING**: Logged but doesn't block generation

```python
from lift_sys.ir.constraints import ConstraintSeverity

constraint = ReturnConstraint(
    value_name="result",
    severity=ConstraintSeverity.WARNING  # Won't block generation
)
```

## Integration with Existing Phases

Constraints work seamlessly with other validation phases:

```
Code Generation Pipeline:

1. IR Translation          → Constraints auto-detected
2. Code Generation         → Constraints guide LLM
3. AST Repair (Phase 4)    → Fixes syntax/structure
4. Constraint Validation   → Validates semantic correctness (Phase 7)
5. Assertion Checking      → Validates runtime behavior (Phase 5b)
6. Final Code              → All validations passed
```

**Validation sequence** (retry loop):
- Generate code
- Repair AST issues (missing returns, unbalanced brackets)
- **Validate constraints** (return exists, early return pattern, position checks)
- Check assertions (runtime values correct)
- Success or retry with feedback

## Best Practices

### 1. Trust Automatic Detection

Constraint detection is designed to be accurate. Let it work automatically rather than manually specifying constraints unless you have specific needs.

### 2. Review Detected Constraints

When debugging, check what constraints were detected:

```python
ir = await translator.translate(prompt)

print(f"Detected {len(ir.constraints)} constraints:")
for constraint in ir.constraints:
    print(f"  - {constraint.type.value}: {constraint.description}")
```

### 3. Use Clear Natural Language

Constraint detection works best with clear, specific language:

- ✓ "Find the **first** index where value appears"
- ✗ "Find where value appears" (ambiguous - first? all?)

- ✓ "**Count** the number of words" (triggers ReturnConstraint)
- ✗ "Get words" (vague - count? list? what?)

- ✓ "Validate email format (**@ and . must not be adjacent**)"
- ✗ "Check email" (missing position requirement)

### 4. Leverage Error Messages

When constraint violations occur, read the error messages carefully. They include:
- Explanation of what's wrong
- Why it matters for correctness
- Concrete examples of how to fix

### 5. Combine with Assertions

Constraints validate structure and patterns. Assertions validate runtime behavior. Use both:

```python
ir = IntermediateRepresentation(
    intent=IntentClause(summary="Find first even number"),
    signature=SigClause(...),
    constraints=[
        LoopBehaviorConstraint(FIRST_MATCH, EARLY_RETURN)  # Structure
    ],
    assertions=[
        Assertion(
            predicate="result % 2 == 0",  # Runtime behavior
            description="Result must be even"
        )
    ]
)
```

## Troubleshooting

### Constraint Detected But Not Needed

If a constraint is incorrectly detected:

```python
# Option 1: Filter it out
ir.constraints = [c for c in ir.constraints if c.type != ConstraintType.RETURN]

# Option 2: Clarify natural language
# Instead of: "Count items"
# Try: "Return list of items" (avoids ReturnConstraint for count)
```

### Constraint Not Detected

If expected constraint is missing:

```python
# Option 1: Make natural language more explicit
# Instead of: "Find value"
# Try: "Find the FIRST index of value" (triggers FIRST_MATCH)

# Option 2: Manually add constraint
from lift_sys.ir.constraints import LoopBehaviorConstraint

ir.constraints.append(
    LoopBehaviorConstraint(
        search_type=LoopSearchType.FIRST_MATCH,
        requirement=LoopRequirement.EARLY_RETURN
    )
)
```

### Constraint Validation Fails Incorrectly

If validation incorrectly reports violation:

1. Check that code actually satisfies constraint
2. Review validator heuristics (may have false positives)
3. Use severity=WARNING to downgrade if needed
4. Report as issue for improvement

## Performance Impact

Constraint system adds minimal overhead:

- **Detection time**: ~50-100ms (during IR translation)
- **Validation time**: ~20-50ms (AST analysis)
- **Retry attempts**: 0-3 (only if violations occur)

**Cost analysis**:
- Baseline cost per IR: $0.0056
- With constraints: ~$0.0062 (+10% for longer prompts)
- **Cost per success**: Decreases due to higher first-attempt success rate

## Related Documentation

- [Constraint Reference](CONSTRAINT_REFERENCE.md) - Complete constraint type reference
- [Phase 7 Architecture](PHASE_7_ARCHITECTURE.md) - Technical implementation details
- [Phase 7 Completion Summary](../PHASE_7_COMPLETE.md) - Full phase 7 results
