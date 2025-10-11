"""Local vLLM provider used for constrained generation."""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, Optional

from .base import BaseProvider, ProviderCapabilities


StructuredRunner = Callable[[str, dict], Awaitable[str]]
TextRunner = Callable[[str, dict], Awaitable[str]]


class LocalVLLMProvider(BaseProvider):
    """Adapter for invoking a Modal hosted vLLM worker."""

    def __init__(
        self,
        structured_runner: Optional[StructuredRunner] = None,
        text_runner: Optional[TextRunner] = None,
    ) -> None:
        super().__init__(
            name="local",
            capabilities=ProviderCapabilities(streaming=False, structured_output=True, reasoning=False),
        )
        self._structured_runner = structured_runner
        self._text_runner = text_runner
        self._initialized = False

    async def initialize(self, credentials: Dict[str, Any]) -> None:  # noqa: D401 - credentials retained for compatibility
        self._initialized = True

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        if self._text_runner is None:
            raise RuntimeError("Local vLLM text generation runner not configured")
        payload = {"max_tokens": max_tokens, "temperature": temperature}
        payload.update(kwargs)
        return await self._text_runner(prompt, payload)

    async def generate_stream(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.generate_text(prompt, **kwargs)
        yield text

    async def generate_structured(self, prompt: str, schema: dict, **kwargs: Any) -> dict:
        if self._structured_runner is None:
            raise RuntimeError("Local vLLM structured runner not configured")
        payload = dict(kwargs)
        payload["schema"] = schema
        text = await self._structured_runner(prompt, payload)
        if isinstance(text, str):
            return json.loads(text)
        return text

    async def check_health(self) -> bool:
        return self._initialized and self._structured_runner is not None

    @property
    def supports_streaming(self) -> bool:
        return False

    @property
    def supports_structured_output(self) -> bool:
        return True
