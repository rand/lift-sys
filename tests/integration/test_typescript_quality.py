"""Integration test for TypeScript quality validation.

This test runs the quality validation framework on a subset of test prompts
to verify the validation system works correctly.
"""

from __future__ import annotations

import pytest

from lift_sys.codegen.languages.typescript_generator import TypeScriptGenerator
from lift_sys.providers.mock import MockProvider
from tests.validation.typescript_quality_validator import TypeScriptQualityValidator


class TestTypeScriptQualityValidation:
    """Test the TypeScript quality validation framework."""

    @pytest.mark.asyncio
    async def test_validator_loads_test_prompts(self):
        """Test that validator can load test prompts from YAML."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        prompts = validator.load_test_prompts()

        # Verify prompts loaded
        assert len(prompts) > 0
        assert len(prompts) == 30  # We defined 30 prompts

        # Verify prompt structure
        first_prompt = prompts[0]
        assert "id" in first_prompt
        assert "category" in first_prompt
        assert "intent" in first_prompt
        assert "signature" in first_prompt

    @pytest.mark.asyncio
    async def test_validator_converts_prompt_to_ir(self):
        """Test conversion of test prompt to IR."""
        provider = MockProvider()
        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        prompts = validator.load_test_prompts()
        basic_prompt = next(p for p in prompts if p["id"] == "basic_001")

        ir = validator.prompt_to_ir(basic_prompt)

        # Verify IR structure
        assert ir.intent.summary == "Add two numbers"
        assert ir.signature.name == "add"
        assert len(ir.signature.parameters) == 2
        assert ir.signature.returns == "int"
        assert len(ir.assertions) > 0

    @pytest.mark.asyncio
    async def test_validator_validates_single_prompt(self):
        """Test validation of a single prompt."""
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
        validator = TypeScriptQualityValidator(generator)

        prompts = validator.load_test_prompts()
        basic_prompt = next(p for p in prompts if p["id"] == "basic_001")

        result = await validator.validate_prompt(basic_prompt)

        # Verify result
        assert result.prompt_id == "basic_001"
        assert result.category == "basic"
        assert result.success is True  # Should succeed with mock provider
        assert result.generated_code is not None
        assert result.syntax_valid is True
        assert result.generation_time_ms > 0
        assert result.code_length_lines > 0

    @pytest.mark.asyncio
    async def test_validator_detects_expected_features(self):
        """Test that validator detects expected code features."""
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
        validator = TypeScriptQualityValidator(generator)

        prompts = validator.load_test_prompts()
        basic_prompt = next(p for p in prompts if p["id"] == "basic_001")

        result = await validator.validate_prompt(basic_prompt)

        # Should have detected expected features
        assert "TSDoc comment" in result.has_expected_features
        assert "Type annotations" in result.has_expected_features
        assert "Return statement" in result.has_expected_features

    @pytest.mark.asyncio
    async def test_validator_runs_multiple_prompts(self):
        """Test validation of multiple prompts."""
        provider = MockProvider()
        # Set up generic responses for all tests
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return true;", "rationale": "Default response"}
    ],
    "variables": [],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        # Run validation on first 3 prompts
        summary = await validator.validate_all(max_prompts=3, max_retries=1)

        # Verify summary
        assert summary.total_prompts == 3
        assert summary.successful + summary.failed == 3
        assert summary.avg_generation_time_ms > 0

    @pytest.mark.asyncio
    async def test_validator_computes_category_stats(self):
        """Test that validator computes per-category statistics."""
        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return result;", "rationale": "Return result"}
    ],
    "variables": [],
    "imports": []
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        # Run validation on first 10 prompts (covers multiple categories)
        summary = await validator.validate_all(max_prompts=10, max_retries=1)

        # Verify category stats exist
        assert len(summary.category_stats) > 0

        # Each category should have counts
        for _category, stats in summary.category_stats.items():
            assert "total" in stats
            assert "successful" in stats
            assert "failed" in stats
            assert stats["total"] == stats["successful"] + stats["failed"]

    @pytest.mark.asyncio
    async def test_validator_exports_results(self, tmp_path):
        """Test that validator can export results to JSON."""
        provider = MockProvider()
        provider.set_response(
            """
{
  "implementation": {
    "body_statements": [
      {"type": "return", "code": "return value;"}
    ]
  }
}
"""
        )

        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        # Run validation
        await validator.validate_all(max_prompts=2, max_retries=1)

        # Export results
        output_file = tmp_path / "results.json"
        validator.export_results(output_file)

        # Verify file was created
        assert output_file.exists()

        # Verify content
        import json

        with open(output_file) as f:
            data = json.load(f)

        assert "results" in data
        assert len(data["results"]) == 2

        # Verify result structure
        result = data["results"][0]
        assert "prompt_id" in result
        assert "category" in result
        assert "success" in result
        assert "generated_code" in result

    @pytest.mark.asyncio
    async def test_validator_handles_generation_failures(self):
        """Test that validator handles generation failures gracefully."""
        provider = MockProvider()
        provider.set_response("invalid json that will fail")

        generator = TypeScriptGenerator(provider)
        validator = TypeScriptQualityValidator(generator)

        prompts = validator.load_test_prompts()
        basic_prompt = next(p for p in prompts if p["id"] == "basic_001")

        result = await validator.validate_prompt(basic_prompt, max_retries=1)

        # Should fail but not crash
        assert result.success is False
        assert len(result.validation_errors) > 0
        assert "Generation failed" in result.validation_errors[0]
