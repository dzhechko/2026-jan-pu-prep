"""CBT lessons router – educational content and progress tracking."""

from uuid import UUID

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession
from app.schemas.lesson import LessonData, LessonResponse, ProgressData

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> LessonResponse:
    """Return a single CBT lesson with the user's progress context."""
    # TODO: Call lesson_service.get_lesson()
    return LessonResponse(
        lesson=LessonData(
            id=lesson_id,
            title="Placeholder lesson",
            content_md="# Coming soon\n\nLesson content will be here.",
            duration_min=5,
        ),
        progress=ProgressData(current=0, total=0),
    )


@router.post("/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Mark a lesson as completed for the current user."""
    # TODO: Call lesson_service.complete_lesson()
    return {"status": "ok", "lesson_id": str(lesson_id)}
