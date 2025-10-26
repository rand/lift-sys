"""H20: CausalGraphBuilder - AST to Causal DAG Conversion.

This module implements conversion of Python AST and call graphs into
causal Directed Acyclic Graphs (DAGs) suitable for DoWhy analysis.

See specs/typed-holes-dowhy.md for complete H20 specification.
"""

import ast

import networkx as nx

from .controlflow_extractor import extract_controlflow_edges
from .node_extractor import extract_nodes


class GraphBuildError(Exception):
    """Base exception for graph building errors."""

    pass


class CyclicGraphError(GraphBuildError):
    """Raised when resulting graph would be cyclic."""

    pass


class CausalGraphBuilder:
    """Converts code structure to causal DAG.

    Type Signature (H20):
        build: (AST, DiGraph, Optional[DiGraph]) → DiGraph

    Constraints:
        - Output MUST be acyclic (DAG)
        - Output MUST have ≥1 root node (no incoming edges)
        - Output MUST have ≥1 leaf node (no outgoing edges)
        - Edge count ≤ O(N log N) where N = node count
        - Must complete in <1s for 100-node input

    Quality Constraints:
        - Edge precision (vs manual review): ≥90%
        - Edge recall (vs manual review): ≥85%

    Performance:
        - Time complexity: O(N log N)
        - Space complexity: O(N + E)

    Implementation Steps (Week 1):
        - STEP-02: Extract nodes (functions, variables, returns)
        - STEP-03: Extract data flow edges
        - STEP-04: Extract control flow edges
        - STEP-05: Prune non-causal edges (exclude logging)
    """

    def build(
        self,
        ast_tree: ast.Module,
        call_graph: nx.DiGraph,
        control_flow: nx.DiGraph | None = None,
    ) -> nx.DiGraph:
        """Build causal graph from code structure.

        Args:
            ast_tree: Python AST from reverse mode
            call_graph: Function call graph
            control_flow: Optional control flow graph

        Returns:
            Causal DAG with typed nodes and edges

        Raises:
            ValueError: If input graph is invalid
            GraphBuildError: If construction fails
            CyclicGraphError: If result would be cyclic

        Node Attributes:
            type: 'function' | 'variable' | 'return' | 'effect'

        Edge Attributes:
            type: 'data_flow' | 'control_flow' | 'call'
        """
        # Initialize graph
        graph = nx.DiGraph()

        # STEP-02: Extract nodes from AST (✅ implemented)
        nodes = extract_nodes(ast_tree)
        for node in nodes:
            graph.add_node(
                node.id,
                name=node.name,
                type=node.type.value,
                line=node.line,
                **node.metadata,
            )

        # STEP-03: Extract data flow edges (⏳ next)
        # TODO: Implement data flow analysis

        # STEP-04: Extract control flow edges (✅ implemented)
        control_edges = extract_controlflow_edges(ast_tree, nodes)
        for source_id, target_id in control_edges:
            graph.add_edge(source_id, target_id, type="control_flow")

        # STEP-05: Prune non-causal edges (⏳ pending STEP-03/04)
        # TODO: Implement edge pruning

        return graph
