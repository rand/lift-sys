#!/usr/bin/env python3
"""
Expanded Test Case Definitions for Performance Benchmarking

Categories:
1. Simple Arithmetic (no control flow)
2. String Operations (no control flow)
3. List Operations (basic, no complex loops)
4. Boolean Logic (simple conditions, may trigger indentation bug)
5. Edge Cases (None handling, empty inputs)
6. Type Conversions (basic operations)

Each test case: (name, prompt, category)
"""

# Category 1: Simple Arithmetic (Expected: 100% success)
SIMPLE_ARITHMETIC = [
    ("add_numbers", "Create a function that adds two numbers", "arithmetic"),
    ("multiply", "Create a function that multiplies two numbers", "arithmetic"),
    ("subtract", "Create a function that subtracts one number from another", "arithmetic"),
    ("divide", "Create a function that divides one number by another", "arithmetic"),
    (
        "absolute_value",
        "Create a function that returns the absolute value of a number",
        "arithmetic",
    ),
    ("power", "Create a function that raises a number to a power", "arithmetic"),
]

# Category 2: String Operations (Expected: 90%+ success)
STRING_OPERATIONS = [
    ("string_length", "Create a function that returns the length of a string", "string"),
    ("uppercase", "Create a function that converts a string to uppercase", "string"),
    ("lowercase", "Create a function that converts a string to lowercase", "string"),
    ("string_concat", "Create a function that concatenates two strings", "string"),
    ("string_reverse", "Create a function that reverses a string", "string"),
]

# Category 3: List Operations (Expected: 80%+ success - simple loops may work)
LIST_OPERATIONS = [
    ("list_length", "Create a function that returns the length of a list", "list"),
    ("list_sum", "Create a function that returns the sum of numbers in a list", "list"),
    ("list_first", "Create a function that returns the first element of a list", "list"),
    ("list_last", "Create a function that returns the last element of a list", "list"),
]

# Category 4: Boolean Logic (Expected: 50-70% - may trigger indentation bug)
BOOLEAN_LOGIC = [
    ("is_even", "Create a function that checks if a number is even", "boolean"),
    ("is_positive", "Create a function that checks if a number is positive", "boolean"),
    ("max_of_two", "Create a function that returns the maximum of two numbers", "boolean"),
    ("min_of_two", "Create a function that returns the minimum of two numbers", "boolean"),
    ("is_empty_string", "Create a function that checks if a string is empty", "boolean"),
]

# Category 5: Edge Cases (Expected: 60-80% - depends on prompt interpretation)
EDGE_CASES = [
    (
        "safe_divide",
        "Create a function that divides two numbers and returns zero if the divisor is zero",
        "edge_case",
    ),
    (
        "default_value",
        "Create a function that returns a value or a default if the value is None",
        "edge_case",
    ),
]

# Category 6: Type Conversions (Expected: 90%+ success)
TYPE_CONVERSIONS = [
    ("int_to_string", "Create a function that converts an integer to a string", "type_conversion"),
    ("string_to_int", "Create a function that converts a string to an integer", "type_conversion"),
    ("float_to_int", "Create a function that converts a float to an integer", "type_conversion"),
]

# Combined test suite
ALL_TEST_CASES = (
    SIMPLE_ARITHMETIC
    + STRING_OPERATIONS
    + LIST_OPERATIONS
    + BOOLEAN_LOGIC
    + EDGE_CASES
    + TYPE_CONVERSIONS
)

# Summary
CATEGORY_COUNTS = {
    "arithmetic": len(SIMPLE_ARITHMETIC),
    "string": len(STRING_OPERATIONS),
    "list": len(LIST_OPERATIONS),
    "boolean": len(BOOLEAN_LOGIC),
    "edge_case": len(EDGE_CASES),
    "type_conversion": len(TYPE_CONVERSIONS),
}

EXPECTED_SUCCESS_RATES = {
    "arithmetic": 1.0,  # 100%
    "string": 0.9,  # 90%
    "list": 0.8,  # 80%
    "boolean": 0.6,  # 60% (indentation bug)
    "edge_case": 0.7,  # 70%
    "type_conversion": 0.9,  # 90%
}


def print_test_suite_summary():
    """Print a summary of the test suite."""
    print("=" * 60)
    print("EXPANDED TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"\nTotal test cases: {len(ALL_TEST_CASES)}")
    print("\nBy category:")
    for category, count in CATEGORY_COUNTS.items():
        expected = EXPECTED_SUCCESS_RATES[category]
        print(f"  {category:20s}: {count:2d} tests (expected {expected * 100:.0f}% success)")

    overall_expected = sum(
        CATEGORY_COUNTS[cat] * EXPECTED_SUCCESS_RATES[cat] for cat in CATEGORY_COUNTS
    ) / len(ALL_TEST_CASES)

    print(f"\nOverall expected success rate: {overall_expected * 100:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    print_test_suite_summary()
    print("\nTest cases:")
    for name, prompt, category in ALL_TEST_CASES:
        print(f"  [{category:15s}] {name:20s}: {prompt}")
