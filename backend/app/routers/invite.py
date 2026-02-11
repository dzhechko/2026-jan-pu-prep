"""Invite router – referral code generation and redemption."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.dependencies import CurrentUser, DbSession

router = APIRouter(prefix="/api/invite", tags=["invite"])


class RedeemRequest(BaseModel):
    invite_code: str


@router.post("/generate")
async def generate_invite(
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Generate a unique invite code for the current user."""
    # TODO: Call invite_service.generate_invite()
    # TODO: Return the invite code and shareable link
    return {
        "status": "ok",
        "invite_code": "placeholder-code",
        "share_url": "https://t.me/nutrimind_bot?start=placeholder-code",
    }


@router.post("/redeem")
async def redeem_invite(
    body: RedeemRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Redeem an invite code.

    Both the inviter and the invitee receive bonus insights.
    """
    # TODO: Call invite_service.redeem_invite()
    # TODO: Validate code exists and not already redeemed
    # TODO: Award bonuses to both parties
    return {
        "status": "ok",
        "message": "Invite redeemed successfully",
    }
