"""End-to-end tests for TypeScript code generation.

This module tests the complete TypeScript generation pipeline from IR to
executable TypeScript code, including LSP context integration.

**Phase 2 Migration Status**: First 3 tests migrated to real Modal with fixture caching
- test_simple_arithmetic_function: ✅ Migrated
- test_async_function_with_promise: ✅ Migrated
- test_function_with_imports: ✅ Migrated
- test_function_with_variables: MockProvider (original)
- test_generation_with_lsp_context: MockProvider (original)
- test_complex_function_with_multiple_features: MockProvider (original)
"""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.ir.models import (
    AssertClause,
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.mock import MockProvider
from lift_sys.providers.modal_provider import ModalProvider


class TestTypeScriptE2E:
    """End-to-end tests for TypeScript generation."""

    @pytest.mark.integration
    @pytest.mark.real_modal
    @pytest.mark.asyncio
    async def test_simple_arithmetic_function(self, code_recorder):
        """Test generating a simple arithmetic function.

        Uses real Modal LLM for TypeScript code generation.
        Cached via code_recorder for fast CI runs.
        """
        # Create IR for addition function
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Add two numbers together",
                rationale="Perform basic arithmetic addition",
            ),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(
                    predicate="result == a + b",
                    rationale="Sum must equal the addition of inputs",
                )
            ],
            metadata=Metadata(origin="test", language="typescript"),
        )

        # Set up real Modal provider
        endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
        provider = ModalProvider(endpoint_url=endpoint_url)
        await provider.initialize({})

        try:
            # Generate TypeScript code (cached via code_recorder)
            generator = TypeScriptGenerator(provider)
            result = await code_recorder.get_or_record(
                key="typescript_simple_add_function",
                generator_fn=lambda: generator.generate(ir),
                metadata={
                    "test": "typescript_e2e",
                    "function": "add",
                    "language": "typescript",
                },
            )

            # Verify result
            assert result.language == "typescript"
            assert result.source_code is not None

            # Verify structure
            code = result.source_code
            assert "export function add" in code or "function add" in code
            assert "number" in code  # TypeScript type annotation
            assert "return" in code
            assert "a" in code and "b" in code

            # Verify TSDoc (may vary with LLM)
            assert "/**" in code or "//" in code  # Some form of documentation

        finally:
            await provider.aclose()

    @pytest.mark.integration
    @pytest.mark.real_modal
    @pytest.mark.asyncio
    async def test_async_function_with_promise(self, code_recorder):
        """Test generating an async function that returns a Promise.

        Uses real Modal LLM for TypeScript async/Promise code generation.
        Cached via code_recorder for fast CI runs.
        """
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Fetch user data from an API",
                rationale="Retrieve user information asynchronously",
            ),
            signature=SigClause(
                name="fetchUser",
                parameters=[Parameter(name="userId", type_hint="str")],
                returns="Promise[dict]",
            ),
            assertions=[],
            metadata=Metadata(origin="test", language="typescript"),
        )

        # Set up real Modal provider
        endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
        provider = ModalProvider(endpoint_url=endpoint_url)
        await provider.initialize({})

        try:
            # Generate TypeScript code (cached via code_recorder)
            generator = TypeScriptGenerator(provider)
            result = await code_recorder.get_or_record(
                key="typescript_async_fetch_user",
                generator_fn=lambda: generator.generate(ir),
                metadata={
                    "test": "typescript_e2e",
                    "function": "fetchUser",
                    "language": "typescript",
                    "feature": "async_promise",
                },
            )

            # Verify result
            code = result.source_code
            assert code is not None
            assert "fetchUser" in code
            assert "string" in code  # userId type
            # Promise might be in return type or function body
            assert "Promise" in code or "async" in code

        finally:
            await provider.aclose()

    @pytest.mark.integration
    @pytest.mark.real_modal
    @pytest.mark.asyncio
    async def test_function_with_imports(self, code_recorder):
        """Test generating a function with external imports (syntax check only).

        Uses real Modal LLM for TypeScript string manipulation code generation.
        Cached via code_recorder for fast CI runs.
        """
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Concatenate two strings with a separator",
                rationale="Join strings using a separator",
            ),
            signature=SigClause(
                name="joinStrings",
                parameters=[
                    Parameter(name="a", type_hint="str"),
                    Parameter(name="b", type_hint="str"),
                    Parameter(name="separator", type_hint="str"),
                ],
                returns="str",
            ),
            assertions=[],
            metadata=Metadata(origin="test", language="typescript"),
        )

        # Set up real Modal provider
        endpoint_url = os.getenv("MODAL_ENDPOINT_URL", "https://rand--generate.modal.run")
        provider = ModalProvider(endpoint_url=endpoint_url)
        await provider.initialize({})

        try:
            # Generate TypeScript code (cached via code_recorder)
            generator = TypeScriptGenerator(provider)
            result = await code_recorder.get_or_record(
                key="typescript_join_strings",
                generator_fn=lambda: generator.generate(ir),
                metadata={
                    "test": "typescript_e2e",
                    "function": "joinStrings",
                    "language": "typescript",
                    "feature": "string_manipulation",
                },
            )

            # Verify function structure
            code = result.source_code
            assert code is not None
            assert "joinStrings" in code
            assert "string" in code  # TypeScript string type
            # Should have all three parameters
            assert "a" in code and "b" in code and "separator" in code

        finally:
            await provider.aclose()

    @pytest.mark.asyncio
    async def test_function_with_variables(self):
        """Test generating a function with local variable declarations."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Calculate the area of a rectangle",
                rationale="Multiply width by height",
            ),
            signature=SigClause(
                name="calculateArea",
                parameters=[
                    Parameter(name="width", type_hint="float"),
                    Parameter(name="height", type_hint="float"),
                ],
                returns="float",
            ),
            assertions=[],
            metadata=Metadata(origin="test", language="typescript"),
        )

        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "assignment", "code": "area = width * height;", "rationale": "Calculate area"},
      {"type": "return", "code": "return area;", "rationale": "Return calculated area"}
    ],
    "variables": [
      {"name": "area", "type_hint": "float", "purpose": "Store calculated area"}
    ],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        result = await generator.generate(ir)

        code = result.source_code
        # Verify variable declaration
        assert "let area: number;" in code
        # Verify usage
        assert "area = width * height;" in code
        assert "return area;" in code

    @pytest.mark.asyncio
    async def test_generation_with_lsp_context(self):
        """Test generation with LSP semantic context from a real repository."""
        temp_dir = TemporaryDirectory()
        repo_path = Path(temp_dir.name)

        # Create a minimal TypeScript project
        (repo_path / "src").mkdir()
        (repo_path / "src" / "models.ts").write_text(
            """
