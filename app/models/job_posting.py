import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class JobPosting(Base, UUIDPKMixin, TimestampMixin):
    """
    A government/private job vacancy notification shown on the student
    Notifications page's Jobs tab - distinct from Question/Test content
    entirely. Students set their own date_of_birth/qualification once (Profile) and
    the Jobs tab filters to postings they're actually eligible for by age
    (min_age/max_age) and qualification.
    """
    __tablename__ = "job_postings"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Free text (e.g. "10th Pass", "Graduate", "Any") rather than an enum -
    # same extensibility reasoning as Question.language.
    qualification: Mapped[str | None] = mapped_column(String(100), nullable=True)
    apply_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Optional scoping to one course (e.g. only relevant to SSC CGL
    # students) - null means relevant to everyone.
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    posted_date: Mapped[date] = mapped_column(Date, nullable=False)
    application_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    course = relationship("Course")
