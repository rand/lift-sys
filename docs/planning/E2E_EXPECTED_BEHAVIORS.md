# End-to-End Expected Behaviors

**Date**: 2025-10-26
**Status**: Specification Complete
**Related**: E2E_TEST_SCENARIOS.md, test_repositories.py

---

## Overview

This document specifies **exact expected outputs** for each test scenario defined in E2E_TEST_SCENARIOS.md. Use this as the ground truth for test assertions.

Format for each scenario:
```
Input: [Repository + configuration]
Output: [Exact expected structure with tolerances]
```

---

## Repository 1: Simple Linear (x → y)

### Input
```python
code = {
    "y": "def double(x):\n    return x * 2"
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x", "y"]
edges = [("x", "y")]
num_nodes = 2
num_edges = 1
is_dag = True
```

#### SCM Structure (Static Mode)
```python
scm = {
    "mode": "static",
    "graph": DiGraph(...),
    "mechanisms": {
        "x": {
            "type": "exogenous",
            "distribution": "uniform",  # Default for roots
            "range": [-5.0, 5.0],
        },
        "y": {
            "type": "linear",
            "parents": ["x"],
            "coefficients": {"x": 2.0},
            "offset": 0.0,
            "inferred_from": "ast_analysis",
        }
    },
    "validation": {
        "graph_is_dag": True,
        "all_nodes_have_mechanisms": True,
    }
}
```

#### SCM Structure (Dynamic Mode, 100 traces)
```python
scm = {
    "mode": "dynamic",
    "graph": DiGraph(...),
    "scm": gcm.StructuralCausalModel(...),  # DoWhy object
    "traces": DataFrame(shape=(100, 2)),  # 100 samples, 2 nodes
    "validation": {
        "r_squared": {
            "y": 1.0 ± 0.01,  # Near-perfect fit for linear
        },
        "fit_quality": "excellent",
    }
}
```

#### Intervention: do(x=5)
```python
intervention_spec = InterventionSpec(
    interventions=[HardIntervention(node="x", value=5.0)],
    query_nodes=None,  # All nodes
)

result = InterventionResult(
    samples={
        "x": np.array([5.0, 5.0, ..., 5.0]),  # 100 samples, all 5.0
        "y": np.array([10.0 ± 0.1, ..., 10.0 ± 0.1]),  # Should be ~10.0
    },
    statistics={
        "x": {
            "mean": 5.0,
            "std": 0.0,
            "min": 5.0,
            "max": 5.0,
        },
        "y": {
            "mean": 10.0 ± 0.5,  # Tolerance for stochastic SCM
            "std": 0.0 ± 0.5,  # Should be near-zero
            "min": 9.5 ± 0.5,
            "max": 10.5 ± 0.5,
        }
    },
    metadata={
        "num_samples": 100,
        "query_time_ms": < 100,  # Performance requirement
        "interventions_applied": 1,
    },
    intervention_spec=intervention_spec,
)
```

#### Intervention: do(x=x+3) [Soft, Shift]
```python
# Original x ~ Uniform[-5, 5], mean ≈ 0
# After shift: x ~ Uniform[-2, 8], mean ≈ 3

result.statistics = {
    "x": {
        "mean": 3.0 ± 1.0,  # Should shift by +3
        "std": 2.89 ± 0.5,  # Std preserved (uniform distribution)
    },
    "y": {
        "mean": 6.0 ± 2.0,  # 2 * (0 + 3) = 6
        "std": 5.77 ± 1.0,  # 2 * std(x)
    }
}
```

#### Intervention: do(x=x*2) [Soft, Scale]
```python
# Original x ~ Uniform[-5, 5], std ≈ 2.89
# After scale: x ~ Uniform[-10, 10], std ≈ 5.77

result.statistics = {
    "x": {
        "mean": 0.0 ± 1.0,  # Mean preserved (symmetric scaling)
        "std": 5.77 ± 1.0,  # Std doubles
    },
    "y": {
        "mean": 0.0 ± 2.0,  # 2 * 0 = 0
        "std": 11.55 ± 2.0,  # 2 * std(x) * 2
    }
}
```

---

## Repository 2: Diamond (x → y, z; y, z → w)

