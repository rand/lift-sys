"""Tests for TypeScript type resolution."""

from __future__ import annotations

from lift_sys.codegen.languages.typescript_types import (
    TypeScriptTypeResolver,
)


class TestBasicTypes:
    """Tests for basic type mappings."""

    def test_string_type(self):
        """Test str → string mapping."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("str")

        assert result.annotation == "string"
        assert not result.is_generic
        assert not result.is_union
        assert not result.needs_import

    def test_number_types(self):
        """Test int and float → number mapping."""
        resolver = TypeScriptTypeResolver()

        int_result = resolver.resolve("int")
        assert int_result.annotation == "number"

        float_result = resolver.resolve("float")
        assert float_result.annotation == "number"

    def test_boolean_type(self):
        """Test bool → boolean mapping."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("bool")

        assert result.annotation == "boolean"

    def test_null_type(self):
        """Test None → null mapping."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("None")

        assert result.annotation == "null"

    def test_any_type(self):
        """Test Any → any mapping."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("Any")

        assert result.annotation == "any"


class TestCollectionTypes:
    """Tests for collection type mappings."""

    def test_simple_list(self):
        """Test list[int] → Array<number>."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[int]")

        assert result.annotation == "Array<number>"
        assert result.is_generic
        assert not result.is_union

    def test_nested_list(self):
        """Test list[list[str]] → Array<Array<string>>."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[list[str]]")

        assert result.annotation == "Array<Array<string>>"
        assert result.is_generic

    def test_simple_dict(self):
        """Test dict[str, int] → Record<string, number>."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("dict[str, int]")

        assert result.annotation == "Record<string, number>"
        assert result.is_generic

    def test_dict_with_generic_value(self):
        """Test dict[str, list[int]] → Record<string, Array<number>>."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("dict[str, list[int]]")

        assert result.annotation == "Record<string, Array<number>>"
        assert result.is_generic

    def test_set_type(self):
        """Test set[int] → Set<number>."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("set[int]")

        assert result.annotation == "Set<number>"
        assert result.is_generic

    def test_tuple_type(self):
        """Test tuple[int, str] → readonly [number, string]."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("tuple[int, str]")

        assert result.annotation == "readonly [number, string]"
        assert result.is_generic


class TestUnionTypes:
    """Tests for union type mappings."""

    def test_simple_union(self):
        """Test str | int → string | number."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("str | int")

        assert result.annotation == "string | number"
        assert result.is_union
        assert not result.is_generic

    def test_union_with_null(self):
        """Test str | None → string | null."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("str | None")

        assert result.annotation == "string | null"
        assert result.is_union

    def test_multi_union(self):
        """Test str | int | bool → string | number | boolean."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("str | int | bool")

        assert result.annotation == "string | number | boolean"
        assert result.is_union

    def test_union_with_generic(self):
        """Test list[str] | None → Array<string> | null."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[str] | None")

        assert result.annotation == "Array<string> | null"
        assert result.is_union


class TestCustomTypes:
    """Tests for custom type handling."""

    def test_custom_type(self):
        """Test User → User (interface)."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("User")

        assert result.annotation == "User"
        assert result.is_interface
        assert not result.needs_import  # Assume same file

    def test_registered_custom_type(self):
        """Test registered custom type mapping."""
        resolver = TypeScriptTypeResolver()
        resolver.register_custom_type("UserId", "string")

        result = resolver.resolve("UserId")
        assert result.annotation == "string"
        assert result.needs_import


class TestPlaceholderTypes:
    """Tests for placeholder/unknown types."""

    def test_empty_type(self):
        """Test empty string → any."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("")

        assert result.annotation == "any"

    def test_typed_hole(self):
        """Test TypedHole → any with TODO."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("TypedHole")

        assert "any" in result.annotation
        assert "TODO" in result.annotation

    def test_ellipsis_placeholder(self):
        """Test ... → any with TODO."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("...")

        assert "any" in result.annotation
        assert "TODO" in result.annotation


