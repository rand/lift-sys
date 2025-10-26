# Causal Analysis Guide

**Date**: 2025-10-26
**Status**: Documentation for DoWhy integration
**Audience**: Python developers using lift-sys reverse mode

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Quick Start](#2-quick-start)
3. [Core Concepts](#3-core-concepts)
4. [Use Cases](#4-use-cases)
5. [Configuration](#5-configuration)
6. [Best Practices](#6-best-practices)
7. [Troubleshooting](#7-troubleshooting)
8. [Advanced Topics](#8-advanced-topics)

---

## 1. Introduction

### What is Causal Analysis?

Causal analysis in lift-sys allows you to understand **cause-and-effect relationships** in your code, going beyond simple structural analysis to answer questions like:

- "What code will break if I change this function?"
- "Why did this function return an unexpected value?"
- "What would happen if I refactor this module?"

Unlike traditional static analysis that shows you *what* code exists, causal analysis tells you *why* your code behaves the way it does and *what would happen if* you made changes.

### Why Use Causal Analysis?

**Traditional approach** (without causal analysis):
```python
# You see: function A calls function B
# You wonder: "If I change A, will B break?"
# You must: Manually trace through code, run tests, hope for the best
```

**Causal approach** (with lift-sys):
```python
# You ask: "What's the impact of changing A?"
impact = ir.causal_impact('function_a')
# You get: {'function_b': 0.85, 'function_c': 0.32}
# Interpretation: B is highly affected (85%), C is slightly affected (32%)
```

**Key benefits**:
- **Impact analysis**: Understand downstream effects before making changes
- **Root cause analysis**: Trace bugs back to their source
- **Refactoring validation**: Verify that refactoring preserves behavior
- **Test prioritization**: Focus tests on causally important code paths

### How It Works

lift-sys uses **DoWhy** (Microsoft Research's causal inference library) to:

1. **Build causal graphs** from your code's AST and call graph
2. **Fit structural causal models (SCMs)** using static analysis or execution traces
3. **Answer interventional queries** like "what if we changed X to value Y?"

The result is a **mathematically rigorous** understanding of your codebase's behavior.

---

## 2. Quick Start

### Installation

Causal analysis requires DoWhy, which runs in a separate Python 3.11 environment:

```bash
# Setup is automatic - DoWhy venv is pre-configured
# Verify it exists:
ls -la .venv-dowhy/

# If needed, recreate:
uv venv --python 3.11 .venv-dowhy
source .venv-dowhy/bin/activate
uv pip install dowhy pandas numpy scikit-learn
deactivate
```

### 5-Minute Example

**Scenario**: You have a Python module and want to understand what code depends on a specific function.

```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

# 1. Initialize lifter
config = LifterConfig(
    run_codeql=False,  # Disable for faster analysis
    run_daikon=False,
    run_stack_graphs=False
)
lifter = SpecificationLifter(config)
lifter.load_repository("/path/to/your/repo")

# 2. Lift code with causal analysis enabled
ir = lifter.lift(
    "src/main.py",
    include_causal=True,    # Enable causal analysis
    static_only=True        # No execution traces needed
)

# 3. Query: What code is affected by validate_input()?
impact = ir.causal_impact("validate_input")

# 4. Inspect results
print("Impact Analysis Results:")
for node, effect_size in impact.affected_nodes.items():
    confidence = impact.confidence_intervals[node]
    print(f"  {node}: {effect_size:.2f} (95% CI: {confidence})")

# Output:
# Impact Analysis Results:
#   process_data: 0.85 (95% CI: (0.78, 0.91))
#   generate_output: 0.72 (95% CI: (0.65, 0.79))
#   log_results: 0.05 (95% CI: (0.01, 0.12))
```

**Interpretation**:
- `process_data` is highly affected (85% effect size) - refactor carefully!
- `generate_output` is moderately affected (72%)
- `log_results` is barely affected (5%) - probably just logging

### Next Steps

- Read [Core Concepts](#3-core-concepts) to understand causal graphs and SCMs
- Explore [Use Cases](#4-use-cases) for practical scenarios
- Check [API Reference](API_REFERENCE.md) for complete API documentation
- Review [Examples](EXAMPLES.md) for runnable code samples

---

## 3. Core Concepts

### Causal Graphs

A **causal graph** (or causal DAG - Directed Acyclic Graph) represents cause-and-effect relationships in your code.

**Nodes** represent:
- Functions
- Variables
- Return values
- Side effects (I/O, state changes)

**Edges** represent causal relationships:
- **Data flow**: A produces data used by B
- **Control flow**: A controls whether B executes
- **Function calls**: A calls B

**Example**:
```python
def validate_input(x):
    if x < 0:
        raise ValueError("x must be positive")
    return x

def process_data(x):
    validated = validate_input(x)  # validate_input → process_data
    return validated * 2

def generate_output(x):
    result = process_data(x)       # process_data → generate_output
    return f"Result: {result}"
```

**Causal graph**:
```
validate_input → process_data → generate_output
```

**Non-causal edges are pruned**:
- Logging calls (no effect on computation)
- Pure I/O (unless it affects computation)
- Import statements

### Structural Causal Models (SCMs)

An **SCM** extends a causal graph with **causal mechanisms** - mathematical functions that describe *how* causes produce effects.

**Example**:
```python
# Code:
def double(x):
    return x * 2

# Causal mechanism:
double_result = f(x) = 2 * x
```

**Static vs Dynamic SCMs**:

| Mode | Input | Mechanism | Accuracy |
|------|-------|-----------|----------|
| **Static** | Code only | Linear approximation from AST | Lower (R² ≈ 0.5-0.7) |
| **Dynamic** | Code + execution traces | Fitted from real data | Higher (R² ≈ 0.7-0.9) |

**When to use each**:
- **Static**: Quick analysis, no test suite available
- **Dynamic**: High accuracy needed, traces available

### Interventions

An **intervention** (written `do(X=x)`) is a hypothetical change to a variable, different from simply observing `X=x`.

**Key difference**:
- **Observation**: "When X happens to be x, what is Y?"
- **Intervention**: "If I force X to be x, what happens to Y?"

**Example**:
```python
# Observation (passive):
# "When validate_input returns True, process_data usually succeeds"
# This could be correlation, not causation!

# Intervention (active):
# "If I make validate_input always return True, process_data will..."
# This is causation - we're forcing a change
```

**In lift-sys**:
```python
# Ask: "What if validate_input always returned True?"
impact = ir.causal_intervention({'validate_input': True})

# Get: Predicted distribution of downstream outputs
print(impact.affected_nodes)
```

### Effect Sizes and Confidence Intervals

**Effect size** measures the magnitude of causal impact:
- 0.0 = no effect
- 0.2 = small effect
- 0.5 = medium effect
- 0.8+ = large effect

Computed as **Cohen's d**: `(E[Y | do(X=x)] - E[Y]) / std(Y)`

**Confidence intervals** (95% CI) indicate uncertainty:
- Narrow interval (e.g., `(0.82, 0.88)`) = high confidence
- Wide interval (e.g., `(0.10, 0.90)`) = high uncertainty

**Example**:
```python
impact = ir.causal_impact("validate_input")
print(impact.affected_nodes['process_data'])  # 0.85
print(impact.confidence_intervals['process_data'])  # (0.78, 0.91)

# Interpretation: We're 95% confident the effect is between 0.78 and 0.91
```

---

## 4. Use Cases

### Use Case 1: Impact Analysis

**Problem**: You need to change a function but don't know what will break.

**Solution**: Query causal impact before making changes.

```python
# Before refactoring validate_input():
lifter = SpecificationLifter(config)
lifter.load_repository(".")
ir = lifter.lift("src/validators.py", include_causal=True)

# Ask: What depends on this function?
impact = ir.causal_impact("validate_input")

# Inspect high-impact dependencies (effect > 0.5)
critical = {
    node: effect
    for node, effect in impact.affected_nodes.items()
    if effect > 0.5
}

print(f"CRITICAL DEPENDENCIES: {critical}")
# Output: {'process_data': 0.85, 'generate_output': 0.72}

# Action: Write extra tests for process_data and generate_output
```

**Benefits**:
- Identify critical dependencies before changes
- Prioritize testing efforts
- Reduce regression risk

### Use Case 2: Root Cause Analysis

**Problem**: A bug appeared, and you need to find the root cause.

**Solution**: Trace backward through causal graph.

```python
# Bug: generate_output() returns incorrect values

# Build causal graph
ir = lifter.lift("src/main.py", include_causal=True)

# Get causal graph
scm = ir.get_causal_scm()
causal_graph = scm.graph

# Find all nodes that affect generate_output
import networkx as nx
ancestors = nx.ancestors(causal_graph, "generate_output")
print(f"Potential root causes: {ancestors}")

# Output: {'validate_input', 'process_data', 'config_loader'}

# Inspect each with intervention queries
for node in ancestors:
    impact = ir.causal_impact(node)
    if impact.affected_nodes.get('generate_output', 0) > 0.5:
        print(f"HIGH IMPACT: {node}")

# Output: HIGH IMPACT: process_data
# Conclusion: Bug is likely in process_data()
```

**Benefits**:
- Systematic bug investigation
- Focus on high-impact code
- Avoid wild goose chases

### Use Case 3: Refactoring Validation

**Problem**: You refactored code and want to verify behavior is preserved.

**Solution**: Compare causal models before and after.

```python
# Before refactoring
ir_before = lifter.lift("src/main.py", include_causal=True)
scm_before = ir_before.get_causal_scm()

# ... perform refactoring ...

# After refactoring
ir_after = lifter.lift("src/main.py", include_causal=True)
scm_after = ir_after.get_causal_scm()

# Compare causal graphs
graph_before = scm_before.graph
graph_after = scm_after.graph

# Check: Same nodes?
nodes_before = set(graph_before.nodes())
nodes_after = set(graph_after.nodes())
print(f"Removed nodes: {nodes_before - nodes_after}")
print(f"Added nodes: {nodes_after - nodes_before}")

# Check: Same edges?
edges_before = set(graph_before.edges())
edges_after = set(graph_after.edges())
print(f"Removed edges: {edges_before - edges_after}")
print(f"Added edges: {edges_after - edges_before}")

# Validate: Run intervention queries
test_interventions = [
    {'validate_input': True},
    {'validate_input': False},
]

for intervention in test_interventions:
    impact_before = InterventionEngine().estimate_impact(scm_before, intervention)
    impact_after = InterventionEngine().estimate_impact(scm_after, intervention)

    # Compare effect sizes
    for node in nodes_before & nodes_after:
        diff = abs(
            impact_before.affected_nodes.get(node, 0) -
            impact_after.affected_nodes.get(node, 0)
        )
        if diff > 0.1:  # Threshold for significant change
            print(f"WARNING: {node} behavior changed by {diff:.2f}")
```

**Benefits**:
- Verify refactoring preserves behavior
- Catch unintended side effects
- Increase refactoring confidence

### Use Case 4: Test Prioritization

**Problem**: You have limited testing resources and need to prioritize.

**Solution**: Focus tests on causally important code.

```python
# Analyze all files in project
lifter = SpecificationLifter(config)
lifter.load_repository(".")
files = lifter.discover_python_files()

# Build global causal graph
all_irs = []
for file in files[:50]:  # Limit for performance
    ir = lifter.lift(str(file), include_causal=True)
    all_irs.append(ir)

# Compute causal importance for each function
importance_scores = {}

for ir in all_irs:
    scm = ir.get_causal_scm()
    graph = scm.graph

    for node in graph.nodes():
        # Importance = number of downstream nodes
        descendants = nx.descendants(graph, node)
        importance_scores[node] = len(descendants)

# Prioritize testing by importance
sorted_functions = sorted(
    importance_scores.items(),
    key=lambda x: x[1],
    reverse=True
)

print("TOP 10 MOST IMPORTANT FUNCTIONS TO TEST:")
for func, score in sorted_functions[:10]:
    print(f"  {func}: {score} downstream dependencies")

# Output:
# TOP 10 MOST IMPORTANT FUNCTIONS TO TEST:
#   validate_input: 25 downstream dependencies
#   load_config: 18 downstream dependencies
#   process_data: 12 downstream dependencies
#   ...
```

**Benefits**:
- Maximize test coverage impact
- Focus on high-leverage code
- Reduce testing time

---

## 5. Configuration

### Lifter Configuration

Control causal analysis via `LifterConfig` and `lift()` parameters:

```python
from lift_sys.reverse_mode import LifterConfig

# Basic config (causal analysis disabled by default)
config = LifterConfig()

# Optimized for speed (disable other analyzers)
config = LifterConfig(
    run_codeql=False,
    run_daikon=False,
    run_stack_graphs=False
)

# Full analysis (all analyzers enabled)
config = LifterConfig(
    run_codeql=True,
    run_daikon=True,
    run_stack_graphs=True,
    codeql_queries=["security/default"],
    daikon_entrypoint="main"
)
```

### Causal Analysis Options

```python
# Static-only mode (no execution traces)
ir = lifter.lift(
    "main.py",
    include_causal=True,
    static_only=True
)

# Dynamic mode (with execution traces)
import pandas as pd

# Collect traces by running code
traces = pd.DataFrame({
    'validate_input': [True, False, True, ...],
    'process_data': [42, None, 84, ...],
    'generate_output': ['Result: 42', None, 'Result: 84', ...]
})

ir = lifter.lift(
    "main.py",
    include_causal=True,
    traces=traces,
    static_only=False
)
```

### Performance Tuning

**For large codebases**:

```python
# Limit file count
config = LifterConfig(
    max_files=100,  # Only analyze first 100 files
    max_file_size_mb=5.0,  # Skip files larger than 5MB
    timeout_per_file_seconds=30.0,  # Skip slow files
    max_total_time_seconds=600.0  # 10-minute total limit
)

# Analyze subset
irs = lifter.lift_all(max_files=50)
```

**For high accuracy**:

```python
# Increase sample size for interventions
impact = ir.causal_impact(
    "validate_input",
    num_samples=10000  # Default: 1000
)
```

---

## 6. Best Practices

### When to Use Static vs Dynamic Mode

**Use Static Mode When**:
- ✅ Quick analysis needed (< 5 seconds)
- ✅ No test suite or traces available
- ✅ Code is simple (mostly linear data flow)
- ✅ Approximate results acceptable (R² ≈ 0.5-0.7)

**Use Dynamic Mode When**:
- ✅ High accuracy required (R² > 0.7)
- ✅ Execution traces available
- ✅ Code is complex (branching, state, I/O)
- ✅ Time budget allows (10-30 seconds)

**Example Decision Tree**:
```
Do you have execution traces?
├─ NO → Use static mode
└─ YES → Do you need high accuracy?
    ├─ NO → Use static mode (faster)
    └─ YES → Use dynamic mode
```

### Caching Results

Causal analysis can be expensive - cache results when possible:

```python
import pickle

# Compute once
ir = lifter.lift("main.py", include_causal=True)

# Save to disk
with open("main_causal.pkl", "wb") as f:
    pickle.dump(ir, f)

# Load later
with open("main_causal.pkl", "rb") as f:
    ir_cached = pickle.load(f)

# Query from cache (fast!)
impact = ir_cached.causal_impact("validate_input")
```

**Invalidate cache when**:
- Code changes
- Traces change
- Configuration changes

### Interpreting Effect Sizes

**Guidelines**:

| Effect Size | Interpretation | Action |
|-------------|----------------|--------|
| 0.0 - 0.2 | Negligible | Safe to ignore |
| 0.2 - 0.5 | Small | Minor testing needed |
| 0.5 - 0.8 | Medium | Significant testing needed |
| 0.8+ | Large | Critical - extensive testing |

**Example**:
```python
impact = ir.causal_impact("validate_input")

for node, effect in impact.affected_nodes.items():
    if effect >= 0.8:
        print(f"CRITICAL: {node}")
    elif effect >= 0.5:
        print(f"WARNING: {node}")
    elif effect >= 0.2:
        print(f"INFO: {node}")
    # Ignore < 0.2
```

### Handling Uncertainty

Always check confidence intervals:

```python
impact = ir.causal_impact("validate_input")

for node, effect in impact.affected_nodes.items():
    ci_low, ci_high = impact.confidence_intervals[node]
    ci_width = ci_high - ci_low

    if ci_width > 0.3:  # Wide interval = high uncertainty
        print(f"WARNING: Uncertain about {node} (CI width: {ci_width:.2f})")
        print(f"  Recommendation: Collect more traces or use dynamic mode")
    else:
        print(f"Confident about {node} (effect: {effect:.2f} ± {ci_width/2:.2f})")
```

---

## 7. Troubleshooting

### Common Issues

#### Issue 1: "DoWhy import failed"

**Symptoms**:
```
ModuleNotFoundError: No module named 'dowhy'
```

**Cause**: DoWhy venv not set up or activated incorrectly

**Solution**:
```bash
# Verify DoWhy venv exists
ls -la .venv-dowhy/

# Recreate if needed
uv venv --python 3.11 .venv-dowhy
source .venv-dowhy/bin/activate
uv pip install dowhy pandas numpy scikit-learn
deactivate

# Verify installation
.venv-dowhy/bin/python -c "import dowhy; print(dowhy.__version__)"
```

#### Issue 2: "Causal graph is cyclic"

**Symptoms**:
```
ValueError: Causal graph must be acyclic (DAG)
```

**Cause**: Code has circular dependencies (A → B → A)

**Solution**:
```python
# Option 1: Refactor code to remove cycles

# Option 2: Break cycle at specific edge
from lift_sys.causal import CausalGraphBuilder

builder = CausalGraphBuilder()
graph = builder.build(ast, call_graph)

# Manually remove problematic edge
if graph.has_edge('func_a', 'func_b'):
    graph.remove_edge('func_a', 'func_b')
    print("Broke cycle: func_a → func_b")
```

#### Issue 3: "Low SCM R² (< 0.7)"

**Symptoms**:
```
ValidationError: SCM R² = 0.45 is below threshold 0.7
```

**Cause**: Static approximation or insufficient traces

**Solutions**:
```python
# Solution 1: Use dynamic mode with more traces
traces = collect_more_execution_traces()  # Get 100+ samples
ir = lifter.lift("main.py", include_causal=True, traces=traces)

# Solution 2: Lower threshold if approximate results acceptable
# (Modify LifterConfig - requires code change)

# Solution 3: Try nonlinear mechanisms
# (Automatically attempted if linear R² < 0.7)
```

#### Issue 4: "Intervention query is slow"

**Symptoms**: Query takes > 1 second

**Causes & Solutions**:

| Cause | Solution |
|-------|----------|
| Large graph (100+ nodes) | Reduce num_samples: `impact = ir.causal_impact(node, num_samples=500)` |
| Complex mechanisms | Use static mode instead of dynamic |
| First query (cold start) | Expected (~100ms overhead), subsequent queries faster |
| Inefficient sampling | Update DoWhy version: `uv pip install --upgrade dowhy` |

#### Issue 5: "Empty affected_nodes dict"

**Symptoms**:
```python
impact = ir.causal_impact("func_x")
print(impact.affected_nodes)  # {}
```

**Cause**: Function has no downstream dependencies

**Solution**:
```python
# Check causal graph
scm = ir.get_causal_scm()
graph = scm.graph

# Find descendants
import networkx as nx
descendants = nx.descendants(graph, "func_x")
print(f"Descendants: {descendants}")

# If empty, function is a leaf node (no downstream impact)
if not descendants:
    print("func_x is a leaf node - it doesn't affect other code")
```

### Debugging Tips

**1. Visualize causal graph**:
```python
import networkx as nx
import matplotlib.pyplot as plt

scm = ir.get_causal_scm()
graph = scm.graph

# Draw graph
pos = nx.spring_layout(graph)
nx.draw(graph, pos, with_labels=True, node_color='lightblue',
        node_size=500, font_size=8, arrows=True)
plt.savefig("causal_graph.png")
print("Graph saved to causal_graph.png")
```

**2. Inspect causal metadata**:
```python
if ir.causal_metadata:
    print(f"Fitted at: {ir.causal_metadata.fitted_at}")
    print(f"Trace count: {ir.causal_metadata.trace_count}")
    print(f"Validation R²: {ir.causal_metadata.validation_r2}")
    print(f"Static only: {ir.causal_metadata.static_only}")
    print(f"Mechanism types: {ir.causal_metadata.mechanism_types}")
```

**3. Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now causal analysis will log detailed information
ir = lifter.lift("main.py", include_causal=True)
```

---

## 8. Advanced Topics

### Multi-File Analysis

Analyze entire projects by aggregating causal graphs:

```python
lifter = SpecificationLifter(config)
lifter.load_repository(".")
files = lifter.discover_python_files()

# Analyze all files
all_irs = []
for file in files[:100]:  # Limit for performance
    ir = lifter.lift(str(file), include_causal=True)
    all_irs.append(ir)

# Merge causal graphs
import networkx as nx

merged_graph = nx.DiGraph()
for ir in all_irs:
    scm = ir.get_causal_scm()
    if scm:
        merged_graph = nx.compose(merged_graph, scm.graph)

print(f"Merged graph: {merged_graph.number_of_nodes()} nodes, "
      f"{merged_graph.number_of_edges()} edges")

# Query on merged graph
# (Requires creating new SCM from merged graph)
```

### Counterfactual Queries

Answer "what if history was different?" questions:

```python
# Requires execution traces
traces = pd.DataFrame({
    'validate_input': [True, False, True, True],
    'process_data': [42, None, 84, 126],
    'output': ['Success', 'Error', 'Success', 'Success']
})

ir = lifter.lift("main.py", include_causal=True, traces=traces)
scm = ir.get_causal_scm()

# Counterfactual: In run #2 (which failed), what if validate_input was True?
from dowhy import gcm

counterfactual = gcm.counterfactual_samples(
    scm,
    queries={'validate_input': lambda x: True},  # Force True
    observed_data=traces.iloc[1:2]  # Row 2 (failed run)
)

print(f"Actual output: {traces.iloc[1]['output']}")  # 'Error'
print(f"Counterfactual output: {counterfactual['output'][0]}")  # 'Success'
print("Conclusion: Failure was caused by validate_input=False")
```

### Custom Causal Mechanisms

Override default mechanisms for specific nodes:

```python
from dowhy import gcm

# Build graph
builder = CausalGraphBuilder()
graph = builder.build(ast, call_graph)

# Create SCM
scm = gcm.StructuralCausalModel(graph)

# Custom mechanism for specific node
def custom_mechanism(x):
    # Your domain knowledge here
    return 2 * x + 5

scm.set_causal_mechanism('process_data',
                         gcm.AdditiveNoiseModel(custom_mechanism))

# Fit remaining mechanisms
gcm.auto.assign_causal_mechanisms(scm, exclude=['process_data'])
gcm.fit(scm, traces)

# Now interventions use your custom mechanism
```

### Sensitivity Analysis

Validate robustness of causal conclusions:

```python
# Run intervention with different sample sizes
sample_sizes = [100, 500, 1000, 5000]
results = []

for n in sample_sizes:
    impact = ir.causal_impact("validate_input", num_samples=n)
    results.append({
        'sample_size': n,
        'effect': impact.affected_nodes.get('process_data', 0),
        'ci': impact.confidence_intervals.get('process_data', (0, 0))
    })

# Check stability
import pandas as pd
df = pd.DataFrame(results)
print(df)

# If effect size varies wildly, conclusion is not robust
effect_std = df['effect'].std()
if effect_std > 0.1:
    print(f"WARNING: Effect size varies significantly (std={effect_std:.2f})")
    print("Recommendation: Collect more traces or use domain knowledge")
else:
    print(f"Robust conclusion (std={effect_std:.2f})")
```

### Performance Optimization

For production use, optimize causal queries:

```python
# 1. Precompute common queries
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_impact(node_name, num_samples=1000):
    return ir.causal_impact(node_name, num_samples=num_samples)

# 2. Use batch interventions
interventions = [
    {'validate_input': True},
    {'validate_input': False},
    {'process_data': 42}
]

# Run in parallel (if DoWhy supports batching)
impacts = [ir.causal_impact(node) for node in ['func_a', 'func_b', 'func_c']]

# 3. Cache IR objects
import diskcache as dc

cache = dc.Cache('.causal_cache')

@cache.memoize(expire=3600)  # 1-hour TTL
def get_causal_ir(file_path):
    return lifter.lift(file_path, include_causal=True)
```

---

## Next Steps

1. **Try it out**: Run the [Quick Start](#2-quick-start) example on your codebase
2. **Deep dive**: Read [API Reference](API_REFERENCE.md) for complete API details
3. **Learn by example**: Study [Examples](EXAMPLES.md) for common patterns
4. **Ask questions**: Open issues on GitHub or join our community

---

**Related Documentation**:
- [API Reference](API_REFERENCE.md) - Complete API specification
- [Examples](EXAMPLES.md) - Runnable code examples
- [Reverse Mode Guide](../REVERSE_MODE.md) - General reverse mode documentation
- [DoWhy Integration Spec](../planning/DOWHY_INTEGRATION_SPEC.md) - Technical design
