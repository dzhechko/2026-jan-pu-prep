"""Risk calculation service – assess current eating behavior risk."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.schemas.pattern import RiskScore

logger = structlog.get_logger()

# CBT micro-exercises for risk alerts (Russian)
RISK_RECOMMENDATIONS: dict[str, str] = {
    "time": (
        "Попробуйте технику «10 минут»: подождите 10 минут "
        "перед перекусом. Часто желание проходит само."
    ),
    "mood": (
        "Остановитесь и сделайте 3 глубоких вдоха. "
        "Спросите себя: «Я голоден или мне грустно?»"
    ),
    "skip": (
        "Важно поесть сейчас! Пропуск приёма пищи повышает "
        "риск переедания вечером. Выберите лёгкий перекус."
    ),
    "context": (
        "Перед выходом из дома подумайте, что вы хотите съесть. "
        "Осознанный выбор — ваш главный инструмент."
    ),
    "default": (
        "Сделайте паузу и задайте себе вопрос: "
        "«Что я сейчас чувствую?» Осознанность — первый шаг."
    ),
}

TIME_WINDOW_LABELS: dict[str, str] = {
    "evening": "вечером (18:00–22:00)",
    "afternoon": "после обеда (15:00–18:00)",
    "night": "поздним вечером (22:00+)",
    "lunch": "в обеденное время (12:00–14:00)",
}


async def calculate_risk(
    db: AsyncSession,
    user_id: UUID,
    now: datetime | None = None,
) -> RiskScore | None:
    """Calculate today's risk score for a user.

    The risk model takes into account:
        - Active patterns and their confidence levels
        - Recent food entries (timing, calorie trends, mood)
        - Current time of day and day of week

    Parameters
    ----------
    db:
        Async database session.
    user_id:
        The user to assess.
    now:
        Override current time for testability.

    Returns
    -------
    RiskScore or None
        Risk assessment, or ``None`` when no active patterns exist.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    current_hour = now.hour
    current_dow = now.weekday()  # 0=Monday, 5=Saturday, 6=Sunday
    is_weekend = current_dow >= 5

    # 1. Load active patterns
    stmt = select(Pattern).where(
        Pattern.user_id == user_id,
        Pattern.active.is_(True),
    )
    result = await db.execute(stmt)
    patterns = result.scalars().all()

    if not patterns:
        return None  # No patterns = no risk assessment

    # 2. Load today's food entries
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    entry_stmt = select(FoodEntry).where(
        and_(
            FoodEntry.user_id == user_id,
            FoodEntry.logged_at >= today_start,
        )
    )
    entry_result = await db.execute(entry_stmt)
    today_entries = entry_result.scalars().all()

    # Check if lunch was logged (11-14h)
    lunch_logged = any(11 <= (e.hour or 0) <= 14 for e in today_entries)

    # Check today's moods
    today_moods = [e.mood for e in today_entries if e.mood]
    has_bad_mood = any(m in ("bad", "awful") for m in today_moods)

    # Total calories today
    total_cal_today = sum(e.total_calories or 0 for e in today_entries)
    high_cal_logged = total_cal_today > 1500  # Already ate a lot

    # 3. Calculate base risk
    risk = 0.0
    top_contributor = "default"
    top_contribution = 0.0
    time_window: str | None = None

    for pattern in patterns:
        contribution = 0.0

        if pattern.type == "time":
            # Evening overeating pattern -- risk rises as evening approaches
            if current_hour >= 15:  # After 3 PM, risk starts increasing
                hour_factor = min(1.0, (current_hour - 15) / 6)  # peaks at 21:00
                contribution = pattern.confidence * 0.4 * hour_factor
                if contribution > 0:
                    time_window = "evening"

        elif pattern.type == "mood":
            if has_bad_mood:
                contribution = pattern.confidence * 0.3

        elif pattern.type == "skip":
            if not lunch_logged and current_hour > 15:
                contribution = pattern.confidence * 0.5
                time_window = time_window or "evening"

        elif pattern.type == "context":
            contribution = pattern.confidence * 0.2

        risk += contribution
        if contribution > top_contribution:
            top_contribution = contribution
            top_contributor = pattern.type

    # 4. Adjustments
    if high_cal_logged:
        risk *= 0.7
    if is_weekend:
        risk *= 1.3

    # 5. Normalize to [0, 1]
    risk = max(0.0, min(1.0, risk))

    # 6. Classify
    if risk < 0.3:
        level = "low"
    elif risk <= 0.6:
        level = "medium"
    else:
        level = "high"

    # 7. Recommendation
    recommendation = RISK_RECOMMENDATIONS.get(
        top_contributor, RISK_RECOMMENDATIONS["default"]
    )

    # Time window label
    tw_label = TIME_WINDOW_LABELS.get(time_window) if time_window else None

    logger.info(
        "risk_calculated",
        user_id=str(user_id),
        level=level,
        raw_risk=round(risk, 3),
        top_contributor=top_contributor,
    )

    return RiskScore(
        level=level,
        time_window=tw_label,
        recommendation=recommendation,
    )
