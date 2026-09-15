import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class Paper(Base, UUIDPKMixin, TimestampMixin):
    """
    A PYQ/exam paper a question can be tagged to, e.g. "SSC CGL 2023 Tier 1
    Shift 1" - the single field every question carries for categorizing and
    bulk-editing by paper (see Question.paper_id).

    Deliberately NOT a foreign key to `Exam` (see that model's docstring):
    Exam is the public, student-facing "you can follow this and get
    notified" entity. Before this split, tagging a question to a paper meant
    creating/picking an Exam row, so every one-off paper an admin tagged a
    question to also cluttered the exam-notifications list. `exam_name` here
    is deliberately just free text - nothing stops it matching a real Exam's
    name for the same real-world exam, but that's a naming convention, not a
    database relationship, and creating a Paper never creates or touches an
    Exam.
    """
    __tablename__ = "papers"

    exam_name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # e.g. "Tier 1 Shift 1" - was the `source` column on Question before
    # this split.
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Optional scoping, same reasoning as Exam.course_id - purely descriptive,
    # not enforced against the questions tagged to this paper.
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )

    course = relationship("Course")

    @property
    def display_name(self) -> str:
        parts = [self.exam_name]
        if self.year:
            parts.append(str(self.year))
        if self.label:
            parts.append(self.label)
        return " ".join(parts)
