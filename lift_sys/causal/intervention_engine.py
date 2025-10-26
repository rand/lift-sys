"""H22: InterventionEngine - Causal Intervention Execution.

This module executes interventions and counterfactual queries on fitted SCMs.

See specs/typed-holes-dowhy.md for complete H22 specification.
"""

import logging
from typing import Any

import networkx as nx

from .dowhy_client import DoWhyClient, DoWhySubprocessError
from .intervention_spec import (
    HardIntervention,
    InterventionResult,
    InterventionSpec,
    SoftIntervention,
    deserialize_intervention,
    serialize_intervention,
)

logger = logging.getLogger(__name__)


class InterventionError(Exception):
    """Base exception for intervention errors."""

    pass


class ParseError(InterventionError):
    """Raised when intervention specification parsing fails."""

    pass


class ValidationError(InterventionError):
    """Raised when intervention specification validation fails."""

    pass


class InterventionEngine:
    """Executes causal interventions and counterfactual queries.

    Type Signature (H22):
        execute: (SCM, InterventionSpec) → InterventionResult

    Constraints:
        - Must support do(X=value) interventions
        - Must support soft interventions (shifts, scales)
        - Must handle multiple interventions simultaneously
        - Query latency <100ms for single intervention
        - Must validate interventions against graph

    Implementation Steps (Week 3):
        - STEP-10: Intervention specification parser ✅
        - STEP-11: Counterfactual query execution ⏳
        - STEP-12: Result serialization ⏳
        - STEP-13: Integration tests ⏳
    """

    def __init__(self):
        """Initialize intervention engine."""
        self.scm_cache: dict[str, Any] = {}  # Cache fitted SCMs for repeated queries

    def parse_intervention(
        self,
        spec: str | dict | HardIntervention | SoftIntervention | InterventionSpec,
    ) -> InterventionSpec:
        """Parse intervention specification from various formats (STEP-10).

        Args:
            spec: Intervention in various formats:
                  - String: "do(x=5)" or "do(x=x+2)"
                  - Dict: {"type": "hard", "node": "x", "value": 5}
                  - HardIntervention/SoftIntervention object
                  - InterventionSpec object (pass-through)

        Returns:
            Parsed and validated InterventionSpec

        Raises:
            ParseError: If parsing fails
            ValidationError: If specification is invalid

        Examples:
            >>> engine.parse_intervention("do(x=5)")
            InterventionSpec(interventions=[HardIntervention(node='x', value=5)], ...)

            >>> engine.parse_intervention({"node": "x", "value": 5})
            InterventionSpec(interventions=[HardIntervention(node='x', value=5)], ...)
        """
        # Pass-through if already InterventionSpec
        if isinstance(spec, InterventionSpec):
            return spec

        # Wrap single intervention objects
        if isinstance(spec, (HardIntervention, SoftIntervention)):
            return InterventionSpec(interventions=[spec])

        # Parse string format
        if isinstance(spec, str):
            return self._parse_string_intervention(spec)

        # Parse dict format
        if isinstance(spec, dict):
            return self._parse_dict_intervention(spec)

        raise ParseError(f"Unsupported intervention format: {type(spec)}")

    def _parse_string_intervention(self, spec: str) -> InterventionSpec:
        """Parse intervention from string format.

        Supported formats:
            - "do(x=5)" - Hard intervention
            - "do(x=x+2)" - Soft intervention (shift)
            - "do(x=x*2)" - Soft intervention (scale)
            - "do(x=5, y=10)" - Multiple interventions

        Args:
            spec: Intervention string

        Returns:
            InterventionSpec

        Raises:
            ParseError: If string format is invalid
        """
        spec = spec.strip()

        # Check for do(...) wrapper
        if not spec.startswith("do(") or not spec.endswith(")"):
            raise ParseError(f"Intervention must be in format 'do(...)': {spec}")

        # Extract inner content
        inner = spec[3:-1].strip()  # Remove "do(" and ")"

        # Split by comma for multiple interventions
        parts = [p.strip() for p in inner.split(",")]

        interventions = []
        for part in parts:
            if "=" not in part:
                raise ParseError(f"Invalid intervention syntax (missing '='): {part}")

            node, value_expr = part.split("=", 1)
            node = node.strip()
            value_expr = value_expr.strip()

            # Parse value expression
            intervention = self._parse_value_expression(node, value_expr)
            interventions.append(intervention)

        return InterventionSpec(interventions=interventions)

    def _parse_value_expression(
        self, node: str, value_expr: str
    ) -> HardIntervention | SoftIntervention:
        """Parse value expression to determine intervention type.

        Args:
            node: Node being intervened on
            value_expr: Value expression (e.g., "5", "x+2", "x*1.5")

        Returns:
            HardIntervention or SoftIntervention

        Raises:
            ParseError: If expression is invalid
        """
        # Check if expression contains node variable (soft intervention)
        if node in value_expr:
            # Soft intervention: do(x=x+2) or do(x=x*1.5)

            # Shift: x+k or x-k
            if "+" in value_expr:
                parts = value_expr.split("+")
                if len(parts) == 2 and parts[0].strip() == node:
                    try:
                        param = float(parts[1].strip())
                        return SoftIntervention(node=node, transform="shift", param=param)
                    except ValueError as e:
                        raise ParseError(f"Invalid shift parameter: {parts[1]}") from e

            if "-" in value_expr and not value_expr.startswith("-"):
                parts = value_expr.split("-")
                if len(parts) == 2 and parts[0].strip() == node:
                    try:
                        param = -float(parts[1].strip())  # Negative shift
                        return SoftIntervention(node=node, transform="shift", param=param)
                    except ValueError as e:
                        raise ParseError(f"Invalid shift parameter: {parts[1]}") from e

            # Scale: x*k or x/k
            if "*" in value_expr:
                parts = value_expr.split("*")
                if len(parts) == 2 and parts[0].strip() == node:
                    try:
                        param = float(parts[1].strip())
                        return SoftIntervention(node=node, transform="scale", param=param)
                    except ValueError as e:
                        raise ParseError(f"Invalid scale parameter: {parts[1]}") from e

            if "/" in value_expr:
                parts = value_expr.split("/")
                if len(parts) == 2 and parts[0].strip() == node:
                    try:
                        param = 1.0 / float(parts[1].strip())  # Convert division to multiplication
                        return SoftIntervention(node=node, transform="scale", param=param)
                    except (ValueError, ZeroDivisionError) as e:
                        raise ParseError(f"Invalid scale parameter: {parts[1]}") from e

            # Custom expression (future)
            return SoftIntervention(node=node, transform="custom", custom_expr=value_expr)

        else:
            # Hard intervention: do(x=5)
            try:
                value = float(value_expr)
                return HardIntervention(node=node, value=value)
            except ValueError as e:
                raise ParseError(f"Invalid hard intervention value: {value_expr}") from e

    def _parse_dict_intervention(self, spec: dict) -> InterventionSpec:
        """Parse intervention from dict format.

        Args:
            spec: Dict with intervention specification

        Returns:
            InterventionSpec

        Raises:
            ParseError: If dict format is invalid
        """
        # Check if it's a complete InterventionSpec dict
        if "interventions" in spec:
            interventions = [deserialize_intervention(i) for i in spec["interventions"]]
            query_nodes = spec.get("query_nodes")
            num_samples = spec.get("num_samples", 1000)
            return InterventionSpec(
                interventions=interventions,
                query_nodes=query_nodes,
                num_samples=num_samples,
            )

        # Single intervention dict
        intervention = deserialize_intervention(spec)
        return InterventionSpec(interventions=[intervention])

    def validate_intervention(self, spec: InterventionSpec, graph: nx.DiGraph) -> None:
        """Validate intervention specification against causal graph.

        Args:
            spec: Intervention specification
            graph: Causal graph

        Raises:
            ValidationError: If intervention is invalid

        Checks:
            - All intervention nodes exist in graph
            - No circular interventions (node depends on itself)
            - Query nodes exist in graph (if specified)
        """
        graph_nodes = set(graph.nodes())

        # Validate intervention nodes
        for intervention in spec.interventions:
            node = intervention.node

            if node not in graph_nodes:
                raise ValidationError(
                    f"Intervention node '{node}' not in causal graph. "
                    f"Available nodes: {sorted(graph_nodes)}"
                )

        # Validate query nodes
        if spec.query_nodes is not None:
            for query_node in spec.query_nodes:
                if query_node not in graph_nodes:
                    raise ValidationError(
                        f"Query node '{query_node}' not in causal graph. "
                        f"Available nodes: {sorted(graph_nodes)}"
                    )

    def execute(
        self,
        scm: dict,
        intervention: str | dict | InterventionSpec,
        graph: nx.DiGraph,
    ) -> InterventionResult:
        """Execute intervention on fitted SCM (STEP-11).

        Args:
            scm: Fitted SCM from SCMFitter (STEP-08)
            intervention: Intervention specification (various formats)
            graph: Causal graph

        Returns:
            InterventionResult with samples and statistics

        Raises:
            InterventionError: If execution fails
            ValidationError: If intervention is invalid

        Performance:
            - <100ms for single intervention (requirement)
        """
        # Parse intervention
        spec = self.parse_intervention(intervention)

        # Validate
        self.validate_intervention(spec, graph)

        # Extract traces from SCM (required for refitting in subprocess)
        traces = scm.get("traces")
        if traces is None:
            raise InterventionError(
                "SCM dict must contain 'traces' for intervention queries. "
                "This is automatically included when using SCMFitter.fit() in dynamic mode."
            )

        # Serialize interventions to DoWhy format
        interventions_list = [serialize_intervention(i) for i in spec.interventions]

        # Execute query via DoWhy subprocess
        try:
            client = DoWhyClient(timeout=60.0)
        except FileNotFoundError as e:
            raise InterventionError(
                f"DoWhy subprocess not available: {e}\n"
                f"Make sure .venv-dowhy exists and scripts/dowhy/query_fitted_scm.py is present"
            ) from e

        try:
            result = client.query_scm(
                graph=graph,
                traces=traces,
                interventions=interventions_list,
                query_nodes=spec.query_nodes,
                num_samples=spec.num_samples,
                quality="GOOD",
            )
        except DoWhySubprocessError as e:
            raise InterventionError(f"DoWhy intervention query failed: {e}") from e
        except Exception as e:
            raise InterventionError(f"Unexpected error during intervention query: {e}") from e

        # Check status
        if result.get("status") != "success":
            error_msg = result.get("error", "Unknown error")
            raise InterventionError(f"Intervention query failed: {error_msg}")

        # Convert to InterventionResult
        return InterventionResult(
            samples=result["samples"],
            statistics=result["statistics"],
            metadata=result["metadata"],
            intervention_spec=spec,
        )
