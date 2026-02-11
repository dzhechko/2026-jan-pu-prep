"""Food logging router -- log meals, view history."""

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.dependencies import CurrentUser, DbSession
from app.models.food_entry import FoodEntry
from app.schemas.food import (
    FoodHistoryResponse,
    FoodLogRequest,
    FoodLogResponse,
)
from app.services import food_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/food", tags=["food"])


@router.post("/log", response_model=FoodLogResponse, status_code=201)
async def log_food(
    body: FoodLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> FoodLogResponse:
    """Log a food entry from natural-language Russian text.

    The text is parsed by the AI pipeline into structured food items
    with estimated calorie counts.
    """
    result = await food_service.log_food(
        db=db,
        user_id=current_user["user_id"],
        raw_text=body.raw_text,
        mood=body.mood,
        context=body.context,
        logged_at=body.logged_at,
    )

    # After logging food, check if this is the 10th entry -- trigger pattern detection
    try:
        count_stmt = (
            select(func.count())
            .select_from(FoodEntry)
            .where(FoodEntry.user_id == current_user["user_id"])
        )
        count_result = await db.execute(count_stmt)
        entry_count = count_result.scalar_one()

        if entry_count == 10:
            try:
                from rq import Queue
                from redis import Redis
                from app.config import settings

                q = Queue("ai_heavy", connection=Redis.from_url(settings.REDIS_URL))
                q.enqueue(
                    "app.workers.pattern_worker.detect_patterns_job",
                    str(current_user["user_id"]),
                )
                logger.info(
                    "pattern_detection_enqueued",
                    user_id=str(current_user["user_id"]),
                    entry_count=entry_count,
                )
            except Exception:
                pass  # Non-critical, patterns will be detected on daily cron
    except Exception:
        pass  # Non-critical -- don't break food logging if count check fails

    return result


@router.get("/history", response_model=FoodHistoryResponse)
async def get_food_history(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> FoodHistoryResponse:
    """Return paginated food log history for the current user."""
    return await food_service.get_food_history(
        db=db,
        user_id=current_user["user_id"],
        limit=limit,
        offset=offset,
    )
