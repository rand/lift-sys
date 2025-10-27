---
track: dspy
document_type: integration_guide
status: planning
priority: P1
completion: 0%
phase: A
last_updated: 2025-10-23
session_protocol: |
  For new Claude Code session:
  1. Rust generator integration is PLANNED but not started
  2. Follow proven TypeScript pattern (see DSPY_TYPESCRIPT_INTEGRATION.md)
  3. Prerequisites: TypeScript integration complete and validated
  4. Implementation: Replace provider calls with ProviderAdapter
  5. Test with: uv run pytest tests/unit/test_rust_generator.py
related_docs:
  - docs/tracks/dspy/DSPY_TYPESCRIPT_INTEGRATION.md
  - docs/tracks/dspy/SESSION_STATE.md
  - lift_sys/dspy_signatures/provider_adapter.py
  - docs/tracks/dspy/DSPY_GO_INTEGRATION.md
  - docs/tracks/dspy/DSPY_JAVA_INTEGRATION.md
---

# DSPy Architecture Integration: Rust Generator

**Date**: 2025-10-23
**Status**: Planning
**Phase**: Architecture Integration (Phase A)

---

## Overview

This document describes the integration of the Rust code generator with the new DSPy + Pydantic AI architecture. This integration follows the **proven pattern** from TypeScript generator integration (commit 1186ca7).

**Goal**: Apply the ProviderAdapter pattern to RustGenerator to enable resource tracking, dual routing, and preparation for DSPy signature integration.

**Prerequisites**: TypeScript generator integration complete and validated.

---

## Integration Strategy

### Phase 1: Minimal Integration (Current Plan)

**Objective**: Replace direct provider calls with ProviderAdapter while preserving existing behavior.

**Changes Required**:
1. **Import DSPy Components**
2. **Update `__init__` to create adapter**
3. **Update `_generate_implementation` to use adapter**
4. **Extract JSON from `dspy.Prediction`**

**Benefits**:
- ✅ Resource tracking (token counts, LLM calls) via H14
- ✅ Dual routing capability (Modal for XGrammar, best available otherwise)
- ✅ Foundation for validation hooks (H9)
- ✅ Backward compatible (tests should pass unchanged)

**Risks**:
- Low - ProviderAdapter is drop-in compatible
- Rust-specific: Schema handles lifetimes, trait bounds, error handling (already tested in existing implementation)

---

## Exact Code Changes

### 1. Import Statements (Line 10-15 region)

**Current** (rust_generator.py, lines 10-15):
```python
from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .rust_schema import RUST_GENERATION_SCHEMA, get_prompt_for_rust_generation
from .rust_types import RustTypeResolver
```

**New** (add after line 11):
```python
from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
# DSPy Architecture Integration (Phase A: Minimal Integration)
from ...dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .rust_schema import RUST_GENERATION_SCHEMA, get_prompt_for_rust_generation
from .rust_types import RustTypeResolver
```

**Changes**: 2 lines added (import statement + comment)

---

### 2. Update `__init__` Method (Lines 26-53)

**Current** (rust_generator.py, lines 26-53):
```python
def __init__(
    self,
    provider: BaseProvider,
    config: CodeGeneratorConfig | None = None,
    repository_path: Path | None = None,
):
    """
    Initialize Rust generator.

    Args:
        provider: LLM provider for code generation
        config: Code generation configuration
        repository_path: Optional repository path for LSP context
    """
    self.provider = provider
    self.config = config or CodeGeneratorConfig()
    self.type_resolver = RustTypeResolver()

    # Set up LSP context provider if repository path provided
    self.context_provider: LSPSemanticContextProvider | None = None
    if repository_path:
        lsp_config = LSPConfig(
            repository_path=repository_path,
            language="rust",
            cache_enabled=True,
            metrics_enabled=True,
        )
        self.context_provider = LSPSemanticContextProvider(lsp_config)
```

