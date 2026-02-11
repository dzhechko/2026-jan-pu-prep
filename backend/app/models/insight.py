"""Insight model – AI-generated insights for users."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("ix_insights_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patterns.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="general")

    seen: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="insights")  # noqa: F821
    pattern: Mapped["Pattern | None"] = relationship(  # noqa: F821
        back_populates="insights"
    )

    def __repr__(self) -> str:
        return f"<Insight {self.type}: {self.title[:30]}>"
