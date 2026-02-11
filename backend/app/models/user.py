"""User model – core Telegram user record."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True
    )
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="ru")

    subscription_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="free"
    )
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    insights_received: Mapped[int] = mapped_column(default=0)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    ai_profile: Mapped["AIProfile"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, lazy="selectin"
    )
    food_entries: Mapped[list["FoodEntry"]] = relationship(  # noqa: F821
        back_populates="user", lazy="selectin"
    )
    patterns: Mapped[list["Pattern"]] = relationship(  # noqa: F821
        back_populates="user", lazy="selectin"
    )
    insights: Mapped[list["Insight"]] = relationship(  # noqa: F821
        back_populates="user", lazy="selectin"
    )
    subscriptions: Mapped[list["Subscription"]] = relationship(  # noqa: F821
        back_populates="user", lazy="selectin"
    )
    sent_invites: Mapped[list["Invite"]] = relationship(  # noqa: F821
        back_populates="inviter",
        foreign_keys="Invite.inviter_id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User {self.telegram_id} ({self.first_name})>"
