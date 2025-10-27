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
  1. Java generator integration is PLANNED but not started
  2. Follow proven TypeScript pattern (see DSPY_TYPESCRIPT_INTEGRATION.md)
  3. Pattern: Exactly follows TypeScript integration approach
  4. Implementation: Replace provider calls with ProviderAdapter
  5. Test with: uv run pytest tests/unit/test_java_generator.py
related_docs:
  - docs/tracks/dspy/DSPY_TYPESCRIPT_INTEGRATION.md
  - docs/tracks/dspy/SESSION_STATE.md
  - lift_sys/dspy_signatures/provider_adapter.py
  - docs/tracks/dspy/DSPY_RUST_INTEGRATION.md
  - docs/tracks/dspy/DSPY_GO_INTEGRATION.md
---

# DSPy Architecture Integration: Java Generator

**Date**: 2025-10-23
**Status**: Planning
**Phase**: Architecture Integration (Phase A)

---

## Overview

This document describes the integration of the Java code generator with the new DSPy + Pydantic AI architecture, following the proven pattern from TypeScript generator integration (commit 1186ca7).

**Goal**: Apply minimal DSPy ProviderAdapter integration to Java generator while preserving existing behavior.

---

## Integration Strategy

### Phase 1: Minimal Integration (Current)

**Objective**: Replace direct provider calls with ProviderAdapter while preserving existing behavior.

**Pattern**: Exactly follows TypeScript integration (see `DSPY_TYPESCRIPT_INTEGRATION.md`)

---

## Exact Code Changes

### 1. Import Statements

**File**: `lift_sys/codegen/languages/java_generator.py`
**Location**: Lines 10-16 (imports section)

**CHANGE**:
```python
# BEFORE (current imports)
from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .java_schema import JAVA_GENERATION_SCHEMA, get_prompt_for_java_generation
from .java_types import JavaTypeResolver

# AFTER (add DSPy imports)
# DSPy Architecture Integration (Phase A: Minimal Integration)
from ...dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
from ...ir.models import IntermediateRepresentation
from ...providers.base import BaseProvider
from ..generator import CodeGeneratorConfig, GeneratedCode
from ..lsp_context import LSPConfig, LSPSemanticContextProvider
from .java_schema import JAVA_GENERATION_SCHEMA, get_prompt_for_java_generation
from .java_types import JavaTypeResolver
```

**Lines Changed**: 2 (add imports)
**Impact**: None (imports only)

---

### 2. Constructor (`__init__`) Modification

**File**: `lift_sys/codegen/languages/java_generator.py`
**Location**: Lines 27-54 (`__init__` method)

