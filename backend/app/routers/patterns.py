"""Patterns router -- discovered behavioral eating patterns."""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.pattern import PatternFeedbackResponse, PatternsResponse
from app.services import pattern_service

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", response_model=PatternsResponse)
async def get_patterns(
    db: DbSession,
    current_user: CurrentUser,
) -> PatternsResponse:
    """Return all active patterns for the current user, along with today's risk score."""
    return await pattern_service.get_user_patterns(db, current_user["user_id"])


@router.post(
    "/{pattern_id}/feedback",
    response_model=PatternFeedbackResponse,
    status_code=200,
)
async def submit_pattern_feedback(
    pattern_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> PatternFeedbackResponse:
    """User disputes a pattern -- reduce confidence by 0.2, deactivate if < 0.3."""
    result = await pattern_service.submit_feedback(
        db, current_user["user_id"], pattern_id
    )
    return PatternFeedbackResponse(**result)
