import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class CourseEnrollment(Base, UUIDPKMixin, TimestampMixin):
    """
    A student's explicit choice to prepare for a course - drives the "My
    Courses" hub (student picks one at signup/onboarding, can add more
    later). Deliberately separate from `Attempt`/practice history: a student
    can be enrolled in a course before ever answering a question in it, and
    the enrollment list is what "My Courses" shows regardless of activity.
    """
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_course_enrollment"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )

    course = relationship("Course")
