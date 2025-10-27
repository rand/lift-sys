---
track: dspy
document_type: integration_guide
status: in_progress
priority: P1
completion: 60%
phase: A
last_updated: 2025-10-23
session_protocol: |
  For new Claude Code session:
  1. TypeScript generator is partially integrated with DSPy ProviderAdapter
  2. Phase 1 (minimal integration) complete - commit 1186ca7
  3. Next: Full DSPy signature migration (Phase 2)
  4. Use this as reference pattern for other language integrations
  5. Test changes with: uv run pytest tests/unit/test_typescript_generator.py
related_docs:
  - docs/tracks/dspy/SESSION_STATE.md
  - docs/tracks/dspy/HOLE_INVENTORY.md
  - lift_sys/dspy_signatures/provider_adapter.py
  - docs/tracks/dspy/DSPY_RUST_INTEGRATION.md
  - docs/tracks/dspy/DSPY_GO_INTEGRATION.md
  - docs/tracks/dspy/DSPY_JAVA_INTEGRATION.md
---

# DSPy Architecture Integration: TypeScript Generator

**Date**: 2025-10-23
**Status**: In Progress
**Phase**: Architecture Integration (Phase A)

---

## Overview

This document describes the integration of the TypeScript code generator with the new DSPy + Pydantic AI architecture. This serves as a **proof-of-concept** for integrating all language generators.

**Goal**: Validate DSPy architecture works end-to-end before migrating all 4 languages.

---

## Integration Strategy

### Phase 1: Minimal Integration (Current)

**Objective**: Replace direct provider calls with ProviderAdapter while preserving existing behavior.

**Changes**:
1. **Import DSPy Components**:
   - `ProviderAdapter` (H1) - Dual routing between Modal/Best Available
   - `ProviderConfig` - Generation configuration

2. **Update `__init__`**:
   ```python
   from lift_sys.dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig

   # Create adapter from provider
   self.adapter = ProviderAdapter(
       provider=provider,
       config=ProviderConfig(
           max_tokens=2000,
           temperature=0.3,
           use_xgrammar=True  # Enable XGrammar constraints
       )
   )
   ```

3. **Update `_generate_implementation`**:
   ```python
   # OLD: Direct provider call
   impl_json = await self.provider.generate_structured(
       prompt=prompt,
       schema=TYPESCRIPT_GENERATION_SCHEMA,
       ...
   )

   # NEW: ProviderAdapter call
   prediction = await self.adapter(
       prompt=prompt,
       schema=TYPESCRIPT_GENERATION_SCHEMA,  # XGrammar constraints
       max_tokens=2000,
       temperature=0.3
   )

   # Extract JSON from prediction
   impl_json = prediction.__dict__
   ```

**Benefits**:
- ✅ Resource tracking (token counts, LLM calls) via H14
- ✅ Dual routing capability (Modal for XGrammar, best available otherwise)
- ✅ Foundation for validation hooks (H9)
- ✅ Backward compatible (tests should pass unchanged)

**Risks**:
- None - ProviderAdapter is designed to be drop-in compatible

---

### Phase 2: DSPy Signatures (Future)

**Objective**: Replace hardcoded prompts with declarative DSPy signatures.

**Approach**:
1. Define `TypeScriptImplementationSignature(dspy.Signature)`:
   ```python
   class TypeScriptImplementationSignature(dspy.Signature):
       """Generate TypeScript implementation from specification."""

       # Inputs
       intent: str = dspy.InputField(desc="High-level intent/summary")
       signature: str = dspy.InputField(desc="TypeScript function signature")
       constraints: list[str] = dspy.InputField(desc="Constraints to satisfy")
       effects: list[str] = dspy.InputField(desc="Operational steps")

       # Output
       implementation: dict = dspy.OutputField(desc="JSON implementation")
   ```

2. Use DSPy modules with schema parameter:
   ```python
   # Create custom module that supports schema
   class SchemaConstrainedPredict(dspy.Predict):
       def forward(self, **kwargs):
           # Pass schema to LM via ProviderAdapter
           return super().forward(**kwargs, schema=self.schema)

   # Use in generator
   predictor = SchemaConstrainedPredict(
       TypeScriptImplementationSignature,
       schema=TYPESCRIPT_GENERATION_SCHEMA
   )
   result = predictor(
       intent=ir.intent.summary,
       signature=ts_signature,
       constraints=constraints,
       effects=effects
   )
   ```

**Benefits**:
- ✅ Declarative specifications (easier to reason about)
- ✅ Optimizable with MIPROv2/COPRO (H8)
- ✅ Composable for complex workflows
- ✅ Better provenance tracking

**Timeline**: After Phase 1 validation

---

### Phase 3: Validation Hooks (Future)

**Objective**: Integrate H9 ValidationHooks for result validation.

