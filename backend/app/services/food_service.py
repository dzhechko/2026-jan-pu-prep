"""Food logging service – parse text, persist entries, query history."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food_entry import FoodEntry
from app.schemas.food import FoodItem, FoodLogResponse, FoodHistoryEntry, FoodHistoryResponse

logger = structlog.get_logger()


async def log_food(
    db: AsyncSession,
    user_id: UUID,
    raw_text: str,
    mood: str | None = None,
    context: str | None = None,
    logged_at: datetime | None = None,
) -> FoodLogResponse:
    """Parse natural-language food text and persist the entry.

    Steps:
        1. Call AI food_parser to convert ``raw_text`` into ``FoodItem[]``.
        2. Save a ``FoodEntry`` row.
        3. Return structured response.
    """
    if logged_at is None:
        logged_at = datetime.now(timezone.utc)

    # TODO: Replace stub with actual AI food parsing
    # parsed_items = await food_parser.parse(raw_text)
    parsed_items: list[FoodItem] = []
    total_calories = 0

    entry = FoodEntry(
        user_id=user_id,
        raw_text=raw_text,
        parsed_items=[item.model_dump() for item in parsed_items],
        total_calories=total_calories,
        mood=mood,
        context=context,
        logged_at=logged_at,
        day_of_week=logged_at.weekday(),
        hour=logged_at.hour,
    )
    db.add(entry)
    await db.flush()

    logger.info("food_logged", user_id=str(user_id), entry_id=str(entry.id))

    return FoodLogResponse(
        entry_id=entry.id,
        parsed_items=parsed_items,
        total_calories=total_calories,
    )


async def parse_food_text(raw_text: str) -> list[FoodItem]:
    """Parse Russian food text into structured items.

    TODO: Integrate with AI food_parser pipeline.
    """
    return []


async def get_food_history(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
    offset: int = 0,
) -> FoodHistoryResponse:
    """Return paginated food log history for a user."""
    # Count total
    count_stmt = select(func.count()).select_from(FoodEntry).where(
        FoodEntry.user_id == user_id
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Fetch entries
    stmt = (
        select(FoodEntry)
        .where(FoodEntry.user_id == user_id)
        .order_by(desc(FoodEntry.logged_at))
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    return FoodHistoryResponse(
        entries=[
            FoodHistoryEntry(
                id=e.id,
                raw_text=e.raw_text,
                parsed_items=[FoodItem(**item) for item in (e.parsed_items or [])],
                total_calories=e.total_calories,
                mood=e.mood,
                context=e.context,
                logged_at=e.logged_at,
            )
            for e in entries
        ],
        total=total,
    )
