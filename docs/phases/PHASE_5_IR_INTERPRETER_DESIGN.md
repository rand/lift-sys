# Phase 5: IR Interpreter Design

**Goal**: Semantic validation to catch logic errors BEFORE they cause test failures

**Target**: 90% → 95%+ success rate

---

## Problem Analysis

**Current State** (90% with Phase 4 v2):
- ✅ Syntactic errors caught (AST repair fixes loop returns, type checks)
- ❌ Semantic errors not caught (get_type_name logic bug)

**get_type_name Failure**:
```
Expected: 'other'
Actual: 'int'
```

**Root Cause**: Generated code has incorrect conditional logic - one branch returns wrong value for certain inputs.

---

## Approach: Code-to-Spec Validation

Instead of "interpreting the IR" (too high-level), we **validate generated code against IR specifications**.

###Strategy

1. **Parse IR Intent & Assertions** → Understand what code SHOULD do
2. **Abstract Interpret Generated Code** → Understand what code DOES
3. **Compare** → Detect mismatches

This catches semantic bugs like:
- Missing edge cases
- Wrong return values for some inputs
- Incomplete conditional coverage

---

## Architecture

```
Generated Code
      ↓
[Abstract Interpreter]  ← Symbolic execution
      ↓
Abstract State Space (all possible behaviors)
      ↓
[Specification Checker] ← Compare vs IR
      ↓
Validation Report (pass/fail + specific errors)
```

---

## Implementation Plan

### Phase 5a: Simple Assertion Checker (Quick Win)

**Goal**: Validate generated code satisfies IR assertions

**Approach**:
```python
class SimpleAssertionChecker:
    """Check generated code against IR assertions."""

    def validate(self, code: str, ir: IntermediateRepresentation) -> ValidationResult:
        # 1. Execute code with symbolic/concrete inputs
        # 2. Check if assertions hold
        # 3. Report violations
```

**Example** (get_type_name):
```python
IR Assertions:
- "Returns 'int' for integer inputs"
- "Returns 'str' for string inputs"
- "Returns 'list' for list inputs"
- "Returns 'other' for other types"

Checker validates:
- check_type(42) == 'int' ✓
- check_type("hello") == 'str' ✓
- check_type([1,2,3]) == 'list' ✓
- check_type(3.14) == 'other' ✗ (returns 'int' - BUG!)
```

**Benefit**: Catches the get_type_name bug!

### Phase 5b: Control Flow Validator (Medium Term)

**Goal**: Validate all code paths are semantically correct

**Approach**:
- Build control flow graph (CFG) from generated code
- Identify all paths
- Check each path satisfies intent

**Example** (find_index):
```python
Paths:
1. Found → return index
2. Not found → return -1

Validate:
- Path 1 returns correct index ✓
- Path 2 executes after loop ✓ (Phase 4 ensures this)
```

### Phase 5c: Full Abstract Interpreter (Long Term)

**Goal**: Complete semantic validation

**Approach**:
- Symbolic execution of generated code
- Abstract domains for values
- Check against full IR specification

---

## Phase 5a Implementation (This Session)

### 1. Create Assertion Checker

```python
# lift_sys/validation/assertion_checker.py

from dataclasses import dataclass
from typing import Any

@dataclass
class ValidationIssue:
    """An issue found during validation."""
    severity: str  # 'error', 'warning'
    message: str
    location: str | None = None

@dataclass
class ValidationResult:
    """Result of validating code against IR."""
    passed: bool
    issues: list[ValidationIssue]

class AssertionChecker:
    """Validates generated code against IR assertions."""

    def validate(
        self,
        code: str,
        function_name: str,
        ir: IntermediateRepresentation
    ) -> ValidationResult:
        """
        Validate generated code satisfies IR assertions.

        Strategy:
        1. Parse assertions from IR
        2. Generate test inputs covering edge cases
        3. Execute code with inputs
        4. Check outputs match assertions
        """
        issues = []

        # Extract function
        namespace = {}
        exec(code, namespace)
        func = namespace.get(function_name)

        if not func:
            issues.append(ValidationIssue(
                severity='error',
                message=f"Function '{function_name}' not found"
            ))
            return ValidationResult(passed=False, issues=issues)

        # Generate test cases from IR
        test_cases = self._generate_test_cases_from_ir(ir)

        # Validate each test case
        for test_input, expected_property in test_cases:
            try:
                actual = func(*test_input)
                if not self._check_property(actual, expected_property):
                    issues.append(ValidationIssue(
                        severity='error',
                        message=f"Assertion failed for input {test_input}: "
                                f"expected {expected_property}, got {actual}"
                    ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity='error',
                    message=f"Execution failed for input {test_input}: {e}"
                ))

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues
        )
```

### 2. Integration Point

```python
# In XGrammarCodeGenerator.generate()

# After AST repair, before returning:
if self.assertion_checker:
    validation = self.assertion_checker.validate(
        code=repaired_code,
        function_name=ir.signature.name,
        ir=ir
    )

    if not validation.passed:
        # Log issues
        for issue in validation.issues:
            print(f"  ⚠️  Validation: {issue.message}")

        # Could trigger retry or refinement here
```

### 3. Test Cases from IR

For get_type_name IR:
```
Intent: "Check the type of a value and return its name"
Assertions:
- Returns 'int' for integers
- Returns 'str' for strings
- Returns 'list' for lists
- Returns 'other' for anything else

Generated test cases:
- (42,) → should return 'int'
- ("hello",) → should return 'str'
- ([1,2,3],) → should return 'list'
- (3.14,) → should return 'other'  # EDGE CASE
- (None,) → should return 'other'
- ({"key": "val"},) → should return 'other'
```

**Result**: Catches missing edge cases!

---

## Expected Impact

### Phase 5a (Assertion Checker)

**Catches**:
- Missing edge cases (get_type_name with float)
- Wrong return values for inputs
- Incomplete conditional coverage

**Expected**:
- Fix get_type_name: ❌ → ✅
- Success rate: 90% → 100% (10/10)

### Future Phases

**Phase 5b** (Control Flow):
- Validate all paths covered
- Check loop termination
- Verify error handling

**Phase 5c** (Full Abstract Interpreter):
- Complete semantic validation
- Symbolic execution
- Property-based testing

---

## Timeline

**Phase 5a**: 2-3 hours
- Create AssertionChecker class
- Implement test case generation from IR
- Integrate with code generation
- Write unit tests
- Verify fixes get_type_name

**Phase 5b**: 1-2 days (future)
**Phase 5c**: 3-5 days (future)

---

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| **get_type_name** | ✅ PASS | Run Phase 2 tests |
| **Success Rate** | 95-100% | 9/10 → 10/10 |
| **No Regressions** | 0 | All passing stay passing |
| **Implementation** | <300 lines | assertion_checker.py |

---

## Next Steps

1. ✅ Design complete
2. → Implement AssertionChecker class
3. → Write unit tests
4. → Integrate with XGrammarCodeGenerator
5. → Run Phase 2 verification
6. → Document results

---

**Phase 5a starts now!** 🚀
