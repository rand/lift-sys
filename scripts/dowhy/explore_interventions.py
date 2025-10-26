#!/usr/bin/env .venv-dowhy/bin/python
"""
Exploration script for DoWhy intervention capabilities.

This script tests various intervention patterns to understand:
1. Hard interventions (do(X=value))
2. Soft interventions (shift distributions)
3. Multiple simultaneous interventions
4. Counterfactual vs interventional queries
5. Performance characteristics

Usage:
    .venv-dowhy/bin/python scripts/dowhy/explore_interventions.py
"""

import time

import networkx as nx
import numpy as np
import pandas as pd
from dowhy import gcm

# ============================================================================
# Helper Functions
# ============================================================================


def create_simple_scm():
    """Create and fit a simple SCM: x → y → z."""
    # Create graph
    graph = nx.DiGraph([("x", "y"), ("y", "z")])

    # Create data (x ~ N(0,1), y = 2*x + noise, z = y + 1 + noise)
    np.random.seed(42)
    n = 1000
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.1, n)
    z = y + 1 + np.random.normal(0, 0.1, n)

    data = pd.DataFrame({"x": x, "y": y, "z": z})

    # Create and fit SCM
    causal_model = gcm.StructuralCausalModel(graph)
    gcm.auto.assign_causal_mechanisms(causal_model, data, quality=gcm.auto.AssignmentQuality.GOOD)
    gcm.fit(causal_model, data)

    return causal_model, data


def create_diamond_scm():
    """Create and fit diamond SCM: x → y, x → z, y → w, z → w."""
    graph = nx.DiGraph([("x", "y"), ("x", "z"), ("y", "w"), ("z", "w")])

    np.random.seed(42)
    n = 1000
    x = np.random.normal(0, 1, n)
    y = 2 * x + np.random.normal(0, 0.1, n)
    z = 3 * x + np.random.normal(0, 0.1, n)
    w = y + z + np.random.normal(0, 0.1, n)

    data = pd.DataFrame({"x": x, "y": y, "z": z, "w": w})

    causal_model = gcm.StructuralCausalModel(graph)
    gcm.auto.assign_causal_mechanisms(causal_model, data, quality=gcm.auto.AssignmentQuality.GOOD)
    gcm.fit(causal_model, data)

    return causal_model, data


# ============================================================================
# Intervention Exploration
# ============================================================================


def explore_hard_intervention():
    """Explore hard intervention: do(X=value)."""
    print("\n" + "=" * 80)
    print("1. HARD INTERVENTION: do(X=value)")
    print("=" * 80)

    scm, data = create_simple_scm()

    # Baseline (no intervention)
    baseline_samples = gcm.draw_samples(scm, num_samples=1000)
    print("\nBaseline means:")
    print(baseline_samples.mean())

    # Hard intervention: do(x = 5)
    print("\nIntervention: do(x = 5)")
    intervention = {"x": lambda x: 5}  # Set x to constant 5
    intervened_samples = gcm.whatif.interventional_samples(
        scm, intervention, num_samples_to_draw=1000
    )

    print("\nIntervened means:")
    print(intervened_samples.mean())

    # Expected: x ≈ 5, y ≈ 10 (2*5), z ≈ 11 (10+1)
    print("\nExpected: x=5, y≈10, z≈11")
    print(
        f"Actual: x={intervened_samples['x'].mean():.2f}, y={intervened_samples['y'].mean():.2f}, z={intervened_samples['z'].mean():.2f}"
    )


def explore_soft_intervention():
    """Explore soft intervention: shift distribution."""
    print("\n" + "=" * 80)
    print("2. SOFT INTERVENTION: shift distribution")
    print("=" * 80)

    scm, data = create_simple_scm()

    # Soft intervention: x → x + 2 (shift mean by 2)
    print("\nIntervention: x → x + 2")
    intervention = {"x": lambda x: x + 2}
    intervened_samples = gcm.whatif.interventional_samples(
        scm, intervention, num_samples_to_draw=1000
    )

    baseline_samples = gcm.draw_samples(scm, num_samples=1000)

    print(
        f"\nBaseline means: x={baseline_samples['x'].mean():.2f}, y={baseline_samples['y'].mean():.2f}, z={baseline_samples['z'].mean():.2f}"
    )
    print(
        f"Intervened means: x={intervened_samples['x'].mean():.2f}, y={intervened_samples['y'].mean():.2f}, z={intervened_samples['z'].mean():.2f}"
    )

    # Expected shift: x +2, y +4 (2*2), z +4
    print("\nExpected shift: Δx≈+2, Δy≈+4, Δz≈+4")


def explore_multiple_interventions():
    """Explore multiple simultaneous interventions."""
    print("\n" + "=" * 80)
    print("3. MULTIPLE INTERVENTIONS: do(x=3, y=10)")
    print("=" * 80)

    scm, data = create_diamond_scm()

    # Baseline
    baseline_samples = gcm.draw_samples(scm, num_samples=1000)
    print("\nBaseline means:")
    print(baseline_samples.mean())

    # Multiple interventions: do(x=3, y=10)
    print("\nIntervention: do(x=3), do(y=10)")
    interventions = {
        "x": lambda x: 3,  # Set x to 3
        "y": lambda y: 10,  # Override y to 10 (breaks x→y edge)
    }
    intervened_samples = gcm.whatif.interventional_samples(
        scm, interventions, num_samples_to_draw=1000
    )

    print("\nIntervened means:")
    print(intervened_samples.mean())

    # Expected: x=3, y=10 (overridden), z≈9 (3*3 from x→z), w≈19 (10+9)
    print("\nExpected: x=3, y=10, z≈9, w≈19")


