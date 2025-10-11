"""Anthropic provider implementation."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .base import BaseProvider, ProviderCapabilities


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(BaseProvider):
    """Thin wrapper around Anthropic's Messages API."""

    def __init__(self) -> None:
        super().__init__(
            name="anthropic",
            capabilities=ProviderCapabilities(streaming=True, structured_output=False, reasoning=True),
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._api_key: Optional[str] = None
        self._default_model = "claude-3-sonnet-20240229"

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        token = credentials.get("access_token") or credentials.get("api_key")
        if not token:
            raise ValueError("Anthropic credentials require an access token or API key")
        self._api_key = token

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: Optional[str] = None,
        **_: Any,
    ) -> str:
        client = await self._ensure_client()
        if not self._api_key:
            raise RuntimeError("Anthropic provider not initialized")
        payload = {
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
        response = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            content=json.dumps(payload),
        )
        response.raise_for_status()
        data = response.json()
        return "".join(part.get("text", "") for part in data["content"])

    async def generate_stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, **kwargs)
        yield text

    async def generate_structured(self, prompt: str, schema: dict, **_: Any) -> dict:
        raise NotImplementedError("Anthropic structured output is not yet implemented")

    async def check_health(self) -> bool:
        return self._api_key is not None

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_structured_output(self) -> bool:
        return False

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
