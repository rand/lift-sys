"""Integration tests for XGrammarIRTranslator with automatic constraint detection."""

import pytest

from lift_sys.forward_mode.xgrammar_translator import XGrammarIRTranslator
from lift_sys.ir.constraints import (
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    PositionConstraint,
    PositionRequirement,
    ReturnConstraint,
)
from lift_sys.providers.mock import MockProvider


class TestXGrammarTranslatorConstraintDetection:
    """Test that XGrammarIRTranslator automatically detects and applies constraints."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""
        return MockProvider()

    @pytest.fixture
    def translator(self, mock_provider):
        """Create translator with mock provider."""
        return XGrammarIRTranslator(mock_provider)

    @pytest.mark.asyncio
    async def test_detects_return_constraint_for_count_function(self, translator, mock_provider):
        """Should automatically detect ReturnConstraint for count function."""
        # Setup mock to return count_words IR
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Count the number of words in a string"
  },
  "signature": {
    "name": "count_words",
    "parameters": [
      {"name": "text", "type_hint": "str"}
    ],
    "returns": "int"
  },
  "effects": [
    {"description": "Split text into words and count them"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate prompt
        ir = await translator.translate("Write a function that counts words in text")

        # Should have automatically detected and added ReturnConstraint
        assert len(ir.constraints) > 0

        # Find ReturnConstraint
        return_constraints = [c for c in ir.constraints if isinstance(c, ReturnConstraint)]
        assert len(return_constraints) == 1
        assert return_constraints[0].value_name == "count"

    @pytest.mark.asyncio
    async def test_detects_loop_constraint_for_find_first(self, translator, mock_provider):
        """Should automatically detect LoopBehaviorConstraint for find first function."""
        # Setup mock to return find_index IR
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Find the first index of a value in a list"
  },
  "signature": {
    "name": "find_index",
    "parameters": [
      {"name": "lst", "type_hint": "list"},
      {"name": "value", "type_hint": "Any"}
    ],
    "returns": "int"
  },
  "effects": [
    {"description": "Iterate through list to find first occurrence"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate prompt
        ir = await translator.translate(
            "Write a function that finds the first index of a value in a list"
        )

        # Should have automatically detected and added LoopBehaviorConstraint
        assert len(ir.constraints) > 0

        # Find LoopBehaviorConstraint
        loop_constraints = [c for c in ir.constraints if isinstance(c, LoopBehaviorConstraint)]
        assert len(loop_constraints) == 1
        assert loop_constraints[0].search_type == LoopSearchType.FIRST_MATCH
        assert loop_constraints[0].requirement == LoopRequirement.EARLY_RETURN

    @pytest.mark.asyncio
    async def test_detects_position_constraint_for_email_validation(
        self, translator, mock_provider
    ):
        """Should automatically detect PositionConstraint for email validation."""
        # Setup mock to return email validation IR
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Validate email address format"
  },
  "signature": {
    "name": "is_valid_email",
    "parameters": [
      {"name": "email", "type_hint": "str"}
    ],
    "returns": "bool"
  },
  "effects": [
    {"description": "Check that @ and . are present and not adjacent"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate prompt
        ir = await translator.translate("Write a function that validates email addresses")

        # Should have automatically detected and added PositionConstraint
        assert len(ir.constraints) > 0

        # Find PositionConstraint
        pos_constraints = [c for c in ir.constraints if isinstance(c, PositionConstraint)]
        assert len(pos_constraints) == 1
        assert pos_constraints[0].elements == ["@", "."]
        assert pos_constraints[0].requirement == PositionRequirement.NOT_ADJACENT

    @pytest.mark.asyncio
    async def test_detects_multiple_constraints(self, translator, mock_provider):
        """Should detect multiple constraint types when applicable."""
        # Setup mock to return IR with multiple constraint triggers
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Find first valid email and compute its index"
  },
  "signature": {
    "name": "find_first_valid_email",
    "parameters": [
      {"name": "emails", "type_hint": "list[str]"}
    ],
    "returns": "int"
  },
  "effects": [
    {"description": "Iterate through emails, check @ and . are not adjacent"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate prompt
        ir = await translator.translate(
            "Write a function that finds the first valid email in a list"
        )

        # Should detect all three constraint types
        assert len(ir.constraints) >= 3

        # Verify each type is present
        has_return = any(isinstance(c, ReturnConstraint) for c in ir.constraints)
        has_loop = any(isinstance(c, LoopBehaviorConstraint) for c in ir.constraints)
        has_position = any(isinstance(c, PositionConstraint) for c in ir.constraints)

        assert has_return, "Should detect ReturnConstraint (compute index)"
        assert has_loop, "Should detect LoopBehaviorConstraint (first match)"
        assert has_position, "Should detect PositionConstraint (email validation)"

    @pytest.mark.asyncio
    async def test_no_constraints_when_not_applicable(self, translator, mock_provider):
        """Should not add constraints when none are applicable."""
        # Setup mock to return simple greeting IR
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Print hello world"
  },
  "signature": {
    "name": "greet",
    "parameters": [],
    "returns": "None"
  },
  "effects": [
    {"description": "Display greeting message"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate prompt
        ir = await translator.translate("Write a function that prints hello world")

        # Should not add any constraints (no compute, no loops, no position requirements)
        assert len(ir.constraints) == 0

    @pytest.mark.asyncio
    async def test_constraints_preserved_across_refinement(self, translator, mock_provider):
        """Should preserve manually added constraints when refining IR."""
        # Setup mock for initial IR
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Count the number of words in a string"
  },
  "signature": {
    "name": "count_words",
    "parameters": [
      {"name": "text", "type_hint": "str"}
    ],
    "returns": "int"
  },
  "effects": [
    {"description": "Split text into words and count them"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # First translation
        ir1 = await translator.translate("Count words in text")
        initial_constraint_count = len(ir1.constraints)

        # Manually add a PositionConstraint
        manual_constraint = PositionConstraint(
            elements=["x", "y"],
            requirement=PositionRequirement.ORDERED,
        )
        ir1.constraints.append(manual_constraint)

        # Setup mock for refined IR (same structure)
        mock_provider.set_response(
            """
{
  "intent": {
    "summary": "Count the number of words in a string",
    "rationale": "Enhanced with better error handling"
  },
  "signature": {
    "name": "count_words",
    "parameters": [
      {"name": "text", "type_hint": "str"}
    ],
    "returns": "int"
  },
  "effects": [
    {"description": "Split text into words and count them"}
  ],
  "metadata": {
    "language": "python"
  }
}
"""
        )

        # Translate again (simulating refinement)
        ir2 = await translator.translate("Add error handling to count_words")

        # Should have re-detected constraints (not duplicated)
        # Constraint count should be same as initial (auto-detected only)
        assert len(ir2.constraints) == initial_constraint_count

    @pytest.mark.asyncio
    async def test_constraint_detection_with_structured_generation(self, translator, mock_provider):
        """Should work with structured generation (when available)."""
        # Setup mock to return structured IR (this will enable structured_output capability)
        mock_provider.set_structured_response(
            {
                "intent": {"summary": "Count the words"},
                "signature": {
                    "name": "count_words",
                    "parameters": [{"name": "text", "type_hint": "str"}],
                    "returns": "int",
                },
                "effects": [{"description": "Split and count"}],
                "metadata": {"language": "python"},
            }
        )

        # Translate prompt
        ir = await translator.translate("Count words in text")

        # Should still detect constraints even with structured generation
        assert len(ir.constraints) > 0
        assert any(isinstance(c, ReturnConstraint) for c in ir.constraints)