def explore_counterfactual_vs_interventional():
    """Compare counterfactual vs interventional queries."""
    print("\n" + "=" * 80)
    print("4. COUNTERFACTUAL vs INTERVENTIONAL")
    print("=" * 80)

    scm, data = create_simple_scm()

    # Interventional: do(x=5), sample from intervened distribution
    print("\nInterventional: What if we set x=5 in general?")
    intervention = {"x": lambda x: 5}
    interventional = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=1000)
    print(f"  Mean y: {interventional['y'].mean():.2f}, Mean z: {interventional['z'].mean():.2f}")

    # Counterfactual: Given we observed specific x, what if x had been 5?
    print("\nCounterfactual: Given we observed x=0, what if x had been 5?")
    observed = pd.DataFrame({"x": [0], "y": [0], "z": [1]})  # Observed values
    try:
        counterfactual = gcm.whatif.counterfactual_samples(
            scm, intervention, observed_data=observed
        )
        print(
            f"  Counterfactual y: {counterfactual['y'].values[0]:.2f}, z: {counterfactual['z'].values[0]:.2f}"
        )
    except Exception as e:
        print(f"  Counterfactual query failed: {e}")
        print("  (May require invertible SCM)")


def explore_conditional_intervention():
    """Explore conditional interventions."""
    print("\n" + "=" * 80)
    print("5. CONDITIONAL INTERVENTION: do(y = f(x))")
    print("=" * 80)

    scm, data = create_simple_scm()

    # Conditional intervention: do(y = 3*x) instead of natural 2*x
    print("\nIntervention: do(y = 3*x) [natural: y=2*x]")
    intervention = {"y": lambda y: y * 1.5}  # Scale y by 1.5 (approximates 3x)
    intervened_samples = gcm.whatif.interventional_samples(
        scm, intervention, num_samples_to_draw=1000
    )

    baseline_samples = gcm.draw_samples(scm, num_samples=1000)

    print(f"\nBaseline y mean: {baseline_samples['y'].mean():.2f}")
    print(f"Intervened y mean: {intervened_samples['y'].mean():.2f}")
    print(f"Intervened z mean: {intervened_samples['z'].mean():.2f}")


def explore_downstream_effects():
    """Explore downstream effects of intervention."""
    print("\n" + "=" * 80)
    print("6. DOWNSTREAM EFFECTS: Identify affected nodes")
    print("=" * 80)

    scm, data = create_diamond_scm()

    # Intervene on x, measure effect on all nodes
    baseline = gcm.draw_samples(scm, num_samples=1000)
    intervention = {"x": lambda x: x + 5}  # Shift x by +5

    intervened = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=1000)

    print("\nIntervention: x → x + 5")
    print("\nEffect sizes (mean difference):")
    for node in ["x", "y", "z", "w"]:
        baseline_mean = baseline[node].mean()
        intervened_mean = intervened[node].mean()
        effect = intervened_mean - baseline_mean
        print(
            f"  {node}: Δ={effect:.2f} (baseline={baseline_mean:.2f}, intervened={intervened_mean:.2f})"
        )


def explore_performance():
    """Test performance of intervention queries."""
    print("\n" + "=" * 80)
    print("7. PERFORMANCE: Query latency")
    print("=" * 80)

    scm, data = create_diamond_scm()

    # Test 1: Single intervention, 1000 samples
    intervention = {"x": lambda x: 5}

    start = time.time()
    samples = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=1000)
    elapsed = time.time() - start
    print(f"\nSingle intervention (1000 samples): {elapsed * 1000:.1f}ms")

    # Test 2: Multiple interventions
    interventions = {"x": lambda x: 5, "y": lambda y: 10}

    start = time.time()
    samples = gcm.whatif.interventional_samples(scm, interventions, num_samples_to_draw=1000)
    elapsed = time.time() - start
    print(f"Multiple interventions (1000 samples): {elapsed * 1000:.1f}ms")

    # Test 3: Large sample size
    start = time.time()
    samples = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=10000)
    elapsed = time.time() - start
    print(f"Single intervention (10000 samples): {elapsed * 1000:.1f}ms")


def explore_error_cases():
    """Test error cases."""
    print("\n" + "=" * 80)
    print("8. ERROR CASES: Invalid interventions")
    print("=" * 80)

    scm, data = create_simple_scm()

    # Invalid node
    print("\nTest 1: Intervention on non-existent node")
    try:
        intervention = {"nonexistent": lambda x: 5}
        samples = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=100)
        print("  ❌ Did not raise error (unexpected)")
    except Exception as e:
        print(f"  ✅ Raised error: {type(e).__name__}")

    # Invalid intervention function
    print("\nTest 2: Invalid intervention function")
    try:
        intervention = {"x": "not a function"}
        samples = gcm.whatif.interventional_samples(scm, intervention, num_samples_to_draw=100)
        print("  ❌ Did not raise error (unexpected)")
    except Exception as e:
        print(f"  ✅ Raised error: {type(e).__name__}")


# ============================================================================
# Main
# ============================================================================


def main():
    """Run all exploration tests."""
    print("\n" + "=" * 80)
    print("DoWhy Intervention Capability Exploration")
    print("=" * 80)

    explore_hard_intervention()
    explore_soft_intervention()
    explore_multiple_interventions()
    explore_counterfactual_vs_interventional()
    explore_conditional_intervention()
    explore_downstream_effects()
    explore_performance()
    explore_error_cases()

    print("\n" + "=" * 80)
    print("Exploration Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
