"""Shared fixtures for E2E tests.

This module provides common fixtures and utilities for end-to-end testing
of the LIFT system workflows.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from lift_sys.api.server import app
from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.providers.mock import MockProvider


@pytest.fixture
def e2e_client():
    """Create a test client for E2E API testing."""
    return TestClient(app)


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing without API calls."""
    return MockProvider()


@pytest.fixture
def typescript_generator(mock_llm_provider):
    """Create a TypeScript generator with mock provider."""
    return TypeScriptGenerator(mock_llm_provider)


@pytest.fixture
def sample_specifications():
    """Provide sample natural language specifications for testing."""
    return {
        "simple_arithmetic": {
            "prompt": "Create a function that adds two numbers together",
            "language": "python",
            "expected_function_name": "add",
        },
        "array_operation": {
            "prompt": "Create a function that filters even numbers from an array",
            "language": "typescript",
            "expected_function_name": "filterEven",
        },
        "async_operation": {
            "prompt": "Create an async function that fetches data from a URL and returns JSON",
            "language": "typescript",
            "expected_function_name": "fetchData",
        },
        "complex_logic": {
            "prompt": """Create a function that validates a password.
            The password must be at least 8 characters, contain uppercase,
            lowercase, and a number.""",
            "language": "python",
            "expected_function_name": "validate_password",
        },
        "multi_function": {
            "prompt": """Create two functions:
            1. A function to calculate the area of a circle given the radius
            2. A function to calculate the circumference of a circle given the radius""",
            "language": "python",
            "expected_function_names": ["calculate_area", "calculate_circumference"],
        },
    }


@pytest.fixture
def sample_python_code():
    """Provide sample Python code for reverse mode testing."""
    return {
        "simple_function": '''
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    return a + b
''',
        "with_validation": '''
def validate_email(email: str) -> bool:
    """Check if email address is valid.

    Args:
        email: Email address to validate

    Returns:
        True if email is valid, False otherwise
    """
    if not email or '@' not in email:
        return False

    parts = email.split('@')
    if len(parts) != 2:
        return False

    username, domain = parts
    return len(username) > 0 and len(domain) > 0 and '.' in domain
''',
        "with_assertions": '''
def factorial(n: int) -> int:
    """Calculate factorial of n.

    Args:
        n: Non-negative integer

    Returns:
        n! (n factorial)

    Raises:
        ValueError: If n is negative
    """
    assert n >= 0, "n must be non-negative"

    if n == 0 or n == 1:
        return 1

    result = 1
    for i in range(2, n + 1):
        result *= i

    return result
''',
    }


@pytest.fixture
def sample_typescript_code():
    """Provide sample TypeScript code for reverse mode testing."""
    return {
        "simple_function": """
export function add(a: number, b: number): number {
    return a + b;
}
""",
        "with_generics": """
export function firstElement<T>(arr: T[]): T | undefined {
    return arr.length > 0 ? arr[0] : undefined;
}
""",
        "async_function": """
export async function fetchUser(id: string): Promise<User> {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
}
""",
    }


@pytest.fixture
def ir_validation_helpers():
    """Provide helper functions for IR validation."""

    def validate_ir_structure(ir_dict: dict[str, Any]) -> bool:
        """Check if IR has required structure."""
        required_keys = ["intent", "signature", "metadata"]
        return all(key in ir_dict for key in required_keys)

    def validate_intent(intent: dict[str, Any]) -> bool:
        """Validate intent clause."""
        return "summary" in intent

    def validate_signature(signature: dict[str, Any]) -> bool:
        """Validate signature clause."""
        return all(key in signature for key in ["name", "parameters", "returns"])

    def validate_assertions(assertions: list[dict[str, Any]]) -> bool:
        """Validate assertion clauses."""
        return all("predicate" in assertion for assertion in assertions)

    return {
        "structure": validate_ir_structure,
        "intent": validate_intent,
        "signature": validate_signature,
        "assertions": validate_assertions,
    }


