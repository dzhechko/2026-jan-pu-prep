"""Batch job functions called by APScheduler for periodic tasks."""

import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models.food_entry import FoodEntry
from app.models.pattern import Pattern
from app.models.user import User
from app.services.notification_service import send_telegram_message

logger = structlog.get_logger()

# Moscow timezone offset (UTC+3)
MSK_OFFSET = timedelta(hours=3)


async def _get_session_factory() -> async_sessionmaker:
    """Create a session factory for batch jobs."""
    engine = create_async_engine(settings.DATABASE_URL, pool_size=2)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _run_daily_patterns_async() -> None:
    """Iterate active users with 10+ food entries and run pattern detection."""
    logger.info("scheduler_job_started", job="daily_patterns")

    session_factory = await _get_session_factory()
    async with session_factory() as session:
        # Find users with 10+ food entries
        stmt = (
            select(User.id)
            .join(FoodEntry, FoodEntry.user_id == User.id)
            .group_by(User.id)
            .having(func.count(FoodEntry.id) >= 10)
        )
        result = await session.execute(stmt)
        user_ids = [row[0] for row in result.all()]

    logger.info("daily_patterns_users_found", count=len(user_ids))

    for user_id in user_ids:
        try:
            async with session_factory() as session:
                from app.services.pattern_service import detect_patterns

                await detect_patterns(session, user_id)
                await session.commit()
            logger.info("daily_patterns_user_done", user_id=str(user_id))
        except Exception as exc:
            logger.error(
                "daily_patterns_user_error",
                user_id=str(user_id),
                error=str(exc),
            )

    await session_factory.kw["bind"].dispose()
    logger.info("scheduler_job_completed", job="daily_patterns", users=len(user_ids))


def run_daily_patterns() -> None:
    """Sync entry point for APScheduler."""
    asyncio.run(_run_daily_patterns_async())


async def _run_daily_insights_async() -> None:
    """Generate daily insights for users with 3+ days of data."""
    logger.info("scheduler_job_started", job="daily_insights")

    session_factory = await _get_session_factory()
    async with session_factory() as session:
        # Find users with entries spanning 3+ days
        three_days_ago = datetime.now(timezone.utc) - timedelta(days=3)
        stmt = (
            select(User.id, User.telegram_id)
            .join(FoodEntry, FoodEntry.user_id == User.id)
            .where(FoodEntry.logged_at <= three_days_ago)
            .group_by(User.id, User.telegram_id)
        )
        result = await session.execute(stmt)
        users = result.all()

    logger.info("daily_insights_users_found", count=len(users))

    for user_id, telegram_id in users:
        try:
            async with session_factory() as session:
                from app.services.insight_service import generate_daily_insight

                insight = await generate_daily_insight(session, user_id)
                await session.commit()

            if insight:
                await send_telegram_message(
                    chat_id=telegram_id,
                    text=(
                        "\U0001f4a1 <b>Новый инсайт готов!</b>\n\n"
                        f"<b>{insight.title}</b>\n"
                        "Открой приложение, чтобы прочитать."
                    ),
                )
        except Exception as exc:
            logger.error(
                "daily_insights_user_error",
                user_id=str(user_id),
                error=str(exc),
            )

    await session_factory.kw["bind"].dispose()
    logger.info("scheduler_job_completed", job="daily_insights", users=len(users))


def run_daily_insights() -> None:
    """Sync entry point for APScheduler."""
    asyncio.run(_run_daily_insights_async())


async def _run_daily_risk_async() -> None:
    """Calculate daily risk for users with patterns and send alerts."""
    logger.info("scheduler_job_started", job="daily_risk")

    session_factory = await _get_session_factory()
    async with session_factory() as session:
        # Find users with active patterns
        stmt = (
            select(User.id, User.telegram_id)
            .join(Pattern, Pattern.user_id == User.id)
            .where(Pattern.active.is_(True))
            .group_by(User.id, User.telegram_id)
        )
        result = await session.execute(stmt)
        users = result.all()

    logger.info("daily_risk_users_found", count=len(users))

    for user_id, telegram_id in users:
        try:
            async with session_factory() as session:
                from app.services.risk_service import calculate_risk

                risk = await calculate_risk(session, user_id)

            if risk and risk.level in ("high", "critical"):
                await send_telegram_message(
                    chat_id=telegram_id,
                    text=(
                        "\u26a0\ufe0f <b>Внимание — повышенный риск</b>\n\n"
                        f"{risk.recommendation}\n\n"
                        "Открой приложение для подробностей."
                    ),
                )
                logger.info(
                    "daily_risk_alert_sent",
                    user_id=str(user_id),
                    level=risk.level,
                )
        except Exception as exc:
            logger.error(
                "daily_risk_user_error",
                user_id=str(user_id),
                error=str(exc),
            )

    await session_factory.kw["bind"].dispose()
    logger.info("scheduler_job_completed", job="daily_risk", users=len(users))


def run_daily_risk() -> None:
    """Sync entry point for APScheduler."""
    asyncio.run(_run_daily_risk_async())


async def _run_food_reminder_async() -> None:
    """Find users who haven't logged food today by 14:00 MSK and send reminder."""
    logger.info("scheduler_job_started", job="food_reminder")

    session_factory = await _get_session_factory()
    now_utc = datetime.now(timezone.utc)
    today_start_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    async with session_factory() as session:
        # Users who have logged at least once (active users) but not today
        users_with_entries_today = (
            select(FoodEntry.user_id)
            .where(FoodEntry.logged_at >= today_start_utc)
            .distinct()
        )

        stmt = (
            select(User.id, User.telegram_id)
            .where(
                User.onboarding_complete.is_(True),
                User.id.not_in(users_with_entries_today),
            )
        )
        result = await session.execute(stmt)
        users = result.all()

    logger.info("food_reminder_users_found", count=len(users))

    for user_id, telegram_id in users:
        try:
            await send_telegram_message(
                chat_id=telegram_id,
                text=(
                    "\U0001f37d <b>Не забудьте записать приёмы пищи!</b>\n\n"
                    "Регулярное ведение дневника помогает выявить "
                    "паттерны питания."
                ),
            )
        except Exception as exc:
            logger.error(
                "food_reminder_error",
                user_id=str(user_id),
                error=str(exc),
            )

    await session_factory.kw["bind"].dispose()
    logger.info("scheduler_job_completed", job="food_reminder", users=len(users))


def run_food_reminder() -> None:
    """Sync entry point for APScheduler."""
    asyncio.run(_run_food_reminder_async())
