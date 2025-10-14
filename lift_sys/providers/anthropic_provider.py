"""Anthropic provider implementation."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from anthropic import AsyncAnthropic

from .base import BaseProvider, ProviderCapabilities


class AnthropicProvider(BaseProvider):
    """Thin wrapper around Anthropic's Messages API."""

    def __init__(self) -> None:
        super().__init__(
            name="anthropic",
            capabilities=ProviderCapabilities(
                streaming=True, structured_output=False, reasoning=True
            ),
        )
        self._client: AsyncAnthropic | None = None
        self._api_key: str | None = None
        self._default_model = "claude-sonnet-4-20250514"

    async def initialize(self, credentials: dict[str, Any]) -> None:
        token = credentials.get("access_token") or credentials.get("api_key")
        if not token:
            raise ValueError("Anthropic credentials require an access token or API key")
        self._api_key = token
        self._client = AsyncAnthropic(api_key=token)

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: str | None = None,
        system_prompt: str | None = None,
        **_: Any,
    ) -> str:
        if not self._client:
            raise RuntimeError("Anthropic provider not initialized")

        kwargs = {
            "model": model or self._default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = await self._client.messages.create(**kwargs)

        # Extract text from response
        return "".join(block.text for block in response.content if hasattr(block, "text"))

    async def generate_stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, **kwargs)
        yield text

    async def generate_structured(self, prompt: str, schema: dict, **_: Any) -> dict:
        raise NotImplementedError("Anthropic structured output is not yet implemented")

    async def check_health(self) -> bool:
        return self._client is not None

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_structured_output(self) -> bool:
        return False

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
