"""Intervention Specification Data Classes.

This module defines data structures for specifying causal interventions
for use with DoWhy SCMs via subprocess interface.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class InterventionType(str, Enum):
    """Type of causal intervention."""

    # Hard intervention: do(X=value) - set node to constant
    HARD = "hard"

    # Soft intervention: do(X=f(X)) - transform distribution
    SOFT = "soft"

    # Observational: no intervention, just query distribution
    OBSERVATIONAL = "observational"


@dataclass
class HardIntervention:
    """Hard intervention: do(X=value).

    Sets a node to a constant value, breaking all incoming edges.

    Example:
        >>> HardIntervention(node="x", value=5.0)
        # Represents: do(x := 5)
    """

    node: str
    value: float | int


@dataclass
class SoftIntervention:
    """Soft intervention: do(X=f(X)).

    Transforms a node's distribution using a function.

    Example:
        >>> SoftIntervention(node="x", transform="shift", param=2.0)
        # Represents: do(x := x + 2)

        >>> SoftIntervention(node="x", transform="scale", param=1.5)
        # Represents: do(x := x * 1.5)
    """

    node: str
    transform: str  # "shift", "scale", "custom"
    param: float | None = None
    custom_expr: str | None = None  # For custom transforms (future)


@dataclass
class InterventionSpec:
    """Complete intervention specification.

    Supports:
    - Single or multiple interventions
    - Hard and soft interventions
    - Query nodes (which nodes to observe after intervention)

    Example:
        >>> spec = InterventionSpec(
        ...     interventions=[
        ...         HardIntervention(node="x", value=5),
        ...         SoftIntervention(node="y", transform="shift", param=2.0)
        ...     ],
        ...     query_nodes=["z", "w"],
        ...     num_samples=1000
        ... )
    """

    interventions: list[HardIntervention | SoftIntervention]
    query_nodes: list[str] | None = None  # None = query all nodes
    num_samples: int = 1000


@dataclass
class InterventionResult:
    """Result of intervention query.

    Contains:
    - Samples from interventional distribution
    - Summary statistics (mean, std, quantiles)
    - Metadata (timing, sample size, etc.)

    Example:
        >>> result.samples
        {"x": [5.0, 5.0, ...], "y": [10.1, 10.2, ...], "z": [15.3, 15.1, ...]}

        >>> result.statistics
        {"x": {"mean": 5.0, "std": 0.0}, "y": {"mean": 10.15, "std": 0.1}, ...}
    """

    samples: dict[str, list[float]]  # node → sample values
    statistics: dict[str, dict[str, float]]  # node → {mean, std, q05, q50, q95}
    metadata: dict[str, Any]  # timing, sample size, etc.
    intervention_spec: InterventionSpec


def serialize_intervention(intervention: HardIntervention | SoftIntervention) -> dict[str, Any]:
    """Serialize intervention for JSON transport.

    Args:
        intervention: Intervention to serialize

    Returns:
        JSON-compatible dict representation

    Example:
        >>> serialize_intervention(HardIntervention(node="x", value=5))
        {"type": "hard", "node": "x", "value": 5}

        >>> serialize_intervention(SoftIntervention(node="y", transform="shift", param=2.0))
        {"type": "soft", "node": "y", "transform": "shift", "param": 2.0}
    """
    if isinstance(intervention, HardIntervention):
        return {"type": "hard", "node": intervention.node, "value": intervention.value}

    elif isinstance(intervention, SoftIntervention):
        result: dict[str, Any] = {
            "type": "soft",
            "node": intervention.node,
            "transform": intervention.transform,
        }
        if intervention.param is not None:
            result["param"] = intervention.param
        if intervention.custom_expr is not None:
            result["custom_expr"] = intervention.custom_expr
        return result

    else:
        raise ValueError(f"Unknown intervention type: {type(intervention)}")


def deserialize_intervention(data: dict[str, Any]) -> HardIntervention | SoftIntervention:
    """Deserialize intervention from JSON dict.

    Args:
        data: JSON dict from serialize_intervention()

    Returns:
        Intervention object

    Raises:
        ValueError: If data format is invalid
    """
    intervention_type = data.get("type")

    if intervention_type == "hard":
        return HardIntervention(node=data["node"], value=data["value"])

    elif intervention_type == "soft":
        return SoftIntervention(
            node=data["node"],
            transform=data["transform"],
            param=data.get("param"),
            custom_expr=data.get("custom_expr"),
        )

    else:
        raise ValueError(f"Unknown intervention type: {intervention_type}")


def intervention_to_lambda_str(intervention: HardIntervention | SoftIntervention) -> str:
    """Convert intervention to Python lambda string for DoWhy.

    Args:
        intervention: Intervention to convert

    Returns:
        Python lambda expression as string

    Example:
        >>> intervention_to_lambda_str(HardIntervention(node="x", value=5))
        "lambda x: 5"

        >>> intervention_to_lambda_str(SoftIntervention(node="y", transform="shift", param=2.0))
        "lambda y: y + 2.0"
    """
    node = intervention.node

    if isinstance(intervention, HardIntervention):
        return f"lambda {node}: {intervention.value}"

    elif isinstance(intervention, SoftIntervention):
        if intervention.transform == "shift":
            return f"lambda {node}: {node} + {intervention.param}"
        elif intervention.transform == "scale":
            return f"lambda {node}: {node} * {intervention.param}"
        elif intervention.transform == "custom" and intervention.custom_expr:
            # Custom expression should already be valid Python
            return f"lambda {node}: {intervention.custom_expr}"
        else:
            raise ValueError(f"Unknown soft intervention transform: {intervention.transform}")

    else:
        raise ValueError(f"Unknown intervention type: {type(intervention)}")


# ============================================================================
# STEP-12: InterventionSpec and InterventionResult Serialization
# ============================================================================


def serialize_intervention_spec(spec: InterventionSpec) -> dict[str, Any]:
    """Serialize InterventionSpec to JSON-compatible dict (STEP-12).

    Args:
        spec: InterventionSpec to serialize

    Returns:
        JSON-compatible dict representation

    Example:
        >>> spec = InterventionSpec(
        ...     interventions=[HardIntervention(node="x", value=5)],
        ...     query_nodes=["y"],
        ...     num_samples=1000
        ... )
        >>> serialize_intervention_spec(spec)
        {
            "interventions": [{"type": "hard", "node": "x", "value": 5}],
            "query_nodes": ["y"],
            "num_samples": 1000
        }
    """
    return {
        "interventions": [serialize_intervention(i) for i in spec.interventions],
        "query_nodes": spec.query_nodes,
        "num_samples": spec.num_samples,
    }


def deserialize_intervention_spec(data: dict[str, Any]) -> InterventionSpec:
    """Deserialize InterventionSpec from JSON dict (STEP-12).

    Args:
        data: JSON dict from serialize_intervention_spec()

    Returns:
        InterventionSpec object

    Raises:
        ValueError: If data format is invalid
    """
    interventions = [deserialize_intervention(i) for i in data["interventions"]]
    return InterventionSpec(
        interventions=interventions,
        query_nodes=data.get("query_nodes"),
        num_samples=data.get("num_samples", 1000),
    )


def serialize_intervention_result(result: InterventionResult) -> dict[str, Any]:
    """Serialize InterventionResult to JSON-compatible dict (STEP-12).

    Args:
        result: InterventionResult to serialize

    Returns:
        JSON-compatible dict representation

    Example:
        >>> result = InterventionResult(
        ...     samples={"x": [5.0, 5.0], "y": [10.1, 10.2]},
        ...     statistics={"x": {"mean": 5.0, "std": 0.0}, "y": {"mean": 10.15, "std": 0.05}},
        ...     metadata={"query_time_ms": 5, "num_samples": 1000},
        ...     intervention_spec=InterventionSpec(interventions=[...])
        ... )
        >>> serialize_intervention_result(result)
        {
            "samples": {"x": [5.0, 5.0], "y": [10.1, 10.2]},
            "statistics": {...},
            "metadata": {...},
            "intervention_spec": {...}
        }
    """
    return {
        "samples": result.samples,
        "statistics": result.statistics,
        "metadata": result.metadata,
        "intervention_spec": serialize_intervention_spec(result.intervention_spec),
    }


def deserialize_intervention_result(data: dict[str, Any]) -> InterventionResult:
    """Deserialize InterventionResult from JSON dict (STEP-12).

    Args:
        data: JSON dict from serialize_intervention_result()

    Returns:
        InterventionResult object

    Raises:
        ValueError: If data format is invalid
    """
    intervention_spec = deserialize_intervention_spec(data["intervention_spec"])

    return InterventionResult(
        samples=data["samples"],
        statistics=data["statistics"],
        metadata=data["metadata"],
        intervention_spec=intervention_spec,
    )
