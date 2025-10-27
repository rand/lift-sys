---
track: dspy
document_type: failure_analysis
status: complete
priority: P0
completion: 100%
phase: A
last_updated: 2025-10-23
session_protocol: |
  For new Claude Code session:
  1. Root cause analysis of 17/21 failed E2E tests (Rust, Go, Java)
  2. Issue: Modal XGrammar not enforcing schemas (missing required fields)
  3. TypeScript passed only because it used cached fixtures (not live API)
  4. Led to schema fix (af59c53) and eventual llguidance migration
  5. Historical record - use for understanding Modal API issues
related_docs:
  - docs/tracks/dspy/DSPY_INTEGRATION_FINAL_RESULTS.md
  - docs/tracks/infrastructure/MODAL_ENDPOINT_ISSUES.md
  - docs/tracks/infrastructure/LLGUIDANCE_MIGRATION_PLAN.md
---

# DSPy Integration Test Failures - Root Cause Analysis

**Date**: 2025-10-23
**Status**: Under Investigation
**Affected**: Rust (6/6 failed), Go (5/5 failed), Java (6/6 failed)

---

## Executive Summary

All 17 E2E tests failed for Rust, Go, and Java generators with DSPy ProviderAdapter integration. **TypeScript tests passed (4/4) only because they used cached fixtures**, not live Modal API calls.

### Root Cause

**Live Modal API responses have a different JSON structure than expected**. The schemas are defined correctly, but the actual XGrammar-constrained generation is returning responses that don't match the schema definition.

---

## Failure Analysis

### 1. Missing 'implementation' Key (10/17 tests)

**Error**: `ValueError: Missing 'implementation' key in JSON`

**Affected**:
- Rust: 5 tests (vector_operations, result_error_handling, string_manipulation, ownership_borrowing, schema_compliance)
- Go: 3 tests (slice_operations, map_operations, goroutines_channels)
- Java: 3 tests (generic_method, stream_operations, schema_compliance)

**What's happening**:
1. Generator calls ProviderAdapter with schema:
   ```python
   prediction = await self.adapter(
       prompt=prompt,
       schema=RUST_GENERATION_SCHEMA,  # Expects { "implementation": {...} }
       ...
   )
   ```

2. ProviderAdapter calls Modal's `generate_structured()` with schema

3. Modal returns JSON, but **without top-level 'implementation' key**

4. Prediction object created from response

5. Generator extracts dict from prediction:
   ```python
   impl_json = {k: v for k, v in prediction.__dict__.items() if not k.startswith("_")}
   ```

6. Validation fails:
   ```python
   if "implementation" not in impl_json:
       raise ValueError("Missing 'implementation' key in JSON")
   ```

**Expected response structure** (from schema):
```json
{
  "implementation": {
    "body_statements": [...],
    "variables": [...],
    "imports": [...]
  }
}
```

**Actual response structure** (inferred from error):
```json
{
  "body_statements": [...],
  "variables": [...],
  "imports": [...]
}
```

**The Modal API is returning the `implementation` object directly, without wrapping it!**

---

### 2. Modal API Timeouts (5/17 tests)

**Error**: `httpx.HTTPStatusError: Client error '408 Request Timeout'`

**Affected**:
- Rust: 1 test (simple_addition)
- Go: 1 test (simple_addition)
- Java: 2 tests (simple_addition, exception_handling)

**Cause**: Modal backend timing out or cancelling requests

**Error message**:
```
ValueError: Modal API error (HTTP 408): Missing request, possibly due to expiry or cancellation
```

**Possible reasons**:
1. Modal endpoint overloaded
2. LLM generation taking too long
3. Network issues between test environment and Modal

---

### 3. Network Timeout (1/17 tests)

**Error**: `httpx.ReadTimeout`

**Affected**: Java (list_operations)

**Cause**: HTTP client timeout waiting for Modal response

---

### 4. Empty IR Response (1/17 tests)

**Error**: `ValueError: All 1 candidates failed generation. Errors: ['Failed to generate IR with constrained generation: ']`

**Affected**: Go (error_handling)

**Cause**: Modal returned empty string

---

##  Why TypeScript Passed

TypeScript tests passed because they're using **response fixtures** instead of making live Modal calls. Looking at `tests/fixtures/code_responses.json`:

```json
{
  "typescript_pipeline_array_filtering": {
    "response": {
      "source_code": "...",  // Final generated code (string)
      "metadata": {...}
    }
  }
}
```

The fixture contains the **final `GeneratedCode` object**, not the raw JSON from Modal's XGrammar generation. This means:

1. Test retrieves cached `GeneratedCode` from fixture
2. No live Modal call made
3. No schema validation happens
4. Test passes ✅

**Rust/Go/Java tests made LIVE calls** because they don't have fixtures cached, so they hit the actual schema mismatch bug.

---

## Comparison: Old vs New Code Flow

### Old Flow (Before DSPy Integration)

**TypeScript Generator (example)**:
```python
# OLD
if hasattr(self.provider, "generate_structured") and self.provider.capabilities.structured_output:
    impl_json = await self.provider.generate_structured(
        prompt=prompt,
        schema=TYPESCRIPT_GENERATION_SCHEMA,
        ...
    )
    return impl_json  # Dict returned directly

response = await self.provider.generate_text(...)
return self._extract_json(response)  # Extract JSON from text
```

**Modal Provider's `generate_structured()`** returns:
```json
{
  "implementation": {
    "body_statements": [...],
    ...
  }
}
```

### New Flow (With DSPy Integration)

