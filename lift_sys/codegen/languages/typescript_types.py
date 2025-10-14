"""TypeScript type resolution and mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class TypeScriptType:
    """Represents a TypeScript type annotation.

    Attributes:
        annotation: TypeScript type string (e.g., "string", "number[]", "Promise<User>")
        is_generic: Whether this is a generic type
        is_union: Whether this is a union type
        is_interface: Whether this should be an interface
        needs_import: Whether this type needs an import statement
        import_source: Source module for import (if needed)
    """

    annotation: str
    is_generic: bool = False
    is_union: bool = False
    is_interface: bool = False
    needs_import: bool = False
    import_source: str | None = None


class TypeScriptTypeResolver:
    """Resolves IR types to TypeScript type annotations.

    Handles mapping from Python/IR type hints to TypeScript types, including:
    - Basic types (str → string, int → number)
    - Collections (list → Array, dict → Record)
    - Generics (list[T] → Array<T>)
    - Union types (str | int → string | number)
    - Custom types (User → User interface)
    """

    # Basic type mappings
    BASIC_TYPE_MAP = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "None": "null",
        "Any": "any",
        "object": "any",
        # Python collections - with proper generic defaults
        "list": "Array<any>",
        "dict": "Record<string, any>",
        "set": "Set<any>",
        "tuple": "readonly any[]",
        # Common Python types
        "bytes": "Uint8Array",
        "bytearray": "Uint8Array",
        # TypeScript-specific
        "undefined": "undefined",
        "void": "void",
        "never": "never",
        "unknown": "unknown",
    }

    def __init__(self):
        """Initialize TypeScript type resolver."""
        self.custom_types: dict[str, str] = {}  # Custom type mappings

    def resolve(self, type_hint: str) -> TypeScriptType:
        """Resolve IR type hint to TypeScript type.

        Args:
            type_hint: Type hint string from IR (e.g., "str", "list[int]", "dict[str, Any]")

        Returns:
            TypeScriptType with appropriate TypeScript annotation

        Examples:
            >>> resolver = TypeScriptTypeResolver()
            >>> resolver.resolve("str").annotation
            'string'
            >>> resolver.resolve("list[int]").annotation
            'Array<number>'
            >>> resolver.resolve("dict[str, int]").annotation
            'Record<string, number>'
            >>> resolver.resolve("str | int").annotation
            'string | number'
        """
        # Trim whitespace
        type_hint = type_hint.strip() if type_hint else ""

        # Handle empty or placeholder types
        if not type_hint:
            return TypeScriptType("any", needs_import=False)

        # Handle TypedHole (placeholder for unknown types)
        if "TypedHole" in type_hint or type_hint == "...":
            return TypeScriptType("any /* TODO: infer type */", needs_import=False)

        # Handle union types (str | int)
        if "|" in type_hint:
            return self._resolve_union_type(type_hint)

        # Handle generic types (list[T], dict[K, V])
        if "[" in type_hint:
            # Check for malformed generic (missing closing bracket)
            if "]" not in type_hint:
                return TypeScriptType("any", needs_import=False)
            return self._resolve_generic_type(type_hint)

        # Handle basic types
        if type_hint in self.BASIC_TYPE_MAP:
            return TypeScriptType(
                self.BASIC_TYPE_MAP[type_hint],
                needs_import=False,
            )

        # Handle custom types (User, MyClass)
        return self._resolve_custom_type(type_hint)

    def _resolve_union_type(self, type_hint: str) -> TypeScriptType:
        """Resolve union type (e.g., 'str | int' → 'string | number').

        Args:
            type_hint: Union type string

        Returns:
            TypeScriptType with union annotation
        """
        parts = [part.strip() for part in type_hint.split("|")]
        resolved_parts = [self.resolve(part).annotation for part in parts]
        return TypeScriptType(
            " | ".join(resolved_parts),
            is_union=True,
            needs_import=False,
        )

    def _resolve_generic_type(self, type_hint: str) -> TypeScriptType:
        """Resolve generic type (e.g., 'list[int]' → 'Array<number>').

        Args:
            type_hint: Generic type string

        Returns:
            TypeScriptType with generic annotation
        """
        # Extract base type and type parameters
        match = re.match(r"(\w+)\[(.+)\]", type_hint)
        if not match:
            # Fallback if parsing fails
            return TypeScriptType("any", needs_import=False)

        base_type = match.group(1)
        type_params = match.group(2)

        # Resolve base type
        base_ts_type = self.BASIC_TYPE_MAP.get(base_type, base_type)

        # Handle specific generic types
        if base_type == "list":
            # list[int] → Array<number>
            inner_type = self.resolve(type_params).annotation
            return TypeScriptType(
                f"Array<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "dict":
            # dict[str, int] → Record<string, number>
            # Split type parameters by comma (handling nested generics)
            key_type, value_type = self._split_type_parameters(type_params)
            key_ts = self.resolve(key_type).annotation
            value_ts = self.resolve(value_type).annotation
            return TypeScriptType(
                f"Record<{key_ts}, {value_ts}>",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "tuple":
            # tuple[int, str] → readonly [number, string]
            types = [t.strip() for t in type_params.split(",")]
            ts_types = [self.resolve(t).annotation for t in types]
            return TypeScriptType(
                f"readonly [{', '.join(ts_types)}]",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "set":
            # set[int] → Set<number>
            inner_type = self.resolve(type_params).annotation
            return TypeScriptType(
                f"Set<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )

        else:
            # Custom generic (e.g., Promise[T], Optional[T])
            inner_type = self.resolve(type_params).annotation
            return TypeScriptType(
                f"{base_ts_type}<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )

    def _resolve_custom_type(self, type_hint: str) -> TypeScriptType:
        """Resolve custom type (e.g., 'User' → 'User' interface).

        Args:
            type_hint: Custom type name

        Returns:
            TypeScriptType with custom type annotation
        """
        # Check if it's a known custom type
        if type_hint in self.custom_types:
            return TypeScriptType(
                self.custom_types[type_hint],
                is_interface=True,
                needs_import=True,
            )

        # Default: treat as interface with same name
        return TypeScriptType(
            type_hint,
            is_interface=True,
            needs_import=False,  # Assume defined in same file
        )

    def _split_type_parameters(self, type_params: str) -> tuple[str, str]:
        """Split type parameters handling nested generics.

        Args:
            type_params: Type parameters string (e.g., "str, int" or "str, list[int]")

        Returns:
            Tuple of (key_type, value_type)

        Examples:
            >>> resolver = TypeScriptTypeResolver()
            >>> resolver._split_type_parameters("str, int")
            ('str', 'int')
            >>> resolver._split_type_parameters("str, list[int]")
            ('str', 'list[int]')
        """
        # Simple case: no nested generics
        if "[" not in type_params:
            parts = [p.strip() for p in type_params.split(",", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
            return type_params, "any"

        # Complex case: handle nested generics
        depth = 0
        split_pos = -1
        for i, char in enumerate(type_params):
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif char == "," and depth == 0:
                split_pos = i
                break

        if split_pos == -1:
            return type_params, "any"

        return type_params[:split_pos].strip(), type_params[split_pos + 1 :].strip()

    def register_custom_type(self, name: str, ts_type: str):
        """Register a custom type mapping.

        Args:
            name: Type name in IR
            ts_type: Corresponding TypeScript type
        """
        self.custom_types[name] = ts_type

    def format_function_signature(
        self,
        name: str,
        parameters: list[tuple[str, str]],
        return_type: str,
        is_async: bool = False,
    ) -> str:
        """Format a TypeScript function signature.

        Args:
            name: Function name
            parameters: List of (param_name, type_hint) tuples
            return_type: Return type hint
            is_async: Whether function is async

        Returns:
            Formatted TypeScript function signature

        Example:
            >>> resolver = TypeScriptTypeResolver()
            >>> resolver.format_function_signature(
            ...     "greet",
            ...     [("name", "str"), ("age", "int")],
            ...     "str",
            ... )
            'function greet(name: string, age: number): string'
        """
        # Resolve parameter types
        param_strs = []
        for param_name, type_hint in parameters:
            ts_type = self.resolve(type_hint).annotation
            param_strs.append(f"{param_name}: {ts_type}")

        # Resolve return type
        ts_return = self.resolve(return_type).annotation

        # Handle async functions
        if is_async:
            if not ts_return.startswith("Promise<"):
                ts_return = f"Promise<{ts_return}>"

        params_str = ", ".join(param_strs)
        async_prefix = "async " if is_async else ""
        return f"{async_prefix}function {name}({params_str}): {ts_return}"

    def format_interface(self, name: str, fields: dict[str, str]) -> str:
        """Format a TypeScript interface definition.

        Args:
            name: Interface name
            fields: Dictionary of field_name → type_hint

        Returns:
            Formatted TypeScript interface

        Example:
            >>> resolver = TypeScriptTypeResolver()
            >>> print(resolver.format_interface(
            ...     "User",
            ...     {"name": "str", "age": "int", "email": "str | None"}
            ... ))
            interface User {
              name: string;
              age: number;
              email: string | null;
            }
        """
        lines = [f"interface {name} {{"]
        for field_name, type_hint in fields.items():
            ts_type = self.resolve(type_hint).annotation
            lines.append(f"  {field_name}: {ts_type};")
        lines.append("}")
        return "\n".join(lines)

    def format_type_alias(self, name: str, type_hint: str) -> str:
        """Format a TypeScript type alias.

        Args:
            name: Type alias name
            type_hint: Type definition

        Returns:
            Formatted TypeScript type alias

        Example:
            >>> resolver = TypeScriptTypeResolver()
            >>> resolver.format_type_alias("UserId", "str")
            'type UserId = string;'
            >>> resolver.format_type_alias("Status", "str | int")
            'type Status = string | number;'
        """
        ts_type = self.resolve(type_hint).annotation
        return f"type {name} = {ts_type};"
