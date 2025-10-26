# TypeScript Edge Case Test Summary

**Date**: 2025-10-23
**Status**: Tests Implemented (Not Yet Executed)
**File**: `tests/integration/test_typescript_edge_cases.py`

## Overview

Added 11 comprehensive edge case tests for the TypeScript generator to identify weaknesses before production deployment. These tests target challenging scenarios that basic tests miss: recursion, generics, complex types, error handling, and async edge cases.

## Test Coverage Matrix

| Category | Test Name | Focus Area | Expected Weakness |
|----------|-----------|------------|-------------------|
| **Recursion** | test_recursive_factorial | Base case, recursive calls, stack safety | Missing base case validation |
| **Recursion** | test_recursive_tree_traversal | Nested objects, null handling | Incomplete null checks |
| **Generics** | test_generic_array_function | Type parameter T, Array<T> | Generic type erasure (T → any) |
| **Generics** | test_generic_promise_function | Promise<T> wrapping | Async detection failures |
| **Complex Types** | test_union_type_handling | Union types (string \| number) | Missing type narrowing/guards |
| **Complex Types** | test_optional_chaining | ?. operator, null-safe access | Missing ?. operator usage |
| **Complex Types** | test_type_guard_discriminated_union | Discriminated unions | Complex type narrowing failures |
| **Error Scenarios** | test_null_undefined_edge_cases | null vs undefined, ?? operator | null/undefined confusion |
| **Error Scenarios** | test_array_bounds_checking | Index validation, bounds checks | Missing validation logic |
| **Async Edge Cases** | test_async_error_propagation | Try/catch in async, rethrowing | Missing error handling |
| **Async Edge Cases** | test_promise_chaining | Multiple awaits, dependencies | Incorrect async sequencing |

## Detailed Test Descriptions

### Recursion Tests

#### test_recursive_factorial
**Scenario**: Generate recursive factorial function (n!)

**IR Specification**:
```python
intent: "Calculate factorial recursively"
signature: factorial(n: int) -> int
effects:
  - "Recurses until base case (n <= 1)"
  - "Returns n * factorial(n-1)"
assertions:
  - "n >= 0" (no negative factorials)
  - "result >= 1" (factorial always positive)
```

**Expected Challenges**:
- Generator must identify need for base case (n <= 1)
- Recursive call must be properly typed
- Stack overflow prevention via constraints

**Predicted Failure Mode**: Missing base case condition → infinite recursion

**Validation Checks**:
- ✓ Contains base case condition (if statement or early return)
- ✓ Contains recursive call to factorial()
- ✓ Has multiplication operator (*)
- ✓ Proper number type annotations

#### test_recursive_tree_traversal
**Scenario**: Count nodes in binary tree recursively

**IR Specification**:
```python
intent: "Count nodes in a binary tree recursively"
signature: countNodes(node: dict | None) -> int
effects:
  - "Returns 0 for null nodes"
  - "Recursively counts left and right subtrees"
assertions:
  - "result >= 0"
```

**Expected Challenges**:
- Union type parameter (node | null)
- Null checks before property access
- Recursive calls on node.left and node.right

**Predicted Failure Mode**: Missing null checks → runtime errors on null.left access

**Validation Checks**:
- ✓ Null/undefined handling (null keyword or ? operator)
- ✓ Recursive call to countNodes()
- ✓ Property access (. or ?.)

---

### Generic Tests

#### test_generic_array_function
**Scenario**: Get first element from generic array

**IR Specification**:
```python
intent: "Get first element from array (generic)"
signature: first(arr: list[Any]) -> Any | None
effects:
  - "Returns undefined for empty arrays"
  - "Returns arr[0] otherwise"
```

**Expected Challenges**:
- Generic type parameter T should be preserved
- Array<T> type annotation
- Return type T | undefined

**Predicted Failure Mode**: Generic type erasure (Array<T> → Array<any>)

