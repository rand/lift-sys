"""Unit tests for docstring generator."""

from lift_sys.codegen.docstring_generator import DefaultDocstringGenerator
from lift_sys.ir.models import IntentClause, Parameter, SigClause


class TestDefaultDocstringGenerator:
    """Tests for DefaultDocstringGenerator."""

    def test_generate_simple_docstring(self):
        """Test generating simple docstring with only summary."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Add two numbers")
        signature = SigClause(
            name="add",
            parameters=[
                Parameter("a", "int"),
                Parameter("b", "int"),
            ],
            returns="int",
        )

        result = generator.generate(intent, signature)

        assert '"""Add two numbers.' in result.content
        assert "Args:" in result.content
        assert "a: Parameter value" in result.content
        assert "b: Parameter value" in result.content
        assert "Returns:" in result.content
        assert "int" in result.content
        assert result.style == "google"

    def test_generate_with_rationale(self):
        """Test generating docstring with rationale."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(
            summary="Calculate factorial",
            rationale="Uses recursive algorithm for simplicity.",
        )
        signature = SigClause(
            name="factorial",
            parameters=[Parameter("n", "int")],
            returns="int",
        )

        result = generator.generate(intent, signature)

        assert "Calculate factorial." in result.content
        assert "Uses recursive algorithm for simplicity." in result.content

    def test_generate_with_parameter_descriptions(self):
        """Test generating docstring with parameter descriptions."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Divide two numbers")
        signature = SigClause(
            name="divide",
            parameters=[
                Parameter("numerator", "float", description="The dividend"),
                Parameter("denominator", "float", description="The divisor (cannot be zero)"),
            ],
            returns="float",
        )

        result = generator.generate(intent, signature)

        assert "numerator: The dividend" in result.content
        assert "denominator: The divisor (cannot be zero)" in result.content

    def test_generate_no_parameters(self):
        """Test generating docstring for function with no parameters."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Get current timestamp")
        signature = SigClause(name="now", parameters=[], returns="float")

        result = generator.generate(intent, signature)

        assert "Get current timestamp." in result.content
        assert "Args:" not in result.content
        assert "Returns:" in result.content

    def test_generate_no_return_type(self):
        """Test generating docstring for function with no return type."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Print greeting")
        signature = SigClause(
            name="greet",
            parameters=[Parameter("name", "str")],
            returns=None,
        )

        result = generator.generate(intent, signature)

        assert "Print greeting." in result.content
        assert "Args:" in result.content
        assert "Returns:" not in result.content

    def test_generate_return_type_none(self):
        """Test that None return type doesn't create Returns section."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Log message")
        signature = SigClause(
            name="log",
            parameters=[Parameter("msg", "str")],
            returns="none",  # lowercase none
        )

        result = generator.generate(intent, signature)

        assert "Log message." in result.content
        # "none" is lowercase, so Returns section should not appear
        assert "Returns:" not in result.content

    def test_summary_with_period(self):
        """Test that summary with period is not duplicated."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Calculate square root.")
        signature = SigClause(
            name="sqrt",
            parameters=[Parameter("x", "float")],
            returns="float",
        )

        result = generator.generate(intent, signature)

        # Should not have double period
        assert "Calculate square root.." not in result.content
        assert "Calculate square root." in result.content

    def test_docstring_format(self):
        """Test that docstring uses triple quotes correctly."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Test function")
        signature = SigClause(name="test", parameters=[], returns=None)

        result = generator.generate(intent, signature)

        assert result.content.startswith('"""')
        assert result.content.endswith('"""')

    def test_multiple_parameters_formatting(self):
        """Test that multiple parameters are formatted correctly."""
        generator = DefaultDocstringGenerator()

        intent = IntentClause(summary="Process data")
        signature = SigClause(
            name="process",
            parameters=[
                Parameter("input_data", "list[str]", "Raw input data"),
                Parameter("config", "dict", "Configuration options"),
                Parameter("validate", "bool", "Whether to validate input"),
            ],
            returns="list[str]",
        )

        result = generator.generate(intent, signature)

        assert "input_data: Raw input data" in result.content
        assert "config: Configuration options" in result.content
        assert "validate: Whether to validate input" in result.content
        assert "Returns:" in result.content
        assert "list[str]" in result.content
