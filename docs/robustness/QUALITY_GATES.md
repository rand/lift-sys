# Robustness Quality Gates

**Last Updated**: 2025-10-22
**Status**: Active (Phase 2 Complete)

## Overview

Quality gates ensure robustness standards are maintained across the lift-sys codebase. These gates are enforced in CI/CD and provide early warning when system robustness degrades.

## Quality Gate Thresholds

### Primary Metrics

| Metric | Target | Warning | Failure | Description |
|--------|--------|---------|---------|-------------|
| **Pass Rate** | ≥90% | <90% | <80% | Percentage of robustness tests passing |
| **Robustness Score** | ≥97% | <95% | <90% | Average robustness across all tests |
| **Sensitivity Score** | ≤3% | >5% | >10% | Average sensitivity to variations |

### Secondary Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **Paraphrase Robustness** | ≥97% | IR generation consistency across prompt variants |
| **IR Variant Robustness** | ≥99% | Code generation consistency across IR variants |
| **E2E Robustness** | ≥95% | Full pipeline robustness (NLP → IR → Code) |

## Quality Gate Levels

### ✅ PASSED (Green)

**Criteria:**
- Pass rate ≥ 90%
- Average robustness ≥ 97%
- Average sensitivity ≤ 3%

**Action:** None required. Continue normal development.

**PR Status:** ✅ Approved for merge

### ⚠️ WARNING (Yellow)

**Criteria:**
- 80% ≤ Pass rate < 90%
- OR 90% ≤ Robustness < 95%
- OR 5% < Sensitivity ≤ 10%

**Action:**
1. Review failing tests
2. Investigate robustness degradation
3. Consider improvements before merge
4. Document known issues

**PR Status:** ⚠️ Requires review and justification

**Example Warning Message:**
```
⚠️  WARNING: Robustness pass rate 85% below warning threshold 90%

Tests Failed: 3/20
Average Robustness: 92%
Average Sensitivity: 8%

Action Required:
- Review failing tests in robustness-output.txt
- Investigate causes of sensitivity increase
- Document findings in PR description
```

### ❌ FAILED (Red)

**Criteria:**
- Pass rate < 80%
- OR Robustness < 90%
- OR Sensitivity > 10%

**Action:**
1. **DO NOT MERGE** - Critical robustness issues
2. Investigate root cause immediately
3. Fix failing tests or revert changes
4. Re-run robustness tests
5. Document fixes in commit messages

**PR Status:** ❌ Blocked until fixed

**Example Failure Message:**
```
❌ CRITICAL: Robustness pass rate 75% below failure threshold 80%

Tests Failed: 5/20
Average Robustness: 85%
Average Sensitivity: 15%

Action Required:
- DO NOT MERGE - Critical robustness degradation
- Review all failing tests immediately
- Consider reverting recent changes
- Document root cause analysis
```

## CI/CD Integration

### GitHub Actions Workflow

**Trigger Events:**
- `pull_request` to `main` or `develop`
- `push` to `main` (post-merge validation)
- `schedule` at 2 AM UTC daily (nightly baseline)
- `workflow_dispatch` (manual trigger)

**Workflow Steps:**
1. Install dependencies (Python, spaCy, NLTK)
2. Run robustness test suite
3. Parse metrics from output
4. Check quality gates
5. Post PR comment with results
6. Upload artifacts (results.xml, output.txt)
7. Generate summary report

**Configuration:**
```yaml
# .github/workflows/robustness.yml
jobs:
  robustness-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Check quality gates
        run: |
          PASS_RATE=${{ steps.metrics.outputs.pass_rate }}
          if (( $PASS_RATE < 80 )); then
            echo "FAILED: Critical robustness issues"
            exit 1
          elif (( $PASS_RATE < 90 )); then
            echo "WARNING: Robustness below target"
          fi
```

### Local Development

**Run Quality Gates Locally:**
```bash
# Run robustness tests
uv run pytest tests/robustness/ -v > /tmp/robustness_output.txt

# Generate report
python scripts/robustness/generate_report.py \
  --input /tmp/robustness_output.txt \
  --format markdown

# Check quality gates (script exits with code 0=pass, 1=fail)
python scripts/robustness/generate_report.py \
  --input /tmp/robustness_output.txt \
  --format json \
  --output /tmp/robustness_report.json

echo "Exit code: $?"
```

## Handling Quality Gate Violations

### WARNING Level Response

**Step 1: Identify Failing Tests**
```bash
# View detailed test output
cat robustness-output.txt | grep FAILED

# Extract specific failure reasons
uv run pytest tests/robustness/ -v --tb=short
```

**Step 2: Analyze Robustness Degradation**
- Compare current metrics to baseline
- Identify which component degraded (paraphrase, IR variant, E2E)
- Review recent code changes that might impact robustness

