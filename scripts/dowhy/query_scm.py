#!/usr/bin/env python3
"""
DoWhy SCM Query Subprocess Worker

This script runs in Python 3.11 (.venv-dowhy) and provides intervention
and counterfactual query capabilities via JSON stdin/stdout communication.

Usage:
    echo '{"scm": {...}, "intervention": {...}}' | .venv-dowhy/bin/python scripts/dowhy/query_scm.py

Input (stdin JSON):
    {
        "scm": {"graph": {...}, "mechanisms": {...}},
        "intervention": {
            "type": "interventional",
            "interventions": [
                {"type": "hard", "node": "x", "value": 5},
                {"type": "soft", "node": "y", "transform": "shift", "param": 2.0}
            ],
            "query_nodes": ["z", "w"],
            "num_samples": 1000
        }
    }

Output (stdout JSON):
    {
        "status": "success",
        "samples": {"z": [...], "w": [...]},
        "statistics": {"z": {"mean": ..., "std": ...}, ...},
        "metadata": {...}
    }
"""

import json
import sys
import time
import traceback
from typing import Any

import networkx as nx
import pandas as pd
from dowhy import gcm


def parse_input() -> dict[str, Any]:
    """Parse JSON input from stdin."""
    try:
        data = json.load(sys.stdin)
        return data
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON input: {e}"}


def reconstruct_scm(scm_data: dict[str, Any]) -> gcm.StructuralCausalModel:
    """Reconstruct fitted SCM from serialized data.

    WARNING: This is a placeholder. Full SCM reconstruction requires
    persisting mechanism parameters and re-instantiating models.

    For STEP-11, we'll use a simpler approach:
    1. Fit SCM from scratch using stored graph + traces
    2. Or serialize/deserialize full model using pickle/cloudpickle

    Args:
        scm_data: Serialized SCM from fit_scm.py

    Returns:
        Reconstructed StructuralCausalModel

    Raises:
        NotImplementedError: Full reconstruction not yet implemented
    """
    # Extract graph
    graph_data = scm_data.get("graph", {})
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    # For now, raise error - full reconstruction needs more work
    # In production, we'd need to:
    # 1. Deserialize mechanism parameters (coefficients, etc.)
    # 2. Re-instantiate sklearn models with those parameters
    # 3. Wrap them in DoWhy causal mechanisms
    # 4. Assign to SCM

    raise NotImplementedError(
        "Full SCM reconstruction not yet implemented. "
        "For STEP-11, pass graph + traces and re-fit, "
        "or use pickle/cloudpickle for serialization."
    )


def parse_intervention_lambda(intervention: dict[str, Any]) -> tuple[str, Any]:
    """Parse intervention dict into (node, lambda_function) pair.

    Args:
        intervention: Intervention specification dict

    Returns:
        (node_name, lambda_function) tuple

    Example:
        >>> parse_intervention_lambda({"type": "hard", "node": "x", "value": 5})
        ("x", <lambda>)

        >>> parse_intervention_lambda({"type": "soft", "node": "y", "transform": "shift", "param": 2.0})
        ("y", <lambda>)
    """
    node = intervention["node"]
    intervention_type = intervention["type"]

    if intervention_type == "hard":
        # Hard intervention: do(X=value)
        value = intervention["value"]
        return (node, lambda x: value)

    elif intervention_type == "soft":
        # Soft intervention: do(X=f(X))
        transform = intervention["transform"]
        param = intervention.get("param")

        if transform == "shift":
            return (node, lambda x: x + param)
        elif transform == "scale":
            return (node, lambda x: x * param)
        elif transform == "custom":
            # Custom expression (future)
            expr = intervention.get("custom_expr")
            # WARNING: eval() is dangerous, use with caution
            # For now, raise error
            raise NotImplementedError("Custom interventions not yet supported")
        else:
            raise ValueError(f"Unknown soft intervention transform: {transform}")

    else:
        raise ValueError(f"Unknown intervention type: {intervention_type}")


