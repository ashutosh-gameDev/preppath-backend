import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PYQPaper(Base, UUIDPKMixin, TimestampMixin):
    """
    The specific PYQ paper a question is from, e.g. "SSC CGL 2023 Tier 1
    Shift 1" - the one field every question carries for categorizing and
    bulk-editing by paper (see Question.pyq_paper_id).

    Deliberately NOT the same thing as `Exam` (the followable, notification
    entity on the Notifications admin page) and NOT a foreign key to it -
    `exam_name` here is plain free text. Tagging a question to a PYQ paper
    must never create or touch an Exam row, and creating an Exam for
    notifications must never create or touch a PYQ paper. They looked like
    the same table once (before this was split out) and that was confusing;
    keeping them fully separate, with this one named unambiguously as "PYQ
    Paper" everywhere in the UI, is the whole point.

    Also deliberately NOT tied to `Test` (test_type='pyq') - a question is
    tagged to its PYQ paper before any full Test row exists for it (that's
    how the admin test builder's "load questions from a PYQ paper" picker
    works: it pulls already-tagged standalone questions together into a new
    Test). Requiring a Test to exist first would invert that workflow.
    """
    __tablename__ = "pyq_papers"

    exam_name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # e.g. "Tier 1 Shift 1"
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Optional scoping, purely descriptive - not enforced against the
    # questions tagged to this paper.
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