**Step 3: Document Findings**
- Add PR comment explaining the warning
- Document known limitations if acceptable
- Create follow-up issue if not fixing immediately

**Example PR Comment:**
```markdown
## ⚠️ Robustness Warning

**Metrics:**
- Pass Rate: 85% (target: 90%)
- Robustness: 92% (target: 97%)

**Analysis:**
- Paraphrase robustness tests show 2 failures
- Related to new prompt templates added in commit abc123
- Templates are more strict about formatting, causing sensitivity

**Justification:**
- Stricter templates improve IR quality
- Tradeoff: Slightly lower robustness for better precision
- Documented in `docs/robustness/KNOWN_ISSUES.md`

**Follow-up:**
- Created issue #456 to improve template robustness
- Will address in Phase 3 optimization
```

### FAILURE Level Response

**Immediate Actions:**
1. **Stop merge** - Do not proceed until fixed
2. **Run git bisect** to find problematic commit
3. **Revert or fix** the offending changes
4. **Re-test** to confirm resolution

**Investigation Process:**
```bash
# Find the failing commit
git bisect start
git bisect bad HEAD
git bisect good <last-known-good-commit>

# At each step:
uv run pytest tests/robustness/ -v

# Mark commits as good/bad
git bisect good  # if tests pass
git bisect bad   # if tests fail

# When found:
git bisect reset
git show <problematic-commit>
```

**Resolution Options:**

**Option 1: Revert**
```bash
git revert <problematic-commit>
git push
```

**Option 2: Fix**
```bash
# Fix the issue
git add .
git commit -m "fix: Restore robustness in <component>

Root cause: <explanation>
Fix: <solution>
Tests: Robustness pass rate restored to 92%"
git push
```

## Baseline Tracking

### Establishing Baselines

**Initial Baseline (Phase 2):**
```bash
# Run baseline measurement tests
uv run pytest tests/robustness/test_baseline_robustness.py -v

# Update expected_results.json
# (Manual step - results reviewed before updating)
```

**Baseline Contents:**
```json
{
  "paraphrase_robustness": {
    "simple_functions": {
      "target_robustness": 0.97,
      "warning_threshold": 0.90,
      "baseline": 0.95  // Measured value
    }
  }
}
```

### Updating Baselines

**When to Update:**
- After major robustness improvements
- Monthly (via nightly build analysis)
- After Phase transitions (Phase 2 → Phase 3)
- When quality gates are consistently exceeded

**How to Update:**
```bash
# Trigger baseline update workflow
gh workflow run robustness.yml -f update_baseline=true

# Or manually:
uv run pytest tests/robustness/test_baseline_robustness.py -v
# Review results
# Update tests/robustness/fixtures/expected_results.json
git add tests/robustness/fixtures/expected_results.json
git commit -m "chore: Update robustness baselines (2025-10-22)"
```

## Fragile Prompt/IR Identification

See **`FRAGILE_PROMPTS.md`** for detailed list of known fragile areas.

**Criteria for "Fragile":**
- Robustness < 90% (sensitivity > 10%)
- Non-deterministic outputs across paraphrases
- Statistical significance in Wilcoxon test (p < 0.05)

**Example:**
```
Fragile Prompt: "Create a function to validate emails"
  - Robustness: 85%
  - Sensitivity: 15%
  - Issue: Multiple valid interpretations (regex vs. DNS check)
  - Mitigation: Use more specific prompts ("Create a function to validate email format using regex")
```

## Continuous Improvement

### Phase 2 → Phase 3 Goals

**Current (Phase 2):**
- Infrastructure in place
- Quality gates enforced
- Baseline measurements available

**Target (Phase 3):**
- DSPy integration for optimization
- Automated robustness improvements
- Adaptive prompt engineering
- Robustness-aware training data generation

### Monitoring Dashboard (Phase 4)

Planned visualization of:
- Robustness trends over time
- Per-component metrics
- Quality gate violation history
- Fragile prompt registry

## References

- **Test Suite**: `tests/robustness/README.md`
- **CI Workflow**: `.github/workflows/robustness.yml`
- **Report Generator**: `scripts/robustness/generate_report.py`
- **TokDrift Paper**: arXiv:2510.14972
- **TokDrift Proposal**: `docs/planning/TOKDRIFT_APPLICABILITY_PROPOSAL.md`

## Appendix: Example Workflow Run

```
Robustness Testing - PR #123

✅ Lint: Passed
✅ Unit Tests: Passed
⚠️  Robustness: Warning

Robustness Metrics:
├─ Pass Rate: 85% ⚠️
├─ Robustness: 92%
├─ Sensitivity: 8%
└─ Status: WARNING

Quality Gates:
├─ Target: ≥90% pass rate, ≥97% robustness
├─ Warning: <90% pass rate
└─ Failure: <80% pass rate

Action Required:
Review failing tests before merge.
See artifacts for detailed output.
```
