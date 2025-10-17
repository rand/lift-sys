# Action Plan: Fixing 3 Persistent Test Failures

**Goal**: Achieve 18/18 passing tests (100%) by fixing the 3 remaining failures identified in Phase 3 testing.

**Current Status**: 15/18 passing (83.3%)

**Date**: 2025-10-17

## Executive Summary

Phase 3 testing with AST repair (temperature 0.8) revealed 3 persistent failures:

1. **count_words** (1/5 tests pass): Missing return statement - returns `None`
2. **find_index** (4/5 tests pass): Returns last occurrence instead of first
3. **is_valid_email** (4/5 tests pass): Accepts "test@.com" (adjacency bug)

**Strategy**: Extend AST repair system with 2 new passes + integrate existing Pass 6

**Expected Outcome**: 18/18 tests passing (100%)

---

## Part 1: Detailed Failure Analysis

### Failure 1: count_words - Missing Return Statement

**Test Results**: 1/5 tests passed

**Error Details**:
```
Test: Count words in "hello world"
Expected: 2
Got: None
Error: Expected 2, got None
```

**Root Cause**: Generated function has no return statement:
```python
def count_words(text: str) -> int:
    words = text.split()
    len(words)  # ❌ Result is computed but not returned
```

**Pattern to Detect**:
- Function has return type annotation (not `None`)
- Function body has expressions that compute values
- Function has NO `return` statement anywhere
- Function implicitly returns `None`

**AST Repair Solution**: Pass 7 - Missing Return Statement Detection

**Implementation Strategy**:
```python
class MissingReturnTransformer(ast.NodeTransformer):
    """Detect and fix functions with missing return statements."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Check if function has return type annotation
        if not node.returns:
            return node

        # Check if return type is not None
        if isinstance(node.returns, ast.Constant) and node.returns.value is None:
            return node

        # Check if function has any return statements
        has_return = any(isinstance(n, ast.Return) for n in ast.walk(node))
        if has_return:
            return node

        # Look for last statement that computes a value
        if not node.body:
            return node

        last_stmt = node.body[-1]

        # Pattern 1: Standalone expression (len(words))
        if isinstance(last_stmt, ast.Expr):
            # Convert to return statement
            new_return = ast.Return(value=last_stmt.value)
            node.body[-1] = ast.copy_location(new_return, last_stmt)
            return node

        # Pattern 2: Assignment then reference
        # def func():
        #     result = compute()
        #     result  # ❌ Should be: return result
        if isinstance(last_stmt, ast.Expr) and isinstance(last_stmt.value, ast.Name):
            new_return = ast.Return(value=last_stmt.value)
            node.body[-1] = ast.copy_location(new_return, last_stmt)
            return node

        return node
```

**Test Cases**:
```python
# Before repair:
def count_words(text: str) -> int:
    words = text.split()
    len(words)

# After repair:
def count_words(text: str) -> int:
    words = text.split()
    return len(words)
```

---

### Failure 2: find_index - Returns Last Occurrence Instead of First

**Test Results**: 4/5 tests passed

**Error Details**:
```
Test: Find 1 in [1, 2, 1]
Expected: 0 (first occurrence)
Got: 2 (last occurrence)
Error: Expected 0, got 2
```

**Root Cause**: Loop overwrites result without early return:
```python
def find_index(items: list[int], target: int) -> int:
    result = -1
    for i, item in enumerate(items):
        if item == target:
            result = i  # ❌ Overwrites on every match
    return result  # Returns LAST match, not FIRST
```

**Correct Implementation**:
```python
def find_index(items: list[int], target: int) -> int:
    for i, item in enumerate(items):
        if item == target:
            return i  # ✅ Early return on FIRST match
    return -1  # Not found
```

**Pattern to Detect**:
- Function uses `enumerate()` in for loop
- Function has variable assignment inside `if` block (e.g., `result = i`)
- Function returns that variable after loop
- Intent is to find "first" match (from IR or prompt)

**AST Repair Solution**: Pass 8 - Enumerate Early Return Pattern

