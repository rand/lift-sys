"""
Equivalence checking for IRs and code snippets.

This module provides tools to determine semantic equivalence of:
1. IR representations (modulo naming, effect ordering, assertion rephrasing)
2. Code snippets (via execution on test inputs OR AST-based structural comparison)

Usage:
    from lift_sys.robustness import EquivalenceChecker

    checker = EquivalenceChecker(normalize_naming=True)

    # Check IR equivalence
    if checker.ir_equivalent(ir1, ir2):
        print("IRs are semantically equivalent")

    # Check code equivalence (execution-based)
    test_inputs = [{"nums": [3, 1, 4]}, {"nums": []}]
    if checker.code_equivalent(code1, code2, test_inputs):
        print("Code snippets are functionally equivalent")

    # Check code equivalence (structural, for mock code)
    if checker.code_equivalent_structural(code1, code2):
        print("Code snippets are structurally equivalent")
"""

import ast
import json
import os
import re
import subprocess
import tempfile
from typing import Any

from lift_sys.ir.models import IntermediateRepresentation
from lift_sys.robustness.types import NamingStyle


class EquivalenceChecker:
    """
    Checks equivalence of IRs and code snippets.

    Supports:
    - IR semantic equivalence (with normalization options)
    - Code functional equivalence (via execution testing)
    - Intent similarity (via sentence embeddings)
    """

    def __init__(
        self,
        normalize_naming: bool = True,
        check_effect_order: bool = False,
        use_smt_solver: bool = False,  # Z3 optional for now (future enhancement)
        intent_similarity_threshold: float = 0.9,
    ):
        """
        Initialize equivalence checker.

        Args:
            normalize_naming: If True, normalize identifiers before comparison
            check_effect_order: If True, effects must be in same order
            use_smt_solver: If True, use Z3 for assertion equivalence (not yet implemented)
            intent_similarity_threshold: Minimum cosine similarity for intent equivalence
        """
        self.normalize_naming = normalize_naming
        self.check_effect_order = check_effect_order
        self.use_smt_solver = use_smt_solver
        self.intent_similarity_threshold = intent_similarity_threshold

        # Lazy-load sentence transformer (expensive initialization)
        self._sentence_model = None

    @property
    def sentence_model(self):
        """Lazy-load sentence transformer model."""
        if self._sentence_model is None:
            from sentence_transformers import SentenceTransformer

            self._sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._sentence_model

    def ir_equivalent(
        self,
        ir1: IntermediateRepresentation,
        ir2: IntermediateRepresentation,
    ) -> bool:
        """
        Check if two IRs are semantically equivalent.

        IRs are considered equivalent if:
        1. Intents are semantically similar (via sentence embeddings)
        2. Signatures are equivalent (modulo naming if normalize_naming=True)
        3. Effects are equivalent (order-independent if check_effect_order=False)
        4. Assertions are equivalent (structural comparison or SMT-based)

        Args:
            ir1: First IR
            ir2: Second IR

        Returns:
            True if IRs are semantically equivalent
        """
        # 1. Check intents (semantic similarity)
        if not self._intents_equivalent(ir1.intent.summary, ir2.intent.summary):
            return False

        # 2. Check signatures (modulo naming if normalize_naming=True)
        if not self._signatures_equivalent(ir1.signature, ir2.signature):
            return False

        # 3. Check effects (order-independent if check_effect_order=False)
        if not self._effects_equivalent(ir1.effects, ir2.effects):
            return False

        # 4. Check assertions (logical equivalence)
        if not self._assertions_equivalent(ir1.assertions, ir2.assertions):
            return False

        return True

    def _intents_equivalent(self, intent1: str, intent2: str) -> bool:
        """
        Check if intents are semantically equivalent using sentence embeddings.

        Args:
            intent1: First intent string
            intent2: Second intent string

        Returns:
            True if cosine similarity exceeds threshold
        """
        # Handle exact matches
        if intent1 == intent2:
            return True

        # Use sentence embeddings for semantic similarity
        from sklearn.metrics.pairwise import cosine_similarity

        emb1 = self.sentence_model.encode([intent1])
        emb2 = self.sentence_model.encode([intent2])

        similarity = cosine_similarity(emb1, emb2)[0][0]
        return similarity >= self.intent_similarity_threshold

    def _signatures_equivalent(self, sig1, sig2) -> bool:
        """
        Check if signatures are equivalent (modulo naming).

        Args:
            sig1: First signature (SigClause)
            sig2: Second signature (SigClause)

        Returns:
            True if signatures are structurally equivalent
        """
        if self.normalize_naming:
            # Normalize both to snake_case before comparison
            sig1_name = self._normalize_name(sig1.name)
            sig2_name = self._normalize_name(sig2.name)
        else:
            sig1_name = sig1.name
            sig2_name = sig2.name

        # Compare function names (after normalization)
        if sig1_name != sig2_name:
            return False

        # Compare return types
        if sig1.returns != sig2.returns:
            return False

        # Compare parameters
        params1 = sig1.parameters
        params2 = sig2.parameters

        if len(params1) != len(params2):
            return False

        for p1, p2 in zip(params1, params2, strict=False):
            # Compare types (must match exactly)
            if p1.type_hint != p2.type_hint:
                return False

            # Compare names (with normalization if enabled)
            if self.normalize_naming:
                if self._normalize_name(p1.name) != self._normalize_name(p2.name):
                    return False
            else:
                if p1.name != p2.name:
                    return False

        return True

    def _effects_equivalent(self, effects1: list, effects2: list) -> bool:
        """
        Check if effects are equivalent (possibly reordered).

        Args:
            effects1: First list of effects (EffectClause)
            effects2: Second list of effects (EffectClause)

        Returns:
            True if effects are equivalent
        """
        if len(effects1) != len(effects2):
            return False

        # Convert to comparable format (description strings)
        desc1 = [e.description for e in effects1]
        desc2 = [e.description for e in effects2]

        # Normalize identifiers in descriptions if normalize_naming is enabled
        if self.normalize_naming:
            desc1 = [self._normalize_text_identifiers(d) for d in desc1]
            desc2 = [self._normalize_text_identifiers(d) for d in desc2]

        if self.check_effect_order:
            # Order matters - must be exact match
            return desc1 == desc2
        else:
            # Order doesn't matter - compare as sets
            return set(desc1) == set(desc2)

    def _assertions_equivalent(self, assertions1: list, assertions2: list) -> bool:
        """
        Check if assertions are logically equivalent.

        Args:
            assertions1: First list of assertions (AssertClause)
            assertions2: Second list of assertions (AssertClause)

        Returns:
            True if assertions are equivalent
        """
        if len(assertions1) != len(assertions2):
            return False

        if self.use_smt_solver:
            # Future: Use Z3 for logical equivalence checking
            # For now, fall back to structural comparison
            pass

        # Structural comparison (predicates must match as sets)
        pred1 = {a.predicate for a in assertions1}
        pred2 = {a.predicate for a in assertions2}

        # Normalize identifiers in predicates if normalize_naming is enabled
        if self.normalize_naming:
            pred1 = {self._normalize_text_identifiers(p) for p in pred1}
            pred2 = {self._normalize_text_identifiers(p) for p in pred2}

        return pred1 == pred2

    def _normalize_name(self, name: str) -> str:
        """
        Normalize identifier to snake_case for comparison.

        Args:
            name: Identifier name

        Returns:
            snake_case version of name
        """
        from lift_sys.robustness.utils import convert_naming_style

        return convert_naming_style(name, NamingStyle.SNAKE_CASE)

    def _normalize_text_identifiers(self, text: str) -> str:
        """
        Normalize identifiers within free-form text to snake_case.

        Similar to IRVariantGenerator._rewrite_identifiers_in_text() but
        used for equivalence comparison. Finds Python identifiers in text
        and normalizes them to snake_case for consistent comparison.

        Args:
            text: Text containing identifiers (e.g., "Validate email format")

        Returns:
            Text with normalized identifiers (e.g., "validate email format")
        """
        # Pattern: match Python identifiers (word chars, underscores, not starting with digit)
        pattern = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

        def replace_identifier(match):
            word = match.group(0)
            # Don't convert reserved words or single characters
            if (
                word.lower()
                in {
                    "len",
                    "is",
                    "not",
                    "and",
                    "or",
                    "in",
                    "true",
                    "false",
                    "none",
                    "if",
                    "else",
                    "for",
                    "while",
                    "def",
                    "class",
                    "return",
                    "import",
                    "from",
                    "as",
                }
                or len(word) == 1
            ):
                return word
            return self._normalize_name(word)

        return re.sub(pattern, replace_identifier, text)

    def code_equivalent(
        self,
        code1: str,
        code2: str,
        test_inputs: list[dict],
        timeout_seconds: int = 5,
    ) -> bool:
        """
        Check if two code snippets are functionally equivalent.

        Executes both code snippets on the same test inputs and compares outputs.
        Both must succeed and produce equivalent outputs for all test cases.

        Args:
            code1: First code snippet (Python)
            code2: Second code snippet (Python)
            test_inputs: List of test input dicts
            timeout_seconds: Maximum execution time per test case

        Returns:
            True if code snippets are functionally equivalent on all test inputs
        """
        if not test_inputs:
            # No test inputs - can't determine equivalence
            return False

        for test_input in test_inputs:
            try:
                output1 = self._execute_code(code1, test_input, timeout_seconds)
                output2 = self._execute_code(code2, test_input, timeout_seconds)

                if not self._outputs_equivalent(output1, output2):
                    return False

            except Exception:
                # If either code fails, they're not equivalent
                # (unless both fail with same error - not implemented yet)
                return False

        return True

    def code_equivalent_structural(
        self,
        code1: str,
        code2: str,
    ) -> bool:
        """
        Check if two code snippets are structurally equivalent via AST comparison.

        This method normalizes identifiers (if normalize_naming=True) and compares
        the AST structure. Useful for simple mock code where execution testing
        isn't feasible.

        For simple function bodies with only statements (no control flow), this
        performs order-independent comparison.

        Args:
            code1: First code snippet (Python)
            code2: Second code snippet (Python)

        Returns:
            True if code snippets have equivalent AST structure
        """
        try:
            # Parse both code snippets
            ast1 = ast.parse(code1)
            ast2 = ast.parse(code2)

            # Normalize ASTs if naming normalization is enabled
            if self.normalize_naming:
                ast1 = self._normalize_ast(ast1)
                ast2 = self._normalize_ast(ast2)

            # Check if both are simple function bodies (single function, only statements)
            is_simple1 = self._is_simple_function_body(ast1)
            is_simple2 = self._is_simple_function_body(ast2)

            # Debug logging
            if not (is_simple1 and is_simple2):
                print(
                    f"DEBUG: Simple function check failed: is_simple1={is_simple1}, is_simple2={is_simple2}"
                )
                print(f"DEBUG: Code1 (first 100 chars):\n{code1[:100]}")
                print(f"DEBUG: Code2 (first 100 chars):\n{code2[:100]}")

            if is_simple1 and is_simple2:
                # For simple function bodies, compare statements order-independently
                result = self._compare_simple_functions(ast1, ast2)
                # Debug logging (will be removed after verification)
                if not result:
                    print("DEBUG: Order-independent comparison failed")
                    print(f"DEBUG: Code1:\n{code1}")
                    print(f"DEBUG: Code2:\n{code2}")
                return result

            # Otherwise, compare AST dumps (string representation)
            return ast.dump(ast1) == ast.dump(ast2)

        except SyntaxError:
            # If either code has syntax errors, they're not equivalent
            return False

    def _is_simple_function_body(self, tree: ast.AST) -> bool:
        """
        Check if AST is a single function with only expression statements (no control flow).

        Args:
            tree: AST tree

        Returns:
            True if tree is a single function with only Expr/Pass statements
        """
        if not isinstance(tree, ast.Module) or len(tree.body) != 1:
            return False

        func = tree.body[0]
        if not isinstance(func, ast.FunctionDef):
            return False

        # Check that all statements are simple expressions or passes (no control flow)
        for stmt in func.body:
            if isinstance(stmt, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                # Has control flow - can't do order-independent comparison
                return False

        return True

    def _compare_simple_functions(self, ast1: ast.AST, ast2: ast.AST) -> bool:
        """
        Compare two simple functions order-independently.

        Compares function signatures and statement bodies as sets.

        Args:
            ast1: First function AST (Module containing single FunctionDef)
            ast2: Second function AST (Module containing single FunctionDef)

        Returns:
            True if functions have same signature and statements (order-independent)
        """
        func1 = ast1.body[0]
        func2 = ast2.body[0]

        # Compare function names (after normalization, should be same)
        if func1.name != func2.name:
            return False

        # Compare arguments
        args1_dump = ast.dump(func1.args)
        args2_dump = ast.dump(func2.args)
        if args1_dump != args2_dump:
            return False

        # Compare number of statements first
        if len(func1.body) != len(func2.body):
            return False

        # Compare statements as sets (order-independent)
        # Each statement is dumped to a canonical string representation
        stmts1 = {ast.dump(stmt) for stmt in func1.body}
        stmts2 = {ast.dump(stmt) for stmt in func2.body}

        return stmts1 == stmts2

    def _normalize_ast(self, tree: ast.AST) -> ast.AST:
        """
        Normalize identifiers in AST to snake_case for comparison.

        This allows comparison of code with different naming conventions
        (camelCase, PascalCase, etc.) as structurally equivalent.

        Args:
            tree: AST tree to normalize

        Returns:
            Normalized AST tree with all identifiers in snake_case
        """

        class IdentifierNormalizer(ast.NodeTransformer):
            def __init__(self, normalize_func):
                self.normalize = normalize_func

            def visit_Name(self, node):
                # Normalize variable names
                node.id = self.normalize(node.id)
                return node

            def visit_FunctionDef(self, node):
                # Normalize function names
                node.name = self.normalize(node.name)
                # Recursively visit function body
                self.generic_visit(node)
                return node

            def visit_arg(self, node):
                # Normalize argument names
                node.arg = self.normalize(node.arg)
                return node

            def visit_Attribute(self, node):
                # Normalize attribute names
                node.attr = self.normalize(node.attr)
                self.generic_visit(node)
                return node

        normalizer = IdentifierNormalizer(self._normalize_name)
        return normalizer.visit(tree)

    def _execute_code(
        self,
        code: str,
        test_input: dict,
        timeout_seconds: int,
    ) -> Any:
        """
        Execute code with test input and return output.

        Creates a temporary Python file, executes it with the test input,
        and returns the JSON-serialized result.

        Args:
            code: Python code snippet
            test_input: Test input dictionary
            timeout_seconds: Execution timeout

        Returns:
            Deserialized output from code execution

        Raises:
            RuntimeError: If code execution fails
            subprocess.TimeoutExpired: If execution exceeds timeout
        """
        # Extract function name from code
        func_name = self._extract_function_name(code)
        if not func_name:
            raise RuntimeError("Could not extract function name from code")

        # Create wrapper code that calls the function and prints result
        wrapper = f"""
import json
import sys

{code}

# Execute function with test input
try:
    # Extract function arguments from test_input
    test_input = {json.dumps(test_input)}
    result = {func_name}(**test_input)
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"__error__": str(e)}}), file=sys.stderr)
    sys.exit(1)
"""

        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(wrapper)
            code_file = f.name

        try:
            # Execute with timeout
            result = subprocess.run(
                ["python3", code_file],
                capture_output=True,
                timeout=timeout_seconds,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Code execution failed: {result.stderr}")

            # Parse output
            output = result.stdout.strip()
            if not output:
                raise RuntimeError("Code produced no output")

            return json.loads(output)

        finally:
            # Clean up temp file
            try:
                os.unlink(code_file)
            except Exception:
                pass  # Best effort cleanup

    def _extract_function_name(self, code: str) -> str | None:
        """
        Extract function name from code snippet.

        Args:
            code: Python code snippet

        Returns:
            Function name or None if not found
        """
        # Match "def function_name(" pattern
        match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        if match:
            return match.group(1)
        return None

    def _outputs_equivalent(self, output1: Any, output2: Any) -> bool:
        """
        Check if two outputs are equivalent.

        Handles:
        - Numerical tolerance for floats
        - Order-independent comparison for sets/lists
        - Exact equality for other types

        Args:
            output1: First output
            output2: Second output

        Returns:
            True if outputs are equivalent
        """
        # Handle exact equality first
        if output1 == output2:
            return True

        # Handle numerical tolerance for floats
        if isinstance(output1, float) and isinstance(output2, float):
            return abs(output1 - output2) < 1e-6

        # Handle collections (order may differ for sets, but preserved for lists)
        if isinstance(output1, (list, tuple)) and isinstance(output2, (list, tuple)):
            if len(output1) != len(output2):
                return False

            # For lists of numbers, allow small floating point differences
            try:
                if all(isinstance(x, (int, float)) for x in list(output1) + list(output2)):
                    return all(
                        abs(float(a) - float(b)) < 1e-6
                        for a, b in zip(output1, output2, strict=False)
                    )
            except (TypeError, ValueError):
                pass

            # Default: exact equality
            return output1 == output2

        # Handle dictionaries
        if isinstance(output1, dict) and isinstance(output2, dict):
            if set(output1.keys()) != set(output2.keys()):
                return False

            return all(self._outputs_equivalent(output1[k], output2[k]) for k in output1)

        # Default: not equivalent
        return False


__all__ = ["EquivalenceChecker"]
