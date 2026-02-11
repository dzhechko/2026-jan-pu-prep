"""Pydantic schemas for payment / subscription endpoints."""

from datetime import datetime

from pydantic import BaseModel


class SubscribeRequest(BaseModel):
    plan: str = "premium"  # "premium" for now
    provider: str = "telegram"
    provider_id: str | None = None  # payment token from Telegram Stars


class SubscriptionResponse(BaseModel):
    status: str  # "active" | "cancelled" | "none"
    plan: str | None  # "premium" | None
    expires_at: datetime | None
    cancelled_at: datetime | None


class SubscribeResponse(BaseModel):
    status: str  # "ok"
    plan: str
    expires_at: datetime


class CancelResponse(BaseModel):
    status: str  # "ok"
    message: str
