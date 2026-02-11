"""Pattern detection service -- discover behavioral eating patterns."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_profile import AIProfile
from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.schemas.pattern import PatternData, PatternsResponse
from app.services.risk_service import calculate_risk

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Cluster-based cold start patterns
# ---------------------------------------------------------------------------

CLUSTER_PATTERNS: dict[str, list[dict]] = {
    "emotional_eater": [
        {
            "type": "mood",
            "description_ru": (
                "Люди с похожим профилем часто едят больше "
                "при стрессе или плохом настроении"
            ),
            "confidence": 0.3,
        },
    ],
    "chaotic_eater": [
        {
            "type": "skip",
            "description_ru": (
                "Люди с похожим профилем часто пропускают "
                "приёмы пищи и переедают позже"
            ),
            "confidence": 0.3,
        },
    ],
    "unstructured_eater": [
        {
            "type": "time",
            "description_ru": (
                "Люди с похожим профилем часто едят "
                "в нерегулярное время"
            ),
            "confidence": 0.3,
        },
    ],
    "mindless_eater": [
        {
            "type": "context",
            "description_ru": (
                "Люди с похожим профилем часто едят "
                "на ходу или перед экраном"
            ),
            "confidence": 0.3,
        },
    ],
    "general": [
        {
            "type": "time",
            "description_ru": (
                "Обратите внимание на время приёмов пищи — "
                "это может раскрыть интересные закономерности"
            ),
            "confidence": 0.25,
        },
    ],
}

# ---------------------------------------------------------------------------
# Hour buckets for time pattern detection
# ---------------------------------------------------------------------------

_MORNING = range(6, 11)     # 6-10
_LUNCH = range(11, 15)      # 11-14
_AFTERNOON = range(15, 18)  # 15-17
_EVENING = range(18, 22)    # 18-21
_NIGHT = list(range(22, 24)) + list(range(0, 6))  # 22-5


def _hour_bucket(hour: int) -> str:
    """Return the time bucket name for a given hour."""
    if hour in _MORNING:
        return "morning"
    if hour in _LUNCH:
        return "lunch"
    if hour in _AFTERNOON:
        return "afternoon"
    if hour in _EVENING:
        return "evening"
    return "night"


# ---------------------------------------------------------------------------
# Statistical pattern detectors
# ---------------------------------------------------------------------------


def _detect_time_patterns(entries: list[FoodEntry]) -> list[dict]:
    """Detect if evening calories consistently exceed 2x lunch calories.

    Returns a list with zero or one pattern dict.
    """
    bucket_calories: dict[str, list[int]] = defaultdict(list)
    for e in entries:
        if e.hour is not None and e.total_calories is not None:
            bucket = _hour_bucket(e.hour)
            bucket_calories[bucket].append(e.total_calories)

    lunch_cals = bucket_calories.get("lunch", [])
    evening_cals = bucket_calories.get("evening", [])

    if not lunch_cals or not evening_cals:
        return []

    avg_lunch = sum(lunch_cals) / len(lunch_cals)
    avg_evening = sum(evening_cals) / len(evening_cals)

    if avg_lunch == 0:
        return []

    if avg_evening > 2 * avg_lunch:
        # Confidence = proportion of days with data
        total_days = len({e.logged_at.date() for e in entries if e.logged_at})
        relevant_days = len(
            {
                e.logged_at.date()
                for e in entries
                if e.hour is not None
                and _hour_bucket(e.hour) == "evening"
                and e.total_calories is not None
            }
        )
        confidence = min(1.0, relevant_days / max(total_days, 1))
        return [
            {
                "type": "time",
                "description_ru": (
                    "Вы съедаете вечером значительно больше, "
                    "чем в обед — вечерние калории превышают "
                    "обеденные более чем в 2 раза"
                ),
                "confidence": confidence,
                "evidence": {
                    "avg_lunch_calories": round(avg_lunch, 1),
                    "avg_evening_calories": round(avg_evening, 1),
                    "ratio": round(avg_evening / avg_lunch, 2),
                },
            }
        ]

    return []


def _detect_mood_patterns(entries: list[FoodEntry]) -> list[dict]:
    """Detect if bad/awful mood correlates with 1.5x higher calories.

    Returns a list with zero or one pattern dict.
    """
    mood_calories: dict[str, list[int]] = defaultdict(list)
    for e in entries:
        if e.mood and e.total_calories is not None:
            mood_calories[e.mood].append(e.total_calories)

    bad_moods = ["bad", "awful"]
    ok_moods = ["ok", "great"]

    bad_cals = []
    for m in bad_moods:
        bad_cals.extend(mood_calories.get(m, []))

    ok_cals = []
    for m in ok_moods:
        ok_cals.extend(mood_calories.get(m, []))

    if not bad_cals or not ok_cals:
        return []

    avg_bad = sum(bad_cals) / len(bad_cals)
    avg_ok = sum(ok_cals) / len(ok_cals)

    if avg_ok == 0:
        return []

    if avg_bad > 1.5 * avg_ok:
        total_days = len({e.logged_at.date() for e in entries if e.logged_at})
        relevant_days = len(
            {
                e.logged_at.date()
                for e in entries
                if e.mood in bad_moods
            }
        )
        confidence = min(1.0, relevant_days / max(total_days, 1))
        return [
            {
                "type": "mood",
                "description_ru": (
                    "При плохом настроении вы съедаете "
                    "значительно больше калорий — "
                    "возможно, еда используется как способ "
                    "справиться с эмоциями"
                ),
                "confidence": confidence,
                "evidence": {
                    "avg_bad_mood_calories": round(avg_bad, 1),
                    "avg_ok_mood_calories": round(avg_ok, 1),
                    "ratio": round(avg_bad / avg_ok, 2),
                },
            }
        ]

    return []


def _detect_context_patterns(entries: list[FoodEntry]) -> list[dict]:
    """Detect if restaurant/street context leads to calorie spikes (>1.5x home).

    Returns a list with zero or one pattern dict.
    """
    context_calories: dict[str, list[int]] = defaultdict(list)
    for e in entries:
        if e.context and e.total_calories is not None:
            context_calories[e.context].append(e.total_calories)

    home_cals = context_calories.get("home", [])
    out_contexts = ["restaurant", "street"]

    out_cals = []
    for ctx in out_contexts:
        out_cals.extend(context_calories.get(ctx, []))

    if not home_cals or not out_cals:
        return []

    avg_home = sum(home_cals) / len(home_cals)
    avg_out = sum(out_cals) / len(out_cals)

    if avg_home == 0:
        return []

    if avg_out > 1.5 * avg_home:
        total_days = len({e.logged_at.date() for e in entries if e.logged_at})
        relevant_days = len(
            {
                e.logged_at.date()
                for e in entries
                if e.context in out_contexts
            }
        )
        confidence = min(1.0, relevant_days / max(total_days, 1))
        return [
            {
                "type": "context",
                "description_ru": (
                    "В ресторане или на ходу вы съедаете "
                    "значительно больше, чем дома — "
                    "обратите внимание на внешние факторы"
                ),
                "confidence": confidence,
                "evidence": {
                    "avg_home_calories": round(avg_home, 1),
                    "avg_out_calories": round(avg_out, 1),
                    "ratio": round(avg_out / avg_home, 2),
                },
            }
        ]

    return []


def _detect_skip_patterns(entries: list[FoodEntry]) -> list[dict]:
    """Detect if skipping lunch (no 11-14h entry) correlates with evening binge.

    For each day, if there is no entry in 11-14h AND entries in 18-22h
    account for > 60% of that day's total calories, it counts as a skip day.

    Returns a list with zero or one pattern dict.
    """
    # Group entries by date
    daily: dict[str, list[FoodEntry]] = defaultdict(list)
    for e in entries:
        if e.logged_at:
            date_key = e.logged_at.date().isoformat()
            daily[date_key].append(e)

    skip_binge_days = 0
    total_days = len(daily)

    if total_days == 0:
        return []

    for _date_key, day_entries in daily.items():
        has_lunch = any(
            e.hour is not None and e.hour in _LUNCH
            for e in day_entries
        )
        if has_lunch:
            continue

        # No lunch entry -- check if evening dominates
        daily_total = sum(
            e.total_calories for e in day_entries
            if e.total_calories is not None
        )
        if daily_total == 0:
            continue

        evening_total = sum(
            e.total_calories
            for e in day_entries
            if e.total_calories is not None
            and e.hour is not None
            and e.hour in _EVENING
        )

        if evening_total / daily_total > 0.6:
            skip_binge_days += 1

    if skip_binge_days == 0:
        return []

    confidence = min(1.0, skip_binge_days / max(total_days, 1))
    return [
        {
            "type": "skip",
            "description_ru": (
                "Вы часто пропускаете обед, а затем "
                "переедаете вечером — большая часть "
                "дневных калорий приходится на ужин"
            ),
            "confidence": confidence,
            "evidence": {
                "skip_binge_days": skip_binge_days,
                "total_days": total_days,
                "ratio": round(skip_binge_days / total_days, 2),
            },
        }
    ]


# ---------------------------------------------------------------------------
# Cold start
# ---------------------------------------------------------------------------


async def _cold_start_patterns(
    db: AsyncSession,
    user_id: UUID,
) -> list[dict]:
    """Return cluster-based patterns for users with insufficient data.

    Confidence is capped at 0.4.
    """
    stmt = select(AIProfile).where(AIProfile.user_id == user_id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    cluster_id = profile.cluster_id if profile else None
    if not cluster_id or cluster_id not in CLUSTER_PATTERNS:
        cluster_id = "general"

    raw_patterns = CLUSTER_PATTERNS[cluster_id]
    patterns = []
    for p in raw_patterns:
        patterns.append(
            {
                "type": p["type"],
                "description_ru": p["description_ru"],
                "confidence": min(0.4, p["confidence"]),
                "evidence": {"source": "cold_start", "cluster_id": cluster_id},
            }
        )

    logger.info(
        "cold_start_patterns",
        user_id=str(user_id),
        cluster_id=cluster_id,
        count=len(patterns),
    )
    return patterns


# ---------------------------------------------------------------------------
# Main detection pipeline
# ---------------------------------------------------------------------------


async def detect_patterns(db: AsyncSession, user_id: UUID) -> list[Pattern]:
    """Run the full statistical pattern detection pipeline for a user.

    Steps:
        1. Fetch food entries for the last 30 days.
        2. If < 10 entries, return cold-start patterns (confidence <= 0.4).
        3. If >= 10, run all statistical detectors.
        4. Rank by confidence DESC, filter >= 0.5, take top 5.
        5. Dedup against existing active patterns (same type).
        6. Deactivate old patterns of same type.
        7. Persist new patterns.
        8. Return newly discovered patterns.
    """
    logger.info("pattern_detection_started", user_id=str(user_id))

    # 1. Fetch food entries for last 30 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = (
        select(FoodEntry)
        .where(
            FoodEntry.user_id == user_id,
            FoodEntry.logged_at >= cutoff,
        )
        .order_by(FoodEntry.logged_at.desc())
    )
    result = await db.execute(stmt)
    entries = list(result.scalars().all())

    # 2. Cold start if insufficient data
    if len(entries) < 10:
        raw_patterns = await _cold_start_patterns(db, user_id)
    else:
        # 3. Run statistical detectors
        raw_patterns = []
        raw_patterns.extend(_detect_time_patterns(entries))
        raw_patterns.extend(_detect_mood_patterns(entries))
        raw_patterns.extend(_detect_context_patterns(entries))
        raw_patterns.extend(_detect_skip_patterns(entries))

    # 4. Rank by confidence DESC, filter >= 0.5 (for stat patterns), take top 5
    # For cold start patterns, keep them even below 0.5
    is_cold_start = len(entries) < 10
    if not is_cold_start:
        raw_patterns = [p for p in raw_patterns if p["confidence"] >= 0.5]

    raw_patterns.sort(key=lambda p: p["confidence"], reverse=True)
    raw_patterns = raw_patterns[:5]

    if not raw_patterns:
        logger.info("no_patterns_detected", user_id=str(user_id))
        return []

    # 5. Dedup against existing active patterns (same type)
    existing_stmt = (
        select(Pattern)
        .where(Pattern.user_id == user_id, Pattern.active.is_(True))
    )
    existing_result = await db.execute(existing_stmt)
    existing_patterns = list(existing_result.scalars().all())
    existing_types = {p.type for p in existing_patterns}

    new_raw = [p for p in raw_patterns if p["type"] not in existing_types]

    if not new_raw:
        logger.info(
            "all_patterns_already_exist",
            user_id=str(user_id),
            types=[p["type"] for p in raw_patterns],
        )
        return []

    # 6. Deactivate old patterns of same type
    new_types = {p["type"] for p in new_raw}
    for existing_p in existing_patterns:
        if existing_p.type in new_types:
            existing_p.active = False

    # 7. Persist new patterns
    new_patterns: list[Pattern] = []
    for p in new_raw:
        pattern = Pattern(
            user_id=user_id,
            type=p["type"],
            description_ru=p["description_ru"],
            confidence=p["confidence"],
            evidence=p.get("evidence"),
            active=True,
        )
        db.add(pattern)
        new_patterns.append(pattern)

    await db.flush()

    logger.info(
        "patterns_detected",
        user_id=str(user_id),
        count=len(new_patterns),
        types=[p.type for p in new_patterns],
    )
    return new_patterns


# ---------------------------------------------------------------------------
# Query active patterns
# ---------------------------------------------------------------------------


async def get_user_patterns(
    db: AsyncSession,
    user_id: UUID,
) -> PatternsResponse:
    """Return all active patterns for a user."""
    stmt = (
        select(Pattern)
        .where(Pattern.user_id == user_id, Pattern.active.is_(True))
        .order_by(Pattern.confidence.desc())
    )
    result = await db.execute(stmt)
    patterns = result.scalars().all()

    # Calculate today's risk score
    risk_today = await calculate_risk(db, user_id)

    return PatternsResponse(
        patterns=[
            PatternData(
                id=p.id,
                type=p.type,
                description_ru=p.description_ru,
                confidence=p.confidence,
                discovered_at=p.discovered_at,
            )
            for p in patterns
        ],
        risk_today=risk_today,
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


async def submit_feedback(
    db: AsyncSession,
    user_id: UUID,
    pattern_id: UUID,
) -> dict:
    """User disputes a pattern -- reduce confidence by 0.2.

    If confidence drops below 0.3, deactivate the pattern.
    """
    pattern = await db.get(Pattern, pattern_id)

    if not pattern or pattern.user_id != user_id:
        raise HTTPException(status_code=404, detail="Pattern not found")

    pattern.confidence = max(0.0, pattern.confidence - 0.2)
    if pattern.confidence < 0.3:
        pattern.active = False

    await db.flush()

    logger.info(
        "pattern_feedback",
        user_id=str(user_id),
        pattern_id=str(pattern_id),
        new_confidence=pattern.confidence,
        active=pattern.active,
    )

    return {
        "status": "ok",
        "new_confidence": pattern.confidence,
        "active": pattern.active,
    }
