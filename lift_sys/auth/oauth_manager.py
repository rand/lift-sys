"""OAuth flow management for provider integrations."""

from __future__ import annotations

import base64
import hashlib
import secrets
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from urllib.parse import urlencode

import httpx

from .provider_configs import OAuthClientConfig
from .token_store import TokenStore


@dataclass(slots=True)
class OAuthState:
    """Persisted state metadata."""

    user_id: str
    code_verifier: str | None = None


@dataclass(slots=True)
class OAuthManager:
    """Coordinates OAuth flows for a provider."""

    provider: str
    client_config: OAuthClientConfig
    token_store: TokenStore
    state_storage: MutableMapping[str, OAuthState] = field(default_factory=dict)
    _http_client: httpx.AsyncClient | None = None

    async def initiate_oauth_flow(self, user_id: str) -> dict[str, str]:
        """Return the authorization URL and state for the provider."""

        state = secrets.token_urlsafe(24)
        code_verifier = None
        challenge_param = {}
        if self.client_config.use_pkce:
            code_verifier = secrets.token_urlsafe(96)
            challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            code_challenge = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode("ascii")
            challenge_param = {
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        self.state_storage[state] = OAuthState(user_id=user_id, code_verifier=code_verifier)
        query = {
            "response_type": "code",
            "client_id": self.client_config.client_id,
            "redirect_uri": self.client_config.redirect_uri,
            "scope": " ".join(self.client_config.scopes),
            "state": state,
        }
        query.update(self.client_config.additional_params)
        query.update(challenge_param)
        return {
            "state": state,
            "auth_url": f"{self.client_config.authorization_url}?{urlencode(query)}",
        }

    async def handle_callback(self, code: str, state: str) -> dict[str, object]:
        """Exchange an authorization code for tokens and persist them."""

        state_data = self.state_storage.pop(state, None)
        if state_data is None:
            raise ValueError("invalid or expired OAuth state")
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_config.client_id,
            "redirect_uri": self.client_config.redirect_uri,
            "code": code,
        }
        if state_data.code_verifier:
            data["code_verifier"] = state_data.code_verifier
        tokens = await self._post_token_request(data)
        self.token_store.save_tokens(state_data.user_id, self.provider, tokens)
        return tokens

    async def refresh_token(self, user_id: str) -> dict[str, object]:
        """Refresh an access token using the stored refresh token."""

        payload = self.token_store.load_tokens(user_id, self.provider)
        if payload is None or "refresh_token" not in payload:
            raise ValueError("no refresh token available for provider")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": payload["refresh_token"],
            "client_id": self.client_config.client_id,
        }
        tokens = await self._post_token_request(data)
        payload.update(tokens)
        self.token_store.save_tokens(user_id, self.provider, payload)
        return payload

    async def revoke_token(self, user_id: str) -> None:
        """Remove stored credentials for the provider."""

        self.token_store.delete_tokens(user_id, self.provider)

    async def _post_token_request(self, data: dict[str, object]) -> dict[str, object]:
        client = await self._ensure_client()
        response = await client.post(self.client_config.token_url, data=data)
        response.raise_for_status()
        return response.json()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
