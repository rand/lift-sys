"""AST Node Extraction for Causal Graph Building (STEP-02).

This module extracts nodes from Python AST that are relevant for causal
analysis: functions, variables, returns, and side effects.

Part of H20 (CausalGraphBuilder) implementation.
"""

import ast
from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeType(Enum):
    """Types of nodes in causal graph."""

    FUNCTION = "function"
    VARIABLE = "variable"
    RETURN = "return"
    EFFECT = "effect"  # Side effects (print, file I/O, etc.)


@dataclass(frozen=True)
class CausalNode:
    """A node in the causal graph.

    Attributes:
        id: Unique identifier (e.g., "func:process_data", "var:x")
        name: Human-readable name
        type: NodeType (function, variable, return, effect)
        line: Line number in source code
        metadata: Additional information (AST node type, signature, etc.)
    """

    id: str
    name: str
    type: NodeType
    line: int
    metadata: dict[str, Any]


class NodeExtractor(ast.NodeVisitor):
    """Extract causal nodes from Python AST.

    Usage:
        extractor = NodeExtractor()
        nodes = extractor.extract(ast_tree)
    """

    def __init__(self):
        self.nodes: list[CausalNode] = []
        self._function_stack: list[str] = []  # Track nested functions
        self._node_ids: set[str] = set()  # Prevent duplicates

    def extract(self, tree: ast.Module) -> list[CausalNode]:
        """Extract all relevant nodes from AST.

        Args:
            tree: Python AST module

        Returns:
            List of CausalNode objects

        Performance:
            - <100ms for 100-node AST (acceptance criteria)
        """
        self.nodes = []
        self._function_stack = []
        self._node_ids = set()
        self.visit(tree)
        return self.nodes

    def _add_node(self, node: CausalNode) -> None:
        """Add node if not duplicate."""
        if node.id not in self._node_ids:
            self.nodes.append(node)
            self._node_ids.add(node.id)

    def _current_scope(self) -> str:
        """Get current function scope."""
        return ".".join(self._function_stack) if self._function_stack else "__module__"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function definition as node."""
        scope = self._current_scope()
        func_id = f"func:{scope}.{node.name}" if scope != "__module__" else f"func:{node.name}"

        self._add_node(
            CausalNode(
                id=func_id,
                name=node.name,
                type=NodeType.FUNCTION,
                line=node.lineno,
                metadata={
                    "ast_type": "FunctionDef",
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "scope": scope,
                },
            )
        )

        # Visit nested functions
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function definition as node."""
        scope = self._current_scope()
        func_id = f"func:{scope}.{node.name}" if scope != "__module__" else f"func:{node.name}"

        self._add_node(
            CausalNode(
                id=func_id,
                name=node.name,
                type=NodeType.FUNCTION,
                line=node.lineno,
                metadata={
                    "ast_type": "AsyncFunctionDef",
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "scope": scope,
                    "async": True,
                },
            )
        )

        # Visit nested functions
        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Extract variable assignments as nodes."""
        scope = self._current_scope()

        for target in node.targets:
            if isinstance(target, ast.Name):
                var_id = f"var:{scope}.{target.id}" if scope != "__module__" else f"var:{target.id}"

                self._add_node(
                    CausalNode(
                        id=var_id,
                        name=target.id,
                        type=NodeType.VARIABLE,
                        line=node.lineno,
                        metadata={
                            "ast_type": "Assign",
                            "scope": scope,
                            "value_type": type(node.value).__name__,
                        },
                    )
                )

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        """Extract augmented assignments (+=, -=, etc.) as variable nodes."""
        scope = self._current_scope()

        if isinstance(node.target, ast.Name):
            var_id = (
                f"var:{scope}.{node.target.id}"
                if scope != "__module__"
                else f"var:{node.target.id}"
            )

            self._add_node(
                CausalNode(
                    id=var_id,
                    name=node.target.id,
                    type=NodeType.VARIABLE,
                    line=node.lineno,
                    metadata={
                        "ast_type": "AugAssign",
                        "scope": scope,
                        "op": type(node.op).__name__,
                    },
                )
            )

        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        """Extract return statements as nodes."""
        scope = self._current_scope()

        # Only create return nodes inside functions
        if scope != "__module__":
            ret_id = f"return:{scope}:L{node.lineno}"

            self._add_node(
                CausalNode(
                    id=ret_id,
                    name=f"return@{scope}",
                    type=NodeType.RETURN,
                    line=node.lineno,
                    metadata={
                        "ast_type": "Return",
                        "scope": scope,
                        "has_value": node.value is not None,
                    },
                )
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Extract function calls that have side effects."""
        scope = self._current_scope()

        # Identify calls with known side effects
        side_effect_functions = {
            "print",
            "write",
            "append",
            "extend",
            "remove",
            "pop",
            "clear",
            "update",
            "open",
        }

        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in side_effect_functions:
            effect_id = f"effect:{scope}.{func_name}:L{node.lineno}"

            self._add_node(
                CausalNode(
                    id=effect_id,
                    name=f"{func_name}()",
                    type=NodeType.EFFECT,
                    line=node.lineno,
                    metadata={
                        "ast_type": "Call",
                        "scope": scope,
                        "function": func_name,
                    },
                )
            )

        self.generic_visit(node)


def extract_nodes(ast_tree: ast.Module) -> list[CausalNode]:
    """Extract causal nodes from AST.

    Convenience function wrapping NodeExtractor.

    Args:
        ast_tree: Python AST module

    Returns:
        List of CausalNode objects (functions, variables, returns, effects)

    Example:
        >>> code = '''
        ... def process(x):
        ...     y = x * 2
        ...     return y
        ... '''
        >>> tree = ast.parse(code)
        >>> nodes = extract_nodes(tree)
        >>> len(nodes)
        3  # func:process, var:process.y, return:process
    """
    extractor = NodeExtractor()
    return extractor.extract(ast_tree)
