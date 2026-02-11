"""AI profile model – stores interview answers, cluster, and risk model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AIProfile(Base):
    __tablename__ = "ai_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    interview_answers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    risk_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="ai_profile")  # noqa: F821

    def __repr__(self) -> str:
        return f"<AIProfile user_id={self.user_id} cluster={self.cluster_id}>"