### Input
```python
code = {
    "y": "def double(x):\n    return x * 2",
    "z": "def increment(x):\n    return x + 1",
    "w": "def add(y, z):\n    return y + z",
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x", "y", "z", "w"]
edges = [("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")]
num_nodes = 4
num_edges = 4
is_dag = True

# Topological order (valid): ["x", "y", "z", "w"] or ["x", "z", "y", "w"]
# Node "w" must come after both "y" and "z"
```

#### SCM Structure (Dynamic Mode)
```python
scm = {
    "mode": "dynamic",
    "mechanisms": {
        "x": {"type": "exogenous"},
        "y": {"type": "linear", "parents": ["x"]},
        "z": {"type": "linear", "parents": ["x"]},
        "w": {"type": "linear", "parents": ["y", "z"]},  # Multi-parent
    },
    "validation": {
        "r_squared": {
            "y": 1.0 ± 0.01,
            "z": 1.0 ± 0.01,
            "w": 1.0 ± 0.01,
        }
    }
}
```

#### Intervention: do(x=5)
```python
result.statistics = {
    "x": {"mean": 5.0, "std": 0.0},
    "y": {"mean": 10.0 ± 0.5, "std": 0.0 ± 0.5},  # 2*5
    "z": {"mean": 6.0 ± 0.5, "std": 0.0 ± 0.5},   # 5+1
    "w": {"mean": 16.0 ± 1.0, "std": 0.0 ± 1.0},  # 10+6
}
```

#### Intervention: do(y=8)
```python
# Intervene on intermediate node
# This cuts edge x → y, but NOT x → z

result.statistics = {
    "x": {"unchanged": True},  # Upstream not affected
    "y": {"mean": 8.0, "std": 0.0},  # Set by intervention
    "z": {"unchanged": True},  # Still depends on x, not y
    "w": {
        "mean": 8.0 + z_original_mean ± 1.0,  # y=8, z from x's distribution
        "changed": True,  # Affected via y
    }
}
```

#### Intervention: do(x=5, z=10) [Multiple]
```python
result.statistics = {
    "x": {"mean": 5.0, "std": 0.0},
    "y": {"mean": 10.0 ± 0.5, "std": 0.0 ± 0.5},  # Still 2*x
    "z": {"mean": 10.0, "std": 0.0},  # Overridden by intervention
    "w": {"mean": 20.0 ± 1.0, "std": 0.0 ± 1.0},  # 10+10
}
```

---

## Repository 3: Chain (x → y → z → w)

### Input
```python
code = {
    "y": "def double(x):\n    return x * 2",
    "z": "def increment(y):\n    return y + 1",
    "w": "def triple(z):\n    return z * 3",
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x", "y", "z", "w"]
edges = [("x", "y"), ("y", "z"), ("z", "w")]
num_nodes = 4
num_edges = 3
is_dag = True

# Topological order: ["x", "y", "z", "w"] (unique)
```

#### Intervention: do(x=4)
```python
# Test full propagation through chain
result.statistics = {
    "x": {"mean": 4.0, "std": 0.0},
    "y": {"mean": 8.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*4
    "z": {"mean": 9.0 ± 0.5, "std": 0.0 ± 0.5},   # 8+1
    "w": {"mean": 27.0 ± 1.0, "std": 0.0 ± 1.0},  # 3*9
}
```

#### Intervention: do(z=5) [Middle of chain]
```python
# Upstream unchanged, downstream affected
result.statistics = {
    "x": {"unchanged": True},  # Not queried or affected
    "y": {"unchanged": True},  # Upstream
    "z": {"mean": 5.0, "std": 0.0},
    "w": {"mean": 15.0 ± 0.5, "std": 0.0 ± 0.5},  # 3*5
}
```

---

## Repository 4: Nonlinear (x → y, y = x²)

### Input
```python
code = {
    "y": "def square(x):\n    return x ** 2"
}
```

### Expected Outputs

#### SCM Structure (Dynamic Mode)
```python
scm = {
    "mode": "dynamic",
    "mechanisms": {
        "x": {"type": "exogenous"},
        "y": {"type": "nonlinear", "parents": ["x"]},
    },
    "validation": {
        "r_squared": {
            # Linear fit should be poor for quadratic data
            "y_linear": < 0.7,  # Fails linear test
            "y_polynomial": > 0.95,  # Good with polynomial
        },
        "mechanism_complexity": "polynomial_degree_2",
    }
}
```

#### Intervention: do(x=3)
```python
result.statistics = {
    "x": {"mean": 3.0, "std": 0.0},
    "y": {"mean": 9.0 ± 1.0, "std": 0.0 ± 1.0},  # 3² = 9
}
```

