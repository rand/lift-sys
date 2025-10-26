"""Test repository definitions for end-to-end DoWhy integration testing.

This module defines 10 small test codebases with known causal structures
for comprehensive pipeline testing: Code → CausalGraph → FittedSCM → Intervention.

Each repository includes:
- Source code (Python functions)
- Expected causal graph structure
- Expected mechanism types
- Expected intervention behaviors
- Performance characteristics

Usage:
    >>> from tests.causal.fixtures.test_repositories import get_repository
    >>> repo = get_repository("simple_linear")
    >>> repo.code  # Dict of node_id → source code
    >>> repo.expected_graph  # Expected networkx DiGraph
    >>> repo.expected_scm_structure  # Expected mechanism types per node
"""

from dataclasses import dataclass
from typing import Any

import networkx as nx


@dataclass
class TestRepository:
    """Definition of a test repository for E2E testing.

    Attributes:
        name: Repository identifier
        description: What causal structure this tests
        code: Dict of node_id → Python source code
        expected_graph: Expected causal graph (networkx DiGraph)
        expected_scm_structure: Expected mechanism types per node
        expected_interventions: Dict of intervention → expected result
        performance_profile: Expected timing characteristics
        complexity_metrics: Size/complexity measures
    """

    name: str
    description: str
    code: dict[str, str]
    expected_graph: nx.DiGraph
    expected_scm_structure: dict[str, str]  # node → mechanism type
    expected_interventions: dict[str, dict[str, Any]]  # intervention → result spec
    performance_profile: dict[str, float]  # metric → max time (seconds)
    complexity_metrics: dict[str, int]  # metric → count


# =============================================================================
# Repository 1: Simple Linear (x → y)
# =============================================================================