**Generator**:
```python
# NEW
prediction = await self.adapter(
    prompt=prompt,
    schema=RUST_GENERATION_SCHEMA,
    ...
)

impl_json = {k: v for k, v in prediction.__dict__.items() if not k.startswith("_")}
```

**ProviderAdapter**:
```python
response_dict = await self.provider.generate_structured(...)  # Returns dict
return self._dict_to_prediction(response_dict, signature=None)
```

**`_dict_to_prediction()`**:
```python
def _dict_to_prediction(self, response: dict, signature=None):
    if signature is not None:
        # Filter to output fields
        ...
    else:
        # No signature, use all fields
        return dspy.Prediction(**response)
```

**The issue**: If Modal is returning:
```json
{
  "body_statements": [...],
  "variables": [...],
  ...
}
```

Then `dspy.Prediction(**response)` creates a prediction with `body_statements`, `variables`, etc. as attributes, but NO `implementation` attribute!

---

## Root Cause Hypothesis

**Two possibilities**:

### Hypothesis 1: Modal XGrammar Ignoring Top-Level Wrapper

Modal's XGrammar engine might be optimizing away the top-level `"implementation"` wrapper and returning the nested object directly.

**Evidence**:
- Schema defines `"implementation"` as a property
- But actual response doesn't have it
- This is consistent across all 3 languages

### Hypothesis 2: Schema Not Being Respected

Modal's `generate_structured()` might not be properly enforcing the JSON schema.

**Evidence**:
- Schemas are correctly defined with `"implementation"` at top level
- But responses don't match
- XGrammar should enforce exact schema compliance

---

## Investigation Plan

### Step 1: Add Debug Logging

Modify ProviderAdapter to log the actual response from Modal:

```python
# In provider_adapter.py, line 179
response_dict = await self.provider.generate_structured(...)

# ADD DEBUG LOGGING
import json
print(f"[DEBUG] Modal response: {json.dumps(response_dict, indent=2)}")

return self._dict_to_prediction(response_dict, signature)
```

### Step 2: Test with Single Rust Test

Run ONE Rust test with debug logging to see actual Modal response:

```bash
uv run pytest tests/integration/test_rust_pipeline_e2e.py::test_nlp_to_rust_vector_operations -v -s
```

### Step 3: Compare TypeScript vs Rust Schema

Check if there's any subtle difference in schema structure:

```bash
# Compare schemas
diff lift_sys/codegen/languages/typescript_schema.py \
     lift_sys/codegen/languages/rust_schema.py
```

### Step 4: Test Modal Directly

Create a minimal test script that calls Modal with the schema directly:

```python
import asyncio
from lift_sys.providers import ModalProvider
from lift_sys.codegen.languages.rust_schema import RUST_GENERATION_SCHEMA

async def test_modal():
    provider = ModalProvider(endpoint_url="https://rand--generate.modal.run")
    response = await provider.generate_structured(
        prompt="Generate Rust implementation for: add two numbers",
        schema=RUST_GENERATION_SCHEMA,
        max_tokens=2000,
        temperature=0.3,
    )
    print(f"Response keys: {list(response.keys())}")
    print(f"Full response: {json.dumps(response, indent=2)}")

asyncio.run(test_modal())
```

---

## Proposed Fixes

### Fix 1: Handle Both Schema Formats

Modify generators to accept BOTH formats:

```python
# In rust_generator.py (and similar for Go/Java)
impl_json = {k: v for k, v in prediction.__dict__.items() if not k.startswith("_")}

# FIX: Check if 'implementation' is missing but expected fields are present
if "implementation" not in impl_json and "body_statements" in impl_json:
    # Modal returned unwrapped format, wrap it
    impl_json = {"implementation": impl_json}

self._validate_implementation(impl_json)
```

### Fix 2: Update Schemas to Match Modal's Actual Behavior

If Modal is consistently returning unwrapped format, update schemas to match:

```python
# Change schema from:
{
  "properties": {
    "implementation": {
      "type": "object",
      "properties": {
        "body_statements": [...],
        ...
      }
    }
  }
}

# To:
{
  "properties": {
    "body_statements": [...],
    ...
  }
}
```

**But this breaks TypeScript compatibility!** TypeScript expects wrapped format.

### Fix 3: Investigate Why TypeScript Works (Recommended)

**Action**: Check if TypeScript generator has special handling we're missing.

**Method**: Read TypeScript generator code carefully, compare with Rust/Go/Java.

---

## Next Steps

1. ✅ **Document failures** (this document)
2. ⏳ **Add debug logging** to ProviderAdapter
3. ⏳ **Run single test with logging** to see actual Modal response
4. ⏳ **Compare TypeScript vs Rust schemas** for differences
5. ⏳ **Implement Fix 1** (handle both formats) if confirmed
6. ⏳ **Re-run all tests** to validate fix
7. ⏳ **Update integration results** document

---

## Modal API Reliability

Beyond the schema issue, **5 tests hit Modal timeouts** (HTTP 408). This indicates:

1. **Modal backend instability** - requests timing out or being cancelled
2. **LLM generation too slow** - exceeding timeout threshold
3. **Network issues** - connectivity problems between test env and Modal

**Recommendations**:
- Increase timeout configuration for Modal calls
- Add retry logic with exponential backoff
- Monitor Modal endpoint health
- Consider caching more responses to avoid live calls during testing

---

## Timeline

- **Test execution**: 29 minutes total (tests ran in parallel)
- **Average per test**: ~5 minutes
- **Modal timeouts**: 5 tests (30% of failures)
- **Schema mismatches**: 10 tests (59% of failures)

---

**Status**: Awaiting debug logging results to confirm root cause
**Owner**: Architecture Integration Team
**Priority**: P0 (Blocking Phase A completion)
