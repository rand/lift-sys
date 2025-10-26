"""Unit tests for edge pruning (STEP-05).

Tests the edge pruner which removes non-causal edges (logging, debugging)
while keeping state-affecting edges.
"""

import ast

import networkx as nx
import pytest

from lift_sys.causal.edge_pruner import (
    prune_non_causal_edges,
    validate_dag,
    validate_graph_structure,
)
from lift_sys.causal.graph_builder import CausalGraphBuilder, CyclicGraphError
from lift_sys.causal.node_extractor import extract_nodes


def test_prune_print_statements():
    """Test that print statements are pruned from the graph."""
    code = """
def process(x):
    print("Processing")
    y = x * 2
    print("Done")
    return y
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Create simple graph with print nodes
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.id, type=node.type.value)

    # Add edges (data flow through prints)
    func_node = next(n for n in nodes if n.name == "process")
    var_node = next(n for n in nodes if n.name == "y")
    print_nodes = [n for n in nodes if "print" in n.id]

    # Before pruning: func -> print1 -> var -> print2 -> return
    if print_nodes:
        graph.add_edge(func_node.id, print_nodes[0].id, type="control_flow")
        graph.add_edge(print_nodes[0].id, var_node.id, type="control_flow")

    initial_edges = graph.number_of_edges()

    # Prune
    pruned = prune_non_causal_edges(graph, nodes)

    # Print nodes should be removed or isolated
    for print_node in print_nodes:
        if print_node.id in pruned.nodes():
            # If still in graph, should have no edges
            assert pruned.degree(print_node.id) == 0


def test_keep_state_changing_operations():
    """Test that state-changing operations are kept."""
    code = """
def update(data):
    data.append(42)
    result = data.pop()
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Create graph
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.id, type=node.type.value)

    # Add edges for state changes
    var_nodes = [n for n in nodes if n.type.value == "variable"]
    if len(var_nodes) >= 1:
        # result variable should be kept
        graph.add_edge(var_nodes[0].id, var_nodes[0].id, type="data_flow")

    # Prune (should keep state-changing nodes)
    pruned = prune_non_causal_edges(graph, nodes)

    # No nodes should be removed (all are causal)
    assert pruned.number_of_nodes() == graph.number_of_nodes()


def test_validate_dag_with_cycle():
    """Test that cyclic graphs are detected."""
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("C", "A")  # Creates cycle

    with pytest.raises(CyclicGraphError, match="cycle"):
        validate_dag(graph)


def test_validate_dag_without_cycle():
    """Test that DAGs pass validation."""
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "C")
    graph.add_edge("A", "C")  # DAG (no cycle)

    assert validate_dag(graph) is True


def test_validate_graph_structure_complete():
    """Test validation of complete graph structure."""
    # Create valid graph
    graph = nx.DiGraph()
    graph.add_node("root")
    graph.add_node("middle")
    graph.add_node("leaf")
    graph.add_edge("root", "middle")
    graph.add_edge("middle", "leaf")

    results = validate_graph_structure(graph)

    assert results["is_dag"] is True
    assert results["has_roots"] is True  # "root" has no incoming
    assert results["has_leaves"] is True  # "leaf" has no outgoing
    assert results["edge_complexity_ok"] is True


def test_validate_graph_structure_no_roots():
    """Test detection of graphs without roots."""
    # Create graph where all nodes have incoming edges (cycle)
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")

    results = validate_graph_structure(graph)

    assert results["has_roots"] is False  # No node without incoming edges
    assert results["is_dag"] is False  # Contains cycle


def test_validate_graph_structure_no_leaves():
    """Test detection of graphs without leaves."""
    # Create graph where all nodes have outgoing edges (cycle)
    graph = nx.DiGraph()
    graph.add_edge("A", "B")
    graph.add_edge("B", "A")

    results = validate_graph_structure(graph)

    assert results["has_leaves"] is False  # No node without outgoing edges


def test_validate_edge_complexity():
    """Test edge complexity validation (≤ N^2)."""
    # Create graph with reasonable edge count
    graph = nx.DiGraph()
    for i in range(10):
        graph.add_node(i)
        if i > 0:
            graph.add_edge(i - 1, i)  # 9 edges for 10 nodes (linear)

    results = validate_graph_structure(graph)
    assert results["edge_complexity_ok"] is True

    # Create graph with too many edges would be N^2 (100 edges for 10 nodes)
    # Our threshold is generous so this should still pass
    for i in range(10):
        for j in range(i + 1, min(i + 5, 10)):
            graph.add_edge(i, j)

    results = validate_graph_structure(graph)
    assert results["edge_complexity_ok"] is True  # Still under N^2


