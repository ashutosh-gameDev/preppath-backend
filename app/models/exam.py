import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin
from app.models.enums import ExamEventType

exam_event_courses = Table(
    "exam_event_courses",
    Base.metadata,
    Column("exam_event_id", UUID(as_uuid=True), ForeignKey("exam_events.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)


class Exam(Base, UUIDPKMixin, TimestampMixin):
    """
    A concrete exam students can follow (e.g. 'SSC CGL 2026'). Optionally
    scoped to a Course so PYQs/mock tests built for that course can be
    grouped under the exam. Also what individual questions tag themselves to
    via Question.exam_id (+ year/source) to record which real PYQ paper a
    question is from - see admin/questions.py's paper-tag handling.
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
    result...) - the source content for student notifications. Delivered by
    course, not by follow: a student sees an event if it targets no specific
    courses (global - `courses` empty) or targets a course they're enrolled
    in (see CourseEnrollment) - no per-student "follow this exam" action
    needed. `UserExamFollow` still exists for a student's own "exams I care
    about" bookmark list, but no longer gates what notifications they get -
    see services/notification_service.py.
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
    courses: Mapped[list["Course"]] = relationship(secondary=exam_event_courses)

    @property
    def course_ids(self) -> list[uuid.UUID]:
        """Convenience for ExamEventOut - from_attributes reads a property
        exactly like a column, so the schema needs no separate unwrapping."""
        return [c.id for c in self.courses]


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
