"""Privacy service -- data export and account deletion (US-7.1 / US-7.2)."""

from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.ai_profile import AIProfile
from app.models.food_entry import FoodEntry
from app.models.insight import Insight
from app.models.invite import Invite
from app.models.lesson import CBTLesson, UserLessonProgress
from app.models.pattern import Pattern
from app.models.subscription import Subscription
from app.models.user import User
from app.services.payment_service import cancel_subscription

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_value(v: object) -> object:
    """Convert UUID and datetime values to JSON-friendly representations."""
    from datetime import datetime
    from uuid import UUID as UUIDType

    if isinstance(v, UUIDType):
        return str(v)
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _model_to_dict(obj: object, fields: list[str]) -> dict:
    """Convert a SQLAlchemy model instance to a dict with the given fields."""
    return {f: _serialize_value(getattr(obj, f)) for f in fields}


# ---------------------------------------------------------------------------
# US-7.1  Data export
# ---------------------------------------------------------------------------


async def export_user_data(db: AsyncSession, user_id: UUID) -> dict:
    """Export all user data as a structured dict matching ExportResponse."""

    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return {
            "profile": {},
            "ai_profile": None,
            "food_entries": [],
            "patterns": [],
            "insights": [],
            "lesson_progress": [],
            "subscriptions": [],
            "invites_sent": [],
        }

    # Profile
    profile = _model_to_dict(user, [
        "id", "telegram_id", "telegram_username", "first_name",
        "language_code", "subscription_status", "subscription_expires_at",
        "insights_received", "onboarding_complete", "created_at", "updated_at",
    ])

    # AI profile
    ai_result = await db.execute(
        select(AIProfile).where(AIProfile.user_id == user_id)
    )
    ai_profile_obj = ai_result.scalar_one_or_none()
    ai_profile = (
        _model_to_dict(ai_profile_obj, [
            "id", "user_id", "interview_answers", "cluster_id",
            "risk_model", "last_updated",
        ])
        if ai_profile_obj
        else None
    )

    # Food entries
    fe_result = await db.execute(
        select(FoodEntry).where(FoodEntry.user_id == user_id)
    )
    food_entries = [
        _model_to_dict(e, [
            "id", "user_id", "raw_text", "parsed_items", "total_calories",
            "mood", "context", "logged_at", "day_of_week", "hour", "created_at",
        ])
        for e in fe_result.scalars().all()
    ]

    # Patterns
    pat_result = await db.execute(
        select(Pattern).where(Pattern.user_id == user_id)
    )
    patterns = [
        _model_to_dict(p, [
            "id", "user_id", "type", "description_ru", "confidence",
            "evidence", "active", "discovered_at",
        ])
        for p in pat_result.scalars().all()
    ]

    # Insights
    ins_result = await db.execute(
        select(Insight).where(Insight.user_id == user_id)
    )
    insights = [
        _model_to_dict(i, [
            "id", "user_id", "pattern_id", "title", "body", "action",
            "type", "seen", "is_locked", "created_at",
        ])
        for i in ins_result.scalars().all()
    ]

    # Lesson progress (joined with CBTLesson for title)
    lp_result = await db.execute(
        select(UserLessonProgress)
        .options(joinedload(UserLessonProgress.lesson))
        .where(UserLessonProgress.user_id == user_id)
    )
    lesson_progress = [
        {
            "user_id": str(lp.user_id),
            "lesson_id": str(lp.lesson_id),
            "lesson_title": lp.lesson.title if lp.lesson else None,
            "completed_at": lp.completed_at.isoformat() if lp.completed_at else None,
        }
        for lp in lp_result.scalars().all()
    ]

    # Subscriptions
    sub_result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscriptions = [
        _model_to_dict(s, [
            "id", "user_id", "plan", "provider", "provider_id", "status",
            "started_at", "expires_at", "cancelled_at",
        ])
        for s in sub_result.scalars().all()
    ]

    # Invites sent
    inv_result = await db.execute(
        select(Invite).where(Invite.inviter_id == user_id)
    )
    invites_sent = [
        _model_to_dict(inv, [
            "id", "inviter_id", "invite_code", "invitee_id",
            "redeemed_at", "created_at",
        ])
        for inv in inv_result.scalars().all()
    ]

    return {
        "profile": profile,
        "ai_profile": ai_profile,
        "food_entries": food_entries,
        "patterns": patterns,
        "insights": insights,
        "lesson_progress": lesson_progress,
        "subscriptions": subscriptions,
        "invites_sent": invites_sent,
    }


# ---------------------------------------------------------------------------
# US-7.2  Account deletion
# ---------------------------------------------------------------------------


async def delete_user_account(db: AsyncSession, user_id: UUID) -> bool:
    """Delete the user and all associated data.

    Returns True if the user was found and deleted, False otherwise.
    CASCADE foreign keys handle deletion of related records.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        return False

    # Cancel active subscription if any
    await cancel_subscription(db, user_id)

    # Delete the user — CASCADE handles the rest
    await db.delete(user)
    await db.flush()

    logger.info("account_deleted", user_id=str(user_id))
    return True
