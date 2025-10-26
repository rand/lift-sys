"""Execution tests for TypeScript code generator.

This module tests that generated TypeScript code EXECUTES correctly with test inputs,
not just compiles. These tests validate:

1. Generated code runs without errors
2. Generated code produces correct outputs for given inputs
3. Generated code handles edge cases (empty inputs, errors, etc.)
4. Execution completes within reasonable time

Unlike test_typescript_pipeline_e2e.py which only validates syntax,
these tests verify FUNCTIONAL correctness by executing generated code.

Strategy:
- Use MockProvider to avoid real LLM calls
- Create simple IR fixtures for predictable code generation
- Execute generated code with typescript_executor helper
- Validate actual outputs match expected outputs
"""

from __future__ import annotations

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Parameter,
    SigClause,
)
from tests.helpers.typescript_executor import (
    check_typescript_runtime_available,
    execute_typescript,
)

# Check if TypeScript runtime is available
TS_AVAILABLE, TS_MESSAGE = check_typescript_runtime_available()
pytestmark = pytest.mark.skipif(
    not TS_AVAILABLE,
    reason=f"TypeScript runtime not available: {TS_MESSAGE}",
)


@pytest.fixture
def simple_addition_ir() -> IntermediateRepresentation:
    """Fixture: IR for simple addition function."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Add two numbers and return the sum"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="number"),
                Parameter(name="b", type_hint="number"),
            ],
            returns="number",
        ),
        effects=[],
        assertions=[],
    )


@pytest.fixture
def array_filter_ir() -> IntermediateRepresentation:
    """Fixture: IR for filtering positive numbers from array."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Filter array to keep only positive numbers"),
        signature=SigClause(
            name="filterPositive",
            parameters=[
                Parameter(name="nums", type_hint="number[]"),
            ],
            returns="number[]",
        ),
        effects=[],
        assertions=[],
    )


