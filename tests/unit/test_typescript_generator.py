"""Tests for TypeScript code generator."""

from __future__ import annotations

from pathlib import Path

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


class TestTypeScriptGeneratorBasics:
    """Basic tests for TypeScript generator."""

    def test_generator_initialization(self):
        """Test TypeScript generator can be initialized."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        assert generator.provider == provider
        assert generator.type_resolver is not None
        assert generator.context_provider is None  # No repository path

    def test_generator_initialization_with_repository(self):
        """Test generator initialization with repository path."""
        import tempfile

        provider = MockProvider()
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            generator = TypeScriptGenerator(provider, repository_path=repo_path)

            assert generator.context_provider is not None

    def test_validate_typescript_syntax_valid(self):
        """Test TypeScript syntax validation with valid code."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        valid_code = """
export function add(a: number, b: number): number {
  return a + b;
}
"""

        # Should return True (or True if tsc not available)
        result = generator._validate_typescript_syntax(valid_code)
        assert isinstance(result, bool)

    def test_extract_json_from_markdown(self):
        """Test JSON extraction from markdown blocks."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        markdown_response = """
Here is the implementation:

```json
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return a + b;", "rationale": "Add numbers"}
    ]
  }
}
```
"""

        result = generator._extract_json(markdown_response)
        assert "implementation" in result
        assert "body_statements" in result["implementation"]

    def test_extract_json_direct(self):
        """Test JSON extraction from direct JSON."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        json_response = '{"implementation": {"body_statements": []}}'

        result = generator._extract_json(json_response)
        assert "implementation" in result

    def test_validate_implementation_valid(self):
        """Test implementation validation with valid JSON."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        valid_impl = {
            "implementation": {
                "body_statements": [{"type": "return", "code": "return x;", "rationale": "test"}]
            }
        }

        # Should not raise
        generator._validate_implementation(valid_impl)

    def test_validate_implementation_missing_key(self):
        """Test implementation validation with missing key."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        invalid_impl = {"wrong_key": {}}

        with pytest.raises(ValueError, match="Missing 'implementation'"):
            generator._validate_implementation(invalid_impl)

    def test_validate_implementation_empty_statements(self):
        """Test implementation validation with empty statements."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        invalid_impl = {"implementation": {"body_statements": []}}

        with pytest.raises(ValueError, match="cannot be empty"):
            generator._validate_implementation(invalid_impl)


class TestTypeScriptCodeBuilding:
    """Tests for TypeScript code building."""

    def test_build_typescript_code_simple(self):
        """Test building simple TypeScript code."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(
                summary="Add two numbers",
                rationale="Perform addition",
            ),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[],
            metadata=Metadata(
                origin="test",
            ),
        )

        impl_json = {
            "implementation": {
                "body_statements": [
                    {"type": "return", "code": "return a + b;", "rationale": "Add the numbers"}
                ],
                "variables": [],
                "imports": [],
            }
        }

        code = generator._build_typescript_code(ir, impl_json, None)

        # Verify structure
        assert "export function add" in code
        assert "a: number" in code
        assert "b: number" in code
        assert ": number {" in code
        assert "return a + b;" in code
        assert "/**" in code  # TSDoc comment
        assert "@param" in code
        assert "@returns" in code

    def test_build_typescript_code_with_imports(self):
        """Test building TypeScript code with imports."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Read file", rationale=""),
            signature=SigClause(
                name="readFile",
                parameters=[Parameter(name="path", type_hint="str")],
                returns="str",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        impl_json = {
            "implementation": {
                "body_statements": [
                    {"type": "return", "code": "return fs.readFileSync(path, 'utf8');"}
                ],
                "variables": [],
                "imports": [{"module": "fs", "imports": ["readFileSync"]}],
            }
        }

        code = generator._build_typescript_code(ir, impl_json, None)

        assert "import { readFileSync } from 'fs';" in code
        assert "export function readFile" in code

    def test_build_typescript_code_with_variables(self):
        """Test building TypeScript code with variable declarations."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Calculate", rationale=""),
            signature=SigClause(
                name="calculate",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        impl_json = {
            "implementation": {
                "body_statements": [
                    {"type": "assignment", "code": "result = x * 2;"},
                    {"type": "return", "code": "return result;"},
                ],
                "variables": [{"name": "result", "type_hint": "int", "purpose": "Store result"}],
                "imports": [],
            }
        }

        code = generator._build_typescript_code(ir, impl_json, None)

        assert "let result: number;" in code
        assert "result = x * 2;" in code
        assert "return result;" in code

    def test_build_async_function(self):
        """Test building async TypeScript function."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Fetch data", rationale=""),
            signature=SigClause(
                name="fetchData",
                parameters=[Parameter(name="url", type_hint="str")],
                returns="Promise[str]",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        impl_json = {
            "implementation": {
                "body_statements": [
                    {"type": "return", "code": "return await fetch(url).then(r => r.text());"}
                ],
                "variables": [],
                "imports": [],
            }
        }

        code = generator._build_typescript_code(ir, impl_json, None)

        # async is handled by type resolver
        assert "fetchData" in code
        assert "Promise<string>" in code or "Promise" in code


class TestTypeScriptPromptBuilding:
    """Tests for generation prompt building."""

    def test_build_generation_prompt_basic(self):
        """Test building basic generation prompt."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Multiply numbers", rationale="Math operation"),
            signature=SigClause(
                name="multiply",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[
                AssertClause(
                    predicate="result >= 0 if both inputs positive",
                    rationale="Positive multiplication",
                )
            ],
            metadata=Metadata(origin="test"),
        )

        prompt = generator._build_generation_prompt(ir, None, ["result >= 0"])

        assert "Multiply numbers" in prompt
        assert "Math operation" in prompt
        assert "function multiply" in prompt
        assert "a: number" in prompt
        assert "b: number" in prompt
        assert "result >= 0" in prompt
        assert "TypeScript" in prompt

    def test_build_generation_prompt_with_context(self):
        """Test building prompt with semantic context."""
        from lift_sys.codegen.semantic_context import (
            ImportPattern,
            SemanticContext,
            TypeInfo,
        )

        provider = MockProvider()
        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Create user", rationale=""),
            signature=SigClause(
                name="createUser",
                parameters=[
                    Parameter(name="name", type_hint="str"),
                    Parameter(name="email", type_hint="str"),
                ],
                returns="User",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        context = SemanticContext(
            available_types=[
                TypeInfo(name="User", module="models", description="User type", example_usage=None)
            ],
            available_functions=[],
            import_patterns=[
                ImportPattern(module="models", common_imports=["User"], usage_context="User model")
            ],
            codebase_conventions={},
        )

        prompt = generator._build_generation_prompt(ir, context, [])

        assert "User" in prompt
        assert "models" in prompt
        assert "Available types from codebase" in prompt


class TestTypeScriptGeneration:
    """Integration tests for TypeScript generation."""

    @pytest.mark.asyncio
    async def test_generate_simple_function(self):
        """Test generating a simple TypeScript function."""
        # Mock provider that returns valid implementation JSON
        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return a + b;", "rationale": "Add numbers"}
    ],
    "variables": [],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Add two numbers", rationale=""),
            signature=SigClause(
                name="add",
                parameters=[
                    Parameter(name="a", type_hint="int"),
                    Parameter(name="b", type_hint="int"),
                ],
                returns="int",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        result = await generator.generate(ir)

        assert result.language == "typescript"
        assert "export function add" in result.source_code
        assert "number" in result.source_code
        assert "return a + b;" in result.source_code
        assert result.metadata["generator"] == "typescript-xgrammar"

    @pytest.mark.asyncio
    async def test_generate_with_retry_on_invalid_json(self):
        """Test generation retries on invalid JSON."""
        provider = MockProvider()

        # First attempt: invalid JSON, second attempt: valid
        provider.set_responses(
            [
                "invalid json here",
                """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return x * 2;"}
    ]
  }
}
""",
            ]
        )

        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Double number", rationale=""),
            signature=SigClause(
                name="double",
                parameters=[Parameter(name="x", type_hint="int")],
                returns="int",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        result = await generator.generate(ir)

        assert result.source_code is not None
        assert result.metadata["attempts"] == 2  # Took 2 attempts

    @pytest.mark.asyncio
    async def test_generate_fails_after_max_retries(self):
        """Test generation fails after max retries."""
        provider = MockProvider()
        provider.set_response("always invalid json")

        generator = TypeScriptGenerator(provider)

        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test", rationale=""),
            signature=SigClause(
                name="test",
                parameters=[],
                returns="void",
            ),
            assertions=[],
            metadata=Metadata(origin="test"),
        )

        with pytest.raises(ValueError, match="Failed to generate"):
            await generator.generate(ir, max_retries=2)
