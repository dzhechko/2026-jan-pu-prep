"""RQ worker job for background insight generation.

This job is typically scheduled daily (e.g., via cron or RQ-scheduler)
to generate fresh insights for active users.
"""

import asyncio
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

logger = structlog.get_logger()


def generate_insight_job(user_id_str: str) -> dict:
    """RQ job entry point for insight generation.

    Parameters
    ----------
    user_id_str:
        String representation of the user UUID.

    Returns
    -------
    dict
        Summary of generation results.
    """
    return asyncio.run(_generate_insight_async(UUID(user_id_str)))


async def _generate_insight_async(user_id: UUID) -> dict:
    """Async implementation of the insight generation job."""
    engine = create_async_engine(settings.DATABASE_URL, pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            from app.services.insight_service import generate_daily_insight

            insight = await generate_daily_insight(session, user_id)
            await session.commit()

            result = {
                "user_id": str(user_id),
                "insight_generated": insight is not None,
                "insight_id": str(insight.id) if insight else None,
                "status": "completed",
            }
            logger.info("insight_worker_done", **result)
            return result

    except Exception as exc:
        logger.error(
            "insight_worker_error",
            user_id=str(user_id),
            error=str(exc),
        )
        return {
            "user_id": str(user_id),
            "insight_generated": False,
            "status": "error",
            "error": str(exc),
        }
    finally:
        await engine.dispose()
