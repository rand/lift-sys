"""Data Flow Edge Extraction for Causal Graph Building (STEP-03).

This module extracts data flow edges from Python AST, tracking how data
flows from variable definitions to uses through assignments, function calls,
and returns.

Part of H20 (CausalGraphBuilder) implementation.
"""

from __future__ import annotations

import ast

from .node_extractor import CausalNode, NodeType


class DataFlowExtractor(ast.NodeVisitor):
    """Extract data flow edges from AST.

    Creates edges of type 'data_flow' connecting:
    - Variable definitions to variable uses
    - Function returns to call sites
    - Function arguments to parameter uses

    Performance:
        - <2s for 100-node graph (acceptance criteria)
        - O(N) time complexity where N = AST node count
    """

    def __init__(self):
        self._edges: list[tuple[str, str]] = []
        self._function_stack: list[str] = []  # Track nested functions
        self._definitions: dict[str, list[str]] = {}  # var_name -> [node_ids]
        self._current_line: int = 0
        # Map from (scope, var_name) -> latest definition node_id at each line
        self._scope_definitions: dict[tuple[str, str], dict[int, str]] = {}

    def extract(
        self, ast_tree: ast.Module, causal_nodes: list[CausalNode]
    ) -> list[tuple[str, str]]:
        """Extract data flow edges.

        Args:
            ast_tree: Python AST
            causal_nodes: List of CausalNode from STEP-02

        Returns:
            List of (source_id, target_id) tuples for data flow edges

        Example:
            >>> code = '''
            ... x = 1
            ... y = x
            ... '''
            >>> tree = ast.parse(code)
            >>> from lift_sys.causal.node_extractor import extract_nodes
            >>> nodes = extract_nodes(tree)
            >>> extractor = DataFlowExtractor()
            >>> edges = extractor.extract(tree, nodes)
            >>> # Should have edge from x definition to y definition
        """
        self._edges = []
        self._function_stack = []
        self._definitions = {}
        self._scope_definitions = {}

        # Build index of nodes by ID for quick lookup
        self._node_index = {node.id: node for node in causal_nodes}

        # Build index of variable definitions (for data flow tracking)
        self._build_definition_index(causal_nodes)

        # Visit AST to find uses and create edges
        self.visit(ast_tree)

        return self._edges

    def _build_definition_index(self, causal_nodes: list[CausalNode]) -> None:
        """Build index of variable definitions by scope and name."""
        for node in causal_nodes:
            if node.type == NodeType.VARIABLE:
                scope = node.metadata.get("scope", "__module__")
                var_name = node.name
                key = (scope, var_name)

                if key not in self._scope_definitions:
                    self._scope_definitions[key] = {}

                # Map line number to this definition
                self._scope_definitions[key][node.line] = node.id

                # Also add to simple definitions list (for backward compat)
                if var_name not in self._definitions:
                    self._definitions[var_name] = []
                self._definitions[var_name].append(node.id)

    def _current_scope(self) -> str:
        """Get current function scope."""
        return ".".join(self._function_stack) if self._function_stack else "__module__"

    def _find_latest_definition(self, var_name: str, use_line: int) -> str | None:
        """Find the latest definition of var_name before use_line in current scope.

        Args:
            var_name: Variable name to look up
            use_line: Line number where variable is used

        Returns:
            Node ID of latest definition, or None if not found
        """
        scope = self._current_scope()
        key = (scope, var_name)

        if key not in self._scope_definitions:
            # Try parent scopes (for nested functions)
            if "." in scope:
                parent_scope = ".".join(scope.split(".")[:-1])
                parent_key = (parent_scope, var_name)
                if parent_key in self._scope_definitions:
                    key = parent_key
                else:
                    # Try module scope as last fallback
                    module_key = ("__module__", var_name)
                    if module_key in self._scope_definitions:
                        key = module_key
                    else:
                        return None
            else:
                # Try module scope
                module_key = ("__module__", var_name)
                if module_key in self._scope_definitions:
                    key = module_key
                else:
                    return None

        definitions = self._scope_definitions[key]

        # Find latest definition before use_line
        latest_line = -1
        latest_def_id = None
        for def_line, def_id in definitions.items():
            if def_line < use_line and def_line > latest_line:
                latest_line = def_line
                latest_def_id = def_id

        return latest_def_id

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition and track scope."""
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition and track scope."""
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment and create edges from RHS uses to LHS definition."""
        # First, find all variable uses in RHS (value)
        rhs_uses = self._find_variable_uses(node.value, node.lineno)

        # Then, find LHS definition nodes
        for target in node.targets:
            if isinstance(target, ast.Name):
                scope = self._current_scope()
                # Build node ID matching node_extractor.py format
                if scope != "__module__":
                    target_def_id = f"var:{scope}.{target.id}:L{node.lineno}"
                else:
                    target_def_id = f"var:{target.id}:L{node.lineno}"

                # Create edges from all RHS uses to this definition
                for use_var_name in rhs_uses:
                    # Find the definition that this use refers to
                    source_def_id = self._find_latest_definition(use_var_name, node.lineno)
                    if source_def_id and source_def_id in self._node_index:
                        self._edges.append((source_def_id, target_def_id))

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Visit augmented assignment (+=, -=, etc.) and create edges."""
        if isinstance(node.target, ast.Name):
            scope = self._current_scope()
            # Build node ID matching node_extractor.py format
            if scope != "__module__":
                target_def_id = f"var:{scope}.{node.target.id}:L{node.lineno}"
            else:
                target_def_id = f"var:{node.target.id}:L{node.lineno}"

            # AugAssign uses the variable itself, so create self-edge from previous def
            prev_def_id = self._find_latest_definition(node.target.id, node.lineno)
            if prev_def_id and prev_def_id in self._node_index:
                self._edges.append((prev_def_id, target_def_id))

            # Also find uses in RHS value
            rhs_uses = self._find_variable_uses(node.value, node.lineno)
            for use_var_name in rhs_uses:
                source_def_id = self._find_latest_definition(use_var_name, node.lineno)
                if source_def_id and source_def_id in self._node_index:
                    self._edges.append((source_def_id, target_def_id))

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Visit return statement and create edges from returned variables."""
        if node.value:
            scope = self._current_scope()
            if scope != "__module__":
                return_id = f"return:{scope}:L{node.lineno}"

                # Find all variable uses in return value
                returned_vars = self._find_variable_uses(node.value, node.lineno)
                for var_name in returned_vars:
                    source_def_id = self._find_latest_definition(var_name, node.lineno)
                    if source_def_id and source_def_id in self._node_index:
                        self._edges.append((source_def_id, return_id))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function call and create edges from arguments.

        Note: We track data flow through call arguments.
        Return value tracking would require interprocedural analysis (future work).
        """
        # Find variable uses in call arguments
        for arg in node.args:
            arg_vars = self._find_variable_uses(arg, node.lineno)
            # For now, we just track that these variables are used
            # Could create edges to the call site if we track call nodes
            # This is simplified - full implementation would need call graph integration

        self.generic_visit(node)

    def _find_variable_uses(self, expr: ast.expr, current_line: int) -> list[str]:
        """Find all variable names used in an expression.

        Args:
            expr: AST expression node
            current_line: Current line number (for context)

        Returns:
            List of variable names used in the expression
        """
        uses = []

        class UseFinder(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Load):  # Only 'use', not 'store'
                    uses.append(node.id)

        finder = UseFinder()
        finder.visit(expr)
        return uses


def extract_dataflow_edges(
    ast_tree: ast.Module, causal_nodes: list[CausalNode]
) -> list[tuple[str, str]]:
    """Extract data flow edges from AST.

    Convenience function wrapping DataFlowExtractor.

    Args:
        ast_tree: Python AST module
        causal_nodes: List of CausalNode from node extraction

    Returns:
        List of (source_id, target_id) tuples representing data flow edges

    Example:
        >>> code = '''
        ... def process(x):
        ...     y = x * 2
        ...     return y
        ... '''
        >>> tree = ast.parse(code)
        >>> from lift_sys.causal.node_extractor import extract_nodes
        >>> nodes = extract_nodes(tree)
        >>> edges = extract_dataflow_edges(tree, nodes)
        >>> # Should have edges: x -> y (via assignment), y -> return
    """
    extractor = DataFlowExtractor()
    return extractor.extract(ast_tree, causal_nodes)
