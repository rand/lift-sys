"""Declarative definitions for Modal image builds used by lift-sys."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass(slots=True)
class ImageSpec:
    """Serializable definition of a Modal image build."""

    name: str
    python: str = "3.11"
    system_packages: list[str] = field(default_factory=list)
    python_packages: list[str] = field(default_factory=list)
    run_commands: list[str] = field(default_factory=list)

    def with_python_packages(self, *packages: str) -> ImageSpec:
        self.python_packages.extend(packages)
        return self

    def with_run_commands(self, *commands: str) -> ImageSpec:
        self.run_commands.extend(commands)
        return self


def base_api_image() -> ImageSpec:
    """Image spec for API workloads."""

    spec = ImageSpec(name="lift-sys-api")
    spec.with_python_packages(
        "fastapi",
        "uvicorn[standard]",
        "httpx",
        "pydantic",
        "pydantic-settings",
        "cryptography",
        "anthropic",
        "openai",
        "google-generativeai",
        "modal-client",
    )
    return spec


def vllm_image() -> ImageSpec:
    """Image spec for vLLM workloads."""

    spec = ImageSpec(name="lift-sys-vllm")
    spec.with_python_packages("vllm", "outlines", "torch", "numpy")
    spec.with_run_commands(
        "huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir /models/Llama-3.1-8B-Instruct",
    )
    return spec


def iter_all_images() -> Iterable[ImageSpec]:
    """Iterate all image specs managed by the deployment."""

    yield base_api_image()
    yield vllm_image()