def get_simple_linear() -> TestRepository:
    """Simplest causal structure: single edge x → y.

    Graph: x → y
    Mechanism: y = 2*x (linear, coefficient=2)
    Test focus: Basic pipeline functionality
    """
    code = {
        "y": """def double(x):
    return x * 2"""
    }

    expected_graph = nx.DiGraph([("x", "y")])

    expected_scm_structure = {
        "x": "exogenous",  # Root node
        "y": "linear",  # y = 2*x
    }

    expected_interventions = {
        "do(x=5)": {
            "x": {"mean": 5.0, "std": 0.0},
            "y": {"mean": 10.0, "std_max": 0.5},  # Should be ~10
        },
        "do(x=x+3)": {  # Soft intervention (shift)
            "x": {"mean_shift": 3.0},  # Original mean + 3
            "y": {"mean_shift": 6.0},  # 2 * (original mean + 3)
        },
    }

    performance_profile = {
        "trace_collection": 0.5,  # <0.5s for 100 samples
        "scm_fitting": 2.0,  # <2s
        "intervention_query": 0.1,  # <100ms
    }

    complexity_metrics = {
        "num_nodes": 2,
        "num_edges": 1,
        "num_functions": 1,
        "max_parents": 1,
    }

    return TestRepository(
        name="simple_linear",
        description="Single edge x→y with linear mechanism",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 2: Diamond Structure (x → y, z; y, z → w)
# =============================================================================


def get_diamond() -> TestRepository:
    """Diamond causal structure: common cause and effect.

    Graph: x → y → w
           x → z → w
    Mechanisms:
        - y = 2*x (linear)
        - z = x + 1 (linear with offset)
        - w = y + z (linear multi-parent)
    Test focus: Multi-path dependencies, collider (w)
    """
    code = {
        "y": """def double(x):
    return x * 2""",
        "z": """def increment(x):
    return x + 1""",
        "w": """def add(y, z):
    return y + z""",
    }

    expected_graph = nx.DiGraph([("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")])

    expected_scm_structure = {
        "x": "exogenous",
        "y": "linear",  # y = 2*x
        "z": "linear",  # z = x + 1
        "w": "linear",  # w = y + z
    }

    expected_interventions = {
        "do(x=5)": {
            "x": {"mean": 5.0, "std": 0.0},
            "y": {"mean": 10.0, "std_max": 0.5},  # 2*5
            "z": {"mean": 6.0, "std_max": 0.5},  # 5+1
            "w": {"mean": 16.0, "std_max": 1.0},  # 10+6
        },
        "do(y=8)": {  # Intervene on intermediate node
            "y": {"mean": 8.0, "std": 0.0},
            # x unchanged (intervention cuts edge)
            "z": {"unchanged": True},  # Still depends on x, not y
            "w": {"changed": True},  # Affected via y
        },
        "do(x=5, z=10)": {  # Multiple interventions
            "x": {"mean": 5.0, "std": 0.0},
            "y": {"mean": 10.0, "std_max": 0.5},  # Still 2*x
            "z": {"mean": 10.0, "std": 0.0},  # Overridden
            "w": {"mean": 20.0, "std_max": 1.0},  # 10+10
        },
    }

    performance_profile = {
        "trace_collection": 1.0,  # <1s for 100 samples
        "scm_fitting": 3.0,  # <3s (4 nodes)
        "intervention_query": 0.1,  # <100ms
    }

    complexity_metrics = {
        "num_nodes": 4,
        "num_edges": 4,
        "num_functions": 3,
        "max_parents": 2,  # w has 2 parents
    }

    return TestRepository(
        name="diamond",
        description="Diamond structure with collider",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 3: Chain (x → y → z → w)
# =============================================================================


def get_chain() -> TestRepository:
    """Linear chain: x → y → z → w.

    Mechanisms:
        - y = 2*x
        - z = y + 1
        - w = 3*z
    Test focus: Transitive dependencies, causal paths
    """
    code = {
        "y": """def double(x):
    return x * 2""",
        "z": """def increment(y):
    return y + 1""",
        "w": """def triple(z):
    return z * 3""",
    }

    expected_graph = nx.DiGraph([("x", "y"), ("y", "z"), ("z", "w")])

    expected_scm_structure = {
        "x": "exogenous",
        "y": "linear",
        "z": "linear",
        "w": "linear",
    }

    expected_interventions = {
        "do(x=4)": {
            "x": {"mean": 4.0, "std": 0.0},
            "y": {"mean": 8.0, "std_max": 0.5},  # 2*4
            "z": {"mean": 9.0, "std_max": 0.5},  # 8+1
            "w": {"mean": 27.0, "std_max": 1.0},  # 3*9
        },
        "do(z=5)": {  # Intervene in middle
            "z": {"mean": 5.0, "std": 0.0},
            # x, y unchanged (upstream)
            "w": {"mean": 15.0, "std_max": 0.5},  # 3*5 (downstream affected)
        },
    }

    performance_profile = {
        "trace_collection": 0.8,
        "scm_fitting": 2.5,
        "intervention_query": 0.1,
    }

    complexity_metrics = {
        "num_nodes": 4,
        "num_edges": 3,
        "num_functions": 3,
        "max_parents": 1,
    }

    return TestRepository(
        name="chain",
        description="Linear chain of dependencies",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 4: Nonlinear (x → y with y = x²)
# =============================================================================


def get_nonlinear() -> TestRepository:
    """Nonlinear relationship: x → y where y = x².

    Test focus: Nonlinear mechanism fitting
    """
    code = {
        "y": """def square(x):
    return x ** 2"""
    }

    expected_graph = nx.DiGraph([("x", "y")])

    expected_scm_structure = {
        "x": "exogenous",
        "y": "nonlinear",  # Polynomial degree 2
    }

    expected_interventions = {
        "do(x=3)": {
            "x": {"mean": 3.0, "std": 0.0},
            "y": {"mean": 9.0, "std_max": 1.0},  # 3²
        },
        "do(x=x*2)": {  # Scale intervention
            # Original x ~ Uniform[-5, 5]
            # After scaling: x ~ Uniform[-10, 10]
            "x": {"std_min": 4.0},  # Scaled distribution
            "y": {"changed": True},  # Nonlinear propagation
        },
    }

    performance_profile = {
        "trace_collection": 0.5,
        "scm_fitting": 3.0,  # Nonlinear fitting takes longer
        "intervention_query": 0.15,  # Slightly slower due to complexity
    }

    complexity_metrics = {
        "num_nodes": 2,
        "num_edges": 1,
        "num_functions": 1,
        "max_parents": 1,
    }

    return TestRepository(
        name="nonlinear",
        description="Nonlinear quadratic relationship",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 5: Multi-Parent (a, b, c → result)
# =============================================================================


def get_multi_parent() -> TestRepository:
    """Multiple parents: a, b, c → result.

    Mechanism: result = 2*a + 3*b - c
    Test focus: Multi-variable linear regression
    """
    code = {
        "result": """def combine(a, b, c):
    return 2 * a + 3 * b - c"""
    }

    expected_graph = nx.DiGraph([("a", "result"), ("b", "result"), ("c", "result")])

    expected_scm_structure = {
        "a": "exogenous",
        "b": "exogenous",
        "c": "exogenous",
        "result": "linear",  # Multi-parent linear
    }

    expected_interventions = {
        "do(a=5)": {
            "a": {"mean": 5.0, "std": 0.0},
            "result": {"changed": True},  # Depends on b, c too
        },
        "do(a=5, b=2, c=1)": {  # Set all parents
            "a": {"mean": 5.0, "std": 0.0},
            "b": {"mean": 2.0, "std": 0.0},
            "c": {"mean": 1.0, "std": 0.0},
            "result": {"mean": 15.0, "std_max": 0.5},  # 2*5 + 3*2 - 1 = 15
        },
    }

    performance_profile = {
        "trace_collection": 0.6,
        "scm_fitting": 2.5,
        "intervention_query": 0.1,
    }

    complexity_metrics = {
        "num_nodes": 4,
        "num_edges": 3,
        "num_functions": 1,
        "max_parents": 3,  # result has 3 parents
    }

    return TestRepository(
        name="multi_parent",
        description="Single node with multiple parents",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 6: Empty (no edges, single node)
# =============================================================================


def get_empty() -> TestRepository:
    """Empty repository: single exogenous node.

    Test focus: Edge case handling
    """
    code = {
        "x": """def constant():
    return 42"""
    }

    expected_graph = nx.DiGraph()  # No edges
    expected_graph.add_node("x")

    expected_scm_structure = {
        "x": "constant",
    }

    expected_interventions = {
        "do(x=10)": {
            "x": {"mean": 10.0, "std": 0.0},
        }
    }

    performance_profile = {
        "trace_collection": 0.1,
        "scm_fitting": 0.5,
        "intervention_query": 0.05,
    }

    complexity_metrics = {
        "num_nodes": 1,
        "num_edges": 0,
        "num_functions": 1,
        "max_parents": 0,
    }

    return TestRepository(
        name="empty",
        description="Single node with no dependencies",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 7: Conditional (piecewise function)
# =============================================================================


def get_conditional() -> TestRepository:
    """Conditional function: y = |x| (absolute value).

    Test focus: Piecewise nonlinear mechanisms
    """
    code = {
        "y": """def abs_value(x):
    if x < 0:
        return -x
    return x"""
    }

    expected_graph = nx.DiGraph([("x", "y")])

    expected_scm_structure = {
        "x": "exogenous",
        "y": "nonlinear",  # Piecewise
    }

    expected_interventions = {
        "do(x=-5)": {
            "x": {"mean": -5.0, "std": 0.0},
            "y": {"mean": 5.0, "std_max": 0.5},  # |-5| = 5
        },
        "do(x=3)": {
            "x": {"mean": 3.0, "std": 0.0},
            "y": {"mean": 3.0, "std_max": 0.5},  # |3| = 3
        },
    }

    performance_profile = {
        "trace_collection": 0.5,
        "scm_fitting": 3.5,  # Piecewise fitting is complex
        "intervention_query": 0.15,
    }

    complexity_metrics = {
        "num_nodes": 2,
        "num_edges": 1,
        "num_functions": 1,
        "max_parents": 1,
    }

    return TestRepository(
        name="conditional",
        description="Piecewise function with conditionals",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 8: Mixed (linear + nonlinear)
# =============================================================================


def get_mixed() -> TestRepository:
    """Mixed mechanisms: x → y (linear), y → z (nonlinear).

    Mechanisms:
        - y = 2*x (linear)
        - z = y² (nonlinear)
    Test focus: Mixed mechanism types in pipeline
    """
    code = {
        "y": """def double(x):
    return x * 2""",
        "z": """def square(y):
    return y ** 2""",
    }

    expected_graph = nx.DiGraph([("x", "y"), ("y", "z")])

    expected_scm_structure = {
        "x": "exogenous",
        "y": "linear",
        "z": "nonlinear",
    }

    expected_interventions = {
        "do(x=3)": {
            "x": {"mean": 3.0, "std": 0.0},
            "y": {"mean": 6.0, "std_max": 0.5},  # 2*3
            "z": {"mean": 36.0, "std_max": 2.0},  # 6²
        },
        "do(y=4)": {
            "y": {"mean": 4.0, "std": 0.0},
            "z": {"mean": 16.0, "std_max": 1.0},  # 4²
        },
    }

    performance_profile = {
        "trace_collection": 0.7,
        "scm_fitting": 3.0,
        "intervention_query": 0.12,
    }

    complexity_metrics = {
        "num_nodes": 3,
        "num_edges": 2,
        "num_functions": 2,
        "max_parents": 1,
    }

    return TestRepository(
        name="mixed",
        description="Mixed linear and nonlinear mechanisms",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 9: Wide (many siblings)
# =============================================================================


def get_wide() -> TestRepository:
    """Wide structure: x → [y1, y2, y3, y4, y5].

    Test focus: Fan-out, many children from single parent
    """
    code = {
        "y1": """def times1(x):
    return x * 1""",
        "y2": """def times2(x):
    return x * 2""",
        "y3": """def times3(x):
    return x * 3""",
        "y4": """def times4(x):
    return x * 4""",
        "y5": """def times5(x):
    return x * 5""",
    }

    edges = [("x", f"y{i}") for i in range(1, 6)]
    expected_graph = nx.DiGraph(edges)

    expected_scm_structure = {
        "x": "exogenous",
        **{f"y{i}": "linear" for i in range(1, 6)},
    }

    expected_interventions = {
        "do(x=2)": {
            "x": {"mean": 2.0, "std": 0.0},
            "y1": {"mean": 2.0, "std_max": 0.5},  # 2*1
            "y2": {"mean": 4.0, "std_max": 0.5},  # 2*2
            "y3": {"mean": 6.0, "std_max": 0.5},  # 2*3
            "y4": {"mean": 8.0, "std_max": 0.5},  # 2*4
            "y5": {"mean": 10.0, "std_max": 0.5},  # 2*5
        }
    }

    performance_profile = {
        "trace_collection": 1.0,
        "scm_fitting": 3.0,  # 6 nodes
        "intervention_query": 0.1,
    }

    complexity_metrics = {
        "num_nodes": 6,
        "num_edges": 5,
        "num_functions": 5,
        "max_parents": 1,
    }

    return TestRepository(
        name="wide",
        description="Wide fan-out structure",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository 10: Large (performance testing)
# =============================================================================


def get_large() -> TestRepository:
    """Large repository for performance testing.

    Structure: 20 nodes in chain/tree structure
    Test focus: Performance at scale (<30s total)
    """
    # Create chain: x0 → x1 → x2 → ... → x19
    code = {
        f"x{i}": f"""def f{i}(x{i - 1}):
    return x{i - 1} + {i}"""
        for i in range(1, 20)
    }

    edges = [(f"x{i - 1}", f"x{i}") for i in range(1, 20)]
    expected_graph = nx.DiGraph(edges)

    expected_scm_structure = {
        "x0": "exogenous",
        **{f"x{i}": "linear" for i in range(1, 20)},
    }

    # Only test intervention on root (propagates through all nodes)
    expected_interventions = {
        "do(x0=1)": {
            "x0": {"mean": 1.0, "std": 0.0},
            "x19": {"changed": True},  # Verify propagation to end
        }
    }

    performance_profile = {
        "trace_collection": 5.0,  # <5s for 100 samples
        "scm_fitting": 15.0,  # <15s for 20 nodes
        "intervention_query": 0.5,  # <500ms (more nodes)
    }

    complexity_metrics = {
        "num_nodes": 20,
        "num_edges": 19,
        "num_functions": 19,
        "max_parents": 1,
    }

    return TestRepository(
        name="large",
        description="Large repository for performance testing",
        code=code,
        expected_graph=expected_graph,
        expected_scm_structure=expected_scm_structure,
        expected_interventions=expected_interventions,
        performance_profile=performance_profile,
        complexity_metrics=complexity_metrics,
    )


# =============================================================================
# Repository Registry
# =============================================================================

_REPOSITORIES = {
    "simple_linear": get_simple_linear,
    "diamond": get_diamond,
    "chain": get_chain,
    "nonlinear": get_nonlinear,
    "multi_parent": get_multi_parent,
    "empty": get_empty,
    "conditional": get_conditional,
    "mixed": get_mixed,
    "wide": get_wide,
    "large": get_large,
}


def get_repository(name: str) -> TestRepository:
    """Get test repository by name.

    Args:
        name: Repository name (e.g., "simple_linear", "diamond")

    Returns:
        TestRepository instance

    Raises:
        KeyError: If repository name not found

    Example:
        >>> repo = get_repository("diamond")
        >>> print(repo.description)
        "Diamond structure with collider"
    """
    if name not in _REPOSITORIES:
        available = ", ".join(_REPOSITORIES.keys())
        raise KeyError(f"Repository '{name}' not found. Available: {available}")
    return _REPOSITORIES[name]()


def list_repositories() -> list[str]:
    """List all available repository names.

    Returns:
        List of repository names

    Example:
        >>> repositories = list_repositories()
        >>> len(repositories)
        10
    """
    return list(_REPOSITORIES.keys())


def get_all_repositories() -> dict[str, TestRepository]:
    """Get all repositories as a dict.

    Returns:
        Dict of name → TestRepository

    Example:
        >>> repos = get_all_repositories()
        >>> repos["diamond"].complexity_metrics["num_nodes"]
        4
    """
    return {name: factory() for name, factory in _REPOSITORIES.items()}
