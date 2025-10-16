#!/usr/bin/env python3
"""
Non-trivial test cases for comprehensive validation.

Organized by category and complexity level.
"""

# Phase 1: High Priority Tests (5 tests)
PHASE_1_TESTS = [
    {
        "name": "letter_grade",
        "category": "control_flow",
        "complexity": "medium",
        "prompt": "Create a function that returns a letter grade (A, B, C, D, or F) based on a numeric score. A is 90+, B is 80-89, C is 70-79, D is 60-69, F is below 60",
        "function_name": "get_grade",
        "test_cases": [
            ((95,), "A"),
            ((85,), "B"),
            ((75,), "C"),
            ((65,), "D"),
            ((55,), "F"),
            ((90,), "A"),  # Boundary
            ((60,), "D"),  # Boundary
        ],
    },
    {
        "name": "filter_even",
        "category": "list_operations",
        "complexity": "medium",
        "prompt": "Create a function that returns a new list containing only the even numbers from the input list",
        "function_name": "filter_even_numbers",
        "test_cases": [
            (([1, 2, 3, 4, 5, 6],), [2, 4, 6]),
            (([1, 3, 5],), []),
            (([],), []),
            (([2, 4, 6],), [2, 4, 6]),
            (([0, -2, -3, 4],), [0, -2, 4]),
        ],
    },
    {
        "name": "count_words",
        "category": "string_manipulation",
        "complexity": "easy",
        "prompt": "Create a function that counts the number of words in a string, where words are separated by spaces",
        "function_name": "count_words",
        "test_cases": [
            (("hello world",), 2),
            (("one",), 1),
            (("",), 0),
            (("  multiple   spaces  ",), 2),
            (("a b c d e",), 5),
        ],
    },
    {
        "name": "first_or_none",
        "category": "edge_cases",
        "complexity": "easy",
        "prompt": "Create a function that returns the first element of a list, or None if the list is empty",
        "function_name": "first_element",
        "test_cases": [
            (([1, 2, 3],), 1),
            (([],), None),
            ((["a"],), "a"),
            (([42, 10, 5],), 42),
        ],
    },
    {
        "name": "classify_number",
        "category": "control_flow",
        "complexity": "medium_hard",
        "prompt": "Create a function that classifies a number. Return 'zero' if zero, 'negative' if negative, 'positive even' if positive and even, or 'positive odd' if positive and odd",
        "function_name": "classify_number",
        "test_cases": [
            ((10,), "positive even"),
            ((7,), "positive odd"),
            ((-5,), "negative"),
            ((0,), "zero"),
            ((-2,), "negative"),
            ((1,), "positive odd"),
        ],
    },
]

# Phase 2: Medium Coverage Tests (+5 tests)
PHASE_2_TESTS = [
    {
        "name": "find_index",
        "category": "list_operations",
        "complexity": "medium",
        "prompt": "Create a function that takes a list and a value as parameters (in that order). Use a for loop with enumerate to iterate through the list. Inside the loop, if an item equals the value, return its index immediately. After the loop ends (not inside it), return -1 to indicate the value was not found.",
        "function_name": "find_value_index",
        "test_cases": [
            (([10, 20, 30], 20), 1),
            (([10, 20, 30], 40), -1),
            (([], 10), -1),
            (([5, 5, 5], 5), 0),  # First occurrence
            (([1, 2, 3], 3), 2),
        ],
    },
    {
        "name": "title_case",
        "category": "string_manipulation",
        "complexity": "medium",
        "prompt": "Create a function that capitalizes the first letter of each word in a string (title case)",
        "function_name": "to_title_case",
        "test_cases": [
            (("hello world",), "Hello World"),
            (("a",), "A"),
            (("",), ""),
            (("python programming",), "Python Programming"),
        ],
    },
    {
        "name": "factorial",
        "category": "mathematical",
        "complexity": "medium",
        "prompt": "Create a function that calculates the factorial of a non-negative integer. Factorial of n is n * (n-1) * ... * 1, and 0! = 1",
        "function_name": "calculate_factorial",
        "test_cases": [
            ((5,), 120),
            ((0,), 1),
            ((1,), 1),
            ((3,), 6),
            ((10,), 3628800),
        ],
    },
    {
        "name": "get_type_name",
        "category": "type_operations",
        "complexity": "medium",
        "prompt": "Create a function that checks the type of a value. Use isinstance() to check if the value is an int, str, or list (in that order with if-elif). Return the exact string 'int', 'str', or 'list' if it matches. If none match, return exactly 'other' (not 'unknown' or anything else, must be the string 'other').",
        "function_name": "get_type_name",
        "test_cases": [
            ((5,), "int"),
            (("hi",), "str"),
            (([1, 2],), "list"),
            ((3.14,), "other"),
            ((True,), "other"),
        ],
    },
    {
        "name": "clamp_value",
        "category": "edge_cases",
        "complexity": "medium",
        "prompt": "Create a function that clamps a value between a minimum and maximum (inclusive). If value < min return min, if value > max return max, otherwise return value",
        "function_name": "clamp",
        "test_cases": [
            ((5, 0, 10), 5),
            ((-5, 0, 10), 0),
            ((15, 0, 10), 10),
            ((0, 0, 10), 0),  # Boundary
            ((10, 0, 10), 10),  # Boundary
        ],
    },
]

