"""Java type resolution and mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class JavaType:
    """Represents a Java type annotation.

    Attributes:
        annotation: Java type string (e.g., "String", "int", "List<Integer>")
        is_generic: Whether this is a generic type
        is_primitive: Whether this is a primitive type (int, boolean, etc.)
        needs_import: Whether this type needs an import statement
        import_source: Source package for import (if needed)
        is_array: Whether this is an array type
    """

    annotation: str
    is_generic: bool = False
    is_primitive: bool = False
    needs_import: bool = False
    import_source: str | None = None
    is_array: bool = False


class JavaTypeResolver:
    """Resolves IR types to Java type annotations.

    Handles mapping from Python/IR type hints to Java types, including:
    - Basic types (str → String, int → int)
    - Collections (list → List, dict → Map)
    - Generics (list[T] → List<T>)
    - Primitives vs boxed types (int vs Integer)
    - Arrays (list[int] → int[] or List<Integer>)
    """

    # Basic type mappings (primitives)
    PRIMITIVE_TYPE_MAP = {
        "int": "int",
        "float": "double",
        "bool": "boolean",
        "byte": "byte",
        "short": "short",
        "long": "long",
        "char": "char",
    }

    # Boxed type mappings
    BOXED_TYPE_MAP = {
        "int": "Integer",
        "float": "Double",
        "bool": "Boolean",
        "byte": "Byte",
        "short": "Short",
        "long": "Long",
        "char": "Character",
    }

    # Reference type mappings
    REFERENCE_TYPE_MAP = {
        "str": "String",
        "string": "String",
        "None": "void",
        "null": "void",
        "Any": "Object",
        "object": "Object",
        "bytes": "byte[]",
        "bytearray": "byte[]",
    }

    # Collection type mappings
    COLLECTION_TYPE_MAP = {
        "list": "List",
        "dict": "Map",
        "set": "Set",
        "tuple": "List",  # Java doesn't have tuples, use List
    }

    # Common imports for collection types
    COLLECTION_IMPORTS = {
        "List": "java.util.List",
        "Map": "java.util.Map",
        "Set": "java.util.Set",
        "ArrayList": "java.util.ArrayList",
        "HashMap": "java.util.HashMap",
        "HashSet": "java.util.HashSet",
    }

    def __init__(self, prefer_primitives: bool = True):
        """Initialize Java type resolver.

        Args:
            prefer_primitives: Whether to prefer primitive types (int) over boxed (Integer)
                              when possible. Default True for better performance.
        """
        self.prefer_primitives = prefer_primitives
        self.custom_types: dict[str, str] = {}  # Custom type mappings

    def resolve(self, type_hint: str, allow_primitive: bool = True) -> JavaType:
        """Resolve IR type hint to Java type.

        Args:
            type_hint: Type hint string from IR (e.g., "str", "list[int]", "dict[str, Any]")
            allow_primitive: Whether to allow primitive types (set False for generics)

        Returns:
            JavaType with appropriate Java annotation

        Examples:
            >>> resolver = JavaTypeResolver()
            >>> resolver.resolve("str").annotation
            'String'
            >>> resolver.resolve("int").annotation
            'int'
            >>> resolver.resolve("list[int]").annotation
            'List<Integer>'
            >>> resolver.resolve("dict[str, int]").annotation
            'Map<String, Integer>'
        """
        # Trim whitespace
        type_hint = type_hint.strip() if type_hint else ""

        # Handle empty types
        if not type_hint:
            return JavaType("Object", needs_import=False)

        # Handle TypedHole (placeholder)
        if "TypedHole" in type_hint or type_hint == "...":
            return JavaType("Object /* TODO: infer type */", needs_import=False)

        # Handle array notation (str[] in Java)
        if type_hint.endswith("[]"):
            base_type = type_hint[:-2].strip()
            resolved_base = self.resolve(base_type, allow_primitive=True)
            return JavaType(
                f"{resolved_base.annotation}[]",
                is_array=True,
                needs_import=resolved_base.needs_import,
                import_source=resolved_base.import_source,
            )

        # Handle generic types (list[T], dict[K, V])
        if "[" in type_hint:
            if "]" not in type_hint:
                return JavaType("Object", needs_import=False)
            return self._resolve_generic_type(type_hint)

        # Handle primitive types
        if type_hint in self.PRIMITIVE_TYPE_MAP and allow_primitive and self.prefer_primitives:
            return JavaType(
                self.PRIMITIVE_TYPE_MAP[type_hint],
                is_primitive=True,
                needs_import=False,
            )

        # Handle boxed types (for generics or when primitives not allowed)
        if type_hint in self.BOXED_TYPE_MAP:
            return JavaType(
                self.BOXED_TYPE_MAP[type_hint],
                is_primitive=False,
                needs_import=False,
            )

        # Handle reference types
        if type_hint in self.REFERENCE_TYPE_MAP:
            return JavaType(
                self.REFERENCE_TYPE_MAP[type_hint],
                needs_import=False,
            )

        # Handle custom types (User, MyClass)
        return self._resolve_custom_type(type_hint)

    def _resolve_generic_type(self, type_hint: str) -> JavaType:
        """Resolve generic type (e.g., 'list[int]' → 'List<Integer>').

        Args:
            type_hint: Generic type string

        Returns:
            JavaType with generic annotation
        """
        # Extract base type and type parameters
        match = re.match(r"(\w+)\[(.+)\]", type_hint)
        if not match:
            return JavaType("Object", needs_import=False)

        base_type = match.group(1)
        type_params = match.group(2)

        # Handle list types
        if base_type == "list":
            # list[int] → List<Integer>
            # Note: primitives become boxed types in generics
            inner_type = self.resolve(type_params, allow_primitive=False).annotation
            return JavaType(
                f"List<{inner_type}>",
                is_generic=True,
                needs_import=True,
                import_source="java.util.List",
            )

        # Handle dict types
        elif base_type == "dict":
            # dict[str, int] → Map<String, Integer>
            key_type, value_type = self._split_type_parameters(type_params)
            key_java = self.resolve(key_type, allow_primitive=False).annotation
            value_java = self.resolve(value_type, allow_primitive=False).annotation
            return JavaType(
                f"Map<{key_java}, {value_java}>",
                is_generic=True,
                needs_import=True,
                import_source="java.util.Map",
            )

        # Handle set types
        elif base_type == "set":
            # set[int] → Set<Integer>
            inner_type = self.resolve(type_params, allow_primitive=False).annotation
            return JavaType(
                f"Set<{inner_type}>",
                is_generic=True,
                needs_import=True,
                import_source="java.util.Set",
            )

        # Handle tuple (treat as List in Java)
        elif base_type == "tuple":
            # tuple[int, str] → List<Object> (Java doesn't have heterogeneous tuples)
            return JavaType(
                "List<Object>",
                is_generic=True,
                needs_import=True,
                import_source="java.util.List",
            )

        # Custom generic type (e.g., Optional<T>)
        else:
            inner_type = self.resolve(type_params, allow_primitive=False).annotation
            return JavaType(
                f"{base_type}<{inner_type}>",
                is_generic=True,
                needs_import=False,  # Assume custom type is available
            )

    def _resolve_custom_type(self, type_hint: str) -> JavaType:
        """Resolve custom/user-defined type.

        Args:
            type_hint: Custom type name

        Returns:
            JavaType for custom type
        """
        # Check if there's a custom mapping
        if type_hint in self.custom_types:
            return JavaType(self.custom_types[type_hint], needs_import=True)

        # Capitalize first letter (Java naming convention for classes)
        java_name = type_hint[0].upper() + type_hint[1:] if type_hint else "Object"

        return JavaType(
            java_name,
            needs_import=False,  # Assume same package or already imported
        )

    def _split_type_parameters(self, params: str) -> tuple[str, str]:
        """Split type parameters handling nested generics.

        Args:
            params: Type parameters string (e.g., "String, Integer")

        Returns:
            Tuple of (first_param, second_param)
        """
        # Simple case: no nested generics
        if "<" not in params:
            parts = [p.strip() for p in params.split(",", 1)]
            if len(parts) == 2:
                return parts[0], parts[1]
            return params, "Object"

        # Complex case: handle nested generics like "Map<String, Integer>, List<String>"
        depth = 0
        split_pos = -1
        for i, char in enumerate(params):
            if char == "<":
                depth += 1
            elif char == ">":
                depth -= 1
            elif char == "," and depth == 0:
                split_pos = i
                break

        if split_pos == -1:
            return params, "Object"

        return params[:split_pos].strip(), params[split_pos + 1 :].strip()

    def format_function_signature(
        self,
        name: str,
        parameters: list[tuple[str, str]],
        return_type: str,
        access_modifier: str = "public",
        is_static: bool = False,
    ) -> str:
        """Format a Java method signature.

        Args:
            name: Method name
            parameters: List of (param_name, param_type) tuples
            return_type: Return type hint
            access_modifier: Access modifier (public, private, protected)
            is_static: Whether method is static

        Returns:
            Formatted Java method signature

        Example:
            >>> resolver = JavaTypeResolver()
            >>> resolver.format_function_signature(
            ...     "addNumbers",
            ...     [("a", "int"), ("b", "int")],
            ...     "int"
            ... )
            'public int addNumbers(int a, int b)'
        """
        # Resolve return type
        java_return = self.resolve(return_type, allow_primitive=True).annotation

        # Resolve parameter types
        java_params = []
        for param_name, param_type in parameters:
            java_type = self.resolve(param_type, allow_primitive=True).annotation
            java_params.append(f"{java_type} {param_name}")

        # Build signature
        parts = [access_modifier]
        if is_static:
            parts.append("static")
        parts.append(java_return)
        parts.append(name)

        params_str = ", ".join(java_params)
        signature = " ".join(parts) + f"({params_str})"

        return signature

    def get_default_value(self, type_hint: str) -> str:
        """Get default value for a Java type.

        Args:
            type_hint: Type hint string

        Returns:
            Default value (e.g., "0" for int, "null" for objects)
        """
        java_type = self.resolve(type_hint, allow_primitive=True)

        # Primitive defaults
        if java_type.is_primitive:
            if java_type.annotation == "boolean":
                return "false"
            elif java_type.annotation in ["int", "byte", "short", "long"]:
                return "0"
            elif java_type.annotation in ["float", "double"]:
                return "0.0"
            elif java_type.annotation == "char":
                return "'\\0'"

        # Reference type default
        return "null"