#### Intervention: do(x=-4)
```python
result.statistics = {
    "x": {"mean": -4.0, "std": 0.0},
    "y": {"mean": 16.0 ± 1.0, "std": 0.0 ± 1.0},  # (-4)² = 16
}
```

---

## Repository 5: Multi-Parent (a, b, c → result)

### Input
```python
code = {
    "result": "def combine(a, b, c):\n    return 2 * a + 3 * b - c"
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["a", "b", "c", "result"]
edges = [("a", "result"), ("b", "result"), ("c", "result")]
num_nodes = 4
num_edges = 3
is_dag = True
```

#### SCM Structure (Dynamic Mode)
```python
scm = {
    "mechanisms": {
        "a": {"type": "exogenous"},
        "b": {"type": "exogenous"},
        "c": {"type": "exogenous"},
        "result": {
            "type": "linear",
            "parents": ["a", "b", "c"],
            "coefficients": {
                "a": 2.0 ± 0.1,  # Should be ~2.0
                "b": 3.0 ± 0.1,  # Should be ~3.0
                "c": -1.0 ± 0.1,  # Should be ~-1.0
            },
            "offset": 0.0 ± 0.1,
        }
    },
    "validation": {
        "r_squared": {"result": 1.0 ± 0.01},
    }
}
```

#### Intervention: do(a=5, b=2, c=1)
```python
# All parents set → Deterministic result
result.statistics = {
    "a": {"mean": 5.0, "std": 0.0},
    "b": {"mean": 2.0, "std": 0.0},
    "c": {"mean": 1.0, "std": 0.0},
    "result": {
        "mean": 15.0 ± 0.5,  # 2*5 + 3*2 - 1 = 15
        "std": 0.0 ± 0.5,
    }
}
```

#### Intervention: do(a=5) [Partial]
```python
# Only 'a' set, 'b' and 'c' remain stochastic
result.statistics = {
    "a": {"mean": 5.0, "std": 0.0},
    "b": {"unchanged": True},  # Still from original distribution
    "c": {"unchanged": True},
    "result": {
        "changed": True,  # Affected by 'a' intervention
        "mean_shift": 10.0 ± 1.0,  # Shifts by 2*5 = 10
    }
}
```

---

## Repository 6: Empty (Single Node)

### Input
```python
code = {
    "x": "def constant():\n    return 42"
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x"]
edges = []
num_nodes = 1
num_edges = 0
is_dag = True
```

#### SCM Structure
```python
scm = {
    "mechanisms": {
        "x": {
            "type": "constant",
            "value": 42.0,
            "parents": [],
        }
    }
}
```

#### Intervention: do(x=10)
```python
result.statistics = {
    "x": {"mean": 10.0, "std": 0.0}
}
```

---

## Repository 7: Conditional (x → y, y = |x|)

### Input
```python
code = {
    "y": """def abs_value(x):
    if x < 0:
        return -x
    return x"""
}
```

### Expected Outputs

#### SCM Structure (Dynamic Mode)
```python
scm = {
    "mechanisms": {
        "x": {"type": "exogenous"},
        "y": {"type": "nonlinear", "parents": ["x"], "subtype": "piecewise"},
    },
    "validation": {
        "r_squared": {
            "y": > 0.7,  # Should fit reasonably well
        },
        "mechanism_complexity": "piecewise_or_nonlinear",
    }
}
```

#### Intervention: do(x=-5)
```python
result.statistics = {
    "x": {"mean": -5.0, "std": 0.0},
    "y": {"mean": 5.0 ± 0.5, "std": 0.0 ± 0.5},  # |-5| = 5
}
```

#### Intervention: do(x=3)
```python
result.statistics = {
    "x": {"mean": 3.0, "std": 0.0},
    "y": {"mean": 3.0 ± 0.5, "std": 0.0 ± 0.5},  # |3| = 3
}
```

---

## Repository 8: Mixed (Linear + Nonlinear)

### Input
```python
code = {
    "y": "def double(x):\n    return x * 2",
    "z": "def square(y):\n    return y ** 2",
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x", "y", "z"]
edges = [("x", "y"), ("y", "z")]
num_nodes = 3
num_edges = 2
is_dag = True
```

