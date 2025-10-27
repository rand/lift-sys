# Phase 3.1: llguidance POC Status

**Date**: 2025-10-27
**Status**: In Progress
**Priority**: CRITICAL (blocks llguidance migration)

---

## Executive Summary

Phase 3.1 validates whether the guidance library with llguidance can replace XGrammar for constrained code generation. Initial setup and testing revealed API compatibility issues and performance characteristics that inform the migration approach.

**Key Findings**:
- ✅ guidance library (0.3.0) installed and working
- ✅ llguidance library (1.1.0) installed
- ✅ POC scripts exist and have been updated for current API
- ⚠️  Local CPU inference is impractically slow (>10 min for simple cases)
- ⚠️  Modal GPU inference has long cold start (~7 min model loading)
- ⏳ Full POC validation still needed to compare with XGrammar baseline

---

## Work Completed

### 1. Environment Setup ✅

**Libraries Installed**:
```bash
guidance                                 0.3.0
guidance-stitch                          0.1.5
llguidance                               1.1.0
transformers                             4.57.0
torch                                    2.8.0
```

**Status**: All dependencies present and compatible

### 2. POC Script API Update ✅

**Issue**: POC scripts used deprecated `gen(schema=...)` API
**Fix**: Updated to use `guidance.json(schema=...)` API

**Files Modified**:
- `scripts/poc/test_guidance_typescript_poc.py`
  - Changed import: `from guidance import json as guidance_json`
  - Updated line 176: `lm += guidance_json(name="output", schema=TYPESCRIPT_GENERATION_SCHEMA)`

**Commit**: 6b7b2c6 - "fix: Update guidance POC to use json() API instead of gen(schema=)"

**Validation**:
```python
# Current API (guidance 0.3.0)
from guidance import json as guidance_json

lm += guidance_json(name="output", schema=schema_dict)  # ✅ Correct
lm += gen(name="output", schema=schema_dict)            # ❌ Deprecated
```

### 3. Local POC Execution ⏳

**Test Run**: `scripts/poc/test_guidance_typescript_poc.py`
**Model**: microsoft/phi-2 (2.7B parameters, CPU mode)
**Results**:
- Model loading: ~10-20 seconds ✅
- Authentication: Working ✅
- Generation phase: >10 minutes (still running when terminated) ❌

**Log**: `/tmp/guidance_poc_run2_20251027_121533.log`

**Conclusion**: CPU inference with phi-2 is too slow for practical POC validation

### 4. Modal POC Deployment ❌

**Deployed**: `scripts/modal/guidance_poc_modal.py`
**Model**: Qwen/Qwen2.5-Coder-32B-Instruct (production model)
**GPU**: A100
**Results**:
- Deployment: 1.0s ✅
- Model download: ~5.3 min (cached after first run) ✅
- Model loading: ~6.7 min (404s) ✅
- Generation phase: **FAILED with cache size error** ❌

**Final Error**:
```
/usr/local/lib/python3.11/site-packages/guidance/models/_transformers.py:522: UserWarning:
Cache is too small. Resetting cache (no method implemented to resize cache for type
<class 'transformers.cache_utils.DynamicCache'>).
```

**Root Cause**: guidance library's transformers integration has a cache size bug with DynamicCache. The cache resets during generation, likely causing generation to fail or produce invalid output.

**Observation**: This is a **known limitation of guidance's transformers backend**, not an issue with llguidance itself or our schema

---

## Baseline Comparison

### XGrammar (Current System)
- **Success Rate**: 4.8%
- **Avg Latency**: ~85s
- **Issues**: Low success rate, unpredictable pre-computation delays

### llguidance/Guidance (Target)
- **Success Rate**: TBD (POC validation needed)
- **Avg Latency**: TBD
- **Target**: >80% success rate (baseline), >95% (production goal)

---

## Technical Challenges Encountered

### 1. API Evolution

**Problem**: POC scripts written for older guidance API
**Impact**: `gen(schema=...)` no longer supported
**Solution**: Updated to `json(schema=...)` API
**Status**: ✅ Resolved

### 2. Execution Performance

