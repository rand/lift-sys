"""Modal.com provider for constrained IR generation with vLLM + XGrammar."""

from __future__ import annotations

from typing import Any

import httpx

from .base import BaseProvider, ProviderCapabilities


class ModalProvider(BaseProvider):
    """Provider that uses Modal.com for GPU-accelerated constrained generation."""

    def __init__(self, endpoint_url: str):
        """
        Initialize Modal provider.

        Args:
            endpoint_url: URL to the generate endpoint (e.g., https://rand--generate.modal.run)
                         For label-based URLs, this should be the direct generate endpoint URL.
        """
        super().__init__(
            name="modal",
            capabilities=ProviderCapabilities(
                streaming=False,
                structured_output=True,  # XGrammar enables schema-constrained generation
                reasoning=True,
            ),
        )
        self.endpoint_url = endpoint_url.rstrip("/")

        # For label-based URLs, derive health URL from generate URL
        # https://rand--generate.modal.run -> https://rand--health.modal.run
        if "--generate" in endpoint_url:
            self.health_url = endpoint_url.replace("--generate", "--health")
        else:
            # Fallback for path-based URLs
            self.health_url = endpoint_url.replace("/generate", "/health")

        self._client: httpx.AsyncClient | None = None

    async def initialize(self, credentials: dict[str, Any]) -> None:
        """Initialize HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=180.0,  # 3 minutes for cold starts (model loading)
            follow_redirects=True,
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> dict:
        """
        Generate structured output matching JSON schema using XGrammar constraints.

        Args:
            prompt: Natural language specification
            schema: JSON schema to enforce during generation
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            **kwargs: Additional parameters (top_p, etc.)

        Returns:
            Generated IR matching the schema

        Raises:
            RuntimeError: If Modal provider not initialized
            httpx.HTTPStatusError: If API request fails
        """
        if not self._client:
            raise RuntimeError("Modal provider not initialized. Call initialize() first.")

        response = await self._client.post(
            self.endpoint_url,  # Direct endpoint URL (label-based or path-based)
            json={
                "prompt": prompt,
                "schema": schema,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": kwargs.get("top_p", 0.95),
            },
        )
        response.raise_for_status()

        result = response.json()

        # Check for errors in the response
        if "error" in result:
            raise ValueError(f"Modal inference error: {result['error']}")

        return result["ir_json"]

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate freeform text (not recommended for Modal - use Anthropic instead).

        Modal is optimized for constrained generation. For general text generation,
        use AnthropicProvider instead.
        """
        raise NotImplementedError(
            "Modal provider is optimized for constrained IR generation only. "
            "Use AnthropicProvider for general text generation."
        )

    async def check_health(self) -> bool:
        """
        Check if Modal endpoint is reachable and healthy.

        Note: Health endpoint is lightweight and doesn't trigger GPU/model loading.
        """
        if not self._client:
            return False

        try:
            response = await self._client.get(
                self.health_url,  # Use dedicated health URL
                timeout=10.0,  # Allow time for cold start
            )
            return response.status_code == 200
        except Exception:
            return False

    async def aclose(self) -> None:
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            self._client = None


__all__ = ["ModalProvider"]
