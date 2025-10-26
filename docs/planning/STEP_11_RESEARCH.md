# STEP-11 Research: Counterfactual Query Execution

**Date**: 2025-10-26
**Status**: Research Complete
**Related**: H22 (InterventionEngine), Week 3 DoWhy Integration

## Summary

Researched DoWhy's intervention and counterfactual query capabilities to prepare infrastructure for STEP-11 implementation. Created subprocess wrapper for executing interventions on fitted SCMs, intervention specification data classes, and comprehensive test fixtures.

**Key Finding**: DoWhy's `gcm.whatif` module provides powerful intervention capabilities with <5ms query latency, but counterfactual queries require invertible SCMs which may not always be feasible with auto-fitted models.

## DoWhy Counterfactual API

### Core Functions

**1. `interventional_samples()` - What-if queries**
```python
gcm.whatif.interventional_samples(
    causal_model: ProbabilisticCausalModel,
    interventions: Dict[str, Callable],  # node → lambda function
    observed_data: Optional[DataFrame] = None,
    num_samples_to_draw: Optional[int] = None
) -> DataFrame
```

**Use case**: Answer "What if we set X=5?" questions
**Performance**: 1-5ms for 1000 samples
**Stability**: Excellent (works with any fitted SCM)

**2. `counterfactual_samples()` - Counterfactuals**
```python
gcm.whatif.counterfactual_samples(
    causal_model: Union[StructuralCausalModel, InvertibleStructuralCausalModel],
    interventions: Dict[str, Callable],
    observed_data: Optional[DataFrame] = None,
    noise_data: Optional[DataFrame] = None
) -> DataFrame
```

**Use case**: Answer "Given we observed X=0, what if X had been 5?"
**Requirements**: Invertible SCM (can recover noise terms)
**Limitation**: Auto-fitted models may not be invertible

**3. `draw_samples()` - Observational queries**
```python
gcm.draw_samples(
    causal_model: ProbabilisticCausalModel,
    num_samples: int
) -> DataFrame
```

**Use case**: Sample from observational distribution (no intervention)
**Performance**: <5ms for 1000 samples

### Intervention Specification Format

**Hard Intervention** (do(X=value)):
```python
{"X": lambda x: 5}  # Set X to constant 5
```

**Soft Intervention** (do(X=f(X))):
```python
{"X": lambda x: x + 2}    # Shift distribution by +2
{"X": lambda x: x * 1.5}  # Scale distribution by 1.5
```

**Multiple Interventions**:
```python
{
    "X": lambda x: 3,      # do(X=3)
    "Y": lambda y: y + 2   # do(Y := Y+2)
}
```

### Exploration Results

Ran comprehensive exploration script (`scripts/dowhy/explore_interventions.py`) with following findings:

**Test 1: Hard Intervention**
- Intervention: do(x=5)
- Expected: x=5, y≈10 (2*5), z≈11 (10+1)
- Actual: x=5.00, y=9.99, z=11.00
- **Status**: ✅ Perfect accuracy

**Test 2: Soft Intervention (Shift)**
- Intervention: x → x + 2
- Expected: Δx≈+2, Δy≈+4, Δz≈+4
- Actual: Δx=+2.07, Δy=+4.14, Δz=+4.14
- **Status**: ✅ Correct propagation

**Test 3: Multiple Interventions**
- Intervention: do(x=3), do(y=10)
- Expected: x=3, y=10, z≈9 (3*x, y edge broken), w≈19 (10+9)
- Actual: x=3.00, y=10.00, z=9.00, w=18.80
- **Status**: ✅ Correct edge cutting

**Test 4: Counterfactual**
- Query: Given x=0, what if x had been 5?
- **Result**: Error - requires InvertibleStructuralCausalModel
- **Status**: ⚠️ Limitation - auto-fitted models not invertible

**Test 5: Performance**
- Single intervention (1000 samples): **1.4ms**
- Multiple interventions (1000 samples): **1.5ms**
- Large query (10000 samples): **3.7ms**
- **Status**: ✅ Meets <100ms requirement easily

**Test 6: Error Handling**
- Invalid node: ✅ Raises ValueError
- Invalid intervention function: ✅ Raises TypeError
- **Status**: ✅ Proper error handling

## Subprocess Integration Approach

### Challenge: SCM Serialization

