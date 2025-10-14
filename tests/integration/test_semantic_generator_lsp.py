"""Integration tests for SemanticCodeGenerator with LSP support."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lift_sys.codegen.generator import CodeGeneratorConfig
from lift_sys.codegen.semantic_generator import SemanticCodeGenerator
from lift_sys.ir.models import (
    IntentClause,
    IntermediateRepresentation,
    Metadata,
    Parameter,
    SigClause,
)
from lift_sys.providers.base import BaseProvider


class MockProvider(BaseProvider):
    """Mock provider for testing code generation."""

    def __init__(self):
        super().__init__(name="mock", capabilities=None)

    async def initialize(self, credentials: dict) -> None:
        pass

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate mock implementation based on prompt."""
        # Simple mock that returns valid implementation JSON
        impl = {
            "implementation": {
                "body_statements": [
                    {
                        "type": "assignment",
                        "code": "result = x + y",
                        "rationale": "Calculate sum",
                    },
                    {"type": "return", "code": "return result"},
                ],
                "algorithm": "Direct addition",
                "complexity": {"time": "O(1)", "space": "O(1)"},
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


@pytest.mark.asyncio
async def test_semantic_generator_with_knowledge_base():
    """Test SemanticCodeGenerator using knowledge base (no repository)."""
    provider = MockProvider()
    config = CodeGeneratorConfig()

    # Create generator without repository path (should use knowledge base)
    generator = SemanticCodeGenerator(
        provider=provider,
        config=config,
        language="python",
        repository_path=None,
    )

    # Should not use LSP
    assert not generator._use_lsp

    # Create simple IR
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Calculate sum of two numbers"),
        signature=SigClause(
            name="add_numbers",
            parameters=[
                Parameter(name="x", type_hint="int"),
                Parameter(name="y", type_hint="int"),
            ],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    # Generate code
    result = await generator.generate(ir)

    # Verify generation succeeded
    assert result.source_code
    assert "def add_numbers(x: int, y: int) -> int:" in result.source_code
    assert result.metadata["semantic_context_used"] is True
    assert result.metadata["use_lsp"] is False


@pytest.mark.asyncio
async def test_semantic_generator_with_lsp():
    """Test SemanticCodeGenerator using LSP (with repository)."""
    provider = MockProvider()
    config = CodeGeneratorConfig()

    # Use lift-sys itself as test repository
    repo_path = Path(__file__).parent.parent.parent

    # Create generator with repository path (should use LSP)
    generator = SemanticCodeGenerator(
        provider=provider,
        config=config,
        language="python",
        repository_path=repo_path,
    )

    # Should use LSP
    assert generator._use_lsp

    # Use async context manager for LSP lifecycle
    async with generator:
        # Create IR for file operations
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Read file and return contents"),
            signature=SigClause(
                name="read_file",
                parameters=[
                    Parameter(name="path", type_hint="str"),
                ],
                returns="str",
            ),
            metadata=Metadata(language="python", origin="test"),
        )

        # Generate code
        result = await generator.generate(ir)

        # Verify generation succeeded
        assert result.source_code
        assert "def read_file(path: str) -> str:" in result.source_code
        assert result.metadata["semantic_context_used"] is True
        assert result.metadata["use_lsp"] is True


@pytest.mark.asyncio
async def test_semantic_generator_lsp_context_content():
    """Test that LSP context affects generated code."""
    provider = MockProvider()
    config = CodeGeneratorConfig()

    repo_path = Path(__file__).parent.parent.parent

    generator = SemanticCodeGenerator(
        provider=provider,
        config=config,
        language="python",
        repository_path=repo_path,
    )

    async with generator:
        # Test file operations - should suggest pathlib
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Check if file exists at given path"),
            signature=SigClause(
                name="file_exists",
                parameters=[Parameter(name="filepath", type_hint="str")],
                returns="bool",
            ),
            metadata=Metadata(language="python", origin="test"),
        )

        result = await generator.generate(ir)

        # Check metadata shows context was retrieved
        assert result.metadata["semantic_context_used"] is True
        assert result.metadata["use_lsp"] is True


@pytest.mark.asyncio
async def test_semantic_generator_fallback_on_invalid_repo():
    """Test that generator falls back to knowledge base on invalid repository."""
    provider = MockProvider()
    config = CodeGeneratorConfig()

    # Use non-existent repository path
    repo_path = Path("/nonexistent/repository")

    # Should fall back to knowledge base
    generator = SemanticCodeGenerator(
        provider=provider,
        config=config,
        language="python",
        repository_path=repo_path,
    )

    # Should not use LSP (repository doesn't exist)
    assert not generator._use_lsp

    # Should still work with knowledge base
    ir = IntermediateRepresentation(
        intent=IntentClause(summary="Simple addition"),
        signature=SigClause(
            name="add",
            parameters=[
                Parameter(name="a", type_hint="int"),
                Parameter(name="b", type_hint="int"),
            ],
            returns="int",
        ),
        metadata=Metadata(language="python", origin="test"),
    )

    result = await generator.generate(ir)
    assert result.source_code
    assert result.metadata["use_lsp"] is False


@pytest.mark.asyncio
async def test_semantic_generator_async_context_manager():
    """Test using generator as async context manager."""
    provider = MockProvider()
    repo_path = Path(__file__).parent.parent.parent

    async with SemanticCodeGenerator(
        provider=provider,
        config=CodeGeneratorConfig(),
        language="python",
        repository_path=repo_path,
    ) as generator:
        ir = IntermediateRepresentation(
            intent=IntentClause(summary="Test function"),
            signature=SigClause(name="test_func", parameters=[], returns="None"),
            metadata=Metadata(language="python", origin="test"),
        )

        result = await generator.generate(ir)
        assert result.source_code
        assert "def test_func() -> None:" in result.source_code
