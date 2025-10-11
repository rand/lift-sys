"""Simple authentication middleware placeholder."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response


async def attach_demo_user(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Attach a demo user id for local development until SSO is wired."""

    request.state.user_id = "demo-user"
    return await call_next(request)