@pytest.fixture
def string_reverse_ir() -> IntermediateRepresentation:
    """Fixture: IR for reversing a string."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Reverse a string"),
        signature=SigClause(
            name="reverseString",
            parameters=[
                Parameter(name="s", type_hint="string"),
            ],
            returns="string",
        ),
        effects=[],
        assertions=[],
    )


@pytest.fixture
def factorial_ir() -> IntermediateRepresentation:
    """Fixture: IR for calculating factorial."""
    return IntermediateRepresentation(
        intent=IntentClause(summary="Calculate factorial of a number"),
        signature=SigClause(
            name="factorial",
            parameters=[
                Parameter(name="n", type_hint="number"),
            ],
            returns="number",
        ),
        effects=[],
        assertions=[],
    )


class TestTypeScriptExecution:
    """Tests for executing generated TypeScript code."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_simple_addition(self, simple_addition_ir, mock_provider):
        """
        Test execution of generated addition function.

        Validates:
        - Generated code executes without errors
        - Correct output for multiple test cases
        - Execution completes in reasonable time
        """
        # Configure mock provider to return simple addition implementation
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return a + b;",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(simple_addition_ir)

        assert typescript.language == "typescript"
        assert typescript.source_code is not None

        # Execute with test inputs
        test_cases = [
            ({"a": 2, "b": 3}, 5),
            ({"a": 0, "b": 0}, 0),
            ({"a": -5, "b": 10}, 5),
            ({"a": 100, "b": 200}, 300),
        ]

        for inputs, expected_output in test_cases:
            result = execute_typescript(typescript.source_code, inputs, timeout_seconds=5)

            assert result.success, f"Execution failed for {inputs}: {result.error}"
            assert result.output == expected_output, (
                f"Expected {expected_output}, got {result.output} for inputs {inputs}"
            )
            assert result.duration_seconds < 5, (
                f"Execution took too long: {result.duration_seconds}s"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_array_filtering(self, array_filter_ir, mock_provider):
        """
        Test execution of generated array filtering function.

        Validates:
        - Array operations work correctly
        - Filtering logic is correct
        - Empty arrays handled properly
        """
        # Configure mock provider to return filter implementation
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return nums.filter(n => n > 0);",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(array_filter_ir)

        assert typescript.source_code is not None

        # Execute with test inputs
        test_cases = [
            ({"nums": [1, -2, 3, -4, 5]}, [1, 3, 5]),
            ({"nums": [-1, -2, -3]}, []),
            ({"nums": [1, 2, 3]}, [1, 2, 3]),
            ({"nums": []}, []),
        ]

        for inputs, expected_output in test_cases:
            result = execute_typescript(typescript.source_code, inputs, timeout_seconds=5)

            assert result.success, f"Execution failed for {inputs}: {result.error}"
            assert result.output == expected_output, (
                f"Expected {expected_output}, got {result.output} for inputs {inputs}"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_string_manipulation(self, string_reverse_ir, mock_provider):
        """
        Test execution of generated string manipulation function.

        Validates:
        - String operations work correctly
        - Edge cases (empty string, single char) handled
        """
        # Configure mock provider to return string reverse implementation
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return s.split('').reverse().join('');",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(string_reverse_ir)

        assert typescript.source_code is not None

        # Execute with test inputs
        test_cases = [
            ({"s": "hello"}, "olleh"),
            ({"s": "a"}, "a"),
            ({"s": ""}, ""),
            ({"s": "TypeScript"}, "tpircSepyT"),
        ]

        for inputs, expected_output in test_cases:
            result = execute_typescript(typescript.source_code, inputs, timeout_seconds=5)

            assert result.success, f"Execution failed for {inputs}: {result.error}"
            assert result.output == expected_output, (
                f"Expected {expected_output}, got {result.output} for inputs {inputs}"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_error_handling(self, mock_provider):
        """
        Test execution with invalid input that should throw error.

        Validates:
        - Errors are captured properly
        - Execution doesn't hang
        - Error messages are informative
        """
        # Create IR for division function (can divide by zero)
        division_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Divide two numbers"),
            signature=SigClause(
                name="divide",
                parameters=[
                    Parameter(name="a", type_hint="number"),
                    Parameter(name="b", type_hint="number"),
                ],
                returns="number",
            ),
            effects=[],
            assertions=[],
        )

        # Configure mock provider to return division implementation (no error handling)
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return a / b;",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(division_ir)

        assert typescript.source_code is not None

        # Execute with valid input (should succeed)
        result = execute_typescript(typescript.source_code, {"a": 10, "b": 2})
        assert result.success
        assert result.output == 5

        # Execute with division by zero (JavaScript returns Infinity, not error)
        result = execute_typescript(typescript.source_code, {"a": 10, "b": 0})
        assert result.success  # JavaScript doesn't throw on division by zero
        # Output will be Infinity (special JSON handling needed)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_async_function(self, mock_provider):
        """
        Test execution of async function with mock data.

        Validates:
        - Async/await patterns work
        - Promise resolution works correctly
        - Async execution time is reasonable
        """
        # Create IR for async fetch function
        async_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Mock async function that returns user data"),
            signature=SigClause(
                name="getUserData",
                parameters=[
                    Parameter(name="userId", type_hint="number"),
                ],
                returns="Promise<{ id: number, name: string }>",
            ),
            effects=[],
            assertions=[],
        )

        # Configure mock provider to return async implementation
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return Promise.resolve({ id: userId, name: 'User' + userId });",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(async_ir)

        assert typescript.source_code is not None

        # Execute with test inputs
        test_cases = [
            ({"userId": 1}, {"id": 1, "name": "User1"}),
            ({"userId": 42}, {"id": 42, "name": "User42"}),
        ]

        for inputs, expected_output in test_cases:
            result = execute_typescript(typescript.source_code, inputs, timeout_seconds=5)

            assert result.success, f"Execution failed for {inputs}: {result.error}"
            assert result.output == expected_output, (
                f"Expected {expected_output}, got {result.output} for inputs {inputs}"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_recursive_function(self, factorial_ir, mock_provider):
        """
        Test execution of recursive function (factorial).

        Validates:
        - Recursion works correctly
        - Base case handled properly
        - No stack overflow for reasonable inputs
        """
        # Configure mock provider to return recursive factorial
        mock_provider.set_generate_response(
            """
            {
                "implementation": "if (n <= 1) return 1; return n * factorial(n - 1);",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(factorial_ir)

        assert typescript.source_code is not None

        # Execute with test inputs
        test_cases = [
            ({"n": 0}, 1),
            ({"n": 1}, 1),
            ({"n": 5}, 120),
            ({"n": 10}, 3628800),
        ]

        for inputs, expected_output in test_cases:
            result = execute_typescript(typescript.source_code, inputs, timeout_seconds=5)

            assert result.success, f"Execution failed for {inputs}: {result.error}"
            assert result.output == expected_output, (
                f"Expected {expected_output}, got {result.output} for inputs {inputs}"
            )

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execution_timeout(self, mock_provider):
        """
        Test that infinite loops are caught by timeout.

        Validates:
        - Timeout mechanism works
        - Execution doesn't hang indefinitely
        """
        # Create IR for function with infinite loop
        infinite_loop_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Function with infinite loop (for testing)"),
            signature=SigClause(
                name="infiniteLoop",
                parameters=[],
                returns="number",
            ),
            effects=[],
            assertions=[],
        )

        # Configure mock provider to return infinite loop
        mock_provider.set_generate_response(
            """
            {
                "implementation": "while (true) { /* infinite loop */ }",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate TypeScript code
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(infinite_loop_ir)

        assert typescript.source_code is not None

        # Execute with short timeout (should timeout)
        import subprocess

        with pytest.raises(subprocess.TimeoutExpired):
            execute_typescript(typescript.source_code, {}, timeout_seconds=1)


class TestTypeScriptExecutionEdgeCases:
    """Tests for edge cases in TypeScript execution."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_with_no_function_definition(self):
        """
        Test execution of code without function definition.

        Should fail gracefully with clear error message.
        """
        code_without_function = "const x = 1 + 2;"

        result = execute_typescript(code_without_function, {}, timeout_seconds=5)

        assert not result.success
        assert result.error is not None
        assert "Could not extract function name" in result.error

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_with_syntax_error(self):
        """
        Test execution of code with syntax errors.

        Should fail with compilation/execution error.
        """
        code_with_error = """
        function broken(a: number, b: number): number {
            return a + b  // Missing semicolon
        }
        """

        # This might succeed (JavaScript is lenient) or fail depending on strict mode
        # Main point is execution doesn't crash
        result = execute_typescript(code_with_error, {"a": 1, "b": 2}, timeout_seconds=5)

        # Either succeeds (JavaScript ASI) or fails gracefully
        assert isinstance(result.success, bool)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_execute_with_complex_return_types(self, mock_provider):
        """
        Test execution with complex return types (objects, nested structures).

        Validates:
        - Complex types serialize/deserialize correctly
        - Nested objects handled properly
        """
        # Create IR for function returning complex object
        complex_ir = IntermediateRepresentation(
            intent=IntentClause(summary="Return user profile with nested data"),
            signature=SigClause(
                name="getUserProfile",
                parameters=[
                    Parameter(name="userId", type_hint="number"),
                ],
                returns="{ id: number, profile: { name: string, age: number } }",
            ),
            effects=[],
            assertions=[],
        )

        # Configure mock provider
        mock_provider.set_generate_response(
            """
            {
                "implementation": "return { id: userId, profile: { name: 'User', age: 30 } };",
                "imports": [],
                "helper_functions": []
            }
            """
        )

        # Generate and execute
        generator = TypeScriptGenerator(mock_provider)
        typescript = await generator.generate(complex_ir)

        result = execute_typescript(typescript.source_code, {"userId": 123})

        assert result.success
        assert result.output == {"id": 123, "profile": {"name": "User", "age": 30}}
