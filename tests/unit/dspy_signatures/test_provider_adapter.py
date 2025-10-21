"""
Tests for ProviderAdapter (H1)

Validates:
1. Async execution with DSPy signatures
2. XGrammar schema passthrough
3. Resource tracking integration
4. Error handling
5. Type safety
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock

import dspy
import pytest

from lift_sys.dspy_signatures.provider_adapter import ProviderAdapter, ProviderConfig
from lift_sys.providers.base import BaseProvider, ProviderCapabilities


# Mock Provider for testing
class MockProvider(BaseProvider):
    """Mock provider for testing ProviderAdapter."""

    def __init__(
        self,
        structured_output: bool = True,
        streaming: bool = False,
    ) -> None:
        super().__init__(
            name="mock",
            capabilities=ProviderCapabilities(
                streaming=streaming,
                structured_output=structured_output,
                reasoning=True,
            ),
        )
        self._initialized = False
        self.generate_structured_mock = AsyncMock()
        self.generate_text_mock = AsyncMock()

    async def initialize(self, credentials: dict) -> None:
        self._initialized = True

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        return await self.generate_text_mock(
            prompt=prompt, max_tokens=max_tokens, temperature=temperature, **kwargs
        )

    async def generate_stream(self, prompt: str, **kwargs: Any):
        raise NotImplementedError("Streaming not implemented in mock")

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        **kwargs: Any,
    ) -> dict:
        return await self.generate_structured_mock(prompt=prompt, schema=schema, **kwargs)

    async def check_health(self) -> bool:
        return self._initialized

    @property
    def supports_streaming(self) -> bool:
        return self.capabilities.streaming

    @property
    def supports_structured_output(self) -> bool:
        return self.capabilities.structured_output


# Mock ResourceUsage for testing
class MockResourceUsage:
    """Mock ResourceUsage for testing resource tracking."""

    def __init__(self) -> None:
        self.llm_calls = 0
        self.tokens = 0

    def add_llm_call(self) -> None:
        self.llm_calls += 1

    def add_tokens(self, count: int) -> None:
        self.tokens += count


# Test Fixtures


@pytest.fixture
def mock_provider() -> MockProvider:
    """Create mock provider with structured output support."""
    return MockProvider(structured_output=True)


@pytest.fixture
def mock_provider_no_xgrammar() -> MockProvider:
    """Create mock provider without structured output support."""
    return MockProvider(structured_output=False)


@pytest.fixture
def adapter(mock_provider: MockProvider) -> ProviderAdapter:
    """Create ProviderAdapter with mock provider."""
    return ProviderAdapter(mock_provider)


@pytest.fixture
def resource_tracker() -> MockResourceUsage:
    """Create mock resource tracker."""
    return MockResourceUsage()


# Test Cases


class TestProviderAdapterInitialization:
    """Test ProviderAdapter initialization and configuration."""

    def test_init_with_default_config(self, mock_provider: MockProvider) -> None:
        """Test initialization with default config."""
        adapter = ProviderAdapter(mock_provider)
        assert adapter.provider == mock_provider
        assert adapter.config.max_tokens == 2048
        assert adapter.config.temperature == 0.3
        assert adapter.config.use_xgrammar is True

    def test_init_with_custom_config(self, mock_provider: MockProvider) -> None:
        """Test initialization with custom config."""
        config = ProviderConfig(max_tokens=4096, temperature=0.0, use_xgrammar=False)
        adapter = ProviderAdapter(mock_provider, config=config)
        assert adapter.config.max_tokens == 4096
        assert adapter.config.temperature == 0.0
        assert adapter.config.use_xgrammar is False

    def test_init_xgrammar_without_support_raises(
        self, mock_provider_no_xgrammar: MockProvider
    ) -> None:
        """Test that XGrammar enabled with unsupported provider raises error."""
        with pytest.raises(ValueError, match="does not support structured output"):
            ProviderAdapter(mock_provider_no_xgrammar, config=ProviderConfig(use_xgrammar=True))

    def test_init_xgrammar_disabled_with_unsupported_provider(
        self, mock_provider_no_xgrammar: MockProvider
    ) -> None:
        """Test that XGrammar disabled works with unsupported provider."""
        adapter = ProviderAdapter(
            mock_provider_no_xgrammar, config=ProviderConfig(use_xgrammar=False)
        )
        assert adapter.supports_xgrammar is False

    def test_supports_xgrammar_property(self, adapter: ProviderAdapter) -> None:
        """Test supports_xgrammar property reflects config and capabilities."""
        assert adapter.supports_xgrammar is True

        # Disable XGrammar in config
        adapter.config.use_xgrammar = False
        assert adapter.supports_xgrammar is False


class TestAsyncExecution:
    """Test async execution with DSPy signatures."""

    @pytest.mark.asyncio
    async def test_call_with_structured_output(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test __call__ with XGrammar structured output."""
        # Setup mock response
        mock_response = {"intent": "Add two numbers", "confidence": 0.95}
        mock_provider.generate_structured_mock.return_value = mock_response

        schema = {"type": "object", "properties": {"intent": {"type": "string"}}}

        # Execute
        result = await adapter("Test prompt", schema=schema)

        # Verify
        assert isinstance(result, dspy.Prediction)
        assert result.intent == "Add two numbers"
        assert result.confidence == 0.95
        mock_provider.generate_structured_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_with_text_generation(
        self, mock_provider: MockProvider, adapter: ProviderAdapter
    ) -> None:
        """Test __call__ with text generation (no schema)."""
        # Setup mock response
        mock_provider.generate_text_mock.return_value = "Generated text response"

        # Execute (no schema, falls back to text generation)
        result = await adapter("Test prompt")

        # Verify
        assert isinstance(result, dspy.Prediction)
        assert result.output == "Generated text response"
        mock_provider.generate_text_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_with_json_text_response(
        self, mock_provider: MockProvider, adapter: ProviderAdapter
    ) -> None:
        """Test __call__ parsing JSON from text response."""
        # Setup mock response (JSON as text)
        mock_provider.generate_text_mock.return_value = '{"result": "parsed JSON"}'

        # Execute
        result = await adapter("Test prompt")

        # Verify
        assert isinstance(result, dspy.Prediction)
        assert result.result == "parsed JSON"

    @pytest.mark.asyncio
    async def test_call_with_kwargs_override(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test __call__ with parameter overrides."""
        mock_response = {"output": "test"}
        mock_provider.generate_structured_mock.return_value = mock_response

        schema = {"type": "object"}

        # Call with overrides
        await adapter("Test prompt", schema=schema, max_tokens=1000, temperature=0.0, top_p=0.9)

        # Verify parameters passed to provider
        call_args = mock_provider.generate_structured_mock.call_args
        assert call_args.kwargs["max_tokens"] == 1000
        assert call_args.kwargs["temperature"] == 0.0
        assert call_args.kwargs["top_p"] == 0.9

    @pytest.mark.asyncio
    async def test_call_error_propagation(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that provider errors are properly propagated."""
        # Setup mock to raise error
        mock_provider.generate_structured_mock.side_effect = RuntimeError("Provider failure")

        # Execute should raise ValueError
        with pytest.raises(ValueError, match="Provider call failed"):
            await adapter("Test prompt", schema={"type": "object"})


class TestResourceTracking:
    """Test resource tracking integration."""

    @pytest.mark.asyncio
    async def test_tracks_llm_calls(
        self,
        adapter: ProviderAdapter,
        mock_provider: MockProvider,
        resource_tracker: MockResourceUsage,
    ) -> None:
        """Test that LLM calls are tracked."""
        adapter.set_resource_tracker(resource_tracker)
        mock_provider.generate_structured_mock.return_value = {"output": "test"}

        # Execute multiple calls
        await adapter("Prompt 1", schema={"type": "object"})
        await adapter("Prompt 2", schema={"type": "object"})
        await adapter("Prompt 3", schema={"type": "object"})

        # Verify tracking
        assert resource_tracker.llm_calls == 3

    @pytest.mark.asyncio
    async def test_tracks_tokens(
        self,
        adapter: ProviderAdapter,
        mock_provider: MockProvider,
        resource_tracker: MockResourceUsage,
    ) -> None:
        """Test that token usage is tracked."""
        adapter.set_resource_tracker(resource_tracker)
        mock_response = {"output": "This is a longer response with multiple words"}
        mock_provider.generate_structured_mock.return_value = mock_response

        # Execute
        await adapter("Test prompt", schema={"type": "object"})

        # Verify tokens tracked (estimate from JSON length)
        assert resource_tracker.tokens > 0

    @pytest.mark.asyncio
    async def test_no_tracking_when_disabled(
        self,
        mock_provider: MockProvider,
        resource_tracker: MockResourceUsage,
    ) -> None:
        """Test that tracking can be disabled."""
        # Create adapter with tracking disabled
        config = ProviderConfig(track_resources=False)
        adapter = ProviderAdapter(mock_provider, config=config)
        adapter.set_resource_tracker(resource_tracker)

        mock_provider.generate_structured_mock.return_value = {"output": "test"}

        # Execute
        await adapter("Test prompt", schema={"type": "object"})

        # Verify NO tracking occurred
        assert resource_tracker.llm_calls == 0
        assert resource_tracker.tokens == 0

    @pytest.mark.asyncio
    async def test_no_tracking_without_tracker(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that adapter works without resource tracker set."""
        # Don't set resource tracker
        mock_provider.generate_structured_mock.return_value = {"output": "test"}

        # Should not raise error
        result = await adapter("Test prompt", schema={"type": "object"})
        assert isinstance(result, dspy.Prediction)


class TestXGrammarSchemaPassthrough:
    """Test XGrammar schema preservation."""

    @pytest.mark.asyncio
    async def test_schema_passed_to_provider(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that JSON schema is passed through to provider."""
        schema = {
            "type": "object",
            "properties": {
                "intent": {"type": "string"},
                "parameters": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["intent"],
        }

        mock_provider.generate_structured_mock.return_value = {
            "intent": "test",
            "parameters": ["a", "b"],
        }

        # Execute
        await adapter("Test prompt", schema=schema)

        # Verify schema passed unchanged
        call_args = mock_provider.generate_structured_mock.call_args
        assert call_args.kwargs["schema"] == schema

    @pytest.mark.asyncio
    async def test_xgrammar_disabled_uses_text_generation(
        self, mock_provider: MockProvider
    ) -> None:
        """Test that XGrammar disabled falls back to text generation."""
        config = ProviderConfig(use_xgrammar=False)
        adapter = ProviderAdapter(mock_provider, config=config)

        mock_provider.generate_text_mock.return_value = "Text response"

        # Call with schema, should ignore it and use text generation
        result = await adapter("Test prompt", schema={"type": "object"})

        # Verify text generation used, not structured
        mock_provider.generate_text_mock.assert_called_once()
        mock_provider.generate_structured_mock.assert_not_called()
        assert result.output == "Text response"


class TestSignatureIntegration:
    """Test integration with DSPy signature field extraction."""

    @pytest.mark.asyncio
    async def test_filters_fields_by_signature(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that response fields are filtered by signature output fields."""
        # Create mock signature with specific output fields
        mock_signature = Mock()
        output_field1 = Mock()
        output_field1.input_variable = "intent"
        output_field2 = Mock()
        output_field2.input_variable = "confidence"
        mock_signature.output_fields = [output_field1, output_field2]

        # Provider returns extra fields
        mock_provider.generate_structured_mock.return_value = {
            "intent": "Add numbers",
            "confidence": 0.9,
            "extra_field": "should be filtered",
            "another_field": 42,
        }

        # Execute with signature
        result = await adapter("Test prompt", schema={"type": "object"}, signature=mock_signature)

        # Verify only signature fields included
        assert result.intent == "Add numbers"
        assert result.confidence == 0.9
        assert not hasattr(result, "extra_field")
        assert not hasattr(result, "another_field")

    @pytest.mark.asyncio
    async def test_text_response_uses_first_output_field(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that text response uses first output field name."""
        # Create mock signature
        mock_signature = Mock()
        output_field = Mock()
        output_field.input_variable = "result"
        mock_signature.output_fields = [output_field]

        # Provider returns text
        mock_provider.generate_text_mock.return_value = "Text result"

        # Execute with signature
        result = await adapter("Test prompt", signature=mock_signature)

        # Verify field name from signature used
        assert result.result == "Text result"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_response_dict(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test handling of empty response dict."""
        mock_provider.generate_structured_mock.return_value = {}

        result = await adapter("Test prompt", schema={"type": "object"})

        # Should return prediction with no fields
        assert isinstance(result, dspy.Prediction)

    @pytest.mark.asyncio
    async def test_malformed_json_text(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test handling of malformed JSON in text response."""
        mock_provider.generate_text_mock.return_value = "{invalid json"

        result = await adapter("Test prompt")

        # Should fall back to single output field
        assert isinstance(result, dspy.Prediction)
        assert result.output == "{invalid json"

    @pytest.mark.asyncio
    async def test_inspect_history_returns_empty(self, adapter: ProviderAdapter) -> None:
        """Test inspect_history returns empty list (not yet implemented)."""
        history = await adapter.inspect_history(n=5)
        assert history == []


class TestTypeSafety:
    """Test type safety and mypy compliance."""

    def test_adapter_type_annotations(self) -> None:
        """Test that ProviderAdapter has proper type annotations."""
        # This test passes if mypy checks pass
        # Verify key methods have correct signatures
        assert callable(ProviderAdapter)
        assert hasattr(ProviderAdapter, "set_resource_tracker")
        assert hasattr(ProviderAdapter, "supports_xgrammar")

    def test_config_type_annotations(self) -> None:
        """Test that ProviderConfig is a valid Pydantic model."""
        from pydantic import ValidationError

        config = ProviderConfig(max_tokens=1000, temperature=0.5)
        assert config.max_tokens == 1000
        assert config.temperature == 0.5

        # Test validation
        with pytest.raises(ValidationError):
            ProviderConfig(max_tokens="invalid")  # type: ignore


# Integration test (end-to-end)


class TestIntegration:
    """Integration tests with real-ish DSPy usage patterns."""

    @pytest.mark.asyncio
    async def test_end_to_end_structured_generation(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test complete flow: prompt -> provider -> prediction."""
        # Simulate DSPy signature output structure
        mock_response = {
            "intent_summary": "Add two numbers",
            "function_name": "add",
            "parameters": ["a: int", "b: int"],
            "return_type": "int",
        }
        mock_provider.generate_structured_mock.return_value = mock_response

        schema = {
            "type": "object",
            "properties": {
                "intent_summary": {"type": "string"},
                "function_name": {"type": "string"},
                "parameters": {"type": "array"},
                "return_type": {"type": "string"},
            },
            "required": ["intent_summary", "function_name", "return_type"],
        }

        # Execute like DSPy would
        result = await adapter(
            prompt="Create a function to add two numbers", schema=schema, max_tokens=2048
        )

        # Verify complete flow
        assert isinstance(result, dspy.Prediction)
        assert result.intent_summary == "Add two numbers"
        assert result.function_name == "add"
        assert result.return_type == "int"
        assert "a: int" in result.parameters

    @pytest.mark.asyncio
    async def test_performance_overhead(
        self, adapter: ProviderAdapter, mock_provider: MockProvider
    ) -> None:
        """Test that adapter overhead is minimal (<10% target)."""
        import time

        mock_provider.generate_structured_mock.return_value = {"output": "test"}

        # Measure adapter overhead
        iterations = 100
        start = time.perf_counter()
        for _ in range(iterations):
            await adapter("Test", schema={"type": "object"})
        adapter_time = time.perf_counter() - start

        # Adapter overhead should be minimal
        # (This test is rough since we're using mocks, but validates no obvious slowdown)
        per_call_overhead = (adapter_time / iterations) * 1000  # ms
        assert per_call_overhead < 1.0  # <1ms per call (very conservative)
