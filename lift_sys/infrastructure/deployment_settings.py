"""Deployment settings and IaC helpers for Modal automation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS_PATH = Path(__file__).with_name("deployment_settings.json")


@dataclass(slots=True)
class APISettings:
    """Declarative configuration for the FastAPI worker pool."""

    replicas: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"replicas": self.replicas}

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> APISettings:
        return cls(replicas=int(data.get("replicas", 1)))


@dataclass(slots=True)
class VLLMSettings:
    """Declarative configuration for the vLLM runtime."""

    concurrency: int = 4
    gpu: str = "A10G"

    def to_dict(self) -> dict[str, Any]:
        return {"concurrency": self.concurrency, "gpu": self.gpu}

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> VLLMSettings:
        return cls(
            concurrency=int(data.get("concurrency", 4)),
            gpu=str(data.get("gpu", "A10G")),
        )


@dataclass(slots=True)
class DeploymentSettings:
    """Top-level IaC state tracked in version control."""

    api: APISettings = field(default_factory=APISettings)
    vllm: VLLMSettings = field(default_factory=VLLMSettings)

    def to_dict(self) -> dict[str, Any]:
        return {"api": self.api.to_dict(), "vllm": self.vllm.to_dict()}

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> DeploymentSettings:
        return cls(
            api=APISettings.from_mapping(data.get("api", {})),
            vllm=VLLMSettings.from_mapping(data.get("vllm", {})),
        )


def load_settings(path: Path | None = None) -> DeploymentSettings:
    """Load deployment settings from disk, falling back to defaults."""

    settings_path = path or DEFAULT_SETTINGS_PATH
    if not settings_path.exists():
        return DeploymentSettings()
    payload = json.loads(settings_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("deployment settings must be a JSON object")
    return DeploymentSettings.from_mapping(payload)


def save_settings(settings: DeploymentSettings, path: Path | None = None) -> None:
    """Persist deployment settings to disk."""

    settings_path = path or DEFAULT_SETTINGS_PATH
    settings_path.write_text(
        json.dumps(settings.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = [
    "APISettings",
    "VLLMSettings",
    "DeploymentSettings",
    "load_settings",
    "save_settings",
    "DEFAULT_SETTINGS_PATH",
]
