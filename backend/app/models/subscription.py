"""Subscription model – payment and plan tracking."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="free")
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="subscriptions")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Subscription {self.plan} status={self.status}>"
