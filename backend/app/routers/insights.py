"""Insights router -- daily AI-generated insights."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.schemas.insight import (
    InsightData,
    InsightFeedback,
    InsightFeedbackResponse,
    InsightResponse,
)
from app.services import insight_service

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/today", response_model=InsightResponse)
async def get_today_insight(
    db: DbSession,
    current_user: CurrentUser,
) -> InsightResponse:
    """Return today's AI-generated insight for the current user.

    Free-tier users receive up to 3 insights per week; premium users
    get unlimited insights.  Locked insights are returned with
    ``is_locked=True`` and a truncated body.
    """
    return await insight_service.get_today_insight(db, current_user["user_id"])


@router.post("/generate", response_model=InsightResponse)
async def generate_insight(
    db: DbSession,
    current_user: CurrentUser,
) -> InsightResponse:
    """Trigger insight generation (for testing / manual trigger).

    Creates a new insight using the local template engine and returns it.
    """
    insight = await insight_service.generate_daily_insight(
        db, current_user["user_id"]
    )
    if not insight:
        raise HTTPException(
            status_code=500, detail="Failed to generate insight"
        )

    return InsightResponse(
        insight=InsightData(
            id=insight.id,
            title=insight.title,
            body=insight.body,
            action=insight.action,
            type=insight.type,
            created_at=insight.created_at,
        ),
        is_locked=insight.is_locked,
    )


@router.post(
    "/{insight_id}/feedback",
    response_model=InsightFeedbackResponse,
)
async def submit_feedback(
    insight_id: UUID,
    body: InsightFeedback,
    db: DbSession,
    current_user: CurrentUser,
) -> InsightFeedbackResponse:
    """Submit feedback (positive/negative) for a specific insight."""
    result = await insight_service.submit_feedback(
        db, current_user["user_id"], insight_id, body.rating
    )
    return InsightFeedbackResponse(**result)


@router.post("/{insight_id}/seen")
async def mark_seen(
    insight_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Mark an insight as seen by the user."""
    return await insight_service.mark_seen(
        db, current_user["user_id"], insight_id
    )
