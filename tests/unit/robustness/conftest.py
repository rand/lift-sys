"""Shared fixtures for robustness tests."""

import pytest

from lift_sys.ir.models import IR


@pytest.fixture
def sample_prompt():
    """Sample NL prompt for testing."""
    return "Create a function that sorts a list of numbers in ascending order"


@pytest.fixture
def sample_ir():
    """Sample IR for testing."""
    return IR(
        intent="Sort numbers in ascending order",
        signature={
            "name": "sort_numbers",
            "parameters": [{"name": "numbers", "type": "list[int | float]"}],
            "return_type": "list[int | float]",
        },
        effects=[],
        assertions=[{"type": "sorted", "order": "ascending"}],
    )


@pytest.fixture
def sample_code():
    """Sample generated code for testing."""
    return '''
def sort_numbers(numbers):
    """Sort a list of numbers in ascending order."""
    return sorted(numbers)
'''
