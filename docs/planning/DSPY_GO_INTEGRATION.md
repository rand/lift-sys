# DSPy Architecture Integration: Go Generator

**Date**: 2025-10-23
**Status**: Planning
**Phase**: Architecture Integration (Phase A)

---

## Overview

This document describes the integration of the Go code generator with the new DSPy + Pydantic AI architecture. This follows the proven pattern established by the TypeScript generator integration (commit 1186ca7).

**Goal**: Apply validated DSPy ProviderAdapter pattern to Go generator, leveraging Go-specific schema features (goroutines, channels, defer, error handling).

---

## Integration Strategy

### Phase 1: Minimal Integration (Planned)

**Objective**: Replace direct provider calls with ProviderAdapter while preserving existing behavior.

**Changes**:
1. **Import DSPy Components**:
   - `ProviderAdapter` (H1) - Dual routing between Modal/Best Available
   - `ProviderConfig` - Generation configuration

2. **Update `__init__`** (Line 25-52):
   ```python
   # BEFORE (line 10):
   from ...providers.base import BaseProvider

   # AFTER (add at line 10):
   from ...dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
   from ...providers.base import BaseProvider

   # BEFORE (line 39):
   self.provider = provider
   self.config = config or CodeGeneratorConfig()

   # AFTER (line 39-48):
   self.provider = provider
   self.config = config or CodeGeneratorConfig()
   self.type_resolver = GoTypeResolver()

   # DSPy Architecture Integration: Create ProviderAdapter for dual routing
   # This enables resource tracking (H14) and prepares for DSPy signature integration
   self.adapter = ProviderAdapter(
       provider=provider,
       config=ProviderConfig(
           max_tokens=2000,
           temperature=0.3,
           use_xgrammar=True,  # Enable XGrammar constraints when available
       ),
   )
   ```

3. **Update `_generate_implementation`** (Line 128-218):
   ```python
   # BEFORE (lines 196-218):
   # Check if provider supports constrained generation (Modal with XGrammar)
   if (
       hasattr(self.provider, "generate_structured")
       and hasattr(self.provider, "capabilities")
       and self.provider.capabilities.structured_output
   ):
       # Use constrained generation - guaranteed to match schema
       impl_json = await self.provider.generate_structured(
           prompt=prompt,
           schema=GO_GENERATION_SCHEMA,
           max_tokens=2000,
           temperature=0.3,
       )
       return impl_json

   # Fallback to text generation for providers without structured output
   response = await self.provider.generate_text(
       prompt=prompt,
       max_tokens=2000,
       temperature=0.3,
   )

   # Extract JSON from response
   return self._extract_json(response)

   # AFTER (lines 196-212):
   # DSPy Architecture Integration: Use ProviderAdapter for dual routing
   # ProviderAdapter automatically:
   # - Routes to Modal (XGrammar) when schema provided and supported
   # - Falls back to best available provider otherwise
   # - Tracks token usage and LLM calls (H14 ResourceLimits)
   # - Prepares for future DSPy signature integration
   prediction = await self.adapter(
       prompt=prompt,
       schema=GO_GENERATION_SCHEMA,
       max_tokens=2000,
       temperature=0.3,
   )

   # Extract implementation dict from dspy.Prediction
   # ProviderAdapter returns prediction with fields: implementation, imports, etc.
   # Convert back to dict for compatibility with existing code
   impl_json = {
       k: v
       for k, v in prediction.__dict__.items()
       if not k.startswith("_")  # Filter out internal dspy attributes
   }

   return impl_json
   ```

**Benefits**:
- ✅ Resource tracking (token counts, LLM calls) via H14
- ✅ Dual routing capability (Modal for XGrammar, best available otherwise)
- ✅ Foundation for validation hooks (H9)
- ✅ Backward compatible (tests should pass unchanged)
- ✅ Go-specific schema features preserved (goroutines, channels, defer, error handling)

