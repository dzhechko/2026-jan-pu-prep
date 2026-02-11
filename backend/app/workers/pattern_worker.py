"""RQ worker job for background pattern detection.

This job is enqueued after a new food entry is logged.  It runs the
pattern detection pipeline and persists any newly discovered patterns.
"""

import asyncio
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = structlog.get_logger()


def detect_patterns_job(user_id_str: str) -> dict:
    """RQ job entry point for pattern detection.

    Parameters
    ----------
    user_id_str:
        String representation of the user UUID (RQ serialises arguments).

    Returns
    -------
    dict
        Summary of detection results.
    """
    return asyncio.run(_detect_patterns_async(UUID(user_id_str)))


async def _detect_patterns_async(user_id: UUID) -> dict:
    """Async implementation of the pattern detection job."""
    engine = create_async_engine(settings.DATABASE_URL, pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            # Import here to avoid circular imports at module level
            from app.services.pattern_service import detect_patterns

            patterns = await detect_patterns(session, user_id)
            await session.commit()

            result = {
                "user_id": str(user_id),
                "patterns_found": len(patterns),
                "status": "completed",
            }
            logger.info("pattern_worker_done", **result)
            return result

    except Exception as exc:
        logger.error(
            "pattern_worker_error",
            user_id=str(user_id),
            error=str(exc),
        )
        return {
            "user_id": str(user_id),
            "patterns_found": 0,
            "status": "error",
            "error": str(exc),
        }
    finally:
        await engine.dispose()
