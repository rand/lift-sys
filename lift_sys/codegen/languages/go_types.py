"""Go type resolution and mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GoType:
    """Represents a Go type annotation.

    Attributes:
        annotation: Go type string (e.g., "string", "[]int", "map[string]User")
        is_generic: Whether this is a generic type (Go 1.18+)
        is_pointer: Whether this is a pointer type
        is_interface: Whether this should be an interface
        needs_import: Whether this type needs an import statement
        import_source: Source package for import (if needed)
    """

    annotation: str
    is_generic: bool = False
    is_pointer: bool = False
    is_interface: bool = False
    needs_import: bool = False
    import_source: str | None = None


class GoTypeResolver:
    """Resolves IR types to Go type annotations.

    Handles mapping from Python/IR type hints to Go types, including:
    - Basic types (str → string, int → int)
    - Collections (list → []T, dict → map[K]V)
    - Pointers (*User)
    - Interfaces (error, io.Reader)
    - Custom types (User struct)
    """

    # Basic type mappings
    BASIC_TYPE_MAP = {
        "str": "string",
        "int": "int",
        "float": "float64",
        "bool": "bool",
        "None": "nil",
        "Any": "interface{}",
        "object": "interface{}",
        # Python collections - with proper Go defaults
        "list": "[]interface{}",
        "dict": "map[string]interface{}",
        "set": "map[interface{}]struct{}",
        "tuple": "[]interface{}",  # Go doesn't have tuples
        # Python bytes
        "bytes": "[]byte",
        "bytearray": "[]byte",
        # Go-specific
        "error": "error",
        "void": "",  # Go doesn't have void, functions just don't return
    }

    def __init__(self):
        """Initialize Go type resolver."""
        self.custom_types: dict[str, str] = {}  # Custom type mappings

    def resolve(self, type_hint: str) -> GoType:
        """Resolve IR type hint to Go type.

        Args:
            type_hint: Type hint string from IR (e.g., "str", "list[int]", "dict[str, Any]")

        Returns:
            GoType with appropriate Go annotation

        Examples:
            >>> resolver = GoTypeResolver()
            >>> resolver.resolve("str").annotation
            'string'
            >>> resolver.resolve("list[int]").annotation
            '[]int'
            >>> resolver.resolve("dict[str, int]").annotation
            'map[string]int'
        """
        # Trim whitespace
        type_hint = type_hint.strip() if type_hint else ""

        # Handle empty or placeholder types
        if not type_hint:
            return GoType("interface{}", needs_import=False)

        # Handle TypedHole (placeholder for unknown types)
        if "TypedHole" in type_hint or type_hint == "...":
            return GoType("interface{} /* TODO: infer type */", needs_import=False)

        # Handle union types (str | int) - Go doesn't have unions, use interface{}
        if "|" in type_hint:
            return GoType("interface{} /* union type not supported in Go */", needs_import=False)

        # Handle generic types (list[T], dict[K, V])
        if "[" in type_hint:
            # Check for malformed generic (missing closing bracket)
            if "]" not in type_hint:
                return GoType("interface{}", needs_import=False)
            return self._resolve_generic_type(type_hint)

        # Handle basic types
        if type_hint in self.BASIC_TYPE_MAP:
            return GoType(
                self.BASIC_TYPE_MAP[type_hint],
                needs_import=False,
            )

        # Handle custom types (User, MyStruct)
        return self._resolve_custom_type(type_hint)

    def _resolve_generic_type(self, type_hint: str) -> GoType:
        """Resolve generic type (e.g., 'list[int]' → '[]int').

        Args:
            type_hint: Generic type string

        Returns:
            GoType with generic annotation
        """
        # Extract base type and type parameters
        match = re.match(r"(\w+)\[(.+)\]", type_hint)
        if not match:
            # Fallback if parsing fails
            return GoType("interface{}", needs_import=False)

        base_type = match.group(1)
        type_params = match.group(2)

        # Handle specific generic types
        if base_type == "list":
            # list[int] → []int
            inner_type = self.resolve(type_params).annotation
            return GoType(
                f"[]{inner_type}",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "dict":
            # dict[str, int] → map[string]int
            # Split type parameters by comma (handling nested generics)
            key_type, value_type = self._split_type_parameters(type_params)
            key_go = self.resolve(key_type).annotation
            value_go = self.resolve(value_type).annotation
            return GoType(
                f"map[{key_go}]{value_go}",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "tuple":
            # tuple[int, str] → []interface{} (Go doesn't have tuples)
            return GoType(
                "[]interface{} /* tuple not supported in Go */",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "set":
            # set[int] → map[int]struct{} (Go idiom for sets)
            inner_type = self.resolve(type_params).annotation
            return GoType(
                f"map[{inner_type}]struct{{}}",
                is_generic=True,
                needs_import=False,
            )

        else:
            # Custom generic (e.g., Optional[T], Result[T])
            # For Go generics (1.18+), this would be [T]
            inner_type = self.resolve(type_params).annotation
            # Most Python generics don't have Go equivalents, use interface{}
            return GoType(
                f"interface{{}} /* {base_type}[{inner_type}] not supported */",
                is_generic=True,
                needs_import=False,
            )

    def _resolve_custom_type(self, type_hint: str) -> GoType:
        """Resolve custom type (e.g., 'User' → 'User' struct).

        Args:
            type_hint: Custom type name

        Returns:
            GoType with custom type annotation
        """
        # Check if it's a known custom type
        if type_hint in self.custom_types:
            return GoType(
                self.custom_types[type_hint],
                is_interface=True,
                needs_import=True,
            )

        # Default: treat as struct with same name
        return GoType(
            type_hint,
            is_interface=False,
            needs_import=False,  # Assume defined in same package
        )

    def _split_type_parameters(self, type_params: str) -> tuple[str, str]:
        """Split type parameters handling nested generics.

        Args:
            type_params: Type parameters string (e.g., "str, int" or "str, list[int]")

        Returns:
            Tuple of (key_type, value_type)

        Examples:
            >>> resolver = GoTypeResolver()
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
            return type_params, "interface{}"

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
            return type_params, "interface{}"

        return type_params[:split_pos].strip(), type_params[split_pos + 1 :].strip()

    def register_custom_type(self, name: str, go_type: str):
        """Register a custom type mapping.

        Args:
            name: Type name in IR
            go_type: Corresponding Go type
        """
        self.custom_types[name] = go_type

    def format_function_signature(
        self,
        name: str,
        parameters: list[tuple[str, str]],
        return_type: str,
        returns_error: bool = False,
    ) -> str:
        """Format a Go function signature.

        Args:
            name: Function name
            parameters: List of (param_name, type_hint) tuples
            return_type: Return type hint
            returns_error: Whether function returns error as second value

        Returns:
            Formatted Go function signature

        Example:
            >>> resolver = GoTypeResolver()
            >>> resolver.format_function_signature(
            ...     "Greet",
            ...     [("name", "str"), ("age", "int")],
            ...     "str",
            ... )
            'func Greet(name string, age int) string'
            >>> resolver.format_function_signature(
            ...     "ReadFile",
            ...     [("path", "str")],
            ...     "bytes",
            ...     returns_error=True,
            ... )
            'func ReadFile(path string) ([]byte, error)'
        """
        # Resolve parameter types
        param_strs = []
        for param_name, type_hint in parameters:
            go_type = self.resolve(type_hint).annotation
            param_strs.append(f"{param_name} {go_type}")

        # Resolve return type
        go_return = self.resolve(return_type).annotation

        # Handle multiple return values (common in Go)
        if returns_error:
            if go_return:
                return_sig = f"({go_return}, error)"
            else:
                return_sig = "error"
        else:
            if go_return:
                return_sig = go_return
            else:
                return_sig = ""

        params_str = ", ".join(param_strs)
        if return_sig:
            return f"func {name}({params_str}) {return_sig}"
        else:
            return f"func {name}({params_str})"

    def format_struct(self, name: str, fields: dict[str, str]) -> str:
        """Format a Go struct definition.

        Args:
            name: Struct name
            fields: Dictionary of field_name → type_hint

        Returns:
            Formatted Go struct

        Example:
            >>> resolver = GoTypeResolver()
            >>> print(resolver.format_struct(
            ...     "User",
            ...     {"Name": "str", "Age": "int", "Email": "str"}
            ... ))
            type User struct {
              Name string
              Age int
              Email string
            }
        """
        lines = [f"type {name} struct {{"]
        for field_name, type_hint in fields.items():
            go_type = self.resolve(type_hint).annotation
            lines.append(f"  {field_name} {go_type}")
        lines.append("}")
        return "\n".join(lines)

    def format_interface(self, name: str, methods: dict[str, str]) -> str:
        """Format a Go interface definition.

        Args:
            name: Interface name
            methods: Dictionary of method_name → signature

        Returns:
            Formatted Go interface

        Example:
            >>> resolver = GoTypeResolver()
            >>> print(resolver.format_interface(
            ...     "Reader",
            ...     {"Read": "(p []byte) (n int, err error)"}
            ... ))
            type Reader interface {
              Read(p []byte) (n int, err error)
            }
        """
        lines = [f"type {name} interface {{"]
        for method_name, signature in methods.items():
            lines.append(f"  {method_name}{signature}")
        lines.append("}")
        return "\n".join(lines)
