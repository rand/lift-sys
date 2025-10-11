"""Encrypted token storage utilities."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from dataclasses import dataclass

from cryptography.fernet import Fernet


@dataclass(slots=True)
class StoredToken:
    """Represents a stored provider token."""

    provider: str
    payload: dict[str, object]


class TokenStore:
    """Persist OAuth tokens encrypted at rest using Fernet symmetric encryption."""

    def __init__(self, storage: MutableMapping[str, str], encryption_key: bytes) -> None:
        self._storage = storage
        self._fernet = Fernet(encryption_key)

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new Fernet key for encryption."""

        return Fernet.generate_key()

    def _key(self, user_id: str, provider: str) -> str:
        return f"{user_id}:{provider}"

    def save_tokens(self, user_id: str, provider: str, payload: dict[str, object]) -> None:
        serialized = json.dumps(payload).encode("utf-8")
        token = self._fernet.encrypt(serialized).decode("utf-8")
        self._storage[self._key(user_id, provider)] = token

    def load_tokens(self, user_id: str, provider: str) -> dict[str, object] | None:
        token = self._storage.get(self._key(user_id, provider))
        if not token:
            return None
        decrypted = self._fernet.decrypt(token.encode("utf-8"))
        return json.loads(decrypted.decode("utf-8"))

    def delete_tokens(self, user_id: str, provider: str) -> None:
        self._storage.pop(self._key(user_id, provider), None)

    def list_providers(self, user_id: str) -> list[str]:
        prefix = f"{user_id}:"
        return [key.split(":", 1)[1] for key in self._storage.keys() if key.startswith(prefix)]
