import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPKMixin


class PYQPaper(Base, UUIDPKMixin, TimestampMixin):
    """
    The specific PYQ paper a question is from, e.g. "SSC CGL 2023 Tier 1
    Shift 1" - the one field every question carries for categorizing and
    bulk-editing by paper (see Question.pyq_paper_id). `exam_name` is plain
    free text (there's no separate followable Exam entity in this platform -
    Course is the only real organizing entity above a paper).

    Deliberately NOT tied to `Test` (test_type='pyq') - a question is
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

    # Students only see published papers; only a super admin flips this.
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    course = relationship("Course")

    @property
    def display_name(self) -> str:
        parts = [self.exam_name]
        if self.year:
            parts.append(str(self.year))
        if self.label:
            parts.append(self.label)
        return " ".join(parts)
