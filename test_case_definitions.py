#!/usr/bin/env python3
"""
Test case definitions with execution validation.

Each test case includes:
- name: Test identifier
- prompt: Natural language specification
- category: Test category
- function_name: Expected function name (for execution)
- test_cases: List of (args, expected_output) for validation
"""

# Test cases with execution validation
TEST_CASES_WITH_VALIDATION = [
    {
        "name": "add_numbers",
        "prompt": "Create a function that adds two numbers",
        "category": "arithmetic",
        "function_name": "add_two_numbers",
        "test_cases": [
            ((2, 3), 5),
            ((10, 20), 30),
            ((0, 0), 0),
            ((-5, 5), 0),
        ],
    },
    {
        "name": "multiply",
        "prompt": "Create a function that multiplies two numbers",
        "category": "arithmetic",
        "function_name": "multiply",
        "test_cases": [
            ((2, 3), 6),
            ((10, 5), 50),
            ((0, 10), 0),
            ((-2, 3), -6),
        ],
    },
    {
        "name": "string_length",
        "prompt": "Create a function that returns the length of a string",
        "category": "string",
        "function_name": "get_string_length",
        "test_cases": [
            (("hello",), 5),
            (("",), 0),
            (("test string",), 11),
        ],
    },
    {
        "name": "uppercase",
        "prompt": "Create a function that converts a string to uppercase",
        "category": "string",
        "function_name": "to_uppercase",
        "test_cases": [
            (("hello",), "HELLO"),
            (("Test",), "TEST"),
            (("",), ""),
        ],
    },
    {
        "name": "is_even",
        "prompt": "Create a function that checks if a number is even",
        "category": "boolean",
        "function_name": "is_even",
        "test_cases": [
            ((2,), True),
            ((3,), False),
            ((0,), True),
            ((-4,), True),
        ],
    },
]

# Quick validation set (3 tests)
QUICK_VALIDATION_TESTS = [
    TEST_CASES_WITH_VALIDATION[0],  # add_numbers
    TEST_CASES_WITH_VALIDATION[2],  # string_length
    TEST_CASES_WITH_VALIDATION[4],  # is_even
]
