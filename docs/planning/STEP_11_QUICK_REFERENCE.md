# STEP-11 Quick Reference Guide

**For**: Developers implementing InterventionEngine (H22)
**Date**: 2025-10-26

## TL;DR

- ✅ DoWhy integration works via subprocess (`scripts/dowhy/query_fitted_scm.py`)
- ✅ Query latency: 3ms (well under <100ms requirement)
- ✅ Support hard interventions (do(X=value)), soft interventions (do(X=f(X)))
- ⚠️ Skip counterfactual queries (require invertible SCMs)
- 🎯 Use SCM caching for repeated queries

## Subprocess API

### Execute Intervention Query

```python
import json
import subprocess

# Prepare input
input_data = {
    "graph": {"nodes": ["x", "y"], "edges": [["x", "y"]]},
    "traces": {"x": [1, 2, 3, ...], "y": [2, 4, 6, ...]},
    "intervention": {
        "type": "interventional",
        "interventions": [
            {"type": "hard", "node": "x", "value": 5.0}
        ],
        "query_nodes": ["y"],
        "num_samples": 1000
    },
    "config": {"quality": "GOOD"}
}

# Run subprocess
result = subprocess.run(
    [".venv-dowhy/bin/python", "scripts/dowhy/query_fitted_scm.py"],
    input=json.dumps(input_data),
    capture_output=True,
    text=True,
    timeout=30.0
)

output = json.loads(result.stdout)
# output["statistics"]["y"]["mean"] = 10.0
```

## Intervention Types

### Hard Intervention

Set node to constant value:

```json
{
  "type": "hard",
  "node": "x",
  "value": 5.0
}
```

**Effect**: x becomes constant (std=0), breaks incoming edges

### Soft Intervention (Shift)

Shift distribution by constant:

```json
{
  "type": "soft",
  "node": "x",
  "transform": "shift",
  "param": 2.0
}
```

**Effect**: x → x + 2, distribution shifts

### Soft Intervention (Scale)

Scale distribution by factor:

```json
{
  "type": "soft",
  "node": "x",
  "transform": "scale",
  "param": 1.5
}
```

**Effect**: x → x * 1.5, variance increases

### Multiple Interventions

```json
{
  "interventions": [
    {"type": "hard", "node": "x", "value": 3},
    {"type": "soft", "node": "y", "transform": "shift", "param": 2}
  ]
}
```

### Observational Query

No intervention, sample from natural distribution:

```json
{
  "type": "observational",
  "num_samples": 1000
}
```

## Using Test Fixtures

```python
from tests.causal.fixtures.intervention_fixtures import (
    simple_linear_scm_data,
    intervention_test_cases
)

# Get test SCM
scm_data = simple_linear_scm_data()
graph = scm_data["graph"]
traces = scm_data["traces"]

# Get test cases
test_cases = intervention_test_cases()
for test in test_cases:
    intervention = test["intervention"]
    expected = test["expected"]
    # Run test...
```

## Using Data Classes

```python
from lift_sys.causal.intervention_spec import (
    HardIntervention,
    SoftIntervention,
    InterventionSpec,
    serialize_intervention
)

# Create intervention
intervention = HardIntervention(node="x", value=5.0)

# Serialize for subprocess
serialized = serialize_intervention(intervention)
# {"type": "hard", "node": "x", "value": 5.0}

# Create full spec
spec = InterventionSpec(
    interventions=[intervention],
    query_nodes=["y", "z"],
    num_samples=1000
)
```

## Performance Tips

### Cache Fitted SCMs

```python
class InterventionEngine:
    def __init__(self):
        self._scm_cache = {}  # graph_hash → fitted SCM

    def estimate_impact(self, graph, traces, intervention):
        # Check cache first
        graph_hash = hash_graph(graph)
        if graph_hash in self._scm_cache:
            # Fast path: <5ms
            return self._query_cached_scm(graph_hash, intervention)
        else:
            # Slow path: ~3s (fit + query)
            return self._fit_and_query(graph, traces, intervention)
```

### Batch Queries

Execute multiple queries on same SCM:

```python
# Fit once
scm = fit_scm(graph, traces)

# Query many times (each <5ms)
for intervention in interventions:
    result = query_scm(scm, intervention)
```

## Error Handling

### Invalid Node

```python
try:
    result = query_scm(...)
except ValueError as e:
    if "not in graph" in str(e):
        raise NodeNotFoundError(f"Node {node} not in graph")
```

### Insufficient Data

