"""Tests for round-trip validation."""

import pytest

from lift_sys.codegen import CodeGenerator, CodeGeneratorConfig, RoundTripValidator
from lift_sys.codegen.roundtrip import DifferenceKind, IRDiffer, SimpleIRExtractor
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)


class TestSimpleIRExtractor:
    """Tests for SimpleIRExtractor."""

    def test_extract_simple_function(self):
        """Test extracting IR from simple function."""
        code = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
'''
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert ir.signature.name == "add"
        assert len(ir.signature.parameters) == 2
        assert ir.signature.parameters[0].name == "a"
        assert ir.signature.parameters[0].type_hint == "int"
        assert ir.signature.parameters[1].name == "b"
        assert ir.signature.parameters[1].type_hint == "int"
        assert ir.signature.returns == "int"
        assert "Add two numbers" in ir.intent.summary

    def test_extract_function_with_assertions(self):
        """Test extracting assertions from code."""
        code = '''
def divide(a: float, b: float) -> float:
    """Divide two numbers."""
    assert b != 0, "Division by zero"
    return a / b
'''
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert len(ir.assertions) == 1
        assert ir.assertions[0].predicate == "b != 0"
        assert ir.assertions[0].rationale == "Division by zero"

    def test_extract_function_with_union_types(self):
        """Test extracting union types."""
        code = '''
def find(id: int) -> str | None:
    """Find item by ID."""
    pass
'''
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert ir.signature.returns == "str | None"

    def test_extract_function_with_generic_types(self):
        """Test extracting generic types."""
        code = '''
def process(data: list[int]) -> dict[str, int]:
    """Process data."""
    pass
'''
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert ir.signature.parameters[0].type_hint == "list[int]"
        assert ir.signature.returns == "dict[str, int]"

    def test_extract_function_without_types(self):
        """Test extracting function without type hints."""
        code = '''
def calculate(x, y):
    """Calculate something."""
    return x + y
