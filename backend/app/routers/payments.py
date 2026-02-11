"""Payments router – subscription management."""

from fastapi import APIRouter

from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/subscribe")
async def subscribe(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Create a new premium subscription.

    Integrates with Telegram Payments / Stars.
    """
    # TODO: Accept SubscribeRequest body (plan, payment_token)
    # TODO: Call payment_service.create_subscription()
    # TODO: Validate payment with Telegram Bot API
    # TODO: Update user.subscription_status
    return {
        "status": "ok",
        "message": "Subscription created",
        "plan": "premium",
    }


@router.delete("/subscription")
async def cancel_subscription(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Cancel the current user's active subscription."""
    # TODO: Call payment_service.cancel_subscription()
    # TODO: Set cancelled_at, update user.subscription_status to "cancelled"
    return {
        "status": "ok",
        "message": "Subscription cancelled",
    }
