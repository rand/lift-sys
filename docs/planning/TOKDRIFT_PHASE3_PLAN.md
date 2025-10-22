# TokDrift Phase 3: DSPy Integration & Optimization

**Date**: 2025-10-22
**Status**: Planning
**Prerequisites**: Phase 1 & 2 Complete ✅
**Duration**: 2-3 weeks (estimated)
**Bead**: lift-sys-295 (to be created)

---

## Executive Summary

Phase 3 integrates the robustness testing framework (Phase 1 & 2) with actual IR/code generation and implements DSPy-based robustness optimization. This phase transforms robustness testing from infrastructure to active improvement.

**Goals:**
1. Replace mock generators with actual IR/code generators
2. Measure true baseline robustness of lift-sys
3. Implement robustness-aware DSPy signature optimization
4. Generate augmented training data for robustness
5. Demonstrate measurable robustness improvements

**Success Criteria:**
- Baseline robustness measured on actual system
- FRAGILE_PROMPTS.md populated with real data
- DSPy optimizer improves fragile signatures
- Robustness improvement: +5-10% on fragile cases
- All tests pass with real generators

---

## Phase 3 Components

### Component 1: Real Generator Integration

**Goal**: Replace mock generators with actual IR/code generation.

**Tasks:**
1. **Integrate IR Generation**
   - Replace `mock_generate_ir()` in tests with actual translator
   - Use `BestOfNIRTranslator` or equivalent
   - Handle generation errors gracefully

2. **Integrate Code Generation**
   - Replace `mock_generate_code()` with actual generator
   - Use `TemplatedCodeGenerator` or equivalent
   - Provide appropriate test inputs

3. **Update Test Suite**
   - Modify `test_paraphrase_robustness.py` for real IR generation
   - Modify `test_ir_variant_robustness.py` for real code generation
   - Update fixtures with realistic test cases

**Acceptance Criteria:**
- All robustness tests run with real generators
- No mock generators in production test paths
- Tests validate actual system behavior
- Pass rate ≥80% with real generators

**Files to Modify:**
```
tests/robustness/test_paraphrase_robustness.py
tests/robustness/test_ir_variant_robustness.py
tests/robustness/test_e2e_robustness.py
tests/robustness/test_baseline_robustness.py
```

---

### Component 2: Baseline Measurement

**Goal**: Measure true robustness of current lift-sys.

**Tasks:**
1. **Run Comprehensive Baseline**
   ```bash
   python scripts/robustness/measure_baseline.py \
     --output baseline_phase3_$(date +%Y%m%d).json
   ```

2. **Analyze Results**
   - Identify fragile prompts (robustness < 90%)
   - Identify fragile IR patterns
   - Calculate overall system robustness

3. **Document Findings**
   - Populate `FRAGILE_PROMPTS.md` with real cases
   - Create GitHub issues for each fragile area
   - Prioritize by impact (P0, P1, P2)

4. **Update Expected Results**
   ```bash
   python scripts/robustness/measure_baseline.py --update-baseline
   ```

**Acceptance Criteria:**
- Baseline measured on ≥20 real prompts
- FRAGILE_PROMPTS.md has ≥5 documented cases
- expected_results.json populated with actual baselines
- GitHub issues created for fragile areas

**Deliverables:**
- `baseline_phase3_YYYYMMDD.json`
- Updated `FRAGILE_PROMPTS.md`
- Updated `expected_results.json`
- GitHub issues (lift-sys-XXX)

---

### Component 3: DSPy Robustness-Aware Optimizer

**Goal**: Implement automatic robustness optimization for signatures.

**Design:**

