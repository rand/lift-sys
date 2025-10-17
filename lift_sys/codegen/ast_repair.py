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

        # Pass 6: Fix email validation adjacency bugs
        tree, email_fixes = self._fix_email_validation(tree, function_name)
        modifications.extend(email_fixes)

        # Pass 7: Fix enumerate loops that accumulate result instead of early return
        tree, enumerate_fixes = self._fix_enumerate_early_return(tree, function_name)
        modifications.extend(enumerate_fixes)

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

    def _fix_email_validation(self, tree: ast.AST, function_name: str) -> tuple[ast.AST, list[str]]:
        """
        Fix email validation adjacency bugs.

        Detects email validation that checks positional ordering but misses
        adjacency (e.g., "test@.com" should be invalid).

        Pattern:
            if email.index('@') > email.rindex('.'):
                return False

        Fix:
            at_pos = email.index('@')
            dot_pos = email.rindex('.')
            if at_pos >= dot_pos or dot_pos - at_pos == 1:
                return False
        """
        modifications = []
        transformer = EmailValidationTransformer(modifications)
        tree = transformer.visit(tree)
        ast.fix_missing_locations(tree)
        return tree, modifications

    def _fix_enumerate_early_return(
        self, tree: ast.AST, function_name: str
    ) -> tuple[ast.AST, list[str]]:
        """
        Fix enumerate loops that accumulate result instead of early return.

        Detects pattern where loops assign to a result variable instead of
        returning immediately when a match is found (returns LAST match instead of FIRST).

        Pattern:
            result = -1
            for i, item in enumerate(items):
                if item == target:
                    result = i
            return result  # BUG: Returns LAST match

        Fix:
            for i, item in enumerate(items):
                if item == target:
                    return i  # FIXED: Early return on FIRST match
            return -1
        """
        modifications = []
        transformer = EnumerateEarlyReturnTransformer(modifications, function_name)
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


class EmailValidationTransformer(ast.NodeTransformer):
    """
    Fix email validation patterns that check positional ordering but miss adjacency.

    Detects: if email.index('@') > email.rindex('.'): return False
    Fixes: Add adjacency check (dot_pos - at_pos == 1)
    """

    def __init__(self, modifications: list[str]):
        self.modifications = modifications

    def visit_If(self, node: ast.If) -> ast.If:
        """Detect and fix email index comparison pattern."""
        if self._is_email_index_pattern(node):
            # Found the pattern - replace with fixed version
            fixed_stmts = self._create_fixed_check(node)
            self.modifications.append("Fixed email validation to check @ and . adjacency")
            # Return the first statement (the other will be added via generic_visit)
            # Actually, we need to replace this If with multiple statements
            # Since we can't return multiple statements from visit_If, we'll transform in place
            return self._transform_in_place(node)
        return self.generic_visit(node)

    def _is_email_index_pattern(self, node: ast.If) -> bool:
        """
        Detect pattern: if email.index('@') > email.rindex('.'): return False

        Returns True if this If statement matches the buggy email validation pattern.
        """
        # Check if test is a Compare with > operator
        if not isinstance(node.test, ast.Compare):
            return False

        compare = node.test
        if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Gt):
            return False

        # Check left side: email.index('@')
        left = compare.left
        if not self._is_method_call(left, "index", "@"):
            return False

        # Check right side: email.rindex('.')
        if len(compare.comparators) != 1:
            return False
        right = compare.comparators[0]
        if not self._is_method_call(right, "rindex", "."):
            return False

        # Check that body has return False
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            return False

        return_stmt = node.body[0]
        if return_stmt.value is None:
            return False

        # Check if returning False
        if isinstance(return_stmt.value, ast.Constant) and return_stmt.value.value is False:
            return True

        # Older Python versions use ast.NameConstant
        if isinstance(return_stmt.value, ast.NameConstant) and return_stmt.value.value is False:
            return True

        return False

    def _is_method_call(self, node: ast.AST, method_name: str, arg_value: str) -> bool:
        """
        Check if node is a method call like email.index('@').

        Args:
            node: AST node to check
            method_name: Expected method name (e.g., "index")
            arg_value: Expected string argument (e.g., "@")
        """
        if not isinstance(node, ast.Call):
            return False

        # Check if it's an attribute access (e.g., email.index)
        if not isinstance(node.func, ast.Attribute):
            return False

        # Check method name
        if node.func.attr != method_name:
            return False

        # Check argument
        if len(node.args) != 1:
            return False

        arg = node.args[0]
        # Check if argument is the expected string
        if isinstance(arg, ast.Constant) and arg.value == arg_value:
            return True

        # Older Python: ast.Str
        if isinstance(arg, ast.Str) and arg.s == arg_value:
            return True

        return False

    def _transform_in_place(self, node: ast.If) -> ast.If:
        """
        Transform the buggy If statement into a fixed version.

        Original:
            if email.index('@') > email.rindex('.'): return False

        Fixed:
            at_pos = email.index('@')
            dot_pos = email.rindex('.')
            if at_pos >= dot_pos or dot_pos - at_pos == 1: return False

        Since we can't insert multiple statements in visit_If, we need a different approach.
        We'll use a helper that modifies the parent's body list instead.

        For now, we'll transform to a compound check with intermediate variables
        using a more complex If test that includes the adjacency check.

        Actually, we can't easily do multi-statement replacement in NodeTransformer.
        Let's use a simpler fix: just update the comparison to include adjacency.

        Change: email.index('@') > email.rindex('.')
        To: email.index('@') >= email.rindex('.') or email.rindex('.') - email.index('@') == 1
        """
        # Extract the email variable/expression
        compare = node.test
        email_var = compare.left.func.value  # The 'email' part of email.index

        # Create: at_pos >= dot_pos
        at_pos_call = compare.left  # email.index('@')
        dot_pos_call = compare.comparators[0]  # email.rindex('.')

        # Create: at_pos >= dot_pos (change > to >=)
        greater_or_equal = ast.Compare(
            left=at_pos_call, ops=[ast.GtE()], comparators=[dot_pos_call]
        )

        # Create: dot_pos - at_pos == 1
        # This is: email.rindex('.') - email.index('@') == 1
        adjacency_check = ast.Compare(
            left=ast.BinOp(left=dot_pos_call, op=ast.Sub(), right=at_pos_call),
            ops=[ast.Eq()],
            comparators=[ast.Constant(value=1)],
        )

        # Combine with or: (at_pos >= dot_pos or dot_pos - at_pos == 1)
        new_test = ast.BoolOp(op=ast.Or(), values=[greater_or_equal, adjacency_check])

        # Update the node's test
        node.test = new_test

        return node

    def _create_fixed_check(self, node: ast.If) -> list[ast.AST]:
        """
        Create fixed version with intermediate variables.

        This method is currently unused but kept for reference.
        """
        # This would be used if we could return multiple statements
        pass