export interface User {
    id: number;
    name: string;
    email: string;
}

export function validateUser(user: User): boolean {
    return user.email.includes('@');
}
"""
        )
        (repo_path / "package.json").write_text('{"name": "test-project", "version": "1.0.0"}')
        (repo_path / "tsconfig.json").write_text(
            '{"compilerOptions": {"target": "ES2020", "module": "commonjs"}}'
        )

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Create a new user object",
                rationale="Initialize user object with name and email",
            ),
            signature=SigClause(
                name="createUser",
                parameters=[
                    Parameter(name="name", type_hint="str"),
                    Parameter(name="email", type_hint="str"),
                ],
                returns="dict",
            ),
            assertions=[],
            metadata=Metadata(origin="test", language="typescript"),
        )

        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return { id: 1, name, email };", "rationale": "Return user object"}
    ],
    "variables": [],
    "imports": []
  }
}
"""
        )

        try:
            # Generate with LSP context
            generator = TypeScriptGenerator(provider, repository_path=repo_path)
            result = await generator.generate(ir)

            code = result.source_code
            # Verify generated code structure
            assert "export function createUser" in code
            assert "name: string" in code
            assert "email: string" in code
            assert "Record<string, any>" in code  # dict maps to Record<string, any>

            # Verify metadata indicates LSP was available
            # (even if it didn't provide context, it was set up)
            assert "has_lsp_context" in result.metadata

        finally:
            temp_dir.cleanup()

    @pytest.mark.asyncio
    async def test_complex_function_with_multiple_features(self):
        """Test generating a complex function with multiple TypeScript features."""
        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Process array of numbers with validation and transformation",
                rationale="Filter, map, and reduce array data",
            ),
            signature=SigClause(
                name="processNumbers",
                parameters=[
                    Parameter(name="numbers", type_hint="list[int]"),
                    Parameter(name="threshold", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(
                    predicate="result >= 0",
                    rationale="Sum must be non-negative",
                )
            ],
            metadata=Metadata(origin="test", language="typescript"),
        )

        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {
        "type": "assignment",
        "code": "filtered = numbers.filter(n => n > threshold);",
        "rationale": "Filter numbers above threshold"
      },
      {
        "type": "assignment",
        "code": "sum = filtered.reduce((acc, n) => acc + n, 0);",
        "rationale": "Sum the filtered numbers"
      },
      {
        "type": "return",
        "code": "return sum;",
        "rationale": "Return the sum"
      }
    ],
    "variables": [
      {"name": "filtered", "type_hint": "list[int]", "purpose": "Filtered numbers"},
      {"name": "sum", "type_hint": "int", "purpose": "Sum of numbers"}
    ],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        result = await generator.generate(ir)

        code = result.source_code
        # Verify all components present
        assert "export function processNumbers" in code
        assert "numbers: Array<number>" in code
        assert "threshold: number" in code
        assert ": number" in code
        assert "let filtered: Array<number>;" in code
        assert "let sum: number;" in code
        assert "filter" in code
        assert "reduce" in code

        # Verify TSDoc includes constraint
        assert "/**" in code
        assert "Process array of numbers with validation and transformation" in code
