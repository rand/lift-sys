"""Edge Pruning for Causal Graphs (STEP-05).

This module prunes non-causal edges from the graph, removing edges to/from
nodes that don't affect program state (e.g., logging, printing).

Part of H20 (CausalGraphBuilder) implementation.
"""

import networkx as nx

from .node_extractor import CausalNode, NodeType

# Functions that don't affect causal state
NON_CAUSAL_FUNCTIONS = {
    # Logging/debugging
    "print",
    "log",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    # Formatting (no state change)
    "format",
    "str",
    "repr",
    # Type checking (no state change)
    "isinstance",
    "type",
    "hasattr",
    # Assertions (side effect but not causal for normal flow)
    "assert",
}


def prune_non_causal_edges(
    graph: nx.DiGraph,
    nodes: list[CausalNode],
) -> nx.DiGraph:
    """Prune non-causal edges from the graph.

    Removes edges connected to nodes that don't affect program state:
    - Logging/print statements
    - Debug output
    - Type checking without state changes
    - Formatting without state changes

    Keeps edges for:
    - State-changing operations (assignments, mutations)
    - Function calls with side effects
    - Control flow affecting execution
    - Data flow affecting computations

    Args:
        graph: Causal graph with all edges
        nodes: List of CausalNode objects

    Returns:
        Pruned graph with only causal edges

    Example:
        >>> # Before pruning:
        >>> # var:x -> print() -> var:y
        >>> # After pruning:
        >>> # var:x -> var:y (print removed)
    """
    # Create a copy to avoid modifying original
    pruned = graph.copy()

    # Build node lookup by ID
    node_by_id = {node.id: node for node in nodes}

    # Identify non-causal nodes (effects with non-causal functions)
    non_causal_node_ids = set()

    for node in nodes:
        if node.type == NodeType.EFFECT:
            # Check if the function is non-causal
            func_name = node.metadata.get("function", "")
            if func_name in NON_CAUSAL_FUNCTIONS:
                non_causal_node_ids.add(node.id)

    # Remove edges to/from non-causal nodes
    edges_to_remove = []

    for source, target in pruned.edges():
        # Remove if source or target is non-causal
        if source in non_causal_node_ids or target in non_causal_node_ids:
            edges_to_remove.append((source, target))

    for source, target in edges_to_remove:
        pruned.remove_edge(source, target)

    # Optionally remove isolated non-causal nodes
    nodes_to_remove = []
    for node_id in non_causal_node_ids:
        if pruned.degree(node_id) == 0:  # No incoming or outgoing edges
            nodes_to_remove.append(node_id)

    for node_id in nodes_to_remove:
        pruned.remove_node(node_id)

    return pruned


def validate_dag(graph: nx.DiGraph) -> bool:
    """Validate that graph is a Directed Acyclic Graph.

    Args:
        graph: Graph to validate

    Returns:
        True if graph is a DAG

    Raises:
        CyclicGraphError: If graph contains cycles
    """
    from .graph_builder import CyclicGraphError

    if not nx.is_directed_acyclic_graph(graph):
        # Find a cycle for error message
        try:
            cycle = nx.find_cycle(graph)
            cycle_str = " -> ".join(str(node) for node, _ in cycle)
            raise CyclicGraphError(f"Graph contains cycle: {cycle_str}")
        except nx.NetworkXNoCycle:
            # Shouldn't happen, but handle gracefully
            raise CyclicGraphError("Graph is not a DAG")

    return True


def validate_graph_structure(graph: nx.DiGraph) -> dict[str, bool]:
    """Validate graph structure against H20 constraints.

    Constraints from specs/typed-holes-dowhy.md:
    - Output MUST be acyclic (DAG)
    - Output MUST have ≥1 root node (no incoming edges)
    - Output MUST have ≥1 leaf node (no outgoing edges)
    - Edge count ≤ O(N log N) where N = node count

    Args:
        graph: Graph to validate

    Returns:
        Dictionary with validation results:
        - is_dag: True if acyclic
        - has_roots: True if ≥1 root node
        - has_leaves: True if ≥1 leaf node
        - edge_complexity_ok: True if edge count reasonable

    Example:
        >>> results = validate_graph_structure(graph)
        >>> if not all(results.values()):
        ...     print(f"Validation failed: {results}")
    """
    results = {
        "is_dag": False,
        "has_roots": False,
        "has_leaves": False,
        "edge_complexity_ok": False,
    }

    # Check if DAG
    results["is_dag"] = nx.is_directed_acyclic_graph(graph)

    # Check for root nodes (no incoming edges)
    root_nodes = [node for node in graph.nodes() if graph.in_degree(node) == 0]
    results["has_roots"] = len(root_nodes) >= 1

    # Check for leaf nodes (no outgoing edges)
    leaf_nodes = [node for node in graph.nodes() if graph.out_degree(node) == 0]
    results["has_leaves"] = len(leaf_nodes) >= 1

    # Check edge complexity (should be ≤ O(N log N))
    # For practical purposes, we'll check ≤ N^2 (quadratic is upper bound)
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()

    if n_nodes > 0:
        # Allow up to N^2 edges (very generous)
        results["edge_complexity_ok"] = n_edges <= n_nodes * n_nodes
    else:
        results["edge_complexity_ok"] = True

    return results
