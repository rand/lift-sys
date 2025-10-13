"""Assertion injection from IR assertions to runtime checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from ..ir.models import AssertClause

AssertionMode = Literal["assert", "raise", "log", "comment"]
AssertionPosition = Literal["precondition", "postcondition", "invariant"]


@dataclass
class InjectedAssertion:
    """An assertion injected into generated code."""

    code_lines: list[str]
    """Lines of code implementing the assertion."""

    position: AssertionPosition
    """Where this assertion should be placed."""

    original_predicate: str
    """Original assertion predicate from IR."""

    rationale: str | None = None
    """Optional explanation for the assertion."""


class AssertionInjector(Protocol):
    """Protocol for injecting assertions into generated code."""

    def inject(self, assertion: AssertClause, mode: AssertionMode = "assert") -> InjectedAssertion:
        """Convert an assertion clause to executable code.

        Args:
            assertion: The assertion clause from IR.
            mode: How to handle assertion violations.

        Returns:
            InjectedAssertion with code and metadata.
        """
        ...

    def inject_all(
        self, assertions: list[AssertClause], mode: AssertionMode = "assert"
    ) -> list[InjectedAssertion]:
        """Inject multiple assertions."""
        ...


class DefaultAssertionInjector:
    """Default implementation for Python assertion injection."""

    def __init__(self, indent: str = "    "):
        """Initialize with indentation style.

        Args:
            indent: Indentation string (default: 4 spaces).
        """
        self.indent = indent

    def inject(self, assertion: AssertClause, mode: AssertionMode = "assert") -> InjectedAssertion:
        """Inject assertion as Python code.

        Supports multiple modes:
        - assert: `assert x > 0, "x must be positive"`
        - raise: `if not (x > 0): raise ValueError("x must be positive")`
        - log: `if not (x > 0): logger.warning("Assertion failed: x > 0")`
        - comment: `# Assertion: x > 0 (x must be positive)`

        Args:
            assertion: Assertion clause from IR.
            mode: How to handle assertion violations.

        Returns:
            InjectedAssertion with code lines and metadata.
        """
        predicate = assertion.predicate.strip()
        rationale = assertion.rationale or "Assertion from specification"

        position = self._infer_position(assertion)

        if mode == "assert":
            code_lines = [f'assert {predicate}, "{rationale}"']
        elif mode == "raise":
            code_lines = [
                f"if not ({predicate}):",
                f'{self.indent}raise ValueError("{rationale}")',
            ]
        elif mode == "log":
            code_lines = [
                f"if not ({predicate}):",
                f'{self.indent}logger.warning("Assertion failed: {predicate}")',
            ]
        elif mode == "comment":
            code_lines = [f"# Assertion: {predicate} ({rationale})"]
        else:
            # Default to assert mode
            code_lines = [f'assert {predicate}, "{rationale}"']

        return InjectedAssertion(
            code_lines=code_lines,
            position=position,
            original_predicate=predicate,
            rationale=rationale,
        )

    def inject_all(
        self, assertions: list[AssertClause], mode: AssertionMode = "assert"
    ) -> list[InjectedAssertion]:
        """Inject multiple assertions.

        Args:
            assertions: List of assertion clauses.
            mode: How to handle assertion violations.

        Returns:
            List of injected assertions.
        """
        return [self.inject(assertion, mode) for assertion in assertions]

    def _infer_position(self, assertion: AssertClause) -> AssertionPosition:
        """Infer where assertion should be placed.

        Uses heuristics based on assertion content:
        - References to parameters → precondition
        - References to return value → postcondition
        - References to self/state → invariant

        Args:
            assertion: Assertion clause to analyze.

        Returns:
            Inferred position for the assertion.
        """
        predicate = assertion.predicate.lower()

        # Check for return value references
        if any(kw in predicate for kw in ["return", "result", "output"]):
            return "postcondition"

        # Check for state/invariant references
        if any(kw in predicate for kw in ["self.", "state", "invariant"]):
            return "invariant"

        # Default to precondition (checks on inputs)
        return "precondition"
