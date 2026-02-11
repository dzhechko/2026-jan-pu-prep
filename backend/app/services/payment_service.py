"""Payment service – subscription lifecycle management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription
from app.models.user import User

logger = structlog.get_logger()


async def create_subscription(
    db: AsyncSession,
    user_id: UUID,
    plan: str = "premium",
    provider: str = "telegram",
    provider_id: str | None = None,
) -> Subscription:
    """Create a new subscription for the user.

    TODO:
        - Validate the payment with the payment provider (Telegram Stars)
        - Handle upgrade / downgrade flows
        - Send confirmation notification via Telegram bot
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        provider=provider,
        provider_id=provider_id,
        status="active",
        started_at=now,
        expires_at=expires_at,
    )
    db.add(subscription)

    # Update user status
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.subscription_status = "premium"
        user.subscription_expires_at = expires_at

    await db.flush()

    logger.info(
        "subscription_created",
        user_id=str(user_id),
        plan=plan,
        expires_at=expires_at.isoformat(),
    )

    return subscription


async def cancel_subscription(
    db: AsyncSession,
    user_id: UUID,
) -> bool:
    """Cancel the user's active subscription.

    The subscription remains valid until ``expires_at`` but won't renew.
    Returns True if a subscription was found and cancelled.
    """
    stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user_id,
            Subscription.status == "active",
        )
    )
    result = await db.execute(stmt)
    subscription = result.scalar_one_or_none()

    if subscription is None:
        return False

    subscription.status = "cancelled"
    subscription.cancelled_at = datetime.now(timezone.utc)

    # Update user status — access continues until expires_at
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user:
        user.subscription_status = "cancelled"

    await db.flush()

    logger.info("subscription_cancelled", user_id=str(user_id))
    return True