**Validation Checks**:
- ✓ Array type annotation (Array or [])
- ✓ Array indexing ([0])
- ✓ Empty array handling (undefined or length check)

#### test_generic_promise_function
**Scenario**: Async function returning Promise<T>

**IR Specification**:
```python
intent: "Delay and return value asynchronously"
signature: delayedValue(value: Any, delayMs: int) -> Promise[Any]
effects:
  - "Waits for delayMs milliseconds"
  - "Returns the value after delay"
assertions:
  - "delayMs >= 0"
```

**Expected Challenges**:
- Async function detection
- Promise<T> type wrapping
- Generic return type in promise

**Predicted Failure Mode**: Missing async keyword or incorrect Promise wrapping

**Validation Checks**:
- ✓ Async keyword or Promise in signature
- ✓ Promise return type
- ✓ Delay mechanism (timeout/sleep)

---

### Complex Type Tests

#### test_union_type_handling
**Scenario**: Function accepting string | number

**IR Specification**:
```python
intent: "Convert value to string (handles string or number)"
signature: toString(value: str | int) -> str
effects:
  - "Returns value as-is if string"
  - "Converts to string if number"
```

**Expected Challenges**:
- Union type annotation (string | number)
- Type narrowing logic (typeof checks)
- Different code paths for each type

**Predicted Failure Mode**: Missing typeof checks → incorrect behavior for different types

**Validation Checks**:
- ✓ Union type annotation (|)
- ⚠️ Type narrowing (typeof) - might be missing
- ✓ String conversion logic

#### test_optional_chaining
**Scenario**: Safe nested property access

**IR Specification**:
```python
intent: "Get nested property safely with optional chaining"
signature: getUserEmail(user: dict | None) -> str | None
effects:
  - "Returns undefined if user is null"
  - "Returns undefined if profile is null"
  - "Returns email if path exists"
```

**Expected Challenges**:
- Optional chaining operator (?.)
- Multiple levels of null safety
- Proper return type handling

**Predicted Failure Mode**: Using . instead of ?. → runtime errors on null access

**Validation Checks**:
- ✓ Optional chaining operator (?.)
- ✓ Nested property access
- ✓ Null/undefined return handling

#### test_type_guard_discriminated_union
**Scenario**: Discriminated union (Result type)

**IR Specification**:
```python
intent: "Extract value from Result type (success or error)"
signature: extractValue(result: dict) -> Any | None
effects:
  - "Returns data if result.kind === 'success'"
  - "Returns null if result.kind === 'error'"
```

**Expected Challenges**:
- Discriminated union pattern
- Type narrowing based on discriminator field
- Type-safe property access after narrowing

**Predicted Failure Mode**: No discriminator checks → accessing wrong properties

**Validation Checks**:
- ✓ Conditional branching (if)
- ✓ Property access (. or ?.)
- ⚠️ Discriminator checks (kind ===) - might be missing

---

### Error Scenario Tests

#### test_null_undefined_edge_cases
**Scenario**: Nullish coalescing (value ?? default)

**IR Specification**:
```python
intent: "Get value or default (handles null and undefined)"
signature: getOrDefault(value: Any | None, defaultValue: Any) -> Any
effects:
  - "Returns value if not null/undefined"
  - "Returns defaultValue if null/undefined"
```

**Expected Challenges**:
- Nullish coalescing operator (??)
- Distinguishing null from undefined
- Proper equality checks (=== vs ==)

**Predicted Failure Mode**: Using == instead of ?? → incorrect behavior for 0 or ""

**Validation Checks**:
- ✓ Nullish coalescing (??) or conditional logic
- ✓ Both parameters used

#### test_array_bounds_checking
**Scenario**: Safe array element access

**IR Specification**:
```python
intent: "Get array element at index safely"
signature: getAt(arr: list[Any], index: int) -> Any | None
effects:
  - "Returns undefined if index < 0"
  - "Returns undefined if index >= arr.length"
  - "Returns arr[index] otherwise"
```