#### SCM Structure (Dynamic Mode)
```python
scm = {
    "mechanisms": {
        "x": {"type": "exogenous"},
        "y": {"type": "linear", "parents": ["x"]},
        "z": {"type": "nonlinear", "parents": ["y"]},
    },
    "validation": {
        "r_squared": {
            "y": 1.0 ± 0.01,  # Linear
            "z": > 0.95,  # Nonlinear (polynomial)
        }
    }
}
```

#### Intervention: do(x=3)
```python
result.statistics = {
    "x": {"mean": 3.0, "std": 0.0},
    "y": {"mean": 6.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*3
    "z": {"mean": 36.0 ± 2.0, "std": 0.0 ± 2.0},  # 6²
}
```

---

## Repository 9: Wide (x → [y1..y5])

### Input
```python
code = {
    "y1": "def times1(x):\n    return x * 1",
    "y2": "def times2(x):\n    return x * 2",
    "y3": "def times3(x):\n    return x * 3",
    "y4": "def times4(x):\n    return x * 4",
    "y5": "def times5(x):\n    return x * 5",
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x", "y1", "y2", "y3", "y4", "y5"]
edges = [("x", "y1"), ("x", "y2"), ("x", "y3"), ("x", "y4"), ("x", "y5")]
num_nodes = 6
num_edges = 5
is_dag = True
```

#### Intervention: do(x=2)
```python
result.statistics = {
    "x": {"mean": 2.0, "std": 0.0},
    "y1": {"mean": 2.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*1
    "y2": {"mean": 4.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*2
    "y3": {"mean": 6.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*3
    "y4": {"mean": 8.0 ± 0.5, "std": 0.0 ± 0.5},   # 2*4
    "y5": {"mean": 10.0 ± 0.5, "std": 0.0 ± 0.5},  # 2*5
}
```

---

## Repository 10: Large (20-node chain)

### Input
```python
code = {
    f"x{i}": f"def f{i}(x{i-1}):\n    return x{i-1} + {i}"
    for i in range(1, 20)
}
```

### Expected Outputs

#### Graph Structure
```python
nodes = ["x0", "x1", ..., "x19"]
edges = [("x0", "x1"), ("x1", "x2"), ..., ("x18", "x19")]
num_nodes = 20
num_edges = 19
is_dag = True
```

#### Performance Metrics
```python
performance = {
    "trace_collection_time": < 5.0,  # seconds
    "scm_fitting_time": < 15.0,      # seconds
    "intervention_query_time": < 0.5, # seconds
    "total_e2e_time": < 30.0,        # seconds
}
```

#### Intervention: do(x0=1)
```python
# Test propagation through long chain
result.statistics = {
    "x0": {"mean": 1.0, "std": 0.0},
    "x1": {"mean": 2.0 ± 0.5, "std": 0.0 ± 0.5},   # 1+1
    "x2": {"mean": 4.0 ± 0.5, "std": 0.0 ± 0.5},   # 2+2
    # ... (intermediate nodes omitted for brevity)
    "x19": {
        "mean": 191.0 ± 5.0,  # Sum: 1 + (1+2+...+19) = 1 + 190 = 191
        "changed": True,
    }
}
```

---

## Error Cases Expected Behaviors

### Error 1: Syntax Error in Code
```python
input_code = {
    "y": "def broken(x)\n    return x * 2"  # Missing colon
}

expected_error = {
    "type": "SyntaxError",
    "message": "invalid syntax at line 1",
    "location": "def broken(x)",
    "suggestion": "Check for missing colons, parentheses, or indentation",
}
```

### Error 2: Circular Dependencies
```python
input_code = {
    "a": "def func_a(b):\n    return b + 1",
    "b": "def func_b(a):\n    return a + 1",  # Circular: a ↔ b
}

expected_error = {
    "type": "GraphError",
    "message": "Circular dependency detected",
    "cycle": ["a", "b", "a"],
    "suggestion": "Refactor to break cycle (introduce intermediate variable)",
}
```

### Error 3: Empty File
```python
input_code = {}

expected_output = {
    "graph": nx.DiGraph(),  # Empty graph, no error
    "scm": None,  # No SCM to fit
    "error": None,  # Valid edge case
}
```

### Error 4: Mismatched Traces
```python
graph_nodes = ["x", "y"]
trace_columns = ["a", "b"]  # Different names!

expected_error = {
    "type": "DataError",
    "message": "Trace columns don't match graph nodes",
    "expected": ["x", "y"],
    "actual": ["a", "b"],
    "suggestion": "Ensure trace collection uses correct node names",
}
```

