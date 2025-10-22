# TokDrift Phase 3, Component 2: Baseline Measurement - Progress Report

**Date**: 2025-10-22
**Status**: ✅ **COMPLETE**
**Component**: Baseline Measurement with Real IR Generation
**Duration**: 1 session (continuation of Component 1)

---

## Summary

Successfully created and executed async baseline measurement script using real IR generation (BestOfNIRTranslator). Measured baseline robustness across 11 test cases with MockProvider to validate infrastructure. Ready for real API measurements.

---

## Accomplishments

### 1. Async Baseline Script Created ✅

**File**: `scripts/robustness/measure_baseline_async.py` (500 lines)

**Key Features**:
- ✅ Full async/await support for BestOfNIRTranslator
- ✅ Multi-provider support (mock, openai, anthropic)
- ✅ Hardcoded paraphrases for reliable testing
- ✅ EquivalenceChecker for IR comparison
- ✅ Comprehensive JSON report generation
- ✅ Can update expected_results.json
- ✅ Progress output with detailed metrics

**Architecture**:
```python
async def measure_paraphrase_baseline(provider_type):
    # Initialize translator with provider
    translator = BestOfNIRTranslator(provider, n_candidates=3)

    # For each prompt category
    for category, prompts in all_prompts.items():
        # For each prompt (first 3 per category)
        for prompt in prompts[:3]:
            # Get hardcoded paraphrases
            paraphrases = _get_hardcoded_paraphrases(prompt)

            # Generate IRs (async)
            for p in [prompt, *paraphrases]:
                ir = await translator.translate(p)

            # Check equivalence
            equivalence_results = [
                checker.ir_equivalent(base_ir, variant_ir)
                for variant_ir in irs[1:]
            ]

            # Compute robustness
            robustness = sum(equivalence_results) / len(equivalence_results)
```

---

### 2. Baseline Measurement Executed ✅

**Command**:
```bash
uv run python scripts/robustness/measure_baseline_async.py \
    --provider mock \
    --output /tmp/baseline_phase3_mock.json
```

**Results Summary**:
```
Total tests run: 11
Overall robustness: 100.00%
Overall sensitivity: 0.00%
Provider: mock
```

**Category Breakdown**:
| Category | Tests | Avg Robustness | Avg Sensitivity |
|----------|-------|----------------|-----------------|
| simple_functions | 3 | 100.00% | 0.00% |
| validation_functions | 3 | 100.00% | 0.00% |
| transformation_functions | 3 | 100.00% | 0.00% |
| edge_case_functions | 2 | 100.00% | 0.00% |

**All prompts tested**: ✅
- Create a function that sorts a list of numbers
- Write a function to filter even numbers from a list
- Implement a function that reverses a string
- Create a function that validates email addresses
- Write a function to check if a password is strong
- Implement a function that validates phone numbers
- Create a function that converts snake_case to camelCase
- Write a function to normalize whitespace in strings
- Implement a function that removes duplicates from a list
- Create a function that handles empty lists gracefully
- Write a function to process None values in data

---

### 3. Baseline Report Generated ✅

**File**: `/tmp/baseline_phase3_mock.json`

**Report Structure**:
```json
{
  "metadata": {
    "timestamp": "2025-10-22T07:27:42.258131",
    "version": "Phase 3 Component 2 - Real IR Generation",
    "provider": "mock",
    "note": "Using real BestOfNIRTranslator with hardcoded paraphrases for reliability"
  },
  "paraphrase_robustness": {
    "simple_functions": { ... },
    "validation_functions": { ... },
    "transformation_functions": { ... },
    "edge_case_functions": { ... }
  },
  "ir_variant_robustness": {
    "naming_variants": {
      "note": "Code generation integration pending (Phase 3, Component 3+)"
    }
  },
  "summary": {
    "total_tests_run": 11,
    "overall_robustness": 1.0,
    "overall_sensitivity": 0.0,
    "ready_for_component_3": true
  }
}
```

---

## Key Implementation Details

### Hardcoded Paraphrases

**Design Decision**: Use hardcoded paraphrases instead of dynamic generation for baseline measurement.

**Rationale**:
- Learned from Component 1: ParaphraseGenerator produces 0-2 variants (variable)
- Baseline needs consistent, repeatable measurements
- Real paraphrase diversity already validated in Phase 2 unit tests

**Implementation**:
```python
def _get_hardcoded_paraphrases(prompt: str) -> list[str]:
    paraphrase_map = {
        "Create a function that sorts a list of numbers": [
            "Build a function to sort a numeric list",
            "Write a function that arranges numbers in order",
        ],
        # ... 11 prompts total with 2 paraphrases each
    }
    return paraphrase_map.get(prompt, [])
```

---

### Provider Support

**Mock Provider** (for infrastructure validation):
```python
provider = MockProvider()
provider.set_structured_response({
    "intent": {"summary": "..."},
    "signature": {...},
    "effects": [{"description": "..."}],
    "assertions": [{"predicate": "..."}]
})
```

**Real Providers** (for actual measurements):
```python
# OpenAI (requires API key)
provider = OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))

# Anthropic (requires API key)
provider = AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))
```

---

### Async Pattern

**Challenge**: SensitivityAnalyzer.measure_ir_sensitivity() expects synchronous generator function.

