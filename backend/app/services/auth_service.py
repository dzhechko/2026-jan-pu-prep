"""Authentication service – Telegram initData validation, JWT, user management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.middleware.telegram_auth import validate_init_data
from app.models.user import User
from app.schemas.auth import AuthResponse, UserResponse

logger = structlog.get_logger()


def create_access_token(user_id: UUID, telegram_id: int) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, telegram_id: int) -> str:
    """Create a signed JWT refresh token with a longer expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "telegram_id": telegram_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def find_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str = "",
    language_code: str = "ru",
) -> User:
    """Look up a user by ``telegram_id``; create one if it does not exist.

    On subsequent logins the profile fields are refreshed from Telegram data.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
            first_name=first_name,
            language_code=language_code,
        )
        db.add(user)
        await db.flush()
        logger.info("user_created", telegram_id=telegram_id, user_id=str(user.id))
    else:
        # Refresh profile fields that may have changed on the Telegram side
        user.telegram_username = username
        user.first_name = first_name or user.first_name
        user.language_code = language_code or user.language_code
        await db.flush()
        logger.info("user_logged_in", telegram_id=telegram_id, user_id=str(user.id))

    return user


async def authenticate_telegram_user(
    init_data_raw: str,
    db: AsyncSession,
) -> AuthResponse:
    """Full authentication flow.

    1. Validate Telegram initData signature.
    2. Extract user info.
    3. Find or create the user.
    4. Issue JWT tokens.
    """
    # Step 1 – Validate signature
    parsed = validate_init_data(init_data_raw, settings.TELEGRAM_BOT_TOKEN)

    # Step 2 – Extract user fields
    tg_user: dict = parsed.get("user", {})
    if not tg_user:
        raise ValueError("initData does not contain a user object")

    telegram_id: int = tg_user["id"]
    username: str | None = tg_user.get("username")
    first_name: str = tg_user.get("first_name", "")
    language_code: str = tg_user.get("language_code", "ru")

    # Step 3 – Find or create
    user = await find_or_create_user(
        db,
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        language_code=language_code,
    )

    # Step 4 – Issue tokens
    access_token = create_access_token(user.id, telegram_id)
    refresh_token = create_refresh_token(user.id, telegram_id)

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