class EnumerateEarlyReturnTransformer(ast.NodeTransformer):
    """
    Fix enumerate loops that accumulate last result instead of early return.

    Detects pattern:
        result = -1
        for i, item in enumerate(items):
            if item == target:
                result = i
        return result

    Transforms to:
        for i, item in enumerate(items):
            if item == target:
                return i
        return -1
    """

    def __init__(self, modifications: list[str], function_name: str):
        self.modifications = modifications
        self.function_name = function_name

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function and fix enumerate early return pattern."""
        # Only process target function
        if node.name != self.function_name:
            return node

        # Look for the pattern:
        # 1. result = -1 (or None)
        # 2. for i, item in enumerate(...):
        #      if ...: result = i
        # 3. return result

        result_var = None
        result_init_idx = None
        enumerate_loop_idx = None
        return_idx = None

        # Find result initialization
        for i, stmt in enumerate(node.body):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and isinstance(
                    stmt.value, (ast.Constant, ast.UnaryOp)
                ):
                    # Found result = -1 or result = None
                    result_var = target.id
                    result_init_idx = i
                    break

        if not result_var:
            return node

        # Find enumerate loop that assigns to result_var
        for i, stmt in enumerate(node.body[result_init_idx + 1 :], start=result_init_idx + 1):
            if isinstance(stmt, ast.For):
                # Check if loop uses enumerate
                if self._is_enumerate_loop(stmt):
                    # Check if loop assigns to result_var
                    if self._assigns_to_var(stmt.body, result_var):
                        enumerate_loop_idx = i
                        break

        if enumerate_loop_idx is None:
            return node

        # Find return statement that returns result_var
        for i, stmt in enumerate(node.body[enumerate_loop_idx + 1 :], start=enumerate_loop_idx + 1):
            if isinstance(stmt, ast.Return) and stmt.value:
                if isinstance(stmt.value, ast.Name) and stmt.value.id == result_var:
                    return_idx = i
                    break

        if return_idx is None:
            return node

        # Found the pattern! Transform it
        loop = node.body[enumerate_loop_idx]
        result_init = node.body[result_init_idx]

        # Transform loop body: replace 'result = i' with 'return i'
        new_loop_body = self._transform_assignments_to_returns(loop.body, result_var)
        loop.body = new_loop_body

        # Get the fallback value from result initialization
        fallback_value = result_init.value

        # Build new function body:
        # - Keep statements before result init
        # - Remove result init
        # - Keep loop (now with early returns)
        # - Replace final return with fallback
        new_body = []
        new_body.extend(node.body[:result_init_idx])  # Before result init
        new_body.append(loop)  # Transformed loop
        # Add fallback return
        new_body.append(ast.Return(value=fallback_value))

        # Keep any statements after the old return (shouldn't be any, but just in case)
        if return_idx + 1 < len(node.body):
            new_body.extend(node.body[return_idx + 1 :])

        node.body = new_body
        self.modifications.append(
            "Fixed enumerate loop to use early return (returns FIRST match, not last)"
        )

        return node

    def _is_enumerate_loop(self, loop: ast.For) -> bool:
        """Check if loop uses enumerate()."""
        if not isinstance(loop.iter, ast.Call):
            return False
        if not isinstance(loop.iter.func, ast.Name):
            return False
        return loop.iter.func.id == "enumerate"

    def _assigns_to_var(self, body: list[ast.stmt], var_name: str) -> bool:
        """Check if body contains assignment to var_name."""
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return True
            # Check nested structures (if/else)
            if isinstance(stmt, ast.If):
                if self._assigns_to_var(stmt.body, var_name):
                    return True
                if stmt.orelse and self._assigns_to_var(stmt.orelse, var_name):
                    return True
        return False

    def _transform_assignments_to_returns(
        self, body: list[ast.stmt], var_name: str
    ) -> list[ast.stmt]:
        """Transform assignments to var_name into return statements."""
        new_body = []
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                # Check if this assigns to var_name
                is_result_assign = False
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        is_result_assign = True
                        break

                if is_result_assign:
                    # Replace with return
                    new_body.append(ast.Return(value=stmt.value))
                else:
                    new_body.append(stmt)
            elif isinstance(stmt, ast.If):
                # Recursively transform if body
                stmt.body = self._transform_assignments_to_returns(stmt.body, var_name)
                if stmt.orelse:
                    stmt.orelse = self._transform_assignments_to_returns(stmt.orelse, var_name)
                new_body.append(stmt)
            else:
                new_body.append(stmt)
        return new_body


__all__ = ["ASTRepairEngine"]