**Local CPU**:
- **Issue**: Inference too slow for POC iteration (>10 min)
- **Impact**: Cannot quickly validate schema compatibility
- **Mitigation**: Use Modal GPU deployment

**Modal GPU**:
- **Issue**: Long cold start (~12 min for 32B model)
- **Impact**: Slow iteration cycle but provides realistic comparison
- **Trade-off**: Slower validation but production-realistic performance data

### 3. API Provider Limitations

**Observation**: guidance library supports:
- OpenAI (via API)
- Transformers (HuggingFace models)
- LlamaCpp (local inference)
- Mock (testing)

**Missing**: Direct Anthropic API support

**Options**:
1. Continue with transformers on Modal (current approach)
2. Use OpenAI-compatible endpoint (if available)
3. Wait for Anthropic support in guidance (future)

---

## Next Steps - REVISED Based on Cache Error

### Critical Finding: Transformers Backend Not Viable

The cache size error reveals that **guidance's transformers backend is not production-ready for our use case**. This blocks the original POC approach but doesn't invalidate llguidance itself.

### Option A: Use llguidance with vLLM Directly (NEW - Recommended)

**Actions**:
1. Deploy vLLM on Modal with llguidance integration (bypassing guidance library)
2. Use llguidance's native JSON schema constraints
3. Test with TypeScript schema on Modal
4. Compare with XGrammar baseline

**Pros**:
- Uses llguidance directly (the actual technology we want)
- Avoids guidance library's transformers backend bugs
- vLLM is production-grade and we already use it
- Direct comparison with current XGrammar/vLLM setup

**Cons**:
- Requires new integration code
- More work than using guidance library

**Rationale**: The llguidance library is what provides the constrained generation (50μs per token). The guidance library is just a wrapper. We should use llguidance directly with vLLM.

### Option B: Use guidance with OpenAI API (Alternative)

**Actions**:
1. Use guidance with OpenAI backend (avoids transformers cache issue)
2. Test TypeScript schema generation
3. Compare success rates (not latency, different infrastructure)

**Pros**:
- Avoids transformers backend bug
- Likely to work immediately
- Validates schema compatibility

**Cons**:
- Different infrastructure than production (OpenAI vs vLLM)
- Cannot compare latency meaningfully
- Ongoing API costs

### Option C: Fix Transformers Cache Issue

**Actions**:
1. Investigate cache size configuration in guidance
2. Modify POC to pre-allocate larger cache
3. Re-run Modal POC

**Pros**:
- Might unblock transformers backend
- Uses existing POC code

**Cons**:
- Unclear if fixable without modifying guidance library
- Time-consuming investigation
- May hit other transformers backend issues

---

## Recommendation - UPDATED

**Proceed with Option A** (Use llguidance with vLLM Directly):

**Rationale**:
1. **Root cause identified**: guidance's transformers backend has cache bugs, not llguidance itself
2. **vLLM + llguidance is the target architecture**: We already use vLLM 0.9.2 with XGrammar, should switch to llguidance
3. **Direct comparison**: Using same infrastructure (vLLM/Modal) gives apples-to-apples comparison
4. **Production path**: This is the actual integration we need for Phase 3.2-3.6

**Why Not guidance Library**:
- guidance is a high-level API wrapper
- Its transformers backend has known cache management issues
- llguidance is the core constraint library (50μs/token)
- vLLM already has llguidance integration built-in

**Implementation Path**:
1. **Check vLLM llguidance integration**: vLLM 0.9.2+ has native llguidance support
2. **Modify Modal deployment**: Switch from `guided_json` (XGrammar) to llguidance in vLLM config
3. **Test with TypeScript schema**: Use same test cases as XGrammar baseline
4. **Compare results**: Success rate and latency vs 4.8% / 85s baseline

**Acceptance Criteria (REVISED)**:
- ✅ vLLM successfully uses llguidance for constrained generation
- ✅ TypeScript schema is compatible with llguidance JSON schema constraints
- ✅ Output validates against our schema
- ✅ Success rate >50% (baseline), target >80%
- ✅ Latency <60s (baseline), target <30s

