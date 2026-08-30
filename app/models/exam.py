import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ExamEventType


class Exam(Base, UUIDPKMixin, TimestampMixin):
    """
    A concrete exam students can follow (e.g. 'SSC CGL 2026'). Optionally
    scoped to a Course so PYQs/mock tests built for that course can be
    grouped under the exam.
    """
    __tablename__ = "exams"

    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    conducting_body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    events: Mapped[list["ExamEvent"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan", order_by="ExamEvent.event_date"
    )


class ExamEvent(Base, UUIDPKMixin, TimestampMixin):
    """
    A dated milestone for an exam (application window, admit card, exam date,
    result...). This doubles as the source content for student notifications:
    a student following the exam sees upcoming events as reminders.
    """
    __tablename__ = "exam_events"

    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default=ExamEventType.OTHER)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    external_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    exam: Mapped["Exam"] = relationship(back_populates="events")


class UserExamFollow(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_exam_follows"
    __table_args__ = (UniqueConstraint("user_id", "exam_id", name="uq_user_exam_follow"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), nullable=False
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