**New** (add after line 53):
```python
def __init__(
    self,
    provider: BaseProvider,
    config: CodeGeneratorConfig | None = None,
    repository_path: Path | None = None,
):
    """
    Initialize Rust generator.

    Args:
        provider: LLM provider for code generation
        config: Code generation configuration
        repository_path: Optional repository path for LSP context
    """
    self.provider = provider
    self.config = config or CodeGeneratorConfig()
    self.type_resolver = RustTypeResolver()

    # Set up LSP context provider if repository path provided
    self.context_provider: LSPSemanticContextProvider | None = None
    if repository_path:
        lsp_config = LSPConfig(
            repository_path=repository_path,
            language="rust",
            cache_enabled=True,
            metrics_enabled=True,
        )
        self.context_provider = LSPSemanticContextProvider(lsp_config)

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

**Changes**: 8 lines added (comment + adapter initialization)

---

### 3. Update `_generate_implementation` Method (Lines 136-218)

**Current** (rust_generator.py, lines 195-218):
```python
# Check if provider supports constrained generation (Modal with XGrammar)
if (
    hasattr(self.provider, "generate_structured")
    and hasattr(self.provider, "capabilities")
    and self.provider.capabilities.structured_output
):
    # Use constrained generation - guaranteed to match schema
    impl_json = await self.provider.generate_structured(
        prompt=prompt,
        schema=RUST_GENERATION_SCHEMA,
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
```

**New** (replace lines 195-218):
```python
# DSPy Architecture Integration: Use ProviderAdapter for dual routing
# ProviderAdapter automatically:
# - Routes to Modal (XGrammar) when schema provided and supported
# - Falls back to best available provider otherwise
# - Tracks token usage and LLM calls (H14 ResourceLimits)
# - Prepares for future DSPy signature integration
prediction = await self.adapter(
    prompt=prompt,
    schema=RUST_GENERATION_SCHEMA,
    max_tokens=2000,
    temperature=0.3,
)

# Extract implementation dict from dspy.Prediction
# ProviderAdapter returns prediction with fields: implementation, imports, lifetimes, etc.
# Convert back to dict for compatibility with existing code
impl_json = {
    k: v
    for k, v in prediction.__dict__.items()
    if not k.startswith("_")  # Filter out internal dspy attributes
}

return impl_json
```

**Changes**:
- **Removed**: 23 lines (old provider routing logic)
- **Added**: 19 lines (new adapter call + extraction)
- **Net**: ~4 fewer lines

---

## Summary of Changes

| Location | Lines Changed | Type | Impact |
|----------|--------------|------|---------|
| Imports | +2 | Add | Import ProviderAdapter, ProviderConfig |
| `__init__` | +8 | Add | Create adapter instance |
| `_generate_implementation` | -23, +19 | Replace | Use adapter instead of direct provider |
| **Total** | **~4 net** | **Minimal** | **Drop-in replacement** |

**Total Files Modified**: 1 (`rust_generator.py`)

---

## Rust-Specific Considerations

### 1. Lifetimes

**Schema Support**: `RUST_GENERATION_SCHEMA` includes dedicated `lifetimes` array:
```json
"lifetimes": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
            "purpose": {"type": "string"}
        }
    }
}
```

**Integration Impact**: None - schema already handles lifetimes. ProviderAdapter passes schema through unchanged.

**Example**:
```json
{
  "lifetimes": [
    {"name": "a", "purpose": "Lifetime for input reference"}
  ]
}
```

**Code Generation**: Existing `_build_rust_code()` method already handles lifetimes from JSON (no changes needed).

---

### 2. Trait Bounds

**Schema Support**: `RUST_GENERATION_SCHEMA` includes `trait_bounds` array:
```json
"trait_bounds": {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "parameter": {"type": "string"},
            "traits": {"type": "array", "items": {"type": "string"}}
        }
    }
}
```

**Integration Impact**: None - schema already handles trait bounds.

**Example**:
```json
{
  "trait_bounds": [
    {
      "parameter": "T",
      "traits": ["Clone", "Debug"]
    }
  ]
}
```

**Code Generation**: Existing code handles trait bounds (no changes needed).

---

### 3. Error Handling (Result/Option)

**Schema Support**: `RUST_GENERATION_SCHEMA` includes dedicated `error_handling` object:
```json
"error_handling": {
    "type": "object",
    "properties": {
        "uses_result": {"type": "boolean"},
        "uses_option": {"type": "boolean"},
        "error_type": {"type": ["string", "null"]},
        "uses_question_mark": {"type": "boolean"}
    }
}
```

**Integration Impact**: None - schema already handles Rust error patterns.

**Example**:
```json
{
  "error_handling": {
    "uses_result": true,
    "error_type": "std::io::Error",
    "uses_question_mark": true
  }
}
```

**Code Generation**: Existing code handles error types (no changes needed).

---

### 4. Ownership and Mutability

**Schema Support**: `variables` array includes `mutability` field:
```json
"variables": {
    "type": "array",
    "items": {
        "properties": {
            "name": {"type": "string"},
            "type_hint": {"type": ["string", "null"]},
            "mutability": {
                "type": "string",
                "enum": ["mut", "immutable"],
                "default": "immutable"
            }
        }
    }
}
```

**Integration Impact**: None - schema already handles Rust ownership patterns.

**Example**:
```json
{
  "variables": [
    {"name": "result", "type_hint": "Vec<i32>", "mutability": "mut"},
    {"name": "count", "type_hint": "usize", "mutability": "immutable"}
  ]
}
```

**Code Generation**: Existing `_build_rust_code()` handles mutability correctly (lines 299-310).

---

### 5. Helper Functions and Generics

**Schema Support**: Includes `helper_functions` with `is_generic` flag:
```json
"helper_functions": {
    "type": "array",
    "items": {
        "properties": {
            "name": {"type": "string"},
            "signature": {"type": "string"},
            "body": {"type": "string"},
            "is_generic": {"type": "boolean", "default": false}
        }
    }
}
```

**Integration Impact**: None - schema already supports generic helpers.

**Example**:
```json
{
  "helper_functions": [
    {
      "name": "process_item",
      "signature": "fn process_item<T: Clone>(item: T) -> T",
      "body": "item.clone()",
      "is_generic": true
    }
  ]
}
```

---

### 6. Rust Syntax Validation

**Current Implementation**: Uses `rustc --crate-type lib` for syntax validation (lines 363-403).

**Integration Impact**: None - validation happens after code generation, unaffected by ProviderAdapter.

**Considerations**:
- Validation runs on generated code string
- Uses subprocess to call `rustc`
- Has timeout protection (10s)
- Gracefully degrades if `rustc` not available

**No changes needed** - validation is independent of provider layer.

---

## Testing Strategy

### Phase 1 Testing

**Objective**: Verify ProviderAdapter integration preserves existing behavior.

**Tests**:
1. **Existing E2E Tests** (must pass unchanged):
   - `tests/integration/test_rust_pipeline_e2e.py` (if exists)
   - Or: `tests/e2e/test_codegen.py` (with Rust examples)

2. **Performance Validation**:
   - Compare latency: old vs new implementation
   - Target: <10% overhead (same as TypeScript)

3. **Resource Tracking**:
   - Verify token counts are tracked
   - Verify LLM call counts are tracked

4. **Rust-Specific Tests**:
   - Test with IR containing lifetimes
   - Test with IR containing trait bounds
   - Test with Result/Option return types
   - Test with mutable variables

**Success Criteria**:
- ✅ All existing tests pass
- ✅ Performance within 10% of baseline
- ✅ Resource tracking works correctly
- ✅ Rust-specific features (lifetimes, traits, mutability) work correctly

---

### Test Commands

```bash
# 1. COMMIT CHANGES FIRST (MANDATORY)
git add lift_sys/codegen/languages/rust_generator.py
git commit -m "feat: Integrate Rust generator with DSPy ProviderAdapter"