### Error 5: Insufficient Traces
```python
num_samples = 3  # Too few!

expected_error = {
    "type": "DataError",
    "message": "Insufficient samples for reliable fitting",
    "num_samples": 3,
    "minimum_recommended": 50,
    "suggestion": "Collect at least 50-100 samples for stable fit",
}
```

### Error 6: Invalid Intervention Node
```python
graph_nodes = ["x", "y"]
intervention = "do(z=5)"  # 'z' not in graph!

expected_error = {
    "type": "ValidationError",
    "message": "Intervention node 'z' not in causal graph",
    "available_nodes": ["x", "y"],
    "suggestion": "Check node name or add node to graph",
}
```

### Error 7: Intervention Without Traces
```python
scm = {
    "mode": "static",
    # Missing 'traces' key!
}
intervention = "do(x=5)"

expected_error = {
    "type": "InterventionError",
    "message": "SCM must contain 'traces' for intervention queries",
    "current_mode": "static",
    "suggestion": "Refit SCM with traces (dynamic mode) to enable interventions",
}
```

---

## Validation Helpers

### Assertion Functions

```python
def assert_graph_structure(actual_graph, expected_repo):
    """Validate graph matches expected structure."""
    assert set(actual_graph.nodes()) == set(expected_repo.expected_graph.nodes())
    assert set(actual_graph.edges()) == set(expected_repo.expected_graph.edges())
    assert nx.is_directed_acyclic_graph(actual_graph)

def assert_scm_quality(scm, expected_r2):
    """Validate SCM fitting quality."""
    for node, expected in expected_r2.items():
        actual = scm["validation"]["r_squared"][node]
        assert actual >= expected, f"Node {node}: R²={actual} < {expected}"

def assert_intervention_result(result, expected_stats, tolerance=0.5):
    """Validate intervention results within tolerance."""
    for node, stats in expected_stats.items():
        if "mean" in stats:
            expected_mean = stats["mean"]
            actual_mean = result.statistics[node]["mean"]
            assert abs(actual_mean - expected_mean) < tolerance, \
                f"Node {node}: mean={actual_mean} != {expected_mean} ± {tolerance}"

def assert_performance(elapsed_time, max_time):
    """Validate performance requirements."""
    assert elapsed_time < max_time, \
        f"Performance: {elapsed_time:.2f}s > {max_time:.2f}s"
```

---

## Tolerance Guidelines

### R² Thresholds
- **Linear relationships**: R² ≥ 0.95 (near-perfect fit expected)
- **Nonlinear relationships**: R² ≥ 0.7 (acceptable fit)
- **Noisy data**: R² ≥ 0.7 (robust to noise)

### Intervention Result Tolerances
- **Hard interventions (deterministic)**:
  - Mean: ± 0.5 (accounts for SCM stochasticity)
  - Std: ± 0.5 (should be near-zero)
- **Soft interventions (distributional)**:
  - Mean: ± 1.0 (larger variance expected)
  - Std: ± 1.0 (distribution shape preserved within tolerance)

### Performance Tolerances
- **Trace collection**: Allow 2x buffer (system variance)
- **SCM fitting**: Allow 1.5x buffer (DoWhy subprocess overhead)
- **Intervention query**: Allow 2x buffer (subprocess communication)

---

## Usage in Tests

```python
from tests.causal.fixtures.test_repositories import get_repository

def test_simple_linear_intervention():
    """Test intervention on simple_linear repository."""
    repo = get_repository("simple_linear")

    # Extract graph
    graph = extract_graph(repo.code)
    assert_graph_structure(graph, repo)

    # Fit SCM
    traces = collect_traces(graph, repo.code, num_samples=100)
    scm = fit_scm(graph, traces)
    assert_scm_quality(scm, {"y": 0.95})

    # Execute intervention
    result = execute_intervention(scm, "do(x=5)", graph)

    # Validate result
    expected = {
        "x": {"mean": 5.0},
        "y": {"mean": 10.0},
    }
    assert_intervention_result(result, expected, tolerance=0.5)
```

---

## Next Steps

1. **Implement assertion helpers** in `tests/causal/e2e/helpers.py`
2. **Use this spec** as ground truth for test assertions
3. **Update tolerances** if empirical results differ systematically
4. **Document deviations** if expected behaviors need adjustment
