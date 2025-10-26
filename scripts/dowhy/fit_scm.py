#!/usr/bin/env python3
"""
DoWhy SCM Fitting Subprocess Worker

This script runs in Python 3.11 (.venv-dowhy) and provides SCM fitting
capabilities via JSON stdin/stdout communication.

Usage:
    echo '{"graph": {...}, "traces": {...}}' | .venv-dowhy/bin/python scripts/dowhy/fit_scm.py

Input (stdin JSON):
    {
        "graph": {"nodes": [...], "edges": [...]},
        "traces": {"X": [...], "Y": [...]},
        "config": {"quality": "GOOD", "validate_r2": true, "r2_threshold": 0.7}
    }

Output (stdout JSON):
    {
        "status": "success",
        "scm": {...},
        "validation": {...},
        "metadata": {...}
    }
"""

import json
import sys
import time
import traceback
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from dowhy import gcm
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


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


def serialize_mechanism(mechanism) -> dict[str, Any]:
    """Serialize a DoWhy causal mechanism to JSON-compatible dict."""
    mechanism_type = type(mechanism).__name__

    # Empirical distribution (root nodes)
    if "EmpiricalDistribution" in mechanism_type:
        return {"type": "empirical", "params": None}

    # Additive noise models (non-root nodes)
    if hasattr(mechanism, "prediction_model"):
        model = mechanism.prediction_model
        model_type = type(model).__name__

        # DoWhy wraps sklearn models - unwrap if needed
        inner_model = model
        if hasattr(model, "sklearn_model"):
            inner_model = model.sklearn_model

        # Extract coefficients if available (most regression models)
        params = {"model_type": model_type}
        if hasattr(inner_model, "coef_"):
            params["coefficients"] = inner_model.coef_.tolist()
        if hasattr(inner_model, "intercept_"):
            params["intercept"] = float(inner_model.intercept_)

        # Determine type based on model
        inner_type = type(inner_model).__name__
        if (
            "LinearRegression" in inner_type
            or "Ridge" in inner_type
            or hasattr(inner_model, "coef_")
        ):
            return {"type": "linear", "params": params}

        # Generic sklearn model
        return {"type": model_type.lower(), "params": params}

    # Unknown mechanism type
    return {"type": "unknown", "params": {"class": mechanism_type}}


def compute_r2_per_node(
    causal_model: gcm.StructuralCausalModel, train_data: pd.DataFrame, val_data: pd.DataFrame
) -> dict[str, float]:
    """
    Compute R² for each non-root node on validation data.

    Args:
        causal_model: Fitted SCM
        train_data: Training data (for context)
        val_data: Validation data (for R² computation)

    Returns:
        Dict mapping node names to R² scores
    """
    r2_scores = {}
    graph = causal_model.graph

    for node in graph.nodes():
        # Skip root nodes (no parents, no prediction)
        parents = list(graph.predecessors(node))
        if not parents:
            continue

        # Get mechanism (causal_mechanism is a method, not a dict)
        try:
            mechanism = causal_model.causal_mechanism(node)
        except (KeyError, ValueError):
            continue

        # Get prediction model if it exists
        if hasattr(mechanism, "prediction_model"):
            model = mechanism.prediction_model

            # Prepare validation data
            X_val = val_data[parents].values
            y_val = val_data[node].values

            # Predict
            try:
                y_pred = model.predict(X_val)
                r2 = r2_score(y_val, y_pred)
                r2_scores[node] = float(r2)
            except Exception as e:
                r2_scores[node] = float("nan")

    return r2_scores


def fit_scm(graph: nx.DiGraph, data: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """
    Fit structural causal model using DoWhy.

    Args:
        graph: Causal graph (NetworkX DiGraph)
        data: Execution traces (pandas DataFrame)
        config: Configuration (quality, validation settings)

    Returns:
        Dict with fitted SCM, validation results, and metadata
    """
    start_time = time.time()

    # Parse config
    quality_str = config.get("quality", "GOOD")
    validate_r2 = config.get("validate_r2", True)
    r2_threshold = config.get("r2_threshold", 0.7)
    test_size = config.get("test_size", 0.2)

    # Validate minimum data requirement
    min_samples = 100
    if len(data) < min_samples:
        return {
            "status": "warning",
            "message": f"Only {len(data)} samples (recommended: ≥{min_samples})",
            "scm": None,
            "validation": None,
        }

    # Split data for cross-validation
    train_data, val_data = train_test_split(data, test_size=test_size, random_state=42)

    # Create structural causal model
    causal_model = gcm.StructuralCausalModel(graph)

    # Auto-assign causal mechanisms
    quality = get_assignment_quality(quality_str)
    gcm.auto.assign_causal_mechanisms(causal_model, train_data, quality=quality)

    # Fit mechanisms to data
    gcm.fit(causal_model, train_data)

    # Compute R² on validation data
    r2_scores = compute_r2_per_node(causal_model, train_data, val_data)

    # Validate R² threshold
    valid_r2_scores = [r2 for r2 in r2_scores.values() if not np.isnan(r2)]
    mean_r2 = float(np.mean(valid_r2_scores)) if valid_r2_scores else 0.0
    passed = mean_r2 >= r2_threshold if validate_r2 else True

    # Identify failed nodes
    failed_nodes = [node for node, r2 in r2_scores.items() if r2 < r2_threshold or np.isnan(r2)]

    # Serialize mechanisms
    mechanisms = {}
    for node in graph.nodes():
        try:
            mechanism = causal_model.causal_mechanism(node)
            mechanisms[node] = serialize_mechanism(mechanism)
        except (KeyError, ValueError):
            # Node has no mechanism assigned (shouldn't happen after fitting)
            mechanisms[node] = {"type": "none", "params": None}

    # Prepare output
    fitting_time = time.time() - start_time

    result = {
        "status": "success" if passed else "validation_failed",
        "scm": {
            "graph": {"nodes": list(graph.nodes()), "edges": list(graph.edges())},
            "mechanisms": mechanisms,
        },
        "validation": {
            "r2_scores": r2_scores,
            "mean_r2": mean_r2,
            "passed": passed,
            "threshold": r2_threshold,
            "failed_nodes": failed_nodes if not passed else [],
        },
        "metadata": {
            "fitting_time_ms": int(fitting_time * 1000),
            "num_samples": len(data),
            "num_train": len(train_data),
            "num_val": len(val_data),
            "dowhy_version": gcm.__version__ if hasattr(gcm, "__version__") else "unknown",
            "quality": quality_str,
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
        config = input_data.get("config", {})

        if not graph_data or not traces_data:
            print(
                json.dumps(
                    {"status": "error", "error": "Missing required fields: 'graph' and 'traces'"}
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
        result = fit_scm(graph, data, config)

        # Output result
        print(json.dumps(result, indent=2))

        # Exit code based on status
        if result["status"] in ["success", "warning"]:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        # Catch-all error handling
        error_result = {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