def compute_statistics(samples: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute summary statistics for intervention results.

    Args:
        samples: DataFrame with intervention samples

    Returns:
        Dict mapping node → {mean, std, q05, q50, q95}
    """
    statistics = {}

    for col in samples.columns:
        values = samples[col]
        statistics[col] = {
            "mean": float(values.mean()),
            "std": float(values.std()),
            "q05": float(values.quantile(0.05)),
            "q50": float(values.quantile(0.50)),  # median
            "q95": float(values.quantile(0.95)),
            "min": float(values.min()),
            "max": float(values.max()),
        }

    return statistics


def execute_interventional_query(
    causal_model: gcm.StructuralCausalModel,
    intervention_spec: dict[str, Any],
) -> dict[str, Any]:
    """Execute interventional query: P(Y | do(X=x)).

    Args:
        causal_model: Fitted SCM
        intervention_spec: Intervention specification

    Returns:
        Dict with samples, statistics, and metadata
    """
    start_time = time.time()

    # Parse interventions
    interventions_list = intervention_spec.get("interventions", [])
    interventions_dict = {}

    for intervention in interventions_list:
        node, lambda_func = parse_intervention_lambda(intervention)
        interventions_dict[node] = lambda_func

    # Parse query parameters
    num_samples = intervention_spec.get("num_samples", 1000)
    query_nodes = intervention_spec.get("query_nodes")  # None = all nodes

    # Execute intervention
    samples = gcm.whatif.interventional_samples(
        causal_model, interventions_dict, num_samples_to_draw=num_samples
    )

    # Filter to query nodes if specified
    if query_nodes is not None:
        samples = samples[query_nodes]

    # Compute statistics
    statistics = compute_statistics(samples)

    # Prepare result
    query_time = time.time() - start_time

    result = {
        "status": "success",
        "query_type": "interventional",
        "samples": {col: samples[col].tolist() for col in samples.columns},
        "statistics": statistics,
        "metadata": {
            "query_time_ms": int(query_time * 1000),
            "num_samples": num_samples,
            "num_interventions": len(interventions_list),
            "query_nodes": query_nodes or list(samples.columns),
        },
    }

    return result


def execute_observational_query(
    causal_model: gcm.StructuralCausalModel,
    query_spec: dict[str, Any],
) -> dict[str, Any]:
    """Execute observational query (no intervention).

    Args:
        causal_model: Fitted SCM
        query_spec: Query specification

    Returns:
        Dict with samples, statistics, and metadata
    """
    start_time = time.time()

    # Parse query parameters
    num_samples = query_spec.get("num_samples", 1000)
    query_nodes = query_spec.get("query_nodes")  # None = all nodes

    # Draw observational samples
    samples = gcm.draw_samples(causal_model, num_samples=num_samples)

    # Filter to query nodes if specified
    if query_nodes is not None:
        samples = samples[query_nodes]

    # Compute statistics
    statistics = compute_statistics(samples)

    # Prepare result
    query_time = time.time() - start_time

    result = {
        "status": "success",
        "query_type": "observational",
        "samples": {col: samples[col].tolist() for col in samples.columns},
        "statistics": statistics,
        "metadata": {
            "query_time_ms": int(query_time * 1000),
            "num_samples": num_samples,
            "query_nodes": query_nodes or list(samples.columns),
        },
    }

    return result


def execute_counterfactual_query(
    causal_model: gcm.StructuralCausalModel,
    query_spec: dict[str, Any],
) -> dict[str, Any]:
    """Execute counterfactual query: Given observed X, what if X had been x'?

    Args:
        causal_model: Fitted SCM (must be invertible)
        query_spec: Query specification with observed data

    Returns:
        Dict with counterfactual samples, statistics, and metadata
    """
    start_time = time.time()

    # Parse interventions
    interventions_list = query_spec.get("interventions", [])
    interventions_dict = {}

    for intervention in interventions_list:
        node, lambda_func = parse_intervention_lambda(intervention)
        interventions_dict[node] = lambda_func

    # Parse observed data
    observed_data_dict = query_spec.get("observed_data")
    if not observed_data_dict:
        raise ValueError("Counterfactual queries require observed_data")

    observed_data = pd.DataFrame(observed_data_dict)

    # Execute counterfactual query
    try:
        samples = gcm.whatif.counterfactual_samples(
            causal_model, interventions_dict, observed_data=observed_data
        )
    except Exception as e:
        # Likely requires invertible SCM
        return {
            "status": "error",
            "error": f"Counterfactual query failed: {e}",
            "details": "May require InvertibleStructuralCausalModel",
        }

    # Compute statistics
    statistics = compute_statistics(samples)

    # Prepare result
    query_time = time.time() - start_time

    result = {
        "status": "success",
        "query_type": "counterfactual",
        "samples": {col: samples[col].tolist() for col in samples.columns},
        "statistics": statistics,
        "metadata": {
            "query_time_ms": int(query_time * 1000),
            "num_observed": len(observed_data),
            "num_interventions": len(interventions_list),
        },
    }

    return result


def main():
    """Main entry point for subprocess worker."""
    try:
        # Parse input
        input_data = parse_input()

        if "error" in input_data:
            print(json.dumps({"status": "error", "error": input_data["error"]}))
            sys.exit(1)

        # Extract components
        scm_data = input_data.get("scm")
        intervention_spec = input_data.get("intervention")

        if not scm_data or not intervention_spec:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": "Missing required fields: 'scm' and 'intervention'",
                    }
                )
            )
            sys.exit(1)

        # Reconstruct SCM
        # NOTE: For STEP-11, we may need to pass graph + traces and re-fit
        # Or use pickle/cloudpickle for full serialization
        try:
            causal_model = reconstruct_scm(scm_data)
        except NotImplementedError as e:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": str(e),
                        "workaround": "Pass graph + traces to fit_scm.py first, "
                        "then use returned SCM reference",
                    }
                )
            )
            sys.exit(1)

        # Determine query type
        query_type = intervention_spec.get("type", "interventional")

        # Execute query
        if query_type == "interventional":
            result = execute_interventional_query(causal_model, intervention_spec)
        elif query_type == "observational":
            result = execute_observational_query(causal_model, intervention_spec)
        elif query_type == "counterfactual":
            result = execute_counterfactual_query(causal_model, intervention_spec)
        else:
            print(json.dumps({"status": "error", "error": f"Unknown query type: {query_type}"}))
            sys.exit(1)

        # Output result
        print(json.dumps(result, indent=2))
        sys.exit(0)

    except Exception as e:
        # Catch-all error handling
        error_result = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