@pytest.fixture
def code_validation_helpers():
    """Provide helper functions for code validation."""

    def is_valid_python_syntax(code: str) -> bool:
        """Check if Python code has valid syntax."""
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError:
            return False

    def is_valid_typescript_syntax(code: str) -> bool:
        """Check if TypeScript code has valid syntax (basic check)."""
        # Basic syntax checks
        if not code.strip():
            return False

        # Check for balanced braces
        if code.count("{") != code.count("}"):
            return False

        # Check for balanced parentheses
        if code.count("(") != code.count(")"):
            return False

        return True

    def has_function_definition(code: str, function_name: str) -> bool:
        """Check if code contains a function definition."""
        # Python or TypeScript function definition
        return (
            f"def {function_name}" in code
            or f"function {function_name}" in code
            or f"const {function_name}" in code
            or f"export function {function_name}" in code
        )

    def has_type_annotations(code: str) -> bool:
        """Check if code has type annotations."""
        # Python type hints or TypeScript types
        return ": " in code or " -> " in code

    def has_docstring(code: str) -> bool:
        """Check if code has documentation."""
        return '"""' in code or "/**" in code

    return {
        "python_syntax": is_valid_python_syntax,
        "typescript_syntax": is_valid_typescript_syntax,
        "has_function": has_function_definition,
        "has_types": has_type_annotations,
        "has_docs": has_docstring,
    }


@pytest.fixture(scope="module")
def performance_tracker():
    """Track performance metrics for E2E tests."""
    import time

    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}
            self._start_times = {}

        def start(self, operation: str):
            """Start timing an operation."""
            self._start_times[operation] = time.time()

        def end(self, operation: str):
            """End timing an operation and record duration."""
            if operation in self._start_times:
                duration = time.time() - self._start_times[operation]
                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(duration)
                del self._start_times[operation]
                return duration
            return None

        def get_stats(self, operation: str) -> dict[str, float]:
            """Get statistics for an operation."""
            if operation not in self.metrics:
                return {}

            durations = self.metrics[operation]
            return {
                "count": len(durations),
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "total": sum(durations),
            }

        def print_summary(self):
            """Print performance summary."""
            print("\n" + "=" * 60)
            print("PERFORMANCE SUMMARY")
            print("=" * 60)
            for operation, _durations in self.metrics.items():
                stats = self.get_stats(operation)
                print(f"\n{operation}:")
                print(f"  Count: {stats['count']}")
                print(f"  Min:   {stats['min']:.3f}s")
                print(f"  Avg:   {stats['avg']:.3f}s")
                print(f"  Max:   {stats['max']:.3f}s")
            print("=" * 60)

    return PerformanceTracker()


@pytest.fixture(scope="module")
def e2e_test_results():
    """Track E2E test results for success rate calculation."""

    class E2ETestResults:
        def __init__(self):
            self.results = []

        def record(
            self,
            test_name: str,
            success: bool,
            duration: float,
            error: str | None = None,
        ):
            """Record a test result."""
            self.results.append(
                {
                    "test_name": test_name,
                    "success": success,
                    "duration": duration,
                    "error": error,
                }
            )

        def get_success_rate(self) -> float:
            """Calculate overall success rate."""
            if not self.results:
                return 0.0
            successful = sum(1 for r in self.results if r["success"])
            return (successful / len(self.results)) * 100

        def print_summary(self):
            """Print test results summary."""
            print("\n" + "=" * 60)
            print("E2E TEST RESULTS SUMMARY")
            print("=" * 60)
            print(f"Total Tests: {len(self.results)}")
            print(f"Passed: {sum(1 for r in self.results if r['success'])}")
            print(f"Failed: {sum(1 for r in self.results if not r['success'])}")
            print(f"Success Rate: {self.get_success_rate():.1f}%")
            print("\nFailed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['error']}")
            print("=" * 60)

    return E2ETestResults()
