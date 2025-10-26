# STEP-08: Dynamic SCM Fitting - Research Findings

**Date**: 2025-10-26
**Status**: Research Complete
**Phase**: Preparation for STEP-08 Implementation
**Related**: `plans/dowhy-execution-plan.md` STEP-08

---

## Executive Summary

This document provides research findings and infrastructure preparation for STEP-08: Dynamic Mechanism Fitting. The goal is to fit Structural Causal Models (SCMs) from execution traces using DoWhy's `gcm.auto.assign_causal_mechanisms()` and validate the fitted models with R² ≥ 0.7.

**Key Findings**:
1. DoWhy provides auto-assignment and fitting APIs suitable for our needs
2. Subprocess wrapper is necessary due to Python 3.11 requirement
3. R² validation is available via `gcm.evaluate_causal_model()`
4. Serialization via pickle (not JSON) is recommended for fitted models
5. Cross-validation requires manual train/test split

---

## Table of Contents

1. [DoWhy API Research](#1-dowhy-api-research)
2. [Subprocess Integration Strategy](#2-subprocess-integration-strategy)
3. [R² Validation Methodology](#3-r2-validation-methodology)
4. [Serialization Approach](#4-serialization-approach)
5. [Test Fixtures](#5-test-fixtures)
6. [Implementation Roadmap](#6-implementation-roadmap)

---

## 1. DoWhy API Research

### 1.1 Creating a StructuralCausalModel

**Function**: `gcm.StructuralCausalModel(graph)`

**Signature**:
```python
from dowhy import gcm
import networkx as nx

# Create from NetworkX DiGraph
causal_graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])
scm = gcm.StructuralCausalModel(causal_graph)
```

**Parameters**:
- `graph`: NetworkX DiGraph representing causal structure
- Nodes represent variables
- Directed edges represent causal relationships (A → B means A causes B)

**Requirements**:
- MUST be a Directed Acyclic Graph (DAG)
- Nodes should have string names matching DataFrame columns
- No self-loops or cycles allowed

**Returns**:
- `StructuralCausalModel` object ready for mechanism assignment

---

### 1.2 Auto-Assigning Causal Mechanisms

**Function**: `gcm.auto.assign_causal_mechanisms(causal_model, data)`

**Signature**:
```python
import pandas as pd

gcm.auto.assign_causal_mechanisms(
    causal_model: gcm.StructuralCausalModel,
    data: pd.DataFrame,
    override_models: bool = False,
    quality: gcm.auto.AssignmentQuality = gcm.auto.AssignmentQuality.GOOD
)
```

**Parameters**:
- `causal_model`: The SCM to populate with mechanisms
- `data`: Training data (DataFrame with columns matching node names)
- `override_models`: If True, replace existing mechanisms (default: False)
- `quality`: Controls model selection complexity
  - `AssignmentQuality.GOOD`: Balanced (default)
  - `AssignmentQuality.BETTER`: More complex models
  - `AssignmentQuality.BEST`: Most complex (slowest)

**Behavior**:
- **Root nodes** (no parents): Assigns empirical distribution
  - Samples from observed data distribution
  - Non-parametric, flexible for all data types
- **Non-root nodes** (has parents): Assigns additive noise models
  - Default: Linear regression (`Y = β₀ + β₁X₁ + ... + ε`)
  - Evaluates multiple models, selects best by MSE
  - Can use non-linear models if linear fit is poor

**Returns**: None (modifies `causal_model` in-place)

**Example**:
```python
# Generate synthetic data
X = np.random.normal(0, 1, 1000)
Y = 2 * X + np.random.normal(0, 1, 1000)
Z = 3 * Y + np.random.normal(0, 1, 1000)
data = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

# Create and assign mechanisms
causal_graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])
scm = gcm.StructuralCausalModel(causal_graph)
gcm.auto.assign_causal_mechanisms(scm, data)
```

---

### 1.3 Fitting the Model

**Function**: `gcm.fit(causal_model, data)`

**Signature**:
```python
gcm.fit(
    causal_model: gcm.StructuralCausalModel,
    data: pd.DataFrame
)
```

**Parameters**:
- `causal_model`: SCM with assigned mechanisms
- `data`: Training data (same as used for assignment)

**Behavior**:
- "Fitting means we learn the generative models of the variables in the SCM according to the data"
- Trains each mechanism's parameters on the data
- For linear mechanisms: Learns regression coefficients
- For empirical distributions: Stores sample data

**Returns**: None (modifies `causal_model` in-place)

**Complete Workflow**:
```python
# 1. Create SCM from graph
scm = gcm.StructuralCausalModel(causal_graph)

# 2. Auto-assign mechanisms
gcm.auto.assign_causal_mechanisms(scm, data)

# 3. Fit mechanisms to data
gcm.fit(scm, data)

# Now SCM is ready for queries
```

---

### 1.4 Querying Fitted Models

**Interventional Samples**:
```python
# Generate samples under intervention
samples = gcm.interventional_samples(
    causal_model=scm,
    interventions={'X': lambda x: 5.0},  # Set X to 5.0
    num_samples_to_draw=1000
)
# Returns: DataFrame with same columns as training data
```

**Counterfactuals** (requires observed data):
```python
# What would Y be if X was different?
counterfactuals = gcm.counterfactual_samples(
    causal_model=scm,
    observed_data=observed_df,
    interventions={'X': lambda x: x + 1}
)
```

---

## 2. Subprocess Integration Strategy

### 2.1 Why Subprocess?

**Problem**: DoWhy requires Python 3.11, lift-sys uses Python 3.13

**Solution**: Run DoWhy in separate Python 3.11 process (`.venv-dowhy`)

**Tradeoffs**:
- ✅ No version conflicts
- ✅ Isolated dependencies
- ✅ Clean API boundary
- ❌ ~100-500ms process startup overhead
- ❌ Data serialization overhead
- ❌ More complex debugging

### 2.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  lift-sys (Python 3.13)                                     │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SCMFitter (lift_sys/causal/scm_fitter.py)          │  │
│  │                                                      │  │
│  │  1. Prepare input: graph_json, traces_json         │  │
│  │  2. Call subprocess wrapper                         │  │
│  │  3. Parse output: fitted SCM                        │  │
│  └─────────────────┬────────────────────────────────────┘  │
│                    │                                        │
│                    │ JSON via stdin/stdout                  │
│                    ▼                                        │
└────────────────────┼────────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────────┐
│  DoWhy Subprocess (Python 3.11, .venv-dowhy)               │
│                    │                                        │
│  ┌─────────────────▼────────────────────────────────────┐  │
│  │  scripts/dowhy/fit_scm.py                           │  │
│  │                                                     │  │
│  │  1. Parse stdin: graph_json, traces_json          │  │
│  │  2. Reconstruct NetworkX graph                    │  │
│  │  3. Create pandas DataFrame from traces           │  │
│  │  4. gcm.auto.assign_causal_mechanisms()           │  │
│  │  5. gcm.fit()                                     │  │
│  │  6. Evaluate (R² scores)                          │  │
│  │  7. Serialize fitted SCM                          │  │
│  │  8. Write JSON to stdout                          │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Input/Output Format

**Input (stdin JSON)**:
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
    "r2_threshold": 0.7
  }
}
```

**Output (stdout JSON)**:
```json
{
  "status": "success",
  "scm": {
    "graph": {"nodes": [...], "edges": [...]},
    "mechanisms": {
      "X": {"type": "empirical", "samples": [...]},
      "Y": {"type": "linear", "coefficients": [2.0], "intercept": 0.1},
      "Z": {"type": "linear", "coefficients": [3.0], "intercept": -0.2}
    }
  },
  "validation": {
    "r2_scores": {"Y": 0.95, "Z": 0.92},
    "mean_r2": 0.935,
    "passed": true
  },
  "metadata": {
    "fitting_time_ms": 523,
    "num_samples": 1000,
    "dowhy_version": "0.13.0"
  }
}
```

**Error Output**:
```json
{
  "status": "error",
  "error": "R² validation failed",
  "details": {
    "r2_scores": {"Y": 0.95, "Z": 0.45},
    "mean_r2": 0.70,
    "threshold": 0.7,
    "failed_nodes": ["Z"]
  }
}
```

---

## 3. R² Validation Methodology

### 3.1 What is R²?

**Definition**: Coefficient of determination, measures how well predictions match actual values

**Formula**: `R² = 1 - (SS_res / SS_tot)`
- `SS_res`: Sum of squared residuals (prediction errors)
- `SS_tot`: Total sum of squares (variance in data)

**Interpretation**:
- R² = 1.0: Perfect fit (all variance explained)
- R² = 0.7: Good fit (70% of variance explained) ← Our threshold
- R² = 0.5: Moderate fit (50% of variance explained)
- R² = 0.0: No predictive power (baseline)
- R² < 0.0: Worse than baseline (model is harmful)

### 3.2 Computing R² for Causal Models

**DoWhy Approach**: Use `gcm.evaluate_causal_model()`

**Function Signature**:
```python
from dowhy.gcm import evaluate_causal_model

results = evaluate_causal_model(
    causal_model: gcm.StructuralCausalModel,
    data: pd.DataFrame,
    evaluate_causal_mechanisms: bool = True,
    evaluate_invertibility_assumptions: bool = False,
    evaluate_overall_kl_divergence: bool = False
)
```

**Returns**: Dictionary with evaluation metrics per node
- `"r2"`: R² score for each non-root node
- `"mse"`: Mean squared error
- `"nmse"`: Normalized MSE
- `"crps"`: Continuous ranked probability score

**Example**:
```python
# Evaluate fitted model
evaluation = gcm.evaluate_causal_model(scm, data)

# Extract R² scores
r2_scores = {}
for node in causal_graph.nodes():
    if node in evaluation:
        r2_scores[node] = evaluation[node].get("r2", None)

print(f"R² scores: {r2_scores}")
# Output: {'Y': 0.95, 'Z': 0.92}
```

### 3.3 Cross-Validation Strategy

**Approach**: Manual 80/20 train/validation split

**Why Manual?** DoWhy doesn't have built-in cross-validation for SCMs

**Implementation**:
```python
from sklearn.model_selection import train_test_split

# Split data
train_data, val_data = train_test_split(
    data,
    test_size=0.2,
    random_state=42
)

# Fit on training data
gcm.auto.assign_causal_mechanisms(scm, train_data)
gcm.fit(scm, train_data)

# Evaluate on validation data
evaluation = gcm.evaluate_causal_model(scm, val_data)

# Check threshold
mean_r2 = np.mean([v["r2"] for v in evaluation.values() if "r2" in v])
if mean_r2 < 0.7:
    raise ValidationError(f"R² {mean_r2:.3f} below threshold 0.7")
```

### 3.4 R² Validation Requirements

**Per STEP-08 Specification**:
- Threshold: R² ≥ 0.7 (configurable)
- Scope: All non-root nodes in the graph
- Validation set: 20% of traces (held out from training)
- Failure behavior: Raise `ValidationError` with details

**Edge Cases**:
1. **Insufficient data**: Require ≥100 samples (20 for validation)
2. **Noisy data**: Try non-linear mechanisms if linear fails
3. **Perfect correlation**: Warn (may indicate data leakage)
4. **Negative R²**: Error (model worse than baseline)

---

## 4. Serialization Approach

### 4.1 Pickle vs JSON

**Recommendation**: Use **pickle** for SCMs, **JSON** for subprocess communication

**Rationale**:
- DoWhy SCMs contain complex Python objects (sklearn models, numpy arrays)
- Pickle preserves full state, JSON does not
- Subprocess wrapper translates pickle ↔ JSON at boundaries

### 4.2 SCM Serialization

**Saving**:
```python
import pickle

# Save fitted SCM to file
with open("scm.pkl", "wb") as f:
    pickle.dump(scm, f)
```

**Loading**:
```python
# Load fitted SCM from file
with open("scm.pkl", "rb") as f:
    scm = pickle.load(f)
```

### 4.3 JSON-Compatible Representation

**For IR Integration**: Store simplified representation in JSON

**Schema**:
```json
{
  "graph": {
    "nodes": ["X", "Y", "Z"],
    "edges": [["X", "Y"], ["Y", "Z"]]
  },
  "mechanisms": {
    "X": {"type": "empirical", "params": null},
    "Y": {"type": "linear", "params": {"coef": [2.0], "intercept": 0.1}},
    "Z": {"type": "linear", "params": {"coef": [3.0], "intercept": -0.2}}
  },
  "validation": {
    "r2_scores": {"Y": 0.95, "Z": 0.92},
    "mean_r2": 0.935
  }
}
```

**Limitation**: Cannot reconstruct full SCM from JSON alone (need pickle file)

**Use Cases**:
- JSON: Display, API responses, IR metadata
- Pickle: Full SCM persistence, cross-session usage

---

## 5. Test Fixtures

### 5.1 Synthetic Test Cases

**Test Case 1: Simple Linear Chain** (X → Y → Z)
```python
# Generate data with known relationships
X = np.random.normal(0, 1, 1000)
Y = 2.0 * X + np.random.normal(0, 0.1, 1000)  # Strong linear
Z = 3.0 * Y + np.random.normal(0, 0.1, 1000)  # Strong linear

data = pd.DataFrame({"X": X, "Y": Y, "Z": Z})
graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])

# Expected: R² > 0.95 for both Y and Z
```

**Test Case 2: Multi-Parent** (X, Y → Z)
```python
X = np.random.normal(0, 1, 1000)
Y = np.random.normal(0, 1, 1000)
Z = 1.5 * X + 2.5 * Y + np.random.normal(0, 0.1, 1000)

data = pd.DataFrame({"X": X, "Y": Y, "Z": Z})
graph = nx.DiGraph([("X", "Z"), ("Y", "Z")])

# Expected: R² > 0.95 for Z
```

**Test Case 3: Non-Linear Relationship**
```python
X = np.random.uniform(-3, 3, 1000)
Y = X**2 + np.random.normal(0, 0.5, 1000)  # Quadratic

data = pd.DataFrame({"X": X, "Y": Y})
graph = nx.DiGraph([("X", "Y")])

# Expected: Linear fit R² ≈ 0.0, non-linear fit R² > 0.8
```

### 5.2 Edge Case Test Cases

**Test Case 4: Insufficient Data**
```python
# Only 50 samples (below minimum)
X = np.random.normal(0, 1, 50)
Y = 2.0 * X + np.random.normal(0, 0.1, 50)

data = pd.DataFrame({"X": X, "Y": Y})
graph = nx.DiGraph([("X", "Y")])

# Expected: Warning or error about insufficient data
```

**Test Case 5: Noisy Data**
```python
X = np.random.normal(0, 1, 1000)
Y = 2.0 * X + np.random.normal(0, 5.0, 1000)  # Large noise

data = pd.DataFrame({"X": X, "Y": Y})
graph = nx.DiGraph([("X", "Y")])

# Expected: R² ≈ 0.3-0.5 (below threshold), should fail validation
```

**Test Case 6: Perfect Correlation** (data leakage)
```python
X = np.random.normal(0, 1, 1000)
Y = 2.0 * X  # No noise!

data = pd.DataFrame({"X": X, "Y": Y})
graph = nx.DiGraph([("X", "Y")])

# Expected: R² = 1.0, warning about potential data leakage
```

### 5.3 Real-World Test Cases

**Test Case 7: Code Execution Traces**
```python
# Simulate traces from function: def double(x): return x * 2
traces = {
    "input_x": [1, 2, 3, 4, 5, ..., 100],
    "output": [2, 4, 6, 8, 10, ..., 200]
}

data = pd.DataFrame(traces)
graph = nx.DiGraph([("input_x", "output")])

# Expected: R² ≈ 1.0 (deterministic function)
```

**Test Case 8: Validation Function** (input → valid → output)
```python
# Simulate: output = process(input) if valid(input) else None
traces = {
    "input": [1, -1, 2, -2, 3, ...],
    "is_valid": [True, False, True, False, True, ...],
    "output": [2, None, 4, None, 6, ...]  # Only when valid
}

data = pd.DataFrame(traces).dropna()
graph = nx.DiGraph([("input", "is_valid"), ("input", "output"), ("is_valid", "output")])

# Expected: Complex relationships, R² moderate (0.5-0.8)
```

---

## 6. Implementation Roadmap

### 6.1 Phase 1: Subprocess Wrapper (DONE)

**Files Created**:
- ✅ `scripts/dowhy/fit_scm.py` - DoWhy subprocess worker
- ✅ `scripts/dowhy/test_fit_scm.py` - Unit tests for wrapper

**Functionality**:
- ✅ Parse JSON input from stdin
- ✅ Reconstruct NetworkX graph
- ✅ Create pandas DataFrame
- ✅ Auto-assign mechanisms
- ✅ Fit SCM
- ✅ Compute R² validation
- ✅ Serialize output to JSON
- ✅ Error handling and logging

### 6.2 Phase 2: Test Fixtures (DONE)

**Files Created**:
- ✅ `tests/fixtures/dowhy_test_cases.py` - Synthetic test data
- ✅ `tests/fixtures/dowhy_traces/` - Sample trace files

**Test Cases**:
- ✅ Simple linear chain
- ✅ Multi-parent graph
- ✅ Non-linear relationships
- ✅ Edge cases (noisy, insufficient, perfect)

### 6.3 Phase 3: Integration with SCMFitter (TODO - STEP-08)

**Files to Modify**:
- `lift_sys/causal/scm_fitter.py` - Add dynamic fitting method
- `lift_sys/causal/trace_collector.py` - Format traces for DoWhy

**Implementation Tasks**:
1. Implement `fit_dynamic(graph, traces) -> SCM`
2. Call subprocess wrapper via `subprocess.run()`
3. Parse JSON response
4. Handle errors and validation failures
5. Return fitted SCM

### 6.4 Phase 4: Validation and Testing (TODO - STEP-09)

**Files to Create**:
- `tests/causal/test_dynamic_fitting.py` - Unit tests
- `tests/integration/test_scm_fitting_e2e.py` - Integration tests

**Test Coverage**:
- Valid fitting with good R²
- Validation failures (R² < 0.7)
- Subprocess errors
- Serialization round-trip
- Performance benchmarks

---

## 7. Key Decisions and Rationale

### 7.1 Subprocess vs In-Process

**Decision**: Use subprocess wrapper

**Rationale**:
- Python version mismatch (3.11 vs 3.13)
- Isolated dependencies reduce conflicts
- ~100-500ms overhead acceptable for fitting (one-time cost)
- Cleaner architecture (separation of concerns)

**Alternative Considered**: Docker container (rejected: too heavy)

### 7.2 Pickle vs JSON for SCM

**Decision**: Pickle for storage, JSON for communication

**Rationale**:
- Pickle preserves full SCM state (sklearn models, numpy arrays)
- JSON for subprocess I/O (human-readable, debuggable)
- Simplified JSON in IR (metadata only, not full SCM)

**Alternative Considered**: Cloudpickle (rejected: overkill)

### 7.3 R² Threshold = 0.7

**Decision**: Require mean R² ≥ 0.7 across all non-root nodes

**Rationale**:
- Standard in ML: R² > 0.7 indicates "good fit"
- Balances accuracy vs strictness
- Configurable (can adjust per use case)

**Alternative Considered**: 0.8 (rejected: too strict for noisy data)

### 7.4 Manual Cross-Validation

**Decision**: Implement 80/20 train/val split manually

**Rationale**:
- DoWhy doesn't provide built-in CV for SCMs
- 80/20 is standard, simple to implement
- Sufficient for validation purposes

**Alternative Considered**: K-fold CV (rejected: unnecessary complexity)

---

## 8. Open Questions and Risks

### 8.1 Open Questions

1. **Q**: How to handle categorical variables in traces?
   - **A**: Use label encoding, document assumption

2. **Q**: What if graph has 100+ nodes?
   - **A**: Test performance, optimize if needed (parallel fitting?)

3. **Q**: Should we cache fitted SCMs?
   - **A**: Yes, add caching in Phase 3 (keyed by graph hash + data hash)

### 8.2 Risks and Mitigations

**Risk 1**: Subprocess overhead too high (>1s)
- **Mitigation**: Benchmark early, optimize if needed
- **Fallback**: Persistent worker process (stdin/stdout loop)

**Risk 2**: R² validation too strict for real code
- **Mitigation**: Make threshold configurable, document assumptions
- **Fallback**: Warning instead of error

**Risk 3**: Serialization fails for complex mechanisms
- **Mitigation**: Test with diverse mechanism types
- **Fallback**: Store pickle path in JSON, not full SCM

**Risk 4**: DoWhy version incompatibility
- **Mitigation**: Pin DoWhy version in `.venv-dowhy`
- **Fallback**: Document supported versions

---

## 9. Next Steps (Implementation Checklist)

### Ready for STEP-08 Implementation

- [x] Research DoWhy API (`gcm.auto.assign_causal_mechanisms`, `gcm.fit`)
- [x] Design subprocess wrapper architecture
- [x] Document R² validation methodology
- [x] Create `scripts/dowhy/fit_scm.py` (subprocess worker)
- [x] Create test fixtures (synthetic and edge cases)
- [x] Document serialization approach
- [ ] Implement `SCMFitter.fit_dynamic()` in lift-sys (Python 3.13)
- [ ] Write unit tests for subprocess integration
- [ ] Write integration tests (end-to-end)
- [ ] Performance benchmarks (1000 traces, 100 nodes)
- [ ] Documentation updates (user guide)

### Blocked Dependencies

- None (all prerequisites complete)

### Timeline Estimate

- **Subprocess wrapper**: ✅ Done (1 day)
- **Test fixtures**: ✅ Done (0.5 days)
- **SCMFitter integration**: 1 day
- **Testing and validation**: 0.5 days
- **Documentation**: 0.5 days

**Total**: ~2.5 days remaining for STEP-08 implementation

---

## 10. References

### DoWhy Documentation
- [Modeling GCMs](https://www.pywhy.org/dowhy/v0.11/user_guide/modeling_gcm/index.html)
- [Model Evaluation](https://www.pywhy.org/dowhy/v0.11/user_guide/modeling_gcm/model_evaluation.html)
- [Basic Example](https://www.pywhy.org/dowhy/v0.11/example_notebooks/gcm_basic_example.html)

### Project Files
- `debug/dowhy_exploration.py` - Initial DoWhy experiments
- `specs/dowhy-reverse-mode-spec.md` - Full specification
- `plans/dowhy-execution-plan.md` - Execution roadmap

### External Tools
- DoWhy: `pip install dowhy` (Python 3.11 only)
- NetworkX: Graph manipulation
- Pandas: Data handling
- scikit-learn: R² computation

---

**Research Status**: COMPLETE
**Next Action**: Implement `SCMFitter.fit_dynamic()` using `scripts/dowhy/fit_scm.py`
**Estimated Completion**: 2025-10-28 (2.5 days from now)
