"""
Execution Validator - Execute generated code with test cases and validate results.

Safely executes generated Python code with test cases to validate correctness.
Provides detailed error messages for regeneration feedback.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass
from typing import Any

from lift_sys.codegen.test_generator import TestCase


@dataclass
class FailedTest:
    """A test case that failed during execution."""

    test_case: TestCase
    """The test case that failed"""

    actual_output: Any | None
    """The actual output from the function"""

    error_message: str
    """Description of what went wrong"""

    exception: Exception | None = None
    """Exception raised, if any"""


@dataclass
class ValidationResult:
    """Result of code execution validation."""

    passed: bool
    """Whether all tests passed"""

    failed_tests: list[FailedTest]
    """List of tests that failed"""

    total_tests: int
    """Total number of tests run"""

    error_summary: str | None = None
    """Summary of errors for regeneration feedback"""


class ExecutionValidator:
    """Execute generated code with test cases and validate results."""

    def __init__(self, timeout_seconds: float = 1.0):
        """
        Initialize validator.

        Args:
            timeout_seconds: Maximum time per test case execution
        """
        self.timeout_seconds = timeout_seconds

    def validate(
        self, code: str, function_name: str, test_cases: list[TestCase]
    ) -> ValidationResult:
        """
        Execute code with test cases and validate results.

        Args:
            code: Python code to execute
            function_name: Name of the function to test
            test_cases: Test cases to run

        Returns:
            ValidationResult with pass/fail status and details
        """
        if not test_cases:
            return ValidationResult(
                passed=True,
                failed_tests=[],
                total_tests=0,
                error_summary=None,
            )

        # Execute code and get function
        func = self._execute_code(code, function_name)

        if func is None:
            # Code failed to execute
            return ValidationResult(
                passed=False,
                failed_tests=[],
                total_tests=len(test_cases),
                error_summary=f"Code failed to execute: function '{function_name}' not found",
            )

        # Run test cases
        failed_tests: list[FailedTest] = []

        for test_case in test_cases:
            try:
                # Execute with timeout
                actual = self._execute_with_timeout(func, test_case.inputs)

                # Check if test passed
                if test_case.should_raise is not None:
                    # Expected an exception but got a result
                    failed_tests.append(
                        FailedTest(
                            test_case=test_case,
                            actual_output=actual,
                            error_message=f"Expected {test_case.should_raise.__name__} to be raised, "
                            f"but got result: {actual}",
                        )
                    )
                elif test_case.expected_output is not None:
                    # Check if output matches expected
                    if actual != test_case.expected_output:
                        failed_tests.append(
                            FailedTest(
                                test_case=test_case,
                                actual_output=actual,
                                error_message=f"Expected {test_case.expected_output!r}, "
                                f"got {actual!r}",
                            )
                        )
                # else: test_case.expected_output is None (assertion-only test)
                # We just check it doesn't crash

            except TimeoutError:
                failed_tests.append(
                    FailedTest(
                        test_case=test_case,
                        actual_output=None,
                        error_message=f"Test timed out after {self.timeout_seconds}s "
                        f"(infinite loop or too slow?)",
                    )
                )

            except Exception as e:
                # Check if this exception was expected
                if test_case.should_raise is not None and isinstance(e, test_case.should_raise):
                    # Expected exception - test passed
                    continue
                else:
                    # Unexpected exception
                    failed_tests.append(
                        FailedTest(
                            test_case=test_case,
                            actual_output=None,
                            error_message=f"Unexpected error: {type(e).__name__}: {e}",
                            exception=e,
                        )
                    )

        # Create summary for regeneration
        error_summary = None
        if failed_tests:
            error_summary = self._create_error_summary(failed_tests)

        return ValidationResult(
            passed=len(failed_tests) == 0,
            failed_tests=failed_tests,
            total_tests=len(test_cases),
            error_summary=error_summary,
        )

    def _execute_code(self, code: str, function_name: str) -> Any | None:
        """
        Execute code and return the function object.

        Args:
            code: Python code to execute
            function_name: Name of function to extract

        Returns:
            Function object, or None if execution failed
        """
        try:
            # Create restricted execution environment
            # Only allow safe builtins
            safe_globals = {
                "__builtins__": {
                    # Basic types
                    "int": int,
                    "float": float,
                    "str": str,
                    "bool": bool,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "set": set,
                    # Basic functions
                    "len": len,
                    "range": range,
                    "enumerate": enumerate,
                    "zip": zip,
                    "sum": sum,
                    "min": min,
                    "max": max,
                    "abs": abs,
                    "round": round,
                    "sorted": sorted,
                    "reversed": reversed,
                    "any": any,
                    "all": all,
                    # String/type operations
                    "isinstance": isinstance,
                    "type": type,
                    "hasattr": hasattr,
                    "getattr": getattr,
                    # Exceptions
                    "Exception": Exception,
                    "ValueError": ValueError,
                    "TypeError": TypeError,
                    "KeyError": KeyError,
                    "IndexError": IndexError,
                    "AttributeError": AttributeError,
                }
            }

            local_vars = {}

            # Execute code
            exec(code, safe_globals, local_vars)

            # Get the function
            if function_name in local_vars:
                return local_vars[function_name]
            else:
                # Function not found - might have different name
                # Try to find it by checking what was defined
                for name, obj in local_vars.items():
                    if callable(obj) and not name.startswith("_"):
                        # Found a function, use it
                        return obj

                return None

        except Exception as e:
            print(f"Failed to execute code: {e}")
            return None

    def _execute_with_timeout(self, func: Any, inputs: dict[str, Any]) -> Any:
        """
        Execute function with timeout.

        Args:
            func: Function to execute
            inputs: Input arguments

        Returns:
            Function output

        Raises:
            TimeoutError: If execution exceeds timeout
            Exception: Any exception raised by the function
        """

        def timeout_handler(signum, frame):
            raise TimeoutError("Function execution timed out")

        # Set up timeout (Unix-like systems only)
        # For Windows compatibility, we'd need a different approach
        try:
            # Try to set signal alarm (Unix)
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(self.timeout_seconds))

            try:
                result = func(**inputs)
                signal.alarm(0)  # Cancel alarm
                return result
            except Exception as e:
                signal.alarm(0)  # Cancel alarm
                raise

        except AttributeError:
            # Windows doesn't have SIGALRM
            # Fall back to no timeout (not ideal, but works for testing)
            return func(**inputs)

    def _create_error_summary(self, failed_tests: list[FailedTest]) -> str:
        """
        Create error summary for regeneration feedback.

        Args:
            failed_tests: List of failed tests

        Returns:
            Error summary string
        """
        lines = [f"Code validation failed: {len(failed_tests)} test(s) failed\n"]

        # Group failures by type
        missing_returns = []
        wrong_outputs = []
        exceptions = []
        timeouts = []

        for failed in failed_tests:
            if "timed out" in failed.error_message:
                timeouts.append(failed)
            elif failed.actual_output is None and failed.exception is None:
                # Likely missing return
                missing_returns.append(failed)
            elif failed.exception is not None:
                exceptions.append(failed)
            else:
                wrong_outputs.append(failed)

        # Add specific guidance based on failure types
        if missing_returns:
            lines.append("\n⚠️  MISSING RETURN STATEMENTS:")
            for failed in missing_returns[:2]:  # Show first 2
                lines.append(f"  • Input: {failed.test_case.inputs}")
                lines.append(f"    Expected: {failed.test_case.expected_output}")
                lines.append("    Got: None (function didn't return anything)")
            lines.append("\n  💡 Suggestion: Add 'return' statement to return the result")

        if wrong_outputs:
            lines.append("\n⚠️  INCORRECT OUTPUTS:")
            for failed in wrong_outputs[:2]:  # Show first 2
                lines.append(f"  • {failed.test_case.description}")
                lines.append(f"    Input: {failed.test_case.inputs}")
                lines.append(f"    Expected: {failed.test_case.expected_output}")
                lines.append(f"    Got: {failed.actual_output}")

            # Detect specific patterns
            if any("FIRST" in str(f.test_case.description) for f in wrong_outputs):
                lines.append(
                    "\n  💡 Suggestion: When finding FIRST occurrence, "
                    "return immediately when found (don't continue loop)"
                )

            if any("email" in str(f.test_case.description).lower() for f in wrong_outputs):
                lines.append(
                    "\n  💡 Suggestion: Email validation must check that dot comes AFTER @ symbol"
                )

        if exceptions:
            lines.append("\n⚠️  UNEXPECTED ERRORS:")
            for failed in exceptions[:2]:
                lines.append(f"  • {failed.error_message}")
            lines.append("\n  💡 Suggestion: Add error handling or check input validity")

        if timeouts:
            lines.append("\n⚠️  TIMEOUTS:")
            lines.append(f"  • {len(timeouts)} test(s) timed out")
            lines.append("\n  💡 Suggestion: Check for infinite loops or missing break statements")

        return "\n".join(lines)
