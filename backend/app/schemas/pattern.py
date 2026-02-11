"""Pattern schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PatternData(BaseModel):
    id: UUID
    type: str
    description_ru: str
    confidence: float
    discovered_at: datetime

    model_config = {"from_attributes": True}


class RiskScore(BaseModel):
    level: str
    time_window: str | None = None
    recommendation: str | None = None


class PatternsResponse(BaseModel):
    patterns: list[PatternData]
    risk_today: RiskScore | None = None


class PatternFeedback(BaseModel):
    """User disputes a pattern."""
    pass  # No body needed, just the path param


class PatternFeedbackResponse(BaseModel):
    status: str
    new_confidence: float
    active: bool
