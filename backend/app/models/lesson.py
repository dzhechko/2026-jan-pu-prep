"""CBT lesson models – educational content and user progress."""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CBTLesson(Base):
    __tablename__ = "cbt_lessons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lesson_order: Mapped[int] = mapped_column(SmallInteger, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    pattern_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(64)), nullable=True
    )
    duration_min: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)

    # ── Relationships ────────────────────────────────────────────
    progress_records: Mapped[list["UserLessonProgress"]] = relationship(
        back_populates="lesson", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CBTLesson #{self.lesson_order}: {self.title}>"


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cbt_lessons.id", ondelete="CASCADE"),
        primary_key=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ────────────────────────────────────────────
    lesson: Mapped["CBTLesson"] = relationship(back_populates="progress_records")

    def __repr__(self) -> str:
        return f"<UserLessonProgress user={self.user_id} lesson={self.lesson_id}>"
