"""Test fixtures for validation module (STEP-09).

Provides SCMs with known R² scores for testing validation logic.
"""

import networkx as nx
import numpy as np
import pandas as pd


def create_perfect_fit_traces(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Create traces with perfect R²=1.0 fit.

    Linear relationship: y = 2x, z = x + y

    Args:
        n_samples: Number of samples
        random_state: Random seed

    Returns:
        DataFrame with columns [x, y, z]
    """
    rng = np.random.RandomState(random_state)
    x = rng.uniform(-10, 10, n_samples)
    y = 2 * x  # Perfect linear relationship
    z = x + y  # Perfect sum

    return pd.DataFrame({"x": x, "y": y, "z": z})


def create_good_fit_traces(
    n_samples: int = 100, noise_level: float = 0.1, random_state: int = 42
) -> pd.DataFrame:
    """Create traces with good R²≈0.95 fit.

    Linear relationship with small noise: y = 2x + ε, where ε ~ N(0, noise_level)

    Args:
        n_samples: Number of samples
        noise_level: Standard deviation of noise (default 0.1)
        random_state: Random seed

    Returns:
        DataFrame with columns [x, y]
    """
    rng = np.random.RandomState(random_state)
    x = rng.uniform(-10, 10, n_samples)
    noise = rng.normal(0, noise_level, n_samples)
    y = 2 * x + noise

    return pd.DataFrame({"x": x, "y": y})


def create_threshold_fit_traces(
    n_samples: int = 100, target_r2: float = 0.7, random_state: int = 42
) -> pd.DataFrame:
    """Create traces with R² near threshold (≈0.7).

    Uses controlled noise to achieve target R².

    For R² = 1 - (SS_res / SS_tot), we need:
    SS_res = SS_tot * (1 - R²)

    Args:
        n_samples: Number of samples
        target_r2: Target R² value (default 0.7)
        random_state: Random seed

    Returns:
        DataFrame with columns [x, y]
    """
    rng = np.random.RandomState(random_state)
    x = rng.uniform(-10, 10, n_samples)

    # True relationship
    y_true = 2 * x

    # Calculate target variance for noise
    # R² = 1 - Var(noise) / Var(y_true)
    # Var(noise) = Var(y_true) * (1 - R²)
    var_y_true = np.var(y_true)
    var_noise = var_y_true * (1 - target_r2)
    std_noise = np.sqrt(var_noise)

    # Add noise
    noise = rng.normal(0, std_noise, n_samples)
    y = y_true + noise

    return pd.DataFrame({"x": x, "y": y})


def create_poor_fit_traces(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Create traces with poor R²<0.5 fit.

    High noise relative to signal: y = 2x + large_noise

    Args:
        n_samples: Number of samples
        random_state: Random seed

    Returns:
        DataFrame with columns [x, y]
    """
    rng = np.random.RandomState(random_state)
    x = rng.uniform(-10, 10, n_samples)

    # Large noise (3x the signal range)
    y_true = 2 * x
    noise = rng.normal(0, np.std(y_true) * 2, n_samples)
    y = y_true + noise

    return pd.DataFrame({"x": x, "y": y})


def create_nonlinear_traces(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Create traces with nonlinear relationship.

    Quadratic: y = x², z = sin(x)

    Note: Linear R² will be poor for these relationships unless using
    nonlinear regression (DoWhy supports this via auto mechanism assignment).

    Args:
        n_samples: Number of samples
        random_state: Random seed

    Returns:
        DataFrame with columns [x, y, z]
    """
    rng = np.random.RandomState(random_state)
    x = rng.uniform(-5, 5, n_samples)
    y = x**2
    z = np.sin(x)

    return pd.DataFrame({"x": x, "y": y, "z": z})


def create_constant_target_traces(n_samples: int = 100) -> pd.DataFrame:
    """Create traces with constant target (zero variance).

    This is an edge case: y is always 5.0 regardless of x.
    R² calculation should handle this gracefully.

    Args:
        n_samples: Number of samples

    Returns:
        DataFrame with columns [x, y]
    """
    x = np.linspace(-10, 10, n_samples)
    y = np.full(n_samples, 5.0)  # Constant

    return pd.DataFrame({"x": x, "y": y})


def create_multi_parent_traces(n_samples: int = 100, random_state: int = 42) -> pd.DataFrame:
    """Create traces with multi-parent nodes.

    Graph structure:
        x1 → y
        x2 → y
        x3 → y

    Relationship: y = 2*x1 + 3*x2 - x3 + noise

    Args:
        n_samples: Number of samples
        random_state: Random seed

    Returns:
        DataFrame with columns [x1, x2, x3, y]
    """
    rng = np.random.RandomState(random_state)
    x1 = rng.uniform(-10, 10, n_samples)
    x2 = rng.uniform(-10, 10, n_samples)
    x3 = rng.uniform(-10, 10, n_samples)

    noise = rng.normal(0, 0.5, n_samples)
    y = 2 * x1 + 3 * x2 - x3 + noise

    return pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "y": y})


def create_dag_traces(
    n_samples: int = 100, random_state: int = 42
) -> tuple[pd.DataFrame, nx.DiGraph]:
    """Create traces for a complete DAG with known R² scores.

    Graph structure:
        x → a → c
        x → b → c

    Relationships:
        a = 2x + small_noise (R² ≈ 0.95)
        b = x² + small_noise (R² varies - nonlinear)
        c = a + b + small_noise (R² ≈ 0.98)

    Args:
        n_samples: Number of samples
        random_state: Random seed

    Returns:
        Tuple of (traces_df, causal_graph)
    """
    rng = np.random.RandomState(random_state)

    # Root node
    x = rng.uniform(-5, 5, n_samples)

    # Intermediate nodes
    a = 2 * x + rng.normal(0, 0.1, n_samples)  # Linear, high R²
    b = x**2 + rng.normal(0, 0.5, n_samples)  # Nonlinear, moderate R²

    # Final node
    c = a + b + rng.normal(0, 0.1, n_samples)  # Sum, high R²

    traces = pd.DataFrame({"x": x, "a": a, "b": b, "c": c})

    # Build graph
    graph = nx.DiGraph()
    graph.add_edges_from([("x", "a"), ("x", "b"), ("a", "c"), ("b", "c")])

    return traces, graph


def create_chain_traces(
    n_samples: int = 100, chain_length: int = 5, random_state: int = 42
) -> tuple[pd.DataFrame, nx.DiGraph]:
    """Create traces for a chain DAG.

    Graph structure:
        x0 → x1 → x2 → ... → xN

    Each node: x_{i+1} = 1.5 * x_i + noise

    Args:
        n_samples: Number of samples
        chain_length: Length of chain (number of nodes)
        random_state: Random seed

    Returns:
        Tuple of (traces_df, causal_graph)
    """
    rng = np.random.RandomState(random_state)

    # Initialize
    data: dict[str, np.ndarray] = {}
    data["x0"] = rng.uniform(-10, 10, n_samples)

    # Build chain
    for i in range(chain_length - 1):
        prev_node = f"x{i}"
        curr_node = f"x{i + 1}"
        noise = rng.normal(0, 0.1, n_samples)
        data[curr_node] = 1.5 * data[prev_node] + noise

    traces = pd.DataFrame(data)

    # Build graph
    graph = nx.DiGraph()
    edges = [(f"x{i}", f"x{i + 1}") for i in range(chain_length - 1)]
    graph.add_edges_from(edges)

    return traces, graph


def create_insufficient_data_traces(n_samples: int = 3) -> pd.DataFrame:
    """Create traces with insufficient data for validation.

    Only 3 samples - not enough for 80/20 split (need ≥5 for 2 in test set).

    Args:
        n_samples: Number of samples (default 3)

    Returns:
        DataFrame with columns [x, y]
    """
    x = np.array([1.0, 2.0, 3.0])[:n_samples]
    y = 2 * x

    return pd.DataFrame({"x": x, "y": y})


# Known R² values for each fixture
FIXTURE_R2_RANGES = {
    "perfect_fit": (0.99, 1.0),  # R² ≈ 1.0
    "good_fit": (0.90, 0.99),  # R² ≈ 0.95
    "threshold_fit": (0.65, 0.75),  # R² ≈ 0.70
    "poor_fit": (0.0, 0.5),  # R² < 0.5
}