**Expected Challenges**:
- Index validation (< 0, >= length)
- Safe array access
- Proper undefined return

**Predicted Failure Mode**: No bounds checking → out-of-bounds access

**Validation Checks**:
- ✓ Length check or conditional
- ✓ Array indexing ([])

---

### Async Edge Case Tests

#### test_async_error_propagation
**Scenario**: Async function with retry on error

**IR Specification**:
```python
intent: "Fetch with retry on failure"
signature: fetchWithRetry(url: str) -> Promise[dict]
effects:
  - "Attempts fetch operation"
  - "Retries once if first attempt fails"
  - "Throws error if both attempts fail"
assertions:
  - "url.length > 0"
```

**Expected Challenges**:
- Try/catch in async context
- Error rethrowing
- Retry logic

**Predicted Failure Mode**: No try/catch blocks → unhandled promise rejections

**Validation Checks**:
- ✓ Async keyword or Promise
- ⚠️ Try/catch blocks - might be missing
- ⚠️ Retry logic - likely missing

#### test_promise_chaining
**Scenario**: Sequential async operations with dependencies

**IR Specification**:
```python
intent: "Fetch user, then fetch their posts (chained async)"
signature: getUserPosts(userId: int) -> Promise[list]
effects:
  - "First: fetch user data by ID"
  - "Then: fetch posts using user data"
  - "Returns array of posts"
assertions:
  - "userId > 0"
```

**Expected Challenges**:
- Multiple await statements
- Correct sequencing (user before posts)
- Data flow between promises

**Predicted Failure Mode**: Parallel awaits instead of sequential → incorrect dependency

**Validation Checks**:
- ✓ Async keyword
- ⚠️ Multiple awaits (>= 2) - might not sequence correctly
- ✓ Promise return type

---

## Predicted Failure Analysis

### High Confidence Failures (>80% Expected)

1. **Recursion Base Cases**: Generator likely won't infer base case conditions
   - test_recursive_factorial
   - test_recursive_tree_traversal

2. **Type Narrowing**: Complex type guards likely missing
   - test_union_type_handling (typeof checks)
   - test_type_guard_discriminated_union (discriminator checks)

3. **Error Handling**: Try/catch blocks rarely generated automatically
   - test_async_error_propagation

4. **Retry Logic**: Complex control flow likely not inferred
   - test_async_error_propagation (retry mechanism)

### Medium Confidence Failures (40-60% Expected)

1. **Optional Chaining**: Might use . instead of ?.
   - test_optional_chaining

2. **Nullish Coalescing**: Might use || instead of ??
   - test_null_undefined_edge_cases

3. **Generic Preservation**: Might erase generics to any
   - test_generic_array_function
   - test_generic_promise_function

4. **Bounds Checking**: Validation logic might be incomplete
   - test_array_bounds_checking

### Low Confidence Failures (<30% Expected)

1. **Basic Async Detection**: Should correctly detect async from IR
   - test_generic_promise_function (async keyword)

2. **Array Operations**: Basic array operations should work
   - test_generic_array_function (indexing)

3. **Promise Chaining**: Basic sequencing might work
   - test_promise_chaining (if LLM understands dependency)

---

## Schema Enhancement Recommendations

Based on predicted failures, consider these IR schema enhancements:

### 1. Control Flow Hints
```python
class ControlFlowHint(BaseModel):
    type: Literal["recursive", "iterative", "conditional"]
    base_case: Optional[str]  # For recursive functions
    loop_variant: Optional[str]  # For iterative functions
```

### 2. Type Guard Hints
```python
class TypeGuard(BaseModel):
    variable: str
    discriminator: Optional[str]  # For discriminated unions
    narrowing_logic: str  # "typeof x === 'string'"
```

### 3. Error Handling Policy
```python
class ErrorHandlingPolicy(BaseModel):
    strategy: Literal["throw", "return_null", "retry"]
    retry_count: Optional[int]
    error_type: Optional[str]
```

