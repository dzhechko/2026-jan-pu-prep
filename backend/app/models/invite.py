"""Invite model – referral system."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    invite_code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    invitee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    inviter: Mapped["User"] = relationship(  # noqa: F821
        back_populates="sent_invites",
        foreign_keys=[inviter_id],
    )
    invitee: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[invitee_id],
    )

    def __repr__(self) -> str:
        return f"<Invite code={self.invite_code} redeemed={self.redeemed_at is not None}>"
