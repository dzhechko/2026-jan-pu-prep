"""FastAPI dependency injection providers."""

from typing import Annotated, AsyncIterator
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session, rolling back on error."""
    async with request.app.state.db_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Redis connection
# ---------------------------------------------------------------------------

async def get_redis(request: Request) -> aioredis.Redis:
    """Return the shared Redis connection from application state."""
    return request.app.state.redis


# ---------------------------------------------------------------------------
# Current user extraction from JWT
# ---------------------------------------------------------------------------

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Extract and validate the JWT from the Authorization header.

    Returns a dict with at least ``user_id`` (UUID str) and
    ``telegram_id`` (int).
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Expected 'Bearer <token>'",
        )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        )

    user_id = payload.get("sub")
    telegram_id = payload.get("telegram_id")

    if not user_id or telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing required claims",
        )

    return {
        "user_id": UUID(user_id),
        "telegram_id": int(telegram_id),
    }


# ---------------------------------------------------------------------------
# Annotated shortcuts for cleaner router signatures
# ---------------------------------------------------------------------------

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[dict, Depends(get_current_user)]
RedisConn = Annotated[aioredis.Redis, Depends(get_redis)]
