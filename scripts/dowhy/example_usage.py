"""
Example Usage of DoWhy Subprocess Client

Demonstrates how to use the DoWhy client from Python 3.13 code.
"""

import networkx as nx
import numpy as np
import pandas as pd
from client import DoWhyClient, DoWhySubprocessError


def example_simple_linear():
    """Example 1: Simple linear chain (X → Y → Z)"""
    print("=" * 60)
    print("Example 1: Simple Linear Chain (X → Y → Z)")
    print("=" * 60)

    # Generate synthetic data
    np.random.seed(42)
    n_samples = 1000

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X + np.random.normal(0, 0.1, n_samples)
    Z = 3.0 * Y + np.random.normal(0, 0.1, n_samples)

    # Create graph and traces
    graph = nx.DiGraph([("X", "Y"), ("Y", "Z")])
    traces = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

    print(f"Graph: {list(graph.edges())}")
    print(f"Traces: {len(traces)} samples")

    # Fit SCM
    client = DoWhyClient()
    result = client.fit_scm(graph, traces)

    # Display results
    print(f"\nStatus: {result['status']}")
    print(f"Mean R²: {result['validation']['mean_r2']:.4f}")
    print(f"R² per node: {result['validation']['r2_scores']}")
    print(f"Fitting time: {result['metadata']['fitting_time_ms']}ms")

    # Check mechanisms
    print("\nFitted Mechanisms:")
    for node, mech in result["scm"]["mechanisms"].items():
        print(f"  {node}: {mech['type']}")
        if mech["params"]:
            print(f"    Params: {mech['params']}")

    print()


def example_multi_parent():
    """Example 2: Multi-parent graph (X, Y → Z)"""
    print("=" * 60)
    print("Example 2: Multi-Parent Graph (X, Y → Z)")
    print("=" * 60)

    # Generate synthetic data
    np.random.seed(42)
    n_samples = 1000

    X = np.random.normal(0, 1, n_samples)
    Y = np.random.normal(0, 1, n_samples)
    Z = 1.5 * X + 2.5 * Y + np.random.normal(0, 0.1, n_samples)

    # Create graph and traces
    graph = nx.DiGraph([("X", "Z"), ("Y", "Z")])
    traces = pd.DataFrame({"X": X, "Y": Y, "Z": Z})

    print(f"Graph: {list(graph.edges())}")
    print(f"Traces: {len(traces)} samples")

    # Fit SCM
    client = DoWhyClient()
    result = client.fit_scm(graph, traces)

    print(f"\nStatus: {result['status']}")
    print(f"Mean R²: {result['validation']['mean_r2']:.4f}")
    print(f"Z mechanism: {result['scm']['mechanisms']['Z']}")

    print()


def example_validation_failure():
    """Example 3: Noisy data (R² validation failure)"""
    print("=" * 60)
    print("Example 3: Noisy Data (R² < 0.7)")
    print("=" * 60)

    # Generate noisy data
    np.random.seed(42)
    n_samples = 1000

    X = np.random.normal(0, 1, n_samples)
    Y = 2.0 * X + np.random.normal(0, 5.0, n_samples)  # High noise!

    # Create graph and traces
    graph = nx.DiGraph([("X", "Y")])
    traces = pd.DataFrame({"X": X, "Y": Y})

    print(f"Graph: {list(graph.edges())}")
    print(f"Traces: {len(traces)} samples (high noise)")

    # Fit SCM
    client = DoWhyClient()
    result = client.fit_scm(graph, traces)

    print(f"\nStatus: {result['status']}")
    print(f"Mean R²: {result['validation']['mean_r2']:.4f}")
    print(f"Passed: {result['validation']['passed']}")
    print(f"Failed nodes: {result['validation']['failed_nodes']}")

    print()


def example_error_handling():
    """Example 4: Error handling"""
    print("=" * 60)
    print("Example 4: Error Handling (Cyclic Graph)")
    print("=" * 60)

    # Create cyclic graph (invalid)
    graph = nx.DiGraph([("X", "Y"), ("Y", "Z"), ("Z", "X")])  # Cycle!
    traces = pd.DataFrame({"X": [1, 2, 3], "Y": [2, 3, 4], "Z": [3, 4, 5]})

    print(f"Graph: {list(graph.edges())} (contains cycle)")

    # Try to fit SCM
    client = DoWhyClient()

    try:
        result = client.fit_scm(graph, traces)
        print(f"Unexpected success: {result['status']}")
    except ValueError as e:
        print("\n✅ Caught expected error:")
        print(f"   {e}")
    except DoWhySubprocessError as e:
        print("\n✅ Caught DoWhy error:")
        print(f"   {e}")

    print()


def example_code_execution_trace():
    """Example 5: Real code execution trace"""
    print("=" * 60)
    print("Example 5: Code Execution Trace (def double(x))")
    print("=" * 60)

    # Simulate execution traces from: def double(x): return x * 2
    n_samples = 100
    input_x = np.arange(1, n_samples + 1)
    output = 2 * input_x

    graph = nx.DiGraph([("input_x", "output")])
    traces = pd.DataFrame({"input_x": input_x, "output": output})

    print(f"Graph: {list(graph.edges())}")
    print(f"Traces: {len(traces)} samples (deterministic)")

    # Fit SCM
    client = DoWhyClient()
    result = client.fit_scm(graph, traces)

    print(f"\nStatus: {result['status']}")
    print(f"Mean R²: {result['validation']['mean_r2']:.4f}")
    print(f"Output mechanism: {result['scm']['mechanisms']['output']}")

    # Expected: coef ≈ 2.0, intercept ≈ 0.0
    params = result["scm"]["mechanisms"]["output"]["params"]
    print("\nExpected: coef=2.0, intercept=0.0")
    print(f"Actual:   coef={params['coefficients'][0]:.4f}, intercept={params['intercept']:.4f}")

    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  DoWhy Subprocess Client - Usage Examples                ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Check availability
    client = DoWhyClient()
    if not client.check_availability():
        print("❌ DoWhy subprocess not available. Exiting.")
        return

    print()

    # Run examples
    example_simple_linear()
    example_multi_parent()
    example_validation_failure()
    example_error_handling()
    example_code_execution_trace()

    print("=" * 60)
    print("All examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
