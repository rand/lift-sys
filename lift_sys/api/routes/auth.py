"""Authentication endpoints for provider OAuth flows."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...auth.oauth_manager import OAuthManager

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_oauth_manager(request: Request, provider: str) -> OAuthManager:
    managers = getattr(request.app.state, "oauth_managers", None)
    if managers is None or provider not in managers:
        raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
    return managers[provider]


async def _initialize_provider(request: Request, provider: str, credentials: dict) -> None:
    registry = getattr(request.app.state, "providers", None)
    if registry is None or provider not in registry:
        raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
    try:
        await registry[provider].initialize(credentials)
    except Exception as exc:  # pragma: no cover - defensive rethrow
        raise HTTPException(
            status_code=400,
            detail=f"failed to initialize provider '{provider}': {exc}",
        ) from exc


def _resolve_user_id(request: Request) -> str:
    return getattr(
        request.state,
        "user_id",
        getattr(request.app.state, "default_user_id", "demo-user"),
    )


@router.post("/{provider}/initiate")
async def initiate_oauth(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    user_id = _resolve_user_id(request)
    return await manager.initiate_oauth_flow(user_id=user_id)


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    tokens = await manager.handle_callback(code=code, state=state)
    await _initialize_provider(request, provider, tokens)
    return {"status": "connected", "tokens": tokens}


@router.post("/{provider}/refresh")
async def refresh(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    user_id = _resolve_user_id(request)
    tokens = await manager.refresh_token(user_id=user_id)
    await _initialize_provider(request, provider, tokens)
    return {"status": "refreshed", "tokens": tokens}


@router.delete("/{provider}/disconnect")
async def disconnect(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    user_id = _resolve_user_id(request)
    await manager.revoke_token(user_id=user_id)
    return {"status": "disconnected"}
