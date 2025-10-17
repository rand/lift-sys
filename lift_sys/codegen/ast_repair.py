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

        # Pass 3: Fix nested min/max checks
        tree, minmax_fixes = self._fix_nested_minmax(tree, function_name)
        modifications.extend(minmax_fixes)

        # Pass 4: Add missing stdlib imports
        tree, import_fixes = self._add_missing_imports(tree, code)
        modifications.extend(import_fixes)

        # Pass 5: Fix missing return statements
        tree, return_fixes = self._fix_missing_returns(tree, function_name)
        modifications.extend(return_fixes)

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

    def _fix_nested_minmax(self, tree: ast.AST, function_name: str) -> tuple[ast.AST, list[str]]:
        """
        Fix nested min/max checks that should be independent.

        Pattern:
            if number < min_value:
                min_value = number
                if number > max_value:  # BUG: Nested, only runs on new min
                    max_value = number

        Fix:
            if number < min_value:
                min_value = number
            if number > max_value:  # FIXED: Independent check
                max_value = number
        """
        modifications = []
        transformer = NestedMinMaxTransformer(modifications)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree, modifications

    def _add_missing_imports(self, tree: ast.AST, code: str) -> tuple[ast.AST, list[str]]:
        """
        Add missing stdlib imports.

        Detects when stdlib modules are referenced but not imported.
        Common patterns: re.search(), math.sqrt(), etc.

        Pattern:
            # Uses re.search() but missing import
            if re.search(pattern, text):
                ...

        Fix:
            import re  # ← ADDED

            if re.search(pattern, text):
                ...
        """
        modifications = []
        transformer = MissingImportTransformer(modifications, code)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree, modifications

    def _fix_missing_returns(self, tree: ast.AST, function_name: str) -> tuple[ast.AST, list[str]]:
        """
        Fix functions that should return but don't.

        Detects functions with return type hints that have code paths without returns.

        Pattern:
            def count_words(text: str) -> int:
                words = text.split()
                # Missing: return len(words)

        Fix:
            def count_words(text: str) -> int:
                words = text.split()
                return len(words)  # ← ADDED based on heuristics
        """
        modifications = []
        transformer = MissingReturnTransformer(modifications)
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


class NestedMinMaxTransformer(ast.NodeTransformer):
    """
    AST transformer to fix nested min/max checks.

    Detects patterns where max check is nested inside min check, which causes
    max to only update when finding a new minimum (incorrect logic).
    """

    def __init__(self, modifications: list[str]):
        self.modifications = modifications

    def visit_For(self, node: ast.For) -> ast.For:
        """Visit for loops and check for nested min/max pattern."""
        new_body = []
        extracted_checks = []

        for stmt in node.body:
            if isinstance(stmt, ast.If) and self._is_min_check_with_nested_max(stmt):
                # Found the pattern! Extract the nested max check
                fixed_min_check, max_check = self._extract_nested_max(stmt)
                new_body.append(fixed_min_check)
                extracted_checks.append(max_check)
                self.modifications.append(
                    "Unnested max check from inside min check (min/max should be independent)"
                )
            else:
                # Keep other statements unchanged
                new_body.append(self.visit(stmt))

        # Add extracted max checks after the modified body
        new_body.extend(extracted_checks)
        node.body = new_body

        return node

    def _is_min_check_with_nested_max(self, if_node: ast.If) -> bool:
        """
        Check if this is a min check with a nested max check.

        Pattern:
            if x < min_var:
                min_var = x
                if x > max_var:  # <- Nested max check
                    max_var = x
        """
        # Must be a comparison (x < min_var)
        if not isinstance(if_node.test, ast.Compare):
            return False

        # Must have at least 2 statements in body
        if len(if_node.body) < 2:
            return False

        # First statement should be assignment (min_var = x)
        first_stmt = if_node.body[0]
        if not isinstance(first_stmt, ast.Assign):
            return False

        # Look for nested If that's a max check
        for stmt in if_node.body[1:]:
            if isinstance(stmt, ast.If) and self._is_max_check(stmt):
                return True

        return False

    def _is_max_check(self, if_node: ast.If) -> bool:
        """
        Check if this is a max check pattern.

        Pattern:
            if x > max_var:
                max_var = x
        """
        # Must be a comparison (x > max_var)
        if not isinstance(if_node.test, ast.Compare):
            return False

        # Check for > operator
        if not if_node.test.ops or not isinstance(if_node.test.ops[0], ast.Gt):
            return False

        # Body should be a single assignment
        if len(if_node.body) != 1:
            return False

        return isinstance(if_node.body[0], ast.Assign)

    def _extract_nested_max(self, min_check: ast.If) -> tuple[ast.If, ast.If]:
        """
        Extract the nested max check from the min check.

        Returns:
            (fixed_min_check, extracted_max_check)
        """
        new_body = []
        max_check = None

        for stmt in min_check.body:
            if isinstance(stmt, ast.If) and self._is_max_check(stmt) and max_check is None:
                # Found the nested max check - extract it
                max_check = stmt
            else:
                # Keep other statements in min check
                new_body.append(stmt)

        min_check.body = new_body
        return min_check, max_check


