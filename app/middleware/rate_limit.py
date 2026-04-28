"""Redis-backed sliding-window rate limiter dependency."""

from __future__ import annotations

import time

from fastapi import Depends, HTTPException, status

from app.auth.rbac import require_roles
from app.services import redis as redis_service

_KEY_PREFIX = "ratelimit"


def stt_rate_limit(user_limit: int, admin_limit: int):
    """Return a FastAPI dependency that enforces per-role, per-minute rate limits.

    The window is a 60-second tumbling window keyed to the current UTC minute.
    Counters are stored in Redis and expire automatically after the window closes.

    Args:
        user_limit:  Maximum requests per minute for the ``user`` role.
        admin_limit: Maximum requests per minute for the ``admin`` role.
    """

    async def _check(user: dict = Depends(require_roles("user", "admin"))) -> dict:
        roles: list[str] = user.get("roles", [])
        limit = admin_limit if "admin" in roles else user_limit

        sub: str = user.get("sub", "anonymous")
        window = int(time.time() // 60)          # current UTC minute bucket
        key = f"{_KEY_PREFIX}:stt:{sub}:{window}"

        redis = redis_service.get_client()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)          # expire after the window ends

        if count > limit:
            role_label = "admin" if "admin" in roles else "user"
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded. {role_label.capitalize()} accounts are "
                    f"allowed {limit} STT request(s) per minute."
                ),
                headers={"Retry-After": "60"},
            )

        return user

    return _check
