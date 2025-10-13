"""Integration tests for code generator."""

import ast

import pytest

from lift_sys.codegen import CodeGenerator, CodeGeneratorConfig
from lift_sys.codegen.generator import IncompleteIRError, InvalidIRError
from lift_sys.ir.models import (
    HoleKind,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
    TypedHole,
)


class TestCodeGenerator:
    """Tests for CodeGenerator."""

    def test_generate_simple_function(self):
        """Test generating a simple function."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers"),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter("a", "int"),
                    Parameter("b", "int"),
                ],
                returns="int",
            ),
        )

        result = generator.generate(ir)

        # Check that code was generated
        assert result.source_code
        assert result.language == "python"

        # Check that it's valid Python
        ast.parse(result.source_code)

        # Check content
        assert "def add(a: int, b: int) -> int:" in result.source_code
        assert '"""Add two numbers.' in result.source_code

    def test_generate_with_ir_type_names(self):
        """Test generating code with IR type names that need mapping."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process array of strings"),
            signature=SigClause(
                name="process",
                parameters=[Parameter("items", "array[string]")],
                returns="integer",
            ),
        )

        result = generator.generate(ir)

        # Should map array -> list, string -> str, integer -> int
        assert "def process(items: list[str]) -> int:" in result.source_code
        ast.parse(result.source_code)

    def test_generate_without_type_hints(self):
        """Test generating code without type hints."""
        config = CodeGeneratorConfig(include_type_hints=False)
        generator = CodeGenerator(config=config)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate sum"),
            signature=SigClause(
                name="sum_values",
                parameters=[Parameter("values", "list[int]")],
                returns="int",
            ),
        )

        result = generator.generate(ir)

        # Should not include type hints
        assert "def sum_values(values):" in result.source_code
        assert "list[int]" not in result.source_code
        assert " -> int:" not in result.source_code
        ast.parse(result.source_code)

    def test_generate_without_docstrings(self):
        """Test generating code without docstrings."""
        config = CodeGeneratorConfig(include_docstrings=False)
        generator = CodeGenerator(config=config)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate product"),
            signature=SigClause(
                name="multiply",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns="int",
            ),
        )

        result = generator.generate(ir)

        # Should not include docstring
        assert '"""' not in result.source_code
        ast.parse(result.source_code)

    def test_generate_with_metadata_comments(self):
        """Test generating code with metadata comments."""
        config = CodeGeneratorConfig(preserve_metadata=True)
        generator = CodeGenerator(config=config)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(name="test", parameters=[], returns=None),
            metadata=Metadata(
                origin="forward_mode",
                source_path="/path/to/source.py",
            ),
        )

        result = generator.generate(ir)

        # Should include metadata comments
        assert "# Generated from IR (origin: forward_mode)" in result.source_code
        assert "# Source: /path/to/source.py" in result.source_code
        ast.parse(result.source_code)

    def test_generate_no_parameters(self):
        """Test generating function with no parameters."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Get current time"),
            signature=SigClause(name="now", parameters=[], returns="float"),
        )

        result = generator.generate(ir)

        assert "def now() -> float:" in result.source_code
        ast.parse(result.source_code)

    def test_generate_long_parameter_list(self):
        """Test generating function with many parameters."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Complex function"),
            signature=SigClause(
                name="complex_func",
                parameters=[
                    Parameter("a", "int"),
                    Parameter("b", "str"),
                    Parameter("c", "float"),
                    Parameter("d", "bool"),
                ],
                returns="dict",
            ),
        )

        result = generator.generate(ir)

        # Long parameter list should be formatted across multiple lines
        assert "def complex_func(" in result.source_code
        ast.parse(result.source_code)

    def test_validate_ir_success(self):
        """Test IR validation succeeds for valid IR."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Valid function"),
            signature=SigClause(
                name="valid",
                parameters=[Parameter("x", "int")],
                returns="int",
            ),
        )

        result = generator.validate_ir(ir)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_ir_with_unresolved_holes(self):
        """Test IR validation fails with unresolved holes."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Incomplete function",
                holes=[TypedHole("hole_1", "str", kind=HoleKind.INTENT)],
            ),
            signature=SigClause(name="incomplete", parameters=[], returns=None),
        )

        result = generator.validate_ir(ir)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert len(result.unresolved_holes) == 1
        assert result.unresolved_holes[0].identifier == "hole_1"

    def test_validate_ir_missing_intent(self):
        """Test IR validation fails with missing intent."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary=""),  # Empty summary
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        result = generator.validate_ir(ir)

        assert result.is_valid is False
        assert any("intent" in error.lower() for error in result.errors)

    def test_validate_ir_missing_types_warning(self):
        """Test IR validation warns about missing types."""
        config = CodeGeneratorConfig(include_type_hints=True)
        generator = CodeGenerator(config=config)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(
                name="test",
                parameters=[Parameter("x", "")],  # Missing type
                returns=None,  # Missing return type
            ),
        )

        result = generator.validate_ir(ir)

        # Should still be valid (warnings, not errors)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert len(result.missing_types) > 0
        assert "x" in result.missing_types

    def test_generate_raises_incomplete_ir_error(self):
        """Test that generate raises IncompleteIRError for unresolved holes."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Incomplete",
                holes=[TypedHole("hole_1", "str")],
            ),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        with pytest.raises(IncompleteIRError) as exc_info:
            generator.generate(ir)

        assert "hole_1" in str(exc_info.value)
        assert len(exc_info.value.holes) == 1

    def test_generate_raises_invalid_ir_error(self):
        """Test that generate raises InvalidIRError for invalid IR."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary=""),  # Invalid: empty summary
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        with pytest.raises(InvalidIRError) as exc_info:
            generator.generate(ir)

        assert "intent" in str(exc_info.value).lower()

    def test_generated_code_is_syntactically_valid(self):
        """Test that all generated code is valid Python syntax."""
        generator = CodeGenerator()

        test_cases = [
            # Simple function
            IntermediateRepresentation(
                intent=IntentClause(summary="Test 1"),
                signature=SigClause(name="test1", parameters=[], returns=None),
            ),
            # With parameters
            IntermediateRepresentation(
                intent=IntentClause(summary="Test 2"),
                signature=SigClause(
                    name="test2",
                    parameters=[Parameter("x", "int")],
                    returns="str",
                ),
            ),
            # With complex types
            IntermediateRepresentation(
                intent=IntentClause(summary="Test 3"),
                signature=SigClause(
                    name="test3",
                    parameters=[
                        Parameter("data", "dict[str, list[int]]"),
                    ],
                    returns="list[str] | None",
                ),
            ),
        ]

        for ir in test_cases:
            result = generator.generate(ir)
            # This will raise SyntaxError if invalid
            ast.parse(result.source_code)

    def test_generate_with_union_types(self):
        """Test generating code with union types (optional types)."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find item"),
            signature=SigClause(
                name="find",
                parameters=[Parameter("id", "int")],
                returns="str | None",
            ),
        )

        result = generator.generate(ir)

        assert "def find(id: int) -> str | None:" in result.source_code
        ast.parse(result.source_code)

    def test_generate_with_custom_indent(self):
        """Test generating code with custom indentation."""
        config = CodeGeneratorConfig(indent="  ")  # 2 spaces
        generator = CodeGenerator(config=config)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        result = generator.generate(ir)

        # Check that 2-space indent is used
        lines = result.source_code.split("\n")
        # Find indented lines
        indented_lines = [line for line in lines if line.startswith("  ")]
        assert len(indented_lines) > 0  # Should have some indented content
        ast.parse(result.source_code)

    def test_generated_code_has_not_implemented_error(self):
        """Test that generated code raises NotImplementedError (stub)."""
        generator = CodeGenerator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Not yet implemented"),
            signature=SigClause(name="stub", parameters=[], returns=None),
        )

        result = generator.generate(ir)

        # Should contain NotImplementedError
        assert "NotImplementedError" in result.source_code
        assert "TODO: Implement stub" in result.source_code
