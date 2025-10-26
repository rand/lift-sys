# Causal Analysis Documentation

**Date**: 2025-10-26
**Status**: Complete documentation suite for DoWhy integration
**Version**: 0.1.0

---

## Overview

This directory contains comprehensive documentation for **causal analysis** features in lift-sys reverse mode.

**What is causal analysis?**
- Understanding **cause-and-effect relationships** in code
- Answering **"what if"** questions about code changes
- **Impact analysis** before refactoring
- **Root cause analysis** for bugs

**Powered by**: [DoWhy](https://github.com/py-why/dowhy) (Microsoft Research's causal inference library)

---

## Documentation Structure

### 1. [Causal Analysis Guide](CAUSAL_ANALYSIS_GUIDE.md) 📘

**Primary user guide** - Start here!

**Contents**:
- ✅ Introduction: What is causal analysis? Why use it?
- ✅ Quick Start: 5-minute working example
- ✅ Core Concepts: Causal graphs, SCMs, interventions
- ✅ Use Cases: Impact analysis, refactoring validation, test prioritization
- ✅ Configuration: Static vs dynamic mode
- ✅ Best Practices: When to use what
- ✅ Troubleshooting: Common issues and solutions
- ✅ Advanced Topics: Multi-file analysis, counterfactuals, custom mechanisms

**Target audience**: All users (beginners to advanced)

**Read this if**: You're new to causal analysis or need conceptual understanding

---

### 2. [API Reference](API_REFERENCE.md) 📚

**Complete API specification** - Reference documentation

**Contents**:
- ✅ `SpecificationLifter.lift()` - Enable causal analysis
- ✅ `IR.causal_impact()` - Query intervention effects
- ✅ `IR.causal_intervention()` - Perform "what if" queries
- ✅ `IR.get_causal_scm()` - Access structural causal model
- ✅ `IR.causal_graph` - Access causal DAG
- ✅ `IR.causal_paths()` - Find causal paths
- ✅ `CausalGraphBuilder` - Build graphs from AST
- ✅ `SCMFitter` - Fit causal models
- ✅ `InterventionEngine` - Process interventions
- ✅ Data models: `ImpactEstimate`, `CausalMetadata`
- ✅ Error types: `GraphBuildError`, `FittingError`, etc.
- ✅ Type hints and signatures

**Target audience**: Developers integrating causal analysis

**Read this if**: You need precise API details and function signatures

---

### 3. [Examples](EXAMPLES.md) 💻

**Runnable code examples** - Practical recipes

**Contents**:
- ✅ Basic examples (impact analysis, interventions, visualization)
- ✅ Impact analysis examples (find critical dependencies, compare functions)
- ✅ Multi-file analysis (entire projects, cross-file dependencies)
- ✅ Static vs dynamic mode (comparison, trace collection)
- ✅ Error handling (missing models, low R², invalid queries)
- ✅ Performance optimization (caching, batch analysis)
- ✅ Advanced examples (custom mechanisms, counterfactuals)
- ✅ Real-world scenarios (refactoring assessment, root cause analysis, test prioritization)

**Target audience**: Developers learning by example

**Read this if**: You prefer copy-paste code over reading docs

---

## Quick Navigation

**I want to...**

| Goal | Document | Section |
|------|----------|---------|
| Understand what causal analysis is | [Guide](CAUSAL_ANALYSIS_GUIDE.md) | [Introduction](CAUSAL_ANALYSIS_GUIDE.md#1-introduction) |
| Get started in 5 minutes | [Guide](CAUSAL_ANALYSIS_GUIDE.md) | [Quick Start](CAUSAL_ANALYSIS_GUIDE.md#2-quick-start) |
| See working code examples | [Examples](EXAMPLES.md) | All sections |
| Find API details for `lift()` | [API Reference](API_REFERENCE.md) | [SpecificationLifter](API_REFERENCE.md#specificationlifter-api) |
| Query causal impact | [API Reference](API_REFERENCE.md) | [IR.causal_impact()](API_REFERENCE.md#ircausal_impact) |
| Compare static vs dynamic mode | [Guide](CAUSAL_ANALYSIS_GUIDE.md) | [Best Practices](CAUSAL_ANALYSIS_GUIDE.md#6-best-practices) |
| Fix "DoWhy import failed" error | [Guide](CAUSAL_ANALYSIS_GUIDE.md) | [Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#7-troubleshooting) |
| Analyze entire project | [Examples](EXAMPLES.md) | [Example 6](EXAMPLES.md#example-6-analyze-entire-project) |
| Assess refactoring risk | [Examples](EXAMPLES.md) | [Example 16](EXAMPLES.md#example-16-pre-refactoring-impact-assessment) |
| Find root cause of bug | [Examples](EXAMPLES.md) | [Example 17](EXAMPLES.md#example-17-root-cause-analysis-for-production-bug) |

---

## User Stories

### Story 1: "I want to know what code breaks if I change function X"

**Use case**: Impact analysis before refactoring

**Solution**:
```python
from lift_sys.reverse_mode import SpecificationLifter, LifterConfig

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/main.py", include_causal=True)

# Query impact
impact = ir.causal_impact("function_x")

# Find critical dependencies
critical = {
    node: effect
    for node, effect in impact.affected_nodes.items()
    if effect > 0.5
}

print(f"Critical dependencies: {critical}")
```

**Learn more**:
- [Guide: Use Case 1 - Impact Analysis](CAUSAL_ANALYSIS_GUIDE.md#use-case-1-impact-analysis)
- [Examples: Example 4 - Find Critical Dependencies](EXAMPLES.md#example-4-find-critical-dependencies)
- [Examples: Example 16 - Pre-Refactoring Assessment](EXAMPLES.md#example-16-pre-refactoring-impact-assessment)

---

### Story 2: "I want to understand why my function returns unexpected values"

**Use case**: Root cause analysis for debugging

**Solution**:
```python
import networkx as nx

lifter = SpecificationLifter(LifterConfig())
lifter.load_repository(".")
ir = lifter.lift("src/buggy.py", include_causal=True)

# Get causal graph
scm = ir.get_causal_scm()
graph = scm.graph

# Find all potential root causes
ancestors = nx.ancestors(graph, "buggy_function")

# Test each with intervention
for ancestor in ancestors:
    impact = ir.causal_impact(ancestor)
    effect = impact.affected_nodes.get('buggy_function', 0)

    if effect > 0.5:
        print(f"HIGH IMPACT: {ancestor} (effect: {effect:.2f})")
```

**Learn more**:
- [Guide: Use Case 2 - Root Cause Analysis](CAUSAL_ANALYSIS_GUIDE.md#use-case-2-root-cause-analysis)
- [Examples: Example 17 - Root Cause Analysis](EXAMPLES.md#example-17-root-cause-analysis-for-production-bug)

---

### Story 3: "I want to validate my refactoring preserves behavior"

**Use case**: Refactoring validation

**Solution**:
```python
# Before refactoring
ir_before = lifter.lift("src/main.py", include_causal=True)
scm_before = ir_before.get_causal_scm()

# ... perform refactoring ...

# After refactoring
ir_after = lifter.lift("src/main.py", include_causal=True)
scm_after = ir_after.get_causal_scm()

# Compare intervention results
test_interventions = [
    {'function_a': True},
    {'function_b': 100},
]

for intervention in test_interventions:
    impact_before = InterventionEngine().estimate_impact(scm_before, intervention)
    impact_after = InterventionEngine().estimate_impact(scm_after, intervention)

    # Check for significant differences
    for node in impact_before.affected_nodes.keys():
        diff = abs(
            impact_before.affected_nodes[node] -
            impact_after.affected_nodes.get(node, 0)
        )
        if diff > 0.1:
            print(f"WARNING: {node} behavior changed!")
```

**Learn more**:
- [Guide: Use Case 3 - Refactoring Validation](CAUSAL_ANALYSIS_GUIDE.md#use-case-3-refactoring-validation)
- [Examples: Example 8 - Compare Static and Dynamic](EXAMPLES.md#example-8-compare-static-and-dynamic-analysis)

---

### Story 4: "I want to prioritize tests by causal importance"

**Use case**: Test prioritization

**Solution**:
```python
import networkx as nx

# Analyze entire project
files = lifter.discover_python_files()
all_irs = [lifter.lift(str(f), include_causal=True) for f in files[:50]]

# Compute importance scores
importance = {}
for ir in all_irs:
    graph = ir.causal_graph
    if graph:
        for node in graph.nodes():
            # Importance = number of downstream nodes
            descendants = nx.descendants(graph, node)
            importance[node] = len(descendants)

# Sort by importance
sorted_funcs = sorted(importance.items(), key=lambda x: x[1], reverse=True)

print("TOP 10 FUNCTIONS TO TEST:")
for func, score in sorted_funcs[:10]:
    print(f"  {func}: {score} downstream dependencies")
```

**Learn more**:
- [Guide: Use Case 4 - Test Prioritization](CAUSAL_ANALYSIS_GUIDE.md#use-case-4-test-prioritization)
- [Examples: Example 18 - Test Prioritization](EXAMPLES.md#example-18-test-prioritization)

---

## Key Concepts

### Causal Graph (DAG)

A **directed acyclic graph** representing cause-and-effect relationships.

- **Nodes**: Functions, variables, return values
- **Edges**: Data flow, control flow, function calls
- **Property**: Acyclic (no circular dependencies)

**Example**:
```
validate_input → process_data → generate_output
```

**Learn more**: [Guide: Core Concepts - Causal Graphs](CAUSAL_ANALYSIS_GUIDE.md#causal-graphs)

---

### Structural Causal Model (SCM)

A **causal graph + mechanisms** that describe how causes produce effects.

- **Static mode**: Linear approximation from code (fast, R² ≈ 0.5-0.7)
- **Dynamic mode**: Fitted from execution traces (accurate, R² ≈ 0.7-0.9)

**Learn more**: [Guide: Core Concepts - SCMs](CAUSAL_ANALYSIS_GUIDE.md#structural-causal-models-scms)

---

### Interventions

**Interventional queries** (`do(X=x)`) answer "what if" questions.

- **Observation**: "When X happens to be x, what is Y?"
- **Intervention**: "If I force X to be x, what happens to Y?"

**Key difference**: Causation vs correlation

**Learn more**: [Guide: Core Concepts - Interventions](CAUSAL_ANALYSIS_GUIDE.md#interventions)

---

### Effect Sizes

**Magnitude of causal impact** (Cohen's d):
- 0.0 - 0.2: Negligible
- 0.2 - 0.5: Small
- 0.5 - 0.8: Medium
- 0.8+: Large

**Confidence intervals**: 95% bootstrap intervals for uncertainty

**Learn more**: [Guide: Core Concepts - Effect Sizes](CAUSAL_ANALYSIS_GUIDE.md#effect-sizes-and-confidence-intervals)

---

## Common Workflows

### Workflow 1: Quick Impact Analysis

**Goal**: Fast, approximate impact analysis

**Steps**:
1. Enable causal analysis with `static_only=True`
2. Query impact with `ir.causal_impact(node)`
3. Interpret effect sizes

**Time**: ~5 seconds per file

**Accuracy**: Moderate (R² ≈ 0.5-0.7)

**Example**: [Examples: Example 1](EXAMPLES.md#example-1-simple-impact-analysis)

---

### Workflow 2: High-Accuracy Analysis

**Goal**: Accurate causal analysis with traces

**Steps**:
1. Collect execution traces (run code, record variables)
2. Convert traces to `pd.DataFrame`
3. Enable causal analysis with `traces=...`
4. Query with high sample count

**Time**: ~30 seconds per file

**Accuracy**: High (R² ≈ 0.7-0.9)

**Example**: [Examples: Example 9](EXAMPLES.md#example-9-collect-execution-traces)

---

### Workflow 3: Multi-File Analysis

**Goal**: Analyze entire project

**Steps**:
1. Discover all Python files
2. Analyze each with `include_causal=True`
3. Merge causal graphs
4. Query on merged graph

**Time**: ~5 minutes for 100 files (static mode)

**Example**: [Examples: Example 6](EXAMPLES.md#example-6-analyze-entire-project)

---

## Configuration Options

### Static vs Dynamic Mode

| Mode | Input | Speed | Accuracy | Use When |
|------|-------|-------|----------|----------|
| **Static** | Code only | Fast (~5s) | Moderate (R² ≈ 0.5-0.7) | Quick analysis, no traces |
| **Dynamic** | Code + traces | Slow (~30s) | High (R² ≈ 0.7-0.9) | High accuracy needed |

**Learn more**: [Guide: Best Practices - Static vs Dynamic](CAUSAL_ANALYSIS_GUIDE.md#when-to-use-static-vs-dynamic-mode)

---

### Sample Size

| `num_samples` | Query Time | Accuracy | Use When |
|---------------|------------|----------|----------|
| 100 | ~10ms | Low | Interactive exploration |
| 1000 (default) | ~50ms | Good | Standard queries |
| 10000 | ~500ms | High | Critical decisions |

**Learn more**: [API Reference: IR.causal_impact()](API_REFERENCE.md#ircausal_impact)

---

## Performance Guidelines

| Operation | Latency | Optimization Tips |
|-----------|---------|-------------------|
| `lift(..., static_only=True)` | ~5s | Default for speed |
| `lift(..., traces=...)` | ~30s | Use only when needed |
| `ir.causal_impact(node)` | ~50ms | Cache IR objects |
| `ir.get_causal_scm()` (first call) | ~10ms | Lazy deserialization |
| Multi-file (50 files, static) | ~5 min | Parallelize with ThreadPoolExecutor |

**Learn more**: [API Reference: Performance Guidelines](API_REFERENCE.md#performance-guidelines)

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "DoWhy import failed" | DoWhy venv not set up | [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#issue-1-dowhy-import-failed) |
| "Causal graph is cyclic" | Circular dependencies | [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#issue-2-causal-graph-is-cyclic) |
| "Low SCM R² (< 0.7)" | Insufficient traces | [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#issue-3-low-scm-r2--07) |
| "Intervention query is slow" | Large graph | [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#issue-4-intervention-query-is-slow) |
| "Empty affected_nodes" | Leaf node (no descendants) | [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#issue-5-empty-affected_nodes-dict) |

**Full troubleshooting guide**: [Guide: Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#7-troubleshooting)

---

## Integration with lift-sys

### Reverse Mode Integration

Causal analysis is **integrated into reverse mode** as an optional feature:

```python
# Without causal analysis (default)
ir = lifter.lift("main.py")
# ir.causal_model is None

# With causal analysis
ir = lifter.lift("main.py", include_causal=True)
# ir.causal_model contains fitted SCM
```

**Backward compatible**: Existing code works without changes

**Learn more**: [API Reference: SpecificationLifter.lift()](API_REFERENCE.md#specificationlifterlift)

---

### IR Schema Extensions

New fields in `IntermediateRepresentation`:

```python
class IntermediateRepresentation(BaseModel):
    # Existing fields (unchanged)
    intent: str
    signature: Signature
    effects: tuple[Effect, ...]
    assertions: tuple[Assertion, ...]

    # NEW: Causal analysis (optional)
    causal_model: Optional[dict] = None  # Serialized SCM
    causal_metadata: Optional[CausalMetadata] = None  # Metadata

    # NEW: Convenience methods
    def causal_impact(self, node: str) -> Optional[ImpactEstimate]: ...
    def causal_intervention(self, interventions: dict) -> Optional[ImpactEstimate]: ...
    def get_causal_scm(self) -> Optional[gcm.StructuralCausalModel]: ...

    @property
    def causal_graph(self) -> Optional[nx.DiGraph]: ...
```

**Learn more**: [API Reference: Data Models](API_REFERENCE.md#data-models)

---

## Related Documentation

**Project documentation**:
- [REVERSE_MODE.md](../REVERSE_MODE.md) - General reverse mode guide
- [DoWhy Integration Spec](../planning/DOWHY_INTEGRATION_SPEC.md) - Technical design
- [DoWhy Technical Review](../research/DOWHY_TECHNICAL_REVIEW.md) - DoWhy assessment

**External resources**:
- [DoWhy GitHub](https://github.com/py-why/dowhy) - Official DoWhy repository
- [DoWhy Documentation](https://py-why.github.io/dowhy/) - Official docs
- [Causal Inference Book](https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/) - Theory

---

## Getting Help

**Questions?**
- Check [Troubleshooting](CAUSAL_ANALYSIS_GUIDE.md#7-troubleshooting) first
- Browse [Examples](EXAMPLES.md) for similar use cases
- Review [API Reference](API_REFERENCE.md) for method details
- Open GitHub issue for bugs/feature requests

**Contributing**:
- Documentation improvements welcome
- New examples appreciated
- Bug reports helpful

---

## Summary

**This documentation suite provides**:
1. ✅ Comprehensive user guide ([CAUSAL_ANALYSIS_GUIDE.md](CAUSAL_ANALYSIS_GUIDE.md))
2. ✅ Complete API reference ([API_REFERENCE.md](API_REFERENCE.md))
3. ✅ 18 runnable examples ([EXAMPLES.md](EXAMPLES.md))
4. ✅ User story scenarios (this README)

**Coverage**:
- ✅ Introduction and concepts
- ✅ Quick start (5 minutes)
- ✅ Use cases (impact analysis, refactoring, testing)
- ✅ Configuration (static/dynamic modes)
- ✅ Best practices
- ✅ Troubleshooting
- ✅ Performance optimization
- ✅ Error handling
- ✅ Advanced topics (counterfactuals, custom mechanisms)
- ✅ Real-world scenarios

**Total**: ~76,000 words, 18 examples, 4 user stories, complete API coverage

---

**Last Updated**: 2025-10-26
**Version**: 0.1.0
**Status**: Complete
