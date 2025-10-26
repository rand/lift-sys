# Causal Analysis API Reference

**Date**: 2025-10-26
**Status**: API documentation for DoWhy integration
**Version**: 0.1.0

---

## Table of Contents

1. [Overview](#overview)
2. [SpecificationLifter API](#specificationlifter-api)
3. [IntermediateRepresentation API](#intermediaterepresentation-api)
4. [CausalGraphBuilder API](#causalgraphbuilder-api)
5. [SCMFitter API](#scmfitter-api)
6. [InterventionEngine API](#interventionengine-api)
7. [Data Models](#data-models)
8. [Error Types](#error-types)
9. [Utility Functions](#utility-functions)

---

## Overview

This document provides the complete API reference for causal analysis capabilities in lift-sys reverse mode.

**Core APIs**:
- `SpecificationLifter.lift()` - Lift code with causal analysis
- `IR.causal_impact()` - Query intervention effects
- `IR.causal_intervention()` - Perform interventional queries
- `IR.get_causal_scm()` - Access structural causal model
- `IR.causal_graph` - Access causal graph property

**When to use**:
- Import `from lift_sys.reverse_mode import SpecificationLifter, LifterConfig`
- Enable causal analysis with `include_causal=True`
- Query results via `IR` convenience methods

---

## SpecificationLifter API

### `SpecificationLifter.lift()`

**Signature**:
```python
def lift(
    self,
    target_module: str,
    *,
    include_causal: bool = False,
    traces: Optional[pd.DataFrame] = None,
    static_only: bool = False
) -> IntermediateRepresentation
```

**Description**: Lift code to IR with optional causal analysis.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_module` | `str` | Required | Path to Python module to analyze (e.g., `"src/main.py"`) |
| `include_causal` | `bool` | `False` | Enable causal analysis (adds `causal_model` to IR) |
| `traces` | `Optional[pd.DataFrame]` | `None` | Execution traces for dynamic SCM fitting (columns = node names) |
| `static_only` | `bool` | `False` | Use static approximation (ignore `traces`) |

**Returns**: `IntermediateRepresentation` with optional causal model

**Raises**:
- `RepositoryNotLoadedError` - Repository not loaded (call `load_repository()` first)
- `AnalysisError` - Analysis failed (file not found, parse error, etc.)
- `GraphBuildError` - Causal graph construction failed
- `FittingError` - SCM fitting failed
- `ValidationError` - SCM validation failed (R² < threshold)

**Examples**:

```python
# Static-only mode (no traces)
ir = lifter.lift("main.py", include_causal=True, static_only=True)

# Dynamic mode (with traces)
import pandas as pd

traces = pd.DataFrame({
    'validate_input': [True, False, True],
    'process_data': [42, None, 84],
    'output': ['Success', 'Error', 'Success']
})

ir = lifter.lift("main.py", include_causal=True, traces=traces)

# Causal analysis disabled (default)
ir = lifter.lift("main.py")  # No causal model
```

**Notes**:
- `include_causal=False` (default) preserves backward compatibility
- `traces` must have columns matching node names in causal graph
- `static_only=True` ignores `traces` parameter
- Static mode is faster (~5s) but less accurate (R² ≈ 0.5-0.7)
- Dynamic mode is slower (~30s) but more accurate (R² ≈ 0.7-0.9)

---

## IntermediateRepresentation API

### `IR.causal_impact()`

**Signature**:
```python
def causal_impact(
    self,
    node: str,
    num_samples: int = 1000
) -> Optional[ImpactEstimate]
```

**Description**: Estimate causal impact of a node on downstream nodes.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `node` | `str` | Required | Name of node to analyze (function, variable, etc.) |
| `num_samples` | `int` | `1000` | Number of samples for estimation (higher = more accurate) |

**Returns**: `ImpactEstimate` or `None` if causal model not available

**Raises**:
- `ValueError` - Node not found in causal graph
- `InterventionError` - Intervention query failed

**Examples**:

```python
# Basic usage
ir = lifter.lift("main.py", include_causal=True)
impact = ir.causal_impact("validate_input")

print(f"Affected nodes: {impact.affected_nodes}")
# {'process_data': 0.85, 'generate_output': 0.72}

print(f"Confidence intervals: {impact.confidence_intervals}")
# {'process_data': (0.78, 0.91), 'generate_output': (0.65, 0.79)}

# High accuracy mode
impact_hq = ir.causal_impact("validate_input", num_samples=10000)

# Check if causal model exists
if not ir.causal_model:
    print("Causal analysis not enabled - run with include_causal=True")
```

**Notes**:
- Returns `None` if `include_causal=False` was used
- Higher `num_samples` increases accuracy but slows query (~1ms per 100 samples)
- Effect sizes use Cohen's d: `(E[Y|do(X)] - E[Y]) / std(Y)`
- Confidence intervals are 95% bootstrap intervals

---

### `IR.causal_intervention()`

**Signature**:
```python
def causal_intervention(
    self,
    interventions: dict[str, Any],
    num_samples: int = 1000
) -> Optional[ImpactEstimate]
```

**Description**: Perform interventional query `do(X=x)` on causal model.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interventions` | `dict[str, Any]` | Required | Dict mapping node names to intervention values |
| `num_samples` | `int` | `1000` | Number of samples for estimation |

**Returns**: `ImpactEstimate` or `None` if causal model not available

**Raises**:
- `ValueError` - Invalid intervention (node not found)
- `InterventionError` - Intervention query failed

**Examples**:

```python
# Single intervention
impact = ir.causal_intervention({'validate_input': True})

# Multiple simultaneous interventions
impact = ir.causal_intervention({
    'validate_input': True,
    'config_value': 100
})

# Inspect results
for node, effect in impact.affected_nodes.items():
    ci_low, ci_high = impact.confidence_intervals[node]
    print(f"{node}: {effect:.2f} (95% CI: [{ci_low:.2f}, {ci_high:.2f}])")
```

**Notes**:
- Interventions are "do" operations (force values), not observations
- Can intervene on multiple nodes simultaneously
- Effect sizes are relative to baseline (no intervention)

---

### `IR.get_causal_scm()`

**Signature**:
```python
def get_causal_scm(self) -> Optional[gcm.StructuralCausalModel]
```

**Description**: Deserialize and return structural causal model.

**Returns**: `StructuralCausalModel` or `None` if not available

**Examples**:

```python
from dowhy import gcm
import networkx as nx

# Get SCM
scm = ir.get_causal_scm()

if scm:
    # Access causal graph
    graph = scm.graph
    print(f"Nodes: {list(graph.nodes())}")
    print(f"Edges: {list(graph.edges())}")

    # Access mechanisms
    for node in graph.nodes():
        mech = scm.causal_mechanism[node]
        print(f"{node}: {type(mech).__name__}")

    # Find descendants of a node
    descendants = nx.descendants(graph, "validate_input")
    print(f"Affected by validate_input: {descendants}")

    # Use DoWhy directly
    samples = gcm.interventional_samples(
        scm,
        {'validate_input': True},
        num_samples_to_draw=500
    )
    print(samples.head())
```

**Notes**:
- Returns `None` if `include_causal=False` was used
- Deserialization is lazy (only happens on first call)
- Subsequent calls return cached SCM

---

### `IR.causal_graph` (Property)

**Signature**:
```python
@property
def causal_graph(self) -> Optional[nx.DiGraph]
```

**Description**: Access causal graph (DAG) as NetworkX DiGraph.

**Returns**: `nx.DiGraph` or `None` if causal model not available

**Examples**:

```python
import networkx as nx
import matplotlib.pyplot as plt

# Get graph
graph = ir.causal_graph

if graph:
    # Graph properties
    print(f"Nodes: {graph.number_of_nodes()}")
    print(f"Edges: {graph.number_of_edges()}")
    print(f"Is DAG: {nx.is_directed_acyclic_graph(graph)}")

    # Node attributes
    for node, attrs in graph.nodes(data=True):
        print(f"{node}: type={attrs.get('type')}")

    # Edge attributes
    for u, v, attrs in graph.edges(data=True):
        print(f"{u} → {v}: {attrs.get('edge_type')}")

    # Visualize
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_color='lightblue',
            arrows=True)
    plt.savefig("causal_graph.png")
```

**Notes**:
- Graph is guaranteed to be a DAG (acyclic)
- Node attributes: `type` (function, variable, return, effect)
- Edge attributes: `edge_type` (data_flow, control_flow, call)

---

### `IR.causal_paths()`

**Signature**:
```python
def causal_paths(
    self,
    source: str,
    target: str,
    max_paths: int = 10
) -> Optional[list[list[str]]]
```

**Description**: Find causal paths from source to target node.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `source` | `str` | Required | Source node name |
| `target` | `str` | Required | Target node name |
| `max_paths` | `int` | `10` | Maximum number of paths to return |

**Returns**: List of paths (each path is list of node names), or `None` if not available

**Raises**:
- `ValueError` - Source or target not found in graph

**Examples**:

```python
# Find all paths from validate_input to output
paths = ir.causal_paths("validate_input", "output")

if paths:
    print(f"Found {len(paths)} causal paths:")
    for i, path in enumerate(paths, 1):
        print(f"  Path {i}: {' → '.join(path)}")

# Output:
# Found 2 causal paths:
#   Path 1: validate_input → process_data → output
#   Path 2: validate_input → config_loader → process_data → output
```

**Notes**:
- Returns all simple paths (no cycles)
- Paths are sorted by length (shortest first)
- If `max_paths` exceeded, returns first N shortest paths

---

## CausalGraphBuilder API

### `CausalGraphBuilder.build()`

**Signature**:
```python
def build(
    self,
    ast: ast.Module,
    call_graph: nx.DiGraph,
    control_flow: Optional[nx.DiGraph] = None
) -> nx.DiGraph
```

**Description**: Build causal graph from AST and call graph.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ast` | `ast.Module` | Required | Python AST (from `ast.parse()`) |
| `call_graph` | `nx.DiGraph` | Required | Function call graph |
| `control_flow` | `Optional[nx.DiGraph]` | `None` | Control flow graph (optional) |

**Returns**: Causal DAG (`nx.DiGraph`)

**Raises**:
- `ValueError` - Graph is cyclic (not a DAG)
- `GraphBuildError` - Construction failed

**Examples**:

```python
import ast
import networkx as nx
from lift_sys.causal import CausalGraphBuilder

# Parse code
code = """
def validate(x):
    return x > 0

def process(x):
    if validate(x):
        return x * 2
    return 0
"""

ast_tree = ast.parse(code)

# Build call graph (simplified - use real implementation)
call_graph = nx.DiGraph()
call_graph.add_edge("process", "validate")

# Build causal graph
builder = CausalGraphBuilder()
causal_graph = builder.build(ast_tree, call_graph)

print(f"Causal graph: {causal_graph.number_of_nodes()} nodes")
print(f"Edges: {list(causal_graph.edges())}")
```

**Notes**:
- Automatically prunes non-causal edges (logging, pure I/O)
- Validates DAG property (raises if cyclic)
- Adds node/edge attributes for metadata

---

## SCMFitter API

### `SCMFitter.fit()`

**Signature**:
```python
def fit(
    self,
    causal_graph: nx.DiGraph,
    traces: Optional[pd.DataFrame] = None,
    static_only: bool = False
) -> gcm.StructuralCausalModel
```

**Description**: Fit structural causal model from graph and traces.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `causal_graph` | `nx.DiGraph` | Required | Causal DAG from `CausalGraphBuilder` |
| `traces` | `Optional[pd.DataFrame]` | `None` | Execution traces (columns = nodes) |
| `static_only` | `bool` | `False` | Use static approximation (ignore traces) |

**Returns**: Fitted `StructuralCausalModel`

**Raises**:
- `FittingError` - Fitting failed
- `ValidationError` - Cross-validation R² < threshold (default: 0.7)

**Examples**:

```python
import pandas as pd
from lift_sys.causal import CausalGraphBuilder, SCMFitter

# Build graph
builder = CausalGraphBuilder()
graph = builder.build(ast_tree, call_graph)

# Static mode (no traces)
fitter = SCMFitter()
scm_static = fitter.fit(graph, static_only=True)

# Dynamic mode (with traces)
traces = pd.DataFrame({
    'validate': [True, False, True, True],
    'process': [42, 0, 84, 126]
})

scm_dynamic = fitter.fit(graph, traces=traces)

# Check validation R²
print(f"Model R²: {scm_dynamic.validation_r2}")
```

**Notes**:
- Static mode uses linear approximation from code structure
- Dynamic mode fits from traces using `dowhy.gcm.auto.assign_causal_mechanisms()`
- Cross-validates with 80/20 train/test split
- Warns if R² < 0.7 (can still use, but less accurate)

---

## InterventionEngine API

### `InterventionEngine.estimate_impact()`

**Signature**:
```python
def estimate_impact(
    self,
    scm: gcm.StructuralCausalModel,
    intervention: dict[str, Any],
    num_samples: int = 1000
) -> ImpactEstimate
```

**Description**: Estimate impact of intervention on downstream nodes.

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scm` | `gcm.StructuralCausalModel` | Required | Fitted causal model |
| `intervention` | `dict[str, Any]` | Required | Node values to intervene on |
| `num_samples` | `int` | `1000` | Number of samples for estimation |

**Returns**: `ImpactEstimate` with effect sizes and confidence intervals

**Raises**:
- `InterventionError` - Intervention invalid or query failed

**Examples**:

```python
from lift_sys.causal import InterventionEngine

# Fit SCM
scm = fitter.fit(graph, traces=traces)

# Single intervention
engine = InterventionEngine()
impact = engine.estimate_impact(
    scm,
    intervention={'validate': True},
    num_samples=1000
)

print(f"Affected nodes: {impact.affected_nodes}")
print(f"Confidence intervals: {impact.confidence_intervals}")

# Multiple interventions
impact_multi = engine.estimate_impact(
    scm,
    intervention={'validate': True, 'config': 100}
)
```

**Notes**:
- Effect sizes use Cohen's d (standardized difference)
- Confidence intervals are 95% bootstrap intervals
- Higher `num_samples` increases accuracy (linear cost)

---

## Data Models

### `ImpactEstimate`

**Definition**:
```python
from dataclasses import dataclass

@dataclass
class ImpactEstimate:
    """Result of causal intervention query."""

    affected_nodes: dict[str, float]
    """Node name → effect size (Cohen's d)"""

    confidence_intervals: dict[str, tuple[float, float]]
    """Node name → (95% CI lower, 95% CI upper)"""

    sample_size: int
    """Number of samples used for estimation"""

    intervention: dict[str, Any]
    """Intervention that was applied"""
```

**Examples**:

```python
impact = ir.causal_impact("validate_input")

# Access fields
print(f"Effect on process_data: {impact.affected_nodes['process_data']}")
# 0.85

print(f"Confidence interval: {impact.confidence_intervals['process_data']}")
# (0.78, 0.91)

print(f"Sample size: {impact.sample_size}")
# 1000

print(f"Intervention: {impact.intervention}")
# {'validate_input': <intervened_value>}
```

---

### `CausalMetadata`

**Definition**:
```python
from pydantic import BaseModel
from datetime import datetime

class CausalMetadata(BaseModel):
    """Metadata about fitted causal model."""

    graph_json: dict
    """NetworkX graph serialized to JSON"""

    mechanism_types: dict[str, str]
    """Node name → mechanism type (e.g., 'LinearRegression')"""

    fitted_at: datetime
    """Timestamp when model was fitted"""

    trace_count: int
    """Number of traces used for fitting"""

    validation_r2: float
    """Cross-validation R² score"""

    static_only: bool
    """True if static approximation used (no traces)"""

    class Config:
        frozen = True
```

**Examples**:

```python
ir = lifter.lift("main.py", include_causal=True)

if ir.causal_metadata:
    print(f"Fitted at: {ir.causal_metadata.fitted_at}")
    print(f"R² score: {ir.causal_metadata.validation_r2:.2f}")
    print(f"Trace count: {ir.causal_metadata.trace_count}")
    print(f"Static only: {ir.causal_metadata.static_only}")

    for node, mech_type in ir.causal_metadata.mechanism_types.items():
        print(f"  {node}: {mech_type}")
```

---

## Error Types

### `GraphBuildError`

**Description**: Causal graph construction failed.

**Causes**:
- Invalid AST
- Cyclic dependencies
- Empty call graph

**Example**:
```python
from lift_sys.causal import GraphBuildError

try:
    graph = builder.build(ast_tree, call_graph)
except GraphBuildError as e:
    print(f"Graph construction failed: {e}")
    # Check AST validity
    # Check for circular imports
```

---

### `FittingError`

**Description**: SCM fitting failed.

**Causes**:
- Incompatible traces (columns don't match nodes)
- Insufficient data
- Numerical instability

**Example**:
```python
from lift_sys.causal import FittingError

try:
    scm = fitter.fit(graph, traces=traces)
except FittingError as e:
    print(f"Fitting failed: {e}")
    # Check trace columns match graph nodes
    # Ensure sufficient traces (>20 recommended)
```

---

### `ValidationError`

**Description**: SCM validation failed (R² < threshold).

**Causes**:
- Insufficient traces
- Nonlinear relationships not captured
- Poor quality traces

**Example**:
```python
from lift_sys.causal import ValidationError

try:
    scm = fitter.fit(graph, traces=traces)
except ValidationError as e:
    print(f"Validation failed: {e}")
    print(f"R² = {e.r2_score:.2f} (threshold: {e.threshold:.2f})")
    # Collect more traces
    # Try dynamic mode with nonlinear mechanisms
```

---

### `InterventionError`

**Description**: Intervention query failed.

**Causes**:
- Node not found in graph
- Invalid intervention value
- SCM not fitted

**Example**:
```python
from lift_sys.causal import InterventionError

try:
    impact = ir.causal_impact("nonexistent_node")
except InterventionError as e:
    print(f"Intervention failed: {e}")
    # Check node exists in graph
    # Verify SCM is fitted
```

---

## Utility Functions

### `serialize_scm()`

**Signature**:
```python
def serialize_scm(scm: gcm.StructuralCausalModel) -> dict
```

**Description**: Serialize SCM to JSON-compatible dict.

**Examples**:
```python
from lift_sys.causal.utils import serialize_scm

scm = fitter.fit(graph, traces=traces)
scm_json = serialize_scm(scm)

# Save to file
import json
with open("scm.json", "w") as f:
    json.dump(scm_json, f, indent=2)
```

---

### `deserialize_scm()`

**Signature**:
```python
def deserialize_scm(data: dict) -> gcm.StructuralCausalModel
```

**Description**: Deserialize SCM from JSON dict.

**Examples**:
```python
from lift_sys.causal.utils import deserialize_scm
import json

# Load from file
with open("scm.json", "r") as f:
    scm_json = json.load(f)

scm = deserialize_scm(scm_json)

# Use normally
engine = InterventionEngine()
impact = engine.estimate_impact(scm, {'node': value})
```

---

## Type Hints

Complete type signatures for type checkers:

```python
from typing import Optional, Any
import pandas as pd
import networkx as nx
from dowhy import gcm
from lift_sys.ir.models import IntermediateRepresentation

# SpecificationLifter
def lift(
    self,
    target_module: str,
    *,
    include_causal: bool = False,
    traces: Optional[pd.DataFrame] = None,
    static_only: bool = False
) -> IntermediateRepresentation: ...

# IR methods
def causal_impact(
    self,
    node: str,
    num_samples: int = 1000
) -> Optional[ImpactEstimate]: ...

def causal_intervention(
    self,
    interventions: dict[str, Any],
    num_samples: int = 1000
) -> Optional[ImpactEstimate]: ...

def get_causal_scm(self) -> Optional[gcm.StructuralCausalModel]: ...

@property
def causal_graph(self) -> Optional[nx.DiGraph]: ...

def causal_paths(
    self,
    source: str,
    target: str,
    max_paths: int = 10
) -> Optional[list[list[str]]]: ...
```

---

## Migration Guide

### From Non-Causal to Causal Analysis

**Before**:
```python
lifter = SpecificationLifter(config)
lifter.load_repository(".")
ir = lifter.lift("main.py")

# Only structural analysis available
print(ir.signature)
print(ir.effects)
```

**After**:
```python
lifter = SpecificationLifter(config)
lifter.load_repository(".")

# Enable causal analysis
ir = lifter.lift("main.py", include_causal=True)

# Structural analysis still works
print(ir.signature)
print(ir.effects)

# NEW: Causal analysis now available
impact = ir.causal_impact("validate_input")
print(f"Affected nodes: {impact.affected_nodes}")
```

**Key changes**:
- Add `include_causal=True` parameter
- Backward compatible (existing code still works)
- New methods available on `IR` object

---

## Performance Guidelines

| Operation | Latency | Recommendations |
|-----------|---------|-----------------|
| `lift(..., include_causal=True, static_only=True)` | ~5s | Default for quick analysis |
| `lift(..., include_causal=True, traces=...)` | ~30s | Use for high accuracy |
| `ir.causal_impact(node)` | ~50ms | Fast, can call repeatedly |
| `ir.causal_impact(node, num_samples=10000)` | ~500ms | High accuracy mode |
| `ir.get_causal_scm()` (first call) | ~10ms | Deserialization overhead |
| `ir.get_causal_scm()` (cached) | ~1ms | Subsequent calls fast |

**Optimization tips**:
- Use static mode for exploratory analysis
- Cache `IR` objects to avoid re-analysis
- Reduce `num_samples` for interactive queries
- Use dynamic mode only when R² > 0.7 required

---

**Related Documentation**:
- [Causal Analysis Guide](CAUSAL_ANALYSIS_GUIDE.md) - User guide with concepts and examples
- [Examples](EXAMPLES.md) - Runnable code samples
- [DoWhy Integration Spec](../planning/DOWHY_INTEGRATION_SPEC.md) - Technical design
