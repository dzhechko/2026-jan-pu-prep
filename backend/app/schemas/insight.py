"""Insight schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InsightData(BaseModel):
    id: UUID
    title: str
    body: str
    action: str | None
    type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightResponse(BaseModel):
    insight: InsightData
    is_locked: bool
