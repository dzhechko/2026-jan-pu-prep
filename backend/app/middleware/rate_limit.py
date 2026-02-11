"""Reusable Redis-based rate limiter — FastAPI dependency.

Uses a simple counter with TTL (fixed window) per client IP + endpoint.
"""

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status


class RateLimiter:
    """Callable dependency that enforces per-IP rate limits via Redis.

    Parameters
    ----------
    max_requests:
        Maximum number of requests allowed within *window_seconds*.
    window_seconds:
        Length of the rate-limit window in seconds.

    Usage::

        _telegram_rate = RateLimiter(max_requests=10, window_seconds=60)

        @router.post("/telegram", dependencies=[Depends(_telegram_rate)])
        async def telegram_auth(...): ...
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        redis: aioredis.Redis = request.app.state.redis

        client_ip = request.client.host if request.client else "unknown"
        endpoint = request.url.path
        key = f"rate:{client_ip}:{endpoint}"

        # INCR atomically creates the key if it doesn't exist (starting at 1).
        current_count: int = await redis.incr(key)

        if current_count == 1:
            # First request in this window — set the TTL.
            await redis.expire(key, self.window_seconds)

        if current_count > self.max_requests:
            # Determine how many seconds remain until the window resets.
            ttl = await redis.ttl(key)
            retry_after = ttl if ttl > 0 else self.window_seconds

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
