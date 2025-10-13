"""Data models for code generation."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ir.models import TypedHole


@dataclass
class GeneratedCode:
    """Result of code generation."""

    source_code: str
    """The generated Python source code."""

    language: str = "python"
    """Target language (always 'python' for now)."""

    ir_version: int | None = None
    """Version of the IR this was generated from."""

    metadata: dict[str, object] = field(default_factory=dict)
    """Additional metadata (imports, dependencies, etc.)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings during generation."""


@dataclass
class ValidationResult:
    """Result of IR validation before generation."""

    is_valid: bool
    """Whether IR is ready for code generation."""

    errors: list[str] = field(default_factory=list)
    """Blocking errors that prevent generation."""

    warnings: list[str] = field(default_factory=list)
    """Non-blocking issues to be aware of."""

    unresolved_holes: list[TypedHole] = field(default_factory=list)
    """Typed holes that must be resolved."""

    missing_types: list[str] = field(default_factory=list)
    """Parameters or returns without type hints."""


@dataclass
class TypeAnnotation:
    """Resolved type annotation for Python code."""

    annotation: str
    """The Python type annotation string (e.g., "list[int]")."""

    imports: set[str] = field(default_factory=set)
    """Required imports (e.g., {"from typing import Any"})."""

    is_generic: bool = False
    """Whether this is a generic type."""

    origin_type: str | None = None
    """Origin type for generics (e.g., "list" for "list[int]")."""


@dataclass
class Docstring:
    """Generated docstring for a function."""

    content: str
    """The formatted docstring content."""

    style: str = "google"
    """Docstring style used."""