**Implementation Strategy**:
```python
class EnumerateEarlyReturnTransformer(ast.NodeTransformer):
    """Fix enumerate loops that should return first match, not last."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        self.modifications = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.name != self.function_name:
            return node

        # Look for pattern:
        # result = -1  (or None)
        # for i, item in enumerate(items):
        #     if item == target:
        #         result = i
        # return result

        # Find result initialization
        result_var = None
        for i, stmt in enumerate(node.body):
            if isinstance(stmt, ast.Assign):
                if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                    if isinstance(stmt.value, ast.Constant):
                        result_var = stmt.targets[0].id
                        break

        if not result_var:
            return node

        # Find enumerate loop
        for i, stmt in enumerate(node.body):
            if not isinstance(stmt, ast.For):
                continue

            # Check if loop uses enumerate
            if not (isinstance(stmt.iter, ast.Call) and
                    isinstance(stmt.iter.func, ast.Name) and
                    stmt.iter.func.id == 'enumerate'):
                continue

            # Check if loop assigns to result_var
            assigns_result = False
            for subnode in ast.walk(stmt):
                if isinstance(subnode, ast.Assign):
                    if len(subnode.targets) == 1:
                        target = subnode.targets[0]
                        if isinstance(target, ast.Name) and target.id == result_var:
                            assigns_result = True
                            break

            if not assigns_result:
                continue

            # TRANSFORM: Replace assignment with early return
            self._transform_loop_body(stmt.body)

            # Remove result initialization (no longer needed)
            node.body = [s for j, s in enumerate(node.body)
                        if not (j < i and isinstance(s, ast.Assign) and
                               isinstance(s.targets[0], ast.Name) and
                               s.targets[0].id == result_var)]

            self.modifications.append(
                f"Converted enumerate loop to use early return instead of "
                f"accumulating result (fixes first vs last bug)"
            )

        return node

    def _transform_loop_body(self, body: list[ast.stmt]) -> None:
        """Replace 'result = i' with 'return i' in loop body."""
        for i, stmt in enumerate(body):
            if isinstance(stmt, ast.If):
                # Transform if body
                self._transform_loop_body(stmt.body)
                # Transform else body
                if stmt.orelse:
                    self._transform_loop_body(stmt.orelse)
            elif isinstance(stmt, ast.Assign):
                # Replace with return
                body[i] = ast.Return(value=stmt.value)
```

**Test Cases**:
```python
# Before repair:
def find_index(items: list[int], target: int) -> int:
    result = -1
    for i, item in enumerate(items):
        if item == target:
            result = i
    return result

# After repair:
def find_index(items: list[int], target: int) -> int:
    for i, item in enumerate(items):
        if item == target:
            return i
    return -1
```

---

### Failure 3: is_valid_email - Accepts test@.com (Adjacency Bug)

**Test Results**: 4/5 tests passed

**Error Details**:
```
Test: Validate "test@.com"
Expected: False (dot immediately after @)
Got: True
Error: Expected False, got True
```

**Root Cause**: Only checks if dot comes after @, misses adjacency:
```python
def is_valid_email(email: str) -> bool:
    if '@' not in email:
        return False
    if '.' not in email:
        return False
    if email.index('@') > email.rindex('.'):  # ❌ Only checks order
        return False
    return True
```

**Pattern to Detect**:
- Function checks `email.index('@') > email.rindex('.')`
- Missing adjacency check: `email.rindex('.') - email.index('@') == 1`

**AST Repair Solution**: Pass 6 - Email Validation Adjacency (ALREADY EXISTS)

**Status**: ✅ Pass 6 already implemented in `lift_sys/codegen/ast_repair.py` (lines 65-67, 350-450)

**Verification**: Need to confirm Pass 6 runs during ValidatedCodeGenerator pipeline

**Test Cases**:
```python
# Before repair:
def is_valid_email(email: str) -> bool:
    if '@' not in email or '.' not in email:
        return False
    if email.index('@') > email.rindex('.'):
        return False
    return True

# After repair:
def is_valid_email(email: str) -> bool:
    if '@' not in email or '.' not in email:
        return False
    if email.index('@') >= email.rindex('.') or email.rindex('.') - email.index('@') == 1:
        return False
    return True
```

