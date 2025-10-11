from __future__ import annotations

import asyncio
import json

import pytest
import pytest_asyncio

from lift_sys.providers.base import BaseProvider, ProviderCapabilities
from lift_sys.providers.local_vllm_provider import LocalVLLMProvider
from lift_sys.services.orchestrator import HybridOrchestrator, Task


class StubExternalProvider(BaseProvider):
    def __init__(self) -> None:
        super().__init__("stub", ProviderCapabilities(streaming=True, structured_output=False, reasoning=True))
        self.calls: list[str] = []

    async def initialize(self, credentials: dict) -> None:  # pragma: no cover - unused path
        pass

    async def generate_text(self, prompt: str, **_: dict) -> str:
        self.calls.append(prompt)
        return f"external:{prompt}"

    async def generate_stream(self, prompt: str, **kwargs: dict):  # pragma: no cover - unused in tests
        yield await self.generate_text(prompt, **kwargs)

    async def generate_structured(self, prompt: str, schema: dict, **kwargs: dict):  # pragma: no cover
        raise NotImplementedError

    async def check_health(self) -> bool:
        return True

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_structured_output(self) -> bool:
        return False


@pytest_asyncio.fixture
async def local_provider() -> LocalVLLMProvider:
    async def structured_runner(prompt: str, payload: dict) -> str:
        schema = payload["schema"]
        return json.dumps({"prompt": prompt, "schema": schema})

    provider = LocalVLLMProvider(structured_runner=structured_runner, text_runner=lambda p, _: asyncio.sleep(0, result=p))
    await provider.initialize({})
    return provider


@pytest.mark.asyncio
async def test_structured_task_routes_to_local(local_provider: LocalVLLMProvider) -> None:
    external = StubExternalProvider()
    orchestrator = HybridOrchestrator(external, local_provider)
    task = Task(prompt="generate", requires_constrained_output=True, output_schema={"type": "object"})
    result = await orchestrator.execute_task(task)
    assert result.provider == "local"
    assert "schema" in result.content


@pytest.mark.asyncio
async def test_reasoning_task_uses_external(local_provider: LocalVLLMProvider) -> None:
    external = StubExternalProvider()
    orchestrator = HybridOrchestrator(external, local_provider)
    task = Task(prompt="plan", requires_reasoning=True)
    result = await orchestrator.execute_task(task)
    assert result.provider == "stub"
    assert result.content == "external:plan"


@pytest.mark.asyncio
async def test_fallback_to_local_on_error(local_provider: LocalVLLMProvider) -> None:
    class ErrorProvider(StubExternalProvider):
        async def generate_text(self, prompt: str, **_: dict) -> str:
            raise RuntimeError("boom")

    external = ErrorProvider()
    orchestrator = HybridOrchestrator(external, local_provider)
    task = Task(prompt="fallback")
    result = await orchestrator.execute_task(task)
    assert result.provider == "local"
    assert result.content == "fallback"
