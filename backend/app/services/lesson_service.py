"""CBT lesson service – content retrieval and progress tracking."""

from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lesson import CBTLesson, UserLessonProgress
from app.schemas.lesson import LessonData, LessonResponse, ProgressData

logger = structlog.get_logger()


async def get_progress(db: AsyncSession, user_id: UUID) -> ProgressData:
    """Return overall lesson completion progress for a user."""
    total_stmt = select(func.count()).select_from(CBTLesson)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar_one()

    completed_stmt = (
        select(func.count())
        .select_from(UserLessonProgress)
        .where(UserLessonProgress.user_id == user_id)
    )
    completed_result = await db.execute(completed_stmt)
    current = completed_result.scalar_one()

    return ProgressData(current=current, total=total)


async def get_lesson(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> LessonResponse | None:
    """Return a lesson by ID with progress context."""
    stmt = select(CBTLesson).where(CBTLesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if lesson is None:
        return None

    progress = await get_progress(db, user_id)

    return LessonResponse(
        lesson=LessonData(
            id=lesson.id,
            title=lesson.title,
            content_md=lesson.content_md,
            duration_min=lesson.duration_min,
        ),
        progress=progress,
    )


async def complete_lesson(
    db: AsyncSession,
    lesson_id: UUID,
    user_id: UUID,
) -> bool:
    """Mark a lesson as completed. Returns True if newly completed."""
    # Check if already completed
    existing = await db.execute(
        select(UserLessonProgress).where(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False  # Already completed

    progress = UserLessonProgress(user_id=user_id, lesson_id=lesson_id)
    db.add(progress)
    await db.flush()

    logger.info(
        "lesson_completed",
        user_id=str(user_id),
        lesson_id=str(lesson_id),
    )
    return True
