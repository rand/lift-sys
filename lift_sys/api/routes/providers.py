"""Endpoints for provider management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...auth.token_store import TokenStore
from ...providers import BaseProvider

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _get_provider_registry(request: Request) -> dict[str, BaseProvider]:
    providers = getattr(request.app.state, "providers", None)
    if providers is None:
        raise HTTPException(status_code=500, detail="provider registry not configured")
    return providers


@router.get("")
async def list_providers(request: Request) -> list[dict[str, object]]:
    registry = _get_provider_registry(request)
    token_store: TokenStore | None = getattr(request.app.state, "token_store", None)
    user_id = getattr(request.state, "user_id", "demo-user")
    payload = []
    for name, provider in registry.items():
        healthy = await provider.check_health()
        payload.append(
            {
                "type": name,
                "capabilities": {
                    "streaming": provider.supports_streaming,
                    "structuredOutput": provider.supports_structured_output,
                    "reasoning": getattr(provider.capabilities, "reasoning", True),
                },
                "status": "healthy" if healthy else "unavailable",
                "authenticated": bool(token_store and name in token_store.list_providers(user_id)),
            }
        )
    return payload


@router.get("/{provider}/status")
async def provider_status(provider: str, request: Request) -> dict[str, object]:
    registry = _get_provider_registry(request)
    if provider not in registry:
        raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
    healthy = await registry[provider].check_health()
    return {"provider": provider, "healthy": healthy}


@router.put("/primary")
async def set_primary(request: Request, payload: dict[str, str]) -> dict[str, object]:
    registry = _get_provider_registry(request)
    provider = payload.get("provider")
    if provider not in registry:
        raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
    request.app.state.primary_provider = provider
    return {"status": "ok", "primary": provider}


@router.get("/current")
async def get_current(request: Request) -> dict[str, object]:
    registry = _get_provider_registry(request)
    primary = getattr(request.app.state, "primary_provider", next(iter(registry)))
    return {"primary": primary}
