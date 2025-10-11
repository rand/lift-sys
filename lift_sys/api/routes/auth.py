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


@router.post("/{provider}/initiate")
async def initiate_oauth(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    # Demo user id for local development; production callers should authenticate.
    return await manager.initiate_oauth_flow(user_id="demo-user")


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    tokens = await manager.handle_callback(code=code, state=state)
    return {"status": "connected", "tokens": tokens}


@router.post("/{provider}/refresh")
async def refresh(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    tokens = await manager.refresh_token(user_id="demo-user")
    return {"status": "refreshed", "tokens": tokens}


@router.delete("/{provider}/disconnect")
async def disconnect(provider: str, request: Request) -> dict:
    manager = get_oauth_manager(request, provider)
    await manager.revoke_token(user_id="demo-user")
    return {"status": "disconnected"}
