"""Food logging router – log meals, view history."""

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.schemas.food import (
    FoodHistoryResponse,
    FoodLogRequest,
    FoodLogResponse,
)
from app.services import food_service

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
    return await food_service.log_food(
        db=db,
        user_id=current_user["user_id"],
        raw_text=body.raw_text,
        mood=body.mood,
        context=body.context,
        logged_at=body.logged_at,
    )


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
