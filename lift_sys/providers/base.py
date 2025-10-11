"""Provider abstraction for lift-sys."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(slots=True)
class ProviderCapabilities:
    """Capabilities reported by a provider implementation."""

    streaming: bool
    structured_output: bool
    reasoning: bool = True


class BaseProvider(ABC):
    """Abstract base class encapsulating provider specific logic."""

    name: str
    capabilities: ProviderCapabilities

    def __init__(self, name: str, capabilities: ProviderCapabilities) -> None:
        self.name = name
        self.capabilities = capabilities

    @abstractmethod
    async def initialize(self, credentials: dict) -> None:
        """Initialize provider with a credentials payload."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Return a text completion for the supplied prompt."""

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Yield tokens of a streaming completion."""

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        **kwargs,
    ) -> dict:
        """Return structured content following the requested schema."""

    @abstractmethod
    async def check_health(self) -> bool:
        """Return whether the provider is currently healthy."""

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether streaming generation is available."""

    @property
    @abstractmethod
    def supports_structured_output(self) -> bool:
        """Whether structured generation is supported."""

    @property
    def provider_type(self) -> str:
        """Return provider identifier string."""

        return self.name

    async def ensure_initialized(self, credentials: dict | None) -> None:
        """Ensure provider is initialized with credentials."""

        if credentials is None:
            raise ValueError(f"no credentials supplied for provider '{self.name}'")
        await self.initialize(credentials)
