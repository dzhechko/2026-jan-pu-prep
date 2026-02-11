"""Authentication router – Telegram Mini App initData flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.middleware.rate_limit import RateLimiter
from app.schemas.auth import AuthResponse, TelegramAuthRequest
from app.services.auth_service import authenticate_telegram_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 10 requests per minute per client IP
_telegram_rate_limit = RateLimiter(max_requests=10, window_seconds=60)


@router.post(
    "/telegram",
    response_model=AuthResponse,
    dependencies=[Depends(_telegram_rate_limit)],
)
async def telegram_auth(
    body: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Authenticate a user via Telegram Mini App initData.

    1. Validates the initData signature using HMAC-SHA256.
    2. Finds or creates the user in the database.
    3. Issues a JWT access token and refresh token.
    """
    return await authenticate_telegram_user(body.init_data, db)
