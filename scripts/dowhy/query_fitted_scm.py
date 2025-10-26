#!/usr/bin/env python3
"""
DoWhy SCM Query Worker (Integrated Fit + Query)

This script combines SCM fitting and querying in a single subprocess.
Instead of trying to serialize/deserialize fitted models, we:
1. Fit the SCM from graph + traces
2. Execute interventions on the fitted model
3. Return results

Usage:
    echo '{"graph": {...}, "traces": {...}, "intervention": {...}}' | \
        .venv-dowhy/bin/python scripts/dowhy/query_fitted_scm.py

Input (stdin JSON):
    {
        "graph": {"nodes": [...], "edges": [...]},
        "traces": {"X": [...], "Y": [...]},
        "intervention": {
            "type": "interventional",
            "interventions": [
                {"type": "hard", "node": "x", "value": 5}
            ],
            "query_nodes": ["y", "z"],
            "num_samples": 1000
        },
        "config": {"quality": "GOOD"}
    }

Output (stdout JSON):
    {
        "status": "success",
        "query_type": "interventional",
        "samples": {"y": [...], "z": [...]},
        "statistics": {"y": {"mean": ..., "std": ...}, ...},
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


def reconstruct_graph(graph_data: dict[str, Any]) -> nx.DiGraph:
    """Reconstruct NetworkX DiGraph from JSON representation."""
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)

    # Validate DAG
    if not nx.is_directed_acyclic_graph(graph):
        raise ValueError("Graph must be a Directed Acyclic Graph (DAG)")

    return graph


def create_dataframe(traces_data: dict[str, list[float]]) -> pd.DataFrame:
    """Create pandas DataFrame from traces."""
    # Validate all columns have same length
    lengths = {k: len(v) for k, v in traces_data.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"Trace columns have different lengths: {lengths}")

    return pd.DataFrame(traces_data)


def get_assignment_quality(quality_str: str) -> gcm.auto.AssignmentQuality:
    """Convert quality string to DoWhy AssignmentQuality enum."""
    quality_map = {
        "GOOD": gcm.auto.AssignmentQuality.GOOD,
        "BETTER": gcm.auto.AssignmentQuality.BETTER,
        "BEST": gcm.auto.AssignmentQuality.BEST,
    }
    return quality_map.get(quality_str, gcm.auto.AssignmentQuality.GOOD)


def fit_scm(
    graph: nx.DiGraph, data: pd.DataFrame, quality: str = "GOOD"
) -> gcm.StructuralCausalModel:
    """Fit structural causal model using DoWhy.

    Args:
        graph: Causal graph (NetworkX DiGraph)
        data: Execution traces (pandas DataFrame)
        quality: Model quality ("GOOD", "BETTER", "BEST")

    Returns:
        Fitted StructuralCausalModel
    """
    # Create structural causal model
    causal_model = gcm.StructuralCausalModel(graph)

    # Auto-assign causal mechanisms
    quality_enum = get_assignment_quality(quality)
    gcm.auto.assign_causal_mechanisms(causal_model, data, quality=quality_enum)

    # Fit mechanisms to data
    gcm.fit(causal_model, data)

    return causal_model


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


def main():
    """Main entry point for subprocess worker."""
    try:
        # Parse input
        input_data = parse_input()

        if "error" in input_data:
            print(json.dumps({"status": "error", "error": input_data["error"]}))
            sys.exit(1)

        # Extract components
        graph_data = input_data.get("graph")
        traces_data = input_data.get("traces")
        intervention_spec = input_data.get("intervention")
        config = input_data.get("config", {})

        if not graph_data or not traces_data or not intervention_spec:
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": "Missing required fields: 'graph', 'traces', and 'intervention'",
                    }
                )
            )
            sys.exit(1)

        # Reconstruct graph and data
        graph = reconstruct_graph(graph_data)
        data = create_dataframe(traces_data)

        # Validate graph nodes match data columns
        data_columns = set(data.columns)
        graph_nodes = set(graph.nodes())

        if graph_nodes != data_columns:
            missing_in_data = graph_nodes - data_columns
            missing_in_graph = data_columns - graph_nodes
            print(
                json.dumps(
                    {
                        "status": "error",
                        "error": "Graph nodes and data columns do not match",
                        "details": {
                            "missing_in_data": list(missing_in_data),
                            "missing_in_graph": list(missing_in_graph),
                        },
                    }
                )
            )
            sys.exit(1)

        # Fit SCM
        quality = config.get("quality", "GOOD")
        fit_start = time.time()
        causal_model = fit_scm(graph, data, quality=quality)
        fit_time = time.time() - fit_start

        # Determine query type
        query_type = intervention_spec.get("type", "interventional")

        # Execute query
        if query_type == "interventional":
            result = execute_interventional_query(causal_model, intervention_spec)
        elif query_type == "observational":
            result = execute_observational_query(causal_model, intervention_spec)
        else:
            print(json.dumps({"status": "error", "error": f"Unknown query type: {query_type}"}))
            sys.exit(1)

        # Add fitting metadata
        result["metadata"]["fit_time_ms"] = int(fit_time * 1000)
        result["metadata"]["num_training_samples"] = len(data)

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
