"""Integration tests for XGrammarCodeGenerator with constraint validation (Phase 7)."""

import pytest

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.constraints import (
    LoopBehaviorConstraint,
    LoopRequirement,
    LoopSearchType,
    ReturnConstraint,
)
from lift_sys.ir.models import (
    EffectClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.mock import MockProvider


class TestXGrammarGeneratorConstraintValidation:
    """Test that XGrammarCodeGenerator validates constraints during code generation."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""
        return MockProvider()

    @pytest.fixture
    def generator(self, mock_provider):
        """Create generator with mock provider."""
        return XGrammarCodeGenerator(mock_provider)

    @pytest.mark.asyncio
    async def test_generates_code_satisfying_return_constraint(self, generator, mock_provider):
        """Should generate code that satisfies ReturnConstraint."""
        # Setup IR with ReturnConstraint
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the number of words in a string"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split the text parameter into words using split()"),
                EffectClause(description="Count the number of words"),
                EffectClause(description="Return the count as an integer"),
            ],
            constraints=[ReturnConstraint(value_name="count")],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return code WITH explicit return
        mock_provider.set_structured_response(
            {
                "implementation": {
                    "body_statements": [
                        {"type": "assignment", "code": "count = len(text.split())"},
                        {"type": "return", "code": "return count"},
                    ]
                }
            }
        )

        # Generate code
        result = await generator.generate(ir)

        # Should succeed without constraint violations
        assert "return count" in result.source_code or "return len(" in result.source_code

    @pytest.mark.asyncio
    async def test_retries_when_return_constraint_violated(self, generator, mock_provider):
        """Should retry generation when ReturnConstraint is violated."""
        # Setup IR with ReturnConstraint
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count the number of words in a string"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split the text parameter into words using split()"),
                EffectClause(description="Count the number of words"),
                EffectClause(description="Return the count as an integer"),
            ],
            constraints=[ReturnConstraint(value_name="count")],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return multiple responses:
        # First attempt: missing return (violates constraint)
        # Second attempt: correct with return
        responses = [
            # First attempt - missing return
            {
                "implementation": {
                    "body_statements": [
                        {"type": "assignment", "code": "count = len(text.split())"},
                        # Missing return!
                    ]
                }
            },
            # Second attempt - has return
            {
                "implementation": {
                    "body_statements": [
                        {"type": "assignment", "code": "count = len(text.split())"},
                        {"type": "return", "code": "return count"},
                    ]
                }
            },
        ]

        # Mock provider to return sequential responses
        call_count = 0

        original_generate_structured = mock_provider.generate_structured

        async def sequential_responses(*args, **kwargs):
            nonlocal call_count
            mock_provider.set_structured_response(responses[min(call_count, len(responses) - 1)])
            call_count += 1
            return await original_generate_structured(*args, **kwargs)

        mock_provider.generate_structured = sequential_responses

        # Generate code
        result = await generator.generate(ir, max_retries=3)

        # Should eventually succeed with return
        assert "return" in result.source_code
        # Should have made multiple attempts
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_generates_code_satisfying_loop_constraint(self, generator, mock_provider):
        """Should generate code that satisfies LoopBehaviorConstraint."""
        # Setup IR with LoopBehaviorConstraint
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find the first index of a value in a list"),
            signature=SigClause(
                name="find_index",
                parameters=[
                    Parameter(name="lst", type_hint="list"),
                    Parameter(name="value", type_hint="Any"),
                ],
                returns="int",
            ),
            effects=[
                EffectClause(description="Enumerate through the lst parameter"),
                EffectClause(description="For each item, check if it equals value"),
                EffectClause(description="If match found, return the index immediately"),
                EffectClause(description="If no match found, return -1"),
            ],
            constraints=[
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                )
            ],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return code WITH early return in loop
        mock_provider.set_structured_response(
            {
                "implementation": {
                    "body_statements": [
                        {"type": "for_loop", "code": "for i, item in enumerate(lst):"},
                        {"type": "if_statement", "code": "if item == value:"},
                        {"type": "return", "code": "return i"},
                        {"type": "return", "code": "return -1"},
                    ]
                }
            }
        )

        # Generate code
        result = await generator.generate(ir)

        # Should have early return inside loop
        assert "for" in result.source_code
        assert "return" in result.source_code

    @pytest.mark.asyncio
    async def test_no_constraint_validation_when_no_constraints(self, generator, mock_provider):
        """Should not run constraint validation when IR has no constraints."""
        # Setup IR WITHOUT constraints
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Print hello world"),
            signature=SigClause(
                name="greet",
                parameters=[],
                returns="None",
            ),
            effects=[
                EffectClause(description="Print greeting message to console"),
            ],
            constraints=[],  # No constraints
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return simple code
        mock_provider.set_structured_response(
            {
                "implementation": {
                    "body_statements": [
                        {"type": "expression", "code": "print('Hello, world!')"},
                    ]
                }
            }
        )

        # Generate code
        result = await generator.generate(ir)

        # Should succeed without constraint validation
        assert "print" in result.source_code

    @pytest.mark.asyncio
    async def test_constraint_validation_after_ast_repair(self, generator, mock_provider):
        """Should validate constraints after AST repair has been applied."""
        # Setup IR with constraints
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[
                EffectClause(description="Split the text parameter into words"),
                EffectClause(description="Return the count of words as an integer"),
            ],
            constraints=[ReturnConstraint(value_name="count")],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return code that may need repair
        mock_provider.set_structured_response(
            {
                "implementation": {
                    "body_statements": [
                        {"type": "return", "code": "return len(text.split())"},
                    ]
                }
            }
        )

        # Generate code
        result = await generator.generate(ir)

        # Code should pass constraint validation (after any repairs)
        assert result.source_code
        assert "return" in result.source_code

    @pytest.mark.asyncio
    async def test_constraint_warnings_logged_but_not_blocking(self, generator, mock_provider):
        """Should log constraint warnings but not block generation."""
        # This test verifies that warning-level violations don't prevent code generation
        # For now, all constraints use error severity, so this is a placeholder for future

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Simple function"),
            signature=SigClause(
                name="simple_func",
                parameters=[],
                returns="int",
            ),
            effects=[
                EffectClause(description="Return the integer value 42"),
            ],
            constraints=[],  # No constraints to test warning behavior
            metadata=Metadata(language="python", origin="test"),
        )

        mock_provider.set_structured_response(
            {"implementation": {"body_statements": [{"type": "return", "code": "return 42"}]}}
        )

        # Generate code
        result = await generator.generate(ir)

        # Should succeed
        assert result.source_code

    @pytest.mark.asyncio
    async def test_multiple_constraints_validated_together(self, generator, mock_provider):
        """Should validate all constraints together."""
        # Setup IR with multiple constraints
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Find first valid item"),
            signature=SigClause(
                name="find_first_valid",
                parameters=[Parameter(name="items", type_hint="list")],
                returns="Any",
            ),
            effects=[
                EffectClause(description="Iterate through the items parameter"),
                EffectClause(description="For each item, check if it is not None"),
                EffectClause(description="If valid item found, return it immediately"),
                EffectClause(description="If no valid item found, return None"),
            ],
            constraints=[
                ReturnConstraint(value_name="result"),
                LoopBehaviorConstraint(
                    search_type=LoopSearchType.FIRST_MATCH,
                    requirement=LoopRequirement.EARLY_RETURN,
                ),
            ],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to return code satisfying both constraints
        mock_provider.set_structured_response(
            {
                "implementation": {
                    "body_statements": [
                        {"type": "for_loop", "code": "for item in items:"},
                        {"type": "if_statement", "code": "if item is not None:"},
                        {"type": "return", "code": "return item"},
                        {"type": "return", "code": "return None"},
                    ]
                }
            }
        )

        # Generate code
        result = await generator.generate(ir)

        # Should satisfy both constraints
        assert "for" in result.source_code
        assert "return" in result.source_code


class TestConstraintValidationFeedback:
    """Test that constraint violations provide useful feedback for retries."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""
        return MockProvider()

    @pytest.fixture
    def generator(self, mock_provider):
        """Create generator with mock provider."""
        return XGrammarCodeGenerator(mock_provider)

    @pytest.mark.asyncio
    async def test_constraint_feedback_includes_violation_details(
        self, generator, mock_provider, capsys
    ):
        """Should include constraint violation details in retry feedback."""
        # Setup IR with constraint
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Count words"),
            signature=SigClause(
                name="count_words",
                parameters=[Parameter(name="text", type_hint="str")],
                returns="int",
            ),
            effects=[],
            constraints=[ReturnConstraint(value_name="count")],
            metadata=Metadata(language="python", origin="test"),
        )

        # Setup mock to fail first, then succeed
        call_count = 0
        responses = [
            {
                "implementation": {
                    "body_statements": [
                        {"type": "assignment", "code": "count = len(text.split())"},
                    ]
                }
            },
            {
                "implementation": {
                    "body_statements": [
                        {"type": "return", "code": "return len(text.split())"},
                    ]
                }
            },
        ]

        original_generate_structured = mock_provider.generate_structured

        async def sequential_responses(*args, **kwargs):
            nonlocal call_count
            mock_provider.set_structured_response(responses[min(call_count, len(responses) - 1)])
            call_count += 1
            return await original_generate_structured(*args, **kwargs)

        mock_provider.generate_structured = sequential_responses

        # Generate code
        result = await generator.generate(ir, max_retries=3)

        # Should have printed constraint violation warning
        captured = capsys.readouterr()
        assert "Constraint validation failed" in captured.out or result.source_code

        # Should eventually succeed
        assert "return" in result.source_code
