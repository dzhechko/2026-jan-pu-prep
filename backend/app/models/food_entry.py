"""Food entry model – individual food log records."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, SmallInteger, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FoodEntry(Base):
    __tablename__ = "food_entries"
    __table_args__ = (
        Index("ix_food_entries_user_logged", "user_id", "logged_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_items: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    total_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mood: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context: Mapped[str | None] = mapped_column(String(255), nullable=True)

    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    hour: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="food_entries")  # noqa: F821

    def __repr__(self) -> str:
        return f"<FoodEntry {self.id} user={self.user_id}>"
