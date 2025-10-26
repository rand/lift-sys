# DoWhy Integration Scripts

This directory contains scripts for integrating DoWhy causal inference into lift-sys via subprocess communication.

## Overview

Since DoWhy requires Python 3.11 and lift-sys uses Python 3.13, we run DoWhy in a separate subprocess using the `.venv-dowhy` environment.

## Files

### `fit_scm.py`
**Purpose**: Subprocess worker for fitting Structural Causal Models (SCMs)

**Usage**:
```bash
echo '{"graph": {...}, "traces": {...}}' | .venv-dowhy/bin/python scripts/dowhy/fit_scm.py
```

**Input** (JSON via stdin):
```json
{
  "graph": {
    "nodes": ["X", "Y", "Z"],
    "edges": [["X", "Y"], ["Y", "Z"]]
  },
  "traces": {
    "X": [1.0, 2.0, 3.0, ...],
    "Y": [2.5, 4.2, 6.1, ...],
    "Z": [7.8, 12.5, 18.3, ...]
  },
  "config": {
    "quality": "GOOD",
    "validate_r2": true,
    "r2_threshold": 0.7,
    "test_size": 0.2
  }
}
```

**Output** (JSON via stdout):
```json
{
  "status": "success",
  "scm": {
    "graph": {"nodes": [...], "edges": [...]},
    "mechanisms": {
      "X": {"type": "empirical", "params": null},
      "Y": {"type": "linear", "params": {"coefficients": [2.0], "intercept": 0.1}},
      "Z": {"type": "linear", "params": {"coefficients": [3.0], "intercept": -0.2}}
    }
  },
  "validation": {
    "r2_scores": {"Y": 0.95, "Z": 0.92},
    "mean_r2": 0.935,
    "passed": true,
    "threshold": 0.7,
    "failed_nodes": []
  },
  "metadata": {
    "fitting_time_ms": 523,
    "num_samples": 1000,
    "num_train": 800,
    "num_val": 200,
    "dowhy_version": "0.13.0",
    "quality": "GOOD"
  }
}
```

**Exit Codes**:
- `0`: Success or warning (check `status` field)
- `1`: Error occurred

### `test_fit_scm.sh`
**Purpose**: Test script for validating `fit_scm.py`

**Usage**:
```bash
./scripts/dowhy/test_fit_scm.sh
```

**What it tests**:
- Linear chain graphs (X → Y → Z)
- Multi-parent graphs (X, Y → Z)
- Non-linear relationships (quadratic)
- Edge cases: insufficient data, noisy data, perfect correlation
- Real-world scenarios: code execution traces, validation functions
- Complex DAGs with multiple paths

**Expected output**:
```
Testing: linear_chain
  Status: success
  ✅ PASS
  Mean R²: 0.998

...

========================================
Test Summary
========================================
Passed: 9 / 9
Failed: 0 / 9

✅ All tests passed!
```

## Configuration Options

### Quality Settings
- `"GOOD"`: Default, balanced performance (linear models)
- `"BETTER"`: More complex models (polynomial, non-linear)
- `"BEST"`: Most complex models (slowest, most accurate)

### Validation Settings
- `validate_r2`: Boolean, whether to enforce R² threshold (default: `true`)
- `r2_threshold`: Float, minimum R² required (default: `0.7`)
- `test_size`: Float, fraction of data for validation (default: `0.2`)

## Error Handling

### Status Values
- `"success"`: Fitting completed, validation passed
- `"validation_failed"`: Fitting completed, but R² below threshold
- `"warning"`: Insufficient data or other non-critical issue
- `"error"`: Critical failure (see `error` and `traceback` fields)

### Common Errors
1. **Graph not a DAG**: Input graph contains cycles
2. **Column mismatch**: Graph nodes don't match DataFrame columns
3. **Insufficient data**: Less than 100 samples (warning, not error)
4. **Invalid JSON**: Malformed input

## Integration with lift-sys

