"""Code validation layer to catch common bugs in generated code."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    """Represents a potential issue in generated code."""

    severity: str  # "error", "warning", "info"
    category: str  # "missing_return", "wrong_pattern", "logic_error"
    message: str
    suggestion: str | None = None


class CodeValidator:
    """Validates generated code and provides feedback for retry."""

    def __init__(self):
        """Initialize validator with known patterns."""
        self.validators = {
            "find": self._validate_find_pattern,
            "search": self._validate_find_pattern,
            "index": self._validate_find_pattern,
            "type": self._validate_type_pattern,
            "check_type": self._validate_type_pattern,
            "get_type": self._validate_type_pattern,
        }

    def validate(
        self, code: str, function_name: str, context: dict | None = None
    ) -> list[ValidationIssue]:
        """
        Validate generated code and return list of issues.

        Args:
            code: Generated Python code
            function_name: Name of the function
            context: Additional context (prompt, expected behavior, etc.)

        Returns:
            List of validation issues found
        """
        issues = []

        # Run pattern-specific validators
        for pattern, validator in self.validators.items():
            if pattern in function_name.lower():
                issues.extend(validator(code, function_name, context))

        # Run general validators
        issues.extend(self._validate_explicit_returns(code))
        issues.extend(self._validate_no_pass_statements(code))

        return issues

    def _validate_find_pattern(
        self, code: str, function_name: str, context: dict | None = None
    ) -> list[ValidationIssue]:
        """Validate find/search/index patterns."""
        issues = []

        # Check for explicit return -1
        if "return -1" not in code and "return None" not in code:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="missing_return",
                    message="Find/search function missing explicit failure return value",
                    suggestion="Add 'return -1' after the loop to handle not-found case",
                )
            )

        # Check for enumerate without start parameter
        if re.search(r"enumerate\([^)]+,\s*1\)", code):
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="wrong_pattern",
                    message="enumerate should start from 0, not 1",
                    suggestion="Use enumerate(lst) without start parameter",
                )
            )

        # AST-based validation: Check for return placement in loops
        loop_issues = self._validate_loop_return_placement(code)
        issues.extend(loop_issues)

        return issues

    def _validate_type_pattern(
        self, code: str, function_name: str, context: dict | None = None
    ) -> list[ValidationIssue]:
        """Validate type checking patterns."""
        issues = []

        # Check for type().__name__ usage
        if "type(" in code and "__name__" in code:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="wrong_pattern",
                    message="Using type().__name__ instead of literal return value",
                    suggestion="Return literal strings ('int', 'str', 'list', 'other') instead of computed type names",
                )
            )

        # Check for exact 'other' string
        if context and "other" in str(context):
            if 'return "other"' not in code and "return 'other'" not in code:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        category="missing_literal",
                        message="Missing literal 'other' return statement",
                        suggestion="Add 'return \"other\"' in the else clause for non-matching types",
                    )
                )

        return issues

    def _validate_explicit_returns(self, code: str) -> list[ValidationIssue]:
        """Check for missing explicit return statements."""
        issues = []

        # Count def and return statements
        def_count = code.count("def ")
        return_count = code.count("return ")

        # Simple heuristic: function should have at least one return
        if def_count > 0 and return_count == 0:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="missing_return",
                    message="Function has no explicit return statements",
                    suggestion="Add explicit return statements for all code paths",
                )
            )

        # Check for implicit None returns (no return at end of function)
        lines = code.strip().split("\n")
        if lines and not any(
            line.strip().startswith("return") for line in lines[-5:]
        ):  # Check last 5 lines
            # If there's an if/for/while at the end, we need a return after it
            for line in lines[-5:]:
                if line.strip() and not line.strip().startswith("#"):
                    if any(line.strip().startswith(kw) for kw in ["if", "for", "while", "elif"]):
                        issues.append(
                            ValidationIssue(
                                severity="warning",
                                category="implicit_return",
                                message="Function may have implicit None return after control flow",
                                suggestion="Add explicit return statement after loops/conditionals",
                            )
                        )
                        break

        return issues

    def _validate_no_pass_statements(self, code: str) -> list[ValidationIssue]:
        """Check for pass statements (stubs)."""
        issues = []

        if "\n    pass" in code or "\n\tpass" in code:
            issues.append(
                ValidationIssue(
                    severity="error",
                    category="incomplete",
                    message="Function contains 'pass' statement - incomplete implementation",
                    suggestion="Replace 'pass' with actual implementation",
                )
            )

        return issues

    def _extract_loop_body(self, code: str) -> str | None:
        """Extract the body of a for loop (simple heuristic)."""
        match = re.search(r"for .+ in .+:\n((?:    .+\n)+)", code)
        if match:
            return match.group(1)
        return None

    def _validate_loop_return_placement(self, code: str) -> list[ValidationIssue]:
        """
        AST-based validation to detect return statements at wrong indentation in loops.

        This catches bugs like:
            for i in range(n):
                if condition:
                    return value
                return fallback  # ❌ Wrong! This is inside the loop!

        Should be:
            for i in range(n):
                if condition:
                    return value
            return fallback  # ✅ Correct! After the loop
        """
        issues = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return issues  # Can't parse, let other validation handle it

        # Find all for loops
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check for return statements that are direct children of the for loop body
                # (not inside if/while/etc)
                for stmt in node.body:
                    if isinstance(stmt, ast.Return):
                        # Found a return statement directly in loop body (not nested in if/etc)
                        issues.append(
                            ValidationIssue(
                                severity="error",
                                category="control_flow_error",
                                message="Return statement directly in loop body (wrong indentation level)",
                                suggestion="Move the fallback return statement AFTER the loop, not inside it. The return should only execute after the loop completes without finding a match.",
                            )
                        )
                    elif isinstance(stmt, ast.If):
                        # Check if there's a return after the if (common pattern error)
                        stmt_index = node.body.index(stmt)
                        if stmt_index + 1 < len(node.body):
                            next_stmt = node.body[stmt_index + 1]
                            if isinstance(next_stmt, ast.Return):
                                # Return immediately after if - likely wrong placement
                                issues.append(
                                    ValidationIssue(
                                        severity="error",
                                        category="control_flow_error",
                                        message="Return statement at same level as if statement inside loop (likely wrong indentation)",
                                        suggestion="The fallback return should be AFTER the entire loop, not inside it at the same level as the if statement.",
                                    )
                                )

        return issues

    def format_issues_for_retry(self, issues: list[ValidationIssue]) -> str:
        """Format validation issues as feedback for retry attempt."""
        if not issues:
            return ""

        feedback = "\n\nVALIDATION ERRORS FOUND:\n"
        for i, issue in enumerate(issues, 1):
            feedback += f"\n{i}. [{issue.severity.upper()}] {issue.category}: {issue.message}"
            if issue.suggestion:
                feedback += f"\n   Suggestion: {issue.suggestion}"

        feedback += "\n\nPlease regenerate the code addressing these issues."
        return feedback


# Convenience function
def validate_code(
    code: str, function_name: str, context: dict | None = None
) -> list[ValidationIssue]:
    """Validate generated code and return issues."""
    validator = CodeValidator()
    return validator.validate(code, function_name, context)
