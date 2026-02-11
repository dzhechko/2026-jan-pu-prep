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
    # Супы и первые блюда
    "борщ": {"calories": 150, "category": "green"},
    "суп": {"calories": 100, "category": "green"},
    "щи": {"calories": 130, "category": "green"},
    "солянка": {"calories": 170, "category": "yellow"},
    "окрошка": {"calories": 120, "category": "green"},
    "уха": {"calories": 90, "category": "green"},
    "бульон": {"calories": 40, "category": "green"},
    "рассольник": {"calories": 140, "category": "green"},
    # Крупы и гарниры
    "каша": {"calories": 200, "category": "yellow"},
    "гречка": {"calories": 180, "category": "yellow"},
    "овсянка": {"calories": 150, "category": "yellow"},
    "рис": {"calories": 200, "category": "yellow"},
    "макароны": {"calories": 300, "category": "yellow"},
    "пюре": {"calories": 160, "category": "yellow"},
    "картошка": {"calories": 130, "category": "yellow"},
    "картофель": {"calories": 130, "category": "yellow"},
    "перловка": {"calories": 170, "category": "yellow"},
    "пшёнка": {"calories": 170, "category": "yellow"},
    "булгур": {"calories": 180, "category": "yellow"},
    "кускус": {"calories": 180, "category": "yellow"},
    "лапша": {"calories": 280, "category": "yellow"},
    # Мясо и птица
    "курица": {"calories": 250, "category": "yellow"},
    "говядина": {"calories": 250, "category": "yellow"},
    "свинина": {"calories": 350, "category": "orange"},
    "индейка": {"calories": 200, "category": "green"},
    "баранина": {"calories": 300, "category": "orange"},
    "котлета": {"calories": 280, "category": "yellow"},
    "сосиска": {"calories": 250, "category": "orange"},
    "сосиски": {"calories": 250, "category": "orange"},
    "колбаса": {"calories": 300, "category": "orange"},
    "ветчина": {"calories": 270, "category": "orange"},
    "шашлык": {"calories": 320, "category": "orange"},
    "фарш": {"calories": 250, "category": "yellow"},
    "печень": {"calories": 170, "category": "yellow"},
    "куриная грудка": {"calories": 165, "category": "green"},
    # Рыба и морепродукты
    "рыба": {"calories": 150, "category": "green"},
    "лосось": {"calories": 200, "category": "green"},
    "сёмга": {"calories": 200, "category": "green"},
    "тунец": {"calories": 130, "category": "green"},
    "треска": {"calories": 80, "category": "green"},
    "селёдка": {"calories": 180, "category": "yellow"},
    "креветки": {"calories": 95, "category": "green"},
    "кальмар": {"calories": 100, "category": "green"},
    # Молочные продукты
    "молоко": {"calories": 60, "category": "green"},
    "кефир": {"calories": 50, "category": "green"},
    "йогурт": {"calories": 70, "category": "green"},
    "творог": {"calories": 120, "category": "green"},
    "сметана": {"calories": 200, "category": "yellow"},
    "сыр": {"calories": 350, "category": "orange"},
    "масло": {"calories": 750, "category": "orange"},
    "сливки": {"calories": 200, "category": "orange"},
    "ряженка": {"calories": 65, "category": "green"},
    # Хлеб и выпечка
    "хлеб": {"calories": 80, "category": "yellow"},
    "батон": {"calories": 90, "category": "yellow"},
    "лаваш": {"calories": 80, "category": "yellow"},
    "булка": {"calories": 300, "category": "orange"},
    "круассан": {"calories": 350, "category": "orange"},
    "блины": {"calories": 230, "category": "yellow"},
    "блинчики": {"calories": 230, "category": "yellow"},
    "оладьи": {"calories": 250, "category": "yellow"},
    "сырники": {"calories": 220, "category": "yellow"},
    "пирожок": {"calories": 280, "category": "orange"},
    "пирог": {"calories": 300, "category": "orange"},
    "печенье": {"calories": 400, "category": "orange"},
    # Готовые блюда
    "пельмени": {"calories": 350, "category": "orange"},
    "вареники": {"calories": 250, "category": "yellow"},
    "пицца": {"calories": 270, "category": "orange"},
    "бутерброд": {"calories": 250, "category": "yellow"},
    "плов": {"calories": 350, "category": "orange"},
    "голубцы": {"calories": 200, "category": "yellow"},
    "винегрет": {"calories": 130, "category": "green"},
    "оливье": {"calories": 200, "category": "yellow"},
    "шаурма": {"calories": 350, "category": "orange"},
    "суши": {"calories": 180, "category": "yellow"},
    "роллы": {"calories": 200, "category": "yellow"},
    "омлет": {"calories": 180, "category": "yellow"},
    "яичница": {"calories": 200, "category": "yellow"},
    "запеканка": {"calories": 200, "category": "yellow"},
    "каша овсяная": {"calories": 150, "category": "yellow"},
    "каша гречневая": {"calories": 180, "category": "yellow"},
    "каша рисовая": {"calories": 200, "category": "yellow"},
    # Овощи
    "салат": {"calories": 50, "category": "green"},
    "огурец": {"calories": 15, "category": "green"},
    "помидор": {"calories": 20, "category": "green"},
    "морковь": {"calories": 35, "category": "green"},
    "капуста": {"calories": 25, "category": "green"},
    "свёкла": {"calories": 45, "category": "green"},
    "лук": {"calories": 40, "category": "green"},
    "перец": {"calories": 25, "category": "green"},
    "баклажан": {"calories": 25, "category": "green"},
    "кабачок": {"calories": 20, "category": "green"},
    "брокколи": {"calories": 30, "category": "green"},
    "цветная капуста": {"calories": 30, "category": "green"},
    "грибы": {"calories": 30, "category": "green"},
    "шпинат": {"calories": 23, "category": "green"},
    "горошек": {"calories": 75, "category": "green"},
    "фасоль": {"calories": 120, "category": "yellow"},
    "кукуруза": {"calories": 95, "category": "yellow"},
    # Фрукты и ягоды
    "яблоко": {"calories": 52, "category": "green"},
    "банан": {"calories": 105, "category": "yellow"},
    "апельсин": {"calories": 45, "category": "green"},
    "мандарин": {"calories": 40, "category": "green"},
    "груша": {"calories": 55, "category": "green"},
    "виноград": {"calories": 70, "category": "yellow"},
    "арбуз": {"calories": 30, "category": "green"},
    "клубника": {"calories": 35, "category": "green"},
    "черника": {"calories": 45, "category": "green"},
    "персик": {"calories": 45, "category": "green"},
    "слива": {"calories": 45, "category": "green"},
    "киви": {"calories": 50, "category": "green"},
    "ананас": {"calories": 50, "category": "green"},
    "гранат": {"calories": 70, "category": "green"},
    "хурма": {"calories": 65, "category": "green"},
    # Яйца
    "яйцо": {"calories": 70, "category": "green"},
    "яйца": {"calories": 140, "category": "green"},
    # Напитки
    "чай": {"calories": 5, "category": "green"},
    "кофе": {"calories": 30, "category": "green"},
    "сок": {"calories": 50, "category": "yellow"},
    "компот": {"calories": 60, "category": "yellow"},
    "кисель": {"calories": 70, "category": "yellow"},
    "вода": {"calories": 0, "category": "green"},
    "лимонад": {"calories": 45, "category": "orange"},
    "кола": {"calories": 42, "category": "orange"},
    "квас": {"calories": 27, "category": "yellow"},
    "смузи": {"calories": 100, "category": "yellow"},
    "какао": {"calories": 80, "category": "yellow"},
    # Сладости и снеки
    "шоколад": {"calories": 540, "category": "orange"},
    "конфета": {"calories": 400, "category": "orange"},
    "конфеты": {"calories": 400, "category": "orange"},
    "торт": {"calories": 350, "category": "orange"},
    "мороженое": {"calories": 200, "category": "orange"},
    "зефир": {"calories": 300, "category": "orange"},
    "мармелад": {"calories": 290, "category": "orange"},
    "халва": {"calories": 520, "category": "orange"},
    "варенье": {"calories": 270, "category": "orange"},
    "мёд": {"calories": 320, "category": "yellow"},
    "орехи": {"calories": 600, "category": "orange"},
    "семечки": {"calories": 580, "category": "orange"},
    "чипсы": {"calories": 530, "category": "orange"},
    "сухарики": {"calories": 400, "category": "orange"},
    # Прочее
    "тофу": {"calories": 80, "category": "green"},
    "сахар": {"calories": 400, "category": "orange"},
    "майонез": {"calories": 620, "category": "orange"},
    "кетчуп": {"calories": 100, "category": "yellow"},
    "соус": {"calories": 150, "category": "yellow"},
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