### From Python 3.13 Code
```python
import json
import subprocess
from pathlib import Path

def fit_scm_subprocess(graph: nx.DiGraph, traces: pd.DataFrame) -> dict:
    """Call DoWhy subprocess to fit SCM."""

    # Prepare input
    input_data = {
        "graph": {
            "nodes": list(graph.nodes()),
            "edges": list(graph.edges())
        },
        "traces": {col: traces[col].tolist() for col in traces.columns},
        "config": {
            "quality": "GOOD",
            "validate_r2": True,
            "r2_threshold": 0.7
        }
    }

    # Run subprocess
    result = subprocess.run(
        [".venv-dowhy/bin/python", "scripts/dowhy/fit_scm.py"],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60
    )

    # Parse output
    output = json.loads(result.stdout)

    if output["status"] == "error":
        raise RuntimeError(f"DoWhy fitting failed: {output['error']}")

    return output
```

## Test Fixtures

Test cases are located in `tests/fixtures/dowhy_traces/`:
- `linear_chain.json` - Simple X → Y → Z
- `multi_parent.json` - X, Y → Z
- `nonlinear.json` - Quadratic relationship
- `insufficient_data.json` - Only 50 samples
- `noisy_data.json` - High noise (R² < 0.7)
- `perfect_correlation.json` - No noise (R² = 1.0)
- `code_execution.json` - Deterministic function traces
- `validation_function.json` - Conditional logic
- `complex_dag.json` - Multi-path DAG

To regenerate fixtures:
```bash
.venv-dowhy/bin/python tests/fixtures/dowhy_test_cases.py
```

## Performance

**Typical Performance** (1000 samples):
- Graph construction: < 1ms
- Mechanism assignment: 100-200ms
- Fitting: 200-400ms
- Validation: 50-100ms
- **Total**: 400-700ms

**Scalability**:
- 100 samples: ~200ms
- 1,000 samples: ~500ms
- 10,000 samples: ~2s
- 100,000 samples: ~20s

**Bottlenecks**:
- Process startup: ~100ms (amortize with persistent worker)
- JSON serialization: O(n) where n = trace size
- SCM fitting: O(n * m) where m = number of edges

## Troubleshooting

### Tests Failing
1. Check `.venv-dowhy` exists: `ls .venv-dowhy/bin/python`
2. Verify DoWhy installed: `.venv-dowhy/bin/python -c "import dowhy; print(dowhy.__version__)"`
3. Check fixture files exist: `ls tests/fixtures/dowhy_traces/`

### Subprocess Timeout
- Increase timeout parameter in `subprocess.run()`
- Check for large trace sizes (>100k samples)
- Try reducing `quality` setting to `"GOOD"`

### R² Validation Failures
- Check if relationships are actually linear
- Reduce `r2_threshold` if data is noisy
- Set `validate_r2: false` to disable enforcement
- Use `quality: "BETTER"` for non-linear relationships

### Memory Issues
- Limit trace size (subsample if needed)
- Use streaming for very large datasets
- Monitor with: `.venv-dowhy/bin/python -m memory_profiler fit_scm.py`

## Future Enhancements

### Planned (STEP-08+)
- [ ] Persistent worker process (avoid startup overhead)
- [ ] Batch fitting for multiple graphs
- [ ] Caching fitted models (keyed by graph + data hash)
- [ ] Non-linear mechanism support (polynomial, RBF)
- [ ] Parallel fitting for independent subgraphs

### Under Consideration
- [ ] GPU acceleration for large-scale fitting
- [ ] Streaming data support (online learning)
- [ ] Model compression for serialization
- [ ] Visualization of fitted mechanisms

## References

- [DoWhy Documentation](https://www.pywhy.org/dowhy/)
- [STEP-08 Research Document](../../docs/planning/STEP_08_RESEARCH.md)
- [DoWhy Reverse Mode Spec](../../specs/dowhy-reverse-mode-spec.md)
- [DoWhy Execution Plan](../../plans/dowhy-execution-plan.md)

## Maintainers

- Primary: Claude (STEP-08 implementation)
- Reviewers: rand

**Last Updated**: 2025-10-26
