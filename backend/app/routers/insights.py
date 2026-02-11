"""Insights router – daily AI-generated insights."""

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.insight import InsightData, InsightResponse

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
    # TODO: Call insight_service.get_today_insight()
    # TODO: Check subscription and lock logic
    import uuid
    from datetime import datetime, timezone

    return InsightResponse(
        insight=InsightData(
            id=uuid.uuid4(),
            title="Your insight is being prepared",
            body="Log a few more meals and we will generate your first personalized insight.",
            action=None,
            type="general",
            created_at=datetime.now(timezone.utc),
        ),
        is_locked=False,
    )
