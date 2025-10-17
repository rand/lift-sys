# Phase 6: Code Generation Quality Improvements

**Goal**: Fix the 3 persistent Phase 3 failures by improving code generation quality (IR → Python translation)

**Target**: 18/18 tests passing (100%)

**Current**: 15/18 tests passing (83.3%)

## Problem Statement

Phase 5 identified that the 3 persistent failures are **code generation bugs**, not IR semantic errors:

1. **count_words**: Code generator fails to emit return statement
   - IR says: "Return the count"
   - Generated code: Returns `None` instead of count value

2. **find_index**: Code generator returns last match instead of first
   - IR says: "Return immediately when found"
   - Generated code: Continues loop, returns last match

3. **is_valid_email**: Code generator accepts invalid email format
   - IR says: "Check that dot comes after @"
   - Generated code: Doesn't check dot position

**Root cause**: XGrammar-constrained generation produces syntactically valid but semantically incorrect Python code.

## Solution: Execution-Based Validation with Regeneration

### Approach

Add a **validation-regeneration loop** to code generation:

```
1. Generate code from IR (current XGrammar approach)
2. Generate test cases from IR (NEW)
3. Execute code with test cases (NEW)
4. If tests fail, regenerate with failure feedback (NEW)
5. Repeat up to N times or until tests pass
```

### Architecture

```
┌─────────────┐
│     IR      │
└──────┬──────┘
       │
       ├─────────────────┐
       │                 │
       v                 v
┌──────────────┐   ┌──────────────┐
│ Code         │   │ Test Case    │
│ Generator    │   │ Generator    │
│ (XGrammar)   │   │ (from IR)    │
└──────┬───────┘   └──────┬───────┘
       │                  │
       v                  v
┌─────────────────────────────┐
│  Execution Validator        │
│  - Run code with tests      │
│  - Capture results          │
│  - Compare with expected    │
└──────┬──────────────────────┘
       │
       ├─ Pass → Return code
       │
       └─ Fail → Regenerate with feedback
                  ↑__________________|
```

## Implementation Plan

### Step 1: Test Case Generator (2-3 hours)

**File**: `lift_sys/codegen/test_generator.py`

Generate test cases from IR components:

```python
class TestCaseGenerator:
    """Generate test cases from IR for validation."""

    def generate_test_cases(self, ir: IntermediateRepresentation) -> list[TestCase]:
        """
        Generate test cases from IR assertions and effects.

        Sources:
        1. IR assertions → expected behavior
        2. Effect descriptions → test scenarios
        3. Parameter types → valid/invalid inputs
        4. Edge cases from signature (empty, None, etc.)
        """

@dataclass
class TestCase:
    inputs: dict[str, Any]
    expected_output: Any | None
    should_raise: type[Exception] | None
    description: str
```

**Test case generation strategies**:

1. **From assertions**:
   - "count is >= 0" → test with empty string, expect 0
   - "index is valid or -1" → test not found case, expect -1

2. **From effects**:
   - "Split by spaces" → test "hello world", expect 2 words
   - "Return immediately when found" → test duplicate values, verify returns first

3. **Edge cases**:
   - Empty collections
   - None values
   - Boundary conditions

### Step 2: Execution Validator (2-3 hours)

**File**: `lift_sys/codegen/execution_validator.py`

Execute generated code and validate results:

```python
class ExecutionValidator:
    """Execute generated code with test cases and validate results."""

    def validate(
        self,
        code: str,
        function_name: str,
        test_cases: list[TestCase]
    ) -> ValidationResult:
        """
        Execute code with test cases.

        Returns:
        - passed: bool
        - failed_tests: list[FailedTest]
        - error_message: str (for feedback)
        """

@dataclass
class ValidationResult:
    passed: bool
    failed_tests: list[FailedTest]
    error_message: str | None  # For regeneration feedback
```

**Execution safety**:
- Use `exec()` with restricted globals
- Timeout after 1 second per test
- Catch all exceptions
- Sandbox environment (no file I/O, network)

### Step 3: Validation-Guided Code Generator (3-4 hours)

**File**: `lift_sys/codegen/validated_generator.py`

Wrapper around XGrammarCodeGenerator with validation loop:

```python
class ValidatedCodeGenerator:
    """Code generator with execution-based validation."""

    def __init__(
        self,
        base_generator: XGrammarCodeGenerator,
        test_generator: TestCaseGenerator,
        validator: ExecutionValidator,
        max_attempts: int = 3
    ):
        """Initialize with base generator and validation components."""

    def generate(self, ir: IntermediateRepresentation) -> GeneratedCode:
        """
        Generate code with validation loop.

        Algorithm:
        1. Generate test cases from IR
        2. For attempt in 1..max_attempts:
           a. Generate code (use temperature > 0 for diversity)
           b. Validate with test cases
           c. If pass: return code
           d. If fail: regenerate with error feedback
        3. If all attempts fail: return best attempt with warnings
        """
```

**Regeneration with feedback**:

When code fails tests, inject failure information into next generation:

```python
# Add to IR metadata or prompt
feedback = f"""
Previous attempt failed tests:
- Test: {test.description}
  Input: {test.inputs}
  Expected: {test.expected}
  Got: {actual}
  Error: {error_message}

Common issues to avoid:
- Missing return statement
- Returning from wrong scope
- Not breaking loop early
"""
```