```python
if len(traces) < 100:
    raise DataError(f"Insufficient traces: {len(traces)} (min: 100)")
```

### Query Timeout

```python
try:
    result = subprocess.run(..., timeout=30.0)
except subprocess.TimeoutExpired:
    raise TimeoutError("Query exceeded 30s timeout")
```

## Computing Effect Sizes

### Cohen's d

```python
def compute_effect_size(baseline_mean, intervened_mean, baseline_std):
    """Cohen's d: standardized mean difference."""
    return (intervened_mean - baseline_mean) / baseline_std

# Example
baseline = query_scm(graph, traces, observational=True)
intervened = query_scm(graph, traces, intervention)

effect_size = compute_effect_size(
    baseline["statistics"]["y"]["mean"],
    intervened["statistics"]["y"]["mean"],
    baseline["statistics"]["y"]["std"]
)
# effect_size = 2.5 (large effect)
```

## Bootstrap Confidence Intervals

```python
def bootstrap_ci(query_func, n_iterations=100, alpha=0.05):
    """Compute 95% CI via bootstrap."""
    means = []
    for _ in range(n_iterations):
        result = query_func()
        means.append(result["statistics"]["y"]["mean"])

    lower = np.percentile(means, 100 * alpha / 2)
    upper = np.percentile(means, 100 * (1 - alpha / 2))

    return (lower, upper)

# Example
ci = bootstrap_ci(lambda: query_scm(graph, traces, intervention))
# ci = (9.8, 10.2)  # 95% CI
```

## Expected Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Fit SCM | ~3s | Once per graph (cache it!) |
| Query (fitted) | <5ms | Very fast |
| Query (integrated) | ~3s | Includes fitting |
| 1000 samples | +3ms | Linear scaling |
| 10000 samples | +4ms | Still fast |

## Common Patterns

### Pattern 1: Single Query

```python
# Simple case: one-shot query
result = query_scm(graph, traces, intervention)
print(f"Mean: {result['statistics']['y']['mean']}")
```

### Pattern 2: Multiple Queries (Cached)

```python
# Efficient: fit once, query many
scm = fit_scm(graph, traces)
for intervention in interventions:
    result = query_scm(scm, intervention)
    # Process result...
```

### Pattern 3: Effect Size Comparison

```python
# Compare intervention to baseline
baseline = query_scm(graph, traces, observational=True)
intervened = query_scm(graph, traces, intervention)

effect = compute_effect_size(
    baseline["statistics"]["y"]["mean"],
    intervened["statistics"]["y"]["mean"],
    baseline["statistics"]["y"]["std"]
)

if abs(effect) > 0.8:
    print(f"Large effect: {effect}")
```

### Pattern 4: Sensitivity Analysis

```python
# Test multiple intervention values
for value in [0, 1, 2, 3, 4, 5]:
    intervention = HardIntervention(node="x", value=value)
    result = query_scm(graph, traces, intervention)
    print(f"x={value} → y={result['statistics']['y']['mean']}")
```

## Files You Need

| File | Purpose |
|------|---------|
| `scripts/dowhy/query_fitted_scm.py` | Subprocess worker |
| `lift_sys/causal/intervention_spec.py` | Data structures |
| `tests/causal/fixtures/intervention_fixtures.py` | Test fixtures |
| `docs/planning/STEP_11_RESEARCH.md` | Detailed documentation |

## Testing

### Run Integration Tests

```bash
uv run python scripts/dowhy/test_query_integration.py
```

### Run Exploration Tests

```bash
.venv-dowhy/bin/python scripts/dowhy/explore_interventions.py
```

### Use Test Fixtures

```python
from tests.causal.fixtures.intervention_fixtures import intervention_test_cases

for test in intervention_test_cases():
    # Your test logic...
    pass
```

## Limitations

⚠️ **Counterfactual queries not supported**
- Require InvertibleStructuralCausalModel
- Auto-fitted models are not invertible
- Use interventional queries instead

⚠️ **Custom transform functions limited**
- Only "shift" and "scale" supported
- Custom expressions require careful handling
- Security concern with eval()

✅ **What works well**
- Hard interventions (do(X=value))
- Soft interventions (shift, scale)
- Multiple interventions
- Observational queries
- Performance (<5ms query time)

## Questions?

- See `docs/planning/STEP_11_RESEARCH.md` for details
- Check `scripts/dowhy/explore_interventions.py` for examples
- Review `tests/causal/fixtures/intervention_fixtures.py` for test cases
- Run `scripts/dowhy/test_query_integration.py` for validation