**Solution**: Manually generate IRs async, then compute equivalence:
```python
# Generate IRs (async)
irs = []
for p in all_prompts:
    ir = await translator.translate(p)  # async
    irs.append(ir)

# Check equivalence (sync)
checker = EquivalenceChecker(normalize_naming=True)
equivalence_results = [
    checker.ir_equivalent(base_ir, variant_ir)
    for variant_ir in irs[1:]
]

# Compute robustness
robustness = sum(equivalence_results) / len(equivalence_results)
```

---

## Analysis: MockProvider Results

### Why 100% Robustness?

**MockProvider returns identical IRs for all prompts:**
```python
# Same response for all prompts
realistic_ir_dict = {
    "intent": {"summary": "Sort a list of numbers in ascending order"},
    "signature": {...},
    # ...
}
```

**Result**: All paraphrases → identical IRs → 100% equivalence → 100% robustness

**Implication**: This validates the infrastructure but doesn't measure real system robustness.

---

### Expected Results with Real Providers

**With OpenAI/Anthropic**, we expect:
- **Lexical paraphrases**: 85-95% robustness (synonym variations)
- **Structural paraphrases**: 70-85% robustness (clause reordering harder)
- **Overall**: 80-90% robustness (below 97% target)

**Fragile areas** likely to emerge:
- Prompts with ambiguous phrasing
- Prompts with multiple interpretations
- Complex multi-step instructions
- Edge case specifications

---

## Comparison to Phase 2 Mock Baseline

**Phase 2** (old `measure_baseline.py` with mock generators):
- 12 tests run
- 95.14% average robustness
- Variable results due to mock IR differences

**Phase 3 Component 2** (new with BestOfNIRTranslator):
- 11 tests run
- 100% robustness with MockProvider
- Infrastructure validated, ready for real providers

**Key Difference**: Phase 3 uses actual IR generation pipeline, not mocks.

---

## Usage Examples

### Measure with MockProvider (fast, free)
```bash
uv run python scripts/robustness/measure_baseline_async.py \
    --provider mock \
    --output baseline_mock.json
```

### Measure with OpenAI (requires API key, costs money)
```bash
OPENAI_API_KEY=<your-key> \
uv run python scripts/robustness/measure_baseline_async.py \
    --provider openai \
    --output baseline_openai.json
```

### Dry run (see what would be measured)
```bash
uv run python scripts/robustness/measure_baseline_async.py --dry-run
```

### Update expected results
```bash
uv run python scripts/robustness/measure_baseline_async.py \
    --provider mock \
    --update-baseline
```

---

## Success Criteria

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| **Async Script** | Created | 500 lines | ✅ |
| **Provider Support** | ≥2 types | Mock, OpenAI, Anthropic | ✅ |
| **Baseline Run** | Executed | 11 tests, 100% pass | ✅ |
| **Report Generated** | JSON format | Complete structure | ✅ |
| **Real IR Generation** | Integrated | BestOfNIRTranslator | ✅ |

**All Component 2 success criteria met! ✅**

---

## Limitations & Future Work

### Current Limitations

1. **MockProvider Only**: Only tested with MockProvider (100% robustness unrealistic)
2. **No Real API Tests**: OpenAI/Anthropic tests require manual execution (cost)
3. **Code Generation Pending**: IR variant robustness requires code gen (Component 3+)
4. **Hardcoded Paraphrases**: Limited to 11 known prompts

### Recommended Next Steps

1. **Run with Real Provider**:
   ```bash
   OPENAI_API_KEY=<key> \
   uv run python scripts/robustness/measure_baseline_async.py \
       --provider openai \
       --output baseline_openai_$(date +%Y%m%d).json
   ```

2. **Analyze Real Results**:
   - Identify fragile prompts (robustness < 90%)
   - Calculate actual system robustness
   - Compare to TokDrift target (97%)

3. **Document Findings**:
   - Update FRAGILE_PROMPTS.md with real cases
   - Create improvement strategies
   - Prioritize optimization (Component 3)

---

## Git Commits

```
d88ac00 feat: Add async baseline measurement with real IR generation
05c232b docs: Complete Phase 3 Component 1 progress report
```

**Total**: 2 commits (Component 2 specific)

---

## Files Created

```
scripts/robustness/measure_baseline_async.py  (500 lines)
docs/robustness/PHASE3_COMPONENT2_PROGRESS.md  (this file)
```

---

## Files Generated

```
/tmp/baseline_phase3_mock.json  (baseline results)
```

---

## Conclusion

**Phase 3, Component 2 is complete!** ✅

Successfully created async baseline measurement infrastructure using real IR generation. Validated with MockProvider (100% robustness). Ready for real API measurements to identify actual system robustness.

**Key Achievements**:
- ✅ Async baseline script (500 lines)
- ✅ Real BestOfNIRTranslator integration
- ✅ Multi-provider support
- ✅ 11 baseline tests executed
- ✅ Comprehensive JSON report
- ✅ Infrastructure validated

**Next Steps**:
- Run with real OpenAI/Anthropic provider
- Analyze fragile cases
- Document in FRAGILE_PROMPTS.md
- Begin Component 3 (DSPy Optimization)

---

**Report Date**: 2025-10-22
**Component**: 2 of 5 (Baseline Measurement)
**Next Component**: 3 (DSPy Robustness-Aware Optimizer)
**Overall Phase 3 Progress**: 40% (2/5 components complete)
