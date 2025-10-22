# Fragile Prompts and IRs Registry

**Last Updated**: 2025-10-22
**Status**: Phase 2 - Infrastructure Complete (Awaiting Baseline Measurements)

## Overview

This document tracks prompts and IRs that exhibit low robustness (high sensitivity to semantic-preserving transformations). These areas require special attention and potential optimization in Phase 3.

## What Makes a Prompt/IR "Fragile"?

**Criteria:**
- **Robustness < 90%** (sensitivity > 10%)
- **Non-deterministic outputs** across semantically equivalent inputs
- **Statistical significance** in Wilcoxon test (p < 0.05)
- **Multiple valid interpretations** that lead to different IRs

**Impact:**
- Unreliable IR generation
- Inconsistent code generation
- Poor user experience (similar prompts → different results)

## Currently Identified Fragile Areas

> **Note**: This section will be populated after baseline measurements in Phase 2.
> Run `uv run pytest tests/robustness/test_baseline_robustness.py -v` to identify fragile areas.

### Fragile Prompts (To Be Measured)

#### Email Validation (Hypothetical Example)

**Prompt:** "Create a function to validate emails"

**Metrics (Example):**
- Robustness: 85% (target: 97%)
- Sensitivity: 15% (target: <3%)
- Wilcoxon p-value: 0.02 (significant)

**Issue:**
Multiple valid interpretations:
- Regex pattern matching
- DNS lookup validation
- SMTP server check
- Domain existence verification

**Generated IR Variance:**
```python
# Paraphrase 1: "Validate email addresses"
IR(
    intent="Check email format with regex",
    signature=SigClause(name="validate_email", ...),
    effects=["Match against email regex pattern"]
)

# Paraphrase 2: "Check if emails are valid"
IR(
    intent="Verify email deliverability",
    signature=SigClause(name="check_email", ...),
    effects=["Lookup domain DNS records", "Verify MX records"]
)
```

**Mitigation:**
Use more specific prompts:
- ✅ "Create a function to validate email format using regex"
- ✅ "Create a function to check email deliverability via DNS"

**Status:** Pending measurement

---

#### Sorting with Edge Cases (Hypothetical Example)

**Prompt:** "Sort a list"

**Metrics (Example):**
- Robustness: 88%
- Sensitivity: 12%

**Issue:**
Ambiguous about:
- In-place vs. returning new list
- Ascending vs. descending
- Handling of duplicates
- Handling of None/null values

**Mitigation:**
- ✅ "Create a function that returns a new sorted list in ascending order"
- ✅ "Create a function that sorts a list in-place"

**Status:** Pending measurement

---

## Fragile IR Patterns (To Be Measured)

### Effect Ordering Ambiguity (Hypothetical)

**Issue:** IRs with independent effects may generate code with different orderings.

**Example:**
```python
IR(
    effects=[
        "Validate input",
        "Log operation",
        "Check permissions"
    ]
)

# May generate:
# Version 1: validate → log → check_perms
# Version 2: check_perms → validate → log
```

**Mitigation:** Specify dependencies or canonical ordering.

**Status:** Pending measurement

---

## Measurement Process

### Step 1: Run Baseline Tests

```bash
# Run baseline robustness measurements
uv run pytest tests/robustness/test_baseline_robustness.py -v \
  > /tmp/baseline_results.txt

# Generate report
python scripts/robustness/generate_report.py \
  --input /tmp/baseline_results.txt \
  --format markdown \
  --output docs/robustness/BASELINE_REPORT.md
```

### Step 2: Identify Low-Robustness Cases

```bash
# Parse baseline results for robustness < 90%
grep -A 5 "Robustness:" /tmp/baseline_results.txt | \
  awk '/[0-8][0-9]\.[0-9]+%/ {print}'
```

### Step 3: Document Findings

For each fragile case, document:
1. **Prompt/IR**: The input that shows fragility
2. **Metrics**: Robustness, sensitivity, p-value
3. **Issue**: Root cause of fragility
4. **Variance**: Examples of different outputs
5. **Mitigation**: How to improve robustness
6. **Status**: Pending fix, In progress, Resolved

### Step 4: Create Issues

```bash
# Create GitHub issue for each fragile area
gh issue create \
  --title "Fragile prompt: [description]" \
  --body "Robustness: X%, Target: 97%\n\nSee FRAGILE_PROMPTS.md for details" \
  --label "robustness,enhancement"
```

## Improvement Strategies

### Strategy 1: Prompt Engineering

**Problem:** Ambiguous prompts lead to multiple interpretations.

**Solution:** Make prompts more specific and constrained.

**Example:**
```
❌ "Create a function to handle errors"
✅ "Create a function that catches exceptions and logs them to stderr"
```

**Impact:** Reduces interpretation variance, improves robustness.

### Strategy 2: IR Constraints

**Problem:** IRs allow too much flexibility in code generation.