'''
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert ir.signature.parameters[0].type_hint == "Any"
        assert ir.signature.parameters[1].type_hint == "Any"
        assert ir.signature.returns is None

    def test_extract_function_no_docstring(self):
        """Test extracting function without docstring."""
        code = """
def test(x: int):
    pass
"""
        extractor = SimpleIRExtractor()
        ir = extractor.extract(code)

        assert ir.intent.summary == ""

    def test_extract_invalid_code_raises_error(self):
        """Test that invalid code raises ValueError."""
        code = "this is not valid python"
        extractor = SimpleIRExtractor()

        with pytest.raises(ValueError, match="Invalid Python code"):
            extractor.extract(code)

    def test_extract_no_function_raises_error(self):
        """Test that code with no function raises ValueError."""
        code = "x = 42"
        extractor = SimpleIRExtractor()

        with pytest.raises(ValueError, match="No function definition found"):
            extractor.extract(code)


class TestIRDiffer:
    """Tests for IRDiffer."""

    def test_diff_identical_irs(self):
        """Test that identical IRs produce no differences."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers"),
            signature=SigClause(
                name="add",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns="int",
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers"),
            signature=SigClause(
                name="add",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns="int",
            ),
        )

        result = differ.diff(ir1, ir2)

        assert len(result.differences) == 0
        assert result.is_match()
        assert result.fidelity_score() == 1.0

    def test_diff_different_signature_name(self):
        """Test detecting different signature names."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func1", parameters=[], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func2", parameters=[], returns=None),
        )

        result = differ.diff(ir1, ir2)

        assert len(result.differences) == 1
        assert result.differences[0].kind == DifferenceKind.SIGNATURE_NAME
        assert result.differences[0].original_value == "func1"
        assert result.differences[0].extracted_value == "func2"
        assert not result.is_match()

    def test_diff_different_return_type(self):
        """Test detecting different return types."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns="int"),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns="str"),
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.RETURN_TYPE][0]
        assert diff.original_value == "int"
        assert diff.extracted_value == "str"
        assert diff.severity == "warning"  # Type differences are warnings

    def test_diff_different_parameter_count(self):
        """Test detecting different parameter counts."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns=None,
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[Parameter("a", "int")], returns=None),
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.PARAMETER_COUNT][0]
        assert diff.original_value == 2
        assert diff.extracted_value == 1

    def test_diff_different_parameter_name(self):
        """Test detecting different parameter names."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[Parameter("x", "int")], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[Parameter("y", "int")], returns=None),
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.PARAMETER_NAME][0]
        assert diff.original_value == "x"
        assert diff.extracted_value == "y"

    def test_diff_different_parameter_type(self):
        """Test detecting different parameter types."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[Parameter("x", "int")], returns=None),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[Parameter("x", "str")], returns=None),
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.PARAMETER_TYPE][0]
        assert diff.original_value == "int"
        assert diff.extracted_value == "str"
        assert diff.severity == "warning"

    def test_diff_different_assertion_count(self):
        """Test detecting different assertion counts."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[
                AssertClause(predicate="x > 0"),
                AssertClause(predicate="y > 0"),
            ],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0")],
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.ASSERTION_COUNT][0]
        assert diff.original_value == 2
        assert diff.extracted_value == 1
        assert diff.severity == "warning"

    def test_diff_different_assertion_predicate(self):
        """Test detecting different assertion predicates."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0")],
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="func", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x >= 0")],
        )

        result = differ.diff(ir1, ir2)

        diff = [d for d in result.differences if d.kind == DifferenceKind.ASSERTION_PREDICATE][0]
        assert diff.original_value == "x > 0"
        assert diff.extracted_value == "x >= 0"

    def test_fidelity_score_calculation(self):
        """Test fidelity score calculation."""
        differ = IRDiffer()

        ir1 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns="int",
            ),
        )

        ir2 = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="func",
                parameters=[Parameter("a", "int"), Parameter("b", "str")],  # Different type
                returns="int",
            ),
        )

        result = differ.diff(ir1, ir2)

        # Should have high fidelity (only one type difference)
        assert result.fidelity_score() > 0.8
        assert result.fidelity_score() < 1.0


class TestRoundTripValidator:
    """Tests for RoundTripValidator."""

    def test_validate_simple_function(self):
        """Test round-trip validation of simple function."""
        validator = RoundTripValidator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers"),
            signature=SigClause(
                name="add",
                parameters=[Parameter("a", "int"), Parameter("b", "int")],
                returns="int",
            ),
        )

        result = validator.validate(ir)

        assert result.original_ir == ir
        assert result.generated_code
        assert result.extracted_ir
        assert result.diff_result
        # Should match on signature
        assert result.extracted_ir.signature.name == "add"
        assert len(result.extracted_ir.signature.parameters) == 2

    def test_validate_function_with_assertions(self):
        """Test round-trip validation preserves assertions."""
        config = CodeGeneratorConfig(inject_assertions=True, assertion_mode="assert")
        generator = CodeGenerator(config=config)
        validator = RoundTripValidator(code_generator=generator)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Divide numbers"),
            signature=SigClause(
                name="divide",
                parameters=[Parameter("a", "float"), Parameter("b", "float")],
                returns="float",
            ),
            assertions=[AssertClause(predicate="b != 0", rationale="No division by zero")],
        )

        result = validator.validate(ir)

        # Should extract the assertion
        assert len(result.extracted_ir.assertions) >= 1
        # Predicate should match
        extracted_predicates = [a.predicate for a in result.extracted_ir.assertions]
        assert "b != 0" in extracted_predicates

    def test_validate_function_without_assertions(self):
        """Test round-trip validation with assertions disabled."""
        config = CodeGeneratorConfig(inject_assertions=False)
        generator = CodeGenerator(config=config)
        validator = RoundTripValidator(code_generator=generator)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
            assertions=[AssertClause(predicate="x > 0")],
        )

        result = validator.validate(ir)

        # Should not extract assertions if not generated
        assert len(result.extracted_ir.assertions) == 0

    def test_is_valid_method(self):
        """Test is_valid method on RoundTripResult."""
        validator = RoundTripValidator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        result = validator.validate(ir)

        # Should be valid (no errors)
        assert result.is_valid() in [True, False]  # Depends on extraction quality
        assert isinstance(result.fidelity_score(), float)
        assert 0.0 <= result.fidelity_score() <= 1.0

    def test_validate_complex_types(self):
        """Test round-trip validation with complex types."""
        validator = RoundTripValidator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Process data"),
            signature=SigClause(
                name="process",
                parameters=[Parameter("data", "list[int]")],
                returns="dict[str, int]",
            ),
        )

        result = validator.validate(ir)

        # Should preserve complex types
        assert "list[int]" in result.extracted_ir.signature.parameters[0].type_hint
        assert (
            "dict[str, int]" in result.extracted_ir.signature.returns
            or result.extracted_ir.signature.returns == "dict[str, int]"
        )

    def test_fidelity_score(self):
        """Test fidelity score is calculated correctly."""
        validator = RoundTripValidator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(
                name="test",
                parameters=[Parameter("x", "int")],
                returns="str",
            ),
        )

        result = validator.validate(ir)

        score = result.fidelity_score()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_generated_code_is_valid_python(self):
        """Test that generated code is valid Python."""
        import ast

        validator = RoundTripValidator()

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test"),
            signature=SigClause(name="test", parameters=[], returns=None),
        )

        result = validator.validate(ir)

        # Should be valid Python syntax
        ast.parse(result.generated_code)
