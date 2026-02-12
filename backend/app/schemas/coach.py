"""Pydantic schemas for the AI Coach feature."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CoachMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500)


class CoachMessageData(BaseModel):
    id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachMessageResponse(BaseModel):
    message: CoachMessageData


class CoachHistoryResponse(BaseModel):
    messages: list[CoachMessageData]
    has_more: bool
