"""API router for AI Coach chat feature."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.models.user import User
from app.schemas.coach import (
    CoachHistoryResponse,
    CoachMessageRequest,
    CoachMessageResponse,
)
from app.services import coach_service

router = APIRouter(prefix="/api/coach", tags=["coach"])


async def _require_premium(db: AsyncSession, user_id: UUID) -> None:
    """Raise 403 if user is not on a premium plan."""
    user = await db.get(User, user_id)
    if not user or user.subscription_status == "free":
        raise HTTPException(
            status_code=403,
            detail="AI Коуч доступен только для Premium-подписчиков.",
        )


@router.post("/message", response_model=CoachMessageResponse)
async def send_message(
    body: CoachMessageRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> CoachMessageResponse:
    """Send a message to the AI coach and receive a response."""
    user_id: UUID = current_user["user_id"]
    await _require_premium(db, user_id)
    return await coach_service.send_message(db, user_id, body.content)


@router.get("/history", response_model=CoachHistoryResponse)
async def get_history(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = 20,
    offset: int = 0,
) -> CoachHistoryResponse:
    """Get paginated chat history."""
    user_id: UUID = current_user["user_id"]
    await _require_premium(db, user_id)
    return await coach_service.get_history(db, user_id, limit=limit, offset=offset)