**Risks**:
- None - ProviderAdapter is designed to be drop-in compatible
- Go schema complexity (8 unique fields vs 3 in TypeScript) - already handled by schema-based routing

---

## Go-Specific Considerations

### 1. Rich Schema Complexity

**Challenge**: Go schema has 8 Go-specific fields not present in TypeScript:

| Feature | TypeScript | Go | Impact |
|---------|-----------|-----|--------|
| goroutines | ❌ | ✅ | Concurrent execution tracking |
| channels | ❌ | ✅ | Communication primitives |
| defer_statements | ❌ | ✅ | LIFO cleanup execution |
| error_handling.returns_error | ❌ | ✅ | Multiple return values |
| error_handling.error_checks | ❌ | ✅ | Explicit error handling |
| statement types (go_statement, defer_statement, error_check, select_statement, range_loop) | ❌ | ✅ | Go-specific control flow |

**Solution**: ProviderAdapter handles this transparently:
- XGrammar-constrained generation enforces full schema compliance
- No changes needed to schema or prompt generation
- Existing `_build_go_code()` already handles all Go-specific fields

**Validation**: Verify all Go-specific fields are preserved after integration.

---

### 2. Error Handling Patterns

**Go's Unique Error Pattern**:
```go
// Multiple return values with error
func doSomething() (Result, error) {
    if err != nil {
        return nil, fmt.Errorf("failed: %w", err)
    }
    return result, nil
}
```

**Schema Support**:
```json
{
  "error_handling": {
    "returns_error": true,
    "error_checks": [
      {
        "source": "doSomething()",
        "handling": "return"  // or "wrap", "log", "ignore", "panic"
      }
    ]
  }
}
```

**Integration Impact**: None - schema and code generation already handle this.

**Testing**: Ensure error handling patterns are preserved in generated code.

---

### 3. Concurrency Primitives

**Goroutines**:
```go
go worker(ch)  // Spawn concurrent goroutine
```

**Channels**:
```go
ch := make(chan int, 10)    // Buffered channel
results := make(chan Result) // Unbuffered channel
<-ch                         // Receive
ch <- value                  // Send
```

**Select Statements**:
```go
select {
case msg := <-ch1:
    // Handle msg
case ch2 <- value:
    // Sent value
case <-time.After(timeout):
    // Timeout
}
```

**Schema Support**:
- `goroutines` array: Tracks spawned goroutines
- `channels` array: Tracks channel creation (buffered, direction)
- `select_statement` type: Handles multi-channel operations

**Integration Impact**: None - schema and code generation already handle this.

**Testing**: Verify concurrent patterns generate correctly.

---

### 4. Defer Statements (LIFO Cleanup)

**Go Defer Pattern**:
```go
func processFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()  // Executed in LIFO order at function exit

    // ... process file
}
```

**Schema Support**:
```json
{
  "defer_statements": [
    {
      "code": "f.Close()",
      "rationale": "Close file handle on function exit"
    }
  ]
}
```

**Code Generation**: Defers emitted at function start (execute at end):
```python
# Line 311-319 in go_generator.py
defer_statements = impl.get("defer_statements", [])
if defer_statements:
    for defer_stmt in defer_statements:
        code = defer_stmt.get("code", "")
        rationale = defer_stmt.get("rationale")
        if rationale:
            lines.append(f"\t// {rationale}")
        lines.append(f"\tdefer {code}")
```

**Integration Impact**: None - defer handling already correct.

**Testing**: Verify defer statements appear in correct position.

---

### 5. No Syntax Validation (vs TypeScript)

**TypeScript Generator** (Line 426-467):
```python
def _validate_typescript_syntax(self, code: str) -> tuple[bool, str]:
    # Runs `tsc --noEmit` for syntax validation
    result = subprocess.run(["tsc", "--noEmit", ...])
    return (result.returncode == 0, result.stdout)
```

