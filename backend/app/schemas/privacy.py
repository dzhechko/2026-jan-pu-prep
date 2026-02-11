"""Schemas for data-privacy endpoints (US-7.1 / US-7.2)."""

from pydantic import BaseModel


class ExportResponse(BaseModel):
    """Full data export for the user."""

    profile: dict
    ai_profile: dict | None
    food_entries: list[dict]
    patterns: list[dict]
    insights: list[dict]
    lesson_progress: list[dict]
    subscriptions: list[dict]
    invites_sent: list[dict]


class DeleteAccountRequest(BaseModel):
    confirmation: str  # Must equal "УДАЛИТЬ"


class DeleteAccountResponse(BaseModel):
    status: str
    message: str
