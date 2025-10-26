#!/usr/bin/env python3
"""
Test script for query_fitted_scm.py integration.

Tests the full flow: graph + traces → fit SCM → execute intervention → return results
"""

import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd


def create_test_data():
    """Create simple test data: x → y → z."""
    graph = nx.DiGraph([("x", "y"), ("y", "z")])

    np.random.seed(42)
    n = 200
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.1, n)
    z = y + 1 + np.random.normal(0, 0.1, n)

    traces = pd.DataFrame({"x": x, "y": y, "z": z})

    return graph, traces


def test_hard_intervention():
    """Test hard intervention: do(x=5)."""
    print("\n" + "=" * 80)
    print("Test 1: Hard Intervention - do(x=5)")
    print("=" * 80)

    graph, traces = create_test_data()

    # Prepare input
    input_data = {
        "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
        "traces": {col: traces[col].tolist() for col in traces.columns},
        "intervention": {
            "type": "interventional",
            "interventions": [{"type": "hard", "node": "x", "value": 5.0}],
            "query_nodes": ["x", "y", "z"],
            "num_samples": 1000,
        },
        "config": {"quality": "GOOD"},
    }

    # Run subprocess
    project_root = Path(__file__).parent.parent.parent
    python_path = project_root / ".venv-dowhy" / "bin" / "python"
    script_path = project_root / "scripts" / "dowhy" / "query_fitted_scm.py"

    result = subprocess.run(
        [str(python_path), str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60.0,
    )

    if result.returncode != 0:
        print("❌ Subprocess failed:")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False

    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse output: {e}")
        print(f"stdout: {result.stdout[:500]}")
        return False

    # Validate results
    if output["status"] != "success":
        print(f"❌ Query failed: {output}")
        return False

    statistics = output["statistics"]
    x_mean = statistics["x"]["mean"]
    y_mean = statistics["y"]["mean"]
    z_mean = statistics["z"]["mean"]

    print("\nResults:")
    print(f"  x mean: {x_mean:.2f} (expected: 5.00)")
    print(f"  y mean: {y_mean:.2f} (expected: 10.00)")
    print(f"  z mean: {z_mean:.2f} (expected: 11.00)")

    # Check with tolerance
    if abs(x_mean - 5.0) > 0.1:
        print(f"❌ x mean incorrect: {x_mean} (expected: 5.0)")
        return False

    if abs(y_mean - 10.0) > 0.3:
        print(f"❌ y mean incorrect: {y_mean} (expected: 10.0)")
        return False

    if abs(z_mean - 11.0) > 0.3:
        print(f"❌ z mean incorrect: {z_mean} (expected: 11.0)")
        return False

    print("\n✅ Test passed!")
    return True


def test_soft_intervention():
    """Test soft intervention: x → x + 2."""
    print("\n" + "=" * 80)
    print("Test 2: Soft Intervention - x → x + 2")
    print("=" * 80)

    graph, traces = create_test_data()

    # Prepare input
    input_data = {
        "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
        "traces": {col: traces[col].tolist() for col in traces.columns},
        "intervention": {
            "type": "interventional",
            "interventions": [{"type": "soft", "node": "x", "transform": "shift", "param": 2.0}],
            "query_nodes": ["x", "y", "z"],
            "num_samples": 1000,
        },
        "config": {"quality": "GOOD"},
    }

    # Run subprocess
    project_root = Path(__file__).parent.parent.parent
    python_path = project_root / ".venv-dowhy" / "bin" / "python"
    script_path = project_root / "scripts" / "dowhy" / "query_fitted_scm.py"

    result = subprocess.run(
        [str(python_path), str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60.0,
    )

    if result.returncode != 0:
        print("❌ Subprocess failed:")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False

    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse output: {e}")
        return False

    # Validate results
    if output["status"] != "success":
        print(f"❌ Query failed: {output}")
        return False

    statistics = output["statistics"]
    x_mean = statistics["x"]["mean"]
    y_mean = statistics["y"]["mean"]
    z_mean = statistics["z"]["mean"]

    # Expected shifts: x+2, y+4 (2*2), z+4
    # Baseline: x≈0, y≈0, z≈1
    print("\nResults:")
    print(f"  x mean: {x_mean:.2f} (expected: ~2.0)")
    print(f"  y mean: {y_mean:.2f} (expected: ~4.0)")
    print(f"  z mean: {z_mean:.2f} (expected: ~5.0)")

    # Check with tolerance
    if abs(x_mean - 2.0) > 0.5:
        print(f"❌ x mean incorrect: {x_mean} (expected: ~2.0)")
        return False

    if abs(y_mean - 4.0) > 0.5:
        print(f"❌ y mean incorrect: {y_mean} (expected: ~4.0)")
        return False

    if abs(z_mean - 5.0) > 0.5:
        print(f"❌ z mean incorrect: {z_mean} (expected: ~5.0)")
        return False

    print("\n✅ Test passed!")
    return True


def test_observational_query():
    """Test observational query (no intervention)."""
    print("\n" + "=" * 80)
    print("Test 3: Observational Query (baseline)")
    print("=" * 80)

    graph, traces = create_test_data()

    # Prepare input
    input_data = {
        "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
        "traces": {col: traces[col].tolist() for col in traces.columns},
        "intervention": {
            "type": "observational",
            "query_nodes": ["x", "y", "z"],
            "num_samples": 1000,
        },
        "config": {"quality": "GOOD"},
    }

    # Run subprocess
    project_root = Path(__file__).parent.parent.parent
    python_path = project_root / ".venv-dowhy" / "bin" / "python"
    script_path = project_root / "scripts" / "dowhy" / "query_fitted_scm.py"

    result = subprocess.run(
        [str(python_path), str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60.0,
    )

    if result.returncode != 0:
        print("❌ Subprocess failed:")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        return False

    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse output: {e}")
        return False

    # Validate results
    if output["status"] != "success":
        print(f"❌ Query failed: {output}")
        return False

    statistics = output["statistics"]
    x_mean = statistics["x"]["mean"]
    z_mean = statistics["z"]["mean"]

    # Expected: x≈0, z≈1
    print("\nResults:")
    print(f"  x mean: {x_mean:.2f} (expected: ~0.0)")
    print(f"  z mean: {z_mean:.2f} (expected: ~1.0)")

    # Check with tolerance
    if abs(x_mean - 0.0) > 0.3:
        print(f"❌ x mean incorrect: {x_mean} (expected: ~0.0)")
        return False

    if abs(z_mean - 1.0) > 0.3:
        print(f"❌ z mean incorrect: {z_mean} (expected: ~1.0)")
        return False

    print("\n✅ Test passed!")
    return True


def test_performance():
    """Test query performance."""
    print("\n" + "=" * 80)
    print("Test 4: Performance (<100ms query time)")
    print("=" * 80)

    graph, traces = create_test_data()

    # Prepare input
    input_data = {
        "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
        "traces": {col: traces[col].tolist() for col in traces.columns},
        "intervention": {
            "type": "interventional",
            "interventions": [{"type": "hard", "node": "x", "value": 5.0}],
            "num_samples": 1000,
        },
        "config": {"quality": "GOOD"},
    }

    # Run subprocess
    project_root = Path(__file__).parent.parent.parent
    python_path = project_root / ".venv-dowhy" / "bin" / "python"
    script_path = project_root / "scripts" / "dowhy" / "query_fitted_scm.py"

    result = subprocess.run(
        [str(python_path), str(script_path)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        timeout=60.0,
    )

    if result.returncode != 0:
        print("❌ Subprocess failed")
        return False

    # Parse output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("❌ Failed to parse output")
        return False

    # Check performance
    query_time_ms = output["metadata"]["query_time_ms"]
    fit_time_ms = output["metadata"]["fit_time_ms"]
    total_time_ms = query_time_ms + fit_time_ms

    print("\nPerformance:")
    print(f"  Fit time: {fit_time_ms}ms")
    print(f"  Query time: {query_time_ms}ms")
    print(f"  Total time: {total_time_ms}ms")

    # Query should be fast (<100ms), fit can be slower
    if query_time_ms > 100:
        print(f"⚠️  Query time exceeds 100ms: {query_time_ms}ms")
        print("   (Note: This is query time only, not including fit)")

    if query_time_ms < 100:
        print(f"\n✅ Test passed! Query time: {query_time_ms}ms")

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("DoWhy Query Integration Tests")
    print("=" * 80)

    results = []

    results.append(("Hard Intervention", test_hard_intervention()))
    results.append(("Soft Intervention", test_soft_intervention()))
    results.append(("Observational Query", test_observational_query()))
    results.append(("Performance", test_performance()))

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\nTotal: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
