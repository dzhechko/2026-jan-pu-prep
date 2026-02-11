"""Food logging router – log meals, view history."""

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbSession
from app.schemas.food import (
    FoodHistoryResponse,
    FoodLogRequest,
    FoodLogResponse,
    FoodItem,
    FoodHistoryEntry,
)

router = APIRouter(prefix="/api/food", tags=["food"])


@router.post("/log", response_model=FoodLogResponse)
async def log_food(
    body: FoodLogRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> FoodLogResponse:
    """Log a food entry from natural-language Russian text.

    The text is parsed by the AI pipeline into structured food items
    with estimated calorie counts.
    """
    # TODO: Call food_service.log_food() which will:
    #   1. Parse raw_text via AI food_parser
    #   2. Create FoodEntry record
    #   3. Enqueue pattern detection job
    import uuid

    return FoodLogResponse(
        entry_id=uuid.uuid4(),
        parsed_items=[
            FoodItem(name="placeholder", calories=0, category="unknown")
        ],
        total_calories=0,
    )


@router.get("/history", response_model=FoodHistoryResponse)
async def get_food_history(
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
) -> FoodHistoryResponse:
    """Return paginated food log history for the current user."""
    # TODO: Call food_service.get_food_history()
    return FoodHistoryResponse(entries=[], total=0)
