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
        user_id = getattr(request.state, "user_id", "anonymous")
        bucket = buckets[user_id]
        if not bucket.consume():
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        return await call_next(request)

    return middleware
