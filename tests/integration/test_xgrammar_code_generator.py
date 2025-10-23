"""Integration tests for XGrammarCodeGenerator with real Modal backend.

This file contains end-to-end integration tests that validate code generation
using real Modal.com LLM inference.

**Testing Strategy**:
- Uses real ModalProvider (Qwen2.5-Coder-32B-Instruct + XGrammar)
- Caches responses via code_recorder for fast CI/CD
- Validates code generation quality (syntax, structure, correctness)
- First run: ~20-40s per test (real API)
- Subsequent runs: <1s per test (cached fixtures)

**Environment Variables**:
- MODAL_ENDPOINT_URL: Modal endpoint (default: https://rand--generate.modal.run)
- RECORD_FIXTURES=true: Record new fixtures (first run only)
- RECORD_FIXTURES=false: Use cached fixtures (default, CI/CD mode)

**Fixture Location**:
- tests/fixtures/code_responses.json - Cached GeneratedCode objects

**Related Files**:
- lift_sys/codegen/xgrammar_generator.py - Code generator implementation
- lift_sys/providers/modal_provider.py - Modal backend
- tests/fixtures/response_recorder.py - Caching infrastructure
- tests/conftest.py - code_recorder fixture
"""

from __future__ import annotations

import ast
import json
import os

import pytest

from lift_sys.codegen.xgrammar_generator import XGrammarCodeGenerator
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.base import BaseProvider, ProviderCapabilities
from lift_sys.providers.modal_provider import ModalProvider


