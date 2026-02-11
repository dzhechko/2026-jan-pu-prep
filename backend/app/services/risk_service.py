"""Risk calculation service – assess current eating behavior risk."""

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.pattern import RiskScore

logger = structlog.get_logger()


async def calculate_risk(
    db: AsyncSession,
    user_id: UUID,
) -> RiskScore | None:
    """Calculate today's risk score for a user.

    The risk model takes into account:
        - Active patterns and their confidence levels
        - Recent food entries (timing, calorie trends)
        - Historical risk model from the AI profile
        - Current time of day and day of week

    TODO:
        - Load user's AI profile with risk_model
        - Load today's food entries
        - Load active patterns
        - Call AI risk_predictor
        - Return structured risk score

    Returns ``None`` when insufficient data is available.
    """
    logger.info("risk_calculation_started", user_id=str(user_id))

    # TODO: Implement risk calculation
    # Placeholder: return None until we have enough data
    return None