**Go Generator** (Line 99-100):
```python
# Note: Go syntax validation would require running `go build` or `gofmt -e`
# which requires a valid Go module. Skipping for now, but could be added.
```

**Why Skip Go Validation**:
1. Requires valid `go.mod` (module context)
2. Requires Go toolchain installed
3. XGrammar constraints already enforce schema compliance
4. Future work: Add `gofmt -e` validation (syntax-only, no module required)

**Integration Impact**: None - no validation to migrate.

**Testing**: Rely on existing schema validation and manual inspection.

---

### 6. Type Resolution Differences

**TypeScript Types**:
- `string`, `number`, `boolean`, `any`
- `Promise<T>` for async
- Union types: `string | null`

**Go Types**:
- `string`, `int`, `float64`, `bool`, `interface{}`
- `error` for error handling
- Pointer types: `*Type`
- Slice types: `[]Type`
- Channel types: `chan Type`, `<-chan Type`, `chan<- Type`

**Type Resolver** (`go_types.py`):
```python
class GoTypeResolver:
    def resolve(self, type_hint: str) -> ResolvedType:
        # Maps Python types to Go types
        mapping = {
            "str": "string",
            "int": "int",
            "list[int]": "[]int",
            # ... etc
        }
```

**Integration Impact**: None - type resolution independent of provider routing.

**Testing**: Verify type mappings preserved.

---

## Testing Strategy

### Phase 1 Testing

**Objective**: Verify ProviderAdapter integration preserves existing behavior.

**Tests**:
1. **Existing E2E Tests** (must pass unchanged):
   - `tests/integration/test_go_pipeline_e2e.py` (if exists)
   - OR create minimal test: simple function generation

2. **Go-Specific Features**:
   - **Goroutines**: Generate function with `go worker()`
   - **Channels**: Generate function using `make(chan int)`
   - **Defer**: Generate function with `defer cleanup()`
   - **Error Handling**: Generate function returning `(Result, error)`
   - **Select**: Generate function with channel select

3. **Performance Validation**:
   - Compare latency: old vs new
   - Target: <10% overhead

4. **Resource Tracking**:
   - Verify token counts are tracked
   - Verify LLM call counts are tracked

**Success Criteria**:
- ✅ All existing tests pass
- ✅ Go-specific features generate correctly (goroutines, channels, defer, errors)
- ✅ Performance within 10% of baseline
- ✅ Resource tracking works

---

## Implementation Plan

### Step 1: Update GoGenerator ⏳

**File**: `lift_sys/codegen/languages/go_generator.py`

**Changes**:
1. **Import** (Line ~10):
   ```python
   from ...dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
   ```

2. **Constructor** (Line ~39-52):
   ```python
   # Add after self.type_resolver = GoTypeResolver()
   self.adapter = ProviderAdapter(
       provider=provider,
       config=ProviderConfig(
           max_tokens=2000,
           temperature=0.3,
           use_xgrammar=True,
       ),
   )
   ```

3. **_generate_implementation** (Line ~196-218):
   ```python
   # Replace provider calls with adapter call
   prediction = await self.adapter(
       prompt=prompt,
       schema=GO_GENERATION_SCHEMA,
       max_tokens=2000,
       temperature=0.3,
   )

   # Extract dict from prediction
   impl_json = {
       k: v
       for k, v in prediction.__dict__.items()
       if not k.startswith("_")
   }

   return impl_json
   ```

**Lines Changed**: ~25 lines (minimal, same as TypeScript)

---

### Step 2: Create Go-Specific Tests

**File**: `tests/integration/test_go_dspy_integration.py`