**Problem**: DoWhy's fitted SCMs contain sklearn models that are difficult to serialize/deserialize through JSON.

**Solution**: Integrated fit + query approach:
1. Pass graph + traces to subprocess
2. Fit SCM in subprocess
3. Execute interventions on fitted model
4. Return results

**Alternative considered**: Pickle/cloudpickle serialization
- **Pros**: Full model preservation
- **Cons**: Binary format, security concerns, version fragility
- **Decision**: Use integrated approach for STEP-11

### Files Created

**1. `scripts/dowhy/query_fitted_scm.py`**
- Subprocess worker for intervention queries
- Combines SCM fitting + query execution
- Input: graph + traces + intervention spec
- Output: samples + statistics + metadata

**2. `scripts/dowhy/query_scm.py`**
- Alternative approach (attempted SCM deserialization)
- **Status**: Incomplete (deserialization not trivial)
- **Kept for reference**: May be useful with pickle approach

**3. `scripts/dowhy/explore_interventions.py`**
- Exploration script for DoWhy capabilities
- Validates all intervention patterns
- Performance benchmarks
- Error case testing

### Subprocess API

**Input Format**:
```json
{
  "graph": {
    "nodes": ["x", "y", "z"],
    "edges": [["x", "y"], ["y", "z"]]
  },
  "traces": {
    "x": [1.0, 2.0, 3.0, ...],
    "y": [2.0, 4.0, 6.0, ...],
    "z": [3.0, 5.0, 7.0, ...]
  },
  "intervention": {
    "type": "interventional",
    "interventions": [
      {"type": "hard", "node": "x", "value": 5.0}
    ],
    "query_nodes": ["y", "z"],
    "num_samples": 1000
  },
  "config": {
    "quality": "GOOD"
  }
}
```

**Output Format**:
```json
{
  "status": "success",
  "query_type": "interventional",
  "samples": {
    "y": [10.1, 9.9, 10.0, ...],
    "z": [11.2, 10.8, 11.1, ...]
  },
  "statistics": {
    "y": {
      "mean": 10.0,
      "std": 0.1,
      "q05": 9.84,
      "q50": 10.0,
      "q95": 10.16,
      "min": 9.7,
      "max": 10.3
    },
    "z": { ... }
  },
  "metadata": {
    "query_time_ms": 15,
    "fit_time_ms": 250,
    "num_samples": 1000,
    "num_interventions": 1,
    "query_nodes": ["y", "z"],
    "num_training_samples": 1000
  }
}
```

## Intervention Specification Data Classes

**File**: `lift_sys/causal/intervention_spec.py`

### Core Types

**1. `InterventionType` Enum**
- `HARD`: do(X=value) - constant intervention
- `SOFT`: do(X=f(X)) - distributional shift
- `OBSERVATIONAL`: no intervention

**2. `HardIntervention` Dataclass**
```python
@dataclass
class HardIntervention:
    node: str
    value: float | int
```

**3. `SoftIntervention` Dataclass**
```python
@dataclass
class SoftIntervention:
    node: str
    transform: str  # "shift", "scale", "custom"
    param: float | None = None
    custom_expr: str | None = None
```

**4. `InterventionSpec` Dataclass**
```python
@dataclass
class InterventionSpec:
    interventions: list[HardIntervention | SoftIntervention]
    query_nodes: list[str] | None = None
    num_samples: int = 1000
```

**5. `InterventionResult` Dataclass**
```python
@dataclass
class InterventionResult:
    samples: dict[str, list[float]]
    statistics: dict[str, dict[str, float]]
    metadata: dict[str, Any]
    intervention_spec: InterventionSpec
```

### Utility Functions

**Serialization**:
- `serialize_intervention()`: Python → JSON dict
- `deserialize_intervention()`: JSON dict → Python
- `intervention_to_lambda_str()`: Intervention → lambda expression

**Example**:
```python
intervention = HardIntervention(node="x", value=5)
serialized = serialize_intervention(intervention)
# {"type": "hard", "node": "x", "value": 5}

lambda_str = intervention_to_lambda_str(intervention)
# "lambda x: 5"
```

## Intervention Patterns

### 1. Hard Intervention (do(X=value))

**Use case**: Set variable to constant, breaking all incoming edges

**Example**:
```python
# Question: What if we always set x=5?
intervention = HardIntervention(node="x", value=5.0)

# DoWhy: {"x": lambda x: 5}
```

