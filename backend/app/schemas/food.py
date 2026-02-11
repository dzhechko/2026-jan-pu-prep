"""Food logging schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FoodLogRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=500)
    mood: Literal["great", "ok", "meh", "bad", "awful"] | None = None
    context: Literal["home", "work", "street", "restaurant"] | None = None
    logged_at: datetime | None = None


class FoodItem(BaseModel):
    name: str
    calories: int
    category: Literal["green", "yellow", "orange"] = "yellow"


class FoodLogResponse(BaseModel):
    entry_id: UUID
    parsed_items: list[FoodItem]
    total_calories: int


class FoodHistoryEntry(BaseModel):
    id: UUID
    raw_text: str
    parsed_items: list[FoodItem]
    total_calories: int | None
    mood: str | None
    context: str | None
    logged_at: datetime

    model_config = {"from_attributes": True}


class FoodHistoryResponse(BaseModel):
    entries: list[FoodHistoryEntry]
    total: int
