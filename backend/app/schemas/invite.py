"""Pydantic schemas for the invite / referral feature (US-6.1)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InviteGenerateResponse(BaseModel):
    invite_code: str
    share_url: str


class RedeemRequest(BaseModel):
    invite_code: str


class RedeemResponse(BaseModel):
    status: str  # "ok" | "error"
    message: str
    premium_days: int | None = None


class InviteInfoResponse(BaseModel):
    id: UUID
    invite_code: str
    share_url: str
    redeemed: bool
    invitee_id: UUID | None = None
    redeemed_at: datetime | None = None
    created_at: datetime


class MyInvitesResponse(BaseModel):
    invites: list[InviteInfoResponse]
    total_redeemed: int