**CHANGE**:
```python
def __init__(
    self,
    provider: BaseProvider,
    config: CodeGeneratorConfig | None = None,
    repository_path: Path | None = None,
):
    """
    Initialize Java generator.

    Args:
        provider: LLM provider for code generation
        config: Code generation configuration
        repository_path: Optional repository path for LSP context
    """
    self.provider = provider
    self.config = config or CodeGeneratorConfig()
    self.type_resolver = JavaTypeResolver(prefer_primitives=True)

    # Set up LSP context provider if repository path provided
    self.context_provider: LSPSemanticContextProvider | None = None
    if repository_path:
        lsp_config = LSPConfig(
            repository_path=repository_path,
            language="java",
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

**Lines Changed**: 10 (add adapter initialization)
**Impact**:
- ✅ Adds resource tracking (token counts, LLM calls)
- ✅ Enables dual routing (Modal/best available)
- ✅ Prepares for validation hooks (H9)

---

### 3. `_generate_implementation` Method Update

**File**: `lift_sys/codegen/languages/java_generator.py`
**Location**: Lines 137-221 (`_generate_implementation` method)

**CHANGE**:

**BEFORE (lines 199-221):**
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
        schema=JAVA_GENERATION_SCHEMA,
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

**AFTER:**
```python
# DSPy Architecture Integration: Use ProviderAdapter for dual routing
# ProviderAdapter automatically:
# - Routes to Modal (XGrammar) when schema provided and supported
# - Falls back to best available provider otherwise
# - Tracks token usage and LLM calls (H14 ResourceLimits)
# - Prepares for future DSPy signature integration
prediction = await self.adapter(
    prompt=prompt,
    schema=JAVA_GENERATION_SCHEMA,
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

**Lines Changed**: ~25 (replace provider call logic with adapter call)
**Impact**:
- ✅ Simplifies routing logic (handled by ProviderAdapter)
- ✅ Adds resource tracking automatically
- ✅ Maintains backward compatibility (returns dict as before)

---

## Java-Specific Considerations

### 1. Schema Complexity

**Java Schema Features** (from `java_schema.py`):
- **Generics**: `<T extends Comparable<T>>`
- **Annotations**: `@Override`, `@Deprecated`, etc.
- **Checked Exceptions**: `throws IOException`
- **Access Modifiers**: `public`, `private`, `protected`, `package-private`
- **Static/Instance Methods**
- **Final Variables**

**Impact on Integration**:
- ✅ **No changes needed** - ProviderAdapter passes schema transparently
- ✅ XGrammar constraints handle Java-specific syntax
- ✅ Schema validation remains unchanged

**Example Java Schema Excerpt**:
```json
{
  "generics": [
    {
      "type_parameter": "T",
      "bounds": "extends Comparable<T>"
    }
  ],
  "exception_handling": {
    "checked_exceptions": ["IOException", "SQLException"]
  },
  "annotations": [
    {"name": "Override"},
    {"name": "SuppressWarnings", "parameters": "\"unchecked\""}
  ]
}
```

**ProviderAdapter Handling**: Schema passed as-is to XGrammar → guarantees compliance

---

### 2. Checked Exceptions in Schema

**Challenge**: Java requires declared checked exceptions in method signatures.

**Current Implementation** (lines 275-332):
- Schema includes `exception_handling.checked_exceptions` array
- `_build_java_code` adds `throws` clause to signature
- Javadoc includes `@throws` annotations

**ProviderAdapter Integration**:
- ✅ **No changes needed** - ProviderAdapter returns prediction with all schema fields
- ✅ Checked exceptions preserved in prediction output
- ✅ Existing `_build_java_code` logic works unchanged

**Example**:
```python
# Before integration
impl_json = await self.provider.generate_structured(...)
checked_exceptions = impl_json.get("exception_handling", {}).get("checked_exceptions", [])

# After integration
prediction = await self.adapter(...)
impl_json = {k: v for k, v in prediction.__dict__.items() if not k.startswith("_")}
checked_exceptions = impl_json.get("exception_handling", {}).get("checked_exceptions", [])
# ✅ Same extraction logic works
```

---

### 3. Generics Syntax

**Challenge**: Java generics require careful escaping and validation.

**Current Implementation** (lines 297-328):
- Schema includes `generics` array with `type_parameter` and `bounds`
- `_build_java_code` constructs generic string: `<T extends Comparable<T>>`
- Inserted after access modifier in signature

**ProviderAdapter Integration**:
- ✅ **No changes needed** - ProviderAdapter preserves generics in prediction
- ✅ XGrammar constraints ensure valid generic syntax
- ✅ Existing signature construction logic works unchanged

**Example**:
```python
# Before integration
impl_json = await self.provider.generate_structured(...)
generics = impl_json.get("generics", [])

# After integration
prediction = await self.adapter(...)
impl_json = {k: v for k, v in prediction.__dict__.items() if not k.startswith("_")}
generics = impl_json.get("generics", [])
# ✅ Same extraction logic works
```

---

### 4. Javac Validation

**Current Implementation** (lines 430-477):
- `_validate_java_syntax()` wraps method in class
- Runs `javac -Xlint:none` to check syntax
- Returns `(is_valid, error_output)` tuple

**ProviderAdapter Integration**:
- ✅ **No changes needed** - validation runs on final code string
- ✅ ProviderAdapter output converts to code via `_build_java_code`
- ✅ Existing validation logic works unchanged

**Validation Flow**:
```
ProviderAdapter → impl_json → _build_java_code → complete_code → _validate_java_syntax
                                                                     ↓
                                                            (is_valid, error_output)
```

---

### 5. Helper Methods

**Current Implementation** (lines 408-427):
- Schema includes `helper_methods` array
- Each helper has: `name`, `signature`, `body`, `access_modifier`
- Appended after main method in code

**ProviderAdapter Integration**:
- ✅ **No changes needed** - ProviderAdapter returns complete prediction with helpers
- ✅ Existing `_build_java_code` logic handles helpers
- ✅ No risk to helper method generation

---

### 6. Variable Declarations with `final`

**Java-Specific Feature** (lines 337-352):
- Variables can be `final` (immutable)
- Schema includes `is_final` boolean
- Code generation: `final int x = 0;` vs `int x = 0;`

**ProviderAdapter Integration**:
- ✅ **No changes needed** - ProviderAdapter preserves `is_final` in prediction
- ✅ Existing variable declaration logic works unchanged

---

## Testing Strategy

### Phase 1 Testing

**Objective**: Verify ProviderAdapter integration preserves existing Java-specific behavior.

**Tests**:
1. **Existing E2E Tests** (must pass unchanged):
   - `tests/integration/test_java_pipeline_e2e.py` (if exists)
   - Unit tests for `JavaGenerator`

2. **Java-Specific Validation**:
   - ✅ Generics syntax (e.g., `<T extends Comparable<T>>`)
   - ✅ Checked exceptions in signature (`throws IOException`)
   - ✅ Annotations (`@Override`, `@SuppressWarnings`)
   - ✅ Final variables (`final int x = 0;`)
   - ✅ Helper methods generation
   - ✅ Javac syntax validation

3. **Performance Validation**:
   - Compare latency: old vs new
   - Target: <10% overhead

4. **Resource Tracking**:
   - Verify token counts are tracked
   - Verify LLM call counts are tracked

**Success Criteria**:
- ✅ All existing tests pass
- ✅ Performance within 10% of baseline
- ✅ Resource tracking works
- ✅ Java-specific features (generics, exceptions) work correctly

---

### Test Commands

```bash
# Step 1: Commit changes first (MANDATORY)
git add lift_sys/codegen/languages/java_generator.py
git commit -m "feat: Integrate Java generator with DSPy ProviderAdapter"

# Step 2: Kill old tests
pkill -f pytest

# Step 3: Run Java E2E tests (if exist)
uv run pytest tests/integration/test_java_pipeline_e2e.py -v \
  > /tmp/java_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Alternative: Run all integration tests
uv run pytest tests/integration/ -k java -v \
  > /tmp/java_dspy_integration_test_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# Step 4: Wait and check
wait
tail -100 /tmp/java_dspy_integration_test_*.log
```

---

## Estimated Effort

### Breakdown

| Task | Estimated Time | Rationale |
|------|---------------|-----------|
| **Code Changes** | 30 minutes | Minimal (~40 lines total) |
| **Testing** | 1-2 hours | Run tests, verify Java features |
| **Documentation** | 30 minutes | Update comments, document issues |
| **Validation** | 1 hour | Verify generics, exceptions, performance |

**Total**: **3-4 hours**

### Confidence Level

**High Confidence** (90%+):
- Pattern proven with TypeScript (commit 1186ca7)
- Minimal changes required (~40 lines)
- No schema modifications needed
- Java-specific features handled by existing code

**Risks**:
- ⚠️ **Low Risk**: Javac validation edge cases
- ⚠️ **Low Risk**: Performance regression (unlikely, <10ms overhead expected)

---

## Implementation Checklist

### Pre-Implementation
- [ ] Read this document completely
- [ ] Review TypeScript integration (commit 1186ca7)
- [ ] Verify DSPy dependencies installed (`uv pip list | grep dspy`)

### Code Changes
- [ ] Import ProviderAdapter and ProviderConfig (2 lines)
- [ ] Add adapter initialization in `__init__` (10 lines)
- [ ] Replace provider call with adapter in `_generate_implementation` (~25 lines)
- [ ] Add explanatory comments (DSPy Architecture Integration)

### Testing
- [ ] Commit changes before testing (MANDATORY)
- [ ] Kill old tests (`pkill -f pytest`)
- [ ] Run Java E2E tests (if exist)
- [ ] Run unit tests for JavaGenerator
- [ ] Verify resource tracking (token counts logged)
- [ ] Validate performance (<10% overhead)

### Validation
- [ ] Test generics syntax (`<T extends Comparable<T>>`)
- [ ] Test checked exceptions (`throws IOException`)
- [ ] Test annotations (`@Override`)
- [ ] Test final variables (`final int x = 0;`)
- [ ] Test helper methods generation
- [ ] Test javac validation (syntax checking)

### Documentation
- [ ] Update comments in java_generator.py
- [ ] Create `DSPY_JAVA_INTEGRATION_RESULTS.md` with findings
- [ ] Document any issues encountered
- [ ] Commit documentation changes

---

## Risk Mitigation

### Risk 1: Schema Field Mismatch

**Scenario**: ProviderAdapter returns prediction missing Java-specific fields (generics, exceptions).

**Mitigation**:
- ProviderAdapter passes schema transparently → XGrammar guarantees compliance
- Fallback: If prediction missing fields, existing code uses defaults (empty arrays)
- Test coverage: Validate all Java-specific fields present in prediction

**Contingency**: If mismatch occurs, investigate ProviderAdapter prediction extraction logic.

---

### Risk 2: Javac Validation Failures

**Scenario**: Generated code passes XGrammar but fails javac validation.

**Mitigation**:
- Existing retry logic (max_retries=3) already handles this
- ProviderAdapter doesn't change validation flow
- Test coverage: Verify retry logic works with adapter

**Contingency**: If validation fails, inspect generated code for syntax errors not caught by XGrammar.

---

### Risk 3: Performance Regression

**Scenario**: ProviderAdapter adds significant latency overhead.

**Mitigation**:
- ProviderAdapter design target: <10ms overhead
- TypeScript integration: Validate performance before Java
- Test coverage: Measure latency before/after integration

**Contingency**: If overhead >10%, profile ProviderAdapter and optimize bottleneck.

---

## Java-Specific Edge Cases

### Edge Case 1: Nested Generics

**Example**: `List<Map<String, List<Integer>>>`

**Current Handling**: Schema supports nested generics via string-based `type_parameter` and `bounds`.

**ProviderAdapter Impact**: ✅ None - schema passed as-is, XGrammar handles nesting.

**Test**: Generate method with nested generic types.

---

### Edge Case 2: Varargs Parameters

**Example**: `public void log(String format, Object... args)`

**Current Handling**: Type resolver supports varargs via `type_hint` string.

**ProviderAdapter Impact**: ✅ None - type hints passed to schema unchanged.

**Test**: Generate method with varargs parameter.

---

### Edge Case 3: Multiple Checked Exceptions

**Example**: `throws IOException, SQLException, TimeoutException`

**Current Handling**: Schema includes array of exception names, joined with commas.

**ProviderAdapter Impact**: ✅ None - exception array preserved in prediction.

**Test**: Generate method throwing 3+ checked exceptions.

---

### Edge Case 4: Anonymous Inner Classes

**Example**: `new Runnable() { public void run() { ... } }`

**Current Handling**: Generated as part of body statements (string code).

**ProviderAdapter Impact**: ✅ None - body statements passed as-is.

**Test**: Generate method creating anonymous inner class.

---

## Comparison with TypeScript Integration

### Similarities

| Aspect | TypeScript | Java |
|--------|-----------|------|
| **Import Changes** | 2 lines | 2 lines |
| **Adapter Init** | 10 lines | 10 lines |
| **Provider Call Replacement** | ~25 lines | ~25 lines |
| **Total Changes** | ~40 lines | ~40 lines |
| **Schema Handling** | Transparent | Transparent |
| **Validation** | TSC syntax check | Javac syntax check |
| **Risk Level** | Low | Low |

---

### Differences

| Aspect | TypeScript | Java |
|--------|-----------|------|
| **Async Detection** | Check `await` in body | Not applicable (Java async via callbacks/futures) |
| **Exception Handling** | Throw only (no checked) | Checked + unchecked (schema field) |
| **Generics** | Simple (`<T>`) | Complex (`<T extends Comparable<T>>`) |
| **Imports** | ES6 modules | Package imports + static imports |
| **Syntax Validator** | `tsc --noEmit` | `javac -Xlint:none` |

**Conclusion**: Java integration slightly more complex due to generics/exceptions, but **no additional risk** - schema already handles these.

---

## Future Enhancements

### Phase 2: DSPy Signatures (Future)

**Objective**: Replace hardcoded prompts with declarative DSPy signatures.

**Java-Specific Considerations**:
1. **Generics in Signatures**:
   ```python
   class JavaImplementationSignature(dspy.Signature):
       """Generate Java implementation with generics support."""

       generics: list[dict] = dspy.InputField(desc="Generic type parameters")
       checked_exceptions: list[str] = dspy.InputField(desc="Checked exceptions")
       implementation: dict = dspy.OutputField(desc="Java implementation JSON")
   ```

2. **Exception Specification**:
   - Input field for checked exceptions
   - Output validation ensures exceptions match signature

3. **Annotation Metadata**:
   - Input field for required annotations
   - Output includes annotation placement

**Timeline**: After Phase 1 validation across all languages

---

### Phase 3: Validation Hooks (Future)

**Objective**: Integrate H9 ValidationHooks for result validation.

**Java-Specific Validators**:
1. **Javac Syntax Validator** (already exists, wrap in ValidationHook)
2. **Generic Bounds Validator** (verify type parameter bounds are valid)
3. **Exception Consistency Validator** (verify thrown exceptions match signature)
4. **Annotation Applicability Validator** (verify annotations valid for target)

**Example**:
```python
async def javac_syntax_validator(
    context: RunContext,
    implementation: dict
) -> ValidationResult:
    code = build_java_code(implementation)
    is_valid, error = validate_java_syntax(code)

    if is_valid:
        return ValidationResult(status="PASS", message="Valid Java")
    else:
        return ValidationResult(
            status="FAIL",
            message="Javac compilation error",
            details={"javac_error": error}
        )
```

**Timeline**: After Phase 2

---

## Rollout Strategy

### Step 1: TypeScript Integration Complete ✅
- Commit: 1186ca7
- Status: Done
- Lessons learned: Documented in `DSPY_TYPESCRIPT_INTEGRATION.md`

### Step 2: Java Integration (This Document)
- Estimated: 3-4 hours
- Dependencies: TypeScript results validate pattern
- Success criteria: All tests pass, Java features work

### Step 3: Rust Integration
- Pattern: Same as TypeScript/Java
- Estimated: 3-4 hours
- Rust-specific: Ownership/borrowing annotations in schema

### Step 4: Go Integration
- Pattern: Same as TypeScript/Java
- Estimated: 3-4 hours
- Go-specific: Error returns, goroutines in schema

**Total Effort for All Languages**: 1.5-2 days

---

## Questions & Answers

### Q: Will generics break with ProviderAdapter?
**A**: No - ProviderAdapter passes schema transparently to XGrammar. Generics are validated by XGrammar constraints. TypeScript integration (simpler generics) validates this pattern.

### Q: What about checked exceptions?
**A**: Schema includes `exception_handling.checked_exceptions` array. ProviderAdapter returns prediction with this field intact. Existing code extracts and formats exceptions unchanged.

### Q: Will javac validation still work?
**A**: Yes - validation runs on final code string (after `_build_java_code`). ProviderAdapter doesn't change validation flow.

### Q: What if prediction is missing Java-specific fields?
**A**: Unlikely - XGrammar guarantees schema compliance. But existing code already has defaults (empty arrays) for missing fields. No additional risk.

### Q: Performance impact on Java generation?
**A**: <10ms expected (ProviderAdapter overhead target). Actual impact measured in testing phase. TypeScript integration validates performance.

---

## References

### Internal Documents
- **TypeScript Integration**: `docs/planning/DSPY_TYPESCRIPT_INTEGRATION.md`
- **Architecture Proposal**: `docs/planning/DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md`
- **Hole Inventory**: `docs/planning/HOLE_INVENTORY.md`
- **Session State**: `docs/planning/SESSION_STATE.md`

### Code Files
- **Java Generator**: `lift_sys/codegen/languages/java_generator.py`
- **Java Schema**: `lift_sys/codegen/languages/java_schema.py`
- **Java Type Resolver**: `lift_sys/codegen/languages/java_types.py`
- **ProviderAdapter**: `lift_sys/dspy_signatures/provider_adapter.py`
- **TypeScript Generator**: `lift_sys/codegen/languages/typescript_generator.py` (reference)

### External Resources
- **DSPy Documentation**: https://dspy-docs.vercel.app/
- **Java Language Spec**: https://docs.oracle.com/javase/specs/
- **XGrammar**: https://github.com/mlc-ai/xgrammar

---

## Document Status

**Status**: ACTIVE (Planning)
**Owner**: Architecture Integration Team
**Next Steps**:
1. Review and approve this document
2. Execute implementation (3-4 hours)
3. Document results in `DSPY_JAVA_INTEGRATION_RESULTS.md`
4. Apply pattern to Rust and Go generators

**Last Updated**: 2025-10-23
