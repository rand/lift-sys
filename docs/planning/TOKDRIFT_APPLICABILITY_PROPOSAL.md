# TokDrift Applicability Analysis and Proposal for lift-sys

**Date**: 2025-10-21
**Status**: Proposal for Review
**Authors**: Research Analysis by Claude
**Version**: 1.0

---

## Executive Summary

This document analyzes the [TokDrift research framework](https://github.com/uw-swag/tokdrift) and proposes its integration into lift-sys to **systematically measure and improve robustness** of our LLM-based IR generation and code generation pipelines.

### TokDrift Key Finding

**Minor formatting variations in semantically identical code cause LLMs to produce different outputs 8-9% of the time**, exposing a fundamental limitation in subword tokenization that doesn't respect grammatical boundaries.

### Proposed Integration

Adapt TokDrift's methodology to:
1. **Test IR generation robustness** against paraphrase variations
2. **Validate code generation consistency** across naming convention variants
3. **Enhance DSPy optimization** with robustness-aware training data
4. **Establish robustness metrics** alongside accuracy metrics
5. **Create adversarial test suites** for continuous validation

### Expected Impact

- **Robustness Improvement**: Reduce sensitivity to input variations from current unknown baseline to <3% (vs TokDrift's 8-9%)
- **Quality Assurance**: Systematic detection of fragile prompts/signatures before production
- **DSPy Optimization**: Better training data leads to more robust optimized signatures
- **Confidence Metrics**: Quantitative robustness scores for IR/code pairs

### Bottom Line

**Current**: No systematic robustness testing → hidden brittleness in production
**Proposed**: TokDrift-inspired validation → measurable, improvable robustness

---

## Table of Contents

1. [TokDrift Research Overview](#1-tokdrift-research-overview)
2. [Applicability Analysis](#2-applicability-analysis)
3. [Proposed Integration Strategy](#3-proposed-integration-strategy)
4. [Technical Architecture](#4-technical-architecture)
5. [Implementation Roadmap](#5-implementation-roadmap)
6. [Success Metrics](#6-success-metrics)
7. [Risk Analysis](#7-risk-analysis)
8. [Alternatives Considered](#8-alternatives-considered)
9. [References](#9-references)

---

## 1. TokDrift Research Overview

### 1.1 Research Paper Summary

**Paper**: "TokDrift: When LLM Speaks in Subwords but Code Speaks in Grammar"
**Authors**: Yinxi Li, Yuntian Deng, Pengyu Nie (UW SWAG)
**Published**: October 2024, arXiv:2510.14972
**Repository**: https://github.com/uw-swag/tokdrift

### 1.2 Core Research Question

How do **semantic-preserving code transformations** (e.g., snake_case → camelCase, whitespace variations) affect LLM performance on code-related tasks?

### 1.3 Key Findings

#### Finding 1: Significant Sensitivity to Formatting
- **Best model** (Qwen2.5-Coder-32B): 6.09% prediction changes
- **Average sensitivity**: 8-9% across tasks
- **Statistical significance**: Confirmed via Wilcoxon signed-rank test for spacing rules

#### Finding 2: Tokenization is the Root Cause
- Subword tokenizers (BPE) are **statistics-driven**, not **grammar-aware**
- Token boundaries don't align with grammatical boundaries
- `sortedLst` may tokenize as `["sorted", "Lst"]` while `sorted_lst` as `["sorted", "_", "lst"]`
- Different tokenizations → different embeddings → different predictions

#### Finding 3: Problem Originates in Early Layers
- Drift occurs at **embedding layer**, not just final prediction
- Cascades through all downstream layers
- Cannot be "fixed" by later layers once tokenization misaligns

#### Finding 4: Larger Models More Robust, But Not Immune
- 30B+ parameter models show lower sensitivity than smaller models
- But even largest models still exhibit 6%+ sensitivity
- Scale helps but doesn't eliminate the problem

### 1.4 Semantic-Preserving Rewrite Rules

TokDrift implements **24 rewrite rules** across two categories:

#### Naming Rules (6 rules)
- `snake_case` ↔ `camelCase`
- `snake_case` ↔ `PascalCase`
- `camelCase` ↔ `SCREAMING_SNAKE_CASE`
- Applicable to: identifiers, function names, variable names

**Example**:
```python
# Original
def sortedLst(items):
    return sorted(items)

# Rewritten (snake_case)
def sorted_lst(items):
    return sorted(items)
```

#### Spacing Rules (18 rules)
- Add/remove spaces around operators (`+`, `-`, `*`, `/`, `==`, etc.)
- Add/remove spaces around parentheses, brackets, braces
- Add/remove spaces after commas, colons
- Normalize whitespace in function calls

**Example**:
```python
# Original
result = calculate(x,y)+10

# Rewritten (normalized spacing)
result = calculate(x, y) + 10
```

### 1.5 Methodology

```
┌─────────────────────────────────────────────────────────┐
│ 1. Input: Seed code samples (HumanEval, CodeNet, etc.) │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Apply semantic-preserving rewrite rules             │
│    → Generate code pairs (original, rewritten)         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Run LLM on both versions                            │
│    → Task: bug fixing, summarization, translation       │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Compare outputs                                      │
│    → Same/different?                                    │
│    → Functionally equivalent?                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. Measure sensitivity                                  │
│    → % samples where output correctness flips           │
│    → Δaccuracy between original and rewritten           │
└─────────────────────────────────────────────────────────┘
```

### 1.6 Tasks Evaluated

1. **Bug Fixing** (Avatar, HumanEval)
2. **Code Summarization** (HumanEval Explain)
3. **Code Translation** (CodeNet Java→Python)

### 1.7 Key Recommendations from Paper

For practitioners building code LLMs:

1. **Design grammar-aware tokenizers** that respect token boundaries
2. **Test robustness** to formatting variations systematically
3. **Use ensemble methods** across multiple tokenizations
4. **Document sensitivity** as part of model evaluation
5. **Consider pre-normalization** of code before feeding to LLM

---

## 2. Applicability Analysis

### 2.1 lift-sys Context

lift-sys is a **bidirectional translation system** with:

**Forward Mode**: Natural Language → IR → Code
- LLM translates NL prompt to IR (via DSPy signatures, planned)
- LLM generates code from IR (via Pydantic AI graph, planned)
- Current success rate: 60%, target: 85%

**Reverse Mode**: Code → IR → Understanding (planned)
- LLM extracts IR from existing code
- Enables refactoring, documentation, migration

**Current Architecture**:
- Pydantic-based IR with constraints, assertions, effects
- XGrammar-constrained generation
- Validation pipeline (semantic, assertion, constraint checking)
- About to implement DSPy + Pydantic AI architecture (see `DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md`)

### 2.2 Relevance to lift-sys

TokDrift's findings are **highly relevant** because:

#### Relevance 1: IR Generation from NL Uses LLMs
**TokDrift Problem**: Different phrasings of the same intent could produce different IRs
**lift-sys Impact**: Brittleness in forward mode, inconsistent IR for equivalent prompts

**Example**:
```
Prompt A: "Create a function that sorts a list of numbers"
Prompt B: "Write a function to sort a numeric list"
Prompt C: "Implement a number list sorting function"
```

All three prompts have identical intent. Will lift-sys generate:
- **Identical IR**? (desired)
- **Equivalent but different IR**? (acceptable)
- **Incompatible IR**? (problem!)

**Without TokDrift-style testing**: We don't know. Hidden brittleness.
**With TokDrift-style testing**: Systematic measurement, targeted improvement.

#### Relevance 2: Code Generation from IR Uses LLMs
**TokDrift Problem**: Different IR formulations could produce functionally different code
**lift-sys Impact**: Same logical requirement produces different implementations

**Example**:
```python
# IR variant A: snake_case identifiers
{
  "signature": {"name": "process_user_data", ...},
  "effects": [{"type": "file_write", "target": "output_file"}]
}

# IR variant B: camelCase identifiers
{
  "signature": {"name": "processUserData", ...},
  "effects": [{"type": "fileWrite", "target": "outputFile"}]
}
```

Both IRs describe the same logic. Will generated code:
- **Be functionally equivalent**? (desired)
- **Handle errors consistently**? (critical)
- **Have same performance characteristics**? (desired)

**Without TokDrift-style testing**: Unknown consistency.
**With TokDrift-style testing**: Quantified, trackable robustness.

#### Relevance 3: DSPy Optimization Needs Robust Training Data
**TokDrift Insight**: Models trained on varied tokenizations are more robust
**lift-sys Opportunity**: Use paraphrase/variant generation to create better DSPy training sets

DSPy's MIPROv2 optimizer learns from validation data. If we provide:
- **Only canonical examples**: Optimizer may overfit to specific phrasings
- **Paraphrased variants**: Optimizer learns to generalize across formulations

**Application**:
```python
# DSPy training data generation (TokDrift-inspired)
def generate_robust_training_examples(canonical_prompt: str, canonical_ir: IR):
    variants = [
        paraphrase_naming(canonical_prompt),      # "sort list" → "order array"
        paraphrase_structure(canonical_prompt),   # active→passive voice
        rewrite_ir_naming(canonical_ir),          # snake_case → camelCase
    ]

    return [
        (variant_prompt, canonical_ir)
        for variant_prompt in variants
    ] + [(canonical_prompt, canonical_ir)]
```

#### Relevance 4: Validation Needs Robustness Metrics
**TokDrift Contribution**: Sensitivity measurement methodology
**lift-sys Gap**: Current validation checks correctness, not robustness

**Current lift-sys validation**:
```python
# Does IR satisfy constraints?
validate_ir(ir) → bool

# Does code satisfy assertions?
validate_code(code, assertions) → bool

# Is code syntactically valid?
validate_syntax(code) → bool
```

**Missing**:
```python
# Is IR generation robust to paraphrases?
validate_ir_robustness(prompts: list[str]) → RobustnessScore

# Is code generation robust to IR variants?
validate_code_robustness(ir_variants: list[IR]) → RobustnessScore
```

### 2.3 Alignment with lift-sys Goals

| lift-sys Goal | TokDrift Contribution |
|---------------|----------------------|
| 85% success rate | Identify and fix fragile prompts/signatures |
| Constraint-driven generation | Test if constraints hold across variants |
| DSPy optimization | Provide robust training data |
| Production reliability | Quantify robustness before deployment |
| Semantic IR | Validate IR equivalence systematically |

### 2.4 Applicability Score

| Aspect | Score (1-5) | Rationale |
|--------|-------------|-----------|
| **Relevance** | 5/5 | Directly addresses LLM brittleness in core workflows |
| **Feasibility** | 4/5 | Straightforward to adapt methodology, some engineering effort |
| **Impact** | 5/5 | Could significantly improve robustness and confidence |
| **Urgency** | 4/5 | Important for production readiness, not blocking current work |
| **Alignment** | 5/5 | Perfect fit with DSPy architecture and quality goals |

**Overall Applicability**: **Highly Recommended** (23/25)

---

## 3. Proposed Integration Strategy

### 3.1 Integration Approach

**Strategy**: Adapt TokDrift's **methodology** (not full framework) to lift-sys's specific needs.

**Why not full adoption?**
- TokDrift is designed for general code LLM research
- lift-sys has specific IR-centric architecture
- We need robustness testing for IR generation, not just code tasks

**What to adapt**:
1. **Semantic-preserving transformations** (paraphrases for NL, variants for IR)
2. **Sensitivity measurement** (% flips in correctness)
3. **Statistical validation** (Wilcoxon signed-rank test)
4. **Robustness as a metric** (alongside accuracy)

### 3.2 Four Integration Pillars

```
┌─────────────────────────────────────────────────────────────┐
│                  TokDrift-Inspired Robustness               │
│                    Testing for lift-sys                     │
└─────────────────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Pillar 1   │    │   Pillar 2   │    │   Pillar 3   │
│              │    │              │    │              │
│  IR Generation│    │ Code Generation│  │     DSPy     │
│  Robustness  │    │   Robustness  │    │ Optimization │
│   Testing    │    │    Testing    │    │ Enhancement  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
                    ┌──────────────┐
                    │   Pillar 4   │
                    │              │
                    │  Benchmark   │
                    │  Integration │
                    └──────────────┘
```

#### Pillar 1: IR Generation Robustness Testing

**Goal**: Ensure paraphrased prompts produce equivalent IRs

**Methodology**:
1. Create **paraphrase variants** of NL prompts:
   - Lexical: synonyms ("create" → "implement", "list" → "array")
   - Structural: reordering ("sort then filter" → "filter then sort" for independent ops)
   - Stylistic: active/passive voice, imperative/declarative

2. Generate IR from each variant using DSPy signatures

3. Compare IRs for **semantic equivalence**:
   - Identical signatures (modulo naming)
   - Equivalent effects (same operations, possibly reordered if independent)
   - Equivalent assertions (logically equivalent conditions)

4. Measure **IR sensitivity**:
   ```python
   ir_sensitivity = (# variants with non-equivalent IR) / (# total variants)
   ```

5. Target: `ir_sensitivity < 3%` (better than TokDrift's 8-9%)

**Example**:
```python
prompts = [
    "Create a function that validates email addresses",
    "Write a function to check if an email is valid",
    "Implement email address validation",
]

irs = [generate_ir(p) for p in prompts]

# Should all produce equivalent IR:
# - function with same logic
# - input: email (str)
# - output: boolean
# - effect: none (pure function)
```

#### Pillar 2: Code Generation Robustness Testing

**Goal**: Ensure IR variants produce functionally equivalent code

**Methodology**:
1. Create **IR variants** with semantic-preserving transformations:
   - Naming: snake_case ↔ camelCase for identifiers
   - Effect ordering: reorder independent effects
   - Assertion rephrasing: logically equivalent assertions with different syntax

2. Generate code from each IR variant

3. Validate **functional equivalence**:
   - Same behavior on test inputs (execute both, compare outputs)
   - Same side effects (file writes, API calls, etc.)
   - Pass same assertion checks

4. Measure **code sensitivity**:
   ```python
   code_sensitivity = (# variants with non-equivalent behavior) / (# total variants)
   ```

5. Target: `code_sensitivity < 3%`

**Example**:
```python
# IR variant A: snake_case
ir_a = IR(
    signature={"name": "validate_email", ...},
    effects=[],
    assertions=[{"type": "output_type", "expected": "bool"}]
)

# IR variant B: camelCase
ir_b = IR(
    signature={"name": "validateEmail", ...},
    effects=[],
    assertions=[{"type": "outputType", "expected": "bool"}]
)

code_a = generate_code(ir_a)
code_b = generate_code(ir_b)

# Should produce functionally equivalent code
assert functional_equivalence(code_a, code_b, test_inputs)
```

#### Pillar 3: DSPy Optimization Enhancement

**Goal**: Use robustness-aware data to improve DSPy signature optimization

**Methodology**:
1. **Data augmentation**: For each training example, generate paraphrase/variant pairs
   ```python
   train_data = [
       (prompt, ir),  # canonical
       (paraphrase_1(prompt), ir),  # variant 1
       (paraphrase_2(prompt), ir),  # variant 2
   ]
   ```

2. **Robustness-aware loss**: Penalize signatures that produce different IRs for equivalent prompts
   ```python
   def robustness_loss(signature, prompt_variants, target_ir):
       irs = [signature(p) for p in prompt_variants]
       return sum(ir_distance(ir, target_ir) for ir in irs)
   ```

3. **MIPROv2 optimization**: Let DSPy find prompts/examples that maximize robustness
   ```python
   optimizer = MIPROv2(
       metric=combined_metric(accuracy=0.7, robustness=0.3),
       teacher_settings={...}
   )
   ```

4. **Validation**: Test optimized signatures against held-out paraphrase sets

**Expected Impact**:
- 10-15% improvement in robustness (from augmented training data)
- Better generalization to unseen phrasings
- More consistent IR generation

#### Pillar 4: Benchmark Integration

**Goal**: Add robustness metrics to lift-sys performance benchmarks

**Methodology**:
1. **Extend `performance_benchmark.py`** with robustness tests
2. **Report sensitivity scores** alongside accuracy
3. **Track over time**: Are we getting more robust?
4. **Set gates**: Don't ship if robustness degrades

**New metrics**:
```python
{
  "accuracy": 0.85,              # existing
  "ir_robustness": 0.97,         # new: 1 - ir_sensitivity
  "code_robustness": 0.96,       # new: 1 - code_sensitivity
  "combined_score": 0.893        # weighted average
}
```

**Dashboard visualization**:
```
Robustness Over Time
───────────────────────────────────────────
IR Generation:      ████████████░░  97% ↑ +2%
Code Generation:    ███████████░░░  96% ↑ +1%
Overall:            ███████████░░░  89% ↑ +1.5%
───────────────────────────────────────────
```

### 3.3 Phased Rollout

```
Phase 1 (Weeks 1-2): Foundation
- Implement paraphrase generator for NL prompts
- Implement IR variant generator
- Create IR equivalence checker
- Create functional equivalence checker (for code)

Phase 2 (Weeks 3-4): Testing Infrastructure
- Build robustness test suite
- Integrate with pytest
- Add to CI/CD pipeline
- Create baseline measurements

Phase 3 (Weeks 5-6): DSPy Integration
- Augment DSPy training data with variants
- Implement robustness-aware loss
- Re-optimize signatures with new data
- Validate improvements

Phase 4 (Weeks 7-8): Production Integration
- Add robustness metrics to benchmarks
- Create monitoring dashboard
- Set quality gates
- Document best practices
```

---

## 4. Technical Architecture

### 4.1 New Components

```
lift_sys/
├── robustness/                      # New module
│   ├── __init__.py
│   ├── paraphrase_generator.py     # NL prompt paraphrasing
│   ├── ir_variant_generator.py     # IR variant generation
│   ├── equivalence_checker.py      # IR/code equivalence
│   ├── sensitivity_analyzer.py     # Sensitivity measurement
│   ├── robustness_metrics.py       # Metric calculations
│   └── statistical_tests.py        # Wilcoxon, etc.
│
├── dspy_signatures/
│   ├── robustness_optimizer.py     # Robustness-aware DSPy optimization
│   └── paraphrase_signatures.py    # Signatures for paraphrase generation
│
└── validation/
    └── robustness_validator.py     # Integration with existing validation
```

### 4.2 Component Details

#### ParaphraseGenerator
```python
class ParaphraseGenerator:
    """Generates paraphrase variants of NL prompts."""

    def generate_lexical_variants(self, prompt: str) -> list[str]:
        """Replace words with synonyms."""
        # "create" → "implement", "list" → "array"

    def generate_structural_variants(self, prompt: str) -> list[str]:
        """Reorder independent clauses."""
        # "sort then filter" → "filter then sort"

    def generate_stylistic_variants(self, prompt: str) -> list[str]:
        """Active/passive, imperative/declarative."""
        # "Create X" → "X should be created"

    def generate_all_variants(self, prompt: str, max_variants: int = 10) -> list[str]:
        """Generate diverse set of paraphrases."""
```

#### IRVariantGenerator
```python
class IRVariantGenerator:
    """Generates semantic-preserving IR variants."""

    def rewrite_naming(self, ir: IR, style: NamingStyle) -> IR:
        """Convert identifier naming style."""
        # snake_case → camelCase

    def reorder_effects(self, ir: IR) -> IR:
        """Reorder independent effects."""

    def rephrase_assertions(self, ir: IR) -> IR:
        """Logically equivalent assertion rewrites."""

    def generate_variants(self, ir: IR, max_variants: int = 5) -> list[IR]:
        """Generate all variants."""
```

#### EquivalenceChecker
```python
class EquivalenceChecker:
    """Checks equivalence of IRs and code."""

    def ir_equivalent(self, ir1: IR, ir2: IR) -> bool:
        """Check if two IRs are semantically equivalent."""
        # - Same signature (modulo naming)
        # - Equivalent effects
        # - Logically equivalent assertions

    def code_equivalent(self, code1: str, code2: str, test_inputs: list) -> bool:
        """Check if two code snippets are functionally equivalent."""
        # Execute both, compare outputs
```

#### SensitivityAnalyzer
```python
class SensitivityAnalyzer:
    """Measures sensitivity to input variations."""

    def measure_ir_sensitivity(
        self,
        prompts: list[str],
        generate_ir: Callable[[str], IR]
    ) -> float:
        """Measure IR generation sensitivity."""
        irs = [generate_ir(p) for p in prompts]
        non_equivalent = sum(
            not self.checker.ir_equivalent(irs[0], ir)
            for ir in irs[1:]
        )
        return non_equivalent / (len(prompts) - 1)

    def measure_code_sensitivity(
        self,
        ir_variants: list[IR],
        generate_code: Callable[[IR], str],
        test_inputs: list
    ) -> float:
        """Measure code generation sensitivity."""
        codes = [generate_code(ir) for ir in ir_variants]
        non_equivalent = sum(
            not self.checker.code_equivalent(codes[0], code, test_inputs)
            for code in codes[1:]
        )
        return non_equivalent / (len(ir_variants) - 1)
```

### 4.3 Integration with Existing Architecture

```python
# In DSPy signature optimization
from lift_sys.robustness import ParaphraseGenerator, SensitivityAnalyzer

def optimize_signature_with_robustness(signature, train_data):
    # 1. Augment training data with paraphrases
    paraphraser = ParaphraseGenerator()
    augmented_data = []
    for prompt, ir in train_data:
        variants = paraphraser.generate_all_variants(prompt, max_variants=5)
        augmented_data.extend([(v, ir) for v in variants])

    # 2. Optimize with robustness metric
    analyzer = SensitivityAnalyzer()
    def robustness_metric(signature, dev_set):
        accuracy = traditional_accuracy(signature, dev_set)
        robustness = 1 - analyzer.measure_ir_sensitivity(...)
        return 0.7 * accuracy + 0.3 * robustness

    optimizer = MIPROv2(metric=robustness_metric)
    return optimizer.compile(signature, augmented_data)
```

```python
# In benchmarking
from lift_sys.robustness import RobustnessMetrics

def run_benchmark_with_robustness(test_suite):
    results = {
        "accuracy": measure_accuracy(test_suite),
        "ir_robustness": RobustnessMetrics.ir_robustness(test_suite),
        "code_robustness": RobustnessMetrics.code_robustness(test_suite),
    }
    results["combined_score"] = (
        0.5 * results["accuracy"] +
        0.25 * results["ir_robustness"] +
        0.25 * results["code_robustness"]
    )
    return results
```

---

## 5. Implementation Roadmap

### 5.1 Phase 1: Foundation (Weeks 1-2)

**Goal**: Build core robustness testing infrastructure

**Tasks**:
1. **Create `lift_sys/robustness/` module** (2 days)
   - Set up package structure
   - Add to pyproject.toml dependencies (spacy, nltk if needed)

2. **Implement ParaphraseGenerator** (3 days)
   - Lexical variants (synonym replacement via WordNet)
   - Structural variants (parse tree manipulation)
   - Stylistic variants (rule-based transformations)
   - Unit tests (>90% coverage)

3. **Implement IRVariantGenerator** (3 days)
   - Naming style conversion (snake_case ↔ camelCase)
   - Effect reordering (respect dependencies)
   - Assertion rephrasing
   - Unit tests

4. **Implement EquivalenceChecker** (4 days)
   - IR equivalence (signature, effects, assertions)
   - Code equivalence (execution-based)
   - Handle edge cases (timeouts, errors)
   - Unit tests

**Deliverables**:
- Working paraphrase generation
- Working IR variant generation
- Reliable equivalence checking
- >90% test coverage

**Success Criteria**:
- Can generate 10+ paraphrases for any prompt
- Can generate 5+ IR variants
- Equivalence checker agrees with human judgment >95%

### 5.2 Phase 2: Testing Infrastructure (Weeks 3-4)

**Goal**: Integrate robustness testing into lift-sys test suite

**Tasks**:
1. **Create robustness test suite** (3 days)
   - `tests/robustness/test_ir_generation.py`
   - `tests/robustness/test_code_generation.py`
   - Golden set of prompts/IRs with known variants

2. **Implement SensitivityAnalyzer** (2 days)
   - IR sensitivity measurement
   - Code sensitivity measurement
   - Statistical tests (Wilcoxon)

3. **Integrate with CI/CD** (2 days)
   - Add robustness tests to GitHub Actions
   - Set initial thresholds (warn if >10% sensitivity)
   - Report metrics in CI output

4. **Create baseline measurements** (3 days)
   - Run on current lift-sys (before DSPy)
   - Document baseline sensitivity scores
   - Identify most fragile prompts/IRs

**Deliverables**:
- Automated robustness tests in CI
- Baseline sensitivity measurements
- Documentation of fragile areas

**Success Criteria**:
- Robustness tests run on every PR
- Baseline established for comparison
- Can identify specific prompts with >15% sensitivity

### 5.3 Phase 3: DSPy Integration (Weeks 5-6)

**Goal**: Enhance DSPy optimization with robustness awareness

**Tasks**:
1. **Create robustness-aware DSPy optimizer** (3 days)
   - Extend MIPROv2 with robustness metric
   - Implement data augmentation pipeline
   - Handle paraphrase caching

2. **Generate augmented training data** (2 days)
   - Apply to existing DSPy training sets
   - Validate paraphrase quality (manual review of sample)
   - Store in structured format

3. **Re-optimize existing signatures** (3 days)
   - Run MIPROv2 with augmented data
   - Compare old vs new signatures
   - A/B test on held-out set

4. **Validate improvements** (2 days)
   - Measure robustness improvement
   - Ensure accuracy didn't degrade
   - Document before/after metrics

**Deliverables**:
- Robustness-optimized DSPy signatures
- Training data with paraphrases
- Performance comparison report

**Success Criteria**:
- 10%+ improvement in IR robustness
- No accuracy regression (>1%)
- New signatures handle unseen paraphrases better

### 5.4 Phase 4: Production Integration (Weeks 7-8)

**Goal**: Make robustness a first-class production metric

**Tasks**:
1. **Extend performance_benchmark.py** (2 days)
   - Add robustness metrics
   - Integrate SensitivityAnalyzer
   - Update result format

2. **Create robustness dashboard** (3 days)
   - Visualization of robustness over time
   - Per-signature robustness scores
   - Identify regressions quickly

3. **Set quality gates** (2 days)
   - Define acceptable thresholds
   - Block PRs that degrade robustness >5%
   - Document in CONTRIBUTING.md

4. **Documentation and training** (3 days)
   - Write robustness testing guide
   - Update developer docs
   - Create examples for common cases

**Deliverables**:
- Robustness in production benchmarks
- Monitoring dashboard
- Quality gates in CI
- Comprehensive documentation

**Success Criteria**:
- Robustness metrics visible in all benchmark runs
- Dashboard shows trends over time
- Team understands how to use robustness tools

### 5.5 Timeline Summary

```
Week 1-2:  Foundation (generators, checkers)
Week 3-4:  Testing Infrastructure (CI, baselines)
Week 5-6:  DSPy Integration (optimization, validation)
Week 7-8:  Production (benchmarks, dashboard, docs)
```

**Total Effort**: 8 weeks, ~1 FTE
**Dependencies**: Can start immediately, no blockers
**Risk**: Low (additive work, doesn't modify existing code)

---

## 6. Success Metrics

### 6.1 Quantitative Metrics

| Metric | Baseline (Est.) | Target | Measurement |
|--------|-----------------|--------|-------------|
| **IR Sensitivity** | Unknown (10-15%?) | <3% | % of paraphrases producing non-equivalent IR |
| **Code Sensitivity** | Unknown (8-10%?) | <3% | % of IR variants producing non-equivalent code |
| **DSPy Robustness Gain** | N/A | +10% | Improvement from augmented training |
| **Test Coverage** | 0% | >90% | Robustness tests in CI |
| **Fragile Signature Detection** | Manual | Automated | Signatures with >10% sensitivity flagged |

### 6.2 Qualitative Success Criteria

**Phase 1 Success**:
- ✅ Developers can generate paraphrases for any prompt
- ✅ IR variants are semantically equivalent (manual validation)
- ✅ Equivalence checker is reliable (>95% agreement with humans)

**Phase 2 Success**:
- ✅ Robustness tests run automatically on every PR
- ✅ Team understands baseline robustness of current system
- ✅ Can prioritize fixing most fragile prompts

**Phase 3 Success**:
- ✅ DSPy signatures are measurably more robust
- ✅ Accuracy maintained or improved
- ✅ Augmented training data is reusable for future signatures

**Phase 4 Success**:
- ✅ Robustness is a standard metric in all discussions
- ✅ Dashboard provides actionable insights
- ✅ Quality gates prevent robustness regressions

### 6.3 Long-Term Impact Metrics

**After 6 months**:
- IR sensitivity: <2% (vs TokDrift's 8-9%)
- Code sensitivity: <2%
- Production incidents due to prompt variations: 0
- Developer confidence in IR generation: High

**After 1 year**:
- Robustness becomes a competitive advantage
- Published case study on TokDrift adaptation
- Contributions back to TokDrift project (if applicable)

---

## 7. Risk Analysis

### 7.1 Technical Risks

#### Risk 1: Paraphrase Quality
**Description**: Generated paraphrases may not preserve semantic meaning
**Likelihood**: Medium
**Impact**: High (false positives in robustness tests)
**Mitigation**:
- Manual validation of paraphrase samples
- Use high-quality paraphrase models (T5, GPT-4)
- Human-in-the-loop for critical test cases

#### Risk 2: Equivalence Checking Complexity
**Description**: Determining IR/code equivalence is undecidable in general
**Likelihood**: High
**Impact**: Medium (some false positives/negatives)
**Mitigation**:
- Focus on practical heuristics (not perfect proofs)
- Conservative: mark uncertain cases as non-equivalent
- Use SMT solvers for assertion equivalence where possible

#### Risk 3: Performance Overhead
**Description**: Robustness tests may slow down CI
**Likelihood**: Medium
**Impact**: Low (CI time increases)
**Mitigation**:
- Run full robustness suite nightly, not on every PR
- Sample-based testing (10% of test suite per PR)
- Parallelize robustness tests

#### Risk 4: DSPy Optimization Complexity
**Description**: Robustness-aware optimization may not converge
**Likelihood**: Low
**Impact**: Medium (no improvement from effort)
**Mitigation**:
- Start with simple weighted metric (0.7 accuracy + 0.3 robustness)
- Fall back to accuracy-only if optimization fails
- Iteratively tune hyperparameters

### 7.2 Organizational Risks

#### Risk 1: Scope Creep
**Description**: Robustness work expands beyond original plan
**Likelihood**: Medium
**Impact**: Medium (delays other priorities)
**Mitigation**:
- Strict phase gates: don't move to next phase until current is done
- Time-box each phase to 2 weeks max
- De-scope if falling behind (e.g., skip dashboard in Phase 4)

#### Risk 2: Lack of Buy-In
**Description**: Team doesn't see value, doesn't use robustness tools
**Likelihood**: Low
**Impact**: High (wasted effort)
**Mitigation**:
- Demo early wins (find fragile prompts in Phase 2)
- Show robustness improvements from DSPy optimization (Phase 3)
- Make tools easy to use (one command to run robustness tests)

### 7.3 Risk Mitigation Summary

**Overall Risk Level**: **Low-Medium**
- Most risks have clear mitigations
- Work is additive (doesn't modify core system)
- Can be de-scoped if needed without major impact

---

## 8. Alternatives Considered

### Alternative 1: Manual Robustness Testing
**Description**: Have developers manually create paraphrase variants
**Pros**: No tooling needed, human quality
**Cons**: Not scalable, inconsistent coverage, labor-intensive
**Verdict**: ❌ Rejected. Need systematic, automated approach.

### Alternative 2: Ignore Robustness, Focus on Accuracy
**Description**: Prioritize 85% accuracy target, defer robustness
**Pros**: Simpler, fewer moving parts
**Cons**: Hidden brittleness in production, no improvement path
**Verdict**: ❌ Rejected. Robustness is critical for production reliability.

### Alternative 3: Use Third-Party Robustness Tools
**Description**: Adopt existing robustness testing frameworks (CheckList, etc.)
**Pros**: Proven tools, community support
**Cons**: Not designed for IR generation, would need heavy customization
**Verdict**: ⚠️ Considered but adapted. TokDrift methodology is more relevant.

### Alternative 4: Build Robustness into IR Schema
**Description**: Extend IR with robustness metadata (e.g., "robustness_score")
**Pros**: Robustness becomes first-class in IR
**Cons**: Couples robustness to IR design, harder to evolve independently
**Verdict**: 🤔 Possible future enhancement, not initial approach.

### Alternative 5: Statistical Ensembles
**Description**: Generate multiple IRs/codes, pick majority vote
**Pros**: Can improve robustness without changing prompts
**Cons**: 3-5x cost (multiple LLM calls), slower
**Verdict**: 🤔 Complementary. Could use for critical production cases.

---

## 9. References

### 9.1 TokDrift Research

1. **Paper**: Li, Y., Deng, Y., & Nie, P. (2024). *TokDrift: When LLM Speaks in Subwords but Code Speaks in Grammar*. arXiv:2510.14972. https://arxiv.org/abs/2510.14972

2. **Repository**: https://github.com/uw-swag/tokdrift

3. **HTML Paper**: https://arxiv.org/html/2510.14972v1

### 9.2 Related Research

4. **CheckList**: Ribeiro, M. T., Wu, T., Guestrin, C., & Singh, S. (2020). *Beyond Accuracy: Behavioral Testing of NLP models with CheckList*. ACL 2020.

5. **Adversarial Robustness**: Goodfellow, I. J., Shlens, J., & Szegedy, C. (2014). *Explaining and Harnessing Adversarial Examples*. ICLR 2015.

6. **Paraphrase Generation**: Wieting, J., & Gimpel, K. (2018). *ParaNMT-50M: Pushing the Limits of Paraphrastic Sentence Embeddings with Millions of Machine Translations*. ACL 2018.

### 9.3 lift-sys Internal Docs

7. **DSPy Architecture Proposal**: `docs/planning/DSPY_PYDANTIC_AI_ARCHITECTURE_PROPOSAL.md`

8. **Semantic IR Roadmap**: `SEMANTIC_IR_ROADMAP.md`

9. **Performance Benchmarks**: `debug/performance_benchmark.py`

### 9.4 Tools and Frameworks

10. **DSPy**: https://github.com/stanfordnlp/dspy

11. **Pydantic AI**: https://ai.pydantic.dev/

12. **XGrammar**: https://github.com/mlc-ai/xgrammar

---

## Appendix A: Example Paraphrase Variants

### Example 1: Simple Function Creation

**Canonical Prompt**:
```
Create a function that sorts a list of numbers in ascending order
```

**Paraphrase Variants**:
1. "Write a function to sort a numeric list in ascending order"
2. "Implement ascending number sorting for a list"
3. "Build a function that orders numbers from smallest to largest"
4. "Create an ascending sorter for numeric lists"
5. "Make a function to arrange numbers in increasing order"

**Expected IR** (all variants should produce equivalent):
```python
{
  "intent": "Sort numbers in ascending order",
  "signature": {
    "name": "sort_numbers",  # or any reasonable name
    "parameters": [{"name": "numbers", "type": "list[int|float]"}],
    "return_type": "list[int|float]"
  },
  "effects": [],
  "assertions": [
    {"type": "sorted", "order": "ascending"}
  ]
}
```

### Example 2: File Processing

**Canonical Prompt**:
```
Create a function that reads a JSON file and validates its schema
```

**Paraphrase Variants**:
1. "Write a function to load and validate a JSON file's structure"
2. "Implement JSON file reading with schema validation"
3. "Build a validator that reads JSON files and checks their schema"
4. "Create a function for JSON schema validation from a file"
5. "Make a JSON file reader with built-in schema checks"

**Expected IR**:
```python
{
  "intent": "Read and validate JSON file",
  "signature": {
    "name": "validate_json_file",
    "parameters": [
      {"name": "filepath", "type": "str"},
      {"name": "schema", "type": "dict"}
    ],
    "return_type": "bool | dict"
  },
  "effects": [
    {"type": "file_read", "target": "filepath"}
  ],
  "assertions": [
    {"type": "file_exists", "target": "filepath"},
    {"type": "valid_json", "target": "file_content"}
  ]
}
```

---

## Appendix B: IR Variant Examples

### Example 1: Naming Convention Variants

**Original IR** (snake_case):
```python
{
  "signature": {
    "name": "process_user_data",
    "parameters": [
      {"name": "user_id", "type": "int"},
      {"name": "data_source", "type": "str"}
    ],
    "return_type": "dict"
  },
  "effects": [
    {"type": "database_read", "target": "user_table"},
    {"type": "file_write", "target": "output_file"}
  ]
}
```

**Variant 1** (camelCase):
```python
{
  "signature": {
    "name": "processUserData",
    "parameters": [
      {"name": "userId", "type": "int"},
      {"name": "dataSource", "type": "str"}
    ],
    "return_type": "dict"
  },
  "effects": [
    {"type": "databaseRead", "target": "userTable"},
    {"type": "fileWrite", "target": "outputFile"}
  ]
}
```

**Variant 2** (PascalCase):
```python
{
  "signature": {
    "name": "ProcessUserData",
    "parameters": [
      {"name": "UserId", "type": "int"},
      {"name": "DataSource", "type": "str"}
    ],
    "return_type": "dict"
  },
  "effects": [
    {"type": "DatabaseRead", "target": "UserTable"},
    {"type": "FileWrite", "target": "OutputFile"}
  ]
}
```

**Expected**: All three variants should produce **functionally equivalent code**.

---

## Appendix C: Statistical Significance Testing

### Wilcoxon Signed-Rank Test

TokDrift uses Wilcoxon signed-rank test to determine if differences in accuracy between original and rewritten code are statistically significant.

**Procedure**:
1. For each test sample, compute `diff = accuracy_original - accuracy_rewritten`
2. Rank absolute differences
3. Sum ranks for positive and negative differences
4. Compute test statistic and p-value
5. If `p < 0.05`, difference is statistically significant

**Application to lift-sys**:
```python
from scipy.stats import wilcoxon

def test_ir_robustness_significance(prompts, canonical_ir):
    """Test if paraphrase variants produce statistically different IRs."""
    canonical_accuracy = [evaluate_ir(canonical_ir, test) for test in tests]

    paraphrase_accuracies = []
    for prompt in prompts:
        ir = generate_ir(prompt)
        acc = [evaluate_ir(ir, test) for test in tests]
        paraphrase_accuracies.append(acc)

    # Compare each paraphrase to canonical
    for para_acc in paraphrase_accuracies:
        stat, p_value = wilcoxon(canonical_accuracy, para_acc)
        if p_value < 0.05:
            print(f"Significant difference detected (p={p_value})")
```

---

**End of Proposal**

**Next Steps**:
1. Review this proposal with lift-sys team
2. Get approval to proceed with Phase 1
3. Create beads for implementation tasks
4. Begin work on paraphrase generation infrastructure

**Questions for Review**:
- Is the 8-week timeline acceptable?
- Should we prioritize any pillar over others?
- Are there additional robustness concerns not covered?
- Should we start with a pilot (e.g., only Pillar 1) before full commitment?
