"""Docstring generation from IR intent and signatures."""

from __future__ import annotations

from typing import Protocol

from ..ir.models import IntentClause, SigClause
from .models import Docstring


class DocstringGenerator(Protocol):
    """Protocol for generating docstrings from IR."""

    def generate(self, intent: IntentClause, signature: SigClause) -> Docstring:
        """Generate docstring from intent and signature.

        Args:
            intent: The intent clause describing purpose.
            signature: The function signature for parameter docs.

        Returns:
            Formatted docstring.
        """
        ...


class DefaultDocstringGenerator:
    """Default docstring generator using Google style."""

    def __init__(self, style: str = "google"):
        """Initialize with docstring style.

        Args:
            style: Docstring style ("google", "numpy", "sphinx")
        """
        self.style = style

    def generate(self, intent: IntentClause, signature: SigClause) -> Docstring:
        """Generate Google-style docstring.

        Args:
            intent: Intent clause with summary and rationale.
            signature: Function signature with parameters and return type.

        Returns:
            Formatted docstring with summary, args, and returns sections.
        """
        if self.style == "google":
            return self._generate_google_style(intent, signature)
        else:
            # For now, only Google style is supported
            return self._generate_google_style(intent, signature)

    def _generate_google_style(self, intent: IntentClause, signature: SigClause) -> Docstring:
        """Generate Google-style docstring.

        Format:
        '''Summary line.

        Extended description (if rationale provided).

        Args:
            param1: Description
            param2: Description

        Returns:
            Return type and description
        '''
        """
        lines = []

        # Summary (from intent)
        summary = intent.summary.strip()
        if not summary.endswith("."):
            summary += "."
        lines.append(f'"""{summary}')

        # Extended description (from rationale)
        if intent.rationale:
            lines.append("")
            rationale = intent.rationale.strip()
            lines.append(rationale)

        # Args section
        if signature.parameters:
            lines.append("")
            lines.append("Args:")
            for param in signature.parameters:
                desc = param.description or "Parameter value"
                lines.append(f"    {param.name}: {desc}")

        # Returns section
        if signature.returns and signature.returns.lower() != "none":
            lines.append("")
            lines.append("Returns:")
            lines.append(f"    {signature.returns}")

        lines.append('"""')

        content = "\n".join(lines)
        return Docstring(content=content, style=self.style)
