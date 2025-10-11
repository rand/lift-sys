"""Unit tests for IR parser.

Tests cover:
- Valid IR parsing
- Syntax error handling
- TypedHole parsing
- Edge cases (empty files, comments only)
- Round-trip serialization
"""

import pytest
from lark.exceptions import UnexpectedCharacters, UnexpectedToken


@pytest.mark.unit
class TestIRParser:
    """Unit tests for IRParser class."""

    def test_parse_simple_ir(self, ir_parser, sample_simple_ir):
        """Test parsing simple IR without holes."""
        ir = ir_parser.parse(sample_simple_ir)

        assert ir.signature.name == "add"
        assert len(ir.signature.parameters) == 2
        assert ir.signature.parameters[0].name == "a"
        assert ir.signature.parameters[1].name == "b"
        assert ir.signature.returns == "int"
        assert len(ir.assertions) == 3
        assert len(ir.typed_holes()) == 0

    def test_parse_ir_with_typed_holes(self, ir_parser, sample_with_holes_ir):
        """Test parsing IR with TypedHole syntax."""
        ir = ir_parser.parse(sample_with_holes_ir)

        assert ir.signature.name == "factorial"
        holes = ir.typed_holes()
        assert len(holes) >= 4

        # Check hole types
        hole_ids = [h.identifier for h in holes]
        assert "optimization_strategy" in hole_ids
        assert "max_recursion" in hole_ids
        assert "cache_size" in hole_ids

    def test_parse_ir_with_effects(self, ir_parser, sample_complex_ir):
        """Test parsing IR with effects clause."""
        ir = ir_parser.parse(sample_complex_ir)

        assert ir.signature.name == "binary_search"
        assert len(ir.effects) == 2
        assert "reads array elements" in ir.effects[0].description
        assert "may return -1" in ir.effects[1].description

    def test_parse_ir_with_comments(self, ir_parser):
        """Test that comments are properly ignored."""
        ir_text = """
ir test {
  # This is a comment
  intent: test function # inline comment
  signature: test(x: int) -> int
  # Another comment
  assert:
    - x > 0  # assertion comment
}
"""
        ir = ir_parser.parse(ir_text)
        assert ir.signature.name == "test"
        assert len(ir.assertions) == 1

    def test_parse_empty_file_raises_error(self, ir_parser):
        """Test that empty file raises parse error."""
        with pytest.raises((UnexpectedToken, UnexpectedCharacters)):
            ir_parser.parse("")

    def test_parse_comments_only_raises_error(self, ir_parser):
        """Test that file with only comments raises error."""
        with pytest.raises((UnexpectedToken, UnexpectedCharacters)):
            ir_parser.parse("# Just comments\n# Nothing else\n")

    def test_parse_missing_signature_raises_error(self, ir_parser, sample_invalid_ir):
        """Test that IR missing required signature raises error."""
        with pytest.raises((UnexpectedToken, UnexpectedCharacters)):
            ir_parser.parse(sample_invalid_ir)

    def test_parse_invalid_syntax_raises_error(self, ir_parser):
        """Test that invalid syntax raises appropriate error."""
        invalid_ir = """
ir broken {
  intent: test
  signature: broken(x: int
  # Missing closing paren and other syntax errors
"""
        with pytest.raises((UnexpectedToken, UnexpectedCharacters)):
            ir_parser.parse(invalid_ir)

    def test_parse_hole_with_metadata(self, ir_parser):
        """Test parsing hole with description metadata."""
        ir_text = """
ir test {
  intent: test
  signature: test(x: int) -> int {<?param: str = "parameter description"?>}
  assert:
    - x > 0
}
"""
        ir = ir_parser.parse(ir_text)
        holes = ir.typed_holes()
        assert len(holes) == 1
        assert holes[0].identifier == "param"
        assert holes[0].description == "parameter description"

    def test_round_trip_serialization(self, ir_parser, sample_simple_ir):
        """Test IR can be parsed, dumped, and re-parsed."""
        ir1 = ir_parser.parse(sample_simple_ir)
        text = ir_parser.dumps(ir1)

        # Text should contain key elements
        assert "add" in text
        assert "signature" in text
        assert "intent" in text

        # Re-parse should produce equivalent IR
        ir2 = ir_parser.parse(text)
        assert ir2.signature.name == ir1.signature.name
        assert len(ir2.assertions) == len(ir1.assertions)

    def test_parse_multiple_parameters(self, ir_parser):
        """Test parsing function with multiple parameters."""
        ir_text = """
ir multi_param {
  intent: test multiple parameters
  signature: func(a: int, b: str, c: float, d: bool) -> dict
  assert:
    - a > 0
}
"""
        ir = ir_parser.parse(ir_text)
        assert len(ir.signature.parameters) == 4
        assert ir.signature.parameters[0].name == "a"
        assert ir.signature.parameters[1].name == "b"
        assert ir.signature.parameters[2].name == "c"
        assert ir.signature.parameters[3].name == "d"

    def test_parse_no_return_type(self, ir_parser):
        """Test parsing function without return type."""
        ir_text = """
ir no_return {
  intent: function with no return
  signature: no_return(x: int)
  assert:
    - x > 0
}
"""
        ir = ir_parser.parse(ir_text)
        assert ir.signature.returns is None

    def test_parse_no_parameters(self, ir_parser):
        """Test parsing function with no parameters."""
        ir_text = """
ir no_params {
  intent: function with no params
  signature: no_params() -> int
  assert:
    - result > 0
}
"""
        ir = ir_parser.parse(ir_text)
        assert len(ir.signature.parameters) == 0
        assert ir.signature.returns == "int"

    def test_parse_multiple_assertions(self, ir_parser):
        """Test parsing multiple assertions."""
        ir_text = """
ir multi_assert {
  intent: test
  signature: test(x: int, y: int) -> int
  assert:
    - x > 0
    - y > 0
    - x < 100
    - y < 100
    - x + y > 0
}
"""
        ir = ir_parser.parse(ir_text)
        assert len(ir.assertions) == 5
        predicates = [a.predicate for a in ir.assertions]
        assert "x > 0" in predicates
        assert "x + y > 0" in predicates

    def test_typed_hole_kinds(self, ir_parser):
        """Test that typed holes are assigned correct kinds."""
        ir_text = """
ir hole_kinds {
  intent: test hole kinds {<?intent_hole: str = "in intent"?>}
  signature: test(x: int) -> int {<?sig_hole: int = "in signature"?>}
  effects:
    - has effect {<?effect_hole: str = "in effect"?>}
  assert:
    - x > 0 {<?assert_hole: str = "in assertion"?>}
}
"""
        ir = ir_parser.parse(ir_text)
        holes = ir.typed_holes()
        assert len(holes) == 4

        # Check that holes are in different clauses
        intent_holes = ir.intent.holes
        sig_holes = ir.signature.holes
        effect_holes = ir.effects[0].holes
        assert_holes = ir.assertions[0].holes

        assert len(intent_holes) == 1
        assert len(sig_holes) == 1
        assert len(effect_holes) == 1
        assert len(assert_holes) == 1