# 2. KILL OLD TESTS
pkill -f pytest

# 3. RUN RUST-SPECIFIC TESTS
# Option A: If rust_pipeline_e2e tests exist
uv run pytest tests/integration/test_rust_pipeline_e2e.py -v \
  > /tmp/rust_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Option B: Run all codegen tests (includes Rust)
uv run pytest tests/integration/test_codegen.py -v -k rust \
  > /tmp/rust_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Option C: Run full codegen test suite
uv run pytest tests/integration/test_codegen.py -v \
  > /tmp/rust_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 4. WAIT FOR COMPLETION
wait

# 5. CHECK RESULTS
tail -100 /tmp/rust_dspy_integration_test_*.log | tail -100
```

---

### Validation Checklist

Before marking integration complete:

- [ ] All existing tests pass
- [ ] Performance regression check (<10% overhead)
- [ ] Resource tracking verified (token counts, call counts)
- [ ] Lifetimes work correctly (if IR contains lifetime annotations)
- [ ] Trait bounds work correctly (if IR contains generic constraints)
- [ ] Result/Option error handling works
- [ ] Mutability (mut/immutable) works correctly
- [ ] Helper functions with generics work
- [ ] Rustc syntax validation still works
- [ ] Documentation updated (this file)

---

## Implementation Plan

### Step 1: Update RustGenerator

**File**: `lift_sys/codegen/languages/rust_generator.py`

**Changes**:
- [ ] Add imports (lines 12-13): `ProviderAdapter`, `ProviderConfig`
- [ ] Update `__init__` (after line 53): Create `self.adapter`
- [ ] Update `_generate_implementation` (replace lines 195-218): Use adapter

**Estimated Time**: 15 minutes

**Lines Changed**: ~4 net (see Summary of Changes above)

---

### Step 2: Run Tests

**Commands**: See "Test Commands" section above

**Estimated Time**:
- Test execution: 2-5 minutes (depending on Modal cold start)
- Analysis: 5-10 minutes

**Total**: 7-15 minutes

---

### Step 3: Validate Results

**Check**:
1. **Test Results**: All pass?
2. **Performance**: Compare with baseline (TypeScript integration results)
3. **Resource Tracking**: Tokens/calls logged in adapter?
4. **Rust Features**: Lifetimes, traits, mutability correct?

**Estimated Time**: 10 minutes

---

### Step 4: Document Findings

**Create**: `docs/planning/DSPY_RUST_INTEGRATION_RESULTS.md`

**Include**:
- Test results (pass/fail counts)
- Performance comparison (latency vs baseline)
- Resource tracking data (tokens, calls)
- Rust-specific feature validation
- Issues encountered (if any)
- Recommendations for Go/Java integration

**Estimated Time**: 20 minutes

---

## Total Effort Estimate

| Phase | Task | Time |
|-------|------|------|
| Step 1 | Code changes | 15 min |
| Step 2 | Run tests | 7-15 min |
| Step 3 | Validate results | 10 min |
| Step 4 | Document findings | 20 min |
| **Total** | **End-to-end** | **52-60 min** |

**Conservative Estimate**: 1 hour
**Best Case**: 45 minutes

---

## Migration Pattern for Other Languages

Once Rust integration is validated, apply the same pattern to:

1. **GoGenerator** (`lift_sys/codegen/languages/go_generator.py`)
   - Similar structure to RustGenerator
   - No lifetimes/traits (simpler)
   - Estimated: 30-45 minutes

2. **JavaGenerator** (`lift_sys/codegen/languages/java_generator.py`)
   - Similar structure to RustGenerator
   - Generics handled differently (type erasure)
   - Estimated: 30-45 minutes

**Total for All 3 Languages** (Rust + Go + Java): 2-2.5 hours

---

## Future Enhancements

### Phase 2: DSPy Signatures (Future)

**Objective**: Replace hardcoded prompts with declarative DSPy signatures.

**Approach**:
1. Define `RustImplementationSignature(dspy.Signature)`:
   ```python
   class RustImplementationSignature(dspy.Signature):
       """Generate Rust implementation from specification."""

       # Inputs
       intent: str = dspy.InputField(desc="High-level intent/summary")
       signature: str = dspy.InputField(desc="Rust function signature")
       constraints: list[str] = dspy.InputField(desc="Constraints to satisfy")
       effects: list[str] = dspy.InputField(desc="Operational steps")

       # Rust-specific inputs
       lifetimes: list[str] = dspy.InputField(desc="Required lifetime parameters")
       trait_bounds: list[dict] = dspy.InputField(desc="Generic trait constraints")

       # Output
       implementation: dict = dspy.OutputField(desc="JSON implementation")
   ```

2. Use DSPy modules with schema:
   ```python
   predictor = SchemaConstrainedPredict(
       RustImplementationSignature,
       schema=RUST_GENERATION_SCHEMA
   )
   result = predictor(
       intent=ir.intent.summary,
       signature=rust_signature,
       constraints=constraints,
       effects=effects,
       lifetimes=lifetime_params,
       trait_bounds=trait_constraints
   )
   ```

**Timeline**: After TypeScript Phase 2 completion

---

### Phase 3: Validation Hooks (Future)

**Objective**: Integrate H9 ValidationHooks for result validation.

**Rust-Specific Validators**:
1. **Rustc Syntax Validator**: Use existing `_validate_rust_syntax()` method
2. **Lifetime Soundness Validator**: Check lifetime annotations are correct
3. **Borrow Checker Validator**: Verify ownership rules satisfied
4. **Schema Compliance Validator**: Verify JSON matches schema

**Example**:
```python
async def rust_borrow_checker_validator(
    context: RunContext,
    implementation: dict
) -> ValidationResult:
    # Build code and run rustc with borrow checker
    code = build_rust_code(implementation)
    is_valid, error = validate_rust_syntax(code)

    if is_valid:
        return ValidationResult(status="PASS", message="Borrow checker satisfied")
    else:
        return ValidationResult(
            status="FAIL",
            message="Borrow checker errors",
            details={"rustc_error": error}
        )
