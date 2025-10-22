# Robustness Testing Scripts

**Purpose**: Utilities for running, analyzing, and reporting on robustness tests.

## Scripts

### `generate_report.py`

Generate structured robustness reports from pytest output.

**Usage:**
```bash
# Run robustness tests and save output
uv run pytest tests/robustness/ -v > robustness_output.txt

# Generate JSON report
python scripts/robustness/generate_report.py \
  --input robustness_output.txt \
  --format json \
  --output report.json

# Generate Markdown report
python scripts/robustness/generate_report.py \
  --input robustness_output.txt \
  --format markdown \
  --output ROBUSTNESS_REPORT.md
```

**Output:**
- **JSON**: Structured metrics for CI/CD integration
- **Markdown**: Human-readable report for documentation

**Metrics Tracked:**
- Total tests, passed, failed, skipped
- Pass rate (%)
- Average robustness (%) - if applicable
- Average sensitivity (%) - if applicable
- Quality gate status (passed/warning/failed)

**Quality Gates:**
- ✅ **Passed**: Pass rate ≥ 90%
- ⚠️  **Warning**: 80% ≤ Pass rate < 90%
- ❌ **Failed**: Pass rate < 80%

## CI/CD Integration

These scripts are used by `.github/workflows/robustness.yml` to:
1. Run robustness tests on PRs and main branch
2. Generate structured reports
3. Post results as PR comments
4. Track metrics over time (nightly builds)

## Local Development

### Run Robustness Tests Locally

```bash
# All tests
uv run pytest tests/robustness/ -v

# Specific test category
uv run pytest tests/robustness/test_paraphrase_robustness.py -v

# With coverage
uv run pytest tests/robustness/ --cov=lift_sys.robustness --cov-report=html
```

### Generate Local Report

```bash
# Capture test output
uv run pytest tests/robustness/ -v > /tmp/robustness_output.txt

# Generate report
python scripts/robustness/generate_report.py \
  --input /tmp/robustness_output.txt \
  --format markdown

# View in terminal or save to file
python scripts/robustness/generate_report.py \
  --input /tmp/robustness_output.txt \
  --format markdown \
  --output docs/robustness/LATEST_REPORT.md
```

## Future Enhancements

Planned scripts for Phase 3+:
- `measure_baseline.py`: Automated baseline measurements
- `compare_baselines.py`: Compare current vs. historical baselines
- `identify_fragile.py`: Identify fragile prompts/IRs
- `optimize_robustness.py`: Suggest improvements for low-robustness areas

## References

- **Test Suite**: `tests/robustness/README.md`
- **CI Workflow**: `.github/workflows/robustness.yml`
- **TokDrift Proposal**: `docs/planning/TOKDRIFT_APPLICABILITY_PROPOSAL.md`
