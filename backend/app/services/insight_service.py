"""Insight generation service -- daily AI insights for users."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food_entry import FoodEntry
from app.models.insight import Insight
from app.models.pattern import Pattern
from app.models.user import User
from app.schemas.insight import InsightData, InsightResponse

logger = structlog.get_logger()

# Free-tier weekly insight limit
FREE_WEEKLY_INSIGHT_LIMIT = 3


# ---------------------------------------------------------------------------
# Russian-language insight templates (CBT-informed, empathetic, non-judgmental)
# ---------------------------------------------------------------------------

PATTERN_INSIGHTS: dict[str, dict] = {
    "time": {
        "title": "Ваш режим питания",
        "body_template": (
            "Мы заметили, что вы часто едите больше в вечернее время. "
            "{evidence} Попробуйте увеличить порцию на обеде — "
            "это может снизить вечерний аппетит."
        ),
        "action": "Завтра добавьте к обеду порцию белка (курица, яйца, тофу)",
    },
    "mood": {
        "title": "Настроение и еда",
        "body_template": (
            "Ваши данные показывают связь между настроением и "
            "калорийностью еды. {evidence} Это нормальная реакция — "
            "осознание уже первый шаг."
        ),
        "action": "При плохом настроении попробуйте 5-минутную прогулку перед едой",
    },
    "context": {
        "title": "Где вы едите",
        "body_template": (
            "Интересная находка: место приёма пищи влияет на ваш выбор. "
            "{evidence} Осознанность в выборе места — "
            "ключ к управлению питанием."
        ),
        "action": "На этой неделе попробуйте один ресторанный приём заменить домашним",
    },
    "skip": {
        "title": "Пропуски приёмов пищи",
        "body_template": (
            "Мы заметили паттерн пропуска обеда. {evidence} "
            "Регулярное питание помогает избежать вечернего переедания."
        ),
        "action": "Поставьте напоминание на обед в 13:00",
    },
}

PROGRESS_INSIGHTS = [
    {
        "title": "Ваш прогресс",
        "body_template": (
            "За последнюю неделю вы записали {entry_count} приёмов пищи. "
            "{comparison} Продолжайте вести дневник — "
            "это главный инструмент осознанности."
        ),
        "action": "Постарайтесь записывать каждый приём пищи в течение следующей недели",
    },
]

CBT_INSIGHTS = [
    {
        "title": "Техника CBT: Пищевой дневник мыслей",
        "body": (
            "Когнитивно-поведенческая терапия учит замечать автоматические "
            "мысли перед едой. Перед следующим приёмом пищи задайте себе: "
            "\"Я ем потому что голоден, или по другой причине?\""
        ),
        "action": "Перед ужином запишите свои мысли и чувства в заметки",
    },
    {
        "title": "Техника CBT: Правило 10 минут",
        "body": (
            "Если вы чувствуете тягу к нездоровой еде, подождите 10 минут. "
            "Часто желание проходит — это работает принцип "
            "\"серфинг побуждений\" из CBT."
        ),
        "action": "При следующем импульсе перекусить поставьте таймер на 10 минут",
    },
    {
        "title": "Техника CBT: Осознанное питание",
        "body": (
            "Попробуйте есть без экрана. Исследования показывают, что "
            "осознанное внимание к еде снижает переедание на 20-30%."
        ),
        "action": "Один приём пищи сегодня проведите без телефона и телевизора",
    },
]

RISK_INSIGHTS = [
    {
        "title": "Итоги недели",
        "body_template": (
            "За эту неделю: {summary}. {risk_note} "
            "Каждая неделя — новый шанс для улучшений."
        ),
        "action": "Выберите одну небольшую цель на следующую неделю",
    },
]

# Fallback insight when no patterns or entries exist
FALLBACK_INSIGHT = {
    "title": "Начните свой путь к осознанному питанию",
    "body": (
        "Записывайте каждый приём пищи — даже небольшой перекус. "
        "Чем больше данных, тем точнее будут наши рекомендации. "
        "Осознанность начинается с наблюдения."
    ),
    "action": "Запишите свой следующий приём пищи с указанием настроения",
}


# ---------------------------------------------------------------------------
# Helper: count user insights
# ---------------------------------------------------------------------------


async def _count_user_insights(db: AsyncSession, user_id: UUID) -> int:
    """Count total insights generated for a user."""
    stmt = select(func.count()).select_from(Insight).where(Insight.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Helper: get active patterns
# ---------------------------------------------------------------------------


async def _get_active_patterns(db: AsyncSession, user_id: UUID) -> list[Pattern]:
    """Load active patterns for a user, ordered by confidence DESC."""
    stmt = (
        select(Pattern)
        .where(Pattern.user_id == user_id, Pattern.active.is_(True))
        .order_by(Pattern.confidence.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Helper: get recent food entries
# ---------------------------------------------------------------------------


async def _get_recent_entries(
    db: AsyncSession, user_id: UUID, days: int = 7
) -> list[FoodEntry]:
    """Load food entries from the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(FoodEntry)
        .where(FoodEntry.user_id == user_id, FoodEntry.logged_at >= cutoff)
        .order_by(FoodEntry.logged_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Local template-based insight generation
# ---------------------------------------------------------------------------


def _generate_local_insight(
    insight_type: str,
    patterns: list[Pattern],
    entries: list[FoodEntry],
    user: User,
    insight_count: int,
) -> tuple[str, str, str | None, UUID | None]:
    """Generate insight title, body, action, and optional pattern_id from local templates.

    Returns (title, body, action, pattern_id).
    """
    if insight_type == "pattern":
        return _generate_pattern_insight(patterns, entries)
    elif insight_type == "progress":
        return _generate_progress_insight(entries)
    elif insight_type == "cbt":
        return _generate_cbt_insight(insight_count)
    elif insight_type == "risk":
        return _generate_risk_insight(patterns, entries)
    else:
        return (
            FALLBACK_INSIGHT["title"],
            FALLBACK_INSIGHT["body"],
            FALLBACK_INSIGHT["action"],
            None,
        )


def _generate_pattern_insight(
    patterns: list[Pattern],
    entries: list[FoodEntry],
) -> tuple[str, str, str | None, UUID | None]:
    """Generate a pattern-based insight from the top active pattern."""
    if not patterns:
        # No patterns available -- use fallback
        return (
            FALLBACK_INSIGHT["title"],
            FALLBACK_INSIGHT["body"],
            FALLBACK_INSIGHT["action"],
            None,
        )

    top_pattern = patterns[0]
    pattern_type = top_pattern.type
    template = PATTERN_INSIGHTS.get(pattern_type)

    if not template:
        # Unknown pattern type -- use fallback with pattern description
        return (
            "Обнаружен паттерн",
            top_pattern.description_ru,
            "Обратите внимание на этот паттерн в течение следующей недели",
            top_pattern.id,
        )

    # Build evidence string from the pattern's evidence dict
    evidence_str = _format_evidence(top_pattern)

    body = template["body_template"].format(evidence=evidence_str)

    return (
        template["title"],
        body,
        template["action"],
        top_pattern.id,
    )


def _format_evidence(pattern: Pattern) -> str:
    """Format a pattern's evidence dict into a human-readable Russian string."""
    evidence = pattern.evidence or {}

    if pattern.type == "time":
        avg_lunch = evidence.get("avg_lunch_calories", "?")
        avg_evening = evidence.get("avg_evening_calories", "?")
        return f"Средние калории: обед {avg_lunch}, ужин {avg_evening}."
    elif pattern.type == "mood":
        avg_bad = evidence.get("avg_bad_mood_calories", "?")
        avg_ok = evidence.get("avg_ok_mood_calories", "?")
        return (
            f"При плохом настроении в среднем {avg_bad} ккал, "
            f"при нормальном — {avg_ok} ккал."
        )
    elif pattern.type == "context":
        avg_home = evidence.get("avg_home_calories", "?")
        avg_out = evidence.get("avg_out_calories", "?")
        return f"Дома в среднем {avg_home} ккал, вне дома — {avg_out} ккал."
    elif pattern.type == "skip":
        skip_days = evidence.get("skip_binge_days", "?")
        total_days = evidence.get("total_days", "?")
        return f"За последний период: {skip_days} из {total_days} дней."
    else:
        return pattern.description_ru


def _generate_progress_insight(
    entries: list[FoodEntry],
) -> tuple[str, str, str | None, UUID | None]:
    """Generate a progress insight comparing this week to last week."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    this_week = [e for e in entries if e.logged_at and e.logged_at >= week_ago]
    last_week = [
        e for e in entries
        if e.logged_at and two_weeks_ago <= e.logged_at < week_ago
    ]

    entry_count = len(this_week)

    if last_week:
        diff = entry_count - len(last_week)
        if diff > 0:
            comparison = f"Это на {diff} больше, чем на прошлой неделе — отличный прогресс!"
        elif diff < 0:
            comparison = (
                f"На прошлой неделе было {len(last_week)} записей. "
                "Попробуйте вернуться к прежнему темпу."
            )
        else:
            comparison = "Стабильный результат — так держать!"
    else:
        comparison = "Это хорошее начало!"

    template = PROGRESS_INSIGHTS[0]
    body = template["body_template"].format(
        entry_count=entry_count,
        comparison=comparison,
    )

    return (template["title"], body, template["action"], None)


def _generate_cbt_insight(
    insight_count: int,
) -> tuple[str, str, str | None, UUID | None]:
    """Rotate through CBT insights based on the insight count."""
    idx = insight_count % len(CBT_INSIGHTS)
    cbt = CBT_INSIGHTS[idx]
    return (cbt["title"], cbt["body"], cbt["action"], None)


def _generate_risk_insight(
    patterns: list[Pattern],
    entries: list[FoodEntry],
) -> tuple[str, str, str | None, UUID | None]:
    """Generate a weekly risk/summary insight."""
    # Build summary parts
    summary_parts = []

    entry_count = len(entries)
    if entry_count > 0:
        summary_parts.append(f"вы записали {entry_count} приёмов пищи")
    else:
        summary_parts.append("на этой неделе записей пока нет")

    if patterns:
        pattern_types = [p.type for p in patterns]
        type_names = {
            "time": "режим питания",
            "mood": "связь настроения и еды",
            "context": "влияние места",
            "skip": "пропуски приёмов пищи",
        }
        named = [type_names.get(t, t) for t in pattern_types[:2]]
        summary_parts.append(
            "обнаружены паттерны: " + ", ".join(named)
        )

    summary = "; ".join(summary_parts)

    # Risk note
    if len(patterns) >= 2:
        risk_note = "Несколько активных паттернов — обратите на них внимание."
    elif len(patterns) == 1:
        risk_note = "Один активный паттерн — вы уже на пути к осознанности."
    else:
        risk_note = "Продолжайте записывать приёмы пищи для более точного анализа."

    template = RISK_INSIGHTS[0]
    body = template["body_template"].format(summary=summary, risk_note=risk_note)

    return (template["title"], body, template["action"], None)


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------


async def generate_daily_insight(db: AsyncSession, user_id: UUID) -> Insight | None:
    """Generate a new insight for the user using local templates.

    This is typically called as a background job or via the /generate endpoint.

    Steps:
        1. Load user
        2. Count existing insights for rotation
        3. Determine insight type based on 7-day rotation
        4. Load patterns and recent entries
        5. Generate insight using local templates
        6. Determine if locked (free tier, > 3 insights)
        7. Persist
        8. Increment user.insights_received
    """
    logger.info("insight_generation_started", user_id=str(user_id))

    # 1. Load user
    user = await db.get(User, user_id)
    if not user:
        logger.warning("insight_generation_user_not_found", user_id=str(user_id))
        return None

    # 2. Count existing insights for rotation
    insight_count = await _count_user_insights(db, user_id)
    day_in_cycle = (insight_count % 7) + 1  # 1-7

    # 3. Determine insight type based on 7-day rotation
    if day_in_cycle <= 3:
        insight_type = "pattern"
    elif day_in_cycle <= 5:
        insight_type = "progress"
    elif day_in_cycle == 6:
        insight_type = "cbt"
    else:
        insight_type = "risk"

    # 4. Load patterns and recent entries
    patterns = await _get_active_patterns(db, user_id)
    entries = await _get_recent_entries(db, user_id, days=7)

    # 5. Generate insight using local templates
    title, body, action, pattern_id = _generate_local_insight(
        insight_type, patterns, entries, user, insight_count
    )

    # 6. Determine if locked (free tier, > 3 insights)
    is_locked = (
        user.subscription_status == "free"
        and (user.insights_received or 0) >= FREE_WEEKLY_INSIGHT_LIMIT
    )

    # 7. Persist
    insight = Insight(
        user_id=user_id,
        pattern_id=pattern_id,
        title=title,
        body=body,
        action=action,
        type=insight_type,
        is_locked=is_locked,
    )
    db.add(insight)

    # 8. Increment counter
    user.insights_received = (user.insights_received or 0) + 1

    await db.flush()

    logger.info(
        "insight_generated",
        user_id=str(user_id),
        insight_type=insight_type,
        is_locked=is_locked,
        title=title[:50],
    )
    return insight


# ---------------------------------------------------------------------------
# Get today's insight
# ---------------------------------------------------------------------------


async def get_today_insight(
    db: AsyncSession,
    user_id: UUID,
) -> InsightResponse:
    """Return today's insight for the user.

    If the user is on the free tier and has exceeded the weekly limit,
    the insight is returned with ``is_locked=True``.
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Try to find today's insight
    stmt = (
        select(Insight)
        .where(
            and_(
                Insight.user_id == user_id,
                Insight.created_at >= today_start,
            )
        )
        .order_by(Insight.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    insight = result.scalar_one_or_none()

    if insight is None:
        # No insight yet today -- return placeholder
        return InsightResponse(
            insight=InsightData(
                id=user_id,  # placeholder
                title="Ваш инсайт готовится",
                body=(
                    "Запишите ещё несколько приёмов пищи, и мы "
                    "подготовим ваш первый персональный инсайт."
                ),
                action=None,
                type="general",
                created_at=datetime.now(timezone.utc),
            ),
            is_locked=False,
        )

    # Check subscription for locking
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    is_locked = False
    if user and user.subscription_status == "free":
        is_locked = insight.is_locked

    return InsightResponse(
        insight=InsightData(
            id=insight.id,
            title=insight.title,
            body=insight.body if not is_locked else insight.body[:100] + "...",
            action=insight.action if not is_locked else None,
            type=insight.type,
            created_at=insight.created_at,
        ),
        is_locked=is_locked,
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


async def submit_feedback(
    db: AsyncSession,
    user_id: UUID,
    insight_id: UUID,
    rating: str,
) -> dict:
    """Submit feedback for an insight.

    Marks the insight as seen when rated.
    """
    insight = await db.get(Insight, insight_id)
    if not insight or insight.user_id != user_id:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight.seen = True
    await db.flush()

    logger.info(
        "insight_feedback",
        user_id=str(user_id),
        insight_id=str(insight_id),
        rating=rating,
    )

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Mark as seen
# ---------------------------------------------------------------------------


async def mark_seen(
    db: AsyncSession,
    user_id: UUID,
    insight_id: UUID,
) -> dict:
    """Mark an insight as seen by the user."""
    insight = await db.get(Insight, insight_id)
    if not insight or insight.user_id != user_id:
        raise HTTPException(status_code=404, detail="Insight not found")

    insight.seen = True
    await db.flush()

    logger.info(
        "insight_marked_seen",
        user_id=str(user_id),
        insight_id=str(insight_id),
    )

    return {"status": "ok"}
