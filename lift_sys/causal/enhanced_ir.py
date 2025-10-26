"""EnhancedIR - IR with causal analysis capabilities.

This module provides an enhanced version of IntermediateRepresentation with
causal query methods. Uses lazy evaluation (@cached_property) to avoid overhead
when causal capabilities aren't used.

See docs/planning/WEEK4_DOWHY_INTEGRATION.md for complete design.
"""

import logging
from functools import cached_property
from typing import Any

import networkx as nx

from lift_sys.ir.models import IntermediateRepresentation

from .intervention_engine import InterventionEngine, InterventionResult

logger = logging.getLogger(__name__)


class EnhancedIR:
    """IR with causal query capabilities.

    This class wraps IntermediateRepresentation and adds causal analysis methods:
    - causal_graph: Access to causal DAG
    - causal_model: Access to fitted SCM
    - causal_impact(): Calculate downstream impact
    - causal_intervention(): Execute what-if queries
    - causal_paths(): Find causal paths between nodes

    Lazy Evaluation:
        All causal properties use @cached_property, computed only on first access.
        Zero overhead if causal features aren't used.

    Usage:
        # Create from CausalEnhancer result
        enhanced_ir = EnhancedIR.from_enhancement_result(result)

        # Check if causal available
        if enhanced_ir.has_causal_capabilities:
            # Access causal graph
            graph = enhanced_ir.causal_graph  # Computed on first access
            print(f"Nodes: {list(graph.nodes())}")

            # Query causal impact
            affected = enhanced_ir.causal_impact("function_name")
            print(f"Downstream impact: {affected}")

            # Execute intervention
            result = enhanced_ir.causal_intervention({"var": 5.0})
            print(f"Result: {result.statistics}")

    Error Handling:
        Methods return None or raise CausalUnavailableError if causal
        capabilities aren't available (e.g., DoWhy subprocess failed).
    """

    def __init__(
        self,
        base_ir: IntermediateRepresentation,
        causal_graph: nx.DiGraph | None = None,
        causal_scm: dict | None = None,
        intervention_engine: InterventionEngine | None = None,
        mode: str | None = None,
        metadata: dict | None = None,
    ):
        """Initialize enhanced IR.

        Args:
            base_ir: Base IntermediateRepresentation
            causal_graph: Causal DAG from H20 (None if unavailable)
            causal_scm: Fitted SCM from H21 (None if unavailable)
            intervention_engine: InterventionEngine instance from H22
            mode: "static" or "dynamic" (None if unavailable)
            metadata: Metadata dict with warnings, timings, etc.
        """
        self._base_ir = base_ir
        self._causal_graph = causal_graph
        self._causal_scm = causal_scm
        self._intervention_engine = intervention_engine
        self._mode = mode
        self._metadata = metadata or {}

    @classmethod
    def from_enhancement_result(cls, result: dict) -> "EnhancedIR":
        """Create EnhancedIR from CausalEnhancer.enhance() result.

        Args:
            result: Dict from CausalEnhancer.enhance()

        Returns:
            EnhancedIR instance
        """
        return cls(
            base_ir=result["ir"],
            causal_graph=result.get("causal_graph"),
            causal_scm=result.get("scm"),
            intervention_engine=result.get("intervention_engine"),
            mode=result.get("mode"),
            metadata=result.get("metadata", {}),
        )

    # =========================================================================
    # Base IR delegation (all base IR properties/methods available)
    # =========================================================================

    @property
    def intent(self):
        """Access base IR intent clause."""
        return self._base_ir.intent

    @property
    def signature(self):
        """Access base IR signature clause."""
        return self._base_ir.signature

    @property
    def effects(self):
        """Access base IR effects."""
        return self._base_ir.effects

    @property
    def assertions(self):
        """Access base IR assertions."""
        return self._base_ir.assertions

    @property
    def metadata(self):
        """Access base IR metadata."""
        return self._base_ir.metadata

    @property
    def constraints(self):
        """Access base IR constraints."""
        return self._base_ir.constraints

    def typed_holes(self):
        """Return typed holes from base IR."""
        return self._base_ir.typed_holes()

    def to_dict(self) -> dict:
        """Serialize to dictionary (base IR format).

        Note: Causal data not included in serialization (can be recomputed).
        """
        return self._base_ir.to_dict()

    # =========================================================================
    # Causal capabilities
    # =========================================================================

    @property
    def has_causal_capabilities(self) -> bool:
        """Check if causal analysis is available.

        Returns:
            True if causal graph and SCM are available
        """
        return self._causal_graph is not None and self._causal_scm is not None

    @property
    def causal_mode(self) -> str | None:
        """Get causal analysis mode ("static" or "dynamic").

        Returns:
            Mode string or None if causal unavailable
        """
        return self._mode

    @property
    def causal_warnings(self) -> list[str]:
        """Get causal analysis warnings.

        Returns:
            List of warning strings (empty if no warnings)
        """
        warnings: list[str] = self._metadata.get("warnings", [])
        return warnings

    @cached_property
    def causal_graph(self) -> nx.DiGraph | None:
        """Get causal graph (lazy evaluation).

        Returns:
            NetworkX DiGraph or None if unavailable

        Examples:
            >>> graph = enhanced_ir.causal_graph
            >>> if graph:
            ...     print(f"Nodes: {list(graph.nodes())}")
            ...     print(f"Edges: {list(graph.edges())}")
        """
        if self._causal_graph is None:
            logger.debug("Causal graph not available")
        return self._causal_graph

    @cached_property
    def causal_model(self) -> dict | None:
        """Get fitted structural causal model (lazy evaluation).

        Returns:
            SCM dict or None if unavailable

        Examples:
            >>> scm = enhanced_ir.causal_model
            >>> if scm:
            ...     print(f"Mode: {scm['mode']}")
            ...     print(f"Mechanisms: {len(scm['mechanisms'])}")
        """
        if self._causal_scm is None:
            logger.debug("Causal model not available")
        return self._causal_scm

    def causal_impact(
        self,
        target_node: str,
        normalize: bool = True,
    ) -> dict[str, float] | None:
        """Calculate causal impact on downstream nodes.

        Computes how changes to target_node affect downstream nodes in the
        causal graph (transitive closure with edge weights if available).

        Args:
            target_node: Node to analyze impact of
            normalize: Normalize impact scores to [0, 1] range

        Returns:
            Dict mapping affected_node → impact_score (0.0 to 1.0)
            Returns None if causal capabilities unavailable

        Examples:
            >>> affected = enhanced_ir.causal_impact("validate_input")
            >>> print(affected)
            {'process_data': 0.85, 'generate_output': 0.72, 'write_file': 0.68}

        Note:
            This is a graph-theoretic analysis (not statistical).
            For statistical impact estimation, use causal_intervention().
        """
        if not self.has_causal_capabilities:
            logger.warning("Causal impact unavailable: causal capabilities not initialized")
            return None

        graph = self.causal_graph
        if graph is None or target_node not in graph.nodes():
            logger.warning(f"Node '{target_node}' not in causal graph")
            return None

        # Compute downstream nodes (transitive closure)
        downstream = nx.descendants(graph, target_node)

        if not downstream:
            logger.debug(f"No downstream nodes for '{target_node}'")
            return {}

        # Calculate impact scores (path lengths, inverse distance)
        impact = {}
        for node in downstream:
            # Shortest path length as proxy for impact (closer = more impact)
            try:
                path_length = nx.shortest_path_length(graph, target_node, node)
                # Inverse distance: closer nodes have higher impact
                score = 1.0 / path_length
                impact[node] = score
            except nx.NetworkXNoPath:
                continue

        # Normalize to [0, 1] range
        if normalize and impact:
            max_score = max(impact.values())
            if max_score > 0:
                impact = {k: v / max_score for k, v in impact.items()}

        return impact

    def causal_intervention(
        self,
        interventions: dict[str, Any],
        query_nodes: list[str] | None = None,
        num_samples: int = 1000,
    ) -> InterventionResult | None:
        """Execute causal intervention query (what-if analysis).

        Computes P(Y | do(X=x)) using fitted SCM and DoWhy.

        Args:
            interventions: Dict mapping node → intervention value
                           Example: {"x": 5.0, "y": 10.0}
            query_nodes: Nodes to query (None = all nodes)
            num_samples: Number of samples for intervention distribution

        Returns:
            InterventionResult with samples and statistics
            Returns None if causal capabilities unavailable

        Raises:
            ValueError: If intervention nodes not in graph

        Examples:
            >>> # What if validate_input always returns True?
            >>> result = enhanced_ir.causal_intervention(
            ...     {"validate_input": True},
            ...     query_nodes=["output", "error_count"]
            ... )
            >>> print(result.statistics["output"]["mean"])
            42.5

        Note:
            Requires dynamic mode (with traces). Static mode doesn't support
            precise intervention queries.
        """
        if not self.has_causal_capabilities:
            logger.warning("Causal intervention unavailable: causal capabilities not initialized")
            return None

        if self._intervention_engine is None:
            logger.warning("Intervention engine not available")
            return None

        # Convert dict to intervention spec format
        # Simple format: {"node": value} → hard intervention
        from .intervention_spec import HardIntervention, InterventionSpec, SoftIntervention

        intervention_list: list[HardIntervention | SoftIntervention] = [
            HardIntervention(node=node, value=value) for node, value in interventions.items()
        ]

        spec = InterventionSpec(
            interventions=intervention_list,
            query_nodes=query_nodes,
            num_samples=num_samples,
        )

        # Execute intervention
        if self._causal_scm is None:
            raise ValueError("Cannot perform intervention: SCM not fitted")

        try:
            result = self._intervention_engine.execute(
                scm=self._causal_scm,
                intervention=spec,
                graph=self._causal_graph,
            )
            return result
        except Exception as e:
            logger.error(f"Intervention execution failed: {e}")
            return None

    def causal_paths(
        self,
        source: str,
        target: str,
        max_paths: int = 10,
    ) -> list[list[str]] | None:
        """Find causal paths from source to target.

        Args:
            source: Source node
            target: Target node
            max_paths: Maximum number of paths to return

        Returns:
            List of paths (each path is list of node names)
            Returns None if causal graph unavailable
            Returns [] if no paths exist

        Examples:
            >>> paths = enhanced_ir.causal_paths("input", "output")
            >>> for path in paths:
            ...     print(" → ".join(path))
            input → validate → process → output
            input → process → output
        """
        if self._causal_graph is None:
            logger.warning("Causal paths unavailable: causal graph not initialized")
            return None

        graph = self.causal_graph
        if graph is None:
            return None

        if source not in graph.nodes() or target not in graph.nodes():
            logger.warning(f"Nodes not in graph: source={source}, target={target}")
            return []

        try:
            # Find all simple paths (acyclic)
            paths = list(nx.all_simple_paths(graph, source, target))[:max_paths]
            return paths
        except nx.NetworkXNoPath:
            return []
        except Exception as e:
            logger.error(f"Path finding failed: {e}")
            return []

    def __repr__(self) -> str:
        """String representation."""
        causal_status = "with causal" if self.has_causal_capabilities else "without causal"
        return f"EnhancedIR({self.signature.name}, {causal_status})"