```python
# lift_sys/robustness/dspy_optimizer.py

from dspy import Signature, Module, Predict
from lift_sys.robustness import (
    ParaphraseGenerator,
    SensitivityAnalyzer
)

class RobustnessAwareSignature(Module):
    """DSPy signature with robustness optimization."""

    def __init__(self, base_signature: Signature, target_robustness: float = 0.97):
        super().__init__()
        self.base_signature = base_signature
        self.target_robustness = target_robustness
        self.predictor = Predict(base_signature)
        self.paraphrase_gen = ParaphraseGenerator()
        self.analyzer = SensitivityAnalyzer()

    def forward(self, **kwargs):
        """Forward pass with robustness validation."""
        # Generate output
        output = self.predictor(**kwargs)

        # Measure robustness (in training/validation)
        if self.training:
            robustness = self._measure_robustness(kwargs, output)
            if robustness < self.target_robustness:
                # Trigger re-optimization
                self._optimize_for_robustness(kwargs, output, robustness)

        return output

    def _measure_robustness(self, inputs, output):
        """Measure robustness to input variations."""
        # Generate input variants
        prompt = inputs.get("prompt", "")
        paraphrases = self.paraphrase_gen.generate(prompt)

        # Test each variant
        variant_outputs = [
            self.predictor(prompt=p, **{k: v for k, v in inputs.items() if k != "prompt"})
            for p in paraphrases
        ]

        # Check equivalence
        equivalence_results = [
            self._check_equivalence(output, variant)
            for variant in variant_outputs
        ]

        # Compute robustness
        robustness = sum(equivalence_results) / len(equivalence_results)
        return robustness

    def _optimize_for_robustness(self, inputs, output, current_robustness):
        """Optimize signature for better robustness."""
        # Use MIPROv2 or COPRO optimizer
        # Objective: Maximize robustness while maintaining accuracy
        pass


class RobustIRGenerator(Module):
    """IR generator with robustness optimization."""

    def __init__(self):
        super().__init__()
        self.signature = RobustnessAwareSignature(
            IRGenerationSignature,
            target_robustness=0.97
        )

    def forward(self, prompt: str):
        return self.signature(prompt=prompt)
```

**Tasks:**
1. **Create `lift_sys/robustness/dspy_optimizer.py`**
   - RobustnessAwareSignature class
   - RobustIRGenerator class
   - Optimization metrics

2. **Integrate with DSPy Optimizers**
   - MIPROv2 for multi-stage optimization
   - COPRO for signature refinement
   - Custom metric: robustness score

3. **Test Optimization**
   - Test on fragile signatures
   - Measure robustness improvement
   - Validate accuracy maintained

**Acceptance Criteria:**
- RobustnessAwareSignature implemented
- Integration with ≥1 DSPy optimizer
- Demonstrated improvement on ≥3 fragile cases
- Robustness +5-10% improvement
- Accuracy maintained (≤2% degradation)

**New Files:**
```
lift_sys/robustness/dspy_optimizer.py  (300+ lines)
tests/unit/robustness/test_dspy_optimizer.py  (150+ lines)
```

---

### Component 4: Training Data Augmentation

**Goal**: Generate augmented training data for robustness.

**Approach:**

```python
# lift_sys/robustness/data_augmentation.py

from lift_sys.robustness import (
    ParaphraseGenerator,
    IRVariantGenerator,
    EquivalenceChecker
)

class RobustTrainingDataGenerator:
    """Generate robustness-enhanced training data."""

    def __init__(self):
        self.paraphrase_gen = ParaphraseGenerator()
        self.ir_variant_gen = IRVariantGenerator()
        self.checker = EquivalenceChecker()

    def augment_dataset(
        self,
        base_examples: list[tuple[str, IR]],
        augmentation_factor: int = 5
    ) -> list[tuple[str, IR]]:
        """Augment training data with verified variants.

        Args:
            base_examples: List of (prompt, ir) pairs
            augmentation_factor: Target multiplier

        Returns:
            Augmented dataset with variants
        """
        augmented = []

        for prompt, ir in base_examples:
            # Keep original
            augmented.append((prompt, ir))

            # Generate prompt variants
            paraphrases = self.paraphrase_gen.generate(
                prompt,
                max_variants=augmentation_factor
            )

            # Verify each variant maps to equivalent IR
            for paraphrase in paraphrases:
                # Generate IR from paraphrase
                variant_ir = generate_ir(paraphrase)

                # Check equivalence
                if self.checker.ir_equivalent(ir, variant_ir):
                    augmented.append((paraphrase, ir))
                else:
                    # Log non-equivalent case for analysis
                    log_fragile_case(prompt, paraphrase, ir, variant_ir)

            # Generate IR variants for same prompt
            ir_variants = self.ir_variant_gen.generate_naming_variants(ir)
            for variant_ir in ir_variants:
                augmented.append((prompt, variant_ir))

        return augmented
```

