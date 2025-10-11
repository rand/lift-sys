"""Modal configuration helpers for lift-sys."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cached_property


@dataclass(slots=True)
class ModalSecretRef:
    """Reference to a Modal secret by name."""

    name: str


@dataclass(slots=True)
class ModalDictRef:
    """Reference to a Modal Dict used for token storage."""

    name: str


@dataclass(slots=True)
class ModalVolumeRef:
    """Reference to a Modal Volume used for shared assets."""

    name: str
    create_if_missing: bool = True


@dataclass(slots=True)
class ModalAppConfig:
    """Configuration values required to bootstrap the Modal deployment."""

    app_name: str = "lift-sys"
    region: str = field(default_factory=lambda: os.getenv("LIFT_SYS_MODAL_REGION", "us-east-1"))
    token_store_dict: ModalDictRef = field(
        default_factory=lambda: ModalDictRef(
            os.getenv("LIFT_SYS_MODAL_TOKEN_DICT", "lift-sys-token-store")
        )
    )
    user_preferences_dict: ModalDictRef = field(
        default_factory=lambda: ModalDictRef(
            os.getenv("LIFT_SYS_MODAL_PREFS_DICT", "lift-sys-user-prefs")
        )
    )
    model_volume: ModalVolumeRef = field(
        default_factory=lambda: ModalVolumeRef(
            os.getenv("LIFT_SYS_MODAL_MODEL_VOLUME", "lift-sys-models")
        )
    )
    api_secrets: Mapping[str, ModalSecretRef] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> ModalAppConfig:
        """Build configuration, auto-discovering provider secret references."""

        secret_mapping: dict[str, ModalSecretRef] = {}
        prefix = "LIFT_SYS_MODAL_SECRET_"
        for key, value in os.environ.items():
            if key.startswith(prefix) and value:
                secret_mapping[key[len(prefix) :].lower()] = ModalSecretRef(value)
        return cls(api_secrets=secret_mapping)

    @cached_property
    def all_secret_names(self) -> tuple[str, ...]:
        """Return the set of unique Modal secret names required by the app."""

        return tuple(sorted({secret.name for secret in self.api_secrets.values()}))

    def require_secret(self, key: str) -> ModalSecretRef:
        """Lookup a secret reference and raise if missing."""

        if key not in self.api_secrets:
            raise KeyError(
                f"secret '{key}' is not configured; set LIFT_SYS_MODAL_SECRET_{key.upper()}"
            )
        return self.api_secrets[key]


def iter_default_secrets() -> Iterable[str]:
    """Return logical secret keys that the deployment expects by default."""

    return ("anthropic", "openai", "gemini", "oauth")