**Approach**:
1. Define validation hooks:
   ```python
   from lift_sys.dspy_signatures.validation_hooks import ValidationHook, ValidationResult

   async def typescript_syntax_validator(
       context: RunContext,
       implementation: dict
   ) -> ValidationResult:
       # Validate TypeScript syntax with tsc
       code = build_typescript_code(implementation)
       is_valid, error = validate_typescript_syntax(code)

       if is_valid:
           return ValidationResult(status="PASS", message="Valid TypeScript")
       else:
           return ValidationResult(
               status="FAIL",
               message="Invalid TypeScript syntax",
               details={"tsc_error": error}
           )
   ```

2. Register hooks in generator:
   ```python
   self.validation_hooks = [
       typescript_syntax_validator,
       schema_compliance_validator,
       execution_safety_validator
   ]
   ```

3. Run hooks after generation:
   ```python
   from lift_sys.dspy_signatures.validation_hooks import run_validators

   validation_results = await run_validators(
       hooks=self.validation_hooks,
       context=context,
       implementation=impl_json
   )

   if any(r.status == "FAIL" for r in validation_results):
       # Retry or raise error
       ...
   ```

**Benefits**:
- ✅ Structured validation (vs ad-hoc checks)
- ✅ Composable validators (chain-of-responsibility)
- ✅ Better error messages
- ✅ Retry logic integration

**Timeline**: After Phase 2

---

## Testing Strategy

### Phase 1 Testing

**Objective**: Verify ProviderAdapter integration preserves existing behavior.

**Tests**:
1. **Existing E2E Tests** (must pass unchanged):
   - `tests/integration/test_typescript_pipeline_e2e.py`
   - All 3 tests (simple addition, async, imports)

2. **Performance Validation**:
   - Compare latency: old vs new
   - Target: <10% overhead

3. **Resource Tracking**:
   - Verify token counts are tracked
   - Verify LLM call counts are tracked

**Success Criteria**:
- ✅ All existing tests pass
- ✅ Performance within 10% of baseline
- ✅ Resource tracking works

---

## Implementation Plan

### Step 1: Update TypeScriptGenerator ✅

**File**: `lift_sys/codegen/languages/typescript_generator.py`

**Changes**:
- [ ] Import ProviderAdapter, ProviderConfig
- [ ] Create adapter in `__init__`
- [ ] Update `_generate_implementation` to use adapter
- [ ] Extract JSON from `dspy.Prediction`

**Lines Changed**: ~20 lines (minimal)

### Step 2: Run Tests

**Commands**:
```bash
# Commit changes first (MANDATORY)
git add lift_sys/codegen/languages/typescript_generator.py
git commit -m "feat: Integrate TypeScript generator with DSPy ProviderAdapter"

# Kill old tests
pkill -f pytest

# Run TypeScript E2E tests
uv run pytest tests/integration/test_typescript_pipeline_e2e.py -v \
  > /tmp/typescript_dspy_integration_test.log 2>&1 &

# Wait and check
wait
tail -100 /tmp/typescript_dspy_integration_test.log
```

### Step 3: Validate Results

**Check**:
1. Test results (all pass?)
2. Performance (latency vs baseline)
3. Resource tracking (tokens/calls logged?)

### Step 4: Document Findings

**Create**: `docs/planning/DSPY_TYPESCRIPT_INTEGRATION_RESULTS.md`

**Include**:
- Test results
- Performance comparison
- Lessons learned
- Issues encountered
- Recommendations for other languages

---

## Migration Pattern for Other Languages

Once TypeScript integration is validated, apply the same pattern to:
1. **RustGenerator** (2-3 hours)
2. **GoGenerator** (2-3 hours)
3. **JavaGenerator** (2-3 hours)

**Total Effort**: 1 day for all 4 languages

---

## Future Enhancements

### Optimization (H8)

After all generators use DSPy signatures:
- Run MIPROv2 to optimize prompts
- Compare quality before/after
- Deploy optimized signatures

### Confidence Calibration (H12)

- Integrate confidence scoring
- Use for retry logic
- Track confidence vs actual quality

### Feature Flags (H13)

- Enable gradual rollout
- A/B test DSPy vs old approach
- Percentage-based deployment

---

## Questions & Answers

**Q: Will this break backward compatibility?**
A: No - ProviderAdapter is designed to be drop-in compatible. Existing tests should pass unchanged.

**Q: What if performance degrades?**
A: ProviderAdapter has <10ms overhead target (from design). If we see more, investigate and optimize.

**Q: Do we need DSPy installed?**
A: Yes - add `dspy` to `pyproject.toml` if not already present.

**Q: What about providers without structured output?**
A: ProviderAdapter handles this - routes to `generate_text()` for providers without XGrammar support.

---

**Document Status**: ACTIVE
**Owner**: Architecture Integration Team
**Next Update**: After Phase 1 completion