**Solution:** Add constraints and canonical orderings.

**Example:**
```python
IR(
    effects=[
        "Validate input",  # MUST be first
        "Process data",
        "Return result"
    ],
    constraints=[
        "effects[0] must execute before effects[1]"
    ]
)
```

**Impact:** Reduces code generation variance.

### Strategy 3: DSPy Optimization (Phase 3)

**Problem:** Manual prompt engineering is time-consuming.

**Solution:** Use DSPy to automatically optimize prompts for robustness.

**Approach:**
```python
from dspy import Signature, Module
from lift_sys.robustness import SensitivityAnalyzer

class RobustIRGenerator(Module):
    def __init__(self):
        self.signature = Signature("prompt -> ir")
        self.analyzer = SensitivityAnalyzer()

    def forward(self, prompt):
        # Generate IR
        ir = self.signature(prompt)

        # Measure robustness
        paraphrases = generate_paraphrases(prompt)
        robustness = self.analyzer.measure_ir_sensitivity(
            [prompt, *paraphrases],
            lambda p: self.signature(p)
        )

        # Optimize if robustness < threshold
        if robustness.robustness < 0.97:
            self.signature = optimize_for_robustness(self.signature)

        return ir
```

**Impact:** Automated robustness improvement.

### Strategy 4: Training Data Augmentation

**Problem:** Limited training data for edge cases.

**Solution:** Generate synthetic training data with known robustness properties.

**Approach:**
- Use ParaphraseGenerator to create variants
- Verify equivalence with EquivalenceChecker
- Train on augmented dataset
- Validate robustness improvement

**Impact:** Improved model robustness through better training.

## Tracking and Metrics

### Per-Prompt Robustness Scores

**Goal:** Track robustness for each prompt category.

**Format:**
```json
{
  "prompt": "Create a function to validate emails",
  "category": "validation",
  "robustness": 0.85,
  "sensitivity": 0.15,
  "last_measured": "2025-10-22",
  "status": "fragile",
  "mitigation": "pending"
}
```

### Improvement Tracking

**Goal:** Monitor robustness improvements over time.

**Format:**
```json
{
  "prompt_id": "email_validation",
  "history": [
    {"date": "2025-10-22", "robustness": 0.85, "phase": 2},
    {"date": "2025-11-15", "robustness": 0.92, "phase": 3},
    {"date": "2025-12-01", "robustness": 0.98, "phase": 3}
  ],
  "improvement": "+13% (Phase 2 → Phase 3)"
}
```

## Phase Roadmap

### Phase 2 (Current)
- ✅ Infrastructure for identifying fragile prompts
- ✅ Baseline measurement framework
- 🔄 Populate this registry with actual measurements

### Phase 3 (DSPy Integration)
- Use DSPy to optimize fragile prompts
- Implement robustness-aware signature optimization
- Generate augmented training data
- Re-measure and validate improvements

### Phase 4 (Production)
- Automated fragile prompt detection in CI
- Real-time robustness monitoring
- Dashboard visualization of fragile areas
- Continuous optimization pipeline

## Contributing

### Adding New Fragile Cases

**Required Information:**
1. Prompt/IR that shows fragility
2. Measured metrics (robustness, sensitivity, p-value)
3. Root cause analysis
4. Example output variance
5. Proposed mitigation
6. Issue/PR links

**Template:**
```markdown
#### [Brief Description]

**Prompt:** "..."

**Metrics:**
- Robustness: X%
- Sensitivity: Y%
- Wilcoxon p-value: Z

**Issue:**
[Explanation of why it's fragile]

**Variance:**
\`\`\`python
# Example outputs showing variance
\`\`\`

**Mitigation:**
- Option 1: ...
- Option 2: ...

**Status:** [Pending/In Progress/Resolved]
**Related Issues:** #123, #456
**Phase:** [2/3/4]
```

### Updating Measurements

**When to Update:**
- After running baseline measurements
- After implementing mitigation strategies
- Monthly (via nightly CI runs)
- After Phase transitions

**How to Update:**
```bash
# Re-run measurements
uv run pytest tests/robustness/test_baseline_robustness.py -v

# Update this document with new metrics
vim docs/robustness/FRAGILE_PROMPTS.md

# Commit changes
git add docs/robustness/FRAGILE_PROMPTS.md
git commit -m "docs: Update fragile prompts with latest measurements"
```

## References

- **Quality Gates**: `QUALITY_GATES.md`
- **Test Suite**: `tests/robustness/README.md`
- **TokDrift Paper**: arXiv:2510.14972
- **Baseline Tests**: `tests/robustness/test_baseline_robustness.py`

---

**Next Steps:**
1. Run baseline measurements (Phase 2 completion)
2. Populate this document with actual fragile cases
3. Create GitHub issues for each fragile area
4. Plan mitigation strategies for Phase 3