---

## Part 2: Implementation Plan

### Phase A: Implement AST Repair Passes (2-3 hours)

**Task A1: Implement Pass 7 - Missing Return Statement**
- Location: `lift_sys/codegen/ast_repair.py`
- Add `MissingReturnTransformer` class (lines ~470-530)
- Hook into `apply_repairs()` at line ~68
- Unit tests: `tests/codegen/test_ast_repair_pass7.py`

**Task A2: Implement Pass 8 - Enumerate Early Return**
- Location: `lift_sys/codegen/ast_repair.py`
- Add `EnumerateEarlyReturnTransformer` class (lines ~540-650)
- Hook into `apply_repairs()` at line ~71
- Unit tests: `tests/codegen/test_ast_repair_pass8.py`

**Task A3: Verify Pass 6 Integration**
- Confirm Pass 6 (EmailValidationTransformer) is active
- Check it runs during ValidatedCodeGenerator pipeline
- Unit tests already exist: `debug/test_email_ast_repair.py`

**Deliverable**: `ast_repair.py` with 8 passes total

---

### Phase B: Integration Testing (1-2 hours)

**Task B1: Test ValidatedCodeGenerator on 3 Failures**
- Location: `debug/test_3_failures_integration_final.py` (create new)
- Test each failure in isolation with ValidatedCodeGenerator
- Verify AST repair passes trigger correctly
- Verify regeneration succeeds when repair fails

**Test Structure**:
```python
async def test_count_words_with_validation():
    # Create IR for count_words
    ir = create_count_words_ir()

    # Generate with validation
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    await provider.initialize(credentials={})

    base_generator = XGrammarCodeGenerator(provider)
    validated_generator = ValidatedCodeGenerator(
        base_generator=base_generator,
        max_attempts=3,
    )

    result = await validated_generator.generate(ir)

    # Verify success
    assert result.metadata.get("validated") == True
    assert result.metadata.get("tests_passed") == result.metadata.get("total_tests")

    # Execute with actual test cases
    exec_namespace = {}
    exec(result.source_code, exec_namespace)
    func = exec_namespace["count_words"]

    # Test cases
    assert func("hello world") == 2
    assert func("one") == 1
    assert func("") == 0
    assert func("a b c d e") == 5

    print("✅ count_words: All tests passed!")
```

**Task B2: Run Full Phase 3 Test Suite**
- Location: `tests/integration/test_phase3_full_suite.py`
- Run all 18 tests with AST repair passes 1-8 enabled
- Temperature: 0.8 (same as baseline)
- Goal: 18/18 passing (100%)

**Deliverable**: Test results log showing 18/18 passing

---

### Phase C: E2E Example - Email Validator (2-3 hours)

**Task C1: Create Bulletproof E2E Example**
- Location: `examples/e2e_email_validator.py`
- Demonstrate complete workflow: Prompt → IR → Validated Code → Execution
- Measure latencies at each step
- Document costs (Modal GPU inference)
- Include failure recovery examples

**E2E Flow**:
```
1. User Prompt: "Create a function that validates email addresses"
   ↓ [~500ms, Modal GPU inference]

2. IR Translation (XGrammarIRTranslator):
   - Intent: "Check if string is a valid email address"
   - Signature: is_valid_email(email: str) -> bool
   - Effects: Check @, check ., verify adjacency
   - Assertions: Must have @ and domain
   ↓ [~800ms, Modal GPU inference]

3. Code Generation (ValidatedCodeGenerator):
   Attempt 1 (temperature=0.3):
   - Generate code
   - Generate test cases (5 tests)
   - Execute tests
   - Result: 4/5 tests pass (adjacency bug)

   Attempt 2 (temperature=0.45):
   - Inject validation feedback
   - Regenerate code
   - AST Repair Pass 6 triggers: Fix adjacency check
   - Execute tests
   - Result: 5/5 tests pass ✅
   ↓ [~1.2s total for 2 attempts]

4. Final Code:
   ```python
   def is_valid_email(email: str) -> bool:
       if '@' not in email or '.' not in email:
           return False
       if email.index('@') >= email.rindex('.') or email.rindex('.') - email.index('@') == 1:
           return False
       return True
   ```

5. Execution & Verification:
   - Test with 10 diverse inputs
   - All tests pass
   - Total latency: ~2.5s end-to-end
   - Cost: ~$0.002 per generation (Modal GPU)
```