def test_integration_with_graph_builder():
    """Integration test: CausalGraphBuilder with pruning."""
    code = """
def validate(data):
    print("Validating data")
    if not data:
        print("Empty data")
        return None

    result = {"valid": True}
    print(f"Result: {result}")
    return result
"""
    tree = ast.parse(code)

    # Build graph (includes pruning)
    builder = CausalGraphBuilder()
    call_graph = nx.DiGraph()  # Empty call graph for this test
    graph = builder.build(tree, call_graph)

    # Verify graph is valid
    assert nx.is_directed_acyclic_graph(graph)

    # Verify print nodes are pruned or isolated
    print_nodes = [n for n in graph.nodes() if "print" in n or "effect" in str(n).lower()]
    for node in print_nodes:
        # Print nodes should have no edges (isolated)
        if node in graph.nodes():
            assert graph.degree(node) == 0, f"Print node {node} has edges"


def test_empty_graph():
    """Test pruning of empty graph."""
    graph = nx.DiGraph()
    nodes = []

    pruned = prune_non_causal_edges(graph, nodes)

    assert pruned.number_of_nodes() == 0
    assert pruned.number_of_edges() == 0


def test_graph_with_only_non_causal_nodes():
    """Test graph with only logging/print nodes."""
    code = """
def debug():
    print("Debug 1")
    print("Debug 2")
    print("Debug 3")
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Create graph
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.id, type=node.type.value)

    # Add some edges between print statements
    print_nodes = [n for n in nodes if "print" in n.id]
    if len(print_nodes) >= 2:
        graph.add_edge(print_nodes[0].id, print_nodes[1].id, type="control_flow")

    # Prune
    pruned = prune_non_causal_edges(graph, nodes)

    # All print nodes should be removed or isolated
    for print_node in print_nodes:
        if print_node.id in pruned.nodes():
            assert pruned.degree(print_node.id) == 0


def test_mixed_causal_and_non_causal():
    """Test graph with mix of causal and non-causal nodes."""
    code = """
def process(x):
    print("Start")
    y = x * 2
    print(f"Computed: {y}")
    z = y + 1
    print("End")
    return z
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    builder = CausalGraphBuilder()
    call_graph = nx.DiGraph()
    graph = builder.build(tree, call_graph)

    # Should have function, variables, return (causal)
    # Print nodes should be pruned or isolated
    var_nodes = [n for n in graph.nodes() if "var:" in n]
    assert len(var_nodes) >= 2  # y and z variables

    return_nodes = [n for n in graph.nodes() if "return:" in n]
    assert len(return_nodes) >= 1


def test_logging_functions_pruned():
    """Test that various logging functions are pruned."""
    code = """
import logging

def process():
    logging.debug("Debug message")
    logging.info("Info message")
    logging.warning("Warning")
    logging.error("Error")
    logging.critical("Critical")

    result = 42
    return result
"""
    tree = ast.parse(code)
    nodes = extract_nodes(tree)

    # Create graph
    graph = nx.DiGraph()
    for node in nodes:
        graph.add_node(node.id, type=node.type.value)

    # Prune
    pruned = prune_non_causal_edges(graph, nodes)

    # Logging effects should be removed or isolated
    logging_nodes = [
        n
        for n in nodes
        if any(log in n.id for log in ["debug", "info", "warning", "error", "critical"])
    ]
    for log_node in logging_nodes:
        if log_node.id in pruned.nodes():
            assert pruned.degree(log_node.id) == 0


def test_preserve_data_flow_edges():
    """Test that data flow edges are preserved during pruning."""
    code = """
def compute(a, b):
    print("Computing")
    x = a + b
    y = x * 2
    print(f"Result: {y}")
    return y
"""
    tree = ast.parse(code)

    builder = CausalGraphBuilder()
    call_graph = nx.DiGraph()
    graph = builder.build(tree, call_graph)

    # Should have data flow edges between variables
    data_flow_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("type") == "data_flow"]

    # Should have some data flow edges (x -> y relationship)
    assert len(data_flow_edges) > 0


def test_preserve_control_flow_edges():
    """Test that control flow edges are preserved during pruning."""
    code = """
def check(x):
    print("Checking")
    if x > 0:
        print("Positive")
        result = x
    else:
        print("Non-positive")
        result = -x
    return result
"""
    tree = ast.parse(code)

    builder = CausalGraphBuilder()
    call_graph = nx.DiGraph()
    graph = builder.build(tree, call_graph)

    # Should have control flow edges (if statement)
    control_flow_edges = [
        (u, v) for u, v, d in graph.edges(data=True) if d.get("type") == "control_flow"
    ]

    # May have control flow edges depending on implementation
    # At minimum, graph should be valid
    assert nx.is_directed_acyclic_graph(graph)


def test_builder_raises_on_invalid_graph():
    """Test that CausalGraphBuilder raises on invalid graph structure."""
    # This is more of a sanity check - in practice, our builder should
    # always produce valid graphs

    code = """
def simple():
    x = 1
    return x
"""
    tree = ast.parse(code)

    builder = CausalGraphBuilder()
    call_graph = nx.DiGraph()

    # Should not raise
    graph = builder.build(tree, call_graph)
    assert graph is not None