**Effect**:
- Intervened node becomes constant (std=0)
- All downstream nodes affected
- Upstream nodes unaffected

**Backdoor/Frontdoor**: Hard interventions automatically handle confounding by breaking incoming edges

### 2. Soft Intervention (do(X=f(X)))

**Use case**: Shift or scale distribution without setting to constant

**Example - Shift**:
```python
# Question: What if we increase x by 2?
intervention = SoftIntervention(node="x", transform="shift", param=2.0)

# DoWhy: {"x": lambda x: x + 2}
```

**Example - Scale**:
```python
# Question: What if we double x?
intervention = SoftIntervention(node="x", transform="scale", param=2.0)

# DoWhy: {"x": lambda x: x * 2}
```

**Effect**:
- Distribution shape preserved
- Mean/variance shift/scale
- Downstream propagation

### 3. Multiple Interventions

**Use case**: Intervene on multiple nodes simultaneously

**Example**:
```python
interventions = [
    HardIntervention(node="x", value=3.0),
    SoftIntervention(node="y", transform="shift", param=2.0)
]

# DoWhy: {"x": lambda x: 3, "y": lambda y: y + 2}
```

**Effect**:
- Both interventions applied
- Downstream nodes see combined effects
- Edge cutting happens for all intervened nodes

### 4. Conditional Interventions

**Use case**: Intervene based on node's current value

**Example**:
```python
# Not directly supported in current spec
# Future: custom expressions
intervention = SoftIntervention(
    node="x",
    transform="custom",
    custom_expr="x if x > 0 else 0"  # ReLU
)
```

**Status**: Not implemented in STEP-11 (future enhancement)

### 5. Backdoor/Frontdoor Adjustments

**DoWhy handling**:
- Hard interventions automatically implement backdoor adjustment (break incoming edges)
- No explicit backdoor/frontdoor specification needed
- Intervention semantics handle confounding

**Example**:
```
Graph: Z → X → Y, Z → Y (Z confounds X→Y)

do(X=5): Breaks Z→X edge, isolates causal effect X→Y
```

## Test Fixtures

**File**: `tests/causal/fixtures/intervention_fixtures.py`

### Standard Test Cases

**1. `simple_linear_scm_data()`**
- Graph: x → y → z
- Ground truth: y=2x, z=y+1
- Use: Basic intervention testing

**2. `diamond_scm_data()`**
- Graph: x → y, x → z, y → w, z → w
- Ground truth: y=2x, z=3x, w=y+z
- Use: Multiple paths, complex effects

**3. `nonlinear_scm_data()`**
- Graph: x → y
- Ground truth: y=x²
- Use: Nonlinear mechanism testing

### Intervention Test Cases

**`intervention_test_cases()`** - 6 standard tests:
1. Hard intervention on root node (do(x=5))
2. Soft intervention shift (x → x+2)
3. Multiple interventions (do(x=3), do(y=10))
4. Intervention on intermediate node (do(y=10))
5. Soft intervention scale (y → 2*y)
6. Observational baseline (no intervention)

**`edge_case_intervention_tests()`** - 5 edge cases:
1. Invalid node intervention → ValueError
2. Zero samples → Error
3. Negative samples → Error
4. Empty interventions list → Observational behavior
5. Query non-existent nodes → Error

**`performance_test_cases()`** - 3 performance tests:
1. Small query (1000 samples): <100ms
2. Large query (10000 samples): <500ms
3. Multiple interventions: <100ms

### Example Usage

```python
from tests.causal.fixtures.intervention_fixtures import intervention_test_cases

for test_case in intervention_test_cases():
    scm_data = test_case["scm_data"]
    intervention = test_case["intervention"]
    expected = test_case["expected"]

    # Run intervention query
    result = query_scm(scm_data["graph"], scm_data["traces"], intervention)

    # Validate
    assert abs(result["statistics"]["x"]["mean"] - expected["x_mean"]) < expected["tolerance"]
```

## Performance Considerations

### Query Latency

**Measured performance** (from exploration):
- 1000 samples: **1.4ms** query time
- 10000 samples: **3.7ms** query time
- Multiple interventions: **1.5ms** query time

**Bottleneck**: SCM fitting (not query execution)
- Fitting: 200-500ms (depends on quality setting)
- Query: <5ms (very fast)