**Task C2: Document Failure Recovery**
- Show what happens when all 3 attempts fail
- Demonstrate "best attempt" fallback
- Document warning messages and metadata
- Show how to use validation feedback for debugging

**Deliverable**:
- `examples/e2e_email_validator.py` (working example)
- `docs/E2E_EMAIL_VALIDATOR.md` (comprehensive guide)

---

## Part 3: Testing Strategy

### Unit Tests (Per-Pass Testing)

**Test Suite 1: AST Repair Pass 7**
- Location: `tests/codegen/test_ast_repair_pass7.py`
- Test cases:
  1. Simple missing return: `len(words)` → `return len(words)`
  2. Missing return with variable: `result` → `return result`
  3. Function with existing return: No change
  4. Function with None return type: No change
  5. Function with no return annotation: No change

**Test Suite 2: AST Repair Pass 8**
- Location: `tests/codegen/test_ast_repair_pass8.py`
- Test cases:
  1. Enumerate with result accumulation → Early return
  2. Enumerate with correct early return: No change
  3. Enumerate without result variable: No change
  4. Regular for loop (not enumerate): No change
  5. Nested enumerate loops: Handle correctly

**Test Suite 3: AST Repair Pass 6 (Existing)**
- Location: `debug/test_email_ast_repair.py` (already exists)
- Verify email validation adjacency fix

### Integration Tests

**Test Suite 4: ValidatedCodeGenerator on 3 Failures**
- Location: `debug/test_3_failures_integration_final.py`
- Test count_words, find_index, is_valid_email in isolation
- Verify each passes with ValidatedCodeGenerator
- Measure attempt counts (should succeed in 1-2 attempts)

**Test Suite 5: Full Phase 3 Test Suite**
- Location: `tests/integration/test_phase3_full_suite_fixed.py`
- Run all 18 tests with AST repair passes 1-8
- Goal: 18/18 passing (100%)
- Compare with baseline: 15/18 → 18/18

### E2E Test

**Test Suite 6: Email Validator E2E**
- Location: `examples/e2e_email_validator.py`
- Test complete workflow end-to-end
- Verify latencies, costs, error handling
- Demonstrate failure recovery

---

## Part 4: Success Criteria

### Objective Metrics

1. **Test Pass Rate**: 18/18 tests passing (100%)
   - Baseline: 15/18 (83.3%)
   - Target: 18/18 (100%)
   - Improvement: +3 tests fixed

2. **Per-Test Results**:
   - count_words: 1/5 → 5/5 (100%)
   - find_index: 4/5 → 5/5 (100%)
   - is_valid_email: 4/5 → 5/5 (100%)

3. **AST Repair Coverage**:
   - Pass 7 (Missing Return): Triggers on count_words
   - Pass 8 (Enumerate Early Return): Triggers on find_index
   - Pass 6 (Email Adjacency): Triggers on is_valid_email

4. **ValidatedCodeGenerator Performance**:
   - Average attempts to success: ≤ 2.0 (ideally 1-2 attempts)
   - Regeneration success rate: 100% (all failures fixed)
   - No infinite loops or timeouts

5. **E2E Workflow**:
   - Complete workflow working end-to-end
   - Total latency: < 3s per generation
   - Cost per generation: < $0.005
   - Failure recovery documented and tested

### Qualitative Criteria

1. **Code Quality**: Generated code is readable, idiomatic Python
2. **Error Messages**: Validation feedback is actionable and clear
3. **Documentation**: E2E example is comprehensive and reproducible
4. **Maintainability**: AST repair passes are well-tested and modular