### Step 4: Integration with Pipeline (1 hour)

Modify `XGrammarIRTranslator` or create new translator:

```python
# In forward_mode/xgrammar_translator.py
class ValidatedXGrammarIRTranslator(XGrammarIRTranslator):
    """IR translator with validated code generation."""

    def __init__(self, provider: BaseProvider, **kwargs):
        super().__init__(provider, **kwargs)

        # Wrap code generator with validation
        self.code_generator = ValidatedCodeGenerator(
            base_generator=self.code_generator,
            test_generator=TestCaseGenerator(),
            validator=ExecutionValidator(),
            max_attempts=3
        )
```

## Expected Impact

### Success Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Phase 3 pass rate | 83.3% (15/18) | 100% (18/18) | +16.7% |
| count_words | ❌ Fail | ✅ Pass | Fixed |
| find_index | ❌ Fail | ✅ Pass | Fixed |
| is_valid_email | ❌ Fail | ✅ Pass | Fixed |

### How It Fixes Each Bug

**1. count_words (missing return)**:
- Test case: `count_words("hello world")` → expect `2`
- Generated code returns `None` → test fails
- Error feedback: "Expected 2, got None - missing return statement?"
- Regeneration with feedback → adds return statement → passes

**2. find_index (returns last instead of first)**:
- Test case: `find_index([1, 2, 1], 1)` → expect `0`
- Generated code returns `2` (last occurrence)
- Error feedback: "Expected 0, got 2 - not breaking loop early?"
- Regeneration with feedback → adds break/immediate return → passes

**3. is_valid_email (invalid validation)**:
- Test case: `is_valid_email("test@.com")` → expect `False`
- Generated code returns `True` (doesn't check dot position)
- Error feedback: "Expected False, got True - dot position not validated?"
- Regeneration with feedback → adds position check → passes

## Timeline

### Week 1: Core Implementation (8-10 hours)
- Day 1-2: Test case generator (2-3h)
- Day 2-3: Execution validator (2-3h)
- Day 3-4: Validated code generator (3-4h)
- Day 4-5: Integration and testing (1h)

### Week 2: Testing and Refinement (4-6 hours)
- Test on 3 persistent failures
- Test on full Phase 3 suite
- Optimize regeneration prompts
- Add more test case patterns

**Total estimated time**: 12-16 hours

## Technical Considerations

### 1. Test Case Quality
**Challenge**: Auto-generated tests might not catch all bugs

**Solutions**:
- Generate diverse test cases (edge cases, typical cases, invalid inputs)
- Use IR assertions as oracle
- Add common edge cases (empty, None, boundary)
- Learn from failures (add new test patterns)

### 2. Execution Safety
**Challenge**: Executing untrusted code is risky

**Solutions**:
- Restricted `exec()` environment (no imports, limited builtins)
- Timeout per test (1 second)
- Resource limits (no infinite loops, large allocations)
- Consider `RestrictedPython` library for production

### 3. Regeneration Cost
**Challenge**: Multiple generation attempts increase latency and cost

**Solutions**:
- Limit max attempts (3 is good balance)
- Use temperature > 0 for diversity (0.3-0.5)
- Cache working code for similar IRs
- Only regenerate if tests fail (most will pass on first try)

**Cost impact**:
- Baseline: 1x generation cost
- With validation (3 attempts max): ~1.5-2x (most pass on attempt 1-2)
- Worth it for 100% success rate

### 4. False Positives
**Challenge**: Tests might pass but code is still wrong

**Solutions**:
- Generate comprehensive test cases
- Use IR assertions as strong oracle
- Add negative tests (should fail)
- Combine with Phase 5 IR validation (already done)

## Alternative Approaches (Considered)

### 1. Improve XGrammar Grammars
**Pros**: Lower latency, deterministic
**Cons**: Hard to encode complex logic rules, doesn't fix semantic bugs

### 2. Few-Shot Examples
**Pros**: Simple, works well for LLMs
**Cons**: Limited by context size, doesn't adapt to failures

### 3. Formal Verification
**Pros**: Provably correct
**Cons**: Too complex, slow, overkill for simple functions

**Decision**: Execution-based validation is best balance of effectiveness and complexity

## Success Criteria

Phase 6 is complete when:
1. ✅ Test case generator implemented and tested
2. ✅ Execution validator implemented and tested
3. ✅ Validated code generator implemented and tested
4. ✅ Integration with pipeline complete
5. ✅ **count_words test passes**
6. ✅ **find_index test passes**
7. ✅ **is_valid_email test passes**
8. ✅ Phase 3 full suite: 18/18 passing (100%)

## Next Steps After Phase 6

If successful (18/18 passing):
1. **Scale testing**: Run on larger test suites (50-100 functions)
2. **Optimize**: Reduce regeneration cost, improve test quality
3. **Production**: Deploy to real workloads
4. **Metrics**: Track success rate, regeneration frequency, latency

If partially successful (16-17/18):
1. **Analyze remaining failures**: Different bug types?
2. **Improve test generation**: More patterns, better coverage
3. **Add more feedback**: Better error messages for regeneration

---

**Phase 6 Status**: 📋 PLANNED

**Next Action**: Implement test case generator
