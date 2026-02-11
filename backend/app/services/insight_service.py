"""Insight generation service – daily AI insights for users."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insight import Insight
from app.models.user import User
from app.schemas.insight import InsightData, InsightResponse

logger = structlog.get_logger()

# Free-tier weekly insight limit
FREE_WEEKLY_INSIGHT_LIMIT = 3


async def generate_daily_insight(db: AsyncSession, user_id: UUID) -> Insight | None:
    """Generate a new insight for the user using the AI pipeline.

    This is typically called as a background job.

    TODO:
        - Load user's active patterns and recent food entries
        - Call AI insight_generator with user context
        - Persist the insight
        - Increment user.insights_received
        - Return the new insight
    """
    logger.info("insight_generation_started", user_id=str(user_id))
    # TODO: Implement insight generation with LLM
    return None


async def get_today_insight(
    db: AsyncSession,
    user_id: UUID,
) -> InsightResponse:
    """Return today's insight for the user.

    If the user is on the free tier and has exceeded the weekly limit,
    the insight is returned with ``is_locked=True``.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Try to find today's insight
    stmt = (
        select(Insight)
        .where(
            and_(
                Insight.user_id == user_id,
                Insight.created_at >= today_start,
            )
        )
        .order_by(Insight.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    insight = result.scalar_one_or_none()

    if insight is None:
        # No insight yet today – return placeholder
        return InsightResponse(
            insight=InsightData(
                id=user_id,  # placeholder
                title="Your insight is being prepared",
                body="Log a few more meals and we will generate your first personalized insight.",
                action=None,
                type="general",
                created_at=datetime.now(timezone.utc),
            ),
            is_locked=False,
        )

    # Check subscription for locking
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    is_locked = False
    if user and user.subscription_status == "free":
        is_locked = insight.is_locked

    return InsightResponse(
        insight=InsightData(
            id=insight.id,
            title=insight.title,
            body=insight.body if not is_locked else insight.body[:100] + "...",
            action=insight.action,
            type=insight.type,
            created_at=insight.created_at,
        ),
        is_locked=is_locked,
    )
