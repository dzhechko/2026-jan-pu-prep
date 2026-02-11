"""Authentication router – Telegram Mini App initData flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db
from app.middleware.rate_limit import RateLimiter
from app.schemas.auth import AuthResponse, TelegramAuthRequest, UserResponse
from app.services.auth_service import (
    authenticate_telegram_user,
    create_access_token,
    create_refresh_token,
    find_or_create_user,
)

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


if settings.APP_ENV == "development":

    @router.post("/dev", response_model=AuthResponse)
    async def dev_auth(
        db: AsyncSession = Depends(get_db),
    ) -> AuthResponse:
        """Dev-only: create/find a test user and issue JWT without Telegram initData."""
        dev_telegram_id = 123456789
        user = await find_or_create_user(
            db,
            telegram_id=dev_telegram_id,
            username="devuser",
            first_name="Dev",
            language_code="ru",
        )
        access_token = create_access_token(user.id, dev_telegram_id)
        refresh_token = create_refresh_token(user.id, dev_telegram_id)
        return AuthResponse(
            token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(
                id=user.id,
                first_name=user.first_name,
                onboarding_complete=user.onboarding_complete,
                subscription_status=user.subscription_status,
            ),
        )
