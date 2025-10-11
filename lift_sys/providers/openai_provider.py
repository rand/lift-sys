"""OpenAI provider implementation."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .base import BaseProvider, ProviderCapabilities

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseProvider):
    """Minimal wrapper around the OpenAI chat completions API."""

    def __init__(self) -> None:
        super().__init__(
            name="openai",
            capabilities=ProviderCapabilities(streaming=True, structured_output=True, reasoning=True),
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._api_key: Optional[str] = None
        self._organization: Optional[str] = None
        self._default_model = "gpt-4o"

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        token = credentials.get("access_token") or credentials.get("api_key")
        if not token:
            raise ValueError("OpenAI credentials require an access token or API key")
        self._api_key = token
        self._organization = credentials.get("organization_id")

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
            raise RuntimeError("OpenAI provider not initialized")
        payload = {
            "model": model or self._default_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"authorization": f"Bearer {self._api_key}"}
        if self._organization:
            headers["OpenAI-Organization"] = self._organization
        response = await client.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            content=json.dumps(payload),
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"].get("content", "")

    async def generate_stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, **kwargs)
        yield text

    async def generate_structured(self, prompt: str, schema: dict, **kwargs: Any) -> dict:
        client = await self._ensure_client()
        if not self._api_key:
            raise RuntimeError("OpenAI provider not initialized")
        payload = {
            "model": kwargs.get("model", self._default_model),
            "temperature": kwargs.get("temperature", 0),
            "response_format": {"type": "json_schema", "json_schema": {"schema": schema}},
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"authorization": f"Bearer {self._api_key}"}
        if self._organization:
            headers["OpenAI-Organization"] = self._organization
        response = await client.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            content=json.dumps(payload),
        )
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        content = message.get("content", "{}")
        return json.loads(content)

    async def check_health(self) -> bool:
        return self._api_key is not None

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_structured_output(self) -> bool:
        return True

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