**Tasks:**
1. **Create Data Augmentation Module**
   - RobustTrainingDataGenerator class
   - Verification pipeline
   - Fragile case logging

2. **Integrate with Training**
   - Augment existing training data
   - Validate augmented examples
   - Measure robustness improvement

3. **Test Augmentation**
   - Verify equivalence of augmented data
   - Measure diversity metrics
   - Validate training effectiveness

**Acceptance Criteria:**
- Data augmentation implemented
- Augmentation factor: 3-5x
- Equivalence validation: >95%
- Diversity metrics calculated
- Training with augmented data improves robustness

**New Files:**
```
lift_sys/robustness/data_augmentation.py  (250+ lines)
tests/unit/robustness/test_data_augmentation.py  (100+ lines)
```

---

### Component 5: Robustness Improvement Validation

**Goal**: Demonstrate measurable robustness improvements.

**Approach:**

1. **Before/After Comparison**
   ```python
   # Measure baseline
   baseline = measure_robustness(original_signature)

   # Optimize
   optimized_signature = optimize_for_robustness(original_signature)

   # Measure improved
   improved = measure_robustness(optimized_signature)

   # Validate improvement
   assert improved.robustness > baseline.robustness
   ```

2. **Statistical Validation**
   ```python
   # Wilcoxon test for significance
   result = analyzer.wilcoxon_test(
       baseline_scores,
       improved_scores,
       alternative="greater"  # Test if improved > baseline
   )

   assert result.p_value < 0.05  # Significant improvement
   assert result.significant
   ```

3. **Regression Testing**
   - Ensure accuracy not degraded
   - Ensure code quality maintained
   - Ensure latency acceptable

**Tasks:**
1. **Create Improvement Test Suite**
   - Before/after comparison tests
   - Statistical validation tests
   - Regression prevention tests

2. **Document Improvements**
   - Create improvement report
   - Update FRAGILE_PROMPTS.md with fixes
   - Document optimization strategies

3. **Integrate with CI**
   - Add improvement tracking to CI
   - Alert on robustness regressions
   - Track trends over time

**Acceptance Criteria:**
- ≥3 fragile cases improved
- Improvements statistically significant (p < 0.05)
- Accuracy maintained (≤2% degradation)
- Latency acceptable (≤20% increase)
- CI tracks improvements

**New Files:**
```
tests/robustness/test_improvement_validation.py  (200+ lines)
docs/robustness/IMPROVEMENT_REPORT.md
```

---

## Implementation Plan

### Week 1: Integration & Baseline

**Day 1-2: Real Generator Integration**
- Integrate actual IR generator in tests
- Integrate actual code generator in tests
- Fix integration issues

**Day 3-4: Baseline Measurement**
- Run comprehensive baseline
- Analyze results
- Document fragile cases

**Day 5: Review & Documentation**
- Update FRAGILE_PROMPTS.md
- Create GitHub issues
- Review baseline with team

### Week 2: Optimization

**Day 1-2: DSPy Optimizer**
- Implement RobustnessAwareSignature
- Integrate with MIPROv2
- Test on fragile cases

**Day 3-4: Data Augmentation**
- Implement RobustTrainingDataGenerator
- Augment training data
- Validate equivalence

**Day 5: Integration Testing**
- Test optimizer + augmentation together
- Measure improvements
- Fix issues

### Week 3: Validation & Documentation

**Day 1-2: Improvement Validation**
- Run before/after comparisons
- Statistical validation
- Regression testing

**Day 3: CI Integration**
- Update CI workflow
- Add improvement tracking
- Test end-to-end

**Day 4-5: Documentation & Completion**
- Create improvement report
- Update documentation
- Phase 3 completion report
- Team review

---

## Success Metrics

### Baseline Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Prompts Tested** | ≥20 | Actual count |
| **Fragile Cases Found** | ≥5 | robustness < 90% |
| **Overall Robustness** | Measured | Average across all |

