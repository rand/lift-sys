# Robustness Test Suite

**Purpose**: Systematic testing of lift-sys robustness to semantic-preserving transformations.

**Based on**: TokDrift methodology (arXiv:2510.14972)

## Overview

This test suite validates that lift-sys produces consistent outputs when inputs are semantically equivalent but syntactically different. The goal is to measure and improve robustness, targeting <3% sensitivity.

## Test Categories

### 1. Paraphrase Robustness Tests (`test_paraphrase_robustness.py`)

Tests IR generation consistency across NLP prompt variations:
- Lexical paraphrases (synonym substitution)
- Structural paraphrases (clause reordering)
- Stylistic paraphrases (voice/mood changes)

**Success Criteria**: >97% of paraphrases produce equivalent IRs

### 2. IR Variant Robustness Tests (`test_ir_variant_robustness.py`)

Tests code generation consistency across IR variations:
- Naming convention changes (snake_case, camelCase, PascalCase)
- Effect ordering changes (when dependencies allow)
- Assertion rephrasing (equivalent predicates)

**Success Criteria**: >97% of IR variants produce equivalent code

### 3. End-to-End Robustness Tests (`test_e2e_robustness.py`)

Tests full pipeline (NLP → IR → Code) robustness:
- Combined prompt + IR + code variations
- Real-world use case scenarios
- Performance under composition

**Success Criteria**: >95% overall robustness score

### 4. Baseline Measurement (`test_baseline_robustness.py`)

Establishes baseline robustness metrics for current system:
- Current sensitivity scores
- Fragile prompts/IRs identification
- Regression detection

## Directory Structure

```
tests/robustness/
├── README.md                      # This file
├── __init__.py                    # Package initialization
├── conftest.py                    # Shared pytest fixtures
├── test_paraphrase_robustness.py  # Paraphrase robustness tests
├── test_ir_variant_robustness.py  # IR variant robustness tests
├── test_e2e_robustness.py         # End-to-end robustness tests
├── test_baseline_robustness.py    # Baseline measurements
└── fixtures/                      # Test data
    ├── prompts.json               # Standard test prompts
    ├── irs.json                   # Standard test IRs
    └── expected_results.json      # Expected robustness scores
```

## Running Tests

### Run All Robustness Tests
```bash
uv run pytest tests/robustness/ -v
```

### Run Specific Test Category
```bash
# Paraphrase robustness only
uv run pytest tests/robustness/test_paraphrase_robustness.py -v

# IR variant robustness only
uv run pytest tests/robustness/test_ir_variant_robustness.py -v

# End-to-end robustness only
uv run pytest tests/robustness/test_e2e_robustness.py -v
```

### Run Baseline Measurement
```bash
uv run pytest tests/robustness/test_baseline_robustness.py -v
```

### Generate Robustness Report
```bash
uv run pytest tests/robustness/ --cov=lift_sys --cov-report=html
```

## Interpreting Results

### Sensitivity Metrics

- **Sensitivity**: Proportion of variants producing non-equivalent outputs (0-1, lower is better)
- **Robustness**: 1 - sensitivity (0-1, higher is better)
- **Target**: <3% sensitivity (>97% robustness)

### Statistical Tests

- **Wilcoxon signed-rank test**: Validates whether differences are statistically significant
- **p-value < 0.05**: Significant difference detected
- **p-value >= 0.05**: No significant difference (robust)

### Example Output

```
SensitivityResult(
  total=10,
  equivalent=9,
  non_equivalent=1
  sensitivity=10.00%,  # Within target (<3% would be ideal)
  robustness=90.00%    # Good, but target is >97%
)
```

## Integration with CI/CD

Robustness tests run automatically on:
- Pull requests (regression detection)
- Main branch commits (baseline tracking)
- Nightly builds (comprehensive analysis)

**Quality Gates**:
- WARN if sensitivity > 10% (yellow)
- FAIL if sensitivity > 20% (red)
- PASS if sensitivity < 3% (green)

## Fixtures

### Standard Test Prompts (`fixtures/prompts.json`)

Curated set of prompts covering:
- Simple functions (sort, filter, map)
- Complex logic (validation, transformation)
- Edge cases (empty inputs, error handling)

### Standard Test IRs (`fixtures/irs.json`)

Curated set of IRs covering:
- Various naming styles
- Different effect orderings
- Diverse assertion patterns

### Expected Results (`fixtures/expected_results.json`)

Baseline robustness scores for regression detection.

## Adding New Tests

### 1. Add Test Function

```python
def test_my_robustness_scenario():
    \"\"\"Test description.\"\"\"
    # Setup
    prompt = "Your prompt here"
    generator = ParaphraseGenerator()

    # Generate variants
    paraphrases = generator.generate(prompt)

    # Measure sensitivity
    analyzer = SensitivityAnalyzer()
    result = analyzer.measure_ir_sensitivity(paraphrases, generate_ir)

    # Assert robustness
    assert result.robustness >= 0.97, f"Robustness too low: {result.robustness:.2%}"
```

### 2. Add to Fixtures (if reusable)

Edit `fixtures/prompts.json` or `fixtures/irs.json` to include new test data.

### 3. Update Expected Results (if baseline)

Edit `fixtures/expected_results.json` to include expected robustness scores.

## Debugging Failed Tests

### Identify Fragile Prompts

```python
# Find which variant failed
for i, (variant, is_equiv) in enumerate(zip(result.variants_tested, result.equivalence_results)):
    if not is_equiv:
        print(f"Variant {i} NOT equivalent: {variant}")
```

### Compare IRs

```python
from lift_sys.robustness import EquivalenceChecker

checker = EquivalenceChecker(normalize_naming=True)
diff = checker.compare_irs(ir1, ir2)  # Get detailed differences
```

### Analyze Sensitivity

```python
# Compare before/after changes
comparison = analyzer.compare_sensitivity(old_result, new_result)
print(f"Sensitivity change: {comparison['sensitivity_change_pct']:.1f}%")
```

## Best Practices

1. **Start with baselines**: Run baseline tests first to understand current state
2. **Isolate issues**: Use specific test categories to narrow down problems
3. **Track over time**: Monitor sensitivity trends, not just point-in-time scores
4. **Document fragile cases**: Record prompts/IRs with low robustness for future improvement
5. **Use statistical tests**: Don't rely on single measurements; validate with Wilcoxon tests

## References

- **TokDrift Paper**: arXiv:2510.14972
- **TokDrift GitHub**: https://github.com/uw-swag/tokdrift
- **lift-sys Proposal**: `docs/planning/TOKDRIFT_APPLICABILITY_PROPOSAL.md`
- **Phase 2 Plan**: `docs/planning/TOKDRIFT_PHASE1_PLAN.md` (contains Phase 2 details)

## Maintenance

- **Update baselines**: After major changes, re-run baseline tests and update `expected_results.json`
- **Add regression tests**: When fixing robustness issues, add tests to prevent recurrence
- **Review fixtures**: Periodically review and expand test fixtures to cover new use cases