class TestFunctionSignatures:
    """Tests for function signature formatting."""

    def test_simple_function_signature(self):
        """Test basic function signature."""
        resolver = TypeScriptTypeResolver()
        sig = resolver.format_function_signature(
            "greet",
            [("name", "str")],
            "str",
        )

        assert sig == "function greet(name: string): string"

    def test_multiple_parameters(self):
        """Test function with multiple parameters."""
        resolver = TypeScriptTypeResolver()
        sig = resolver.format_function_signature(
            "add",
            [("a", "int"), ("b", "int")],
            "int",
        )

        assert sig == "function add(a: number, b: number): number"

    def test_async_function_signature(self):
        """Test async function signature."""
        resolver = TypeScriptTypeResolver()
        sig = resolver.format_function_signature(
            "fetchUser",
            [("id", "str")],
            "User",
            is_async=True,
        )

        assert sig == "async function fetchUser(id: string): Promise<User>"

    def test_async_with_promise_return(self):
        """Test async function already returning Promise."""
        resolver = TypeScriptTypeResolver()
        sig = resolver.format_function_signature(
            "fetchData",
            [],
            "Promise[str]",
            is_async=True,
        )

        # Should not double-wrap Promise
        assert "Promise<Promise<" not in sig
        assert "Promise<string>" in sig


class TestInterfaceFormatting:
    """Tests for interface definition formatting."""

    def test_simple_interface(self):
        """Test basic interface formatting."""
        resolver = TypeScriptTypeResolver()
        interface = resolver.format_interface(
            "User",
            {"name": "str", "age": "int"},
        )

        assert "interface User {" in interface
        assert "name: string;" in interface
        assert "age: number;" in interface
        assert "}" in interface

    def test_interface_with_optional_field(self):
        """Test interface with optional field (union with null)."""
        resolver = TypeScriptTypeResolver()
        interface = resolver.format_interface(
            "User",
            {"name": "str", "email": "str | None"},
        )

        assert "name: string;" in interface
        assert "email: string | null;" in interface

    def test_interface_with_generic_field(self):
        """Test interface with generic field."""
        resolver = TypeScriptTypeResolver()
        interface = resolver.format_interface(
            "Response",
            {"data": "list[str]", "count": "int"},
        )

        assert "data: Array<string>;" in interface
        assert "count: number;" in interface


class TestTypeAliases:
    """Tests for type alias formatting."""

    def test_simple_type_alias(self):
        """Test basic type alias."""
        resolver = TypeScriptTypeResolver()
        alias = resolver.format_type_alias("UserId", "str")

        assert alias == "type UserId = string;"

    def test_union_type_alias(self):
        """Test type alias with union."""
        resolver = TypeScriptTypeResolver()
        alias = resolver.format_type_alias("Status", "str | int")

        assert alias == "type Status = string | number;"

    def test_generic_type_alias(self):
        """Test type alias with generic."""
        resolver = TypeScriptTypeResolver()
        alias = resolver.format_type_alias("UserList", "list[User]")

        assert alias == "type UserList = Array<User>;"


class TestComplexTypes:
    """Tests for complex type scenarios."""

    def test_nested_generics(self):
        """Test deeply nested generic types."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[dict[str, list[int]]]")

        assert result.annotation == "Array<Record<string, Array<number>>>"

    def test_union_of_generics(self):
        """Test union of generic types."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[str] | dict[str, int]")

        assert "Array<string>" in result.annotation
        assert "Record<string, number>" in result.annotation
        assert " | " in result.annotation

    def test_custom_generic(self):
        """Test custom generic type (e.g., Promise)."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("Promise[User]")

        assert result.annotation == "Promise<User>"
        assert result.is_generic


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_whitespace_in_type(self):
        """Test type with extra whitespace."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("  str  ")

        # Should handle gracefully (might need trimming in implementation)
        assert "string" in result.annotation or result.annotation == "any"

    def test_malformed_generic(self):
        """Test malformed generic syntax."""
        resolver = TypeScriptTypeResolver()
        result = resolver.resolve("list[")

        # Should fallback to 'any'
        assert result.annotation == "any"

    def test_type_parameter_splitting(self):
        """Test _split_type_parameters helper."""
        resolver = TypeScriptTypeResolver()

        # Simple case
        key, value = resolver._split_type_parameters("str, int")
        assert key == "str"
        assert value == "int"

        # Nested generic case
        key, value = resolver._split_type_parameters("str, list[int]")
        assert key == "str"
        assert value == "list[int]"

        # Deeply nested case
        key, value = resolver._split_type_parameters("str, dict[str, list[int]]")
        assert key == "str"
        assert value == "dict[str, list[int]]"
