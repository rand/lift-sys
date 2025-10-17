# Phase 5: IR Interpreter for Semantic Validation

**Date**: October 16, 2025
**Status**: Planning → Implementation
**Goal**: Catch semantic logic errors before code generation

---

## Problem Statement

**Current limitation**: AST repair fixes syntactic bugs, but can't catch semantic logic errors.

**Persistent failures** (3/18 tests):
1. **count_words** - Returns None instead of count (missing return logic)
2. **find_index** - Off-by-one error (returns last index, not first)
3. **is_valid_email** - Validation logic accepts invalid emails

These are **semantic errors** - the syntax is correct, but the logic is wrong.

---

## Solution: Symbolic IR Interpretation

**Key insight**: Instead of just checking assertions on generated code, **interpret the IR symbolically** to detect logic errors in the specification itself.

### Example: count_words

**IR Effects**:
```
1. Split string by spaces
2. Iterate through split result
3. Count elements
```

**Problem**: Effects don't explicitly return the count.

**IR Interpreter would detect**:
- Effect chain produces a value (count)
- But no effect says "return this value"
- **Semantic error**: Missing return logic

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────┐
│         IR Interpreter                          │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  1. Effect Chain Analyzer                │  │
│  │     - Parse effect descriptions          │  │
│  │     - Build symbolic execution trace     │  │
│  │     - Track data flow                    │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  2. Semantic Validator                   │  │
│  │     - Check return value consistency     │  │
│  │     - Validate control flow completeness │  │
│  │     - Verify assertion coverage          │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  3. Logic Error Detector                 │  │
│  │     - Off-by-one patterns                │  │
│  │     - Missing return statements          │  │
│  │     - Unreachable code                   │  │
│  │     - Invalid validation logic           │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Data Model

```python
@dataclass
class SymbolicValue:
    """Represents a value in symbolic execution."""
    name: str
    type_hint: str
    source: str  # "parameter", "computed", "literal"
    provenance: list[str]  # Trail of operations

@dataclass
class ExecutionTrace:
    """Trace of symbolic execution through effects."""
    values: dict[str, SymbolicValue]
    operations: list[str]
    return_value: SymbolicValue | None
    issues: list[SemanticIssue]

@dataclass
class SemanticIssue:
    """A semantic error detected during interpretation."""
    severity: str  # "error", "warning"
    category: str  # "missing_return", "off_by_one", "invalid_logic"
    message: str
    effect_index: int | None
    suggestion: str | None
```

---

## Implementation Plan

### Step 1: Effect Chain Analyzer (2-3 hours)

Parse effect descriptions and build symbolic execution trace.

**Input**: IR with effects
```json
{
  "effects": [
    {"description": "Split input string by spaces into words list"},
    {"description": "Iterate through words list"},
    {"description": "Count the number of elements"}
  ]
}
```

**Output**: ExecutionTrace
```python
ExecutionTrace(
    values={
        "input_string": SymbolicValue(name="input_string", type="str", source="parameter"),
        "words": SymbolicValue(name="words", type="list[str]", source="computed",
                              provenance=["split(input_string, ' ')"]),
        "count": SymbolicValue(name="count", type="int", source="computed",
                              provenance=["len(words)"])
    },
    operations=["split", "iterate", "count"],
    return_value=None,  # ❌ Missing!
    issues=[
        SemanticIssue(
            severity="error",
            category="missing_return",
            message="Effect chain produces 'count' but doesn't return it",
            effect_index=2,
            suggestion="Add effect: 'Return the count'"
        )
    ]
)
```

**Implementation**:
- Parse effect descriptions using LLM or regex patterns
- Extract verbs (split, iterate, count) and objects (string, list, elements)
- Track data flow between effects
- Detect produced values and their types

**File**: `lift_sys/validation/effect_analyzer.py` (~300 lines)

---

### Step 2: Semantic Validator (2-3 hours)

Check IR consistency and validate semantics.