**Optimization strategy**:
1. Fit SCM once, cache in memory
2. Execute multiple queries on same SCM
3. Use `quality="GOOD"` for faster fitting (vs "BEST")

### Scalability

**Sample size**:
- 1000 samples: Sufficient for most queries
- 10000 samples: High precision estimates
- 100 samples: Quick prototyping

**Graph complexity**:
- <10 nodes: <5ms query time
- 10-50 nodes: 5-20ms query time (estimated)
- 50+ nodes: 20-100ms query time (estimated)

**Constraint**: STEP-11 requires <100ms total time
- **Solution**: Fit SCM separately (STEP-08), query quickly (STEP-11)
- **Implementation**: Session-based caching of fitted SCMs

### Memory Usage

**SCM storage**:
- Small graph (<10 nodes): ~1MB per fitted SCM
- Large graph (50 nodes): ~10-50MB per fitted SCM

**Samples storage**:
- 1000 samples × 10 nodes × 8 bytes: ~80KB
- 10000 samples × 10 nodes × 8 bytes: ~800KB

**Recommendation**: Store fitted SCMs in session cache, discard intervention samples after computing statistics

## Implementation Recommendations

### For STEP-11 Implementation

**1. Use `query_fitted_scm.py` subprocess approach**
- Simpler than SCM deserialization
- Reliable and tested
- Performance acceptable (fit time is main cost)

**2. Add SCM caching for multiple queries**
```python
class InterventionEngine:
    def __init__(self):
        self._scm_cache: dict[str, Any] = {}  # graph_hash → fitted SCM

    def estimate_impact(self, scm_id: str, intervention: InterventionSpec):
        # Use cached SCM if available
        # Or fit from graph + traces if not
```

**3. Support observational and interventional queries only**
- Skip counterfactual queries (require invertible SCMs)
- Focus on do(X=x) and observational P(Y)
- Document limitation

**4. Implement effect size computation**
```python
def compute_effect_size(baseline_mean, intervened_mean, baseline_std):
    """Cohen's d: (μ_intervention - μ_baseline) / σ_baseline"""
    return (intervened_mean - baseline_mean) / baseline_std
```

**5. Add confidence intervals via bootstrap**
```python
# Run intervention query N times (N=100)
# Compute 2.5% and 97.5% quantiles of means
# Report as 95% CI
```

### Error Handling Patterns

**Invalid node**:
```python
try:
    result = query_scm(graph, traces, intervention)
except ValueError as e:
    if "not in graph" in str(e):
        raise NodeNotFoundError(f"Node {node} not found in graph")
```

**Insufficient data**:
```python
if len(traces) < 100:
    raise DataError(f"Insufficient traces: {len(traces)} (minimum: 100)")
```

**Query timeout**:
```python
# Subprocess with timeout=30s
# If fitting + query > 30s, raise TimeoutError
```

## Next Steps (STEP-11 Implementation)

**Week 3 Timeline**:

**STEP-10: Intervention API implementation** (2 days)
1. Implement `InterventionEngine.estimate_impact()`
2. Integrate `query_fitted_scm.py` subprocess
3. Add SCM caching for repeated queries
4. Unit tests for hard/soft interventions

**STEP-11: Confidence interval estimation** (2 days)
1. Implement bootstrap CI estimation
2. Add effect size computation (Cohen's d)
3. Integration tests with Week 2 SCM fitter
4. Performance validation (<100ms requirement)

**STEP-12: Documentation and validation** (1 day)
1. Document intervention patterns
2. Create example queries
3. Validate against test fixtures
4. Update H22 specification

## Conclusion

**Research Status**: ✅ Complete

**Key Deliverables**:
1. ✅ DoWhy intervention API documented
2. ✅ Subprocess wrapper created (`query_fitted_scm.py`)
3. ✅ Intervention specs defined (`intervention_spec.py`)
4. ✅ Test fixtures created (`intervention_fixtures.py`)
5. ✅ Performance validated (<5ms query time)

**Readiness for STEP-11**: 🟢 Ready to implement

**Blockers**: None

**Recommendations**:
1. Use integrated fit+query approach (simplest)
2. Add SCM caching for performance
3. Skip counterfactual queries (invertibility requirement)
4. Focus on interventional and observational queries

**Next Action**: Begin STEP-10 implementation (InterventionEngine with subprocess integration)