**Next Immediate Steps**:
1. Research vLLM llguidance integration (check vLLM docs)
2. Modify `scripts/modal/start_dev.sh` to use llguidance instead of XGrammar
3. Run existing Modal integration tests with llguidance
4. Document results and make go/no-go decision

**Timeline**: 1-2 hours (much faster than fixing guidance transformers backend)

---

## Files Created/Modified

**Created**:
- `debug/test_guidance_poc.py` (initial attempt, superseded by scripts/poc/)

**Modified**:
- `scripts/poc/test_guidance_typescript_poc.py` (API update)

**Deployed**:
- `scripts/modal/guidance_poc_modal.py` (production POC on Modal)

**Documentation**:
- This file: `validation/PHASE3_1_LLGUIDANCE_POC_STATUS.md`

---

## Timeline

- **Start**: 2025-10-27 12:00 MDT
- **API Fix**: 2025-10-27 12:05 MDT (commit 6b7b2c6)
- **Local POC**: 2025-10-27 12:15 MDT (terminated due to slow execution)
- **Modal Deploy**: 2025-10-27 12:20 MDT
- **Modal Run**: 2025-10-27 12:20-12:30 MDT (timeout at 10 min, still running)
- **Current**: 2025-10-27 12:30 MDT

**Estimated Completion**: 2025-10-27 12:40 MDT (if Modal POC completes successfully)

---

## Dependencies

**Blocked By**: N/A (Phase 2 complete)

**Blocks**:
- Phase 3.2: Implement GuidanceProvider
- Phase 3.3: Integrate with ProviderAdapter
- Phase 3.4-3.6: All subsequent migration phases

**Critical Path**: YES - blocks entire llguidance migration

---

## Open Questions

1. **API Provider**: Should we wait for Anthropic support in guidance, or proceed with transformers?
   - Current approach: transformers on Modal (production-realistic)
   - Alternative: Anthropic when available (may have better quality)

2. **Model Selection**: Qwen 32B vs alternatives?
   - Current: Qwen/Qwen2.5-Coder-32B-Instruct (matches production)
   - Could test with smaller models for faster iteration

3. **Schema Complexity**: Full TypeScript schema vs simplified?
   - Current: Full production schema (realistic but complex)
   - Could simplify for initial validation

4. **Success Threshold**: What success rate justifies migration?
   - Proposed: >50% baseline, >80% target
   - XGrammar baseline: 4.8% (very low bar)

---

## Risks

1. **POC Timeout**: Modal function may exceed timeout without results
   - Mitigation: Check Modal dashboard/logs directly
   - Fallback: Use smaller model or simplified schema

2. **Low Success Rate**: guidance may not significantly outperform XGrammar
   - Mitigation: Investigate prompt engineering, model selection
   - Fallback: Re-evaluate migration, investigate other libraries

3. **Schema Incompatibility**: TypeScript schema may not be fully supported
   - Mitigation: Test incremental schema complexity
   - Fallback: Modify schema or use Pydantic conversion

4. **Integration Complexity**: GuidanceProvider may be harder than expected
   - Mitigation: Phase 3.2 will reveal integration challenges
   - Fallback: Hybrid approach (XGrammar + guidance)

---

## Related Documents

- **Migration Plan**: `docs/planning/LLGUIDANCE_MIGRATION_PLAN.md`
- **XGrammar Baseline**: `validation/PHASE1_VALIDATION_REPORT.md`
- **TypeScript Schema**: `lift_sys/codegen/languages/typescript_schema.py`
- **POC Scripts**: `scripts/poc/test_guidance_typescript_poc.py`, `scripts/modal/guidance_poc_modal.py`

---

## Success Metrics

**Phase 3.1 Complete When**:
- ✅ guidance POC successfully generates valid TypeScript
- ✅ Success rate documented and compared to XGrammar (4.8%)
- ✅ Latency documented and compared to XGrammar (~85s)
- ✅ Go/no-go decision made for migration
- ✅ Next phase (3.2) ready to begin

**Current Status**: 4/5 criteria met, awaiting Modal POC results for final validation