**Checks**:
1. **Return value consistency**: If signature says `returns: int`, ensure effect chain produces int
2. **Parameter usage**: All parameters used in effects
3. **Assertion coverage**: Assertions match return type and effects
4. **Control flow completeness**: All paths return a value (if return type specified)

**Implementation**:
```python
class SemanticValidator:
    def validate_return_consistency(self, ir: IR, trace: ExecutionTrace) -> list[SemanticIssue]:
        """Ensure effect chain produces value matching return type."""
        issues = []

        if ir.signature.returns:
            if not trace.return_value:
                issues.append(SemanticIssue(
                    severity="error",
                    category="missing_return",
                    message=f"Function returns '{ir.signature.returns}' but effect chain doesn't return anything",
                    suggestion="Add return effect or fix effect chain"
                ))
            elif trace.return_value.type_hint != ir.signature.returns:
                issues.append(SemanticIssue(
                    severity="warning",
                    category="type_mismatch",
                    message=f"Effect chain returns '{trace.return_value.type_hint}' but signature says '{ir.signature.returns}'",
                ))

        return issues

    def validate_assertion_coverage(self, ir: IR, trace: ExecutionTrace) -> list[SemanticIssue]:
        """Ensure assertions can be checked by effects."""
        # Check that assertions reference values produced by effects
        pass
```

**File**: `lift_sys/validation/semantic_validator.py` (~400 lines)

---

### Step 3: Logic Error Detector (2-3 hours)

Detect common semantic bug patterns.

**Patterns to detect**:

1. **Off-by-one errors**:
   - Effect says "find first occurrence" but returns last index
   - Loop index confusion (enumerate bugs)

2. **Missing return statements**:
   - Effect chain produces value but doesn't return it
   - Already handled in Step 2

3. **Invalid validation logic**:
   - Email validation that accepts `test@.com`
   - Pattern: "Check if X contains Y" but logic is wrong

4. **Unreachable code**:
   - Effect after unconditional return
   - Contradictory conditions

**Implementation**:
```python
class LogicErrorDetector:
    def detect_off_by_one(self, ir: IR, trace: ExecutionTrace) -> list[SemanticIssue]:
        """Detect potential off-by-one errors."""
        issues = []

        # Look for "first" in intent/effects but "last" in implementation
        intent_text = ir.intent.summary.lower()
        effect_texts = [e.description.lower() for e in ir.effects]

        if "first" in intent_text or any("first" in e for e in effect_texts):
            # Check if effects use patterns that might return last instead
            for i, effect in enumerate(ir.effects):
                if "enumerate" in effect.description.lower():
                    # Common bug: returning index at end of loop (last) instead of first
                    if "return" in effect.description.lower():
                        issues.append(SemanticIssue(
                            severity="warning",
                            category="off_by_one",
                            message="Effect returns index from enumerate loop - ensure it returns FIRST match, not last",
                            effect_index=i,
                            suggestion="Return immediately when found, don't continue loop"
                        ))

        return issues

    def detect_invalid_validation(self, ir: IR) -> list[SemanticIssue]:
        """Detect validation logic that might be incorrect."""
        issues = []

        intent = ir.intent.summary.lower()
        if "valid" in intent or "validate" in intent or "check" in intent:
            # This is a validation function
            # Check assertions for obvious bugs
            for assertion in ir.assertions:
                pred = assertion.predicate.lower()

                # Example: email validation
                if "email" in intent:
                    if "@" in pred and "." in pred:
                        # Check if validation is complete
                        if "after" not in pred:
                            issues.append(SemanticIssue(
                                severity="warning",
                                category="invalid_logic",
                                message="Email validation may be incomplete - ensure dot comes AFTER @",
                                suggestion="Check that dot position > @ position"
                            ))

        return issues
```

**File**: `lift_sys/validation/logic_error_detector.py` (~350 lines)

---

### Step 4: Integration (1-2 hours)

Integrate IR Interpreter into code generation pipeline.

**Current flow**:
```
NLP → IR → Code Generation → AST Repair → Validation
```

