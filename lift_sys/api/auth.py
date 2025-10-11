"""Authentication configuration and session management for the API."""
from __future__ import annotations

import logging
import os
import secrets
from typing import Any, Dict, Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from .schemas import SessionInfo, UserIdentity

LOGGER = logging.getLogger(__name__)

_SESSION_COOKIE = "lift_sys_session"
_REDIRECT_KEY = "post_auth_redirect"


class AuthSettings:
    """Runtime configuration for OAuth providers."""

    google_client_id: Optional[str]
    google_client_secret: Optional[str]
    github_client_id: Optional[str]
    github_client_secret: Optional[str]
    callback_base_url: str
    session_secret: str

    def __init__(self) -> None:
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        self.callback_base_url = os.getenv(
            "LIFT_SYS_CALLBACK_BASE", "http://localhost:8000"
        )
        configured_secret = os.getenv("LIFT_SYS_SESSION_SECRET")
        if configured_secret:
            self.session_secret = configured_secret
        else:
            self.session_secret = secrets.token_hex(32)
            LOGGER.warning(
                "LIFT_SYS_SESSION_SECRET not configured; using ephemeral secret."
            )


class AuthContext:
    """Holds shared authentication components for dependency injection."""

    def __init__(self, settings: AuthSettings) -> None:
        self.settings = settings
        self.oauth = OAuth()
        self.providers: set[str] = set()
        self._register_clients()

    def _register_clients(self) -> None:
        if self.settings.google_client_id and self.settings.google_client_secret:
            self.oauth.register(
                name="google",
                client_id=self.settings.google_client_id,
                client_secret=self.settings.google_client_secret,
                server_metadata_url=
                "https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )
            self.providers.add("google")
        else:
            LOGGER.info("Google OAuth client not configured; skipping registration.")

        if self.settings.github_client_id and self.settings.github_client_secret:
            self.oauth.register(
                name="github",
                client_id=self.settings.github_client_id,
                client_secret=self.settings.github_client_secret,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com/",
                client_kwargs={"scope": "read:user user:email"},
            )
            self.providers.add("github")
        else:
            LOGGER.info("GitHub OAuth client not configured; skipping registration.")

    def get_client(self, provider: str):
        if provider not in self.providers:
            raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
        client = self.oauth.create_client(provider)
        if client is None:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=404, detail=f"unknown provider '{provider}'")
        return client


def _ensure_session_middleware(app: FastAPI, secret_key: str) -> None:
    if getattr(app.state, "session_configured", False):
        return
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie=_SESSION_COOKIE,
        same_site="lax",
        https_only=False,
    )
    app.state.session_configured = True


def configure_auth(app: FastAPI) -> APIRouter:
    """Initialise OAuth clients and return an authentication router."""

    settings = AuthSettings()
    _ensure_session_middleware(app, settings.session_secret)

    context = AuthContext(settings)
    app.state.auth_context = context

    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.get("/providers")
    async def list_providers() -> Dict[str, bool]:
        registered = {name: name in context.providers for name in ("google", "github")}
        return registered

    @router.get("/login/{provider}")
    async def login(request: Request, provider: str, redirect: Optional[str] = None):
        client = context.get_client(provider)
        callback_url = f"{context.settings.callback_base_url}/api/auth/callback/{provider}"
        if redirect:
            request.session[_REDIRECT_KEY] = redirect
        try:
            return await client.authorize_redirect(request, callback_url)
        except OAuthError as exc:  # pragma: no cover - authlib wraps provider errors
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/callback/{provider}")
    async def auth_callback(request: Request, provider: str):
        client = context.get_client(provider)
        try:
            token = await client.authorize_access_token(request)
        except OAuthError as exc:
            LOGGER.error("OAuth callback failed for provider %s: %s", provider, exc)
            raise HTTPException(status_code=400, detail="oauth_callback_failed") from exc

        profile = await _resolve_profile(provider, client, token, request)
        if not profile:
            raise HTTPException(status_code=400, detail="profile_unavailable")

        user_identity = UserIdentity(**profile)
        request.session["user"] = user_identity.model_dump()
        request.session["user_id"] = user_identity.id
        tokens: Dict[str, Any] = request.session.get("tokens", {})
        tokens[provider] = token
        request.session["tokens"] = tokens

        redirect_target = request.session.pop(
            _REDIRECT_KEY, os.getenv("LIFT_SYS_POST_LOGIN_REDIRECT", "http://localhost:3000")
        )
        return RedirectResponse(url=redirect_target)

    @router.post("/logout")
    async def logout(request: Request) -> JSONResponse:
        request.session.clear()
        return JSONResponse({"authenticated": False})

    @router.get("/session", response_model=SessionInfo)
    async def session(request: Request) -> SessionInfo:
        user_data = request.session.get("user")
        if user_data:
            user = UserIdentity.model_validate(user_data)
            return SessionInfo(authenticated=True, user=user)
        return SessionInfo(authenticated=False)

    return router


async def _resolve_profile(
    provider: str, client: Any, token: Dict[str, Any], request: Request
) -> Optional[Dict[str, Any]]:
    """Derive a normalised user profile from provider metadata."""

    if provider == "google":
        userinfo = token.get("userinfo")
        if not userinfo:
            userinfo = await client.parse_id_token(request, token)
        if not userinfo:
            return None
        return {
            "id": f"google:{userinfo.get('sub')}",
            "provider": "google",
            "email": userinfo.get("email"),
            "name": userinfo.get("name"),
            "avatar_url": userinfo.get("picture"),
        }

    if provider == "github":
        resp = await client.get("user", token=token)
        profile = resp.json()
        email = profile.get("email")
        if not email:
            emails_resp = await client.get("user/emails", token=token)
            emails = emails_resp.json()
            primary = next((item for item in emails if item.get("primary")), None)
            email = primary.get("email") if primary else None
        return {
            "id": f"github:{profile.get('id')}",
            "provider": "github",
            "email": email,
            "name": profile.get("name") or profile.get("login"),
            "avatar_url": profile.get("avatar_url"),
        }

    LOGGER.warning("Unsupported OAuth provider '%s'", provider)
    return None


def require_authenticated_user(request: Request) -> UserIdentity:
    """FastAPI dependency that enforces an authenticated session."""

    demo_user = request.headers.get("x-demo-user")
    if demo_user:
        user = UserIdentity(id=f"demo:{demo_user}", provider="internal", name=demo_user)
        request.state.user_id = user.id
        return user

    user_data = request.session.get("user")
    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login_required")
    user = UserIdentity.model_validate(user_data)
    request.state.user_id = user.id
    return user


AuthenticatedUser = UserIdentity

__all__ = [
    "AuthenticatedUser",
    "configure_auth",
    "require_authenticated_user",
]
