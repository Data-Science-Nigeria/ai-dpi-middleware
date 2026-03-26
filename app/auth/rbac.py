"""Role-based access control dependency."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.auth.oauth import get_current_user


def require_roles(*roles: str):
    """Return a dependency that enforces the caller has at least one of the given roles."""

    async def _check(user: dict = Depends(get_current_user)) -> dict:
        token_roles: list[str] = user.get("roles", [])
        if not any(r in token_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role(s): {list(roles)}",
            )
        return user

    return _check
