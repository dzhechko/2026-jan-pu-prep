"""Food logging service – parse text, persist entries, query history."""

import re
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food_entry import FoodEntry
from app.schemas.food import FoodItem, FoodLogResponse, FoodHistoryEntry, FoodHistoryResponse

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Local Russian food database – fallback when OpenAI is unavailable
# ---------------------------------------------------------------------------

RUSSIAN_FOOD_DB: dict[str, dict[str, int | str]] = {
    "борщ": {"calories": 150, "category": "green"},
    "хлеб": {"calories": 80, "category": "yellow"},
    "каша": {"calories": 200, "category": "yellow"},
    "гречка": {"calories": 180, "category": "yellow"},
    "овсянка": {"calories": 150, "category": "yellow"},
    "салат": {"calories": 50, "category": "green"},
    "курица": {"calories": 250, "category": "yellow"},
    "рис": {"calories": 200, "category": "yellow"},
    "макароны": {"calories": 300, "category": "yellow"},
    "яйцо": {"calories": 70, "category": "green"},
    "яблоко": {"calories": 52, "category": "green"},
    "банан": {"calories": 105, "category": "yellow"},
    "шоколад": {"calories": 540, "category": "orange"},
    "пельмени": {"calories": 350, "category": "orange"},
    "суп": {"calories": 100, "category": "green"},
    "чай": {"calories": 5, "category": "green"},
    "кофе": {"calories": 30, "category": "green"},
    "молоко": {"calories": 60, "category": "green"},
    "сыр": {"calories": 350, "category": "orange"},
    "колбаса": {"calories": 300, "category": "orange"},
    "огурец": {"calories": 15, "category": "green"},
    "помидор": {"calories": 20, "category": "green"},
    "картошка": {"calories": 130, "category": "yellow"},
    "тофу": {"calories": 80, "category": "green"},
    "пицца": {"calories": 270, "category": "orange"},
    "бутерброд": {"calories": 250, "category": "yellow"},
}

# Pre-compiled pattern for splitting food text by common Russian delimiters
_SPLIT_PATTERN = re.compile(r"\s*(?:,\s*|\s+и\s+|\s+с\s+|\+)\s*")


async def parse_food_text(raw_text: str) -> list[FoodItem]:
    """Parse Russian food text into structured items.

    Strategy:
        1. Split *raw_text* by common delimiters (``", "``, ``" и "``, ``" с "``, ``"+"``)
        2. For each token, try a case-insensitive lookup in the local DB.
        3. If not found locally, attempt the AI food parser (may fail without API key).
        4. If the AI parser also fails, create an item with ``calories=0, category="yellow"``.
    """
    tokens = _SPLIT_PATTERN.split(raw_text.strip())
    tokens = [t.strip() for t in tokens if t.strip()]

    items: list[FoodItem] = []
    # Collect tokens not found in local DB for a single AI call
    unknown_tokens: list[str] = []

    for token in tokens:
        lookup_key = token.lower()
        if lookup_key in RUSSIAN_FOOD_DB:
            entry = RUSSIAN_FOOD_DB[lookup_key]
            items.append(
                FoodItem(
                    name=token,
                    calories=int(entry["calories"]),
                    category=str(entry["category"]),
                )
            )
        else:
            unknown_tokens.append(token)

    # Try AI parser for unknown tokens
    if unknown_tokens:
        try:
            from app.ai.food_parser import parse_food_text as ai_parse

            ai_items = await ai_parse(", ".join(unknown_tokens))
            if ai_items:
                items.extend(ai_items)
            else:
                # AI returned empty – create fallback items
                for token in unknown_tokens:
                    items.append(FoodItem(name=token, calories=0, category="yellow"))
        except Exception:
            logger.warning(
                "ai_food_parser_unavailable",
                unknown_tokens=unknown_tokens,
            )
            for token in unknown_tokens:
                items.append(FoodItem(name=token, calories=0, category="yellow"))

    return items


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
        1. Call ``parse_food_text`` to convert *raw_text* into ``FoodItem[]``.
        2. Save a ``FoodEntry`` row.
        3. Return structured response.
    """
    if logged_at is None:
        logged_at = datetime.now(timezone.utc)

    parsed_items = await parse_food_text(raw_text)
    total_calories = sum(item.calories for item in parsed_items)

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