**Test Cases**:
```python
import pytest
from lift_sys.codegen.languages.go_generator import GoGenerator
from lift_sys.ir.models import IntermediateRepresentation, Intent, Signature, Parameter

@pytest.mark.asyncio
async def test_go_simple_function(modal_provider):
    """Test basic Go function generation with DSPy integration."""
    ir = IntermediateRepresentation(
        intent=Intent(summary="Add two integers"),
        signature=Signature(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
    )

    generator = GoGenerator(provider=modal_provider)
    result = await generator.generate(ir)

    assert result.language == "go"
    assert "func add(a int, b int) int" in result.source_code
    assert "return a + b" in result.source_code


@pytest.mark.asyncio
async def test_go_error_handling(modal_provider):
    """Test Go error handling patterns with DSPy integration."""
    ir = IntermediateRepresentation(
        intent=Intent(summary="Divide two integers, return error if divisor is zero"),
        signature=Signature(
            name="safeDivide",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        effects=[
            Effect(description="Check if b is zero and return error"),
            Effect(description="Return a / b if valid"),
        ],
    )

    generator = GoGenerator(provider=modal_provider)
    result = await generator.generate(ir)

    # Should generate function returning (int, error)
    assert "func safeDivide(a int, b int) (int, error)" in result.source_code
    assert "if err != nil" in result.source_code or "if b == 0" in result.source_code
    assert "return" in result.source_code


@pytest.mark.asyncio
async def test_go_channels(modal_provider):
    """Test Go channel generation with DSPy integration."""
    ir = IntermediateRepresentation(
        intent=Intent(summary="Send integers to channel"),
        signature=Signature(
            name="sendInts",
            parameters=[
                Parameter(name="ch", type_hint="chan int"),
                Parameter(name="n", type_hint="int"),
            ],
            returns="void",
        ),
        effects=[
            Effect(description="Send integers 1 to n to channel ch"),
        ],
    )

    generator = GoGenerator(provider=modal_provider)
    result = await generator.generate(ir)

    assert "chan int" in result.source_code
    assert "ch <-" in result.source_code or "ch <- " in result.source_code


@pytest.mark.asyncio
async def test_go_defer(modal_provider):
    """Test Go defer statement generation with DSPy integration."""
    ir = IntermediateRepresentation(
        intent=Intent(summary="Read file contents with proper cleanup"),
        signature=Signature(
            name="readFile",
            parameters=[Parameter(name="path", type_hint="string")],
            returns="string",
        ),
        effects=[
            Effect(description="Open file"),
            Effect(description="Defer file close"),
            Effect(description="Read contents"),
            Effect(description="Return contents"),
        ],
    )

    generator = GoGenerator(provider=modal_provider)
    result = await generator.generate(ir)

    assert "defer" in result.source_code
    assert "Close()" in result.source_code or ".Close()" in result.source_code
```

---

### Step 3: Run Tests

**Commands**:
```bash
# Commit changes first (MANDATORY)
git add lift_sys/codegen/languages/go_generator.py
git add tests/integration/test_go_dspy_integration.py
git commit -m "feat: Integrate Go generator with DSPy ProviderAdapter"

# Kill old tests
pkill -f pytest

# Run Go E2E tests
uv run pytest tests/integration/test_go_dspy_integration.py -v \
  > /tmp/go_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Wait and check
wait
tail -100 /tmp/go_dspy_integration_test_*.log | grep -A 50 "PASSED\|FAILED\|ERROR"
```

---

### Step 4: Validate Go-Specific Features

**Manual Inspection**:
```bash
# Generate sample Go code and inspect
cat > /tmp/test_go_generation.py <<'EOF'
import asyncio
from lift_sys.codegen.languages.go_generator import GoGenerator
from lift_sys.providers.modal_provider import ModalProvider
from lift_sys.ir.models import IntermediateRepresentation, Intent, Signature, Parameter, Effect

async def main():
    provider = ModalProvider(endpoint_url="...")
    generator = GoGenerator(provider=provider)

    # Test goroutines
    ir = IntermediateRepresentation(
        intent=Intent(summary="Process data concurrently"),
        signature=Signature(
            name="processConcurrent",
            parameters=[Parameter(name="items", type_hint="[]int")],
            returns="void",
        ),
        effects=[
            Effect(description="Create channel for results"),
            Effect(description="Spawn goroutine for each item"),
            Effect(description="Collect results"),
        ],
    )

    result = await generator.generate(ir)
    print("=== Generated Go Code ===")
    print(result.source_code)
    print("\n=== Metadata ===")
    print(result.metadata)

asyncio.run(main())
EOF

uv run python /tmp/test_go_generation.py > /tmp/go_sample_output.txt 2>&1

# Inspect output
cat /tmp/go_sample_output.txt
```

