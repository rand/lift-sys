"""Provider OAuth configuration models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(slots=True)
class OAuthClientConfig:
    """Configuration for initiating OAuth flows."""

    provider: str
    client_id: str
    authorization_url: str
    token_url: str
    scopes: tuple[str, ...]
    redirect_uri: str
    additional_params: Mapping[str, str]
    use_pkce: bool = False
    service_account_key: str | None = None


def build_default_configs(base_redirect_uri: str) -> dict[str, OAuthClientConfig]:
    """Return default configuration stubs for each provider."""

    return {
        "anthropic": OAuthClientConfig(
            provider="anthropic",
            client_id="",
            authorization_url="https://console.anthropic.com/oauth/authorize",
            token_url="https://api.anthropic.com/oauth/token",
            scopes=("api",),
            redirect_uri=f"{base_redirect_uri}/anthropic/callback",
            additional_params={},
            use_pkce=True,
        ),
        "openai": OAuthClientConfig(
            provider="openai",
            client_id="",
            authorization_url="https://auth.openai.com/authorize",
            token_url="https://api.openai.com/oauth/token",
            scopes=("api.read", "api.write"),
            redirect_uri=f"{base_redirect_uri}/openai/callback",
            additional_params={},
        ),
        "gemini": OAuthClientConfig(
            provider="gemini",
            client_id="",
            authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes=("https://www.googleapis.com/auth/generative-language",),
            redirect_uri=f"{base_redirect_uri}/gemini/callback",
            additional_params={"access_type": "offline", "prompt": "consent"},
            use_pkce=True,
        ),
    }
