"""Authentication router – Telegram Mini App initData flow."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.auth import AuthResponse, TelegramAuthRequest
from app.services.auth_service import authenticate_telegram_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
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