# Phase 3: Full Coverage Tests (+8 tests)
PHASE_3_TESTS = [
    {
        "name": "validate_password",
        "category": "control_flow",
        "complexity": "medium",
        "prompt": "Create a function that validates a password. Return 'too short' if less than 8 chars, 'no number' if no digit, 'no uppercase' if no uppercase letter, or 'valid' if all conditions met",
        "function_name": "validate_password",
        "test_cases": [
            (("abc",), "too short"),
            (("abcdefgh",), "no number"),
            (("abcdefg1",), "no uppercase"),
            (("Abcdefg1",), "valid"),
            (("PASSWORD123",), "valid"),
        ],
    },
    {
        "name": "average_numbers",
        "category": "list_operations",
        "complexity": "medium",
        "prompt": "Create a function that calculates the average of a list of numbers. Return 0.0 for an empty list",
        "function_name": "calculate_average",
        "test_cases": [
            (([1, 2, 3, 4, 5],), 3.0),
            (([10],), 10.0),
            (([],), 0.0),
            (([2, 4],), 3.0),
        ],
    },
    {
        "name": "is_valid_email",
        "category": "string_manipulation",
        "complexity": "medium",
        "prompt": "Create a function that checks if a string is a valid email address. Must contain @ symbol and a dot after the @",
        "function_name": "is_valid_email",
        "test_cases": [
            (("user@example.com",), True),
            (("user@example",), False),
            (("userexample.com",), False),
            (("@example.com",), False),
            (("user@.com",), False),
        ],
    },
    {
        "name": "fibonacci",
        "category": "mathematical",
        "complexity": "medium_hard",
        "prompt": "Create a function that returns the nth Fibonacci number (0-indexed). Fibonacci sequence: 0, 1, 1, 2, 3, 5, 8, 13, ...",
        "function_name": "get_fibonacci",
        "test_cases": [
            ((0,), 0),
            ((1,), 1),
            ((2,), 1),
            ((5,), 5),
            ((10,), 55),
        ],
    },
    {
        "name": "is_prime",
        "category": "mathematical",
        "complexity": "medium",
        "prompt": "Create a function that checks if a number is prime. A prime number is greater than 1 and only divisible by 1 and itself",
        "function_name": "is_prime_number",
        "test_cases": [
            ((7,), True),
            ((4,), False),
            ((1,), False),
            ((2,), True),
            ((13,), True),
            ((15,), False),
        ],
    },
    {
        "name": "safe_int_conversion",
        "category": "type_operations",
        "complexity": "medium",
        "prompt": "Create a function that converts a string to an integer, returning 0 if the conversion fails",
        "function_name": "safe_int",
        "test_cases": [
            (("123",), 123),
            (("abc",), 0),
            (("",), 0),
            (("456",), 456),
        ],
    },
    {
        "name": "min_max_tuple",
        "category": "data_structures",
        "complexity": "medium",
        "prompt": "Create a function that returns both the minimum and maximum values from a list as a tuple (min, max)",
        "function_name": "get_min_max",
        "test_cases": [
            (([1, 5, 3],), (1, 5)),
            (([7],), (7, 7)),
            (([3, 1, 4, 1, 5],), (1, 5)),
            (([-5, -1, -10],), (-10, -1)),
        ],
    },
    {
        "name": "merge_dictionaries",
        "category": "data_structures",
        "complexity": "medium",
        "prompt": "Create a function that merges two dictionaries, with values from the second dictionary overwriting the first for duplicate keys",
        "function_name": "merge_dicts",
        "test_cases": [
            (({"a": 1}, {"b": 2}), {"a": 1, "b": 2}),
            (({"a": 1}, {"a": 2}), {"a": 2}),
            (({}, {"x": 10}), {"x": 10}),
            (({"a": 1, "b": 2}, {"b": 3, "c": 4}), {"a": 1, "b": 3, "c": 4}),
        ],
    },
]

# Combined test suites
ALL_TESTS = PHASE_1_TESTS + PHASE_2_TESTS + PHASE_3_TESTS

# Test suite definitions
TEST_SUITES = {
    "phase1": {
        "name": "Phase 1: High Priority",
        "tests": PHASE_1_TESTS,
        "description": "Critical functionality validation (5 tests)",
    },
    "phase2": {
        "name": "Phase 2: Medium Coverage",
        "tests": PHASE_1_TESTS + PHASE_2_TESTS,
        "description": "Comprehensive validation (10 tests)",
    },
    "phase3": {
        "name": "Phase 3: Full Coverage",
        "tests": ALL_TESTS,
        "description": "Complete validation (18 tests)",
    },
}


def get_test_suite(phase="phase1"):
    """Get test suite by phase name."""
    return TEST_SUITES.get(phase, TEST_SUITES["phase1"])


def get_tests_by_category(category):
    """Filter tests by category."""
    return [t for t in ALL_TESTS if t["category"] == category]


def get_tests_by_complexity(complexity):
    """Filter tests by complexity."""
    return [t for t in ALL_TESTS if t["complexity"] == complexity]