**Checklist**:
- [ ] Goroutines: `go functionName()`
- [ ] Channels: `make(chan Type)`, `ch <-`, `<-ch`
- [ ] Defer: `defer cleanup()`
- [ ] Error handling: `(Result, error)`, `if err != nil`
- [ ] Imports: `import (...)` block formatted correctly
- [ ] GoDoc comments: `// Function description`

---

### Step 5: Document Results

**Create**: `docs/planning/DSPY_GO_INTEGRATION_RESULTS.md`

**Include**:
- Test results (pass/fail)
- Go-specific feature validation (goroutines, channels, defer, errors)
- Performance comparison (latency vs baseline)
- Resource tracking metrics (tokens, calls)
- Issues encountered (if any)
- Recommendations for remaining languages (Rust, Java)

---

## Migration Pattern for Other Languages

Once Go integration is validated, apply the same pattern to:
1. **RustGenerator** (2-3 hours)
   - Rust-specific: lifetimes, ownership, Result<T, E>, match expressions
2. **JavaGenerator** (2-3 hours)
   - Java-specific: exceptions, generics, annotations

**Total Effort**: 1 day for all remaining languages

---

## Future Enhancements

### Phase 2: DSPy Signatures (Future)

**Objective**: Replace hardcoded prompts with declarative DSPy signatures.

**Approach**:
```python
class GoImplementationSignature(dspy.Signature):
    """Generate Go implementation from specification."""

    # Inputs
    intent: str = dspy.InputField(desc="High-level intent/summary")
    signature: str = dspy.InputField(desc="Go function signature")
    constraints: list[str] = dspy.InputField(desc="Constraints to satisfy")
    effects: list[str] = dspy.InputField(desc="Operational steps")

    # Go-specific inputs
    needs_concurrency: bool = dspy.InputField(desc="Whether to use goroutines")
    needs_channels: bool = dspy.InputField(desc="Whether to use channels")
    returns_error: bool = dspy.InputField(desc="Whether to return error")

    # Output
    implementation: dict = dspy.OutputField(desc="JSON implementation (schema-constrained)")
```

**Benefits**:
- ✅ Go-specific semantics captured declaratively
- ✅ Optimizable with MIPROv2/COPRO (H8)
- ✅ Better provenance tracking

**Timeline**: After all 4 generators integrated (Phase A complete)

---

### Phase 3: Validation Hooks (Future)

**Objective**: Integrate H9 ValidationHooks for Go-specific validation.

**Approach**:
```python
async def go_syntax_validator(context: RunContext, implementation: dict) -> ValidationResult:
    """Validate Go syntax using gofmt -e (syntax-only, no module required)."""
    code = build_go_code(implementation)

    # Use gofmt -e for syntax checking (doesn't require go.mod)
    result = subprocess.run(
        ["gofmt", "-e"],
        input=code.encode(),
        capture_output=True,
        timeout=5,
    )

    if result.returncode == 0:
        return ValidationResult(status="PASS", message="Valid Go syntax")
    else:
        return ValidationResult(
            status="FAIL",
            message="Invalid Go syntax",
            details={"gofmt_error": result.stderr.decode()},
        )

async def go_error_handling_validator(context: RunContext, implementation: dict) -> ValidationResult:
    """Validate Go error handling patterns."""
    impl = implementation.get("implementation", {})
    error_handling = impl.get("error_handling", {})

    # Check if function claims to return error
    returns_error = error_handling.get("returns_error", False)

    # Check if body has error checks
    body = impl.get("body_statements", [])
    has_error_checks = any(stmt.get("type") == "error_check" for stmt in body)

    # Warn if returns_error but no error checks
    if returns_error and not has_error_checks:
        return ValidationResult(
            status="WARN",
            message="Function returns error but no error checks found",
            details={"suggestion": "Add error_check statements in body"},
        )

    return ValidationResult(status="PASS", message="Error handling validated")
```

