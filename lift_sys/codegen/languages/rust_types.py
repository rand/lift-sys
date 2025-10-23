"""Rust type resolution and mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class RustType:
    """Represents a Rust type annotation.

    Attributes:
        annotation: Rust type string (e.g., "String", "Vec<i32>", "Result<User, Error>")
        is_generic: Whether this is a generic type
        is_reference: Whether this is a reference type (&T)
        is_mutable: Whether this is a mutable reference (&mut T)
        needs_import: Whether this type needs a use statement
        import_source: Source module for import (if needed)
    """

    annotation: str
    is_generic: bool = False
    is_reference: bool = False
    is_mutable: bool = False
    needs_import: bool = False
    import_source: str | None = None


class RustTypeResolver:
    """Resolves IR types to Rust type annotations.

    Handles mapping from Python/IR type hints to Rust types, including:
    - Basic types (str → String, int → i32)
    - Collections (list → Vec, dict → HashMap)
    - Generics (list[T] → Vec<T>)
    - Option types (str | None → Option<String>)
    - Result types for error handling
    - Custom types (User → User struct)
    """

    # Basic type mappings
    BASIC_TYPE_MAP = {
        "str": "String",
        "int": "i32",
        "float": "f64",
        "bool": "bool",
        "None": "()",
        "Any": "Box<dyn std::any::Any>",
        "object": "Box<dyn std::any::Any>",
        # Python collections
        "list": "Vec<T>",
        "dict": "std::collections::HashMap<K, V>",
        "set": "std::collections::HashSet<T>",
        "tuple": "(T,)",
        # Rust-specific
        "bytes": "Vec<u8>",
        "bytearray": "Vec<u8>",
    }

    def __init__(self):
        """Initialize Rust type resolver."""
        self.custom_types: dict[str, str] = {}  # Custom type mappings

    def resolve(self, type_hint: str) -> RustType:
        """Resolve IR type hint to Rust type.

        Args:
            type_hint: Type hint string from IR (e.g., "str", "list[int]", "str | None")

        Returns:
            RustType with appropriate Rust annotation

        Examples:
            >>> resolver = RustTypeResolver()
            >>> resolver.resolve("str").annotation
            'String'
            >>> resolver.resolve("list[int]").annotation
            'Vec<i32>'
            >>> resolver.resolve("dict[str, int]").annotation
            'HashMap<String, i32>'
            >>> resolver.resolve("str | None").annotation
            'Option<String>'
        """
        # Trim whitespace
        type_hint = type_hint.strip() if type_hint else ""

        # Handle empty or placeholder types
        if not type_hint:
            return RustType("()", needs_import=False)

        # Handle TypedHole (placeholder for unknown types)
        if "TypedHole" in type_hint or type_hint == "...":
            return RustType("() /* TODO: infer type */", needs_import=False)

        # Handle Option types (str | None)
        if "|" in type_hint and "None" in type_hint:
            return self._resolve_option_type(type_hint)

        # Handle generic types (list[T], dict[K, V])
        if "[" in type_hint:
            # Check for malformed generic (missing closing bracket)
            if "]" not in type_hint:
                return RustType("()", needs_import=False)
            return self._resolve_generic_type(type_hint)

        # Handle basic types
        if type_hint in self.BASIC_TYPE_MAP:
            rust_type = self.BASIC_TYPE_MAP[type_hint]
            needs_import = "HashMap" in rust_type or "HashSet" in rust_type
            return RustType(
                rust_type,
                needs_import=needs_import,
                import_source="std::collections" if needs_import else None,
            )

        # Handle custom types (User, MyStruct)
        return self._resolve_custom_type(type_hint)

    def _resolve_option_type(self, type_hint: str) -> RustType:
        """Resolve optional type (e.g., 'str | None' → 'Option<String>').

        Args:
            type_hint: Union type string with None

        Returns:
            RustType with Option annotation
        """
        parts = [part.strip() for part in type_hint.split("|")]
        # Remove None from parts
        non_none_parts = [p for p in parts if p != "None"]
        if len(non_none_parts) == 1:
            inner_type = self.resolve(non_none_parts[0]).annotation
            return RustType(
                f"Option<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )
        # Multiple non-None types not supported well in Rust
        # Fall back to Option<Box<dyn Any>>
        return RustType(
            "Option<Box<dyn std::any::Any>>",
            is_generic=True,
            needs_import=False,
        )

    def _resolve_generic_type(self, type_hint: str) -> RustType:
        """Resolve generic type (e.g., 'list[int]' → 'Vec<i32>').

        Args:
            type_hint: Generic type string

        Returns:
            RustType with generic annotation
        """
        # Extract base type and type parameters
        match = re.match(r"(\w+)\[(.+)\]", type_hint)
        if not match:
            # Fallback if parsing fails
            return RustType("()", needs_import=False)

        base_type = match.group(1)
        type_params = match.group(2)

        # Handle specific generic types
        if base_type == "list":
            # list[int] → Vec<i32>
            inner_type = self.resolve(type_params).annotation
            return RustType(
                f"Vec<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "dict":
            # dict[str, int] → HashMap<String, i32>
            key_type, value_type = self._split_type_parameters(type_params)
            key_rust = self.resolve(key_type).annotation
            value_rust = self.resolve(value_type).annotation
            return RustType(
                f"HashMap<{key_rust}, {value_rust}>",
                is_generic=True,
                needs_import=True,
                import_source="std::collections::HashMap",
            )

        elif base_type == "tuple":
            # tuple[int, str] → (i32, String)
            types = [t.strip() for t in type_params.split(",")]
            rust_types = [self.resolve(t).annotation for t in types]
            return RustType(
                f"({', '.join(rust_types)})",
                is_generic=True,
                needs_import=False,
            )

        elif base_type == "set":
            # set[int] → HashSet<i32>
            inner_type = self.resolve(type_params).annotation
            return RustType(
                f"HashSet<{inner_type}>",
                is_generic=True,
                needs_import=True,
                import_source="std::collections::HashSet",
            )

        else:
            # Custom generic (e.g., Result[T, E], Option[T])
            inner_type = self.resolve(type_params).annotation
            rust_base = self.BASIC_TYPE_MAP.get(base_type, base_type)
            return RustType(
                f"{rust_base}<{inner_type}>",
                is_generic=True,
                needs_import=False,
            )

    def _resolve_custom_type(self, type_hint: str) -> RustType:
        """Resolve custom type (e.g., 'User' → 'User' struct).

        Args:
            type_hint: Custom type name

        Returns:
            RustType with custom type annotation
        """
        # Check if it's a known custom type
        if type_hint in self.custom_types:
            return RustType(
                self.custom_types[type_hint],
                needs_import=True,
            )

        # Default: treat as struct with same name
        return RustType(
            type_hint,
            needs_import=False,  # Assume defined in same file
        )

    def _split_type_parameters(self, type_params: str) -> tuple[str, str]:
        """Split type parameters handling nested generics.

        Args:
            type_params: Type parameters string (e.g., "str, int" or "str, Vec<int>")

        Returns:
            Tuple of (key_type, value_type)

        Examples:
            >>> resolver = RustTypeResolver()
            >>> resolver._split_type_parameters("str, int")
            ('str', 'int')
            >>> resolver._split_type_parameters("str, Vec<int>")
            ('str', 'Vec<int>')
        """
        # Simple case: no nested generics
        if "[" not in type_params and "<" not in type_params:
            parts = [p.strip() for p in type_params.split(",", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
            return type_params, "()"

        # Complex case: handle nested generics
        depth = 0
        split_pos = -1
        for i, char in enumerate(type_params):
            if char in "[<":
                depth += 1
            elif char in "]>":
                depth -= 1
            elif char == "," and depth == 0:
                split_pos = i
                break

        if split_pos == -1:
            return type_params, "()"

        return type_params[:split_pos].strip(), type_params[split_pos + 1 :].strip()

    def register_custom_type(self, name: str, rust_type: str):
        """Register a custom type mapping.

        Args:
            name: Type name in IR
            rust_type: Corresponding Rust type
        """
        self.custom_types[name] = rust_type

    def format_function_signature(
        self,
        name: str,
        parameters: list[tuple[str, str]],
        return_type: str,
        is_pub: bool = True,
    ) -> str:
        """Format a Rust function signature.

        Args:
            name: Function name
            parameters: List of (param_name, type_hint) tuples
            return_type: Return type hint
            is_pub: Whether function is public

        Returns:
            Formatted Rust function signature

        Example:
            >>> resolver = RustTypeResolver()
            >>> resolver.format_function_signature(
            ...     "greet",
            ...     [("name", "str"), ("age", "int")],
            ...     "str",
            ... )
            'pub fn greet(name: String, age: i32) -> String'
        """
        # Resolve parameter types
        param_strs = []
        for param_name, type_hint in parameters:
            rust_type = self.resolve(type_hint).annotation
            param_strs.append(f"{param_name}: {rust_type}")

        # Resolve return type
        rust_return = self.resolve(return_type).annotation

        params_str = ", ".join(param_strs)
        pub_prefix = "pub " if is_pub else ""

        # Handle unit return type
        if rust_return == "()":
            return f"{pub_prefix}fn {name}({params_str})"
        else:
            return f"{pub_prefix}fn {name}({params_str}) -> {rust_return}"

    def format_struct(self, name: str, fields: dict[str, str], is_pub: bool = True) -> str:
        """Format a Rust struct definition.

        Args:
            name: Struct name
            fields: Dictionary of field_name → type_hint
            is_pub: Whether struct is public

        Returns:
            Formatted Rust struct

        Example:
            >>> resolver = RustTypeResolver()
            >>> print(resolver.format_struct(
            ...     "User",
            ...     {"name": "str", "age": "int", "email": "str | None"}
            ... ))
            pub struct User {
                pub name: String,
                pub age: i32,
                pub email: Option<String>,
            }
        """
        pub_prefix = "pub " if is_pub else ""
        lines = [f"{pub_prefix}struct {name} {{"]
        for field_name, type_hint in fields.items():
            rust_type = self.resolve(type_hint).annotation
            lines.append(f"    pub {field_name}: {rust_type},")
        lines.append("}")
        return "\n".join(lines)

    def format_type_alias(self, name: str, type_hint: str, is_pub: bool = True) -> str:
        """Format a Rust type alias.

        Args:
            name: Type alias name
            type_hint: Type definition
            is_pub: Whether type is public

        Returns:
            Formatted Rust type alias

        Example:
            >>> resolver = RustTypeResolver()
            >>> resolver.format_type_alias("UserId", "str")
            'pub type UserId = String;'
            >>> resolver.format_type_alias("Result", "Result<User, Error>")
            'pub type Result = Result<User, Error>;'
        """
        rust_type = self.resolve(type_hint).annotation
        pub_prefix = "pub " if is_pub else ""
        return f"{pub_prefix}type {name} = {rust_type};"