### 4. Null Safety Level
```python
class NullSafetyLevel(BaseModel):
    level: Literal["strict", "lenient"]
    use_optional_chaining: bool
    use_nullish_coalescing: bool
```

---

## Next Steps

### Before Recording Fixtures

1. **Review test IRs**: Ensure IR specifications accurately capture intent
2. **Add more assertions**: Consider adding more specific assertions to IR
3. **Document expected behavior**: Clarify what "correct" output looks like

### During Fixture Recording

1. **Record with real Modal LLM**: Set `RECORD_FIXTURES=true`
2. **Analyze failures**: Document which tests fail and why
3. **Compare with predictions**: Verify predicted failure modes

### After Test Execution

1. **Categorize failures**:
   - Generator bugs (needs fixing)
   - IR limitations (needs schema enhancement)
   - Unrealistic expectations (adjust test)

2. **Prioritize fixes**:
   - Critical: Recursion base cases, null safety
   - Important: Type narrowing, error handling
   - Nice-to-have: Advanced generic preservation

3. **Update generator**:
   - Add missing patterns to schema
   - Enhance prompt engineering
   - Implement fallback strategies

---

## Test Infrastructure

### Fixture Caching

All tests use `code_recorder` fixture for fast CI:

```python
typescript = await code_recorder.get_or_record(
    key="typescript_edge_recursive_factorial",
    generator_fn=lambda: generator.generate(ir),
    metadata={
        "test": "typescript_edge_cases",
        "category": "recursion",
        "feature": "recursive_function",
        "expected_failure": "missing_base_case",
    },
)
```

### Metadata Tags

Each test includes metadata for tracking:
- `test`: Test module name
- `category`: Test category (recursion, generics, etc.)
- `feature`: Specific feature being tested
- `expected_failure`: Predicted failure mode

### Running Tests

```bash
# Record new fixtures (real Modal LLM)
RECORD_FIXTURES=true uv run pytest tests/integration/test_typescript_edge_cases.py -v

# Use cached fixtures (fast CI)
uv run pytest tests/integration/test_typescript_edge_cases.py -v

# Run specific category
uv run pytest tests/integration/test_typescript_edge_cases.py -k "recursion" -v

# Run with coverage
uv run pytest tests/integration/test_typescript_edge_cases.py --cov=lift_sys.codegen.languages
```

---

## Success Metrics

### Coverage Goals

- [ ] 100% of edge case tests implemented (11/11) ✅
- [ ] All tests have fixture recordings
- [ ] Failure analysis documented for each failing test
- [ ] At least 60% pass rate on first run (7/11 passing)
- [ ] All critical failures fixed within 2 weeks

### Quality Indicators

**Good Generator Quality** (80%+ pass rate):
- Recursion: Both tests pass with correct base cases
- Generics: At least 1/2 tests preserve generic types
- Complex Types: 2/3 tests handle types correctly
- Error Scenarios: 1/2 tests implement validation
- Async: 1/2 tests handle async patterns correctly

**Needs Improvement** (50-80% pass rate):
- Some edge cases fail but basic patterns work
- Schema enhancements can address most failures

**Critical Issues** (<50% pass rate):
- Fundamental generator weaknesses
- Major schema redesign needed

---

## Related Documentation

- **Test File**: `tests/integration/test_typescript_edge_cases.py`
- **Generator**: `lift_sys/codegen/languages/typescript_generator.py`
- **Type Resolver**: `lift_sys/codegen/languages/typescript_types.py`
- **Schema**: `lift_sys/codegen/languages/typescript_schema.py`
- **Existing Tests**: `tests/integration/test_typescript_pipeline_e2e.py`
- **Quality Framework**: `tests/validation/typescript_quality_validator.py`

---

**Status**: Ready for fixture recording
**Next Action**: Run with RECORD_FIXTURES=true to capture LLM responses
**Owner**: Claude Code Agent
**Last Updated**: 2025-10-23