**Benefits**:
- ✅ Go-specific validation (gofmt, error handling patterns)
- ✅ Composable validators (chain-of-responsibility)
- ✅ Better error messages

**Timeline**: After Phase 2

---

## Risk Assessment

### Low Risk
- ProviderAdapter integration (proven pattern from TypeScript)
- Schema preservation (no changes to GO_GENERATION_SCHEMA)
- Test creation (follow existing patterns)

### Medium Risk
- Go-specific feature validation (requires manual inspection)
- No syntax validation (unlike TypeScript with tsc)
  - **Mitigation**: Rely on XGrammar constraints, add gofmt validation in Phase 3

### High Risk
- None identified

---

## Estimated Effort

### Implementation
- Code changes: **30 minutes** (25 lines, same as TypeScript)
- Test creation: **1-2 hours** (4 test cases covering Go features)
- Test execution: **30 minutes** (including Modal cold start)
- Validation: **1 hour** (manual inspection of Go-specific features)

**Total**: **3-4 hours**

### Documentation
- Integration results: **30 minutes**
- Update session state: **15 minutes**

**Grand Total**: **4-5 hours** (half day)

---

## Success Criteria

**Must Pass**:
1. ✅ All existing tests pass (if any)
2. ✅ New Go-specific tests pass (goroutines, channels, defer, errors)
3. ✅ Resource tracking works (tokens, calls logged)
4. ✅ Performance within 10% of baseline
5. ✅ Generated code compiles with `gofmt -e` (syntax-only)

**Nice to Have**:
- Generated code follows Go best practices (short declarations, explicit errors)
- Concurrency patterns are idiomatic (channels over locks)
- Defer statements appear in correct order (LIFO)

---

## Questions & Answers

**Q: Why integrate Go before Rust/Java?**
A: Go has the most complex schema (8 unique fields) - validating it works builds confidence for simpler languages.

**Q: What if goroutines/channels don't generate correctly?**
A: Schema already handles this - test by inspecting generated code. If issues found, update prompts in `go_schema.py`, not integration code.

**Q: Should we add `go build` validation?**
A: Not for Phase 1 - requires go.mod setup. Use `gofmt -e` in Phase 3 (syntax-only, no module).

**Q: What about Go generics (Go 1.18+)?**
A: Schema doesn't currently support generics - future enhancement. Add to type resolver when needed.

**Q: Performance concerns with complex schema?**
A: XGrammar handles schema complexity efficiently. Expect similar performance to TypeScript.

---

## Next Steps

1. **Implement** (30 min): Update `go_generator.py` following Step 1
2. **Test** (2 hours): Create and run Go-specific tests (Step 2-3)
3. **Validate** (1 hour): Manual inspection of Go features (Step 4)
4. **Document** (45 min): Write results doc (Step 5)
5. **Update SESSION_STATE.md**: Mark progress on Architecture Integration

---

**Document Status**: ACTIVE
**Owner**: Architecture Integration Team
**Next Update**: After Go integration completion
**Related Documents**:
- `docs/planning/DSPY_TYPESCRIPT_INTEGRATION.md` (proven pattern)
- `docs/planning/SESSION_STATE.md` (current work context)
- `lift_sys/codegen/languages/go_schema.py` (Go schema details)
