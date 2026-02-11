"""Onboarding router – user interview and profile setup."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models.ai_profile import AIProfile
from app.models.user import User
from app.schemas.onboarding import InterviewRequest, InterviewResponse
from app.services.onboarding_service import assign_cluster

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/interview", response_model=InterviewResponse)
async def submit_interview(
    body: InterviewRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> InterviewResponse:
    """Submit onboarding interview answers.

    Stores the answers in the AI profile, assigns a cluster,
    and marks the user's onboarding as complete.
    """
    user_id = current_user["user_id"]

    # Fetch the user from the database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Determine cluster from answers
    cluster_id = assign_cluster(body.answers)

    # Serialize answers to JSON-compatible format
    interview_answers = [
        {"question_id": a.question_id, "answer_id": a.answer_id}
        for a in body.answers
    ]

    # Create or update AIProfile
    result = await db.execute(
        select(AIProfile).where(AIProfile.user_id == user_id)
    )
    ai_profile = result.scalar_one_or_none()

    if ai_profile is None:
        ai_profile = AIProfile(
            user_id=user_id,
            interview_answers=interview_answers,
            cluster_id=cluster_id,
        )
        db.add(ai_profile)
    else:
        ai_profile.interview_answers = interview_answers
        ai_profile.cluster_id = cluster_id

    # Mark onboarding as complete
    user.onboarding_complete = True

    await db.flush()

    return InterviewResponse(
        profile_initialized=True,
        cluster_id=cluster_id,
    )
