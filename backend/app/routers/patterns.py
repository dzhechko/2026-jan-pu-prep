"""Patterns router – discovered behavioral eating patterns."""

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.pattern import PatternsResponse

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", response_model=PatternsResponse)
async def get_patterns(
    db: DbSession,
    current_user: CurrentUser,
) -> PatternsResponse:
    """Return all active patterns for the current user, along with today's risk score."""
    # TODO: Call pattern_service.get_user_patterns()
    # TODO: Call risk_service.calculate_risk() for risk_today
    return PatternsResponse(patterns=[], risk_today=None)
