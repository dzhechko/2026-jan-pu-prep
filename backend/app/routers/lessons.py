"""CBT lessons router – educational content and progress tracking."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.schemas.lesson import LessonResponse, LessonsListResponse
from app.services import lesson_service

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("", response_model=LessonsListResponse)
async def list_lessons(
    db: DbSession,
    current_user: CurrentUser,
) -> LessonsListResponse:
    """Return all CBT lessons with the user's completion status."""
    user_id: UUID = current_user["user_id"]
    return await lesson_service.get_all_lessons(db, user_id)


@router.get("/recommended", response_model=LessonResponse | None)
async def get_recommended(
    db: DbSession,
    current_user: CurrentUser,
) -> LessonResponse | None:
    """Return today's recommended lesson based on user's patterns."""
    user_id: UUID = current_user["user_id"]
    result = await lesson_service.get_recommended_lesson(db, user_id)
    if result is None:
        return None
    return result


@router.get("/{lesson_id}", response_model=LessonResponse)
async def get_lesson(
    lesson_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> LessonResponse:
    """Return a single CBT lesson with the user's progress context."""
    user_id: UUID = current_user["user_id"]
    result = await lesson_service.get_lesson(db, lesson_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return result


@router.post("/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Mark a lesson as completed for the current user."""
    user_id: UUID = current_user["user_id"]
    newly_completed = await lesson_service.complete_lesson(db, lesson_id, user_id)
    return {
        "status": "ok",
        "lesson_id": str(lesson_id),
        "newly_completed": newly_completed,
    }