### Improvement Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Fragile Cases Improved** | ≥3 | Before/after |
| **Robustness Improvement** | +5-10% | Statistical test |
| **Accuracy Maintained** | ≤2% degradation | Validation set |
| **Latency Impact** | ≤20% increase | Benchmark |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Test Pass Rate** | 100% | CI results |
| **Code Coverage** | ≥90% | pytest-cov |
| **Statistical Significance** | p < 0.05 | Wilcoxon test |

---

## Dependencies

### Prerequisites (✅ Complete)
- Phase 1: ParaphraseGenerator, IRVariantGenerator, EquivalenceChecker
- Phase 2: SensitivityAnalyzer, test suite, CI/CD

### External Dependencies
- **DSPy**: For signature optimization (already in pyproject.toml)
- **Actual IR Generator**: BestOfNIRTranslator or equivalent
- **Actual Code Generator**: TemplatedCodeGenerator or equivalent

### New Dependencies (if needed)
- None expected (all tooling already available)

---

## Risks & Mitigation

### Risk 1: Integration Complexity

**Risk**: Integrating real generators may reveal unforeseen issues.

**Mitigation**:
- Start with simple test cases
- Gradual rollout (paraphrase → IR variant → E2E)
- Comprehensive error handling

### Risk 2: Optimization Effectiveness

**Risk**: DSPy optimization may not improve robustness significantly.

**Mitigation**:
- Test on multiple optimizer types (MIPROv2, COPRO)
- Manual prompt engineering fallback
- Document what works/doesn't work

### Risk 3: Performance Impact

**Risk**: Robustness optimization may degrade performance.

**Mitigation**:
- Measure latency at each step
- Set acceptable thresholds (≤20% increase)
- Optimize critical paths if needed

### Risk 4: Statistical Validity

**Risk**: Improvements may not be statistically significant.

**Mitigation**:
- Ensure sufficient sample size (≥20 cases)
- Use appropriate statistical tests (Wilcoxon)
- Accept p < 0.05 as significant

---

## Deliverables Checklist

### Code
- [ ] `lift_sys/robustness/dspy_optimizer.py`
- [ ] `lift_sys/robustness/data_augmentation.py`
- [ ] Updated test files with real generators
- [ ] New test files for Phase 3 components

### Data
- [ ] `baseline_phase3_YYYYMMDD.json`
- [ ] Updated `expected_results.json`
- [ ] Augmented training dataset

### Documentation
- [ ] Updated `FRAGILE_PROMPTS.md`
- [ ] `IMPROVEMENT_REPORT.md`
- [ ] `PHASE3_COMPLETION_REPORT.md`
- [ ] Updated `README.md`

### Testing
- [ ] All robustness tests pass with real generators
- [ ] Improvement validation tests pass
- [ ] Statistical significance demonstrated
- [ ] CI workflow updated

---

## Next Steps (Immediate)

1. **Create Phase 3 Bead**
   ```bash
   bd create "Phase 3: DSPy Integration & Optimization" \
     -t feature \
     -p P0 \
     --body "$(cat docs/planning/TOKDRIFT_PHASE3_PLAN.md)" \
     --json
   ```

2. **Break Down into Sub-Beads**
   - Real generator integration
   - Baseline measurement
   - DSPy optimizer
   - Data augmentation
   - Improvement validation

3. **Start with Integration**
   - Begin integrating actual IR generator
   - Test with simple prompts first
   - Expand to full test suite

---

## References

- **Phase 1 Report**: `docs/robustness/PHASE1_COMPLETION_REPORT.md`
- **Phase 2 Report**: `docs/robustness/PHASE2_COMPLETION_REPORT.md`
- **TokDrift Paper**: arXiv:2510.14972
- **DSPy Documentation**: https://dspy-ai.github.io/dspy/
- **Pydantic AI**: https://ai.pydantic.dev/

---

**Document Status**: Planning Complete
**Ready to Start**: Yes
**Prerequisites Met**: ✅ All Phase 1 & 2 deliverables complete
**Estimated Timeline**: 2-3 weeks
**Next Action**: Create beads and begin integration
