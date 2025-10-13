"""Unit tests for type resolver."""

import pytest

from lift_sys.codegen.type_resolver import DefaultTypeResolver, TypeResolutionError
from lift_sys.ir.models import Parameter


class TestDefaultTypeResolver:
    """Tests for DefaultTypeResolver."""

    def test_resolve_simple_builtin_types(self):
        """Test resolving simple built-in types."""
        resolver = DefaultTypeResolver()

        # Already Python types - pass through
        assert resolver.resolve("str").annotation == "str"
        assert resolver.resolve("int").annotation == "int"
        assert resolver.resolve("float").annotation == "float"
        assert resolver.resolve("bool").annotation == "bool"
        assert resolver.resolve("None").annotation == "None"

    def test_resolve_ir_type_names(self):
        """Test mapping IR type names to Python types."""
        resolver = DefaultTypeResolver()

        # IR type names should be mapped
        assert resolver.resolve("string").annotation == "str"
        assert resolver.resolve("integer").annotation == "int"
        assert resolver.resolve("boolean").annotation == "bool"
        assert resolver.resolve("array").annotation == "list"
        assert resolver.resolve("dictionary").annotation == "dict"
        assert resolver.resolve("none").annotation == "None"
        assert resolver.resolve("null").annotation == "None"

    def test_resolve_union_types(self):
        """Test resolving union types."""
        resolver = DefaultTypeResolver()

        # Union with None (optional type)
        result = resolver.resolve("str | None")
        assert result.annotation == "str | None"

        # Union of multiple types
        result = resolver.resolve("int | float")
        assert result.annotation == "int | float"

        # Union with IR type names
        result = resolver.resolve("string | None")
        assert result.annotation == "str | None"

    def test_resolve_generic_types(self):
        """Test resolving generic types."""
        resolver = DefaultTypeResolver()

        # Simple generics
        result = resolver.resolve("list[int]")
        assert result.annotation == "list[int]"
        assert result.is_generic is True
        assert result.origin_type == "list"

        result = resolver.resolve("dict[str, int]")
        assert result.annotation == "dict[str, int]"
        assert result.is_generic is True
        assert result.origin_type == "dict"

        # IR type names in generics
        result = resolver.resolve("array[integer]")
        assert result.annotation == "list[int]"
        assert result.is_generic is True

        result = resolver.resolve("dictionary[string, integer]")
        assert result.annotation == "dict[str, int]"

    def test_resolve_nested_generics(self):
        """Test resolving nested generic types."""
        resolver = DefaultTypeResolver()

        result = resolver.resolve("list[list[int]]")
        assert result.annotation == "list[list[int]]"

        result = resolver.resolve("dict[str, list[int]]")
        assert result.annotation == "dict[str, list[int]]"

    def test_resolve_custom_types(self):
        """Test that custom types pass through unchanged."""
        resolver = DefaultTypeResolver()

        # Custom class names should pass through
        result = resolver.resolve("UserModel")
        assert result.annotation == "UserModel"

        result = resolver.resolve("MyCustomType")
        assert result.annotation == "MyCustomType"

    def test_resolve_parameter_type(self):
        """Test resolving parameter types."""
        resolver = DefaultTypeResolver()

        param = Parameter(name="x", type_hint="integer")
        result = resolver.resolve_parameter_type(param)
        assert result.annotation == "int"

    def test_resolve_return_type_with_none(self):
        """Test resolving return type when None."""
        resolver = DefaultTypeResolver()

        result = resolver.resolve_return_type(None)
        assert result.annotation == "None"

        result = resolver.resolve_return_type("")
        assert result.annotation == "None"

    def test_resolve_return_type_with_value(self):
        """Test resolving return type with actual value."""
        resolver = DefaultTypeResolver()

        result = resolver.resolve_return_type("string")
        assert result.annotation == "str"

        result = resolver.resolve_return_type("list[int]")
        assert result.annotation == "list[int]"

    def test_resolve_empty_type_hint_raises_error(self):
        """Test that empty type hint raises error."""
        resolver = DefaultTypeResolver()

        with pytest.raises(TypeResolutionError) as exc_info:
            resolver.resolve("")

        assert "Empty type hint" in str(exc_info.value)

    def test_resolve_with_whitespace(self):
        """Test that whitespace is handled correctly."""
        resolver = DefaultTypeResolver()

        result = resolver.resolve("  str  ")
        assert result.annotation == "str"

        result = resolver.resolve(" list[int] ")
        assert result.annotation == "list[int]"

    def test_resolve_complex_union_with_generics(self):
        """Test resolving complex union types with generics."""
        resolver = DefaultTypeResolver()

        result = resolver.resolve("list[int] | None")
        assert result.annotation == "list[int] | None"

        result = resolver.resolve("dict[str, int] | list[str] | None")
        assert result.annotation == "dict[str, int] | list[str] | None"
