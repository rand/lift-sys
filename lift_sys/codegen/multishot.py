"""Multi-shot generation with empirical test validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GenerationCandidate:
    """Represents a candidate implementation with test results."""

    code: str
    passed_tests: int
    total_tests: int
    errors: list[str]
    score: float  # Normalized 0-1 score

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0


class MultishotGenerator:
    """Generates multiple implementations and selects the best through testing."""

    def __init__(self, num_shots: int = 3, temperature_range: tuple[float, float] = (0.2, 0.5)):
        """
        Initialize multishot generator.

        Args:
            num_shots: Number of implementations to generate
            temperature_range: (min, max) temperature for generation diversity
        """
        self.num_shots = num_shots
        self.temperature_range = temperature_range

    async def generate_and_test(
        self,
        generator,  # XGrammarCodeGenerator instance
        ir,  # IntermediateRepresentation
        test_cases: list[tuple[tuple, Any]] | None = None,
    ) -> GenerationCandidate:
        """
        Generate multiple implementations and select the best.

        Args:
            generator: XGrammarCodeGenerator instance
            ir: Intermediate representation
            test_cases: Optional test cases [(inputs, expected_output), ...]

        Returns:
            Best performing candidate
        """
        candidates = []

        # Generate multiple candidates with varying temperatures
        temperatures = self._generate_temperatures()

        for _i, _temp in enumerate(temperatures):
            try:
                # Generate with specific temperature (temperature variation not yet implemented)
                # TODO: Pass temperature to generator when API supports it
                code_result = await generator.generate(ir, max_retries=1)

                # Test if test cases provided
                if test_cases:
                    test_result = self._run_tests(
                        code_result.source_code, ir.signature.name, test_cases
                    )
                    candidate = GenerationCandidate(
                        code=code_result.source_code,
                        passed_tests=test_result["passed"],
                        total_tests=test_result["total"],
                        errors=test_result["errors"],
                        score=test_result["passed"] / test_result["total"]
                        if test_result["total"] > 0
                        else 0.0,
                    )
                else:
                    # No tests, use validation only
                    candidate = GenerationCandidate(
                        code=code_result.source_code,
                        passed_tests=1,
                        total_tests=1,
                        errors=[],
                        score=1.0,  # Assume success if no tests
                    )

                candidates.append(candidate)

                # If we found a perfect implementation, return early
                if candidate.score == 1.0:
                    return candidate

            except Exception as e:
                # If generation fails, continue with next attempt
                candidates.append(
                    GenerationCandidate(
                        code="",
                        passed_tests=0,
                        total_tests=1,
                        errors=[str(e)],
                        score=0.0,
                    )
                )

        # Return best candidate
        if candidates:
            return max(candidates, key=lambda c: c.score)

        # Fallback: no successful generations
        return GenerationCandidate(
            code="",
            passed_tests=0,
            total_tests=1,
            errors=["All generation attempts failed"],
            score=0.0,
        )

    def _generate_temperatures(self) -> list[float]:
        """Generate temperature values for diversity."""
        min_temp, max_temp = self.temperature_range
        if self.num_shots == 1:
            return [(min_temp + max_temp) / 2]

        # Generate evenly spaced temperatures
        step = (max_temp - min_temp) / (self.num_shots - 1)
        return [min_temp + i * step for i in range(self.num_shots)]

    def _run_tests(
        self,
        code: str,
        function_name: str,
        test_cases: list[tuple[tuple, Any]],
    ) -> dict[str, Any]:
        """
        Execute test cases against generated code.

        Args:
            code: Generated Python code
            function_name: Name of function to test
            test_cases: List of (inputs, expected_output) tuples

        Returns:
            Dict with "passed", "total", "errors"
        """
        passed = 0
        errors = []

        try:
            # Execute code
            namespace = {}
            exec(code, namespace)

            # Find function
            func = namespace.get(function_name)
            if not func:
                # Try to find any callable
                for name, obj in namespace.items():
                    if callable(obj) and not name.startswith("_"):
                        func = obj
                        break

            if not func:
                return {
                    "passed": 0,
                    "total": len(test_cases),
                    "errors": [f"Function '{function_name}' not found"],
                }

            # Run test cases
            for inputs, expected in test_cases:
                try:
                    actual = func(*inputs)
                    if actual == expected:
                        passed += 1
                    else:
                        errors.append(f"Test failed: {inputs} -> expected {expected}, got {actual}")
                except Exception as e:
                    errors.append(f"Test error: {inputs} -> {str(e)}")

        except Exception as e:
            errors.append(f"Execution error: {str(e)}")

        return {
            "passed": passed,
            "total": len(test_cases),
            "errors": errors,
        }
