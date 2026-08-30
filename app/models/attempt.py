import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPKMixin


class Attempt(Base, UUIDPKMixin):
    """
    THE single source of truth for every question a student has ever
    answered - whether solved standalone in practice mode or as part of a
    mock test / PYQ paper (`test_attempt_id` is set in the latter case).

    Every dashboard number (progress graphs, strong/weak areas, improvement,
    recommendations, subject/topic performance, XP) is derived from this
    table. Nothing here is ever deleted.
    """
    __tablename__ = "attempts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True, index=True
    )
    test_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("test_attempts.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Denormalized at write time so analytics queries don't need to join
    # `questions` just to bucket by difficulty/type.
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    selected_option: Mapped[str | None] = mapped_column(String(1), nullable=True)  # null = skipped
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_taken_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    question = relationship("Question")
    course = relationship("Course")
    subject = relationship("Subject")
    topic = relationship("Topic")
