"""Payments router – subscription management."""

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.schemas.payment import (
    CancelResponse,
    SubscribeRequest,
    SubscribeResponse,
    SubscriptionResponse,
)
from app.services import payment_service

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe(
    body: SubscribeRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> SubscribeResponse:
    """Create a new premium subscription.

    Integrates with Telegram Payments / Stars.
    """
    subscription = await payment_service.create_subscription(
        db,
        user_id=current_user["user_id"],
        plan=body.plan,
        provider=body.provider,
        provider_id=body.provider_id,
    )
    return SubscribeResponse(
        status="ok",
        plan=subscription.plan,
        expires_at=subscription.expires_at,
    )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: DbSession,
    current_user: CurrentUser,
) -> SubscriptionResponse:
    """Return the current user's subscription status."""
    info = await payment_service.get_subscription_status(
        db, user_id=current_user["user_id"]
    )
    return SubscriptionResponse(**info)


@router.delete("/subscription", response_model=CancelResponse)
async def cancel_subscription(
    db: DbSession,
    current_user: CurrentUser,
) -> CancelResponse:
    """Cancel the current user's active subscription."""
    cancelled = await payment_service.cancel_subscription(
        db, user_id=current_user["user_id"]
    )
    if not cancelled:
        raise HTTPException(status_code=404, detail="No active subscription found")
    return CancelResponse(status="ok", message="Subscription cancelled")
