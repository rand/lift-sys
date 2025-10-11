"""Lightweight rate limiting middleware placeholder."""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response


class TokenBucket:
    """In-memory token bucket used for local development."""

    def __init__(self, rate: int, per_seconds: float) -> None:
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = rate
        self.updated_at = time.monotonic()

    def consume(self, tokens: int = 1) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.updated_at = now
        self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per_seconds))
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


def rate_limiter(
    max_requests: int = 60, per_seconds: float = 60.0
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    buckets: dict[str, TokenBucket] = defaultdict(lambda: TokenBucket(max_requests, per_seconds))

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        user_id = _resolve_rate_limit_key(request)
        bucket = buckets[user_id]
        if not bucket.consume():
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return await call_next(request)

    return middleware


def _resolve_rate_limit_key(request: Request) -> str:
    """Determine the token bucket key for the incoming request."""

    existing = getattr(request.state, "user_id", None)
    if existing:
        return existing

    allow_demo = getattr(request.app.state, "allow_demo_user_header", False)
    if allow_demo:
        demo_user = request.headers.get("x-demo-user")
        if demo_user:
            user_id = f"demo:{demo_user}"
            request.state.user_id = user_id
            return user_id

    session_user = request.session.get("user_id")
    if session_user:
        request.state.user_id = session_user
        return session_user

    return "anonymous"
