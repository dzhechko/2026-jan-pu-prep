"""FastAPI application entry point for NutriMind."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.config import settings

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lifespan – set up / tear down shared resources
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Create the async DB engine and Redis pool on startup; dispose on shutdown."""
    engine: AsyncEngine = create_async_engine(
        settings.DATABASE_URL,
        echo=(settings.APP_ENV == "development"),
        pool_size=10,
        max_overflow=20,
    )
    application.state.db_engine = engine
    application.state.db_session_factory = async_sessionmaker(
        engine, expire_on_commit=False
    )

    application.state.redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    # Seed CBT lessons if the table is empty (idempotent)
    async with application.state.db_session_factory() as session:
        from app.services.lesson_service import seed_lessons
        await seed_lessons(session)
        await session.commit()

    # Start scheduler for periodic jobs (pattern detection, insights, risk, reminders)
    if settings.SCHEDULER_ENABLED:
        from app.scheduler import configure_scheduler, scheduler

        configure_scheduler()
        scheduler.start()
        logger.info("scheduler_started")

    logger.info("startup_complete", env=settings.APP_ENV, version=settings.APP_VERSION)

    yield

    # Shutdown scheduler
    if settings.SCHEDULER_ENABLED:
        from app.scheduler import scheduler

        scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    await application.state.redis.aclose()
    await engine.dispose()
    logger.info("shutdown_complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NutriMind API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – allow Telegram WebApp origins and localhost during development
# ---------------------------------------------------------------------------

ALLOWED_ORIGINS = [
    "https://web.telegram.org",
    "https://nutrimind.app",
    settings.TELEGRAM_MINI_APP_URL,
    # Dev origins
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in ALLOWED_ORIGINS if o],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler – return a consistent error envelope
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            }
        },
    )


# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

from app.routers import (  # noqa: E402
    auth,
    onboarding,
    food,
    insights,
    patterns,
    lessons,
    payments,
    invite,
    privacy,
    coach,
)

app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(food.router)
app.include_router(insights.router)
app.include_router(patterns.router)
app.include_router(lessons.router)
app.include_router(payments.router)
app.include_router(invite.router)
app.include_router(privacy.router)
app.include_router(coach.router)


# ---------------------------------------------------------------------------
# Health-check endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", tags=["health"])
async def health() -> dict:
    """Shallow health check – always returns OK if the process is running."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/health/ready", tags=["health"])
async def health_ready(request: Request) -> JSONResponse:
    """Deep health check – verifies connectivity to Postgres and Redis."""
    errors: list[str] = []

    # Check database
    try:
        async with request.app.state.db_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        errors.append(f"database: {exc}")

    # Check Redis
    try:
        await request.app.state.redis.ping()
    except Exception as exc:
        errors.append(f"redis: {exc}")

    if errors:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "version": settings.APP_VERSION,
                "errors": errors,
            },
        )

    return JSONResponse(
        status_code=200,
        content={"status": "ok", "version": settings.APP_VERSION},
    )
