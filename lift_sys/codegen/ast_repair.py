"""
Deterministic AST-based code repair.

Complements AI code generation with mechanical fixes for known bug patterns.
Instead of asking AI to understand corrections through prompts, we detect and
fix bugs using deterministic AST transformations.
"""

import ast


class ASTRepairEngine:
    """
    Deterministically fix known code patterns using AST transformations.

    This engine complements AI code generation:
    - AI generates initial code (creative, ~80% correct)
    - AST repair fixes known mechanical issues (deterministic, 100% for known patterns)
    """

    def repair(self, code: str, function_name: str, context: dict | None = None) -> str | None:
        """
        Attempt to repair known bugs in generated code.

        Args:
            code: Generated Python code
            function_name: Name of the function being repaired
            context: Optional context (e.g., IR, validation issues)

        Returns:
            Fixed code if repairs were made, None if no repairs needed

        Raises:
            SyntaxError: If code cannot be parsed
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Can't repair unparseable code
            raise SyntaxError(f"Cannot repair code with syntax errors: {e}") from e

        # Apply repair passes
        modifications = []

        # Pass 1: Fix loop return placement
        tree, loop_fixes = self._fix_loop_returns(tree, function_name)
        modifications.extend(loop_fixes)

        # Pass 2: Fix type checking patterns
        tree, type_fixes = self._fix_type_checks(tree, function_name)
        modifications.extend(type_fixes)

        if not modifications:
            return None  # No repairs needed

        # Convert back to code
        try:
            repaired_code = ast.unparse(tree)
            return repaired_code
        except Exception as e:
            # If unparsing fails, return None (don't break things)
            print(f"  ⚠️ AST repair failed to unparse: {e}")
            return None

    def _fix_loop_returns(self, tree: ast.AST, function_name: str) -> tuple[ast.AST, list[str]]:
        """
        Fix returns placed inside loops when they should be after.

        Pattern:
            for index, item in enumerate(lst):
                if item == value:
                    return index
                return -1  # ← BUG: Inside loop

        Fix:
            for index, item in enumerate(lst):
                if item == value:
                    return index
            return -1  # ← FIXED: After loop
        """
        modifications = []
        transformer = LoopReturnTransformer(modifications)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree, modifications

    def _fix_type_checks(self, tree: ast.AST, function_name: str) -> tuple[ast.AST, list[str]]:
        """
        Fix type().__name__ patterns to use isinstance.

        Pattern:
            return type(value).__name__.lower()

        Fix:
            if isinstance(value, int): return 'int'
            elif isinstance(value, str): return 'str'
            elif isinstance(value, list): return 'list'
            else: return 'other'
        """
        modifications = []
        transformer = TypeCheckTransformer(modifications)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree, modifications


class LoopReturnTransformer(ast.NodeTransformer):
    """
    AST transformer to fix return statements inside loops.

    Detects returns that are direct children of loop bodies (not inside if/else)
    and moves them to after the loop.
    """

    def __init__(self, modifications: list[str]):
        self.modifications = modifications

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function and fix loop returns in its body."""
        new_body = []

        for stmt in node.body:
            if isinstance(stmt, ast.For):
                # Check if loop has returns that should be after it
                fixed_loop, fallback_return = self._fix_loop(stmt)
                new_body.append(fixed_loop)

                if fallback_return:
                    # Add the fallback return after the loop
                    new_body.append(fallback_return)
                    self.modifications.append(
                        "Moved fallback return from inside loop to after loop"
                    )
            else:
                new_body.append(self.visit(stmt))

        node.body = new_body
        return node

    def _fix_loop(self, loop: ast.For) -> tuple[ast.For, ast.Return | None]:
        """
        Fix a single loop, extracting fallback returns.

        Returns:
            (fixed_loop, fallback_return or None)
        """
        new_body = []
        fallback_return = None

        for _, stmt in enumerate(loop.body):
            if isinstance(stmt, ast.Return):
                # This is a return directly in the loop body
                # It should be the fallback (after the loop)
                if fallback_return is None:
                    fallback_return = stmt
                else:
                    # Multiple returns in loop - keep the first one we found
                    pass
            else:
                # Keep other statements (including if/else with returns)
                new_body.append(stmt)

        loop.body = new_body if new_body else [ast.Pass()]  # Need at least one statement
        return loop, fallback_return


class TypeCheckTransformer(ast.NodeTransformer):
    """
    AST transformer to fix type().__name__ patterns.

    Replaces type(x).__name__ with proper isinstance checks.
    """

    def __init__(self, modifications: list[str]):
        self.modifications = modifications
        self.found_type_pattern = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function and check for type().__name__ pattern."""
        # Look for simple pattern: single return with type().__name__
        if len(node.body) == 1 and isinstance(node.body[0], ast.Return):
            ret = node.body[0]
            if self._is_type_name_pattern(ret.value):
                # Extract the value node (unwrap .lower() if present)
                pattern_node = ret.value
                if isinstance(pattern_node, ast.Call) and isinstance(
                    pattern_node.func, ast.Attribute
                ):
                    if pattern_node.func.attr == "lower":
                        # Unwrap .lower() to get to the Attribute node
                        pattern_node = pattern_node.func.value

                # Now pattern_node is the Attribute node for __name__
                # Get the argument to type()
                value_node = pattern_node.value.args[0]

                # Replace entire function body with isinstance chain
                new_body = self._create_isinstance_chain(value_node)
                node.body = new_body
                self.modifications.append("Replaced type().__name__ with isinstance checks")
                self.found_type_pattern = True

        return node

    def _is_type_name_pattern(self, node) -> bool:
        """
        Detect type(x).__name__ or type(x).__name__.lower() pattern.

        AST structure:
            Attribute(value=Call(func=Name('type')), attr='__name__')
        or:
            Call(func=Attribute(...), args=[])  # for .lower()
        """
        if node is None:
            return False

        # Check for .lower() wrapper
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "lower":
                # Check if it's wrapping type().__name__
                node = node.func.value

        # Check for type(x).__name__
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "__name__"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "type"
            and len(node.value.args) == 1
        )

    def _create_isinstance_chain(self, value_node) -> list[ast.stmt]:
        """
        Create isinstance check chain.

        Returns:
            if isinstance(value, int): return 'int'
            elif isinstance(value, str): return 'str'
            elif isinstance(value, list): return 'list'
            else: return 'other'
        """
        # Create isinstance checks
        checks = [
            ("int", ast.Name("int", ast.Load())),
            ("str", ast.Name("str", ast.Load())),
            ("list", ast.Name("list", ast.Load())),
        ]

        # Build chain from end to beginning for cleaner nesting
        # Start with final else: return 'other'
        final_else = [ast.Return(value=ast.Constant(value="other"))]

        # Build nested if-elif structure backwards
        current_orelse = final_else
        for type_name, type_obj in reversed(checks):
            test = ast.Call(
                func=ast.Name("isinstance", ast.Load()), args=[value_node, type_obj], keywords=[]
            )
            body = [ast.Return(value=ast.Constant(value=type_name))]

            # Create If node with current orelse
            if_node = ast.If(test=test, body=body, orelse=current_orelse)
            current_orelse = [if_node]

        # Return the outermost If statement
        return current_orelse


__all__ = ["ASTRepairEngine"]
