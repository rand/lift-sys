"""AST Control Flow Edge Extraction (STEP-04).

This module extracts control flow edges from Python AST that show how
conditionals and loops affect execution paths.

Part of H20 (CausalGraphBuilder) implementation.
"""

import ast

from .node_extractor import CausalNode


class ControlFlowExtractor(ast.NodeVisitor):
    """Extract control flow edges from Python AST.

    Creates edges of type 'control_flow' connecting:
    - Conditions to branches they control
    - Loop conditions to loop bodies
    - Try/except/finally flow

    Usage:
        extractor = ControlFlowExtractor()
        edges = extractor.extract(ast_tree, causal_nodes)
    """

    def __init__(self):
        self.edges: list[tuple[str, str]] = []
        self._nodes_by_line: dict[int, list[CausalNode]] = {}
        self._function_stack: list[str] = []  # Track current function scope

    def extract(self, tree: ast.Module, causal_nodes: list[CausalNode]) -> list[tuple[str, str]]:
        """Extract control flow edges from AST.

        Args:
            tree: Python AST module
            causal_nodes: List of CausalNode from STEP-02

        Returns:
            List of (source_id, target_id) tuples for control flow edges

        Performance:
            - <2s for 100-node graph (acceptance criteria)
        """
        self.edges = []
        self._nodes_by_line = {}
        self._function_stack = []

        # Index nodes by line number for efficient lookup
        for node in causal_nodes:
            if node.line not in self._nodes_by_line:
                self._nodes_by_line[node.line] = []
            self._nodes_by_line[node.line].append(node)

        # Visit AST to extract control flow
        self.visit(tree)

        return self.edges

    def _current_scope(self) -> str:
        """Get current function scope."""
        return ".".join(self._function_stack) if self._function_stack else "__module__"

    def _get_nodes_at_line(self, lineno: int) -> list[CausalNode]:
        """Get all nodes at a specific line number."""
        return self._nodes_by_line.get(lineno, [])

    def _get_nodes_in_range(self, start: int, end: int | None) -> list[CausalNode]:
        """Get all nodes in a line range (inclusive).

        Args:
            start: Starting line number
            end: Ending line number (if None, uses start)
        """
        nodes = []
        end_line = end if end is not None else start
        for line in range(start, end_line + 1):
            nodes.extend(self._get_nodes_at_line(line))
        return nodes

    def _add_edge(self, source_id: str, target_id: str) -> None:
        """Add a control flow edge if not duplicate."""
        edge = (source_id, target_id)
        if edge not in self.edges:
            self.edges.append(edge)

    def _extract_condition_nodes(self, test: ast.expr) -> list[CausalNode]:
        """Extract nodes involved in a conditional test expression.

        Args:
            test: AST expression node (the condition)

        Returns:
            List of CausalNode that are referenced in the condition
        """
        # Find all Name nodes in the test (variable references)
        condition_vars = []

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name) -> None:
                condition_vars.append(node.id)

        NameCollector().visit(test)

        # Get nodes at the test line that match these variables
        test_line = getattr(test, "lineno", 0)
        nodes_at_line = self._get_nodes_at_line(test_line)

        # Also check previous lines for variable definitions
        scope = self._current_scope()
        condition_nodes = []

        for var_name in condition_vars:
            # Look for the most recent definition of this variable
            for line in range(test_line, 0, -1):
                for node in self._get_nodes_at_line(line):
                    if node.name == var_name and node.metadata.get("scope") == scope:
                        condition_nodes.append(node)
                        break
                if condition_nodes and condition_nodes[-1].name == var_name:
                    break  # Found this variable, move to next

        return condition_nodes

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Track function scope for control flow analysis."""
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Track async function scope for control flow analysis."""
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_If(self, node: ast.If) -> None:
        """Extract control flow edges for if/elif/else statements.

        Creates edges showing conditional execution of branches.
        Strategy: Link nodes in if-body to nodes in else-body to show
        they are mutually exclusive control paths.
        """
        # Get the line range for the if body
        if_body_start = node.body[0].lineno if node.body else node.lineno + 1
        if_body_end = node.body[-1].end_lineno if node.body else if_body_start

        # Get nodes in the if body
        if_body_nodes = self._get_nodes_in_range(if_body_start, if_body_end)

        # Try to get nodes in condition for linking
        condition_nodes = self._extract_condition_nodes(node.test)

        # Create edges from condition variables to if body nodes
        if condition_nodes:
            for cond_node in condition_nodes:
                for body_node in if_body_nodes:
                    if cond_node.id != body_node.id:
                        self._add_edge(cond_node.id, body_node.id)
        elif if_body_nodes:
            # No condition nodes - look for nodes before the if statement
            # and link them to if-body to show conditional execution
            nodes_before_if = []
            for line in range(node.lineno - 1, 0, -1):
                nodes_at_line = self._get_nodes_at_line(line)
                # Find nodes in same scope
                scope = self._current_scope()
                for n in nodes_at_line:
                    if n.metadata.get("scope") == scope:
                        nodes_before_if.append(n)
                        break
                if nodes_before_if:
                    break

            if nodes_before_if:
                # Link most recent node before if to if-body
                for body_node in if_body_nodes[:1]:  # Just first body node
                    if nodes_before_if[0].id != body_node.id:
                        self._add_edge(nodes_before_if[0].id, body_node.id)
            elif len(if_body_nodes) > 1:
                # No previous nodes - link body nodes sequentially
                for i in range(len(if_body_nodes) - 1):
                    if if_body_nodes[i].id != if_body_nodes[i + 1].id:
                        self._add_edge(if_body_nodes[i].id, if_body_nodes[i + 1].id)

        # Handle else/elif
        if node.orelse:
            else_start = node.orelse[0].lineno
            else_end = node.orelse[-1].end_lineno if node.orelse else else_start

            # If orelse is another If (elif), recursively handle it
            if isinstance(node.orelse[0], ast.If):
                # For elif, connect if-body to elif condition variables
                elif_condition_nodes = self._extract_condition_nodes(node.orelse[0].test)
                if elif_condition_nodes and if_body_nodes:
                    # Link first if-body node to elif condition (showing alternate path)
                    for if_node in if_body_nodes[:1]:  # Just first node to avoid explosion
                        for elif_cond in elif_condition_nodes[:1]:
                            if if_node.id != elif_cond.id:
                                self._add_edge(if_node.id, elif_cond.id)
            else:
                # It's an else block - link to show alternate path
                else_nodes = self._get_nodes_in_range(else_start, else_end)

                if condition_nodes:
                    # Link condition to else block
                    for cond_node in condition_nodes:
                        for else_node in else_nodes:
                            if cond_node.id != else_node.id:
                                self._add_edge(cond_node.id, else_node.id)
                elif if_body_nodes and else_nodes:
                    # No condition nodes found, link if and else bodies to show mutual exclusion
                    for if_node in if_body_nodes[:1]:
                        for else_node in else_nodes[:1]:
                            if if_node.id != else_node.id:
                                self._add_edge(if_node.id, else_node.id)

        # Continue visiting children
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Extract control flow edges for while loops.

        Creates edges from:
        - Loop condition to loop body (if condition nodes found)
        - Or link body nodes in sequence to show repeated execution
        """
        # Get nodes involved in the condition
        condition_nodes = self._extract_condition_nodes(node.test)

        # Get the line range for the loop body
        body_start = node.body[0].lineno if node.body else node.lineno + 1
        body_end = node.body[-1].end_lineno if node.body else body_start

        # Get nodes in the loop body
        body_nodes = self._get_nodes_in_range(body_start, body_end)

        # Create edges from condition to loop body
        if condition_nodes:
            for cond_node in condition_nodes:
                for body_node in body_nodes:
                    if cond_node.id != body_node.id:
                        self._add_edge(cond_node.id, body_node.id)
        elif body_nodes:
            # No condition nodes - create internal loop structure
            # Link consecutive nodes to show execution flow
            for i in range(len(body_nodes) - 1):
                if body_nodes[i].id != body_nodes[i + 1].id:
                    self._add_edge(body_nodes[i].id, body_nodes[i + 1].id)

        # Handle else clause (executed when loop completes without break)
        if node.orelse:
            else_start = node.orelse[0].lineno
            else_end = node.orelse[-1].end_lineno if node.orelse else else_start
            else_nodes = self._get_nodes_in_range(else_start, else_end)

            if condition_nodes:
                for cond_node in condition_nodes:
                    for else_node in else_nodes:
                        if cond_node.id != else_node.id:
                            self._add_edge(cond_node.id, else_node.id)
            elif body_nodes and else_nodes:
                # Link last body node to else clause
                for else_node in else_nodes[:1]:
                    if body_nodes[-1].id != else_node.id:
                        self._add_edge(body_nodes[-1].id, else_node.id)

        # Continue visiting children
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Extract control flow edges for for loops.

        Creates edges from:
        - Iterator expression to loop body (if iterator nodes found)
        - Or link body nodes in sequence to show iteration
        """
        # Get the iterator expression line
        iter_line = node.iter.lineno if hasattr(node.iter, "lineno") else node.lineno
        iter_nodes = self._get_nodes_at_line(iter_line)

        # Get the line range for the loop body
        body_start = node.body[0].lineno if node.body else node.lineno + 1
        body_end = node.body[-1].end_lineno if node.body else body_start

        # Get nodes in the loop body
        body_nodes = self._get_nodes_in_range(body_start, body_end)

        # Create edges from iterator to loop body
        if iter_nodes:
            for iter_node in iter_nodes:
                for body_node in body_nodes:
                    if iter_node.id != body_node.id:
                        self._add_edge(iter_node.id, body_node.id)
        elif body_nodes:
            # No iterator nodes - look for nodes before loop
            nodes_before_loop = []
            for line in range(node.lineno - 1, 0, -1):
                nodes_at_line = self._get_nodes_at_line(line)
                scope = self._current_scope()
                for n in nodes_at_line:
                    if n.metadata.get("scope") == scope:
                        nodes_before_loop.append(n)
                        break
                if nodes_before_loop:
                    break

            if nodes_before_loop:
                # Link most recent node before loop to loop body
                for body_node in body_nodes[:1]:
                    if nodes_before_loop[0].id != body_node.id:
                        self._add_edge(nodes_before_loop[0].id, body_node.id)
            elif len(body_nodes) > 1:
                # No previous nodes - link body nodes in sequence
                for i in range(len(body_nodes) - 1):
                    if body_nodes[i].id != body_nodes[i + 1].id:
                        self._add_edge(body_nodes[i].id, body_nodes[i + 1].id)

        # Handle else clause
        if node.orelse:
            else_start = node.orelse[0].lineno
            else_end = node.orelse[-1].end_lineno if node.orelse else else_start
            else_nodes = self._get_nodes_in_range(else_start, else_end)

            if iter_nodes:
                for iter_node in iter_nodes:
                    for else_node in else_nodes:
                        if iter_node.id != else_node.id:
                            self._add_edge(iter_node.id, else_node.id)
            elif body_nodes and else_nodes:
                # Link last body node to else clause
                for else_node in else_nodes[:1]:
                    if body_nodes[-1].id != else_node.id:
                        self._add_edge(body_nodes[-1].id, else_node.id)
            elif else_nodes:
                # No body or iter nodes - look for nodes before loop
                nodes_before = []
                for line in range(node.lineno - 1, 0, -1):
                    nodes_at_line = self._get_nodes_at_line(line)
                    scope = self._current_scope()
                    for n in nodes_at_line:
                        if n.metadata.get("scope") == scope:
                            nodes_before.append(n)
                            break
                    if nodes_before:
                        break

                if nodes_before:
                    # Link node before loop to else clause
                    for else_node in else_nodes[:1]:
                        if nodes_before[0].id != else_node.id:
                            self._add_edge(nodes_before[0].id, else_node.id)
                elif len(else_nodes) > 1:
                    # No nodes before - link else nodes sequentially
                    for i in range(len(else_nodes) - 1):
                        if else_nodes[i].id != else_nodes[i + 1].id:
                            self._add_edge(else_nodes[i].id, else_nodes[i + 1].id)

        # Continue visiting children
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Extract control flow edges for try/except/finally blocks.

        Creates edges showing the flow through exception handling.
        """
        # Get try body nodes
        try_start = node.body[0].lineno if node.body else node.lineno + 1
        try_end = node.body[-1].end_lineno if node.body else try_start
        try_nodes = self._get_nodes_in_range(try_start, try_end)

        # For each except handler
        for handler in node.handlers:
            except_start = handler.body[0].lineno if handler.body else handler.lineno + 1
            except_end = handler.body[-1].end_lineno if handler.body else except_start
            except_nodes = self._get_nodes_in_range(except_start, except_end)

            # Create edges from try to except (potential flow on exception)
            for try_node in try_nodes:
                for except_node in except_nodes:
                    if try_node.id != except_node.id:
                        self._add_edge(try_node.id, except_node.id)

        # Handle else clause (executed if no exception)
        if node.orelse:
            else_start = node.orelse[0].lineno
            else_end = node.orelse[-1].end_lineno if node.orelse else else_start
            else_nodes = self._get_nodes_in_range(else_start, else_end)

            # Edges from try to else (normal flow)
            for try_node in try_nodes:
                for else_node in else_nodes:
                    if try_node.id != else_node.id:
                        self._add_edge(try_node.id, else_node.id)

        # Handle finally clause (always executed)
        if node.finalbody:
            finally_start = node.finalbody[0].lineno
            finally_end = node.finalbody[-1].end_lineno if node.finalbody else finally_start
            finally_nodes = self._get_nodes_in_range(finally_start, finally_end)

            # Edges from try to finally
            for try_node in try_nodes:
                for finally_node in finally_nodes:
                    if try_node.id != finally_node.id:
                        self._add_edge(try_node.id, finally_node.id)

            # Edges from except handlers to finally
            for handler in node.handlers:
                except_start = handler.body[0].lineno if handler.body else handler.lineno + 1
                except_end = handler.body[-1].end_lineno if handler.body else except_start
                except_nodes = self._get_nodes_in_range(except_start, except_end)

                for except_node in except_nodes:
                    for finally_node in finally_nodes:
                        if except_node.id != finally_node.id:
                            self._add_edge(except_node.id, finally_node.id)

        # Continue visiting children
        self.generic_visit(node)


def extract_controlflow_edges(
    ast_tree: ast.Module, causal_nodes: list[CausalNode]
) -> list[tuple[str, str]]:
    """Extract control flow edges from AST.

    Convenience function wrapping ControlFlowExtractor.

    Args:
        ast_tree: Python AST module
        causal_nodes: List of CausalNode from node extraction

    Returns:
        List of (source_id, target_id) tuples representing control flow

    Example:
        >>> code = '''
        ... def check(x):
        ...     if x > 0:
        ...         result = x
        ...     else:
        ...         result = -x
        ...     return result
        ... '''
        >>> tree = ast.parse(code)
        >>> nodes = extract_nodes(tree)
        >>> edges = extract_controlflow_edges(tree, nodes)
        >>> # Edges connect condition (x) to result assignments
    """
    extractor = ControlFlowExtractor()
    return extractor.extract(ast_tree, causal_nodes)