class MissingImportTransformer(ast.NodeTransformer):
    """
    AST transformer to add missing stdlib imports.

    Detects when code references stdlib modules without importing them.
    """

    # Common stdlib modules we can safely auto-import
    STDLIB_MODULES = {
        "re",
        "math",
        "random",
        "json",
        "os",
        "sys",
        "datetime",
        "time",
        "itertools",
        "collections",
        "functools",
    }

    def __init__(self, modifications: list[str], code: str):
        self.modifications = modifications
        self.code = code
        self.modules_to_import = set()

    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Visit module and detect missing imports."""
        # Find all module references in the code
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Attribute):
                # Check for module.function() patterns
                if isinstance(stmt.value, ast.Name):
                    module_name = stmt.value.id
                    if module_name in self.STDLIB_MODULES:
                        self.modules_to_import.add(module_name)

        # Check if modules are already imported
        existing_imports = set()
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                for alias in stmt.names:
                    existing_imports.add(alias.name)
            elif isinstance(stmt, ast.ImportFrom):
                if stmt.module:
                    existing_imports.add(stmt.module)

        # Add missing imports
        missing = self.modules_to_import - existing_imports
        if missing:
            # Insert imports at the beginning
            new_imports = [
                ast.Import(names=[ast.alias(name=module, asname=None)])
                for module in sorted(missing)
            ]
            node.body = new_imports + node.body
            for module in sorted(missing):
                self.modifications.append(f"Added missing import: {module}")

        return node


class MissingReturnTransformer(ast.NodeTransformer):
    """
    AST transformer to fix missing return statements.

    Detects functions with return type hints that don't return on all paths.
    """

    def __init__(self, modifications: list[str]):
        self.modifications = modifications

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function and check for missing returns."""
        # Only fix if function has return type hint
        if not node.returns:
            return node

        # Check if function already has returns
        has_return = self._has_return_statement(node.body)
        if has_return:
            return node

        # Heuristic: Try to add a return based on last statement
        if not node.body:
            return node

        last_stmt = node.body[-1]

        # Pattern 1: Last statement assigns to a variable - return it
        if isinstance(last_stmt, ast.Assign):
            if len(last_stmt.targets) == 1 and isinstance(last_stmt.targets[0], ast.Name):
                var_name = last_stmt.targets[0].id
                # Add return statement
                return_stmt = ast.Return(value=ast.Name(id=var_name, ctx=ast.Load()))
                node.body.append(return_stmt)
                self.modifications.append(f"Added missing return statement: return {var_name}")

        # Pattern 2: Last statement is an expression (e.g., len(words)) - return it
        elif isinstance(last_stmt, ast.Expr):
            # Convert expression to return
            return_stmt = ast.Return(value=last_stmt.value)
            node.body[-1] = return_stmt
            self.modifications.append("Added missing return statement for expression")

        return node

    def _has_return_statement(self, body: list) -> bool:
        """Check if function body has any return statements."""
        for stmt in body:
            if isinstance(stmt, ast.Return):
                return True
            # Check nested structures
            if isinstance(stmt, (ast.If, ast.For, ast.While)):
                if self._has_return_statement(stmt.body):
                    return True
                if hasattr(stmt, "orelse") and self._has_return_statement(stmt.orelse):
                    return True
        return False


__all__ = ["ASTRepairEngine"]
