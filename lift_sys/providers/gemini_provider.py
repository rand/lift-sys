"""Google Gemini provider implementation."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx

from .base import BaseProvider, ProviderCapabilities

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-1.5-pro"


class GeminiProvider(BaseProvider):
    """Wrapper for Google Gemini API via REST."""

    def __init__(self) -> None:
        super().__init__(
            name="gemini",
            capabilities=ProviderCapabilities(streaming=True, structured_output=True, reasoning=True),
        )
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None
        self._api_key: Optional[str] = None
        self._project_id: Optional[str] = None

    async def initialize(self, credentials: Dict[str, Any]) -> None:
        self._access_token = credentials.get("access_token")
        self._api_key = credentials.get("api_key")
        self._project_id = credentials.get("project_id")
        if not (self._access_token or self._api_key):
            raise ValueError("Gemini credentials require an access token or API key")

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        model: Optional[str] = None,
        **_: Any,
    ) -> str:
        client = await self._ensure_client()
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        query = ""
        if self._api_key:
            query = f"?key={self._api_key}"
        response = await client.post(
            f"{GEMINI_API_URL}/{model or DEFAULT_MODEL}:generateContent{query}",
            headers=headers,
            content=json.dumps(
                {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
                }
            ),
        )
        response.raise_for_status()
        data = response.json()
        return "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])

    async def generate_stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, **kwargs)
        yield text

    async def generate_structured(self, prompt: str, schema: dict, **kwargs: Any) -> dict:
        client = await self._ensure_client()
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        query = ""
        if self._api_key:
            query = f"?key={self._api_key}"
        response = await client.post(
            f"{GEMINI_API_URL}/{kwargs.get('model', DEFAULT_MODEL)}:generateContent{query}",
            headers=headers,
            content=json.dumps(
                {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": kwargs.get("temperature", 0)},
                    "safetySettings": kwargs.get("safety_settings", []),
                    "systemInstruction": kwargs.get("system_instruction"),
                    "responseSchema": schema,
                }
            ),
        )
        response.raise_for_status()
        data = response.json()
        content = data["candidates"][0]["content"]["parts"][0].get("text", "{}")
        return json.loads(content)

    async def check_health(self) -> bool:
        return bool(self._access_token or self._api_key)

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
