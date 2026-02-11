"""Pattern detection service – discover behavioral eating patterns."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pattern import Pattern
from app.schemas.pattern import PatternData, PatternsResponse

logger = structlog.get_logger()


async def detect_patterns(db: AsyncSession, user_id: UUID) -> list[Pattern]:
    """Run the pattern detection pipeline for a user.

    This is typically called as a background job after new food entries
    are logged.

    TODO:
        - Fetch recent food entries for the user
        - Call AI pattern_detector to identify new patterns
        - Compare against existing active patterns (dedup)
        - Persist new patterns and deactivate stale ones
        - Return newly discovered patterns
    """
    logger.info("pattern_detection_started", user_id=str(user_id))
    # TODO: Implement pattern detection logic
    return []


async def get_user_patterns(
    db: AsyncSession,
    user_id: UUID,
) -> PatternsResponse:
    """Return all active patterns for a user."""
    stmt = (
        select(Pattern)
        .where(Pattern.user_id == user_id, Pattern.active.is_(True))
        .order_by(Pattern.confidence.desc())
    )
    result = await db.execute(stmt)
    patterns = result.scalars().all()

    return PatternsResponse(
        patterns=[
            PatternData(
                id=p.id,
                type=p.type,
                description_ru=p.description_ru,
                confidence=p.confidence,
                discovered_at=p.discovered_at,
            )
            for p in patterns
        ],
        risk_today=None,  # TODO: integrate risk_service.calculate_risk()
    )
