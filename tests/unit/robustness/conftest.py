"""Shared fixtures for robustness tests."""

import pytest

from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)


@pytest.fixture
def sample_prompt():
    """Sample NL prompt for testing."""
    return "Create a function that sorts a list of numbers in ascending order"


@pytest.fixture
def sample_ir():
    """Sample IR for testing."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Sort numbers in ascending order"),
        signature=SigClause(
            name="sort_numbers",
            parameters=[Parameter(name="numbers", type_hint="list[int | float]")],
            returns="list[int | float]",
        ),
        effects=[],
        assertions=[AssertClause(predicate="result is sorted in ascending order")],
    )


@pytest.fixture
def sample_code():
    """Sample generated code for testing."""
    return '''
def sort_numbers(numbers):
    """Sort a list of numbers in ascending order."""
    return sorted(numbers)
'''