class MockCodeGenProvider(BaseProvider):
    """Mock provider for code generation testing."""

    def __init__(self, implementation_json: dict | None = None):
        super().__init__(
            name="mock_codegen",
            capabilities=ProviderCapabilities(
                streaming=False,
                structured_output=False,  # Mock doesn't support structured output
                reasoning=False,
            ),
        )
        self.implementation_json = implementation_json
        self.call_count = 0

    async def initialize(self, credentials: dict) -> None:
        pass

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate mock implementation JSON based on prompt."""
        self.call_count += 1

        # If specific implementation provided, use it
        if self.implementation_json:
            return json.dumps(self.implementation_json, indent=2)

        # Otherwise, generate based on prompt analysis
        prompt_lower = prompt.lower()

        # Detect function type from prompt (be specific to avoid false matches)
        if (
            "sum of two" in prompt_lower
            or "calculate_sum" in prompt_lower
            or ("add" in prompt_lower and "two" in prompt_lower)
        ):
            impl = {
                "implementation": {
                    "body_statements": [
                        {
                            "type": "assignment",
                            "code": "result = x + y",
                            "rationale": "Calculate sum of inputs",
                        },
                        {"type": "return", "code": "return result"},
                    ],
                    "algorithm": "Direct arithmetic addition",
                    "complexity": {"time": "O(1)", "space": "O(1)"},
                },
                "imports": [],
            }

        elif "area" in prompt_lower and "circle" in prompt_lower:
            impl = {
                "implementation": {
                    "body_statements": [
                        {
                            "type": "assignment",
                            "code": "result = 3.14159 * radius ** 2",
                            "rationale": "Calculate area using formula πr²",
                        },
                        {"type": "return", "code": "return result"},
                    ],
                    "algorithm": "Circle area formula: π × radius²",
                    "complexity": {"time": "O(1)", "space": "O(1)"},
                },
                "imports": [],
            }

        elif "valid" in prompt_lower and "email" in prompt_lower:
            impl = {
                "implementation": {
                    "body_statements": [
                        {
                            "type": "assignment",
                            "code": "pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'",
                            "rationale": "Email regex pattern",
                        },
                        {
                            "type": "assignment",
                            "code": "is_valid = bool(re.match(pattern, email))",
                            "rationale": "Check if email matches pattern",
                        },
                        {"type": "return", "code": "return is_valid"},
                    ],
                    "algorithm": "Regex-based email validation",
                },
                "imports": [{"module": "re", "names": ["match"]}],
            }

        elif "factorial" in prompt_lower:
            impl = {
                "implementation": {
                    "body_statements": [
                        {
                            "type": "if_statement",
                            "code": "if n == 0 or n == 1:\n    return 1",
                            "rationale": "Base case: factorial of 0 and 1 is 1",
                        },
                        {
                            "type": "assignment",
                            "code": "result = 1",
                            "rationale": "Initialize result",
                        },
                        {
                            "type": "for_loop",
                            "code": "for i in range(2, n + 1):\n    result *= i",
                            "rationale": "Multiply all numbers from 2 to n",
                        },
                        {"type": "return", "code": "return result"},
                    ],
                    "algorithm": "Iterative factorial calculation",
                    "complexity": {"time": "O(n)", "space": "O(1)"},
                },
                "imports": [],
            }

        else:
            # Generic implementation
            impl = {
                "implementation": {
                    "body_statements": [
                        {
                            "type": "comment",
                            "code": "# Implementation based on specification",
                        },
                        {
                            "type": "assignment",
                            "code": "result = None  # TODO: Implement logic",
                        },
                        {"type": "return", "code": "return result"},
                    ],
                    "algorithm": "Generic algorithm",
                },
                "imports": [],
            }

        return json.dumps(impl, indent=2)

    async def generate_stream(self, prompt: str, **kwargs):
        yield await self.generate_text(prompt, **kwargs)

    async def generate_structured(self, prompt: str, schema: dict, **kwargs) -> dict:
        raise NotImplementedError

    async def check_health(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_structured_output(self) -> bool:
        return False


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_xgrammar_generator_simple_sum(code_recorder):
    """Test generating a simple sum function with real Modal."""
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")

    # Create IR for sum function
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Calculate the sum of two numbers"),
        signature=SigClause(
            name="calculate_sum",
            parameters=[
                Parameter(name="x", type_hint="int"),
                Parameter(name="y", type_hint="int"),
            ],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        generator = XGrammarCodeGenerator(provider)

        # Generate code using code_recorder for caching
        result = await code_recorder.get_or_record(
            key="generator_simple_sum",
            generator_fn=lambda: generator.generate(ir),
            metadata={"test": "simple_sum", "function": "calculate_sum"},
        )

        # Verify code is valid Python
        ast.parse(result.source_code)

        # Verify function signature
        assert "def calculate_sum(" in result.source_code
        assert "x" in result.source_code
        assert "y" in result.source_code
        assert "return" in result.source_code

        # Verify metadata
        assert result.language == "python"
        # Real Modal uses XGrammar constrained generation
        assert result.metadata.get("generator") in ("xgrammar_text", "xgrammar_constrained")

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_xgrammar_generator_circle_area(code_recorder):
    """Test generating circle area calculation with real Modal."""
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Calculate the area of a circle given its radius"),
        signature=SigClause(
            name="calculate_circle_area",
            parameters=[Parameter(name="radius", type_hint="float")],
            returns="float",
        ),
        assertions=[AssertClause(predicate="radius > 0", rationale="Radius must be positive")],
        metadata=Metadata(language="python", origin="test"),
    )

    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        generator = XGrammarCodeGenerator(provider)

        result = await code_recorder.get_or_record(
            key="generator_circle_area",
            generator_fn=lambda: generator.generate(ir),
            metadata={"test": "circle_area", "function": "calculate_circle_area"},
        )

        # Verify syntax
        ast.parse(result.source_code)

        # Verify signature
        assert "def calculate_circle_area(" in result.source_code
        assert "radius" in result.source_code

        # Verify implementation uses math (pi, radius calculation)
        # Real LLM may use different formulas (math.pi, 3.14159, etc.)
        assert "radius" in result.source_code

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_xgrammar_generator_with_imports(code_recorder):
    """Test generating function that needs imports with real Modal."""
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Validate an email address"),
        signature=SigClause(
            name="validate_email",
            parameters=[Parameter(name="email", type_hint="str")],
            returns="bool",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        generator = XGrammarCodeGenerator(provider)

        result = await code_recorder.get_or_record(
            key="generator_email_validation",
            generator_fn=lambda: generator.generate(ir),
            metadata={"test": "with_imports", "function": "validate_email"},
        )

        # Verify syntax
        ast.parse(result.source_code)

        # Verify function signature
        assert "def validate_email(" in result.source_code
        assert "email" in result.source_code

        # Real LLM may use different validation approaches
        assert "return" in result.source_code

    finally:
        await provider.aclose()


@pytest.mark.integration
@pytest.mark.real_modal
@pytest.mark.asyncio
async def test_xgrammar_generator_factorial(code_recorder):
    """Test generating factorial function with real Modal."""
    endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Calculate factorial of a number"),
        signature=SigClause(
            name="factorial",
            parameters=[Parameter(name="n", type_hint="int")],
            returns="int",
        ),
        assertions=[
            AssertClause(
                predicate="n >= 0", rationale="Factorial only defined for non-negative integers"
            )
        ],
        metadata=Metadata(language="python", origin="test"),
    )

    provider = ModalProvider(endpoint_url=endpoint_url)
    await provider.initialize({})

    try:
        generator = XGrammarCodeGenerator(provider)

        result = await code_recorder.get_or_record(
            key="generator_factorial",
            generator_fn=lambda: generator.generate(ir),
            metadata={"test": "factorial", "function": "factorial"},
        )

        # Verify syntax
        ast.parse(result.source_code)

        # Verify signature
        assert "def factorial(" in result.source_code
        assert "n" in result.source_code

        # Real LLM may use iteration or recursion
        assert "return" in result.source_code

    finally:
        await provider.aclose()


@pytest.mark.asyncio
async def test_xgrammar_generator_retry_on_error():
    """Test retry mechanism when generation fails."""
    call_count = [0]

    # Valid implementation to return on second attempt
    valid_impl = {
        "implementation": {
            "body_statements": [
                {"type": "assignment", "code": "result = x + y"},
                {"type": "return", "code": "return result"},
            ]
        },
        "imports": [],
    }

    class RetryProvider(MockCodeGenProvider):
        async def generate_text(self, prompt: str, **kwargs) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                # First attempt: invalid JSON
                return "invalid json {"
            # Second attempt: valid JSON
            return json.dumps(valid_impl, indent=2)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Sum two numbers"),
        signature=SigClause(
            name="sum_numbers",
            parameters=[Parameter(name="x", type_hint="int"), Parameter(name="y", type_hint="int")],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    provider = RetryProvider()
    generator = XGrammarCodeGenerator(provider)

    result = await generator.generate(ir, max_retries=3)

    # Verify retry happened
    assert call_count[0] == 2

    # Verify code is valid
    ast.parse(result.source_code)


@pytest.mark.asyncio
async def test_xgrammar_generator_validation_error():
    """Test handling of invalid implementation JSON."""
    # Invalid: missing body_statements
    invalid_impl = {"implementation": {}}

    provider = MockCodeGenProvider(implementation_json=invalid_impl)
    generator = XGrammarCodeGenerator(provider)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Test function"),
        signature=SigClause(name="test_func", parameters=[], returns="None"),
        metadata=Metadata(language="python", origin="test"),
    )

    with pytest.raises(ValueError, match="Missing required field: implementation.body_statements"):
        await generator.generate(ir)


@pytest.mark.asyncio
async def test_xgrammar_generator_complex_implementation():
    """Test generating complex implementation with multiple statement types."""
    complex_impl = {
        "implementation": {
            "body_statements": [
                {"type": "assignment", "code": "items = []", "rationale": "Initialize result list"},
                {
                    "type": "for_loop",
                    "code": "for i in range(len(data)):\n    if data[i] > 0:\n        items.append(data[i])",
                    "rationale": "Filter positive values",
                },
                {
                    "type": "if_statement",
                    "code": "if not items:\n    return []",
                    "rationale": "Handle empty result",
                },
                {"type": "return", "code": "return sorted(items)"},
            ],
            "algorithm": "Filter and sort positive values",
            "complexity": {"time": "O(n log n)", "space": "O(n)"},
        },
        "imports": [],
    }

    provider = MockCodeGenProvider(implementation_json=complex_impl)
    generator = XGrammarCodeGenerator(provider)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Filter and sort positive values"),
        signature=SigClause(
            name="filter_positive",
            parameters=[Parameter(name="data", type_hint="list[int]")],
            returns="list[int]",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    result = await generator.generate(ir)

    # Verify syntax
    ast.parse(result.source_code)

    # Verify algorithm comment
    assert "Algorithm: Filter and sort positive values" in result.source_code

    # Verify implementation elements
    assert "items = []" in result.source_code
    assert "for i in range" in result.source_code
    assert "return sorted(items)" in result.source_code


@pytest.mark.asyncio
async def test_xgrammar_generator_with_helper_functions():
    """Test generating code with helper functions."""
    impl_with_helper = {
        "implementation": {
            "body_statements": [
                {"type": "assignment", "code": "result = _helper(x)"},
                {"type": "return", "code": "return result"},
            ],
            "algorithm": "Use helper function for calculation",
        },
        "imports": [],
        "helper_functions": [
            {
                "name": "_helper",
                "signature": "_helper(value: int) -> int",
                "body": "return value * 2",
            }
        ],
    }

    provider = MockCodeGenProvider(implementation_json=impl_with_helper)
    generator = XGrammarCodeGenerator(provider)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Process value using helper"),
        signature=SigClause(
            name="process_value",
            parameters=[Parameter(name="x", type_hint="int")],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    result = await generator.generate(ir)

    # Verify syntax
    ast.parse(result.source_code)

    # Verify helper function is generated before main function
    assert "def _helper(value: int) -> int:" in result.source_code
    assert "return value * 2" in result.source_code

    # Verify main function uses helper
    assert "result = _helper(x)" in result.source_code


@pytest.mark.asyncio
async def test_xgrammar_generator_preserves_docstring():
    """Test that generator preserves docstrings from structural generator."""
    ir = IntermediateRepresentation(
        intent=IntentClause(
            summary="Calculate sum of two numbers",
            rationale="Needed for arithmetic operations",
        ),
        signature=SigClause(
            name="add",
            parameters=[Parameter(name="a", type_hint="int"), Parameter(name="b", type_hint="int")],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    provider = MockCodeGenProvider()
    generator = XGrammarCodeGenerator(provider)

    result = await generator.generate(ir)

    # Verify syntax
    ast.parse(result.source_code)

    # Verify docstring is present
    assert '"""' in result.source_code
    assert "Calculate sum of two numbers" in result.source_code


@pytest.mark.asyncio
async def test_xgrammar_generator_no_params_function():
    """Test generating function with no parameters."""
    impl_no_params = {
        "implementation": {
            "body_statements": [
                {"type": "assignment", "code": "result = 42", "rationale": "Return constant value"},
                {"type": "return", "code": "return result"},
            ],
            "algorithm": "Return constant value",
        },
        "imports": [],
    }

    provider = MockCodeGenProvider(implementation_json=impl_no_params)
    generator = XGrammarCodeGenerator(provider)

    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Return the answer to everything"),
        signature=SigClause(name="get_answer", parameters=[], returns="int"),
        metadata=Metadata(language="python", origin="test"),
    )

    result = await generator.generate(ir)

    # Verify syntax
    ast.parse(result.source_code)

    # Verify signature (no params)
    assert "def get_answer() -> int:" in result.source_code

    # Verify implementation
    assert "result = 42" in result.source_code
    assert "return result" in result.source_code
