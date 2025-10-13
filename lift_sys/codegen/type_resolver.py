"""Type resolution from IR types to Python type annotations."""

from __future__ import annotations

import re
from typing import Protocol

from ..ir.models import Parameter
from .models import TypeAnnotation


class TypeResolutionError(Exception):
    """Cannot resolve a type hint to Python type."""

    def __init__(self, type_hint: str, reason: str):
        self.type_hint = type_hint
        self.reason = reason
        super().__init__(f"Cannot resolve type '{type_hint}': {reason}")


class TypeResolver(Protocol):
    """Protocol for resolving IR type hints to Python types."""

    def resolve(self, type_hint: str) -> TypeAnnotation:
        """Resolve a type hint from IR to Python annotation.

        Args:
            type_hint: Type hint string from IR (e.g., "list[int]", "str | None")

        Returns:
            TypeAnnotation with resolved type and required imports.

        Raises:
            TypeResolutionError: If type cannot be resolved.
        """
        ...

    def resolve_parameter_type(self, param: Parameter) -> TypeAnnotation:
        """Resolve type for a function parameter."""
        ...

    def resolve_return_type(self, return_hint: str | None) -> TypeAnnotation:
        """Resolve return type annotation."""
        ...


class DefaultTypeResolver:
    """Default implementation of TypeResolver for Python 3.10+."""

    def __init__(self, target_version: str = "3.10"):
        """Initialize with target Python version.

        Args:
            target_version: Python version string (e.g., "3.10", "3.11")
        """
        self.target_version = target_version
        self._type_map = self._build_type_map()

    def resolve(self, type_hint: str) -> TypeAnnotation:
        """Resolve type hint with Python 3.10+ syntax.

        Handles:
        - Simple types: "str", "int", "bool"
        - Union types: "str | None", "int | float"
        - Generic types: "list[int]", "dict[str, int]"
        - Complex types: "Callable[[int], str]"

        Args:
            type_hint: Type hint string from IR.

        Returns:
            TypeAnnotation with resolved type.

        Raises:
            TypeResolutionError: If type cannot be resolved.
        """
        if not type_hint or type_hint.strip() == "":
            raise TypeResolutionError(type_hint, "Empty type hint")

        type_hint = type_hint.strip()

        # Check if already a valid Python type with generics
        if self._is_python_type(type_hint):
            # Check if it's a generic type
            if "[" in type_hint and "]" in type_hint:
                import re

                match = re.match(r"^(\w+)\[.+\]$", type_hint)
                if match:
                    return TypeAnnotation(
                        annotation=type_hint, is_generic=True, origin_type=match.group(1)
                    )
            return TypeAnnotation(annotation=type_hint)

        # Try mapping IR type names to Python types
        mapped = self._type_map.get(type_hint.lower())
        if mapped:
            return TypeAnnotation(annotation=mapped)

        # Handle union types: "string | None" → "str | None"
        if "|" in type_hint:
            return self._resolve_union(type_hint)

        # Handle generic types: "array[integer]" → "list[int]"
        if "[" in type_hint and "]" in type_hint:
            return self._resolve_generic(type_hint)

        # If no mapping found, return as-is with warning
        # This allows custom types to pass through
        return TypeAnnotation(
            annotation=type_hint,
            imports=set(),
        )

    def resolve_parameter_type(self, param: Parameter) -> TypeAnnotation:
        """Resolve type for a function parameter.

        Args:
            param: Parameter with type hint.

        Returns:
            TypeAnnotation for the parameter.
        """
        return self.resolve(param.type_hint)

    def resolve_return_type(self, return_hint: str | None) -> TypeAnnotation:
        """Resolve return type annotation.

        Args:
            return_hint: Return type hint from IR, or None.

        Returns:
            TypeAnnotation (defaults to "None" if no hint provided).
        """
        if not return_hint:
            return TypeAnnotation(annotation="None")

        return self.resolve(return_hint)

    def _build_type_map(self) -> dict[str, str]:
        """Build mapping of IR types to Python types.

        Returns:
            Dictionary mapping IR type names to Python type names.
        """
        return {
            # Primitives
            "string": "str",
            "str": "str",
            "integer": "int",
            "int": "int",
            "float": "float",
            "boolean": "bool",
            "bool": "bool",
            "none": "None",
            "null": "None",
            # Collections
            "array": "list",
            "list": "list",
            "dictionary": "dict",
            "dict": "dict",
            "set": "set",
            "tuple": "tuple",
            # Special
            "any": "Any",
            "object": "Any",
        }

    def _is_python_type(self, type_hint: str) -> bool:
        """Check if type hint is already a valid Python type.

        Args:
            type_hint: Type hint to check.

        Returns:
            True if already valid Python type syntax.
        """
        # Simple built-in types
        if type_hint in {"str", "int", "float", "bool", "None", "bytes"}:
            return True

        # Generic types with Python syntax
        if re.match(r"^(list|dict|set|tuple|frozenset)\[.+\]$", type_hint):
            return True

        # Union types with Python syntax
        if " | " in type_hint:
            parts = [p.strip() for p in type_hint.split("|")]
            return all(self._is_python_type(p) for p in parts)

        return False

    def _resolve_union(self, type_hint: str) -> TypeAnnotation:
        """Resolve union type annotations.

        Args:
            type_hint: Union type string (e.g., "string | None")

        Returns:
            TypeAnnotation with resolved union.
        """
        parts = [p.strip() for p in type_hint.split("|")]
        resolved_parts = []

        for part in parts:
            try:
                resolved = self.resolve(part)
                resolved_parts.append(resolved.annotation)
            except TypeResolutionError:
                # If part can't be resolved, use as-is
                resolved_parts.append(part)

        annotation = " | ".join(resolved_parts)
        return TypeAnnotation(annotation=annotation)

    def _resolve_generic(self, type_hint: str) -> TypeAnnotation:
        """Resolve generic type annotations.

        Args:
            type_hint: Generic type string (e.g., "array[integer]")

        Returns:
            TypeAnnotation with resolved generic.
        """
        # Extract base type and type parameters
        match = re.match(r"^(\w+)\[(.+)\]$", type_hint)
        if not match:
            raise TypeResolutionError(type_hint, "Invalid generic type syntax")

        base_type = match.group(1)
        type_params = match.group(2)

        # Resolve base type
        resolved_base = self._type_map.get(base_type.lower(), base_type)

        # Resolve type parameters
        # Handle nested generics and multiple parameters
        if "," in type_params:
            # Multiple type parameters (e.g., "dict[str, int]")
            params = [p.strip() for p in type_params.split(",")]
            resolved_params = []
            for param in params:
                try:
                    resolved = self.resolve(param)
                    resolved_params.append(resolved.annotation)
                except TypeResolutionError:
                    resolved_params.append(param)
            params_str = ", ".join(resolved_params)
        else:
            # Single type parameter (e.g., "list[int]")
            try:
                resolved = self.resolve(type_params)
                params_str = resolved.annotation
            except TypeResolutionError:
                params_str = type_params

        annotation = f"{resolved_base}[{params_str}]"
        return TypeAnnotation(
            annotation=annotation,
            is_generic=True,
            origin_type=resolved_base,
        )
