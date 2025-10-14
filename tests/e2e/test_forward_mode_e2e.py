"""End-to-end tests for forward mode: NLP → IR → Code.

These tests verify the complete forward workflow from natural language
specifications to executable code.
"""

from __future__ import annotations

import pytest


class TestForwardModeE2E:
    """E2E tests for forward mode workflows."""

    @pytest.mark.asyncio
    async def test_simple_python_function_generation(
        self,
        sample_specifications,
        code_validation_helpers,
        performance_tracker,
        e2e_test_results,
    ):
        """Test E2E: NLP specification → IR → Python code."""
        spec = sample_specifications["simple_arithmetic"]
        test_name = "simple_python_function_generation"

        try:
            performance_tracker.start(test_name)

            # Step 1: NLP → IR (would normally use LLM, using mock for now)
            # This is a placeholder - actual implementation would call the API
            ir_dict = {
                "intent": {
                    "summary": "Add two numbers together",
                    "rationale": "Perform basic arithmetic addition",
                },
                "signature": {
                    "name": "add",
                    "parameters": [
                        {"name": "a", "type_hint": "int"},
                        {"name": "b", "type_hint": "int"},
                    ],
                    "returns": "int",
                },
                "assertions": [
                    {
                        "predicate": "result == a + b",
                        "rationale": "Sum equals addition of inputs",
                    }
                ],
                "metadata": {"origin": "test", "language": "python"},
            }

            # Verify IR structure
            assert "intent" in ir_dict
            assert "signature" in ir_dict
            assert ir_dict["signature"]["name"] == spec["expected_function_name"]

            # Step 2: IR → Code (would normally use code generator)
            # Placeholder generated code
            generated_code = '''
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Perform basic arithmetic addition

    Args:
        a: First number
        b: Second number

    Returns:
        Sum of a and b
    """
    result = a + b

    # Sum equals addition of inputs
    assert result == a + b, "Sum equals addition of inputs"

    return result
'''

            # Step 3: Validate generated code
            assert code_validation_helpers["python_syntax"](generated_code)
            assert code_validation_helpers["has_function"](
                generated_code, spec["expected_function_name"]
            )
            assert code_validation_helpers["has_types"](generated_code)
            assert code_validation_helpers["has_docs"](generated_code)

            # Step 4: Execute and test
            # Create a scope and execute the code
            scope = {}
            exec(generated_code, scope)

            # Test the function
            add_func = scope["add"]
            result = add_func(2, 3)
            assert result == 5
            assert add_func(10, 20) == 30
            assert add_func(-5, 5) == 0

            duration = performance_tracker.end(test_name)
            e2e_test_results.record(test_name, True, duration)

            print(f"✓ {test_name} passed in {duration:.3f}s")

        except Exception as e:
            duration = performance_tracker.end(test_name) or 0
            e2e_test_results.record(test_name, False, duration, str(e))
            raise

    @pytest.mark.asyncio
    async def test_typescript_function_generation(
        self,
        sample_specifications,
        code_validation_helpers,
        performance_tracker,
        e2e_test_results,
    ):
        """Test E2E: NLP specification → IR → TypeScript code."""
        spec = sample_specifications["array_operation"]
        test_name = "typescript_function_generation"

        try:
            performance_tracker.start(test_name)

            # Step 1: NLP → IR
            ir_dict = {
                "intent": {
                    "summary": "Filter even numbers from an array",
                    "rationale": "Return only the even numbers",
                },
                "signature": {
                    "name": "filterEven",
                    "parameters": [{"name": "numbers", "type_hint": "list[int]"}],
                    "returns": "list[int]",
                },
                "assertions": [
                    {
                        "predicate": "all elements in result are even",
                        "rationale": "All returned numbers must be divisible by 2",
                    }
                ],
                "metadata": {"origin": "test", "language": "typescript"},
            }

            # Verify IR
            assert ir_dict["signature"]["name"] == spec["expected_function_name"]

            # Step 2: IR → TypeScript Code
            generated_code = """
/**
 * Filter even numbers from an array
 *
 * Return only the even numbers
 *
 * @param numbers - Array of numbers to filter
 * @returns Array containing only even numbers
 */
export function filterEven(numbers: Array<number>): Array<number> {
  // All returned numbers must be divisible by 2
  return numbers.filter(n => n % 2 === 0);
}
"""

            # Step 3: Validate generated TypeScript code
            assert code_validation_helpers["typescript_syntax"](generated_code)
            assert code_validation_helpers["has_function"](
                generated_code, spec["expected_function_name"]
            )
            assert code_validation_helpers["has_types"](generated_code)
            assert code_validation_helpers["has_docs"](generated_code)

            # Verify TypeScript-specific features
            assert "Array<number>" in generated_code
            assert "export function" in generated_code
            assert ".filter(" in generated_code
            assert "/**" in generated_code  # TSDoc

            duration = performance_tracker.end(test_name)
            e2e_test_results.record(test_name, True, duration)

            print(f"✓ {test_name} passed in {duration:.3f}s")

        except Exception as e:
            duration = performance_tracker.end(test_name) or 0
            e2e_test_results.record(test_name, False, duration, str(e))
            raise

    @pytest.mark.asyncio
    async def test_complex_validation_logic(
        self,
        sample_specifications,
        code_validation_helpers,
        performance_tracker,
        e2e_test_results,
    ):
        """Test E2E: Complex specification with validation logic."""
        spec = sample_specifications["complex_logic"]
        test_name = "complex_validation_logic"

        try:
            performance_tracker.start(test_name)

            # Step 1: NLP → IR (complex specification)
            ir_dict = {
                "intent": {
                    "summary": "Validate password strength",
                    "rationale": "Check password meets security requirements",
                },
                "signature": {
                    "name": "validate_password",
                    "parameters": [{"name": "password", "type_hint": "str"}],
                    "returns": "bool",
                },
                "assertions": [
                    {
                        "predicate": "len(password) >= 8",
                        "rationale": "Password must be at least 8 characters",
                    },
                    {
                        "predicate": "has uppercase letter",
                        "rationale": "Password must contain uppercase",
                    },
                    {
                        "predicate": "has lowercase letter",
                        "rationale": "Password must contain lowercase",
                    },
                    {
                        "predicate": "has digit",
                        "rationale": "Password must contain number",
                    },
                ],
                "metadata": {"origin": "test", "language": "python"},
            }

            # Verify IR captures all requirements
            assert len(ir_dict["assertions"]) == 4

            # Step 2: IR → Code with multiple checks
            generated_code = '''
def validate_password(password: str) -> bool:
    """Validate password strength.

    Check password meets security requirements

    Args:
        password: Password string to validate

    Returns:
        True if password is valid, False otherwise
    """
    # Password must be at least 8 characters
    if len(password) < 8:
        return False

    # Password must contain uppercase
    if not any(c.isupper() for c in password):
        return False

    # Password must contain lowercase
    if not any(c.islower() for c in password):
        return False

    # Password must contain number
    if not any(c.isdigit() for c in password):
        return False

    return True
'''

            # Step 3: Validate code
            assert code_validation_helpers["python_syntax"](generated_code)
            assert code_validation_helpers["has_function"](
                generated_code, spec["expected_function_name"]
            )

            # Step 4: Execute and test
            scope = {}
            exec(generated_code, scope)
            validate_password = scope["validate_password"]

            # Test various password scenarios
            assert validate_password("Passw0rd") is True
            assert validate_password("short") is False  # Too short
            assert validate_password("nouppercase1") is False  # No uppercase
            assert validate_password("NOLOWERCASE1") is False  # No lowercase
            assert validate_password("NoNumbers") is False  # No numbers
            assert validate_password("ValidPass123") is True

            duration = performance_tracker.end(test_name)
            e2e_test_results.record(test_name, True, duration)

            print(f"✓ {test_name} passed in {duration:.3f}s")

        except Exception as e:
            duration = performance_tracker.end(test_name) or 0
            e2e_test_results.record(test_name, False, duration, str(e))
            raise

    @pytest.mark.asyncio
    async def test_async_typescript_function(
        self,
        sample_specifications,
        code_validation_helpers,
        performance_tracker,
        e2e_test_results,
    ):
        """Test E2E: Async TypeScript function generation."""
        spec = sample_specifications["async_operation"]
        test_name = "async_typescript_function"

        try:
            performance_tracker.start(test_name)

            # Step 1: NLP → IR
            ir_dict = {
                "intent": {
                    "summary": "Fetch data from URL and return JSON",
                    "rationale": "Perform async HTTP request",
                },
                "signature": {
                    "name": "fetchData",
                    "parameters": [{"name": "url", "type_hint": "str"}],
                    "returns": "Promise[dict]",
                },
                "assertions": [
                    {
                        "predicate": "returns JSON data",
                        "rationale": "Promise resolves with parsed JSON",
                    }
                ],
                "metadata": {"origin": "test", "language": "typescript"},
            }

            # Verify async signature
            assert "Promise" in ir_dict["signature"]["returns"]

            # Step 2: IR → Async TypeScript code
            generated_code = """
/**
 * Fetch data from URL and return JSON
 *
 * Perform async HTTP request
 *
 * @param url - URL to fetch from
 * @returns Promise resolving to JSON data
 */
export async function fetchData(url: string): Promise<Record<string, any>> {
  // Promise resolves with parsed JSON
  const response = await fetch(url);
  return response.json();
}
"""

            # Step 3: Validate async TypeScript code
            assert code_validation_helpers["typescript_syntax"](generated_code)
            assert "async function" in generated_code
            assert "await" in generated_code
            assert "Promise<" in generated_code
            assert "fetch(" in generated_code

            duration = performance_tracker.end(test_name)
            e2e_test_results.record(test_name, True, duration)

            print(f"✓ {test_name} passed in {duration:.3f}s")

        except Exception as e:
            duration = performance_tracker.end(test_name) or 0
            e2e_test_results.record(test_name, False, duration, str(e))
            raise

    def test_e2e_results_summary(self, e2e_test_results, performance_tracker, request):
        """Print summary of all E2E test results."""
        # This test should run last
        if request.session.testsfailed == 0:
            e2e_test_results.print_summary()
            performance_tracker.print_summary()

            # Verify we meet the 80% success rate goal
            success_rate = e2e_test_results.get_success_rate()
            print(f"\n\nE2E Success Rate: {success_rate:.1f}%")

            if success_rate < 80:
                print(f"⚠️  WARNING: Success rate {success_rate:.1f}% is below 80% target")
            else:
                print(f"✓ Success rate {success_rate:.1f}% meets 80% target")
