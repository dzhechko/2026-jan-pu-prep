"""Onboarding router – user interview and profile setup."""

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/interview")
async def submit_interview(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Submit onboarding interview answers.

    Stores the answers in the AI profile and triggers cluster assignment.
    """
    # TODO: Accept InterviewRequest body schema
    # TODO: Create or update AIProfile with interview_answers
    # TODO: Trigger cluster assignment (background job)
    # TODO: Mark user.onboarding_complete = True
    return {
        "status": "ok",
        "message": "Interview submitted",
        "onboarding_complete": True,
    }