```

**Timeline**: After Phase 2

---

## Risks and Mitigations

### Risk 1: Rust-Specific Schema Complexity

**Risk**: Rust schema has more fields than TypeScript (lifetimes, trait_bounds, error_handling).

**Mitigation**:
- Schema already tested with existing RustGenerator
- ProviderAdapter passes schema through unchanged
- No new behavior introduced

**Likelihood**: Low
**Impact**: Low

---

### Risk 2: Performance Regression

**Risk**: ProviderAdapter adds overhead.

**Mitigation**:
- TypeScript integration showed <10% overhead target
- ProviderAdapter designed for minimal overhead
- Performance validation in testing phase

**Likelihood**: Low
**Impact**: Medium

**Fallback**: If >10% overhead, investigate and optimize adapter.

---

### Risk 3: Rustc Validation Interaction

**Risk**: Adapter changes affect syntax validation.

**Mitigation**:
- Validation runs on generated code string (independent of adapter)
- No changes to `_validate_rust_syntax()` method
- Tests will catch any issues

**Likelihood**: Very Low
**Impact**: Medium

---

### Risk 4: Resource Tracking Overhead

**Risk**: Token/call tracking adds latency.

**Mitigation**:
- Tracking is simple counter increments (<1ms)
- Optional (can disable with `track_resources=False`)
- TypeScript integration will validate overhead

**Likelihood**: Very Low
**Impact**: Low

---

## Questions & Answers

**Q: Will this break backward compatibility?**
A: No - ProviderAdapter is drop-in compatible. Existing tests should pass unchanged. Same pattern as TypeScript.

**Q: What about Rust's unique features (lifetimes, trait bounds)?**
A: Schema already handles these. ProviderAdapter passes schema through unchanged. No new behavior introduced.

**Q: What if rustc validation fails more often?**
A: Validation logic unchanged - runs on generated code string regardless of provider. If failure rate changes, it's an LLM quality issue, not adapter issue.

**Q: Does ProviderAdapter understand Rust syntax?**
A: No - it's provider-agnostic. It passes prompt + schema to underlying provider, gets JSON back, converts to `dspy.Prediction`. Language-specific logic stays in generator.

**Q: What about providers without structured output?**
A: ProviderAdapter handles this - routes to `generate_text()` and parses JSON from response. Same as existing fallback behavior.

**Q: How does this compare to TypeScript integration?**
A: Nearly identical:
- Same imports
- Same adapter initialization
- Same call pattern
- Only difference: Rust schema has more fields (lifetimes, traits), but adapter doesn't care

---

## References

### Internal Documents
- [TypeScript Integration Guide](./DSPY_TYPESCRIPT_INTEGRATION.md) - Proven pattern
- [TypeScript Integration Commit](https://github.com/rand/lift-sys/commit/1186ca7) - Working example
- [ProviderAdapter Design](./DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md) - H1 specification
- [Hole Inventory](./HOLE_INVENTORY.md) - H1, H9, H14 dependencies

### Code Files
- `lift_sys/codegen/languages/rust_generator.py` - Target file
- `lift_sys/codegen/languages/typescript_generator.py` - Reference implementation
- `lift_sys/codegen/languages/rust_schema.py` - Rust schema definition
- `lift_sys/dspy_signatures/provider_adapter.py` - ProviderAdapter implementation

### External Resources
- [Rust Reference](https://doc.rust-lang.org/reference/) - Lifetimes, traits, ownership
- [DSPy Documentation](https://dspy-docs.vercel.app/) - Prediction objects
- [XGrammar](https://github.com/mlc-ai/xgrammar) - Constraint-based generation

---

**Document Status**: ACTIVE
**Owner**: Architecture Integration Team
**Next Update**: After Rust integration completion
**Related Work**: TypeScript integration (complete), Go/Java integration (pending)