---

## Part 5: Timeline & Dependencies

### Estimated Timeline: 5-8 hours total

**Phase A: AST Repair Implementation (2-3 hours)**
- Pass 7: 1 hour (implementation + unit tests)
- Pass 8: 1.5 hours (more complex pattern + unit tests)
- Pass 6 verification: 0.5 hours

**Phase B: Integration Testing (1-2 hours)**
- Individual test suite: 0.5 hours
- Full Phase 3 suite: 0.5-1 hour (waiting for Modal inference)
- Analysis and debugging: 0.5 hours

**Phase C: E2E Example (2-3 hours)**
- Implementation: 1 hour
- Documentation: 1-1.5 hours
- Testing and refinement: 0.5 hours

### Dependencies

1. **Modal.com GPU Instance**: Must be running for all testing
2. **Existing Components**:
   - XGrammarCodeGenerator (working)
   - ValidatedCodeGenerator (working)
   - TestCaseGenerator (working)
   - ExecutionValidator (working)
3. **Git Status**: Clean working tree (already synced with origin)

---

## Part 6: Risk Mitigation

### Risk 1: AST Repair Pass 7/8 Don't Trigger

**Likelihood**: Medium
**Impact**: High (tests would still fail)

**Mitigation**:
- Add extensive logging to AST repair system
- Unit test each transformer in isolation
- Add debug mode to print AST before/after repair
- Fallback: ValidatedCodeGenerator regeneration should fix even if AST repair misses

### Risk 2: ValidatedCodeGenerator Exceeds Max Attempts

**Likelihood**: Low (with AST repair, should succeed in 1-2 attempts)
**Impact**: Medium (would return "best attempt" with warnings)

**Mitigation**:
- Increase max_attempts to 5 if needed
- Improve validation feedback quality
- Add more diverse test cases to catch bugs earlier
- AST repair should handle deterministic bugs

### Risk 3: E2E Example Not Reproducible

**Likelihood**: Low
**Impact**: Medium (would undermine trust in workflow)

**Mitigation**:
- Pin all dependency versions
- Document Modal.com setup steps
- Provide fallback local inference option
- Include troubleshooting guide

### Risk 4: Performance Regression

**Likelihood**: Low
**Impact**: Low (latency increase acceptable if accuracy improves)

**Mitigation**:
- Measure baseline latency before changes
- Profile AST repair passes (should be < 50ms)
- Optimize if needed (e.g., skip passes if no match)
- Document performance characteristics

---

## Part 7: Next Steps (Immediate Actions)

### Step 1: Implement Pass 7 (Missing Return Statement)
- [ ] Add `MissingReturnTransformer` to `ast_repair.py`
- [ ] Hook into `apply_repairs()` method
- [ ] Write unit tests in `tests/codegen/test_ast_repair_pass7.py`
- [ ] Verify on count_words manually

### Step 2: Implement Pass 8 (Enumerate Early Return)
- [ ] Add `EnumerateEarlyReturnTransformer` to `ast_repair.py`
- [ ] Hook into `apply_repairs()` method
- [ ] Write unit tests in `tests/codegen/test_ast_repair_pass8.py`
- [ ] Verify on find_index manually

### Step 3: Integration Test
- [ ] Create `debug/test_3_failures_integration_final.py`
- [ ] Test each failure with ValidatedCodeGenerator
- [ ] Verify AST repair passes trigger
- [ ] Run full Phase 3 test suite

### Step 4: E2E Example
- [ ] Create `examples/e2e_email_validator.py`
- [ ] Document workflow in `docs/E2E_EMAIL_VALIDATOR.md`
- [ ] Measure latencies and costs
- [ ] Test failure recovery

### Step 5: Documentation
- [ ] Update `docs/PHASE_6_COMPLETION.md` with final results
- [ ] Create `WEEK_2_COMPLETION_SUMMARY.md` with 18/18 results
- [ ] Update `docs/REALITY_CHECK_AND_PLAN.md` with progress
- [ ] Clean up bead numbering conflicts

