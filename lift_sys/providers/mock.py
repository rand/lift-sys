"""Mock provider for testing."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from .base import BaseProvider, ProviderCapabilities


class MockProvider(BaseProvider):
    """Mock LLM provider for testing.

    Returns pre-configured responses for testing without making real API calls.
    """

    def __init__(self):
        """Initialize mock provider."""
        # Initialize base class with capabilities
        super().__init__(
            name="mock",
            capabilities=ProviderCapabilities(
                streaming=True,
                structured_output=True,  # Mock supports structured output for testing
                reasoning=True,
            ),
        )
        self._responses: list[str] = []
        self._response_index = 0
        self._default_response = '{"implementation": {"body_statements": []}}'
        self._structured_response: dict[str, Any] | None = None

    def set_response(self, response: str):
        """Set a single response to return."""
        self._responses = [response]
        self._response_index = 0

    def set_responses(self, responses: list[str]):
        """Set multiple responses to return in sequence."""
        self._responses = responses
        self._response_index = 0

    def set_structured_response(self, response: dict[str, Any]):
        """Set a structured response to return from generate_structured()."""
        self._structured_response = response
        # Enable structured output capability when structured response is set
        self.capabilities.structured_output = True

    async def initialize(self) -> None:
        """Initialize provider (no-op for mock)."""
        pass

    async def check_health(self) -> dict[str, Any]:
        """Check provider health (always healthy for mock)."""
        return {"status": "healthy", "provider": "mock"}

    def supports_streaming(self) -> bool:
        """Mock supports streaming."""
        return True

    def supports_structured_output(self) -> bool:
        """Mock supports structured output."""
        return True

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate text using mock responses.

        Args:
            prompt: Input prompt (ignored)
            max_tokens: Max tokens to generate (ignored)
            temperature: Sampling temperature (ignored)
            **kwargs: Additional provider-specific arguments (ignored)

        Returns:
            Pre-configured mock response
        """
        if not self._responses:
            return self._default_response

        response = self._responses[self._response_index]

        # Advance to next response for sequential responses
        if self._response_index < len(self._responses) - 1:
            self._response_index += 1

        return response

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response (yields complete response at once)."""
        response = await self.generate_text(prompt, max_tokens, temperature, **kwargs)
        yield response

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs,
    ) -> dict[str, Any]:
        """Generate structured response (returns default empty structure)."""
        import json

        # If structured response is set, return it directly
        if self._structured_response is not None:
            return self._structured_response

        # Otherwise try to parse text response as JSON
        response = await self.generate_text(prompt, max_tokens, temperature, **kwargs)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"implementation": {"body_statements": []}}
