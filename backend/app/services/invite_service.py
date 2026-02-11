"""Invite service – referral code generation and redemption."""

import secrets
from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite

logger = structlog.get_logger()


def _generate_code(length: int = 8) -> str:
    """Generate a URL-safe random invite code."""
    return secrets.token_urlsafe(length)[:length].upper()


async def generate_invite(
    db: AsyncSession,
    user_id: UUID,
) -> Invite:
    """Generate a unique invite code for the user."""
    # Generate a unique code (retry on collision)
    for _ in range(5):
        code = _generate_code()
        existing = await db.execute(
            select(Invite).where(Invite.invite_code == code)
        )
        if existing.scalar_one_or_none() is None:
            break
    else:
        raise RuntimeError("Failed to generate unique invite code after 5 attempts")

    invite = Invite(
        inviter_id=user_id,
        invite_code=code,
    )
    db.add(invite)
    await db.flush()

    logger.info("invite_generated", user_id=str(user_id), code=code)
    return invite


async def redeem_invite(
    db: AsyncSession,
    invite_code: str,
    invitee_id: UUID,
) -> Invite | None:
    """Redeem an invite code.

    Returns the invite if successfully redeemed, or None if the code
    is invalid or already used.

    TODO:
        - Award bonus insights to both inviter and invitee
        - Send notification to inviter
    """
    stmt = select(Invite).where(Invite.invite_code == invite_code)
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if invite is None:
        logger.warning("invite_not_found", code=invite_code)
        return None

    if invite.invitee_id is not None:
        logger.warning("invite_already_redeemed", code=invite_code)
        return None

    if invite.inviter_id == invitee_id:
        logger.warning("invite_self_redeem", code=invite_code, user_id=str(invitee_id))
        return None

    invite.invitee_id = invitee_id
    invite.redeemed_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        "invite_redeemed",
        code=invite_code,
        inviter_id=str(invite.inviter_id),
        invitee_id=str(invitee_id),
    )
    return invite