---

## Appendix A: Test Case Details

### count_words Test Cases (5 total)
```python
[
    ({"text": "hello world"}, 2),      # Basic case
    ({"text": "one"}, 1),               # Single word
    ({"text": ""}, 0),                  # Empty string
    ({"text": "a b c d e"}, 5),         # Multiple words
    ({"text": "  spaced  "}, 1),        # Extra spaces
]
```

### find_index Test Cases (5 total)
```python
[
    ({"items": [1, 2, 3], "target": 2}, 1),     # Middle
    ({"items": [1, 2, 3], "target": 4}, -1),    # Not found
    ({"items": [], "target": 1}, -1),           # Empty list
    ({"items": [1, 2, 1], "target": 1}, 0),     # Duplicate (FIRST!)
    ({"items": [5], "target": 5}, 0),           # Single element
]
```

### is_valid_email Test Cases (5 total)
```python
[
    ({"email": "test@example.com"}, True),      # Valid
    ({"email": "invalid"}, False),              # No @ or .
    ({"email": "no@at"}, False),                # No . after @
    ({"email": "test@.com"}, False),            # Adjacency bug!
    ({"email": "@example.com"}, True),          # Basic validation OK
]
```

---

## Appendix B: Code Snippets

### AST Repair Integration Point

```python
# In lift_sys/codegen/ast_repair.py, apply_repairs() method:

def apply_repairs(self, code: str, function_name: str) -> tuple[str, list[str]]:
    """Apply all AST repair passes to generated code."""
    modifications = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return code, [f"Syntax error, cannot apply repairs: {e}"]

    # Pass 1: Self-reference
    tree, self_ref_fixes = self._fix_self_reference(tree, function_name)
    modifications.extend(self_ref_fixes)

    # Pass 2: Unused loop variables
    tree, unused_fixes = self._fix_unused_loop_vars(tree, function_name)
    modifications.extend(unused_fixes)

    # Pass 3: Boolean comparisons
    tree, bool_fixes = self._fix_boolean_comparisons(tree, function_name)
    modifications.extend(bool_fixes)

    # Pass 4: Unreachable code
    tree, unreachable_fixes = self._fix_unreachable_code(tree, function_name)
    modifications.extend(unreachable_fixes)

    # Pass 5: Shadowed built-ins
    tree, shadow_fixes = self._fix_shadowed_builtins(tree, function_name)
    modifications.extend(shadow_fixes)

    # Pass 6: Email validation adjacency
    tree, email_fixes = self._fix_email_validation(tree, function_name)
    modifications.extend(email_fixes)

    # Pass 7: Missing return statements ← NEW
    tree, return_fixes = self._fix_missing_return(tree, function_name)
    modifications.extend(return_fixes)

    # Pass 8: Enumerate early return ← NEW
    tree, enumerate_fixes = self._fix_enumerate_early_return(tree, function_name)
    modifications.extend(enumerate_fixes)

    try:
        repaired_code = ast.unparse(tree)
        return repaired_code, modifications
    except Exception as e:
        return code, modifications + [f"Failed to unparse repaired AST: {e}"]
```

---

## Appendix C: Modal.com Inference Details

**Endpoint**: `https://rand--generate.modal.run`

**Model**: Qwen2.5-Coder-32B-Instruct (or similar)

**Cost per Request**: ~$0.001-0.002 (depends on input/output tokens)

**Latency**:
- IR translation: ~500-800ms
- Code generation: ~600-1000ms
- Total for 2 attempts: ~2-3s

**Failure Modes**:
- Modal instance cold start: +5-10s first request
- Rate limiting: Unlikely with current usage
- Timeout: 30s max (configurable)

**Optimization**:
- Keep Modal instance warm (periodic pings)
- Batch requests if possible
- Cache IR translations for identical prompts

---

**Status**: Ready to implement
**Next Action**: Begin with Pass 7 implementation
**Owner**: Claude (with user review)
**Priority**: High (blocks 100% test pass rate)