**New flow**:
```
NLP → IR → IR Interpreter (NEW!) → Code Generation → AST Repair → Validation
                ↓
           Reject IR if semantic errors
           Provide feedback for regeneration
```

**Implementation**:
```python
class XGrammarCodeGenerator:
    def generate(self, ir: IR) -> GenerationResult:
        # NEW: Interpret IR before generating code
        interpreter = IRInterpreter()
        interpretation = interpreter.interpret(ir)

        if interpretation.has_errors():
            return GenerationResult(
                success=False,
                error="Semantic validation failed",
                issues=interpretation.issues,
                suggestions=[issue.suggestion for issue in interpretation.issues if issue.suggestion]
            )

        # Continue with code generation...
        code = self._generate_code_from_ir(ir)

        # Apply AST repair
        repaired_code = self.ast_repairer.repair(code, ir.signature.name)

        return GenerationResult(
            success=True,
            source_code=repaired_code,
            semantic_issues=interpretation.warnings  # Non-blocking warnings
        )
```

**File**: Update `lift_sys/codegen/xgrammar_generator.py` (~50 line additions)

---

### Step 5: Testing (2-3 hours)

Test on the 3 persistent failures.

**Test 1: count_words**
- Input IR: Effects that count but don't return
- Expected: Detect missing return
- Action: Regenerate IR with explicit return effect

**Test 2: find_index**
- Input IR: Find first occurrence with enumerate
- Expected: Warn about off-by-one risk
- Action: Validate generated code returns first, not last

**Test 3: is_valid_email**
- Input IR: Email validation with @ and .
- Expected: Warn about incomplete validation (dot after @)
- Action: Regenerate with explicit "dot after @" check

**Files**:
- `tests/validation/test_ir_interpreter.py` (~200 lines)
- `tests/integration/test_phase5_semantic_validation.py` (~150 lines)

---

## Success Metrics

**Primary goal**: Reduce Phase 3 failures from 3 to 0-1 (83.3% → 94-100%)

**Targets**:
- ✅ **count_words**: Detect missing return → regenerate IR → pass
- ✅ **find_index**: Detect off-by-one risk → validate code → pass
- ✅ **is_valid_email**: Detect incomplete validation → regenerate → pass

**Metrics**:
- IR rejection rate: Expect 10-20% of IRs to have semantic issues
- Regeneration success: 80%+ of rejected IRs pass after one regeneration
- False positive rate: <5% (don't reject valid IRs)

---

## Timeline

| Task | Effort | Status |
|------|--------|--------|
| 1. Effect Chain Analyzer | 2-3 hours | Pending |
| 2. Semantic Validator | 2-3 hours | Pending |
| 3. Logic Error Detector | 2-3 hours | Pending |
| 4. Integration | 1-2 hours | Pending |
| 5. Testing | 2-3 hours | Pending |
| **Total** | **9-14 hours** | **~2 days** |

---

## Future Enhancements

**Phase 5b**: More sophisticated patterns
- Symbolic execution with SMT solver
- Abstract interpretation
- Control flow graph analysis

**Phase 5c**: LLM-based semantic checking
- Use LLM to reason about IR consistency
- Generate test cases from effects
- Suggest fixes for detected issues

---

## Risks & Mitigations

**Risk 1**: False positives reject valid IRs
- **Mitigation**: Conservative warnings, only error on obvious bugs
- **Fallback**: User can override with flag

**Risk 2**: Can't parse all effect descriptions
- **Mitigation**: Start with simple patterns, expand coverage iteratively
- **Fallback**: Skip interpretation if can't parse (don't block generation)

**Risk 3**: Adds latency to generation pipeline
- **Mitigation**: Interpretation should be <100ms (mostly regex/pattern matching)
- **Monitoring**: Track interpretation time in metrics

---

## References

- Current validation: `lift_sys/validation/assertion_checker.py`
- AST repair: `lift_sys/codegen/ast_repair.py` (5 passes)
- Test failures: `docs/PERSISTENT_FAILURES_ANALYSIS.md`
