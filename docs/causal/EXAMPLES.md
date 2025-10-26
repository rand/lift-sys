# Causal Analysis Examples

**Date**: 2025-10-26
**Status**: Runnable examples for DoWhy integration
**Audience**: Python developers using lift-sys

---

## Table of Contents

1. [Basic Examples](#basic-examples)
2. [Impact Analysis Examples](#impact-analysis-examples)
3. [Multi-File Analysis Examples](#multi-file-analysis-examples)
4. [Static vs Dynamic Mode Examples](#static-vs-dynamic-mode-examples)
5. [Error Handling Examples](#error-handling-examples)
6. [Performance Optimization Examples](#performance-optimization-examples)
7. [Advanced Examples](#advanced-examples)
8. [Real-World Scenarios](#real-world-scenarios)

---

## Basic Examples

### Example 1: Simple Impact Analysis

**Goal**: Analyze a single file and find what code depends on a function.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

# Setup
config = LifterConfig(
    run_codeql=False,  # Disable for speed
    run_daikon=False,
    run_stack_graphs=False
)

lifter = SpecificationLifter(config)
lifter.load_repository(".")

# Analyze with causal analysis
ir = lifter.lift("src/validators.py", include_causal=True, static_only=True)

# Query impact
impact = ir.causal_impact("validate_input")

# Print results
print("=" * 60)
print("IMPACT ANALYSIS: validate_input()")
print("=" * 60)

for node, effect_size in sorted(
    impact.affected_nodes.items(),
    key=lambda x: x[1],
    reverse=True
):
    ci_low, ci_high = impact.confidence_intervals[node]
    ci_width = ci_high - ci_low

    # Categorize impact
    if effect_size >= 0.8:
        severity = "CRITICAL"
    elif effect_size >= 0.5:
        severity = "HIGH"
    elif effect_size >= 0.2:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    print(f"[{severity:8s}] {node:30s} "
          f"Effect: {effect_size:5.2f} "
          f"(95% CI: [{ci_low:5.2f}, {ci_high:5.2f}], "
          f"width: {ci_width:5.2f})")

print("=" * 60)
```

**Expected Output**:
```
============================================================
IMPACT ANALYSIS: validate_input()
============================================================
[CRITICAL] process_data                Effect:  0.85 (95% CI: [ 0.78,  0.91], width:  0.13)
[HIGH    ] generate_output             Effect:  0.72 (95% CI: [ 0.65,  0.79], width:  0.14)
[MEDIUM  ] log_results                 Effect:  0.35 (95% CI: [ 0.28,  0.42], width:  0.14)
[LOW     ] send_notification           Effect:  0.12 (95% CI: [ 0.05,  0.19], width:  0.14)
============================================================
```

---

### Example 2: Intervention Query

**Goal**: Answer "what if" questions about code changes.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Analyze
ir = lifter.lift("src/main.py", include_causal=True)

# Query: "What if validate_input always returned True?"
impact = ir.causal_intervention({'validate_input': True})

print("INTERVENTION: do(validate_input = True)")
print()

for node, effect in impact.affected_nodes.items():
    print(f"  {node}: {effect:.2f}")

# Example output:
# INTERVENTION: do(validate_input = True)
#
#   process_data: 0.85
#   generate_output: 0.72
#   error_handler: -0.62  (negative = reduces error handling)
```

---

### Example 3: Visualize Causal Graph

**Goal**: Visualize cause-and-effect relationships.

```python
import networkx as nx
import matplotlib.pyplot as plt
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

# Analyze
lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/core.py", include_causal=True)

# Get causal graph
graph = ir.causal_graph

if graph:
    # Create visualization
    plt.figure(figsize=(12, 8))

    # Layout
    pos = nx.spring_layout(graph, seed=42)

    # Color nodes by type
    node_colors = []
    for node in graph.nodes():
        node_type = graph.nodes[node].get('type', 'unknown')
        color_map = {
            'function': 'lightblue',
            'variable': 'lightgreen',
            'return': 'orange',
            'effect': 'pink'
        }
        node_colors.append(color_map.get(node_type, 'gray'))

    # Draw
    nx.draw(
        graph, pos,
        with_labels=True,
        node_color=node_colors,
        node_size=1000,
        font_size=8,
        font_weight='bold',
        arrows=True,
        edge_color='gray',
        arrowsize=20
    )

    plt.title("Causal Graph: src/core.py", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("causal_graph.png", dpi=300, bbox_inches='tight')
    print("Graph saved to causal_graph.png")
```

---

## Impact Analysis Examples

### Example 4: Find Critical Dependencies

**Goal**: Identify functions with the highest downstream impact.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import networkx as nx

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/main.py", include_causal=True)

# Get all functions in graph
scm = ir.get_causal_scm()
graph = scm.graph

function_nodes = [
    node for node in graph.nodes()
    if graph.nodes[node].get('type') == 'function'
]

# Compute importance scores
importance = {}
for func in function_nodes:
    # Number of downstream nodes
    descendants = nx.descendants(graph, func)
    importance[func] = len(descendants)

# Sort by importance
sorted_funcs = sorted(
    importance.items(),
    key=lambda x: x[1],
    reverse=True
)

# Print top 10
print("TOP 10 MOST CRITICAL FUNCTIONS")
print("=" * 60)
print(f"{'Rank':<6} {'Function':<40} {'Dependencies':<15}")
print("-" * 60)

for rank, (func, deps) in enumerate(sorted_funcs[:10], 1):
    print(f"{rank:<6} {func:<40} {deps:<15}")

print("=" * 60)
```

**Expected Output**:
```
TOP 10 MOST CRITICAL FUNCTIONS
============================================================
Rank   Function                                 Dependencies
------------------------------------------------------------
1      validate_input                           25
2      load_config                              18
3      process_data                             12
4      init_database                            10
5      authenticate_user                        8
6      generate_output                          6
7      handle_error                             4
8      log_message                              2
9      send_notification                        1
10     cleanup                                  0
============================================================
```

---

### Example 5: Compare Function Importance

**Goal**: Compare impact of multiple functions side-by-side.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/api.py", include_causal=True)

# Functions to compare
functions = ['validate_request', 'process_request', 'format_response']

# Analyze each
print("FUNCTION COMPARISON")
print("=" * 80)

all_impacts = {}
for func in functions:
    impact = ir.causal_impact(func)
    all_impacts[func] = impact.affected_nodes

# Find all affected nodes
all_nodes = set()
for impacts in all_impacts.values():
    all_nodes.update(impacts.keys())

# Print comparison table
print(f"{'Node':<30}", end='')
for func in functions:
    print(f"{func:<20}", end='')
print()
print("-" * 80)

for node in sorted(all_nodes):
    print(f"{node:<30}", end='')
    for func in functions:
        effect = all_impacts[func].get(node, 0.0)
        print(f"{effect:>8.2f}           ", end='')
    print()

print("=" * 80)
```

**Expected Output**:
```
FUNCTION COMPARISON
================================================================================
Node                          validate_request    process_request     format_response
------------------------------------------------------------------------------------
authenticate                      0.85                0.00                0.00
database_query                    0.72                0.90                0.00
error_handler                     0.45                0.65                0.10
response_builder                  0.30                0.80                0.95
logger                            0.15                0.20                0.05
================================================================================
```

---

## Multi-File Analysis Examples

### Example 6: Analyze Entire Project

**Goal**: Build causal graph for entire codebase.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import networkx as nx

# Setup with resource limits
config = LifterConfig(
    run_codeql=False,
    run_daikon=False,
    run_stack_graphs=False,
    max_files=100,  # Limit for performance
    max_file_size_mb=5.0
)

lifter = SpecificationLifter(config)
lifter.load_repository(".")

# Discover files
files = lifter.discover_python_files()
print(f"Found {len(files)} Python files")

# Analyze all
print("Analyzing files...")
all_irs = []
for i, file in enumerate(files[:50], 1):  # Limit to 50 for demo
    print(f"  [{i:2d}/50] {file}")
    try:
        ir = lifter.lift(str(file), include_causal=True, static_only=True)
        all_irs.append(ir)
    except Exception as e:
        print(f"    ERROR: {e}")

print(f"\nSuccessfully analyzed {len(all_irs)} files")

# Merge causal graphs
merged_graph = nx.DiGraph()
for ir in all_irs:
    graph = ir.causal_graph
    if graph:
        merged_graph = nx.compose(merged_graph, graph)

print(f"\nMerged causal graph:")
print(f"  Nodes: {merged_graph.number_of_nodes()}")
print(f"  Edges: {merged_graph.number_of_edges()}")

# Find most connected nodes
in_degrees = dict(merged_graph.in_degree())
out_degrees = dict(merged_graph.out_degree())

print(f"\nTop 5 most depended-on nodes (high in-degree):")
for node, degree in sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {node}: {degree} incoming edges")

print(f"\nTop 5 most impactful nodes (high out-degree):")
for node, degree in sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
    print(f"  {node}: {degree} outgoing edges")
```

---

### Example 7: Cross-File Impact Analysis

**Goal**: Understand how changes in one file affect another.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import networkx as nx

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Analyze multiple files
files = ["src/models.py", "src/api.py", "src/database.py"]
irs = {}

for file in files:
    irs[file] = lifter.lift(file, include_causal=True)

# Merge graphs
merged = nx.DiGraph()
for ir in irs.values():
    if ir.causal_graph:
        merged = nx.compose(merged, ir.causal_graph)

# Query: What in api.py depends on User model in models.py?
source = "User"  # From models.py
api_nodes = [
    node for node in merged.nodes()
    if node.startswith("api.")
]

print(f"Impact of '{source}' on api.py:")
print("=" * 60)

for node in api_nodes:
    if nx.has_path(merged, source, node):
        path = nx.shortest_path(merged, source, node)
        print(f"  {node}:")
        print(f"    Path: {' → '.join(path)}")
        print(f"    Length: {len(path) - 1} hops")

print("=" * 60)
```

---

## Static vs Dynamic Mode Examples

### Example 8: Compare Static and Dynamic Analysis

**Goal**: See accuracy difference between modes.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import pandas as pd

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Static mode (no traces)
ir_static = lifter.lift("src/calc.py", include_causal=True, static_only=True)

# Dynamic mode (with traces)
# Collect traces by running code
traces = pd.DataFrame({
    'add': [2, 4, 6, 8, 10],
    'multiply': [1, 4, 9, 16, 25],
    'result': [3, 8, 15, 24, 35]
})

ir_dynamic = lifter.lift("src/calc.py", include_causal=True, traces=traces)

# Compare metadata
print("STATIC MODE:")
if ir_static.causal_metadata:
    print(f"  R²: {ir_static.causal_metadata.validation_r2:.3f}")
    print(f"  Traces: {ir_static.causal_metadata.trace_count}")
    print(f"  Static only: {ir_static.causal_metadata.static_only}")

print("\nDYNAMIC MODE:")
if ir_dynamic.causal_metadata:
    print(f"  R²: {ir_dynamic.causal_metadata.validation_r2:.3f}")
    print(f"  Traces: {ir_dynamic.causal_metadata.trace_count}")
    print(f"  Static only: {ir_dynamic.causal_metadata.static_only}")

# Compare interventions
intervention = {'add': 5}

impact_static = ir_static.causal_intervention(intervention)
impact_dynamic = ir_dynamic.causal_intervention(intervention)

print("\nINTERVENTION COMPARISON: do(add = 5)")
print("=" * 70)
print(f"{'Node':<20} {'Static Effect':<15} {'Dynamic Effect':<15} {'Diff':<10}")
print("-" * 70)

all_nodes = set(impact_static.affected_nodes.keys()) | set(impact_dynamic.affected_nodes.keys())

for node in sorted(all_nodes):
    static_effect = impact_static.affected_nodes.get(node, 0.0)
    dynamic_effect = impact_dynamic.affected_nodes.get(node, 0.0)
    diff = abs(static_effect - dynamic_effect)

    print(f"{node:<20} {static_effect:>8.2f}       {dynamic_effect:>8.2f}        {diff:>8.2f}")

print("=" * 70)
```

**Expected Output**:
```
STATIC MODE:
  R²: 0.650
  Traces: 0
  Static only: True

DYNAMIC MODE:
  R²: 0.850
  Traces: 5
  Static only: False

INTERVENTION COMPARISON: do(add = 5)
======================================================================
Node                 Static Effect   Dynamic Effect   Diff
----------------------------------------------------------------------
multiply                 0.50            0.75            0.25
result                   0.85            0.92            0.07
======================================================================
```

---

### Example 9: Collect Execution Traces

**Goal**: Generate traces for dynamic analysis.

```python
import pandas as pd
import sys
from io import StringIO

# Code to analyze
code = """
def validate(x):
    return x > 0

def process(x):
    if validate(x):
        return x * 2
    return 0

def run(x):
    validated = validate(x)
    processed = process(x)
    return processed
"""

# Instrumentation to collect traces
trace_data = []

class Tracer:
    def __init__(self):
        self.current_trace = {}

    def trace_call(self, name, value):
        self.current_trace[name] = value

    def save_trace(self):
        trace_data.append(self.current_trace.copy())
        self.current_trace = {}

tracer = Tracer()

# Execute code with tracing
exec(code)

# Run with different inputs
test_inputs = [5, -3, 10, 0, 7]

for x in test_inputs:
    tracer.current_trace['input'] = x

    # Manually trace (in practice, use ast.NodeTransformer to inject)
    validated = validate(x)
    tracer.trace_call('validate', validated)

    processed = process(x)
    tracer.trace_call('process', processed)

    result = run(x)
    tracer.trace_call('result', result)

    tracer.save_trace()

# Convert to DataFrame
traces = pd.DataFrame(trace_data)
print("Collected traces:")
print(traces)

# Use for causal analysis
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/code.py", include_causal=True, traces=traces)

print(f"\nCausal metadata:")
print(f"  R²: {ir.causal_metadata.validation_r2:.3f}")
print(f"  Traces used: {ir.causal_metadata.trace_count}")
```

---

## Error Handling Examples

### Example 10: Graceful Error Handling

**Goal**: Handle missing causal models and invalid queries.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from lift_sys.causal import InterventionError

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Analyze WITHOUT causal analysis
ir_no_causal = lifter.lift("src/main.py")  # include_causal=False

# Try to query (should return None)
impact = ir_no_causal.causal_impact("some_function")

if impact is None:
    print("Causal analysis not enabled. Re-run with include_causal=True")
else:
    print(f"Impact: {impact.affected_nodes}")

# Analyze WITH causal analysis
ir_causal = lifter.lift("src/main.py", include_causal=True)

# Try to query non-existent node
try:
    impact = ir_causal.causal_impact("nonexistent_function")
except InterventionError as e:
    print(f"Error: {e}")
    print("Available nodes:")
    if ir_causal.causal_graph:
        for node in sorted(ir_causal.causal_graph.nodes())[:10]:
            print(f"  - {node}")

# Check if node exists before querying
node_to_query = "validate_input"
if ir_causal.causal_graph and node_to_query in ir_causal.causal_graph.nodes():
    impact = ir_causal.causal_impact(node_to_query)
    print(f"\nImpact of {node_to_query}: {impact.affected_nodes}")
else:
    print(f"Node '{node_to_query}' not found in causal graph")
```

---

### Example 11: Handle Low R² Scores

**Goal**: Deal with poorly fitted models.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from lift_sys.causal import ValidationError
import pandas as pd

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Try with insufficient traces
traces_small = pd.DataFrame({
    'func_a': [1, 2],
    'func_b': [2, 4]
})

try:
    ir = lifter.lift("src/main.py", include_causal=True, traces=traces_small)
except ValidationError as e:
    print(f"Validation error: {e}")
    print(f"R² = {e.r2_score:.2f} (threshold: {e.threshold:.2f})")
    print("\nSolutions:")
    print("  1. Collect more traces (20+ recommended)")
    print("  2. Use static_only mode for approximate results")
    print("  3. Lower R² threshold (if approximate OK)")

    # Fallback to static mode
    print("\nFalling back to static mode...")
    ir_static = lifter.lift("src/main.py", include_causal=True, static_only=True)
    print(f"Static R²: {ir_static.causal_metadata.validation_r2:.2f}")

# Check R² before using
ir = lifter.lift("src/main.py", include_causal=True)

if ir.causal_metadata:
    r2 = ir.causal_metadata.validation_r2

    if r2 < 0.5:
        print(f"WARNING: Very low R² ({r2:.2f})")
        print("Results may be unreliable. Consider:")
        print("  - Collecting more/better traces")
        print("  - Using static mode instead")
    elif r2 < 0.7:
        print(f"CAUTION: Moderate R² ({r2:.2f})")
        print("Results are approximate. Use with care.")
    else:
        print(f"Good R² ({r2:.2f}). Proceed with confidence.")
```

---

## Performance Optimization Examples

### Example 12: Cache IR Objects

**Goal**: Avoid re-analyzing the same files.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import pickle
from pathlib import Path
import hashlib

class CachedLifter:
    def __init__(self, lifter, cache_dir=".causal_cache"):
        self.lifter = lifter
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _get_cache_key(self, file_path):
        """Generate cache key from file path and content hash."""
        content = Path(file_path).read_text()
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{Path(file_path).stem}_{content_hash}.pkl"

    def lift_cached(self, file_path, **kwargs):
        """Lift with caching."""
        cache_key = self._get_cache_key(file_path)
        cache_file = self.cache_dir / cache_key

        # Check cache
        if cache_file.exists():
            print(f"Cache HIT: {file_path}")
            with open(cache_file, 'rb') as f:
                return pickle.load(f)

        # Cache miss - analyze
        print(f"Cache MISS: {file_path}")
        ir = self.lifter.lift(file_path, **kwargs)

        # Save to cache
        with open(cache_file, 'wb') as f:
            pickle.dump(ir, f)

        return ir

# Usage
lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
cached_lifter = CachedLifter(lifter)

# First call - analyzes and caches
ir1 = cached_lifter.lift_cached("src/main.py", include_causal=True)

# Second call - loads from cache (fast!)
ir2 = cached_lifter.lift_cached("src/main.py", include_causal=True)

# Query both (same results)
impact1 = ir1.causal_impact("validate_input")
impact2 = ir2.causal_impact("validate_input")

assert impact1.affected_nodes == impact2.affected_nodes
print("Cached results match!")
```

---

### Example 13: Batch Analysis with Progress

**Goal**: Analyze many files efficiently.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

def analyze_file(lifter, file_path):
    """Analyze single file (can run in parallel)."""
    try:
        ir = lifter.lift(str(file_path), include_causal=True, static_only=True)
        return (file_path, ir, None)
    except Exception as e:
        return (file_path, None, str(e))

# Setup
config = LifterConfig(
    run_codeql=False,
    run_daikon=False,
    run_stack_graphs=False,
    max_files=100
)

lifter = SpecificationLifter(config)
lifter.load_repository(".")
files = lifter.discover_python_files()[:50]  # Limit for demo

# Parallel analysis with progress bar
results = []
errors = []

with ThreadPoolExecutor(max_workers=4) as executor:
    # Submit all tasks
    futures = {
        executor.submit(analyze_file, lifter, f): f
        for f in files
    }

    # Collect results with progress bar
    for future in tqdm(as_completed(futures), total=len(futures), desc="Analyzing"):
        file_path, ir, error = future.result()
        if error:
            errors.append((file_path, error))
        else:
            results.append((file_path, ir))

print(f"\nSuccess: {len(results)} files")
print(f"Errors: {len(errors)} files")

if errors:
    print("\nFailed files:")
    for file, error in errors[:5]:  # Show first 5
        print(f"  {file}: {error}")
```

---

## Advanced Examples

### Example 14: Custom Causal Mechanisms

**Goal**: Override default mechanisms with domain knowledge.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from lift_sys.causal import CausalGraphBuilder, SCMFitter
from dowhy import gcm
import pandas as pd

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Get AST and call graph (implementation detail - simplified)
ast_tree = ...  # Parse code
call_graph = ...  # Build call graph

# Build causal graph
builder = CausalGraphBuilder()
graph = builder.build(ast_tree, call_graph)

# Create SCM
scm = gcm.StructuralCausalModel(graph)

# Custom mechanism for specific node (using domain knowledge)
def custom_validation_mechanism(x):
    """We know validation always returns True for x > 0."""
    return x > 0

scm.set_causal_mechanism(
    'validate_input',
    gcm.ClassifierFCM(classifier=custom_validation_mechanism)
)

# Auto-assign remaining mechanisms
gcm.auto.assign_causal_mechanisms(scm, exclude=['validate_input'])

# Fit with traces
traces = pd.DataFrame({
    'input': [5, -3, 10, 0, 7],
    'validate_input': [True, False, True, False, True],
    'process_data': [10, 0, 20, 0, 14]
})

gcm.fit(scm, traces)

# Use for interventions
from lift_sys.causal import InterventionEngine

engine = InterventionEngine()
impact = engine.estimate_impact(scm, {'input': 100})

print(f"Impact of input=100: {impact.affected_nodes}")
```

---

### Example 15: Counterfactual Analysis

**Goal**: Answer "what if history was different?" questions.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
from dowhy import gcm
import pandas as pd

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")

# Collect execution traces
traces = pd.DataFrame({
    'user_authenticated': [True, False, True, True, False],
    'request_validated': [True, False, True, True, False],
    'data_processed': [True, False, True, True, False],
    'response_sent': [True, False, True, True, False]
})

# Analyze with traces
ir = lifter.lift("src/api.py", include_causal=True, traces=traces)
scm = ir.get_causal_scm()

# Counterfactual question:
# "In the failed request (row 1), what if user was authenticated?"

failed_request = traces.iloc[1:2]  # Row with index 1
print("Original failed request:")
print(failed_request)

# Counterfactual intervention
counterfactual = gcm.counterfactual_samples(
    scm,
    queries={'user_authenticated': lambda x: True},  # Force True
    observed_data=failed_request
)

print("\nCounterfactual (if user_authenticated was True):")
print(counterfactual)

# Compare
print("\nComparison:")
print(f"  Actual response_sent: {failed_request['response_sent'].values[0]}")
print(f"  Counterfactual response_sent: {counterfactual['response_sent'].values[0]}")
print(f"  Conclusion: Authentication was the root cause!")
```

---

## Real-World Scenarios

### Example 16: Pre-Refactoring Impact Assessment

**Goal**: Assess risk before refactoring critical code.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

def assess_refactoring_risk(file_path, function_name):
    """Assess risk of refactoring a function."""

    lifter = SpecificationLifter(LifterConfig())
    lifter.load_repository(".")

    # Analyze
    ir = lifter.lift(file_path, include_causal=True)
    impact = ir.causal_impact(function_name)

    if not impact:
        return "UNKNOWN", []

    # Count high-impact dependencies
    critical = []
    high_risk = []
    medium_risk = []

    for node, effect in impact.affected_nodes.items():
        if effect >= 0.8:
            critical.append((node, effect))
        elif effect >= 0.5:
            high_risk.append((node, effect))
        elif effect >= 0.2:
            medium_risk.append((node, effect))

    # Determine risk level
    if critical:
        risk = "CRITICAL"
    elif len(high_risk) >= 5:
        risk = "HIGH"
    elif len(high_risk) >= 2 or len(medium_risk) >= 10:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    recommendations = []

    if risk == "CRITICAL":
        recommendations.append(f"⚠️  {len(critical)} critical dependencies found!")
        recommendations.append("   Recommendations:")
        recommendations.append("   - Create comprehensive test suite first")
        recommendations.append("   - Refactor incrementally with frequent testing")
        recommendations.append("   - Consider feature flags for gradual rollout")

    elif risk == "HIGH":
        recommendations.append(f"⚡ {len(high_risk)} high-impact dependencies")
        recommendations.append("   Recommendations:")
        recommendations.append("   - Write tests for affected functions")
        recommendations.append("   - Use branch-by-abstraction pattern")

    elif risk == "MEDIUM":
        recommendations.append(f"📝 {len(medium_risk)} medium-impact dependencies")
        recommendations.append("   Recommendations:")
        recommendations.append("   - Standard testing practices sufficient")

    else:
        recommendations.append("✅ Low risk - safe to refactor")

    return risk, recommendations

# Usage
risk, recs = assess_refactoring_risk("src/core.py", "validate_input")

print(f"REFACTORING RISK ASSESSMENT: validate_input()")
print(f"Risk Level: {risk}")
print()
for rec in recs:
    print(rec)
```

---

### Example 17: Root Cause Analysis for Production Bug

**Goal**: Find the root cause of a production bug.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import networkx as nx

def find_root_cause(file_path, buggy_function, symptom_value):
    """Find potential root causes of a bug."""

    lifter = SpecificationLifter(LifterConfig())
    lifter.load_repository(".")
    ir = lifter.lift(file_path, include_causal=True)

    scm = ir.get_causal_scm()
    if not scm:
        return []

    graph = scm.graph

    # Find all ancestors (potential root causes)
    ancestors = nx.ancestors(graph, buggy_function)

    # Test each ancestor with intervention
    root_causes = []

    for ancestor in ancestors:
        impact = ir.causal_impact(ancestor)

        if not impact:
            continue

        effect_on_bug = impact.affected_nodes.get(buggy_function, 0.0)

        if effect_on_bug >= 0.5:  # High impact
            ci_low, ci_high = impact.confidence_intervals.get(
                buggy_function, (0, 0)
            )

            root_causes.append({
                'function': ancestor,
                'effect_size': effect_on_bug,
                'confidence': (ci_low, ci_high),
                'path': nx.shortest_path(graph, ancestor, buggy_function)
            })

    # Sort by effect size
    root_causes.sort(key=lambda x: x['effect_size'], reverse=True)

    return root_causes

# Usage
causes = find_root_cause(
    "src/payment.py",
    "process_payment",
    "transaction_failed"
)

print("ROOT CAUSE ANALYSIS: process_payment()")
print("=" * 70)

for i, cause in enumerate(causes[:5], 1):
    print(f"\n{i}. {cause['function']}")
    print(f"   Effect size: {cause['effect_size']:.2f}")
    print(f"   95% CI: [{cause['confidence'][0]:.2f}, {cause['confidence'][1]:.2f}]")
    print(f"   Causal path: {' → '.join(cause['path'])}")

print("\n" + "=" * 70)
print("RECOMMENDATION: Investigate functions in order of effect size")
```

---

### Example 18: Test Prioritization

**Goal**: Prioritize tests by causal importance.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig
import networkx as nx

def prioritize_tests(repo_path, output_file="test_priorities.txt"):
    """Generate test priority list based on causal importance."""

    config = LifterConfig(
        run_codeql=False,
        run_daikon=False,
        run_stack_graphs=False,
        max_files=100
    )

    lifter = SpecificationLifter(config)
    lifter.load_repository(repo_path)

    # Analyze all files
    files = lifter.discover_python_files()
    all_irs = []

    print(f"Analyzing {len(files)} files...")
    for i, file in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {file}")
        try:
            ir = lifter.lift(str(file), include_causal=True, static_only=True)
            all_irs.append((file, ir))
        except Exception as e:
            print(f"    Error: {e}")

    # Compute importance scores
    function_importance = {}

    for file, ir in all_irs:
        if not ir.causal_graph:
            continue

        graph = ir.causal_graph

        for node in graph.nodes():
            if graph.nodes[node].get('type') != 'function':
                continue

            # Importance metrics
            descendants = len(nx.descendants(graph, node))
            in_degree = graph.in_degree(node)
            out_degree = graph.out_degree(node)

            # Combined score
            importance = (
                descendants * 0.5 +      # Downstream impact
                out_degree * 0.3 +       # Direct dependencies
                in_degree * 0.2          # Usage frequency
            )

            function_importance[f"{file}::{node}"] = importance

    # Sort by importance
    sorted_functions = sorted(
        function_importance.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Write to file
    with open(output_file, 'w') as f:
        f.write("TEST PRIORITIZATION (by causal importance)\n")
        f.write("=" * 70 + "\n\n")

        for rank, (func, score) in enumerate(sorted_functions[:50], 1):
            priority = "P0" if score >= 20 else "P1" if score >= 10 else "P2"
            f.write(f"[{priority}] Rank {rank:2d}: {func:<50} Score: {score:.1f}\n")

    print(f"\nTest priorities written to {output_file}")
    return sorted_functions

# Usage
priorities = prioritize_tests(".")
```

---

**Related Documentation**:
- [Causal Analysis Guide](CAUSAL_ANALYSIS_GUIDE.md) - Concepts and best practices
- [API Reference](API_REFERENCE.md) - Complete API specification
- [DoWhy Integration Spec](../planning/DOWHY_INTEGRATION_SPEC.md) - Technical design
