"""
DoWhy Test Case Fixtures

Synthetic and edge-case test data for STEP-08 (Dynamic SCM Fitting).
"""

import json
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd


def generate_linear_chain(
    n_samples: int = 1000, noise_std: float = 0.1, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 1: Simple Linear Chain (X → Y → Z)

    Expected R²: > 0.95 for both Y and Z
    """
    np.random.seed(seed)

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X + np.random.normal(0, noise_std, n_samples)
    Z = 3.0 * Y + np.random.normal(0, noise_std, n_samples)

    graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])
    data = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

    return graph, data


def generate_multi_parent(
    n_samples: int = 1000, noise_std: float = 0.1, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 2: Multi-Parent Graph (X, Y → Z)

    Expected R²: > 0.95 for Z
    """
    np.random.seed(seed)

    X = np.random.normal(0, 1, n_samples)
    Y = np.random.normal(0, 1, n_samples)
    Z = 1.5 * X + 2.5 * Y + np.random.normal(0, noise_std, n_samples)

    graph = nx.DiGraph([("X", "Z"), ("Y", "Z")])
    data = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

    return graph, data


def generate_nonlinear(
    n_samples: int = 1000, noise_std: float = 0.5, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 3: Non-Linear Relationship (X → Y, quadratic)

    Expected: Linear fit R² ≈ 0.0, non-linear fit R² > 0.8
    """
    np.random.seed(seed)

    X = np.random.uniform(-3, 3, n_samples)
    Y = X**2 + np.random.normal(0, noise_std, n_samples)

    graph = nx.DiGraph([("X", "Y")])
    data = pd.DataFrame({"X": X, "Y": Y})

    return graph, data


def generate_insufficient_data(
    n_samples: int = 50, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 4: Insufficient Data (below minimum threshold)

    Expected: Warning about insufficient data
    """
    np.random.seed(seed)

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X + np.random.normal(0, 0.1, n_samples)

    graph = nx.DiGraph([("X", "Y")])
    data = pd.DataFrame({"X": X, "Y": Y})

    return graph, data


def generate_noisy_data(
    n_samples: int = 1000, noise_std: float = 5.0, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 5: Noisy Data (large noise, low R²)

    Expected: R² ≈ 0.3-0.5 (below threshold), validation failure
    """
    np.random.seed(seed)

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X + np.random.normal(0, noise_std, n_samples)

    graph = nx.DiGraph([("X", "Y")])
    data = pd.DataFrame({"X": X, "Y": Y})

    return graph, data


def generate_perfect_correlation(
    n_samples: int = 1000, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 6: Perfect Correlation (no noise, potential data leakage)

    Expected: R² = 1.0, warning about perfect correlation
    """
    np.random.seed(seed)

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X  # No noise!

    graph = nx.DiGraph([("X", "Y")])
    data = pd.DataFrame({"X": X, "Y": Y})

    return graph, data


def generate_code_execution_trace(
    n_samples: int = 100, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 7: Code Execution Traces (deterministic function)

    Simulates: def double(x): return x * 2

    Expected: R² ≈ 1.0 (deterministic)
    """
    np.random.seed(seed)

    input_x = np.arange(1, n_samples + 1)
    output = 2 * input_x

    graph = nx.DiGraph([("input_x", "output")])
    data = pd.DataFrame({"input_x": input_x, "output": output})

    return graph, data


def generate_validation_function_trace(
    n_samples: int = 1000, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 8: Validation Function Trace

    Simulates:
        is_valid = (input > 0)
        output = process(input) if is_valid else None

    Expected: Complex relationships, R² moderate (0.5-0.8)
    """
    np.random.seed(seed)

    # Generate inputs
    input_vals = np.random.uniform(-5, 5, n_samples)
    is_valid = (input_vals > 0).astype(int)

    # Output only defined when valid
    output = np.where(is_valid, 2 * input_vals + 1, np.nan)

    # Remove NaN rows
    data = pd.DataFrame({"input": input_vals, "is_valid": is_valid, "output": output}).dropna()

    graph = nx.DiGraph([("input", "is_valid"), ("input", "output"), ("is_valid", "output")])

    return graph, data


def generate_complex_dag(
    n_samples: int = 1000, noise_std: float = 0.1, seed: int = 42
) -> tuple[nx.DiGraph, pd.DataFrame]:
    """
    Test Case 9: Complex DAG (A → B → D, A → C → D)

    Expected: R² > 0.8 for all nodes
    """
    np.random.seed(seed)

    A = np.random.normal(0, 1, n_samples)
    B = 2.0 * A + np.random.normal(0, noise_std, n_samples)
    C = 1.5 * A + np.random.normal(0, noise_std, n_samples)
    D = 1.0 * B + 0.5 * C + np.random.normal(0, noise_std, n_samples)

    graph = nx.DiGraph([("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")])

    data = pd.DataFrame({"A": A, "B": B, "C": C, "D": D})

    return graph, data


def graph_to_json(graph: nx.DiGraph) -> dict:
    """Convert NetworkX graph to JSON representation."""
    return {"nodes": list(graph.nodes()), "edges": list(graph.edges())}


def dataframe_to_json(df: pd.DataFrame) -> dict[str, list[float]]:
    """Convert pandas DataFrame to JSON representation."""
    return {col: df[col].tolist() for col in df.columns}


def save_test_case(name: str, graph: nx.DiGraph, data: pd.DataFrame, output_dir: Path):
    """Save test case to JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    test_case = {
        "name": name,
        "graph": graph_to_json(graph),
        "traces": dataframe_to_json(data),
        "config": {"quality": "GOOD", "validate_r2": True, "r2_threshold": 0.7},
    }

    output_path = output_dir / f"{name}.json"
    with open(output_path, "w") as f:
        json.dump(test_case, f, indent=2)

    print(f"Saved: {output_path}")


def generate_all_test_cases(output_dir: str = "tests/fixtures/dowhy_traces"):
    """Generate and save all test cases."""
    output_path = Path(output_dir)

    test_cases = [
        ("linear_chain", generate_linear_chain()),
        ("multi_parent", generate_multi_parent()),
        ("nonlinear", generate_nonlinear()),
        ("insufficient_data", generate_insufficient_data()),
        ("noisy_data", generate_noisy_data()),
        ("perfect_correlation", generate_perfect_correlation()),
        ("code_execution", generate_code_execution_trace()),
        ("validation_function", generate_validation_function_trace()),
        ("complex_dag", generate_complex_dag()),
    ]

    for name, (graph, data) in test_cases:
        save_test_case(name, graph, data, output_path)

    print(f"\nGenerated {len(test_cases)} test cases in {output_path}")


if __name__ == "__main__":
    generate_all_test_cases()
