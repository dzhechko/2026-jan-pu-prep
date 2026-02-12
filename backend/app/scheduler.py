"""APScheduler configuration for periodic background jobs."""

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.workers.scheduler_jobs import (
    run_daily_insights,
    run_daily_patterns,
    run_daily_risk,
    run_food_reminder,
)

logger = structlog.get_logger()

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


def configure_scheduler() -> None:
    """Register all periodic jobs with the scheduler."""
    scheduler.add_job(
        run_daily_patterns,
        CronTrigger(hour=3, minute=0),
        id="daily_patterns",
        name="Daily pattern detection",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_insights,
        CronTrigger(hour=6, minute=0),
        id="daily_insights",
        name="Daily insight generation",
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_risk,
        CronTrigger(hour=7, minute=0),
        id="daily_risk",
        name="Daily risk calculation",
        replace_existing=True,
    )
    scheduler.add_job(
        run_food_reminder,
        CronTrigger(hour=14, minute=0),
        id="food_reminder",
        name="Food logging reminder",
        replace_existing=True,
    )

    job_ids = [j.id for j in scheduler.get_jobs()]
    logger.info("scheduler_configured", jobs=job_ids)
